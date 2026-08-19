import { TrendLabel } from "@/lib/api";
import { cn } from "@/lib/utils";

const toneMap: Record<TrendLabel, string> = {
  Normal: "bg-emerald-100 text-emerald-800",
  Moderate: "bg-amber-100 text-amber-800",
  Surge: "bg-rose-100 text-rose-700"
};

export function TrendPill({ trend }: { trend: TrendLabel }) {
  return (
    <span className={cn("inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]", toneMap[trend])}>
      {trend}
    </span>
  );
}
