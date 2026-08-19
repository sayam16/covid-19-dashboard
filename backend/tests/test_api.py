from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.data_loader import CountryNotFoundError, data_loader_service


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_country_returns_404(monkeypatch) -> None:
    def raise_missing(*args, **kwargs):
        raise CountryNotFoundError("Country `Atlantis` was not found in the processed dataset.")

    monkeypatch.setattr(data_loader_service, "get_country_data", raise_missing)
    response = client.get("/api/get-country-data", params={"country": "Atlantis"})
    assert response.status_code == 404
    assert "Atlantis" in response.json()["detail"]


def test_global_summary_contract(monkeypatch) -> None:
    payload = {
        "latest_date": "2026-02-22",
        "total_cases": 100.0,
        "total_deaths": 10.0,
        "new_cases_last_7d": 5.0,
        "new_deaths_last_7d": 1.0,
        "countries_tracked": 2,
        "trend_counts": {"Normal": 1, "Surge": 1},
        "top_surge_countries": [],
        "global_series": [],
        "source_window": {
            "analysis_start": "2020-01-04",
            "analysis_end": "2026-02-22",
            "daily_feed_start": "2020-01-04",
            "daily_feed_end": "2026-02-22",
            "weekly_feed_end": "2026-04-05",
            "hospital_feed_end": "2026-02-01",
            "analysis_mode": "daily WHO series with dailyized weekly continuation",
        },
        "comparison_window": {"previous_total_cases": 95.0, "previous_total_deaths": 9.0},
    }
    monkeypatch.setattr(data_loader_service, "get_global_summary", lambda: payload)
    response = client.get("/api/global-summary")
    assert response.status_code == 200
    assert response.json()["countries_tracked"] == 2
