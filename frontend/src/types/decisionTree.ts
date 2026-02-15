/**
 * Decision tree types: supports both DMN (compiler) and legacy list+edges shapes.
 */

export type NodeType = 'root' | 'question' | 'condition' | 'outcome' | 'action' | 'score'

export interface Edge {
  source_id: string
  target_id: string
  label?: string
  value?: unknown
}

export interface ConditionSpec {
  variable: string
  operator: string
  threshold?: number | string | boolean
  unit?: string
}

export interface ActionSpec {
  recommendation: string
  urgency_level?: 'emergency' | 'urgent' | 'routine' | 'deferred' | 'other'
  code?: string
}

export interface DecisionNode {
  id: string
  type: NodeType
  label: string
  description?: string
  condition?: ConditionSpec
  action?: ActionSpec
  score_expression?: string
  children?: string[]
  metadata?: Record<string, unknown>
}

/** Legacy: nodes as array */
export interface DecisionTreeLegacy {
  id: string
  version: string
  name: string
  description?: string
  nodes: DecisionNode[]
  edges: Edge[]
  root_id?: string
  metadata?: Record<string, unknown>
}

/** DMN: nodes as record, root_node_id, variables */
export interface DecisionVariable {
  name: string
  type: 'numeric' | 'boolean' | 'categorical'
  units?: string
  terminology_mapping?: Record<string, string | string[]>
  source?: string
  description?: string
}

export interface DecisionTreeDmn {
  id: string
  version: string
  name: string
  description?: string
  domain: string
  root_node_id: string
  nodes: Record<string, DecisionNode>
  variables: DecisionVariable[]
  metadata?: Record<string, unknown>
}

export type DecisionTree = DecisionTreeLegacy | DecisionTreeDmn

export function isDmnTree(tree: DecisionTree): tree is DecisionTreeDmn {
  return 'root_node_id' in tree && typeof (tree as DecisionTreeDmn).nodes === 'object' && !Array.isArray((tree as DecisionTreeDmn).nodes)
}

export function getTreeNodes(tree: DecisionTree): Record<string, DecisionNode> | DecisionNode[] {
  if (isDmnTree(tree)) return tree.nodes
  const byId: Record<string, DecisionNode> = {}
  for (const n of (tree as DecisionTreeLegacy).nodes) byId[n.id] = n
  return byId
}

export function getRootId(tree: DecisionTree): string | undefined {
  if (isDmnTree(tree)) return tree.root_node_id
  return (tree as DecisionTreeLegacy).root_id
}

export function getTreeVariables(tree: DecisionTree): DecisionVariable[] {
  if (isDmnTree(tree)) return tree.variables ?? []
  return []
}

export interface TreeSummary {
  id: string
  version: string
  name: string
  description?: string
  status?: string
  domain?: string
  created_at: string
  updated_at: string
}

export interface TreeListFilters {
  status?: string
  domain?: string
}
