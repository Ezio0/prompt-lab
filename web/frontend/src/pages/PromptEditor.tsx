import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createVersion, getDiff, listVersions } from '../api/client'

export default function PromptEditor() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [text, setText] = useState('')
  const [note, setNote] = useState('')
  const [changedVar, setChangedVar] = useState('prompt')
  const [author, setAuthor] = useState('')
  const [diffPreview, setDiffPreview] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handlePreviewDiff = async () => {
    setError('')
    try {
      const versions = await listVersions()
      if (versions.length === 0) {
        setDiffPreview('(This will be the first version)')
        return
      }
      const latest = versions[0]
      const diff = await getDiff(latest.id, `__preview__`)
      setDiffPreview(`Diff vs ${latest.id}:\n${diff}`)
    } catch {
      setDiffPreview('(Cannot preview diff — register to see)')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !text.trim()) {
      setError('Name and prompt text are required')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await createVersion({
        name: name.trim(),
        prompt_text: text,
        changed_var: changedVar,
        change_note: note,
        author: author || undefined,
      })
      navigate('/versions')
    } catch (err: unknown) {
      const msg = err instanceof Error && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Registration failed'
        : 'Registration failed'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">Prompt Editor</h1>
      <form onSubmit={handleSubmit} className="space-y-4 max-w-3xl">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-xs text-neutral-500 mb-1">Version Name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. v3-simplified"
              className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="w-40">
            <label className="block text-xs text-neutral-500 mb-1">Changed Type</label>
            <select
              value={changedVar}
              onChange={e => setChangedVar(e.target.value)}
              className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm"
            >
              <option value="prompt">prompt</option>
              <option value="model">model</option>
              <option value="params">params</option>
              <option value="data">data</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-neutral-500 mb-1">
            Prompt Text <span className="text-neutral-600">(use {'{variable}'} for placeholders)</span>
          </label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="You are a helpful assistant. Recommend {topic} for {user}."
            rows={12}
            className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm font-mono"
          />
        </div>

        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-xs text-neutral-500 mb-1">Change Note</label>
            <input
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. Simplified instructions, removed verbose examples"
              className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="w-40">
            <label className="block text-xs text-neutral-500 mb-1">Author</label>
            <input
              value={author}
              onChange={e => setAuthor(e.target.value)}
              placeholder="optional"
              className="w-full bg-neutral-900 border border-neutral-700 rounded px-3 py-2 text-sm"
            />
          </div>
        </div>

        {error && <div className="text-red-400 text-sm">{error}</div>}
        {diffPreview && (
          <pre className="bg-neutral-900 border border-neutral-800 rounded p-3 text-xs font-mono whitespace-pre-wrap">{diffPreview}</pre>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition"
          >
            {submitting ? 'Registering...' : 'Register Version'}
          </button>
          <button
            type="button"
            onClick={handlePreviewDiff}
            className="text-sm text-neutral-400 hover:text-white transition"
          >
            Preview diff
          </button>
          <span className="text-xs text-neutral-600">⚠️ Registration is permanent and cannot be undone</span>
        </div>
      </form>
    </div>
  )
}
