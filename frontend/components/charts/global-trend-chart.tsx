"use client";

import { useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Brush
} from "recharts";

import { GlobalSeriesPoint, SourceWindow } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";

type MetricMode = "cases" | "deaths";
type RangeMode = "30" | "90" | "180" | "all";
type ScaleMode = "linear" | "log";

const rangeOptions: Array<{ label: string; value: RangeMode }> = [
  { label: "30D", value: "30" },
  { label: "90D", value: "90" },
  { label: "180D", value: "180" },
  { label: "All", value: "all" }
];

const metricOptions: Array<{ label: string; value: MetricMode }> = [
  { label: "Cases", value: "cases" },
  { label: "Deaths", value: "deaths" }
];

const scaleOptions: Array<{ label: string; value: ScaleMode }> = [
  { label: "Linear", value: "linear" },
  { label: "Log", value: "log" }
];

function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short"
  }).format(new Date(value));
}

export function GlobalTrendChart({
  data,
  sourceWindow
}: {
  data: GlobalSeriesPoint[];
  sourceWindow: SourceWindow;
}) {
  const [metric, setMetric] = useState<MetricMode>("cases");
  const [range, setRange] = useState<RangeMode>("180");
  const [scale, setScale] = useState<ScaleMode>("linear");
  const [showRaw, setShowRaw] = useState(true);
  const [showSmooth, setShowSmooth] = useState(true);

  const chartData = useMemo(() => {
    const withDerived = data.map((point, index, list) => {
      const deathsWindow = list.slice(Math.max(0, index - 6), index + 1);
      const deathsMa7 =
        deathsWindow.reduce((sum, item) => sum + Number(item.new_deaths ?? 0), 0) / deathsWindow.length;

      const rawValue = metric === "cases" ? Number(point.new_cases ?? 0) : Number(point.new_deaths ?? 0);
      const smoothValue = metric === "cases" ? Number(point.cases_ma7 ?? 0) : deathsMa7;

      return {
        ...point,
        label: formatDateLabel(point.date),
        rawValue,
        smoothValue,
        rawValueLog: rawValue > 0 ? rawValue : null,
        smoothValueLog: smoothValue > 0 ? smoothValue : null
      };
    });

    if (range === "all") return withDerived;
    return withDerived.slice(-Number(range));
  }, [data, metric, range]);

  const rawKey = scale === "log" ? "rawValueLog" : "rawValue";
  const smoothKey = scale === "log" ? "smoothValueLog" : "smoothValue";
  const transitionDate = sourceWindow.daily_feed_end || "";
  const transitionVisible = chartData.some((point) => point.date === transitionDate);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 rounded-[1.75rem] border border-slate-100 bg-slate-50/80 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {metricOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setMetric(option.value)}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition",
                  metric === option.value
                    ? "bg-ink text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {rangeOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setRange(option.value)}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition",
                  range === option.value
                    ? "bg-tealDeep text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {scaleOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setScale(option.value)}
                className={cn(
                  "rounded-full px-4 py-2 text-sm font-medium transition",
                  scale === option.value
                    ? "bg-ember text-white"
                    : "bg-white text-slate-600 hover:bg-slate-100"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
          <label className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2">
            <input checked={showRaw} onChange={() => setShowRaw((value) => !value)} type="checkbox" />
            Raw series
          </label>
          <label className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2">
            <input checked={showSmooth} onChange={() => setShowSmooth((value) => !value)} type="checkbox" />
            7-day trend
          </label>
          <div className="rounded-full bg-white px-3 py-2">
            Daily feed through <span className="font-medium text-ink">{sourceWindow.daily_feed_end}</span>
          </div>
          <div className="rounded-full bg-white px-3 py-2">
            Weekly continuation through <span className="font-medium text-ink">{sourceWindow.weekly_feed_end}</span>
          </div>
        </div>
      </div>

      <div className="h-[26rem] w-full">
        <ResponsiveContainer>
          <ComposedChart data={chartData}>
            <defs>
              <linearGradient id="globalSmoothFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="5%" stopColor="#0f766e" stopOpacity={0.22} />
                <stop offset="95%" stopColor="#0f766e" stopOpacity={0.03} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#dbeafe" />
            <XAxis dataKey="date" minTickGap={30} tick={{ fill: "#64748b", fontSize: 12 }} tickFormatter={formatDateLabel} />
            <YAxis
              scale={scale}
              domain={scale === "log" ? [1, "auto"] : [0, "auto"]}
              allowDataOverflow={scale === "log"}
              tick={{ fill: "#64748b", fontSize: 12 }}
              tickFormatter={(value) => formatNumber(Number(value))}
            />
            <Tooltip
              contentStyle={{ borderRadius: 18, borderColor: "#e2e8f0" }}
              formatter={(value, _name, item) => {
                const label = item.dataKey === rawKey ? "Raw" : "7-day trend";
                return [value == null ? "N/A" : formatNumber(Number(value), false), label];
              }}
              labelFormatter={(value) => new Date(value).toDateString()}
            />
            <Legend />
            {transitionVisible ? (
              <ReferenceLine
                x={transitionDate}
                stroke="#1d4ed8"
                strokeDasharray="4 4"
                label={{
                  value: "Daily feed ends",
                  fill: "#1d4ed8",
                  fontSize: 11,
                  position: "insideTopRight"
                }}
              />
            ) : null}
            {showSmooth ? (
              <Area
                type="monotone"
                dataKey={smoothKey}
                stroke="#0f766e"
                fill="url(#globalSmoothFill)"
                strokeWidth={2.5}
                name={metric === "cases" ? "Cases MA7" : "Deaths MA7"}
                connectNulls
              />
            ) : null}
            {showRaw ? (
              <Line
                type="monotone"
                dataKey={rawKey}
                stroke="#c2410c"
                strokeWidth={2}
                dot={false}
                name={metric === "cases" ? "Daily cases" : "Daily deaths"}
                connectNulls
              />
            ) : null}
            <Brush
              dataKey="date"
              height={26}
              stroke="#94a3b8"
              travellerWidth={10}
              tickFormatter={formatDateLabel}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-3 text-sm text-slate-600 md:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 px-4 py-3">
          Analysis window: <span className="font-medium text-ink">{sourceWindow.analysis_start}</span> to{" "}
          <span className="font-medium text-ink">{sourceWindow.analysis_end}</span>
        </div>
        <div className="rounded-2xl bg-slate-50 px-4 py-3">
          Feed mode: <span className="font-medium text-ink">{sourceWindow.analysis_mode}</span>
        </div>
        <div className="rounded-2xl bg-slate-50 px-4 py-3">
          Tip: use `Log` plus `7-day trend` to compare waves without raw weekly pulses dominating the view.
        </div>
      </div>
    </div>
  );
}
