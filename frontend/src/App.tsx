import { useCallback, useMemo, useState } from 'react'
import { CreateTreesSection } from './components/Sections/CreateTreesSection'
import { EditTreesSection } from './components/Sections/EditTreesSection'
import { TestingSection } from './components/Sections/TestingSection'
import './App.css'

type TabId = 'create' | 'edit' | 'test'

function App() {
  const [tab, setTab] = useState<TabId>('create')
  const [selectedTreeId, setSelectedTreeId] = useState<string | null>(null)

  const handleSelectTree = useCallback((id: string) => setSelectedTreeId(id), [])
  const handleClearTree = useCallback(() => setSelectedTreeId(null), [])
  const openTreeInEditor = useCallback((id: string) => {
    setSelectedTreeId(id)
    setTab('edit')
  }, [])

  const tabContent = useMemo(() => {
    if (tab === 'create') {
      return <CreateTreesSection onOpenTree={openTreeInEditor} />
    }
    if (tab === 'edit') {
      return (
        <EditTreesSection
          selectedTreeId={selectedTreeId}
          onSelectTree={handleSelectTree}
          onClearSelection={handleClearTree}
        />
      )
    }
    return (
      <TestingSection
        selectedTreeId={selectedTreeId}
        onSelectTree={handleSelectTree}
      />
    )
  }, [tab, openTreeInEditor, selectedTreeId, handleSelectTree, handleClearTree])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-row">
          <div>
            <h1>CAIRE</h1>
            <p>Clinical AI for Rule-based Execution — authoring &amp; review</p>
          </div>
          <nav className="tabs" aria-label="Primary">
            <button
              type="button"
              className={tab === 'create' ? 'tab active' : 'tab'}
              onClick={() => setTab('create')}
            >
              Create
            </button>
            <button
              type="button"
              className={tab === 'edit' ? 'tab active' : 'tab'}
              onClick={() => setTab('edit')}
            >
              Edit
            </button>
            <button
              type="button"
              className={tab === 'test' ? 'tab active' : 'tab'}
              onClick={() => setTab('test')}
            >
              Test
            </button>
          </nav>
        </div>
      </header>
      <main className="app-main">{tabContent}</main>
    </div>
  )
}

export default App
