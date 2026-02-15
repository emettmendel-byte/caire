import { useState, useCallback } from 'react'
import { TreeList } from './components/TreeList'
import { TreeEditor } from './components/TreeEditor'
import { TreeViewerErrorBoundary } from './components/TreeViewer/TreeViewerErrorBoundary'
import './App.css'

function App() {
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null)

  const handleSelectTree = useCallback((id: string) => setSelectedTreeId(id), [])
  const handleBack = useCallback(() => setSelectedTreeId(null), [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>CAIRE</h1>
        <p>Clinical AI for Rule-based Execution — authoring &amp; review</p>
      </header>
      <main className="app-main">
        <aside className="sidebar">
          <h2>Trees</h2>
          <TreeList onSelect={handleSelectTree} />
        </aside>
        <section className="content">
          {selectedTreeId ? (
            <TreeViewerErrorBoundary>
              <TreeEditor treeId={selectedTreeId} onBack={handleBack} />
            </TreeViewerErrorBoundary>
          ) : (
            <p className="hint">Select a decision tree from the list or add one via the API (e.g. POST /api/compile or upload a guideline).</p>
          )}
        </section>
      </main>
    </div>
  )
}

export default App
