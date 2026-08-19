import { CalendarRange, DatabaseZap, Radar } from "lucide-react";

export function Topbar() {
  return (
    <header className="mb-8 flex flex-col gap-4 rounded-[2rem] border border-white/50 bg-white/75 px-6 py-5 shadow-float backdrop-blur lg:flex-row lg:items-center lg:justify-between">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-ember">Scalable COVID-19 Data Analytics Dashboard</p>
        <h1 className="font-display text-3xl text-ink">
          Signal-first monitoring for cases, surges, and short-horizon forecasts
        </h1>
      </div>

      <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
        <div className="flex items-center gap-2 rounded-2xl bg-roseSoft px-4 py-3">
          <DatabaseZap className="size-4 text-ember" />
          Multi-source ingestion
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-tealSoft px-4 py-3">
          <Radar className="size-4 text-tealDeep" />
          Hybrid trend detection
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-slateSoft px-4 py-3">
          <CalendarRange className="size-4 text-slate-700" />
          7 to 14 day forecasting
        </div>
      </div>
    </header>
  );
}
