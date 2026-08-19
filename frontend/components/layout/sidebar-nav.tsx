"use client";

import Link from "next/link";
import { Activity, BarChart3, BrainCircuit, Globe2 } from "lucide-react";

import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "Global Dashboard", icon: Globe2 },
  { href: "/country", label: "Country Analysis", icon: BarChart3 },
  { href: "/insights", label: "AI Insights", icon: BrainCircuit }
];

export function SidebarNav() {
  return (
    <aside className="sticky top-0 hidden h-screen w-72 shrink-0 border-r border-white/50 bg-white/55 px-6 py-8 backdrop-blur xl:block">
      <div className="mb-10 flex items-center gap-3">
        <div className="rounded-2xl bg-gradient-to-br from-ember to-tealDeep p-3 text-white shadow-float">
          <Activity className="size-6" />
        </div>
        <div>
          <p className="font-display text-xl text-ink">COVID Signal Studio</p>
          <p className="text-sm text-slate-500">Forecasting and public-health intelligence</p>
        </div>
      </div>

      <nav className="space-y-2">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-slate-600 transition hover:bg-white hover:text-ink"
            )}
          >
            <Icon className="size-4" />
            <span>{label}</span>
          </Link>
        ))}
      </nav>

      <div className="mt-10 rounded-3xl bg-gradient-to-br from-tealDeep to-emerald-700 p-5 text-white shadow-float">
        <p className="font-display text-lg">AI Insight Box</p>
        <p className="mt-2 text-sm leading-6 text-emerald-50">
          Surface surge conditions, explain drivers, and compare pressure across countries from one shared analytics workflow.
        </p>
      </div>
    </aside>
  );
}
