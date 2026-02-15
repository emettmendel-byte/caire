import { useState } from 'react'
import type { TestCasePayload, TestResultItem } from '../../api/tests'
import { createTestCase, runInlineTest } from '../../api/tests'

interface TestCaseFormProps {
  treeId: string
  variables: Array<{ name: string; type: string }>
  onCreated: (tc: TestCasePayload) => void
}

export function TestCaseForm({ treeId, variables, onCreated }: TestCaseFormProps) {
  const [inputValues, setInputValues] = useState<Record<string, string>>({})
  const [expectedOutcome, setExpectedOutcome] = useState('')
  const [expectedPath, setExpectedPath] = useState('')
  const [result, setResult] = useState<TestResultItem | null>(null)
  const [running, setRunning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const varList = variables.length > 0 ? variables : [{ name: 'input', type: 'string' }]

  const handleRun = async () => {
    setError(null)
    setResult(null)
    setRunning(true)
    try {
      const payload: Record<string, string | number | boolean | null> = {}
      Object.entries(inputValues).forEach(([k, v]) => {
        if (v === 'true') payload[k] = true
        else if (v === 'false') payload[k] = false
        else {
          const n = Number(v)
          payload[k] = Number.isNaN(n) ? (v || null) : n
        }
      })
      const pathList = expectedPath.trim() ? expectedPath.split(',').map((s) => s.trim()).filter(Boolean) : []
      const res = await runInlineTest(treeId, {
        input_values: payload,
        expected_path: pathList,
        expected_outcome: expectedOutcome.trim() || undefined,
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run failed')
    } finally {
      setRunning(false)
    }
  }

  const handleSave = async () => {
    setError(null)
    setSaving(true)
    try {
      const payload: Record<string, string | number | boolean | null> = {}
      Object.entries(inputValues).forEach(([k, v]) => {
        if (v === 'true') payload[k] = true
        else if (v === 'false') payload[k] = false
        else {
          const n = Number(v)
          payload[k] = Number.isNaN(n) ? (v || null) : n
        }
      })
      const pathList = expectedPath.trim() ? expectedPath.split(',').map((s) => s.trim()).filter(Boolean) : []
      const created = await createTestCase(treeId, {
        input_values: payload,
        expected_path: pathList,
        expected_outcome: expectedOutcome.trim() || undefined,
      })
      onCreated(created)
      setInputValues({})
      setExpectedOutcome('')
      setExpectedPath('')
      setResult(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <h4 className="text-sm font-medium text-slate-700">New test case</h4>
      <div className="mt-2 space-y-2">
        {varList.map((v) => (
          <div key={v.name}>
            <label className="block text-xs text-slate-500">{v.name}</label>
            <input
              type="text"
              value={inputValues[v.name] ?? ''}
              onChange={(e) => setInputValues((prev) => ({ ...prev, [v.name]: e.target.value }))}
              placeholder={v.type === 'boolean' ? 'true/false' : v.type}
              className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
        ))}
        <div>
          <label className="block text-xs text-slate-500">Expected path (node IDs, comma-separated)</label>
          <input
            type="text"
            value={expectedPath}
            onChange={(e) => setExpectedPath(e.target.value)}
            placeholder="root, node2, outcome_1"
            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500">Expected outcome</label>
          <input
            type="text"
            value={expectedOutcome}
            onChange={(e) => setExpectedOutcome(e.target.value)}
            placeholder="Recommendation text to expect"
            className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="rounded bg-clinical-blue px-2 py-1 text-sm text-white hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save test case'}
          </button>
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {running ? 'Running…' : 'Run this test'}
          </button>
        </div>
        {error && <p className="text-xs text-red-600">{error}</p>}
        {result && (
          <div className={`rounded border p-2 text-sm ${result.passed ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'}`}>
            {result.passed ? '✓ Passed' : '✗ Failed'}
            {result.actual_outcome != null && <p className="mt-1">Outcome: {result.actual_outcome}</p>}
            {result.actual_path.length > 0 && <p className="mt-0.5 text-xs">Path: {result.actual_path.join(' → ')}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
