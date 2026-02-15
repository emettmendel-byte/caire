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
  return res.json() as Promise<T>
}

export const treesApi = {
  list(): Promise<TreeSummary[]> {
    return fetch(`${API}/trees/`).then(handleResponse)
  },

  get(id: string): Promise<DecisionTree> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`).then(handleResponse)
  },

  create(tree: DecisionTree): Promise<DecisionTree> {
    return fetch(`${API}/trees/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tree),
    }).then(handleResponse)
  },

  update(id: string, tree: DecisionTree): Promise<DecisionTree> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tree),
    }).then(handleResponse)
  },

  delete(id: string): Promise<void> {
    return fetch(`${API}/trees/${encodeURIComponent(id)}`, { method: 'DELETE' }).then(handleResponse)
  },

  generateFromFile(file: File, options?: { name?: string; tree_id?: string }): Promise<DecisionTree> {
    const form = new FormData()
    form.append('file', file)
    if (options?.name) form.append('name', options.name)
    if (options?.tree_id) form.append('tree_id', options.tree_id)
    return fetch(`${API}/trees/generate`, { method: 'POST', body: form }).then(handleResponse)
  },
}
