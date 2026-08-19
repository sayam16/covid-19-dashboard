import { Sparkles } from "lucide-react";

interface InsightBoxProps {
  title?: string;
  body: string;
}

export function InsightBox({ title = "AI Insight", body }: InsightBoxProps) {
  return (
    <div className="rounded-[2rem] border border-amber-200 bg-gradient-to-br from-amber-50 via-white to-rose-50 p-5 shadow-float">
      <div className="flex items-center gap-3">
        <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
          <Sparkles className="size-5" />
        </div>
        <div>
          <p className="font-display text-xl text-ink">{title}</p>
          <p className="text-sm text-slate-500">Auto-generated interpretation from the latest merged signal</p>
        </div>
      </div>
      <p className="mt-4 text-sm leading-7 text-slate-700">{body}</p>
    </div>
  );
}
