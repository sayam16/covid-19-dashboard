from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler

from app.core.config import settings
from app.services.data_loader import data_loader_service
from app.services.insights import insight_service

try:
    from statsmodels.tsa.seasonal import STL
    from tensorflow.keras import Sequential
    from tensorflow.keras.layers import Dense, Input, LSTM
    from xgboost import XGBRegressor
except ImportError as exc:  # pragma: no cover - exercised only when deps are missing
    STL = None
    Sequential = None
    Dense = None
    Input = None
    LSTM = None
    XGBRegressor = None
    MODEL_IMPORT_ERROR = exc
else:
    MODEL_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ForecastArtifacts:
    trend_forecast: np.ndarray
    residual_forecast: np.ndarray
    seasonal_forecast: np.ndarray
    feature_importance: list[dict[str, float | str]]
    metrics: dict[str, float]


class ForecastService:
    MODEL_VERSION = "2026-04-23-v3"
    WEIGHTS = {"trend": 0.4, "residual": 0.4, "seasonal": 0.2}

    def predict(self, country: str, horizon: int = 14) -> dict[str, object]:
        if MODEL_IMPORT_ERROR is not None:
            raise RuntimeError(
                "Forecast dependencies are not installed. Install backend requirements before using /predict."
            ) from MODEL_IMPORT_ERROR

        horizon = max(7, min(14, horizon))
        country_df = data_loader_service.get_country_data(country)
        series = country_df["cases_ma7"].astype(float).fillna(0.0)
        recent_mean = float(country_df["cases_ma7"].tail(28).mean() or 0.0)
        latest_actual = float(country_df["new_cases"].iloc[-1])

        if recent_mean < 5 and float(country_df["new_cases"].tail(28).max() or 0.0) < 10:
            dates = pd.date_range(country_df["date"].iloc[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
            forecast_points = [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "predicted_cases": 0.0,
                    "trend_component": 0.0,
                    "residual_component": 0.0,
                    "seasonal_component": 0.0,
                    "lower_bound": 0.0,
                    "upper_bound": 1.0,
                }
                for date in dates
            ]
            return {
                "country": country_df["country"].iloc[-1],
                "horizon": horizon,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "history_end_date": country_df["date"].iloc[-1].strftime("%Y-%m-%d"),
                "model_version": self.MODEL_VERSION,
                "forecast": forecast_points,
                "weights": self.WEIGHTS,
                "model_metrics": {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "smape": 0.0},
                "feature_importance": [],
                "narrative": insight_service.forecast_narrative(
                    country_df["country"].iloc[-1],
                    [0.0] * horizon,
                    latest_actual,
                ),
            }

        if len(series) < 60:
            raise ValueError("At least 60 days of data are required to generate a hybrid forecast.")

        start_time = time.time()
        try:
            trend, seasonal, residual = self._stl_decompose(series)
            artifacts = self._train_components(country_df, trend, seasonal, residual, horizon)
        except Exception as exc:
            logger.exception("Forecast generation failed for %s: %s", country, exc)
            raise RuntimeError(f"Forecast generation failed: {exc}") from exc

        generation_time = time.time() - start_time
        logger.info("Generated forecast for %s in %.2f seconds", country, generation_time)

        final_forecast = (
            self.WEIGHTS["trend"] * artifacts.trend_forecast
            + self.WEIGHTS["residual"] * artifacts.residual_forecast
            + self.WEIGHTS["seasonal"] * artifacts.seasonal_forecast
        )
        final_forecast = np.clip(final_forecast, a_min=0.0, a_max=None)
        if recent_mean < 5 and latest_actual < 5:
            final_forecast = np.zeros_like(final_forecast)
        if recent_mean < 200:
            cap = max(recent_mean * 1.5, 25.0)
            final_forecast = np.clip(final_forecast, a_min=0.0, a_max=cap)

        historical_error = float(country_df["new_cases"].tail(28).std() or 1.0)
        dates = pd.date_range(country_df["date"].iloc[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")

        forecast_points = []
        for idx, date in enumerate(dates):
            predicted = float(final_forecast[idx])
            margin = max(predicted * 0.18, historical_error * 0.85)
            forecast_points.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "predicted_cases": round(predicted, 2),
                    "trend_component": round(float(artifacts.trend_forecast[idx]), 2),
                    "residual_component": round(float(artifacts.residual_forecast[idx]), 2),
                    "seasonal_component": round(float(artifacts.seasonal_forecast[idx]), 2),
                    "lower_bound": round(max(predicted - margin, 0.0), 2),
                    "upper_bound": round(predicted + margin, 2),
                }
            )

        narrative = insight_service.forecast_narrative(
            country_df["country"].iloc[-1],
            [point["predicted_cases"] for point in forecast_points],
            latest_actual,
        )

        return {
            "country": country_df["country"].iloc[-1],
            "horizon": horizon,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "history_end_date": country_df["date"].iloc[-1].strftime("%Y-%m-%d"),
            "model_version": self.MODEL_VERSION,
            "forecast": forecast_points,
            "weights": self.WEIGHTS,
            "model_metrics": artifacts.metrics,
            "feature_importance": artifacts.feature_importance,
            "narrative": narrative,
        }

    def _stl_decompose(self, series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
        stl = STL(series, period=7, robust=True)
        result = stl.fit()
        trend = result.trend.bfill().ffill()
        seasonal = result.seasonal.fillna(0.0)
        residual = result.resid.fillna(0.0)
        return trend, seasonal, residual

    def _train_components(
        self,
        country_df: pd.DataFrame,
        trend: pd.Series,
        seasonal: pd.Series,
        residual: pd.Series,
        horizon: int,
    ) -> ForecastArtifacts:
        trend_frame = self._build_trend_features(country_df, trend)
        feature_columns = [column for column in trend_frame.columns if column not in {"date", "target"}]

        test_size = min(max(horizon, 7), max(7, len(trend_frame) // 5))
        train_frame = trend_frame.iloc[:-test_size]
        test_frame = trend_frame.iloc[-test_size:]

        xgb_model = XGBRegressor(
            n_estimators=settings.xgb_estimators,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=42,
        )
        xgb_model.fit(train_frame[feature_columns], train_frame["target"])
        trend_test_pred = xgb_model.predict(test_frame[feature_columns])
        trend_forecast = self._recursive_xgb_forecast(
            xgb_model=xgb_model,
            history_frame=trend_frame.copy(),
            feature_columns=feature_columns,
            horizon=horizon,
        )

        residual_predictions, residual_test_pred = self._train_lstm(
            residual=residual,
            horizon=horizon,
            test_size=test_size,
        )
        residual_cap = max(float(np.nanpercentile(np.abs(residual.to_numpy(dtype=float)), 90)), 1.0)
        residual_predictions = np.clip(residual_predictions, -residual_cap, residual_cap)
        residual_test_pred = np.clip(residual_test_pred, -residual_cap, residual_cap)
        seasonal_forecast = self._seasonal_projection(seasonal, horizon)
        seasonal_test = self._seasonal_projection(seasonal.iloc[:-test_size], test_size)

        actual = country_df["cases_ma7"].iloc[-test_size:].to_numpy(dtype=float)
        hybrid_test_pred = (
            self.WEIGHTS["trend"] * trend_test_pred
            + self.WEIGHTS["residual"] * residual_test_pred
            + self.WEIGHTS["seasonal"] * seasonal_test
        )

        metrics = {
            "mae": round(float(mean_absolute_error(actual, hybrid_test_pred)), 3),
            "rmse": round(float(np.sqrt(mean_squared_error(actual, hybrid_test_pred))), 3),
            "mape": round(
                float(np.mean(np.abs((actual - hybrid_test_pred) / np.clip(actual, a_min=10.0, a_max=None))) * 100),
                3,
            ),
            "smape": round(
                float(
                    np.mean(
                        200
                        * np.abs(actual - hybrid_test_pred)
                        / np.clip(np.abs(actual) + np.abs(hybrid_test_pred), a_min=1.0, a_max=None)
                    )
                ),
                3,
            ),
        }
        feature_importance = sorted(
            (
                {"feature": feature, "importance": round(float(score), 4)}
                for feature, score in zip(feature_columns, xgb_model.feature_importances_)
            ),
            key=lambda item: item["importance"],
            reverse=True,
        )[:10]

        return ForecastArtifacts(
            trend_forecast=trend_forecast,
            residual_forecast=residual_predictions,
            seasonal_forecast=seasonal_forecast,
            feature_importance=feature_importance,
            metrics=metrics,
        )

    def _build_trend_features(self, country_df: pd.DataFrame, trend: pd.Series) -> pd.DataFrame:
        frame = pd.DataFrame(
            {
                "date": country_df["date"].to_numpy(),
                "target": trend.to_numpy(dtype=float),
                "new_cases": country_df["new_cases"].to_numpy(dtype=float),
                "cases_ma7": country_df["cases_ma7"].to_numpy(dtype=float),
                "growth_rate": country_df["growth_rate"].to_numpy(dtype=float),
                "surge_ratio": country_df["surge_ratio"].to_numpy(dtype=float),
            }
        )
        frame["lag_1"] = frame["target"].shift(1)
        frame["lag_7"] = frame["target"].shift(7)
        frame["lag_14"] = frame["target"].shift(14)
        frame["rolling_mean_7"] = frame["target"].rolling(7).mean()
        frame["rolling_std_7"] = frame["target"].rolling(7).std()
        frame["rolling_mean_14"] = frame["target"].rolling(14).mean()
        frame["day_of_week"] = pd.to_datetime(frame["date"]).dt.dayofweek
        frame["day_of_month"] = pd.to_datetime(frame["date"]).dt.day
        frame["month"] = pd.to_datetime(frame["date"]).dt.month
        frame = frame.dropna().reset_index(drop=True)
        return frame

    def _recursive_xgb_forecast(
        self,
        xgb_model: XGBRegressor,
        history_frame: pd.DataFrame,
        feature_columns: list[str],
        horizon: int,
    ) -> np.ndarray:
        history = history_frame.copy().reset_index(drop=True)
        predictions: list[float] = []

        for _ in range(horizon):
            next_date = pd.to_datetime(history["date"].iloc[-1]) + pd.Timedelta(days=1)
            target_history = history["target"].tolist()
            
            recent_cases = history["new_cases"].tail(7).tolist()
            
            row = {
                "date": next_date,
                "new_cases": float(history["new_cases"].iloc[-1]),
                "cases_ma7": float(np.mean(recent_cases + predictions[-7:])) if predictions else float(np.mean(recent_cases)),
                "growth_rate": float(history["growth_rate"].iloc[-1]),
                "surge_ratio": float(history["surge_ratio"].iloc[-1]),
                "lag_1": target_history[-1],
                "lag_7": target_history[-7] if len(target_history) >= 7 else target_history[-1],
                "lag_14": target_history[-14] if len(target_history) >= 14 else target_history[-1],
                "rolling_mean_7": float(np.mean(target_history[-7:])),
                "rolling_std_7": float(np.std(target_history[-7:])),
                "rolling_mean_14": float(np.mean(target_history[-14:])),
                "day_of_week": next_date.dayofweek,
                "day_of_month": next_date.day,
                "month": next_date.month,
            }
            feature_row = pd.DataFrame([row])[feature_columns]
            predicted_value = float(xgb_model.predict(feature_row)[0])
            predictions.append(predicted_value)

            appended = row | {"target": predicted_value}
            history = pd.concat([history, pd.DataFrame([appended])], ignore_index=True)

        return np.array(predictions, dtype=float)

    def _train_lstm(self, residual: pd.Series, horizon: int, test_size: int) -> tuple[np.ndarray, np.ndarray]:
        scaler = MinMaxScaler(feature_range=(-1, 1))
        scaled = scaler.fit_transform(residual.to_numpy(dtype=float).reshape(-1, 1))
        window = min(settings.lstm_window, max(7, len(residual) // 6))

        x_all, y_all = self._create_sequences(scaled, window)
        split_index = max(len(x_all) - test_size, 1)
        x_train, y_train = x_all[:split_index], y_all[:split_index]
        x_test = x_all[split_index:]

        model = Sequential(
            [
                Input(shape=(window, 1)),
                LSTM(48, return_sequences=True),
                LSTM(24),
                Dense(12, activation="relu"),
                Dense(1),
            ]
        )
        model.compile(optimizer="adam", loss="mse")
        model.fit(
            x_train,
            y_train,
            epochs=settings.lstm_epochs,
            batch_size=settings.lstm_batch_size,
            verbose=0,
        )

        test_pred_scaled = model.predict(x_test, verbose=0) if len(x_test) else np.array([[0.0]])
        test_pred = scaler.inverse_transform(test_pred_scaled).flatten()

        seed = scaled[-window:].flatten().tolist()
        future_preds_scaled: list[float] = []
        for _ in range(horizon):
            window_input = np.array(seed[-window:], dtype=float).reshape(1, window, 1)
            next_scaled = float(model.predict(window_input, verbose=0)[0][0])
            future_preds_scaled.append(next_scaled)
            seed.append(next_scaled)

        future_pred = scaler.inverse_transform(np.array(future_preds_scaled).reshape(-1, 1)).flatten()
        return future_pred, test_pred[-test_size:]

    @staticmethod
    def _create_sequences(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
        x, y = [], []
        for idx in range(window, len(values)):
            x.append(values[idx - window : idx])
            y.append(values[idx])
        return np.array(x), np.array(y)

    @staticmethod
    def _seasonal_projection(seasonal: pd.Series, horizon: int) -> np.ndarray:
        season = seasonal.tail(7).to_numpy(dtype=float)
        return np.resize(season, horizon)


forecast_service = ForecastService()
