/**
 * Decision tree types (mirrors backend shared/schemas for API contract).
 */

export type NodeType = 'root' | 'question' | 'condition' | 'outcome' | 'action'

export interface Edge {
  source_id: string
  target_id: string
  label?: string
  value?: unknown
}

export interface DecisionNode {
  id: string
  type: NodeType
  label: string
  description?: string
  metadata?: Record<string, unknown>
}

export interface DecisionTree {
  id: string
  version: string
  name: string
  description?: string
  nodes: DecisionNode[]
  edges: Edge[]
  root_id?: string
  metadata?: Record<string, unknown>
}

export interface TreeSummary {
  id: string
  version: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}
