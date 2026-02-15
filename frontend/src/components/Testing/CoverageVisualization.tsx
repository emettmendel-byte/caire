import type { DecisionTree, DecisionNode } from '../../types/decisionTree'
import { getTreeNodes } from '../../types/decisionTree'
import type { TestSuiteResult } from '../../api/tests'

interface CoverageVisualizationProps {
  tree: DecisionTree
  lastResult: TestSuiteResult | null
  onHighlightNode?: (nodeId: string) => void
}

export function CoverageVisualization({ tree, lastResult, onHighlightNode }: CoverageVisualizationProps) {
  const nodes = getTreeNodes(tree)
  const nodeList: DecisionNode[] = Array.isArray(nodes) ? nodes : Object.values(nodes)
  const nodeIds = new Set(nodeList.map((n) => n.id))

  const hitCount: Record<string, number> = {}
  nodeIds.forEach((id) => (hitCount[id] = 0))
  if (lastResult?.results) {
    for (const r of lastResult.results) {
      for (const nid of r.actual_path) {
        if (nodeIds.has(nid)) hitCount[nid] = (hitCount[nid] ?? 0) + 1
      }
    }
  }

  const maxHit = Math.max(0, ...Object.values(hitCount))
  const covered = Object.keys(hitCount).filter((id) => hitCount[id] > 0).length
  const total = nodeIds.size
  const pct = total > 0 ? Math.round((covered / total) * 100) : 0

  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <h4 className="text-sm font-medium text-slate-800">Coverage</h4>
      <p className="mt-1 text-2xl font-semibold text-slate-700">
        {pct}% <span className="text-sm font-normal text-slate-500">({covered}/{total} nodes)</span>
      </p>
      <ul className="mt-3 space-y-1 max-h-48 overflow-y-auto">
        {nodeList.map((n) => {
          const count = hitCount[n.id] ?? 0
          const ratio = maxHit > 0 ? count / maxHit : 0
          const intensity = count === 0 ? 'bg-slate-100' : ratio >= 0.5 ? 'bg-emerald-400' : ratio >= 0.25 ? 'bg-amber-300' : 'bg-amber-100'
          return (
            <li key={n.id} className="flex items-center gap-2 text-sm">
              <span
                className={`inline-block h-4 w-4 rounded ${intensity} flex-shrink-0`}
                title={`Hit ${count} time(s)`}
              />
              <span className="truncate text-slate-700">{n.label || n.id}</span>
              <span className="text-xs text-slate-400 flex-shrink-0">{count}×</span>
              {onHighlightNode && (
                <button
                  type="button"
                  onClick={() => onHighlightNode(n.id)}
                  className="text-xs text-clinical-blue hover:underline flex-shrink-0"
                >
                  Show
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
