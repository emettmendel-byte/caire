/**
 * Convert DecisionTree to React Flow nodes/edges. Supports optional layout in tree.metadata.layout.
 */

import type { Node, Edge } from '@xyflow/react'
import type { DecisionTree, DecisionNode } from '../../types/decisionTree'
import { getTreeNodes, getRootId, isDmnTree } from '../../types/decisionTree'
import type { TreeNodeData } from '../TreeViewer/TreeNode'
import { nodeToData } from '../TreeViewer/TreeNode'

const DEFAULT_WIDTH = 240
const DEFAULT_HEIGHT = 100

export type LayoutMap = Record<string, { x: number; y: number }>

function getStoredLayout(tree: DecisionTree): LayoutMap | undefined {
  const meta = tree.metadata as Record<string, unknown> | undefined
  return meta?.layout as LayoutMap | undefined
}

export function treeToFlow(tree: DecisionTree): { nodes: Node[]; edges: Edge[] } {
  const nodesMap = getTreeNodes(tree)
  const rootId = getRootId(tree)
  const byId: Record<string, DecisionNode> = Array.isArray(nodesMap)
    ? Object.fromEntries((nodesMap as DecisionNode[]).map((n) => [n.id, n]))
    : (nodesMap as Record<string, DecisionNode>)
  const isLegacy = !isDmnTree(tree)
  const legacyEdges = isLegacy
    ? ((tree as { edges?: { source_id: string; target_id: string }[] }).edges ?? [])
    : []
  const layout = getStoredLayout(tree)

  const positions = new Map<string, { x: number; y: number }>()

  if (rootId && byId[rootId]) {
    const queue: { id: string; depth: number; index: number }[] = [{ id: rootId, depth: 0, index: 0 }]
    const seen = new Set<string>()
    while (queue.length > 0) {
      const { id, depth, index } = queue.shift()!
      if (seen.has(id)) continue
      seen.add(id)
      const stored = layout?.[id]
      positions.set(id, stored ?? { x: index * DEFAULT_WIDTH, y: depth * DEFAULT_HEIGHT })
      const node = byId[id]
      const kids =
        node?.children ??
        legacyEdges.filter((e) => e.source_id === id).map((e) => e.target_id)
      kids.forEach((kid, i) => queue.push({ id: kid, depth: depth + 1, index: index * 2 + i }))
    }
  }
  if (positions.size === 0) {
    Object.keys(byId).forEach((id, i) => {
      const stored = layout?.[id]
      positions.set(id, stored ?? { x: i * DEFAULT_WIDTH, y: 0 })
    })
  }

  const nodes: Node[] = []
  const edges: Edge[] = []
  positions.forEach((pos, id) => {
    const node = byId[id]
    if (!node) return
    nodes.push({
      id,
      type: 'treeNode',
      position: { x: pos.x, y: pos.y },
      data: nodeToData(node) as TreeNodeData & Record<string, unknown>,
    })
  })
  if (isLegacy) {
    legacyEdges.forEach((e) =>
      edges.push({ id: `${e.source_id}-${e.target_id}`, source: e.source_id, target: e.target_id })
    )
  } else {
    positions.forEach((_, id) => {
      const node = byId[id]
      ;(node?.children ?? []).forEach((target) =>
        edges.push({ id: `${id}-${target}`, source: id, target })
      )
    })
  }

  return { nodes, edges }
}

/** Apply flow node positions back to tree.metadata.layout (mutates tree). */
export function applyLayoutToTree(
  tree: DecisionTree,
  flowNodes: { id: string; position: { x: number; y: number } }[]
): void {
  const meta = (tree.metadata ?? {}) as Record<string, unknown>
  const layout: LayoutMap = (meta.layout as LayoutMap) ?? {}
  flowNodes.forEach((n) => {
    layout[n.id] = { x: n.position.x, y: n.position.y }
  })
  meta.layout = layout
  tree.metadata = meta
}
