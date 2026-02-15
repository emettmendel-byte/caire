/**
 * Tree API: fetch, update, validate, refine. Error handling and loading-friendly.
 */

import type { DecisionTree, TreeSummary, TreeListFilters, DecisionNode } from '../types/decisionTree'

const API = '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export async function fetchTree(treeId: string): Promise<DecisionTree> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}`)
  return handleResponse<DecisionTree>(res)
}

export async function fetchAllTrees(filters?: TreeListFilters): Promise<TreeSummary[]> {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.domain) params.set('domain', filters.domain)
  const qs = params.toString()
  const url = qs ? `${API}/trees/?${qs}` : `${API}/trees/`
  const res = await fetch(url)
  return handleResponse<TreeSummary[]>(res)
}

/** Save tree (full replace). Supports DMN shape. */
export async function updateTree(treeId: string, tree: DecisionTree): Promise<DecisionTree> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tree),
  })
  return handleResponse<DecisionTree>(res)
}

export interface ValidationErrorItem {
  code: string
  message: string
  node_id?: string
  path?: string[]
}

export interface ValidateTreeResponse {
  errors: ValidationErrorItem[]
  valid: boolean
}

/** Run validation on tree (DMN shape). */
export async function validateTree(tree: DecisionTree): Promise<ValidateTreeResponse> {
  const res = await fetch(`${API}/trees/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tree),
  })
  return handleResponse<ValidateTreeResponse>(res)
}

/** Refine a node with LLM. Returns updated node. */
export async function refineNode(treeId: string, nodeId: string, instruction: string): Promise<DecisionNode> {
  const res = await fetch(`${API}/trees/${encodeURIComponent(treeId)}/nodes/refine`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId, instruction }),
  })
  return handleResponse<DecisionNode>(res)
}
