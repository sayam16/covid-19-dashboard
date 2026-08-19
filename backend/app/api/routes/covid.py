from __future__ import annotations

import logging
from datetime import datetime, timezone, date

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DataLoadRun, ForecastCache
from app.db.session import get_db
from app.schemas.covid import (
    CountriesResponse,
    CountryDataResponse,
    DatasetLoadResponse,
    ForecastResponse,
    GlobalSummaryResponse,
    TrendResponse,
)
from app.services.data_loader import CountryNotFoundError, data_loader_service
from app.services.forecast import forecast_service
from app.services.insights import insight_service

logger = logging.getLogger(__name__)

async def require_admin_key(x_admin_key: str | None = Header(default=None)):
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key header.")

def parse_date(value: str | None, param_name: str) -> str | None:
    if value is None:
        return None
    try:
        date.fromisoformat(value)
        return value
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{param_name} must be ISO 8601 (YYYY-MM-DD).")

router = APIRouter(tags=["covid"])


@router.post("/load-data", response_model=DatasetLoadResponse, dependencies=[Depends(require_admin_key)])
def load_data(
    force_reload: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    payload = data_loader_service.load_data(force_reload=force_reload)
    db.add(
        DataLoadRun(
            status=payload["status"],
            countries_count=payload["countries_count"],
            rows_count=payload["rows_count"],
        )
    )
    db.commit()
    return payload


@router.get("/countries", response_model=CountriesResponse)
def countries() -> dict[str, list[str]]:
    return {"countries": data_loader_service.list_countries()}


@router.get("/get-country-data", response_model=CountryDataResponse)
def get_country_data(
    country: str = Query(..., min_length=2),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> dict[str, object]:
    start_date = parse_date(start_date, "start_date")
    end_date = parse_date(end_date, "end_date")
    try:
        country_df = data_loader_service.get_country_data(country, start_date=start_date, end_date=end_date)
    except CountryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    insights = insight_service.summarize_country(country_df)
    response_df = country_df.copy()
    response_df["date"] = response_df["date"].dt.strftime("%Y-%m-%d")
    numeric_columns = response_df.select_dtypes(include=["number"]).columns
    response_df[numeric_columns] = response_df[numeric_columns].round(2)
    response_df = response_df.astype(object).replace({np.nan: None, np.inf: None, -np.inf: None})
    response_df["who_region"] = response_df["who_region"].fillna("Other")
    return {
        "country": country_df["country"].iloc[-1],
        "start_date": response_df["date"].iloc[0],
        "end_date": response_df["date"].iloc[-1],
        "rows": len(response_df),
        "insights": insights,
        "data": response_df.to_dict(orient="records"),
    }


@router.get("/predict", response_model=ForecastResponse)
def predict(
    country: str = Query(..., min_length=2),
    horizon: int = Query(default=14, ge=7, le=14),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        country_df = data_loader_service.get_country_data(country)
    except CountryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    latest_history_date = country_df["date"].iloc[-1].strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc)
    cached = (
        db.query(ForecastCache)
        .filter(
            ForecastCache.country == country_df["country"].iloc[-1],
            ForecastCache.horizon == horizon,
            ForecastCache.expires_at > now,
        )
        .order_by(ForecastCache.generated_at.desc())
        .first()
    )
    if (
        cached
        and cached.payload.get("history_end_date") == latest_history_date
        and cached.payload.get("model_version") == forecast_service.MODEL_VERSION
    ):
        logger.info("Cache hit for forecast of country: %s, horizon: %d", country, horizon)
        return cached.payload

    try:
        payload = forecast_service.predict(country=country, horizon=horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.add(ForecastCache.make(country=payload["country"], horizon=payload["horizon"], payload=payload))
    db.commit()
    return payload


@router.get("/trend", response_model=TrendResponse)
def trend(country: str = Query(..., min_length=2)) -> dict[str, object]:
    try:
        _, payload = data_loader_service.latest_assessment(country)
    except CountryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return payload


@router.get("/global-summary", response_model=GlobalSummaryResponse)
def global_summary() -> dict[str, object]:
    return data_loader_service.get_global_summary()
