/**
 * MetricChart — grouped bar chart comparing baseline vs candidate across
 * multiple eval metrics, using recharts.
 */
import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EvalSummary } from "../types";

interface MetricChartProps {
  evalSummary: EvalSummary;
  height?: number;
}

interface Datum {
  metric: string;
  baseline: number | null;
  candidate: number | null;
}

const AXIS = { fontSize: 11, fill: "#9a9aa3", fontFamily: "var(--mono)" } as const;

const tooltipStyle = {
  backgroundColor: "#1a1a1e",
  border: "1px solid #2e2e34",
  borderRadius: "6px",
  fontSize: "12px",
  color: "#ededf0",
} as const;

export default function MetricChart({
  evalSummary,
  height = 240,
}: MetricChartProps): ReactNode {
  // Union of metric names across both sides
  const metrics = new Set<string>([
    ...Object.keys(evalSummary.baseline ?? {}),
    ...Object.keys(evalSummary.candidate ?? {}),
  ]);

  const data: Datum[] = [...metrics]
    .sort()
    .map((metric) => ({
      metric,
      baseline: evalSummary.baseline?.[metric]?.avg ?? null,
      candidate: evalSummary.candidate?.[metric]?.avg ?? null,
    }));

  if (data.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)] text-sm text-[var(--text-muted)]">
        No evaluation metrics available
      </div>
    );
  }

  return (
    <div
      className="rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)] p-4"
      style={{ height }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#232327" vertical={false} />
          <XAxis
            dataKey="metric"
            tick={AXIS}
            tickLine={{ stroke: "#2e2e34" }}
            axisLine={{ stroke: "#2e2e34" }}
            interval={0}
            angle={-12}
            textAnchor="end"
            height={48}
          />
          <YAxis
            domain={[0, 1]}
            tick={AXIS}
            tickLine={{ stroke: "#2e2e34" }}
            axisLine={{ stroke: "#2e2e34" }}
          />
          <Tooltip
            cursor={{ fill: "rgba(99,102,241,0.06)" }}
            contentStyle={tooltipStyle}
            formatter={(value) => {
              const n = typeof value === "number" ? value : Number(value);
              return Number.isNaN(n) ? String(value) : n.toFixed(3);
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "#9a9aa3", paddingTop: 4 }}
            iconType="circle"
          />
          <Bar dataKey="baseline" name="baseline" fill="#6366f1" radius={[3, 3, 0, 0]} maxBarSize={36}>
            {data.map((d, i) => (
              <Cell key={`b-${i}`} opacity={d.baseline === null ? 0.15 : 1} />
            ))}
          </Bar>
          <Bar dataKey="candidate" name="candidate" fill="#22c55e" radius={[3, 3, 0, 0]} maxBarSize={36}>
            {data.map((d, i) => (
              <Cell key={`c-${i}`} opacity={d.candidate === null ? 0.15 : 1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
