"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Globe2, ShieldAlert, Skull } from "lucide-react";

import { GlobalTrendChart } from "@/components/charts/global-trend-chart";
import { Panel } from "@/components/ui/panel";
import { StatCard } from "@/components/ui/stat-card";
import { TrendPill } from "@/components/ui/trend-pill";
import { fetchGlobalSummary, GlobalSummary } from "@/lib/api";
import { formatNumber } from "@/lib/format";

export default function HomePage() {
  const [summary, setSummary] = useState<GlobalSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGlobalSummary().then(setSummary).catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <Panel title="Backend unavailable" description={error} />;
  }

  if (!summary) {
    return <Panel title="Loading global summary" description="Fetching latest harmonized case, hospitalization, and vaccination data." />;
  }

  return (
    <div className="space-y-6 pb-10">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total Cases"
          value={formatNumber(summary.total_cases)}
          accent="ember"
          icon={<Globe2 className="size-5 text-ember" />}
          helper={`As of ${summary.latest_date}`}
        />
        <StatCard
          label="Total Deaths"
          value={formatNumber(summary.total_deaths)}
          accent="slate"
          icon={<Skull className="size-5 text-slate-700" />}
          helper="Cumulative across tracked countries"
        />
        <StatCard
          label="New Cases, 7 Days"
          value={formatNumber(summary.new_cases_last_7d)}
          accent="teal"
          icon={<AlertTriangle className="size-5 text-tealDeep" />}
          helper="Rolling 7-day aggregate"
        />
        <StatCard
          label="Countries Tracked"
          value={formatNumber(summary.countries_tracked, false)}
          accent="slate"
          icon={<ShieldAlert className="size-5 text-slate-700" />}
          helper="Countries with harmonized time series"
        />
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.6fr,0.9fr]">
        <Panel
          title="Global activity curve"
          description="Interactive global trend view with range, scale, and series controls across the merged WHO case feeds."
        >
          <GlobalTrendChart data={summary.global_series} sourceWindow={summary.source_window} />
        </Panel>

        <Panel
          title="Trend overview"
          description="Countries with the highest current pressure scores based on surge ratio, growth, and hospitalization signals."
        >
          <div className="space-y-4">
            {summary.top_surge_countries.map((country) => (
              <div key={country.country} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-display text-xl text-ink">{country.country}</p>
                    <p className="text-sm text-slate-500">
                      {formatNumber(country.cases_ma7)} avg daily cases, {(country.growth_rate * 100).toFixed(1)}% growth
                    </p>
                  </div>
                  <TrendPill trend={country.trend_label} />
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-400 to-rose-500"
                    style={{ width: `${Math.min(country.trend_score, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
