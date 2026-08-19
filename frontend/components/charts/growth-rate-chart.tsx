"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CountryPoint } from "@/lib/api";
import { formatPercent } from "@/lib/format";

export function GrowthRateChart({ data }: { data: CountryPoint[] }) {
  const chartData = data.slice(-90).map((point) => ({
    date: point.date,
    growth_rate: point.growth_rate
  }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" minTickGap={28} tick={{ fill: "#64748b", fontSize: 12 }} />
          <YAxis tickFormatter={(value) => formatPercent(Number(value))} tick={{ fill: "#64748b", fontSize: 12 }} />
          <Tooltip formatter={(value: number) => formatPercent(Number(value))} />
          <Bar dataKey="growth_rate" fill="#0f766e" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
