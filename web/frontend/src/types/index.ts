/* ============================================================
 * Prompt Lab — TypeScript domain types (mirror REST API shapes)
 * ============================================================ */

/** List item shape from GET /api/versions */
export interface VersionListItem {
  id: string;
  content_hash: string;
  timestamp: string;
  author: string;
  changed_var: string;
  change_note: string;
  changed_from: string | null;
}

/** Full version shape from GET /api/versions/{id} */
export interface Version extends VersionListItem {
  name: string;
  prompt_text: string;
}

/** Diff endpoint payload */
export interface DiffResponse {
  diff: string;
}

/** Case list item from GET /api/cases */
export interface CaseListItem {
  case_id: string;
  collection: string;
  type?: string;
  [key: string]: unknown;
}

/** Request body for POST /api/versions */
export interface CreateVersionPayload {
  name: string;
  prompt_text: string;
  changed_from?: string | null;
  changed_var?: string;
  change_note?: string;
  author?: string;
}

/** Per-side output record inside a case */
export interface SideOutput {
  output: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  finish_reason: string;
  error: string | null;
}

/** Single evaluation entry */
export interface Evaluation {
  metric_name: string;
  score: number;
  reason: string;
  status: string;
}

/** A single case inside a run */
export interface RunCase {
  case_id: string;
  baseline: SideOutput;
  candidate: SideOutput;
  evaluations: Evaluation[];
}

/** Summary stats per side */
export interface SideSummary {
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  avg_latency_ms: number;
  non_empty_rate: number;
  error_rate: number;
}

/** Per-metric aggregate { avg, count } */
export interface MetricAgg {
  avg: number;
  count: number;
}

/** Nested eval summary keyed by side then metric name */
export interface EvalSummary {
  baseline: Record<string, MetricAgg>;
  candidate: Record<string, MetricAgg>;
}

export interface RunSummary {
  baseline: SideSummary;
  candidate: SideSummary;
  eval_summary: EvalSummary;
}

/** Full run result from GET /api/runs/{id} */
export interface RunResult {
  run_id: string;
  baseline_version: string;
  candidate_version: string;
  dataset: string;
  timestamp: string;
  total_cases?: number;
  cases: RunCase[];
  summary: RunSummary;
}

/** List item shape from GET /api/runs */
export interface RunListItem {
  run_id: string;
  baseline_version: string;
  candidate_version: string;
  dataset: string;
  timestamp: string;
  total_cases: number;
}

/** Request body for POST /api/runs */
export interface CreateRunPayload {
  baseline: string;
  candidate: string;
  dataset: string;
  model?: string;
  max_tokens?: number;
  thinking?: string;
  concurrency?: number;
}

/** GET /api/config payload (loosely typed) */
export interface AppConfig {
  provider: Record<string, unknown>;
  run: Record<string, unknown>;
  eval: Record<string, unknown>;
}

/** Standard API error wrapper (best-effort) */
export interface ApiError {
  detail?: string;
  message?: string;
}
