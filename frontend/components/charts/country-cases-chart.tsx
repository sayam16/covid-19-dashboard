"use client";

import {
  Area,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import { CountryPoint, ForecastPoint } from "@/lib/api";
import { formatNumber } from "@/lib/format";

export function CountryCasesChart({
  history,
  forecast
}: {
  history: CountryPoint[];
  forecast: ForecastPoint[];
}) {
  const trimmedHistory = history.slice(-120).map((point) => ({
    ...point,
    forecast_cases: null,
    surge_overlay: point.trend_label === "Surge" ? point.new_cases : null
  }));

  const forecastData = forecast.map((point) => ({
    date: point.date,
    new_cases: null,
    cases_ma7: null,
    forecast_cases: point.predicted_cases,
    surge_overlay: null
  }));

  const merged = [...trimmedHistory, ...forecastData];

  return (
    <div className="h-96 w-full">
      <ResponsiveContainer>
        <ComposedChart data={merged}>
          <XAxis dataKey="date" minTickGap={28} tick={{ fill: "#64748b", fontSize: 12 }} />
          <YAxis tickFormatter={(value) => formatNumber(value)} tick={{ fill: "#64748b", fontSize: 12 }} />
          <Tooltip formatter={(value: number) => (value === null ? "N/A" : formatNumber(Number(value), false))} />
          <Legend />
          <Area
            type="monotone"
            dataKey="surge_overlay"
            fill="#fecdd3"
            stroke="none"
            name="Surge periods"
            connectNulls={false}
          />
          <Line type="monotone" dataKey="new_cases" stroke="#c2410c" dot={false} strokeWidth={2} name="Daily cases" />
          <Line type="monotone" dataKey="cases_ma7" stroke="#0f766e" dot={false} strokeWidth={2} name="7-day average" />
          <Line
            type="monotone"
            dataKey="forecast_cases"
            stroke="#1d4ed8"
            strokeDasharray="6 6"
            dot={false}
            strokeWidth={2}
            name="Forecast"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
