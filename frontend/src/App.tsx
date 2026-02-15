import { useState, useCallback } from 'react'
import { TreeList } from './components/TreeList'
import { TreeView } from './components/TreeView'
import type { DecisionTree } from './types/decisionTree'
import { treesApi } from './api/client'
import './App.css'

function App() {
  const [selectedTree, setSelectedTree] = useState<DecisionTree | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadTree = useCallback((id: string) => {
    setError(null)
    treesApi
      .get(id)
      .then(setSelectedTree)
      .catch((e) => setError(e.message))
  }, [])

  const clearSelection = useCallback(() => {
    setSelectedTree(null)
    setError(null)
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>CAIRE</h1>
        <p>Clinical AI for Rule-based Execution — authoring &amp; review</p>
      </header>
      <main className="app-main">
        <aside className="sidebar">
          <h2>Trees</h2>
          <TreeList onSelect={loadTree} />
        </aside>
        <section className="content">
          {error && <p className="error">{error}</p>}
          {selectedTree ? (
            <>
              <button type="button" className="back" onClick={clearSelection}>
                ← Back to list
              </button>
              <TreeView tree={selectedTree} />
            </>
          ) : (
            <p className="hint">Select a decision tree from the list or add one via the API (e.g. POST /api/trees or /api/trees/generate).</p>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
