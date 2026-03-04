import { useMemo } from 'react'
import { TreeList } from '../TreeList'
import { TreeEditor } from '../TreeEditor'
import { TreeViewerErrorBoundary } from '../TreeViewer/TreeViewerErrorBoundary'
import { SplitPane } from '../Layout/SplitPane'

interface EditTreesSectionProps {
  selectedTreeId: string | null
  onSelectTree: (id: string) => void
  onClearSelection: () => void
}

export function EditTreesSection({ selectedTreeId, onSelectTree, onClearSelection }: EditTreesSectionProps) {
  const effectiveTreeId = useMemo(() => (selectedTreeId && selectedTreeId.length > 0 ? selectedTreeId : null), [selectedTreeId])

  return (
    <div className="section">
      <SplitPane
        storageKey="split:edit"
        minLeftPx={260}
        minRightPx={520}
        initialLeftPx={300}
        left={(
          <aside className="sidebar">
            <h2>Trees (JSON)</h2>
            <TreeList onSelect={onSelectTree} />
          </aside>
        )}
        right={(
          <section className="content">
            {effectiveTreeId ? (
              <TreeViewerErrorBoundary>
                <TreeEditor treeId={effectiveTreeId} onBack={onClearSelection} />
              </TreeViewerErrorBoundary>
            ) : (
              <div className="content-pad">
                <p className="hint">Select a tree to edit.</p>
              </div>
            )}
          </section>
        )}
      />
    </div>
  )
}

