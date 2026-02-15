import { useCallback, useEffect, useState } from 'react'
import type { DecisionTree } from '../../types/decisionTree'
import { getTreeVariables, getTreeNodes } from '../../types/decisionTree'
import type { TestCasePayload, TestSuiteResult } from '../../api/tests'
import { fetchTestCases, deleteTestCase, generateTestCases, runAllTests, fetchLatestTestResults } from '../../api/tests'
import { TestCaseForm } from './TestCaseForm'
import { TestResultsPanel } from './TestResultsPanel'
import { CoverageVisualization } from './CoverageVisualization'

/** Variable names for test inputs: from tree variables or from question/condition node ids. */
function getVariableNames(tree: DecisionTree): Array<{ name: string; type: string }> {
  const vars = getTreeVariables(tree)
  if (vars.length > 0) return vars.map((v) => ({ name: v.name, type: v.type }))
  const nodes = getTreeNodes(tree)
  const nodeList = Array.isArray(nodes) ? nodes : Object.values(nodes)
  const questionLike = nodeList.filter(
    (n) => (n.type === 'question' || n.type === 'condition') && n.id
  )
  return questionLike.map((n) => ({ name: n.id, type: 'boolean' }))
}

interface TestCaseManagerProps {
  treeId: string
  tree: DecisionTree
  onHighlightNode?: (nodeId: string) => void
  onClose: () => void
}

export function TestCaseManager({ treeId, tree, onHighlightNode, onClose }: TestCaseManagerProps) {
  const [cases, setCases] = useState<TestCasePayload[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [suiteResult, setSuiteResult] = useState<TestSuiteResult | null>(null)
  const [latestResults, setLatestResults] = useState<TestSuiteResult | null>(null)
  const [showResults, setShowResults] = useState(false)
  const variables = getVariableNames(tree)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const list = await fetchTestCases(treeId)
      setCases(list)
    } catch {
      setCases([])
    } finally {
      setLoading(false)
    }
  }, [treeId])

  useEffect(() => {
    load()
  }, [load])

  const loadLatestResults = useCallback(async () => {
    try {
      const data = await fetchLatestTestResults(treeId)
      if (data && 'results' in data) setLatestResults(data as TestSuiteResult)
      else setLatestResults(null)
    } catch {
      setLatestResults(null)
    }
  }, [treeId])

  useEffect(() => {
    loadLatestResults()
  }, [loadLatestResults])

  const handleDelete = async (caseId: string) => {
    try {
      await deleteTestCase(treeId, caseId)
      setCases((prev) => prev.filter((c) => c.id !== caseId))
    } catch (e) {
      console.error(e)
    }
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const created = await generateTestCases(treeId, 10)
      setCases((prev) => [...created, ...prev])
    } catch (e) {
      console.error(e)
    } finally {
      setGenerating(false)
    }
  }

  const handleRunAll = useCallback(async () => {
    try {
      const result = await runAllTests(treeId)
      setSuiteResult(result)
      setLatestResults(result)
      setShowResults(true)
    } catch (e) {
      console.error(e)
    }
  }, [treeId])

  return (
    <div className="flex h-full flex-col border-l border-slate-200 bg-slate-50">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-3 py-2">
        <h2 className="font-medium text-slate-800">Test cases</h2>
        <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
          ✕
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <TestCaseForm treeId={treeId} variables={variables} onCreated={(tc) => setCases((prev) => [tc, ...prev])} />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {generating ? 'Generating…' : 'Generate test cases'}
          </button>
          <button
            type="button"
            onClick={handleRunAll}
            className="rounded bg-emerald-600 px-2 py-1 text-sm text-white hover:bg-emerald-700"
          >
            Run all tests
          </button>
        </div>
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <ul className="space-y-1">
            {cases.map((tc) => (
              <li key={tc.id} className="flex items-center justify-between rounded border border-slate-200 bg-white p-2 text-sm">
                <span className="truncate text-slate-700">
                  {Object.entries(tc.input_values)
                    .map(([k, v]) => `${k}=${String(v)}`)
                    .join(', ')}
                </span>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => handleDelete(tc.id)}
                    className="text-red-600 hover:text-red-800"
                    title="Delete"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <CoverageVisualization tree={tree} lastResult={latestResults} onHighlightNode={onHighlightNode} />

      {showResults && suiteResult && (
        <TestResultsPanel
          result={suiteResult}
          onClose={() => setShowResults(false)}
          onHighlightNode={onHighlightNode}
        />
      )}
    </div>
  )
}
