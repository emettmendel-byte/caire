import { useEffect, useState } from 'react'
import type { TreeSummary } from '../types/decisionTree'
import { treesApi } from '../api/client'

interface TreeListProps {
  onSelect: (id: string) => void
}

export function TreeList({ onSelect }: TreeListProps) {
  const [trees, setTrees] = useState<TreeSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    treesApi
      .list()
      .then(setTrees)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="loading">Loading trees…</p>
  if (error) return <p className="error">Error: {error}</p>
  if (trees.length === 0) return <p className="empty">No decision trees yet. Create one from a guideline (API) or add a sample in /models.</p>

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
