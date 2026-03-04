/**
 * API client for CAIRE backend.
 * Uses relative /api so Vite proxy forwards to backend.
 */

import type { DecisionTree, TreeSummary } from '../types/decisionTree'

const API = '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  const json = await res.json()
  return json as T
}

export const treesApi = {
  list(): Promise<TreeSummary[]> {
    return fetch(`${API}/trees/`).then((res) => handleResponse<TreeSummary[]>(res))
  },

  get(id: string): Promise<DecisionTree> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`).then((res) => handleResponse<DecisionTree>(res))
  },

  create(tree: DecisionTree): Promise<DecisionTree> {
    return fetch(`${API}/trees/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tree),
    }).then((res) => handleResponse<DecisionTree>(res))
  },

  update(id: string, tree: DecisionTree): Promise<DecisionTree> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tree),
    }).then((res) => handleResponse<DecisionTree>(res))
  },

  delete(id: string): Promise<void> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`, { method: 'DELETE' }).then((res) => handleResponse<void>(res))
  },

  generateFromFile(file: File, options?: { name?: string; tree_id?: string }): Promise<DecisionTree> {
    const form = new FormData()
    form.append('file', file)
    if (options?.name) form.append('name', options.name)
    if (options?.tree_id) form.append('tree_id', options.tree_id)
    return fetch(`${API}/trees/generate`, { method: 'POST', body: form }).then((res) => handleResponse<DecisionTree>(res))
  },

  /** Load sample tree from models/sample_triage_v1.json into the database. */
  seedSample(): Promise<{ id: string; name: string; version: string }> {
    return fetch(`${API}/trees/seed-sample`, { method: 'POST' }).then((res) => handleResponse(res))
  },
}

export const guidelinesApi = {
  list(q?: string): Promise<Array<{ id: string; filename: string; file_path?: string; domain?: string; processed_at?: string | null; created_at: string }>> {
    const qs = q ? `?q=${encodeURIComponent(q)}` : ''
    return fetch(`${API}/guidelines/${qs}`).then((res) => handleResponse(res))
  },
  upload(
    file: File,
    domain = 'general'
  ): Promise<{ id: string; [key: string]: unknown }> {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${API}/guidelines/upload?domain=${encodeURIComponent(domain)}`, {
      method: 'POST',
      body: form,
    }).then((res) => handleResponse(res))
  },
}

export const compileApi = {
  trigger(
    guidelineId: string
  ): Promise<{ job_id: string; guideline_id: string; status: string }> {
    return fetch(`${API}/compile/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ guideline_id: guidelineId }),
    }).then((res) => handleResponse(res))
  },
  getStatus(
    jobId: string
  ): Promise<{
    job_id: string
    status: string
    result_tree_id: string | null
    error_message: string | null
    progress_message: string | null
    llm_raw_output?: string | null
    parsed_tree_snapshot?: unknown
  }> {
    return fetch(`${API}/compile/${encodeURIComponent(jobId)}/status`).then(
      (res) => handleResponse(res)
    )
  },
  getPromptPreview(
    guidelineId: string
  ): Promise<{
    guideline_id: string
    domain: string
    system_prompt: string
    user_prompt: string
  }> {
    return fetch(`${API}/compile/prompt-preview/${encodeURIComponent(guidelineId)}`).then((res) => handleResponse(res))
  },
}

export async function pollCompileJob(jobId: string, opts?: { intervalMs?: number; maxAttempts?: number }): Promise<{ result_tree_id: string }> {
  const intervalMs = opts?.intervalMs ?? 1500
  const maxAttempts = opts?.maxAttempts ?? 120
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const status = await compileApi.getStatus(jobId)
    if (status.status === 'completed' && status.result_tree_id) return { result_tree_id: status.result_tree_id }
    if (status.status === 'failed') throw new Error(status.error_message || 'Compilation failed')
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  throw new Error('Compilation timed out')
}
