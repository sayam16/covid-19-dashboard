import { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  icon?: ReactNode;
  accent?: "ember" | "teal" | "slate";
  helper?: string;
}

const accentStyles = {
  ember: "from-orange-50 to-roseSoft text-ember",
  teal: "from-tealSoft to-emerald-50 text-tealDeep",
  slate: "from-slateSoft to-slate-50 text-slate-700"
};

export function StatCard({ label, value, icon, accent = "slate", helper }: StatCardProps) {
  return (
    <div className={cn("rounded-[2rem] border border-white/60 bg-gradient-to-br p-5 shadow-float", accentStyles[accent])}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">{label}</p>
          <p className="mt-3 font-display text-3xl text-ink">{value}</p>
          {helper ? <p className="mt-2 text-sm text-slate-500">{helper}</p> : null}
        </div>
        {icon ? <div className="rounded-2xl bg-white/70 p-3">{icon}</div> : null}
      </div>
    </div>
  );
}
