from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import logging

import pandas as pd

logger = logging.getLogger(__name__)

from app.core.config import settings


@dataclass(slots=True)
class TrendAssessment:
    label: str
    score: float
    narrative: str
    drivers: dict[str, float | str | None]


class InsightService:
    def classify_row(self, row: pd.Series) -> TrendAssessment:
        surge_ratio = self._safe_float(row.get("surge_ratio", 0.0))
        growth_rate = self._safe_float(row.get("growth_rate", 0.0))
        hospitalizations = self._safe_float(row.get("Covid_new_hospitalizations_last_7days", 0.0))
        vaccination = self._safe_float(row.get("vaccination_coverage_all", 0.0))
        cases_ma7 = self._safe_float(row.get("cases_ma7", 0.0))
        deaths_ma7 = self._safe_float(row.get("deaths_ma7", 0.0))

        score = (
            (surge_ratio - 1.0) * 45
            + growth_rate * 35
            + np.log1p(max(hospitalizations, 0.0)) * 3
            + np.log1p(max(cases_ma7, 0.0)) * 2
            - vaccination * 0.15
        )
        score = float(np.clip(score, 0.0, 100.0))

        if cases_ma7 < 10 and hospitalizations < 5 and deaths_ma7 < 2:
            label = "Normal"
            score = min(score, 15.0)
        elif (
            cases_ma7 >= 250
            and (
                surge_ratio >= settings.trend_surge_ratio_threshold
                or growth_rate >= settings.trend_surge_growth_threshold
                or hospitalizations >= 50
                or score >= 65
            )
        ):
            label = "Surge"
        elif (
            cases_ma7 >= 50
            and (
                surge_ratio >= settings.trend_moderate_ratio_threshold
                or growth_rate >= settings.trend_moderate_growth_threshold
                or hospitalizations >= 10
                or score >= 35
            )
        ):
            label = "Moderate"
        else:
            label = "Normal"

        narrative = self._build_narrative(label, cases_ma7, growth_rate, surge_ratio, vaccination)
        return TrendAssessment(
            label=label,
            score=score,
            narrative=narrative,
            drivers={
                "cases_ma7": round(cases_ma7, 2),
                "growth_rate": round(growth_rate, 4),
                "surge_ratio": round(surge_ratio, 4),
                "vaccination_coverage_all": round(vaccination, 2) if vaccination else None,
                "hospitalizations_7d": round(hospitalizations, 2) if hospitalizations else None,
                "deaths_ma7": round(deaths_ma7, 2),
            },
        )

    def summarize_country(self, country_df: pd.DataFrame) -> list[str]:
        latest = country_df.iloc[-1]
        prior = country_df.iloc[-8] if len(country_df) > 8 else country_df.iloc[0]
        growth_delta = float(latest["growth_rate"] - prior.get("growth_rate", 0.0))
        cases_ma7 = float(latest["cases_ma7"])
        vaccinations = latest.get("vaccination_coverage_all")

        bullets = [
            f"7-day average cases are at {cases_ma7:,.0f}, with a {float(latest['growth_rate']) * 100:.1f}% week-over-week change.",
            f"Current trend is {latest['trend_label']}, driven by a surge ratio of {float(latest['surge_ratio']):.2f}.",
        ]

        if growth_delta > 0.05:
            bullets.append("Momentum is accelerating relative to the previous week, suggesting rising transmission pressure.")
        elif growth_delta < -0.05:
            bullets.append("Momentum has eased compared with the previous week, which suggests the curve is stabilizing.")

        if pd.notna(vaccinations):
            bullets.append(f"Vaccination coverage for the `all` group is {float(vaccinations):.1f}% in the latest merged record.")

        return bullets

    def forecast_narrative(self, country: str, forecast_values: list[float], latest_actual: float) -> str:
        if not forecast_values:
            return f"No forecast is currently available for {country}."

        end_value = forecast_values[-1]
        delta = end_value - latest_actual
        pct = (delta / latest_actual * 100) if latest_actual > 0 else 0.0

        if pct >= 15:
            tone = "Cases are projected to increase rapidly"
        elif pct >= 5:
            tone = "Cases are projected to continue rising"
        elif pct <= -15:
            tone = "Cases are projected to fall sharply"
        elif pct <= -5:
            tone = "Cases are projected to trend downward"
        else:
            tone = "Cases are projected to remain relatively stable"

        return f"{tone} in {country} over the next {len(forecast_values)} days, ending near {end_value:,.0f} daily cases."

    @staticmethod
    def _build_narrative(
        label: str,
        cases_ma7: float,
        growth_rate: float,
        surge_ratio: float,
        vaccination: float,
    ) -> str:
        vaccination_text = (
            f" Vaccination coverage is {vaccination:.1f}% for the `all` group."
            if vaccination
            else ""
        )
        return (
            f"The current signal is {label.lower()} with a 7-day average of {cases_ma7:,.0f}, "
            f"week-over-week growth of {growth_rate * 100:.1f}%, and a surge ratio of {surge_ratio:.2f}."
            f"{vaccination_text}"
        )

    @staticmethod
    def _safe_float(value: object) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return 0.0 if pd.isna(numeric) else numeric


insight_service = InsightService()
