import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getRun } from '../api/client'
import EvalScoreCard from '../components/EvalScoreCard'
import MetricChart from '../components/MetricChart'
import type { RunResult } from '../types'

export default function RunReport() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<RunResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    getRun(id).then((r: RunResult) => { setRun(r); setLoading(false) }).catch(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-neutral-500">Loading...</div>
  if (!run) return <div className="text-red-400">Run not found</div>

  const { summary } = run
  const evalSummary = summary.eval_summary
  const hasEval = evalSummary && (evalSummary.baseline || evalSummary.candidate) &&
    (Object.keys(evalSummary.baseline || {}).length > 0 || Object.keys(evalSummary.candidate || {}).length > 0)

  const chartData = [
    { name: 'Prompt Tokens', baseline: Math.round(summary.baseline.avg_prompt_tokens), candidate: Math.round(summary.candidate.avg_prompt_tokens) },
    { name: 'Completion', baseline: Math.round(summary.baseline.avg_completion_tokens), candidate: Math.round(summary.candidate.avg_completion_tokens) },
    { name: 'Latency (ms)', baseline: Math.round(summary.baseline.avg_latency_ms), candidate: Math.round(summary.candidate.avg_latency_ms) },
  ]

  return (
    <div>
      <h1 className="text-xl font-bold mb-2">Run: {run.run_id}</h1>
      <div className="flex gap-4 text-sm text-neutral-400 mb-6">
        <span>{run.baseline_version} → {run.candidate_version}</span>
        <span>Dataset: {run.dataset}</span>
        <span>{run.timestamp}</span>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {chartData.map(d => (
          <div key={d.name} className="bg-neutral-900 rounded-lg border border-neutral-800 p-3">
            <div className="text-xs text-neutral-500">{d.name}</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-purple-400 font-bold">{d.baseline}</span>
              <span className="text-neutral-600 text-xs">→</span>
              <span className="text-cyan-400 font-bold">{d.candidate}</span>
              {d.baseline > 0 && (
                <span className={`text-xs ${d.candidate < d.baseline ? 'text-green-400' : 'text-red-400'}`}>
                  {d.candidate < d.baseline ? '↓' : '↑'}{Math.abs((d.candidate - d.baseline) / d.baseline * 100).toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        ))}
        <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-3">
          <div className="text-xs text-neutral-500">Error Rate</div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-purple-400 font-bold">{(summary.baseline.error_rate * 100).toFixed(0)}%</span>
            <span className="text-neutral-600 text-xs">→</span>
            <span className="text-cyan-400 font-bold">{(summary.candidate.error_rate * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      {hasEval && (
        <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-4 mb-6">
          <h2 className="text-sm font-bold mb-3">Evaluation Metric Comparison</h2>
          <MetricChart evalSummary={evalSummary} />
        </div>
      )}

      {/* Per-case table */}
      <h2 className="text-sm font-bold mb-3">Per-case Results ({run.cases.length})</h2>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-neutral-800 text-neutral-500">
              <th className="text-left py-2 pr-3">Case</th>
              <th className="text-right py-2 pr-3">B-tokens</th>
              <th className="text-right py-2 pr-3">C-tokens</th>
              <th className="text-right py-2 pr-3">B-ms</th>
              <th className="text-right py-2 pr-3">C-ms</th>
              {hasEval && <th className="text-left py-2">Eval Scores</th>}
            </tr>
          </thead>
          <tbody>
            {run.cases.map(c => {
              const half = c.evaluations.length / 2
              const baselineEvals = c.evaluations.slice(0, half)
              const candidateEvals = c.evaluations.slice(half)
              return (
                <tr key={c.case_id} className="border-b border-neutral-900">
                  <td className="py-2 pr-3 font-mono text-purple-400">{c.case_id}</td>
                  <td className="text-right py-2 pr-3">{c.baseline.prompt_tokens}</td>
                  <td className="text-right py-2 pr-3">{c.candidate.prompt_tokens}</td>
                  <td className="text-right py-2 pr-3">{Math.round(c.baseline.latency_ms)}</td>
                  <td className="text-right py-2 pr-3">{Math.round(c.candidate.latency_ms)}</td>
                  {hasEval && (
                    <td className="py-2">
                      <div className="flex flex-wrap gap-1">
                        {baselineEvals.map((ev, i) => (
                          <span key={`b-${i}`} className={`text-xs px-1.5 py-0.5 rounded ${ev.status === 'pass' ? 'bg-green-950 text-green-400' : ev.status === 'error' ? 'bg-red-950 text-red-400' : 'bg-neutral-800 text-neutral-500'}`}>
                            B:{ev.score.toFixed(2)}
                          </span>
                        ))}
                        {candidateEvals.map((ev, i) => (
                          <span key={`c-${i}`} className={`text-xs px-1.5 py-0.5 rounded ${ev.status === 'pass' ? 'bg-cyan-950 text-cyan-400' : ev.status === 'error' ? 'bg-red-950 text-red-400' : 'bg-neutral-800 text-neutral-500'}`}>
                            C:{ev.score.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Eval summary cards */}
      {hasEval && (
        <div className="mt-6">
          <h2 className="text-sm font-bold mb-3">Evaluation Summary</h2>
          <div className="grid grid-cols-3 gap-3">
            {Object.keys(evalSummary.baseline || {}).map(metric => {
              const b = evalSummary.baseline?.[metric]
              const c = evalSummary.candidate?.[metric]
              return (
                <EvalScoreCard key={metric} metricName={metric} baseline={b} candidate={c} />
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
