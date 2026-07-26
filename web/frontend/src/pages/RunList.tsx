import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listRuns } from '../api/client'
import type { RunListItem } from '../types'

export default function RunList() {
  const [runs, setRuns] = useState<RunListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listRuns().then(r => { setRuns(r); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-neutral-500">Loading...</div>

  if (runs.length === 0) {
    return (
      <div className="text-neutral-500">
        <p className="text-lg">No runs yet.</p>
        <p className="text-sm mt-2">Run: <code className="bg-neutral-800 px-2 py-0.5 rounded">prompt-lab run --baseline v1 --candidate v2 --dataset cases</code></p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">A/B Runs</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-800 text-neutral-400">
            <th className="text-left py-2 pr-4">Run ID</th>
            <th className="text-left py-2 pr-4">Baseline</th>
            <th className="text-left py-2 pr-4">Candidate</th>
            <th className="text-left py-2 pr-4">Dataset</th>
            <th className="text-left py-2 pr-4">Cases</th>
            <th className="text-left py-2">Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {runs.map(r => (
            <tr key={r.run_id} className="border-b border-neutral-900 hover:bg-neutral-900">
              <td className="py-2 pr-4"><Link to={`/runs/${r.run_id}`} className="text-purple-400 hover:underline font-mono text-xs">{r.run_id}</Link></td>
              <td className="py-2 pr-4">{r.baseline_version}</td>
              <td className="py-2 pr-4">{r.candidate_version}</td>
              <td className="py-2 pr-4">{r.dataset}</td>
              <td className="py-2 pr-4">{r.total_cases}</td>
              <td className="py-2 text-neutral-400">{r.timestamp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
