"use client";

import { useEffect, useState } from "react";

import { FeatureImportanceChart } from "@/components/charts/feature-importance-chart";
import { InsightBox } from "@/components/ui/insight-box";
import { Panel } from "@/components/ui/panel";
import { TrendPill } from "@/components/ui/trend-pill";
import {
  ForecastResponse,
  TrendResponse,
  fetchForecast,
  fetchTrend
} from "@/lib/api";
import { titleCase } from "@/lib/format";
import { useCountrySelector } from "@/hooks/useCountrySelector";

export default function InsightsPage() {
  const { countries, selectedCountry, setSelectedCountry } = useCountrySelector("India");
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedCountry) return;
    Promise.all([fetchTrend(selectedCountry), fetchForecast(selectedCountry)])
      .then(([trendPayload, forecastPayload]) => {
        setTrend(trendPayload);
        setForecast(forecastPayload);
        setError(null);
      })
      .catch((err) => setError(err.message));
  }, [selectedCountry]);

  return (
    <div className="space-y-6 pb-10">
      <Panel title="AI insights panel" description="Explain the latest classification and inspect which engineered signals matter most to the trend forecast.">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="inline-flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <select
              className="bg-transparent text-lg font-medium text-ink outline-none"
              value={selectedCountry}
              onChange={(event) => setSelectedCountry(event.target.value)}
            >
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>
          {trend ? <TrendPill trend={trend.classification} /> : null}
        </div>
      </Panel>

      {error ? <Panel title="Unable to load insights" description={error} /> : null}

      {trend && forecast ? (
        <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
          <div className="space-y-6">
            <InsightBox body={forecast.narrative} />
            <Panel title="Driver breakdown" description="Live trend inputs returned by the backend classification service.">
              <div className="space-y-3">
                {Object.entries(trend.drivers).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-500">{titleCase(key)}</span>
                    <span className="font-medium text-ink">{value ?? "N/A"}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <Panel title="XGBoost feature importance" description="Top engineered features influencing the trend-component regressor.">
            {forecast.feature_importance.length ? (
              <FeatureImportanceChart data={forecast.feature_importance} />
            ) : (
              <p className="text-sm leading-7 text-slate-600">
                Feature importance is only shown when the recent case series has enough activity to justify hybrid model training. For low-activity periods, the backend serves a fast stability forecast instead.
              </p>
            )}
          </Panel>
        </div>
      ) : (
        !error && <Panel title="Loading AI insights" description="Collecting classification drivers and feature importance from the backend." />
      )}
    </div>
  );
}
