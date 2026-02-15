import { useCallback, useEffect, useState } from 'react'
import type { TreeSummary } from '../types/decisionTree'
import { treesApi } from '../api/client'

interface TreeListProps {
  onSelect: (id: string) => void
}

function loadList(setTrees: (t: TreeSummary[]) => void, setError: (e: string | null) => void, setLoading: (l: boolean) => void) {
  setLoading(true)
  setError(null)
  treesApi
    .list()
    .then(setTrees)
    .catch((e) => setError(e.message))
    .finally(() => setLoading(false))
}

export function TreeList({ onSelect }: TreeListProps) {
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)
  const [uploading, setUploading] = useState(false)

  const refresh = useCallback(() => {
    loadList(setTrees, setError, setLoading)
  }, [])

  useEffect(() => {
    loadList(setTrees, setError, setLoading)
  }, [])

  const handleLoadSample = () => {
    setSeeding(true)
    treesApi
      .seedSample()
      .then(() => refresh())
      .catch((e) => setError(e.message))
      .finally(() => setSeeding(false))
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    treesApi
      .generateFromFile(file, { tree_id: file.name.replace(/\.[^.]+$/, '').replace(/\s+/g, '-') })
      .then(() => refresh())
      .catch((err) => setError(err.message))
      .finally(() => {
        setUploading(false)
        e.target.value = ''
      })
  }

  if (loading) return <p className="loading">Loading trees…</p>
  if (error) return <p className="error">Error: {error}</p>
  if (trees.length === 0) {
    return (
      <div className="empty">
        <p>No decision trees yet.</p>
        <div className="empty-actions">
          <button type="button" onClick={handleLoadSample} disabled={seeding} className="btn-primary">
            {seeding ? 'Loading…' : 'Load sample tree'}
          </button>
          <label className="btn-secondary">
            <input type="file" accept=".md,.pdf,.txt" onChange={handleFileSelect} disabled={uploading} className="sr-only" />
            {uploading ? 'Uploading…' : 'Create from guideline (file)'}
          </label>
        </div>
        <p className="empty-hint">Or add a JSON file to <code>/models</code> and ensure the backend can read it.</p>
      </div>
    )
  }

  return (
    <ul className="tree-list">
      {trees.map((t) => (
        <li key={t.id}>
          <button type="button" onClick={() => onSelect(t.id)}>
            <strong>{t.name}</strong>
            <span className="meta">v{t.version} · {t.id}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
