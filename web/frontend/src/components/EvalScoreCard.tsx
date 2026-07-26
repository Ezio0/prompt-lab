/**
 * EvalScoreCard — compact card showing a single eval metric's score for
 * baseline vs candidate, with a small delta indicator.
 */
import type { ReactNode } from "react";
import type { MetricAgg } from "../types";

interface EvalScoreCardProps {
  metricName: string;
  baseline?: MetricAgg;
  candidate?: MetricAgg;
}

function fmt(n: number | undefined, digits = 3): string {
  if (n === undefined || n === null || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

function deltaClass(d: number): string {
  if (d > 0.001) return "text-emerald-400";
  if (d < -0.001) return "text-rose-400";
  return "text-zinc-400";
}

function scoreColor(score: number | undefined): string {
  if (score === undefined) return "text-zinc-500";
  if (score >= 0.85) return "text-emerald-400";
  if (score >= 0.7) return "text-amber-400";
  if (score >= 0.5) return "text-orange-400";
  return "text-rose-400";
}

export default function EvalScoreCard({
  metricName,
  baseline,
  candidate,
}: EvalScoreCardProps): ReactNode {
  const bAvg = baseline?.avg;
  const cAvg = candidate?.avg;
  const delta =
    bAvg !== undefined && cAvg !== undefined ? cAvg - bAvg : undefined;

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)] p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--text-primary)]">
          {metricName}
        </span>
        {delta !== undefined && (
          <span className={`text-xs font-mono ${deltaClass(delta)}`}>
            {delta >= 0 ? "+" : ""}
            {delta.toFixed(3)}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
            baseline
          </span>
          <span className={`font-mono text-lg ${scoreColor(bAvg)}`}>
            {fmt(bAvg)}
          </span>
          {baseline && (
            <span className="text-[10px] text-[var(--text-muted)]">
              n={baseline.count}
            </span>
          )}
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">
            candidate
          </span>
          <span className={`font-mono text-lg ${scoreColor(cAvg)}`}>
            {fmt(cAvg)}
          </span>
          {candidate && (
            <span className="text-[10px] text-[var(--text-muted)]">
              n={candidate.count}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
