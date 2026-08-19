from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetLoadResponse(BaseModel):
    status: str
    loaded_at: datetime
    countries_count: int
    rows_count: int
    sources: dict[str, str]


class CountrySeriesPoint(BaseModel):
    date: str
    country: str
    country_code: str
    who_region: str | None = None
    new_cases: float
    cumulative_cases: float
    new_deaths: float
    cumulative_deaths: float
    cases_ma7: float
    deaths_ma7: float
    growth_rate: float
    rolling_trend_14: float
    surge_ratio: float
    trend_label: str
    Covid_new_hospitalizations_last_7days: float | None = None
    Covid_new_icu_admissions_last_7days: float | None = None
    vaccination_coverage_all: float | None = None


class CountryDataResponse(BaseModel):
    country: str
    start_date: str
    end_date: str
    rows: int
    insights: list[str]
    data: list[CountrySeriesPoint]


class ForecastPoint(BaseModel):
    date: str
    predicted_cases: float
    trend_component: float
    residual_component: float
    seasonal_component: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    country: str
    horizon: int = Field(default=14, ge=7, le=14)
    generated_at: str
    history_end_date: str
    model_version: str
    forecast: list[ForecastPoint]
    weights: dict[str, float]
    model_metrics: dict[str, float]
    feature_importance: list[dict[str, float | str]]
    narrative: str


class TrendResponse(BaseModel):
    country: str
    classification: str
    score: float
    narrative: str
    latest_date: str
    drivers: dict[str, float | str | None]


class GlobalSummaryResponse(BaseModel):
    latest_date: str
    total_cases: float
    total_deaths: float
    new_cases_last_7d: float
    new_deaths_last_7d: float
    countries_tracked: int
    trend_counts: dict[str, int]
    top_surge_countries: list[dict[str, float | str]]
    global_series: list[dict[str, float | str]]
    source_window: dict[str, str]
    comparison_window: dict[str, float]


class CountriesResponse(BaseModel):
    countries: list[str]
