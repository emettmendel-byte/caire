import type { TestSuiteResult, TestResultItem } from '../../api/tests'

interface TestResultsPanelProps {
  result: TestSuiteResult
  onClose: () => void
  onHighlightNode?: (nodeId: string) => void
}

export function TestResultsPanel({ result, onClose, onHighlightNode }: TestResultsPanelProps) {
  const failed = result.results?.filter((r) => !r.passed) ?? []

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `test-results-${result.tree_id}-${result.run_at ?? 'export'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportCsv = () => {
    const rows = [
      ['test_case_id', 'passed', 'actual_path', 'expected_path', 'actual_outcome', 'expected_outcome', 'execution_time_ms'],
      ...(result.results ?? []).map((r) => [
        r.test_case_id,
        r.passed,
        r.actual_path.join(';'),
        r.expected_path.join(';'),
        r.actual_outcome ?? '',
        r.expected_outcome ?? '',
        r.execution_time_ms,
      ]),
    ]
    const csv = rows.map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `test-results-${result.tree_id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="border-t border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <h3 className="font-medium text-slate-800">Test results</h3>
        <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
          ✕
        </button>
      </div>
      <div className="max-h-64 overflow-y-auto p-3 space-y-3">
        <div className="flex items-center gap-4">
          <span className="text-sm text-slate-600">
            {result.passed}/{result.total} passed
          </span>
          {result.run_at && <span className="text-xs text-slate-400">{result.run_at}</span>}
          <div className="flex gap-1">
            <button type="button" onClick={exportJson} className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-50">
              Export JSON
            </button>
            <button type="button" onClick={exportCsv} className="rounded border border-slate-300 px-2 py-0.5 text-xs hover:bg-slate-50">
              Export CSV
            </button>
          </div>
        </div>
        {result.breaking_changes && result.breaking_changes.length > 0 && (
          <div className="rounded border border-amber-200 bg-amber-50 p-2 text-sm text-amber-800">
            Breaking: {result.breaking_changes.join('; ')}
          </div>
        )}
        {failed.length > 0 && (
          <div>
            <h4 className="text-xs font-medium uppercase text-slate-500">Failed tests</h4>
            <ul className="mt-1 space-y-2">
              {failed.map((r) => (
                <FailedTestItem key={r.test_case_id} item={r} onHighlightNode={onHighlightNode} />
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

function FailedTestItem({
  item,
  onHighlightNode,
}: {
  item: TestResultItem
  onHighlightNode?: (nodeId: string) => void
}) {
  return (
    <li className="rounded border border-red-200 bg-red-50 p-2 text-sm text-red-900">
      <p className="font-medium">{item.test_case_id}</p>
      {item.error_message && <p className="mt-0.5 text-xs">{item.error_message}</p>}
      <div className="mt-1 grid grid-cols-2 gap-x-2 text-xs">
        <div>
          <span className="text-slate-500">Expected path:</span>
          <p className="font-mono">{item.expected_path.join(' → ') || '—'}</p>
        </div>
        <div>
          <span className="text-slate-500">Actual path:</span>
          <p className="font-mono">
            {item.actual_path.map((id) => (
              <span key={id}>
                {onHighlightNode ? (
                  <button type="button" onClick={() => onHighlightNode(id)} className="underline hover:no-underline">
                    {id}
                  </button>
                ) : (
                  id
                )}
                {id !== item.actual_path[item.actual_path.length - 1] ? ' → ' : ''}
              </span>
            ))}
            {item.actual_path.length === 0 && '—'}
          </p>
        </div>
      </div>
      {item.expected_outcome && (
        <div className="mt-1 text-xs">
          <span className="text-slate-500">Expected outcome:</span> {item.expected_outcome}
        </div>
      )}
      {item.actual_outcome != null && (
        <div className="mt-0.5 text-xs">
          <span className="text-slate-500">Actual outcome:</span> {item.actual_outcome}
        </div>
      )}
    </li>
  )
}
