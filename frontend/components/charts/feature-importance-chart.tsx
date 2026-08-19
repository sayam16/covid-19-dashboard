"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { titleCase } from "@/lib/format";

export function FeatureImportanceChart({
  data
}: {
  data: Array<{ feature: string; importance: number }>;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 12, right: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tick={{ fill: "#64748b", fontSize: 12 }} />
          <YAxis
            dataKey="feature"
            type="category"
            width={130}
            tick={{ fill: "#475569", fontSize: 12 }}
            tickFormatter={titleCase}
          />
          <Tooltip formatter={(value: number) => Number(value).toFixed(3)} />
          <Bar dataKey="importance" fill="#c2410c" radius={[0, 8, 8, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
