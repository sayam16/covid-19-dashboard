"use client";

import { useEffect, useState } from "react";
import { Activity, HeartPulse, TrendingUp } from "lucide-react";

import { CountryCasesChart } from "@/components/charts/country-cases-chart";
import { GrowthRateChart } from "@/components/charts/growth-rate-chart";
import { InsightBox } from "@/components/ui/insight-box";
import { Panel } from "@/components/ui/panel";
import { StatCard } from "@/components/ui/stat-card";
import { TrendPill } from "@/components/ui/trend-pill";
import {
  CountryResponse,
  ForecastResponse,
  TrendResponse,
  fetchCountryData,
  fetchForecast,
  fetchTrend
} from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/format";
import { useCountrySelector } from "@/hooks/useCountrySelector";

export default function CountryPage() {
  const { countries, selectedCountry, setSelectedCountry } = useCountrySelector("India");
  const [countryData, setCountryData] = useState<CountryResponse | null>(null);
  const [countryDataLoading, setCountryDataLoading] = useState(true);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [forecastLoading, setForecastLoading] = useState(true);
  const [trendLoading, setTrendLoading] = useState(true);

  useEffect(() => {
    if (!selectedCountry) return;
    setCountryDataLoading(true);
    fetchCountryData(selectedCountry)
      .then(setCountryData)
      .catch((err) => setError(err.message))
      .finally(() => setCountryDataLoading(false));
  }, [selectedCountry]);

  useEffect(() => {
    if (!selectedCountry) return;
    setTrendLoading(true);
    fetchTrend(selectedCountry)
      .then(setTrend)
      .catch((err) => setError(err.message))
      .finally(() => setTrendLoading(false));
  }, [selectedCountry]);

  useEffect(() => {
    if (!selectedCountry) return;
    setForecastLoading(true);
    fetchForecast(selectedCountry)
      .then(setForecast)
      .catch((err) => setError(err.message))
      .finally(() => setForecastLoading(false));
  }, [selectedCountry]);

  const latest = countryData?.data[countryData.data.length - 1];

  return (
    <div className="space-y-6 pb-10">
      <Panel title="Country analysis" description="Explore smoothed case trends, growth momentum, and short-horizon forecasts for any tracked country.">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-500">Selected country</p>
            <div className="mt-3 inline-flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
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
          </div>
          {trend ? (
            <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-4 py-3">
              <span className="text-sm text-slate-500">Live classification</span>
              <TrendPill trend={trend.classification} />
            </div>
          ) : null}
        </div>
      </Panel>

      {error ? <Panel title="Unable to load country view" description={error} /> : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {countryDataLoading ? (
          <div className="h-[104px] animate-pulse rounded-3xl bg-slate-100" />
        ) : latest ? (
          <StatCard
            label="Latest Daily Cases"
            value={formatNumber(latest.new_cases)}
            accent="ember"
            icon={<Activity className="size-5 text-ember" />}
            helper={`Latest point: ${latest.date}`}
          />
        ) : null}

        {countryDataLoading ? (
          <div className="h-[104px] animate-pulse rounded-3xl bg-slate-100" />
        ) : latest ? (
          <StatCard
            label="7-Day Average"
            value={formatNumber(latest.cases_ma7)}
            accent="teal"
            icon={<TrendingUp className="size-5 text-tealDeep" />}
            helper={formatPercent(latest.growth_rate)}
          />
        ) : null}

        {countryDataLoading || trendLoading ? (
          <div className="h-[104px] animate-pulse rounded-3xl bg-slate-100" />
        ) : latest && trend ? (
          <StatCard
            label="Surge Ratio"
            value={latest.surge_ratio.toFixed(2)}
            accent="slate"
            icon={<HeartPulse className="size-5 text-slate-700" />}
            helper={`Trend score ${trend.score.toFixed(1)}`}
          />
        ) : null}

        {countryDataLoading ? (
          <div className="h-[104px] animate-pulse rounded-3xl bg-slate-100" />
        ) : latest ? (
          <StatCard
            label="Vaccination"
            value={latest.vaccination_coverage_all ? `${latest.vaccination_coverage_all.toFixed(1)}%` : "N/A"}
            accent="slate"
            helper="Latest `all`-group coverage signal"
          />
        ) : null}
      </section>

      <div className="grid gap-6">
        <Panel title={`${selectedCountry} cases and forecast`} description="Daily cases, 7-day moving average, and hybrid 14-day forecast with surge highlighting.">
          {countryDataLoading ? (
            <div className="h-[300px] animate-pulse rounded-3xl bg-slate-100" />
          ) : countryData ? (
            <CountryCasesChart history={countryData.data} forecast={forecast?.forecast ?? []} />
          ) : null}
        </Panel>

        <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
          <Panel title="Growth momentum" description="Week-over-week change in the smoothed case curve.">
            {countryDataLoading ? (
              <div className="h-[250px] animate-pulse rounded-3xl bg-slate-100" />
            ) : countryData ? (
              <GrowthRateChart data={countryData.data} />
            ) : null}
          </Panel>

          <div className="space-y-6">
            {trendLoading && forecastLoading ? (
              <div className="h-[100px] animate-pulse rounded-3xl bg-slate-100" />
            ) : (trend || forecast) ? (
              <InsightBox body={trend?.narrative ?? forecast?.narrative ?? ""} />
            ) : null}
            <Panel title="Key observations">
              {countryDataLoading ? (
                <div className="h-[150px] animate-pulse rounded-3xl bg-slate-100" />
              ) : countryData ? (
                <div className="space-y-3 text-sm leading-7 text-slate-600">
                  {countryData.insights.map((item) => (
                    <p key={item}>{item}</p>
                  ))}
                </div>
              ) : null}
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
}
