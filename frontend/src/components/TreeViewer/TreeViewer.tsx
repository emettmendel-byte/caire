import { useCallback, useEffect, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Connection,
  type Node,
  type Edge,
} from '@xyflow/react'
import type { TreeNodeData } from './TreeNode'
import '@xyflow/react/dist/style.css'
import { fetchTree } from '../../api/trees'
import type { DecisionTree, DecisionNode } from '../../types/decisionTree'
import { isDmnTree, getTreeNodes, getRootId, getTreeVariables } from '../../types/decisionTree'
import { TreeNode, nodeToData } from './TreeNode'
import { TreeMetadata } from './TreeMetadata'
import { NodeInspector } from './NodeInspector'
import { TreeViewerError } from './TreeViewerError'

const nodeTypes = { treeNode: TreeNode }

function treeToFlow(tree: DecisionTree): { nodes: Node[]; edges: Edge[] } {
  const nodesMap = getTreeNodes(tree)
  const rootId = getRootId(tree)
  const byId = Array.isArray(nodesMap)
    ? Object.fromEntries((nodesMap as DecisionNode[]).map((n) => [n.id, n]))
    : (nodesMap as Record<string, DecisionNode>)
  const isLegacy = !isDmnTree(tree)
  const legacyEdges = isLegacy ? ((tree as { edges?: { source_id: string; target_id: string }[] }).edges ?? []) : []

  const positions = new Map<string, { x: number; y: number }>()
  const width = 240
  const height = 100

  if (rootId && byId[rootId]) {
    const queue: { id: string; depth: number; index: number }[] = [{ id: rootId, depth: 0, index: 0 }]
    const seen = new Set<string>()
    while (queue.length > 0) {
      const { id, depth, index } = queue.shift()!
      if (seen.has(id)) continue
      seen.add(id)
      positions.set(id, { x: index * width, y: depth * height })
      const node = byId[id]
      const kids = node?.children ?? legacyEdges.filter((e) => e.source_id === id).map((e) => e.target_id)
      kids.forEach((kid, i) => queue.push({ id: kid, depth: depth + 1, index: index * 2 + i }))
    }
  }
  if (positions.size === 0) {
    Object.keys(byId).forEach((id, i) => positions.set(id, { x: i * width, y: 0 }))
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
    legacyEdges.forEach((e) => edges.push({ id: `${e.source_id}-${e.target_id}`, source: e.source_id, target: e.target_id }))
  } else {
    positions.forEach((_, id) => {
      const node = byId[id]
      ;(node?.children ?? []).forEach((target) => edges.push({ id: `${id}-${target}`, source: id, target }))
    })
  }

  return { nodes, edges }
}

interface TreeViewerProps {
  treeId: string
  onBack?: () => void
}

export function TreeViewer({ treeId, onBack }: TreeViewerProps) {
  const [tree, setTree] = useState<DecisionTree | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<TreeNodeData>>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [refresh, setRefresh] = useState(0)

  const handleRetry = useCallback(() => {
    setError(null)
    setRefresh((r) => r + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchTree(treeId)
      .then((t) => {
        if (cancelled) return
        setTree(t)
        const { nodes: n, edges: e } = treeToFlow(t)
        setNodes(n as Node<TreeNodeData>[])
        setEdges(e)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e : new Error(String(e)))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [treeId, refresh, setNodes, setEdges])

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges])
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => setSelectedNodeId(node.id), [])
  const variables = tree ? getTreeVariables(tree) : []
  const nodesMap = tree ? getTreeNodes(tree) : {}
  const selectedNode = selectedNodeId && typeof nodesMap === 'object' && !Array.isArray(nodesMap)
    ? (nodesMap as Record<string, DecisionNode>)[selectedNodeId]
    : null

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-100">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-clinical-blue border-t-transparent" />
          <p className="mt-2 text-sm text-slate-600">Loading tree…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return <TreeViewerError error={error} onRetry={handleRetry} onBack={onBack} />
  }

  if (!tree) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-100 text-slate-600">
        No tree data.
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-slate-100">
      {onBack && (
        <div className="border-b border-slate-200 bg-white px-2 py-1">
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-slate-600 hover:text-slate-900"
          >
            ← Back to list
          </button>
        </div>
      )}
      <TreeMetadata tree={tree} />
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 min-h-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes as import('@xyflow/react').NodeTypes}
            fitView
            className="bg-clinical-paper"
          >
            <Background />
            <Controls />
            <MiniMap nodeColor={(n) => (n.data?.type === 'condition' ? '#0ea5e9' : n.data?.type === 'action' ? '#059669' : '#ca8a04')} />
          </ReactFlow>
        </div>
        <NodeInspector
          node={selectedNode ?? null}
          variables={variables}
          onClose={() => setSelectedNodeId(null)}
          onEdit={undefined}
        />
      </div>
    </div>
  )
}
