from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.insights import insight_service

logger = logging.getLogger(__name__)

class CountryNotFoundError(ValueError):
    pass


class DatasetNotReadyError(RuntimeError):
    pass


class DataLoaderService:
    def __init__(self) -> None:
        self._merged_df: pd.DataFrame | None = None
        self._loaded_at: datetime | None = None
        self._country_lookup: dict[str, str] = {}
        self._source_window: dict[str, str] = {}

    def load_data(self, force_reload: bool = False) -> dict[str, object]:
        if not force_reload and self._merged_df is not None:
            logger.info("Cache hit: merged_df is already loaded in memory.")
            return self._build_load_response()

        if not force_reload and self._cache_is_fresh():
            logger.info("Cache hit: Loading merged timeseries from cache file.")
            self._merged_df = pd.read_pickle(settings.merged_cache_path)
            self._loaded_at = datetime.now(timezone.utc)
            self._country_lookup = {
                country.upper(): country
                for country in sorted(self._merged_df["country"].dropna().unique().tolist())
            }
            self._source_window = self._compute_source_window()
            logger.info("Cache hit: Loaded merged timeseries successfully.")
            return self._build_load_response()

        logger.info("Starting raw dataset ingestion and harmonization...")
        try:
            cases = self._load_cases()
            hospitals = self._load_hospitalizations(cases)
            vaccinations = self._load_vaccinations(cases)

            merged = (
                cases.merge(
                    hospitals,
                    on=["country_code", "country", "date", "who_region"],
                    how="left",
                )
                .merge(vaccinations, on=["country_code", "country", "date"], how="left")
                .sort_values(["country", "date"])
                .reset_index(drop=True)
            )

            merged = self._ensure_time_series_continuity(merged)
            merged = self._engineer_features(merged)

            self._merged_df = merged
            self._loaded_at = datetime.now(timezone.utc)
            self._country_lookup = {
                country.upper(): country
                for country in sorted(merged["country"].dropna().unique().tolist())
            }
            self._source_window = self._compute_source_window()

            settings.merged_cache_path.parent.mkdir(parents=True, exist_ok=True)
            settings.metadata_cache_path.parent.mkdir(parents=True, exist_ok=True)
            merged.to_pickle(settings.merged_cache_path)
            logger.info("Raw datasets ingested and features engineered successfully.")
        except Exception as exc:
            logger.exception("Failed to load and merge datasets: %s", exc)
            raise

        return self._build_load_response()
        settings.metadata_cache_path.write_text(
            json.dumps(
                {
                    "loaded_at": self._loaded_at.isoformat(),
                    "rows_count": int(len(merged)),
                    "countries_count": int(merged["country"].nunique()),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        return self._build_load_response()

    def list_countries(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._country_lookup.values())

    def get_country_data(
        self,
        country: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        self._ensure_loaded()
        canonical_country = self._resolve_country(country)
        country_df = self._merged_df.loc[self._merged_df["country"] == canonical_country].copy()

        if start_date:
            country_df = country_df.loc[country_df["date"] >= pd.to_datetime(start_date)]
        if end_date:
            country_df = country_df.loc[country_df["date"] <= pd.to_datetime(end_date)]

        if country_df.empty:
            raise CountryNotFoundError(f"No records found for {country}.")

        return country_df.reset_index(drop=True)

    def get_global_summary(self) -> dict[str, object]:
        self._ensure_loaded()
        latest = self._latest_country_rows()
        seven_days_ago = self._latest_country_rows(offset_days=7)

        total_cases = float(latest["cumulative_cases"].sum())
        total_deaths = float(latest["cumulative_deaths"].sum())
        new_cases_last_7d = float(latest["new_cases_7d_sum"].sum())
        new_deaths_last_7d = float(latest["new_deaths_7d_sum"].sum())

        global_series = (
            self._merged_df.groupby("date", as_index=False)[["new_cases", "new_deaths"]]
            .sum()
            .tail(180)
            .copy()
        )
        global_series["cases_ma7"] = global_series["new_cases"].rolling(7, min_periods=1).mean()
        global_series[["new_cases", "new_deaths", "cases_ma7"]] = global_series[
            ["new_cases", "new_deaths", "cases_ma7"]
        ].round(2)
        global_series["date"] = global_series["date"].dt.strftime("%Y-%m-%d")

        ranked = latest.loc[
            (latest["cases_ma7"] >= 25) | (latest["Covid_new_hospitalizations_last_7days"].fillna(0) >= 5)
        ].copy()
        if ranked.empty:
            ranked = latest.copy()

        top_surge = ranked.sort_values(["trend_score", "cases_ma7"], ascending=False).head(8)
        top_surge_countries = [
            {
                "country": row.country,
                "trend_label": row.trend_label,
                "trend_score": round(float(row.trend_score), 2),
                "cases_ma7": round(float(row.cases_ma7), 2),
                "growth_rate": round(float(row.growth_rate), 4),
            }
            for row in top_surge.itertuples()
        ]

        return {
            "latest_date": latest["date"].max().strftime("%Y-%m-%d"),
            "total_cases": round(total_cases, 2),
            "total_deaths": round(total_deaths, 2),
            "new_cases_last_7d": round(new_cases_last_7d, 2),
            "new_deaths_last_7d": round(new_deaths_last_7d, 2),
            "countries_tracked": int(latest["country"].nunique()),
            "trend_counts": latest["trend_label"].value_counts().to_dict(),
            "top_surge_countries": top_surge_countries,
            "global_series": global_series.to_dict(orient="records"),
            "source_window": self._source_window,
            "comparison_window": {
                "previous_total_cases": round(float(seven_days_ago["cumulative_cases"].sum()), 2),
                "previous_total_deaths": round(float(seven_days_ago["cumulative_deaths"].sum()), 2),
            },
        }

    def latest_assessment(self, country: str) -> tuple[pd.DataFrame, dict[str, object]]:
        country_df = self.get_country_data(country)
        latest = country_df.iloc[-1]
        assessment = insight_service.classify_row(latest)
        return country_df, {
            "country": latest["country"],
            "classification": assessment.label,
            "score": round(assessment.score, 2),
            "narrative": assessment.narrative,
            "latest_date": latest["date"].strftime("%Y-%m-%d"),
            "drivers": assessment.drivers,
        }

    def _load_cases(self) -> pd.DataFrame:
        daily = self._load_case_source(settings.covid_daily_data_path, "daily")
        weekly = self._load_case_source(settings.covid_weekly_data_path, "weekly")

        if daily.empty and weekly.empty:
            raise FileNotFoundError("No WHO case dataset was found. Provide daily or weekly input files.")

        numeric_cols = ["new_cases", "cumulative_cases", "new_deaths", "cumulative_deaths"]
        if not daily.empty:
            daily[numeric_cols] = daily[numeric_cols].apply(pd.to_numeric, errors="coerce")
            daily["new_cases"] = daily["new_cases"].fillna(0.0).clip(lower=0.0)
            daily["new_deaths"] = daily["new_deaths"].fillna(0.0).clip(lower=0.0)

        if weekly.empty:
            return daily.reset_index(drop=True)

        weekly[numeric_cols] = weekly[numeric_cols].apply(pd.to_numeric, errors="coerce")
        weekly_tail = self._expand_weekly_to_daily(weekly, daily)

        cases = pd.concat([daily, weekly_tail], ignore_index=True)
        cases = cases.dropna(subset=["date", "country"])
        cases = cases.sort_values(["country_code", "date", "source_name"])
        cases = cases.drop_duplicates(subset=["country_code", "date"], keep="first")
        return cases.reset_index(drop=True)

    def _load_case_source(self, path, source_name: str) -> pd.DataFrame:
        case_columns = [
            "Date_reported",
            "Country_code",
            "Country",
            "WHO_region",
            "New_cases",
            "Cumulative_cases",
            "New_deaths",
            "Cumulative_deaths",
        ]
        if not path.exists():
            return pd.DataFrame(
                columns=[
                    "date",
                    "country_code",
                    "country",
                    "who_region",
                    "new_cases",
                    "cumulative_cases",
                    "new_deaths",
                    "cumulative_deaths",
                    "source_name",
                ]
            )

        frame = pd.read_csv(path, usecols=case_columns)
        frame = frame.rename(
            columns={
                "Date_reported": "date",
                "Country_code": "country_code",
                "Country": "country",
                "WHO_region": "who_region",
                "New_cases": "new_cases",
                "Cumulative_cases": "cumulative_cases",
                "New_deaths": "new_deaths",
                "Cumulative_deaths": "cumulative_deaths",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["country_code"] = frame["country_code"].astype(str).str.upper().str.strip()
        frame["country"] = frame["country"].astype(str).str.strip().str.title()
        frame["who_region"] = (
            frame["who_region"]
            .astype(str)
            .str.strip()
            .replace({"EMR": "EMRO", "nan": np.nan, "": np.nan})
        )
        frame["source_name"] = source_name
        return frame.dropna(subset=["date", "country"]).reset_index(drop=True)

    def _expand_weekly_to_daily(self, weekly: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
        expanded_rows: list[dict[str, object]] = []
        daily_last_dates = daily.groupby("country_code")["date"].max().to_dict() if not daily.empty else {}
        daily_last_cases = (
            daily.sort_values(["country_code", "date"]).groupby("country_code")["cumulative_cases"].last().to_dict()
            if not daily.empty
            else {}
        )
        daily_last_deaths = (
            daily.sort_values(["country_code", "date"]).groupby("country_code")["cumulative_deaths"].last().to_dict()
            if not daily.empty
            else {}
        )

        for country_code, group in weekly.groupby("country_code", sort=False):
            group = group.sort_values("date").reset_index(drop=True)
            last_daily_date = daily_last_dates.get(country_code)
            if last_daily_date is not None:
                group = group.loc[group["date"] > last_daily_date]

            previous_cases = self._safe_number(daily_last_cases.get(country_code))
            previous_deaths = self._safe_number(daily_last_deaths.get(country_code))
            previous_date = last_daily_date

            for row in group.itertuples(index=False):
                end_date = row.date
                start_date = end_date - pd.Timedelta(days=6)
                if previous_date is not None:
                    start_date = max(start_date, previous_date + pd.Timedelta(days=1))
                if start_date > end_date:
                    continue

                dates = pd.date_range(start_date, end_date, freq="D")
                periods = len(dates)
                total_new_cases = self._safe_number(row.new_cases)
                total_new_deaths = self._safe_number(row.new_deaths)
                cumulative_cases_end = self._safe_number(row.cumulative_cases, default=previous_cases + total_new_cases)
                cumulative_deaths_end = self._safe_number(row.cumulative_deaths, default=previous_deaths + total_new_deaths)

                if total_new_cases == 0 and cumulative_cases_end > previous_cases:
                    total_new_cases = cumulative_cases_end - previous_cases
                if total_new_deaths == 0 and cumulative_deaths_end > previous_deaths:
                    total_new_deaths = cumulative_deaths_end - previous_deaths

                daily_cases = total_new_cases / periods if periods else 0.0
                daily_deaths = total_new_deaths / periods if periods else 0.0
                case_points = (
                    np.linspace(previous_cases + daily_cases, cumulative_cases_end, periods)
                    if periods
                    else np.array([])
                )
                death_points = (
                    np.linspace(previous_deaths + daily_deaths, cumulative_deaths_end, periods)
                    if periods
                    else np.array([])
                )

                region = row.who_region if pd.notna(row.who_region) else np.nan
                for index, date in enumerate(dates):
                    expanded_rows.append(
                        {
                            "date": date,
                            "country_code": row.country_code,
                            "country": row.country,
                            "who_region": region,
                            "new_cases": round(daily_cases, 6),
                            "cumulative_cases": round(float(case_points[index]), 6),
                            "new_deaths": round(daily_deaths, 6),
                            "cumulative_deaths": round(float(death_points[index]), 6),
                            "source_name": "weekly_dailyized",
                        }
                    )

                previous_cases = cumulative_cases_end
                previous_deaths = cumulative_deaths_end
                previous_date = end_date

        return pd.DataFrame(expanded_rows)

    def _load_hospitalizations(self, case_reference: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "Date_reported",
            "Country_code",
            "Country",
            "WHO_region",
            "Covid_new_hospitalizations_last_7days",
            "Covid_new_icu_admissions_last_7days",
            "Covid_new_hospitalizations_last_28days",
            "Covid_new_icu_admissions_last_28days",
        ]
        if not settings.covid_hospital_data_path.exists():
            return pd.DataFrame(columns=["country_code", "country", "date", "who_region"])

        frame = pd.read_csv(settings.covid_hospital_data_path, usecols=columns)
        frame = frame.rename(
            columns={
                "Date_reported": "date",
                "Country_code": "country_code",
                "Country": "country",
                "WHO_region": "who_region",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["country_code"] = frame["country_code"].astype(str).str.upper().str.strip()
        code_to_country = (
            case_reference.drop_duplicates(subset=["country_code"])
            .set_index("country_code")["country"]
            .to_dict()
        )
        code_to_region = (
            case_reference.drop_duplicates(subset=["country_code"])
            .set_index("country_code")["who_region"]
            .to_dict()
        )
        frame["country"] = frame["country_code"].map(code_to_country).fillna(
            frame["country"].astype(str).str.strip().str.title()
        )
        frame["who_region"] = frame["country_code"].map(code_to_region).fillna(frame["who_region"])
        numeric_cols = [
            "Covid_new_hospitalizations_last_7days",
            "Covid_new_icu_admissions_last_7days",
            "Covid_new_hospitalizations_last_28days",
            "Covid_new_icu_admissions_last_28days",
        ]
        frame[numeric_cols] = frame[numeric_cols].apply(pd.to_numeric, errors="coerce")
        return frame.dropna(subset=["date", "country"]).reset_index(drop=True)

    def _load_vaccinations(self, case_reference: pd.DataFrame) -> pd.DataFrame:
        columns = [
            "COUNTRY",
            "DATE",
            "GROUP",
            "COVID_VACCINE_ADM_1D",
            "COVID_VACCINE_COV_1D",
            "POPULATION",
        ]
        if not settings.covid_vaccination_data_path.exists():
            return pd.DataFrame(columns=["country_code", "country", "date"])

        frame = pd.read_csv(settings.covid_vaccination_data_path, usecols=columns)
        frame = frame.rename(
            columns={
                "COUNTRY": "country_code",
                "DATE": "date",
                "GROUP": "group",
                "COVID_VACCINE_ADM_1D": "vaccination_administered",
                "COVID_VACCINE_COV_1D": "vaccination_coverage",
                "POPULATION": "vaccination_population",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["country_code"] = frame["country_code"].astype(str).str.upper().str.strip()
        frame["group"] = frame["group"].astype(str).str.lower().str.strip()

        code_to_country = (
            case_reference.drop_duplicates(subset=["country_code"])
            .set_index("country_code")["country"]
            .to_dict()
        )
        frame["country"] = frame["country_code"].map(code_to_country)

        preferred = frame.loc[frame["group"] == "all"].copy()
        preferred = preferred.groupby(["country_code", "country", "date"], as_index=False).agg(
            vaccination_administered_all=("vaccination_administered", "max"),
            vaccination_coverage_all=("vaccination_coverage", "max"),
            vaccination_population=("vaccination_population", "max"),
        )

        fallback = frame.groupby(["country_code", "country", "date"], as_index=False).agg(
            vaccination_administered_avg=("vaccination_administered", "mean"),
            vaccination_coverage_avg=("vaccination_coverage", "mean"),
            vaccination_groups_reported=("group", "nunique"),
        )

        merged = fallback.merge(
            preferred,
            on=["country_code", "country", "date"],
            how="left",
        )
        merged["vaccination_coverage_all"] = merged["vaccination_coverage_all"].fillna(
            merged["vaccination_coverage_avg"]
        )
        merged["vaccination_administered_all"] = merged["vaccination_administered_all"].fillna(
            merged["vaccination_administered_avg"]
        )
        return merged.dropna(subset=["date", "country"]).reset_index(drop=True)

    def _ensure_time_series_continuity(self, merged: pd.DataFrame) -> pd.DataFrame:
        groups: list[pd.DataFrame] = []
        interpolation_cols = [
            "Covid_new_hospitalizations_last_7days",
            "Covid_new_icu_admissions_last_7days",
            "Covid_new_hospitalizations_last_28days",
            "Covid_new_icu_admissions_last_28days",
            "vaccination_administered_all",
            "vaccination_coverage_all",
            "vaccination_population",
        ]

        for _, group in merged.groupby("country", sort=False):
            group = group.sort_values("date").reset_index(drop=True)
            if group["date"].duplicated().any():
                aggregations = {
                    "country_code": "last",
                    "country": "last",
                    "who_region": "last",
                    "new_cases": "max",
                    "cumulative_cases": "last",
                    "new_deaths": "max",
                    "cumulative_deaths": "last",
                }
                for column in interpolation_cols:
                    if column in group.columns:
                        aggregations[column] = "mean"
                if "vaccination_groups_reported" in group.columns:
                    aggregations["vaccination_groups_reported"] = "max"
                group = group.groupby("date", as_index=False).agg(aggregations)

            full_dates = pd.date_range(group["date"].min(), group["date"].max(), freq="D")
            expanded = group.set_index("date").reindex(full_dates)
            expanded.index.name = "date"
            expanded["country"] = group["country"].iloc[0]
            expanded["country_code"] = group["country_code"].iloc[0]

            region_series = group["who_region"].dropna()
            expanded["who_region"] = region_series.iloc[-1] if not region_series.empty else "Other"
            expanded["new_cases"] = pd.to_numeric(expanded["new_cases"], errors="coerce").fillna(0.0).clip(lower=0.0)
            expanded["new_deaths"] = pd.to_numeric(expanded["new_deaths"], errors="coerce").fillna(0.0).clip(lower=0.0)
            expanded["cumulative_cases"] = expanded["new_cases"].cumsum()
            expanded["cumulative_deaths"] = expanded["new_deaths"].cumsum()

            for column in interpolation_cols:
                if column in expanded:
                    expanded[column] = pd.to_numeric(expanded[column], errors="coerce").interpolate(
                        limit_direction="both"
                    )

            groups.append(expanded.reset_index())

        return pd.concat(groups, ignore_index=True).rename(columns={"index": "date"})

    def _engineer_features(self, merged: pd.DataFrame) -> pd.DataFrame:
        engineered_groups: list[pd.DataFrame] = []

        for _, group in merged.groupby("country", sort=False):
            group = group.sort_values("date").reset_index(drop=True)
            group["cases_ma7"] = group["new_cases"].rolling(7, min_periods=1).mean()
            group["deaths_ma7"] = group["new_deaths"].rolling(7, min_periods=1).mean()
            group["growth_rate"] = (
                group["cases_ma7"].pct_change(periods=7).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            )
            group["rolling_trend_14"] = group["cases_ma7"].diff(14).fillna(0.0)
            baseline = group["cases_ma7"].rolling(28, min_periods=7).mean().replace(0, np.nan)
            group["surge_ratio"] = (group["cases_ma7"] / baseline).replace([np.inf, -np.inf], np.nan).fillna(1.0)
            group["new_cases_7d_sum"] = group["new_cases"].rolling(7, min_periods=1).sum()
            group["new_deaths_7d_sum"] = group["new_deaths"].rolling(7, min_periods=1).sum()

            assessments = group.apply(insight_service.classify_row, axis=1)
            group["trend_label"] = [assessment.label for assessment in assessments]
            group["trend_score"] = [assessment.score for assessment in assessments]
            engineered_groups.append(group)

        merged = pd.concat(engineered_groups, ignore_index=True)
        merged["date"] = pd.to_datetime(merged["date"])
        return merged

    def _latest_country_rows(self, offset_days: int = 0) -> pd.DataFrame:
        self._ensure_loaded()
        latest_rows = []
        for _, group in self._merged_df.groupby("country", sort=False):
            group = group.sort_values("date")
            latest_index = max(len(group) - 1 - offset_days, 0)
            latest_rows.append(group.iloc[latest_index])
        return pd.DataFrame(latest_rows)

    def _cache_is_fresh(self) -> bool:
        if not settings.merged_cache_path.exists():
            return False

        cache_mtime = settings.merged_cache_path.stat().st_mtime
        sources = [
            settings.covid_daily_data_path,
            settings.covid_weekly_data_path,
            settings.covid_hospital_data_path,
            settings.covid_vaccination_data_path,
        ]
        return all((not source.exists()) or source.stat().st_mtime <= cache_mtime for source in sources)

    def _build_load_response(self) -> dict[str, object]:
        self._ensure_loaded()
        return {
            "status": "success",
            "loaded_at": self._loaded_at or datetime.now(timezone.utc),
            "countries_count": int(self._merged_df["country"].nunique()),
            "rows_count": int(len(self._merged_df)),
            "sources": {
                "daily_cases": str(settings.covid_daily_data_path),
                "weekly_cases": str(settings.covid_weekly_data_path),
                "hospital_icu": str(settings.covid_hospital_data_path),
                "vaccination": str(settings.covid_vaccination_data_path),
            },
        }

    def _resolve_country(self, country: str) -> str:
        normalized = country.strip().upper()
        if normalized in self._country_lookup:
            return self._country_lookup[normalized]

        partial_match = next(
            (value for key, value in self._country_lookup.items() if normalized in key),
            None,
        )
        if partial_match:
            return partial_match

        raise CountryNotFoundError(f"Country `{country}` was not found in the processed dataset.")

    def _ensure_loaded(self) -> None:
        if self._merged_df is None:
            self.load_data(force_reload=False)
        if self._merged_df is None:
            raise DatasetNotReadyError("Dataset is not loaded yet.")

    @staticmethod
    def _safe_number(value: object, default: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        if pd.isna(numeric):
            return default
        return max(numeric, 0.0)

    def _compute_source_window(self) -> dict[str, str]:
        def read_bound(path, bound: str) -> str:
            if not path.exists():
                return ""
            frame = pd.read_csv(path, usecols=["Date_reported"])
            series = pd.to_datetime(frame["Date_reported"], errors="coerce")
            value = series.min() if bound == "min" else series.max()
            return value.strftime("%Y-%m-%d") if pd.notna(value) else ""

        analysis_start = (
            self._merged_df["date"].min().strftime("%Y-%m-%d")
            if self._merged_df is not None and not self._merged_df.empty
            else ""
        )
        analysis_end = (
            self._merged_df["date"].max().strftime("%Y-%m-%d")
            if self._merged_df is not None and not self._merged_df.empty
            else ""
        )

        return {
            "analysis_start": analysis_start,
            "analysis_end": analysis_end,
            "daily_feed_start": read_bound(settings.covid_daily_data_path, "min"),
            "daily_feed_end": read_bound(settings.covid_daily_data_path, "max"),
            "weekly_feed_end": read_bound(settings.covid_weekly_data_path, "max"),
            "hospital_feed_end": read_bound(settings.covid_hospital_data_path, "max"),
            "analysis_mode": "daily WHO series with dailyized weekly continuation",
        }


data_loader_service = DataLoaderService()
