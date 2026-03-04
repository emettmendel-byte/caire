import { useCallback, useEffect, useMemo, useState } from 'react'
import { TreeList } from '../TreeList'
import { treesApi } from '../../api/client'
import type { DecisionTree } from '../../types/decisionTree'
import { TestCaseManager } from '../Testing'
import { runInlineTest } from '../../api/tests'
import { SplitPane } from '../Layout/SplitPane'

interface TestingSectionProps {
  selectedTreeId: string | null
  onSelectTree: (id: string) => void
}

export function TestingSection({ selectedTreeId, onSelectTree }: TestingSectionProps) {
  const [tree, setTree] = useState<DecisionTree | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [inputJson, setInputJson] = useState<string>('{\n  \n}')
  const [runBusy, setRunBusy] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<{
    actual_outcome: string | null
    actual_path: string[]
    execution_time_ms: number
  } | null>(null)

  const effectiveTreeId = selectedTreeId && selectedTreeId.length > 0 ? selectedTreeId : null

  useEffect(() => {
    if (!effectiveTreeId) {
      setTree(null)
      return
    }
    setLoading(true)
    setError(null)
    treesApi
      .get(effectiveTreeId)
      .then((t) => setTree(t))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [effectiveTreeId])

  const parsedInput = useMemo(() => {
    try {
      const v = JSON.parse(inputJson)
      if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>
      return null
    } catch {
      return null
    }
  }, [inputJson])

  const handleRun = useCallback(async () => {
    if (!effectiveTreeId) return
    setRunBusy(true)
    setRunError(null)
    setRunResult(null)
    try {
      const obj = parsedInput
      if (!obj) throw new Error('Input must be a JSON object (e.g. {"age": 42, "fever": true}).')
      const res = await runInlineTest(effectiveTreeId, {
        input_values: obj as Record<string, string | number | boolean | null>,
      })
      setRunResult({
        actual_outcome: res.actual_outcome ?? null,
        actual_path: res.actual_path ?? [],
        execution_time_ms: res.execution_time_ms ?? 0,
      })
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunBusy(false)
    }
  }, [effectiveTreeId, parsedInput])

  return (
    <div className="section">
      <SplitPane
        storageKey="split:test"
        minLeftPx={260}
        minRightPx={560}
        initialLeftPx={300}
        left={(
          <aside className="sidebar">
            <h2>Tests</h2>
            <TreeList onSelect={onSelectTree} />
          </aside>
        )}
        right={(
          <section className="content">
            {!effectiveTreeId ? (
              <div className="content-pad">
                <p className="hint">Select a tree to test.</p>
              </div>
            ) : loading ? (
              <div className="content-pad">
                <p className="loading">Loading tree…</p>
              </div>
            ) : error ? (
              <div className="content-pad">
                <p className="error">{error}</p>
              </div>
            ) : !tree ? (
              <div className="content-pad">
                <p className="hint">No tree loaded.</p>
              </div>
            ) : (
              <div className="test-layout">
                <div className="card">
                  <h3>Quick run</h3>
                  <p className="hint">Provide `input_values` as JSON and run through the tree.</p>
                  <textarea
                    className="json"
                    value={inputJson}
                    onChange={(e) => setInputJson(e.target.value)}
                    rows={10}
                    spellCheck={false}
                  />
                  <div className="row">
                    <button type="button" className="btn-primary" disabled={runBusy} onClick={handleRun}>
                      {runBusy ? 'Running…' : 'Run'}
                    </button>
                  </div>
                  {runError && <p className="error">{runError}</p>}
                  {runResult && (
                    <div className="result">
                      <div><strong>Outcome:</strong> {runResult.actual_outcome ?? '(none)'}</div>
                      <div><strong>Path:</strong> {runResult.actual_path.join(' → ') || '(empty)'}</div>
                      <div><strong>Time:</strong> {runResult.execution_time_ms} ms</div>
                    </div>
                  )}
                </div>

                <div className="card">
                  <h3>Test cases</h3>
                  <TestCaseManager
                    treeId={effectiveTreeId}
                    tree={tree}
                    onHighlightNode={() => {}}
                    onClose={() => {}}
                  />
                </div>
              </div>
            )}
          </section>
        )}
      />
    </div>
  )
}

