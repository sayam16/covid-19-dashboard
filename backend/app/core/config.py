from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw: str | None, fallback: Path) -> Path:
    if not raw:
        return fallback.resolve()

    path = Path(raw)
    if path.is_absolute():
        return path.resolve()

    return (BACKEND_DIR / raw).resolve()


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "COVID Analytics API")
    app_env: str = os.getenv("APP_ENV", "development")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    cors_origins: list[str] = tuple(
        origin.strip()
        for origin in os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    )
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BACKEND_DIR / 'covid_analytics.db').as_posix()}",
    )
    auto_load_on_startup: bool = _parse_bool(os.getenv("AUTO_LOAD_ON_STARTUP"), True)
    default_forecast_horizon: int = int(os.getenv("DEFAULT_FORECAST_HORIZON", "14"))
    trend_surge_ratio_threshold: float = float(os.getenv("TREND_SURGE_RATIO_THRESHOLD", "1.35"))
    trend_moderate_ratio_threshold: float = float(os.getenv("TREND_MODERATE_RATIO_THRESHOLD", "1.10"))
    trend_surge_growth_threshold: float = float(os.getenv("TREND_SURGE_GROWTH_THRESHOLD", "0.20"))
    trend_moderate_growth_threshold: float = float(os.getenv("TREND_MODERATE_GROWTH_THRESHOLD", "0.05"))
    lstm_window: int = int(os.getenv("LSTM_WINDOW", "14"))
    lstm_epochs: int = int(os.getenv("LSTM_EPOCHS", "12"))
    lstm_batch_size: int = int(os.getenv("LSTM_BATCH_SIZE", "16"))
    xgb_estimators: int = int(os.getenv("XGB_ESTIMATORS", "240"))
    covid_daily_data_path: Path = _resolve_path(
        os.getenv("COVID_DAILY_DATA_PATH"),
        RAW_DATA_DIR / "WHO-COVID-19-global-daily-data.csv",
    )
    covid_weekly_data_path: Path = _resolve_path(
        os.getenv("COVID_WEEKLY_DATA_PATH"),
        RAW_DATA_DIR / "WHO-COVID-19-global-data.csv",
    )
    covid_hospital_data_path: Path = _resolve_path(
        os.getenv("COVID_HOSPITAL_DATA_PATH"),
        RAW_DATA_DIR / "WHO-COVID-19-global-hosp-icu-data.csv",
    )
    covid_vaccination_data_path: Path = _resolve_path(
        os.getenv("COVID_VACCINATION_DATA_PATH"),
        RAW_DATA_DIR / "COV_VAC_UPTAKE_2024.csv",
    )
    merged_cache_path: Path = (PROCESSED_DATA_DIR / "merged_timeseries.pkl").resolve()
    metadata_cache_path: Path = (CACHE_DIR / "dataset_metadata.json").resolve()
    admin_api_key: str = os.getenv("ADMIN_API_KEY", "")


settings = Settings()
