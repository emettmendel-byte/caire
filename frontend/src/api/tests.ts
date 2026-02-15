/**
 * Test cases and test execution API.
 */

const API = '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export interface TestCasePayload {
  id: string
  tree_id: string
  input_values: Record<string, string | number | boolean | null>
  expected_path: string[]
  expected_outcome: string | null
  created_at?: string
}

export interface TestResultItem {
  test_case_id: string
  passed: boolean
  actual_path: string[]
  expected_path: string[]
  actual_outcome: string | null
  expected_outcome: string | null
  execution_trace: Array<{
    node_id: string
    node_label: string
    node_type: string
    condition_evaluated?: Record<string, unknown>
    next_node_id?: string
  }>
  execution_time_ms: number
  error_message?: string
}

export interface TestSuiteResult {
  tree_id: string
  total: number
  passed: number
  failed: number
  breaking_changes: string[]
  results: TestResultItem[]
  run_at?: string
}

export async function fetchTestCases(treeId: string): Promise<TestCasePayload[]> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test-cases`)
  return handleResponse<TestCasePayload[]>(res)
}

export async function createTestCase(
  treeId: string,
  body: { input_values: Record<string, string | number | boolean | null>; expected_path?: string[]; expected_outcome?: string }
): Promise<TestCasePayload> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test-cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input_values: body.input_values,
      expected_path: body.expected_path ?? [],
      expected_outcome: body.expected_outcome ?? null,
    }),
  })
  return handleResponse<TestCasePayload>(res)
}

export async function deleteTestCase(treeId: string, caseId: string): Promise<void> {
  await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test-cases/${encodeURIComponent(caseId)}`, {
    method: 'DELETE',
  })
}

export async function runSingleTest(treeId: string, caseId: string): Promise<TestResultItem> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test-cases/${encodeURIComponent(caseId)}/run`, {
    method: 'POST',
  })
  return handleResponse<TestResultItem>(res)
}

/** Run a single test with inline payload (no save). */
export async function runInlineTest(
  treeId: string,
  body: { input_values: Record<string, string | number | boolean | null>; expected_path?: string[]; expected_outcome?: string }
): Promise<TestResultItem> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test/run-inline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      input_values: body.input_values,
      expected_path: body.expected_path ?? [],
      expected_outcome: body.expected_outcome ?? null,
    }),
  })
  return handleResponse<TestResultItem>(res)
}

export async function runAllTests(treeId: string): Promise<TestSuiteResult> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test`, {
    method: 'POST',
  })
  return handleResponse<TestSuiteResult>(res)
}

export async function generateTestCases(treeId: string, count?: number): Promise<TestCasePayload[]> {
  const qs = count != null ? `?count=${count}` : ''
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/test-cases/generate${qs}`, {
    method: 'POST',
  })
  return handleResponse<TestCasePayload[]>(res)
}

export async function fetchLatestTestResults(treeId: string): Promise<TestSuiteResult | { tree_id: string; results: []; total: 0; passed: 0; failed: 0; run_at: null }> {
  const res = await fetch(`${API}/test-results/${encodeURIComponent(treeId)}`)
  return handleResponse(res)
}
