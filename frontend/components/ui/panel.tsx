import { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

interface PanelProps extends PropsWithChildren {
  className?: string;
  title?: string;
  description?: string;
}

export function Panel({ children, className, title, description }: PanelProps) {
  return (
    <section className={cn("rounded-[2rem] border border-white/60 bg-white/80 p-6 shadow-float backdrop-blur", className)}>
      {title ? <h2 className="font-display text-2xl text-ink">{title}</h2> : null}
      {description ? <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p> : null}
      <div className={cn(title ? "mt-6" : "")}>{children}</div>
    </section>
  );
}
