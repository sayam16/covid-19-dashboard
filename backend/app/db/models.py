from __future__ import annotations

from datetime import datetime, timezone, timedelta

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DataLoadRun(Base):
    __tablename__ = "data_load_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="success", nullable=False)
    countries_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ForecastCache(Base):
    __tablename__ = "forecast_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    country: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    @classmethod
    def make(cls, country, horizon, payload, ttl_hours=6):
        now = datetime.now(timezone.utc)
        return cls(
            country=country,
            horizon=horizon,
            payload=payload,
            generated_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
