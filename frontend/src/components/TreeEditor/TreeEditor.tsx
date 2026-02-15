import { useCallback, useEffect, useMemo, useState } from 'react'
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
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { fetchTree, updateTree, validateTree } from '../../api/trees'
import type { DecisionTree, DecisionNode } from '../../types/decisionTree'
import { isDmnTree, getTreeNodes, getRootId, getTreeVariables } from '../../types/decisionTree'
import { TreeNode } from '../TreeViewer/TreeNode'
import { TreeMetadata } from '../TreeViewer/TreeMetadata'
import { NodeInspector } from '../TreeViewer/NodeInspector'
import { treeToFlow, applyLayoutToTree } from './treeToFlow'
import { useTreeEditorStore } from './treeEditorStore'
import { NodeEditModal } from './NodeEditModal'
import { VariableManager } from './VariableManager'
import { ValidationPanel } from './ValidationPanel'
import { TestCaseManager } from '../Testing'

const nodeTypes = { treeNode: TreeNode }

function cloneTree(t: DecisionTree): DecisionTree {
  return JSON.parse(JSON.stringify(t))
}

function addChildToTree(tree: DecisionTree, parentId: string, label: string, type: 'condition' | 'action' | 'score'): DecisionTree {
  const next = cloneTree(tree)
  if (!isDmnTree(next)) return tree
  const nodes = next.nodes as Record<string, DecisionNode>
  const id = `node-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  nodes[id] = {
    id,
    type,
    label,
    children: [],
  }
  const parent = nodes[parentId]
  if (parent) {
    parent.children = [...(parent.children ?? []), id]
  } else {
    next.root_node_id = id
  }
  return next
}

function deleteNodeFromTree(tree: DecisionTree, nodeId: string): DecisionTree {
  const next = cloneTree(tree)
  if (!isDmnTree(next)) return tree
  const nodes = next.nodes as Record<string, DecisionNode>
  delete nodes[nodeId]
  Object.values(nodes).forEach((n) => {
    if (n.children) n.children = n.children.filter((c) => c !== nodeId)
  })
  if (next.root_node_id === nodeId) {
    const first = Object.keys(nodes)[0]
    next.root_node_id = first ?? ''
  }
  return next
}

function updateNodeInTree(tree: DecisionTree, nodeId: string, patch: Partial<DecisionNode>): DecisionTree {
  const next = cloneTree(tree)
  if (!isDmnTree(next)) return tree
  const nodes = next.nodes as Record<string, DecisionNode>
  const node = nodes[nodeId]
  if (!node) return tree
  Object.assign(node, patch)
  return next
}

interface TreeEditorProps {
  treeId: string
  onBack?: () => void
}

export function TreeEditor({ treeId, onBack }: TreeEditorProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [refresh, setRefresh] = useState(0)
  const [editMode, setEditMode] = useState(false)
  const [modalNodeId, setModalNodeId] = useState<string | null>(null)
  const [showVariables, setShowVariables] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Array<{ code: string; message: string; node_id?: string }>>([])
  const [showValidation, setShowValidation] = useState(false)
  const [showTesting, setShowTesting] = useState(false)
  const [saveAsNewVersion, setSaveAsNewVersion] = useState(false)

  const {
    tree,
    lastSavedTree,
    dirty,
    syncStatus,
    syncError,
    selectedNodeId,
    version,
    setTree,
    updateTree: updateStoreTree,
    undo,
    redo,
    markSaved,
    setSyncStatus,
    setSelectedNodeId,
    revertToLastSaved,
    canUndo,
    canRedo,
    reset,
  } = useTreeEditorStore()

  useEffect(() => {
    reset()
    return () => reset()
  }, [treeId, reset])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchTree(treeId)
      .then((t) => {
        if (cancelled) return
        setTree(t, false)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e : new Error(String(e)))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [treeId, refresh, setTree])

  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!tree) return { nodes: [], edges: [] }
    return treeToFlow(tree)
  }, [tree])

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges)

  useEffect(() => {
    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [flowNodes, flowEdges, setNodes, setEdges])

  const onNodesChangeWithLayout = useCallback(
    (changes: Parameters<typeof onNodesChange>[0]) => {
      onNodesChange(changes)
      if (!tree || !isDmnTree(tree)) return
      const dragEnd = changes.some((c) => c.type === 'position' && (c as { dragging?: boolean }).dragging === false)
      if (dragEnd) {
        setNodes((current) => {
          const withPositions = current.map((n) => {
            const ch = changes.find((c) => 'id' in c && c.id === n.id && c.type === 'position') as { position?: { x: number; y: number } } | undefined
            if (ch?.position) return { ...n, position: ch.position }
            return n
          })
          const nextTree = cloneTree(tree)
          applyLayoutToTree(nextTree, withPositions)
          updateStoreTree(nextTree)
          return withPositions
        })
      }
    },
    [tree, onNodesChange, setNodes, updateStoreTree]
  )
  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges])
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => setSelectedNodeId(node.id),
    [setSelectedNodeId]
  )

  const runValidation = useCallback(async () => {
    if (!tree) return
    try {
      const res = await validateTree(tree)
      setValidationErrors(res.errors)
      setShowValidation(true)
    } catch (e) {
      setValidationErrors([{ code: 'request', message: e instanceof Error ? e.message : 'Validation request failed' }])
      setShowValidation(true)
    }
  }, [tree])

  const handleSave = useCallback(async () => {
    if (!tree || !treeId) return
    setSyncStatus('saving')
    try {
      let toSave = tree
      if (saveAsNewVersion && tree.version) {
        const parts = tree.version.split('.')
        const last = parseInt(parts[parts.length - 1], 10)
        if (!Number.isNaN(last)) {
          parts[parts.length - 1] = String(last + 1)
          toSave = { ...cloneTree(tree), version: parts.join('.') }
        }
      }
      const saved = await updateTree(treeId, toSave)
      markSaved(saved as DecisionTree)
      setSaveAsNewVersion(false)
    } catch (e) {
      setSyncStatus('error', e instanceof Error ? e.message : 'Save failed')
    }
  }, [tree, treeId, saveAsNewVersion, markSaved, setSyncStatus])

  const handleAddChild = useCallback(() => {
    if (!tree || !isDmnTree(tree)) return
    const parentId = selectedNodeId ?? getRootId(tree) ?? ''
    const next = addChildToTree(tree, parentId || '', 'New node', 'condition')
    updateStoreTree(next)
    setSelectedNodeId(null)
  }, [tree, selectedNodeId, updateStoreTree, setSelectedNodeId])

  const handleDeleteNode = useCallback(() => {
    if (!tree || !selectedNodeId) return
    const next = deleteNodeFromTree(tree, selectedNodeId)
    updateStoreTree(next)
    setSelectedNodeId(null)
  }, [tree, selectedNodeId, updateStoreTree, setSelectedNodeId])

  const handleRevert = useCallback(() => {
    revertToLastSaved()
    setRefresh((r) => r + 1)
  }, [revertToLastSaved])

  const handleNodeUpdated = useCallback(
    (nodeId: string, updated: DecisionNode) => {
      if (!tree) return
      updateStoreTree(updateNodeInTree(tree, nodeId, updated))
      setModalNodeId(null)
    },
    [tree, updateStoreTree]
  )

  const variables = tree ? getTreeVariables(tree) : []
  const nodesMap = tree ? getTreeNodes(tree) : {}
  const nodesRecord = typeof nodesMap === 'object' && !Array.isArray(nodesMap) ? (nodesMap as Record<string, DecisionNode>) : {}
  const selectedNode = selectedNodeId ? nodesRecord[selectedNodeId] ?? null : null

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
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 bg-slate-100 text-slate-700">
        <p>{error.message}</p>
        <button
          type="button"
          onClick={() => setRefresh((r) => r + 1)}
          className="rounded border border-slate-400 bg-white px-3 py-1 text-sm hover:bg-slate-50"
        >
          Retry
        </button>
        {onBack && (
          <button type="button" onClick={onBack} className="text-sm text-slate-600 hover:underline">
            ← Back
          </button>
        )}
      </div>
    )
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
          <button type="button" onClick={onBack} className="text-sm text-slate-600 hover:text-slate-900">
            ← Back to list
          </button>
        </div>
      )}

      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-2 py-2">
        <span className="text-sm font-medium text-slate-700">Version: {version || tree.version}</span>
        <label className="flex items-center gap-1 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={saveAsNewVersion}
            onChange={(e) => setSaveAsNewVersion(e.target.checked)}
          />
          Save as new version
        </label>
        <span className="flex-1" />
        <span
          className="text-xs"
          title={syncError ?? undefined}
        >
          {syncStatus === 'saving' && 'Saving…'}
          {syncStatus === 'saved' && 'Saved'}
          {syncStatus === 'error' && `Error: ${syncError}`}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-2 py-2">
        <button
          type="button"
          onClick={() => setEditMode((e) => !e)}
          className={`rounded px-2 py-1 text-sm ${editMode ? 'bg-clinical-blue text-white' : 'bg-slate-200 text-slate-700'}`}
        >
          {editMode ? 'Edit mode' : 'View mode'}
        </button>
        <button
          type="button"
          onClick={() => setShowTesting(true)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
        >
          Tests
        </button>
        {editMode && (
          <>
            <button
              type="button"
              onClick={handleAddChild}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
            >
              Add child
            </button>
            <button
              type="button"
              onClick={handleDeleteNode}
              disabled={!selectedNodeId}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Delete node
            </button>
            <button
              type="button"
              onClick={() => selectedNodeId && setModalNodeId(selectedNodeId)}
              disabled={!selectedNodeId}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Edit node
            </button>
            <button
              type="button"
              onClick={runValidation}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
            >
              Run validation
            </button>
            <button
              type="button"
              onClick={() => setShowVariables(true)}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50"
            >
              Variables
            </button>
            <button
              type="button"
              onClick={undo}
              disabled={!canUndo()}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
            >
              Undo
            </button>
            <button
              type="button"
              onClick={redo}
              disabled={!canRedo()}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm disabled:opacity-50"
            >
              Redo
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={!dirty}
              className="rounded bg-emerald-600 px-2 py-1 text-sm text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              Save
            </button>
            <button
              type="button"
              onClick={handleRevert}
              disabled={!dirty || !lastSavedTree}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Revert
            </button>
          </>
        )}
      </div>

      <TreeMetadata tree={tree} />
      <div className="flex flex-1 min-h-0">
        <div className="flex-1 min-h-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChangeWithLayout}
            onEdgesChange={onEdgesChange}
            onConnect={editMode ? onConnect : undefined}
            onNodeClick={onNodeClick}
            nodesDraggable={editMode}
            nodesConnectable={editMode}
            elementsSelectable
            nodeTypes={nodeTypes as import('@xyflow/react').NodeTypes}
            fitView
            className="bg-clinical-paper"
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(n) =>
                n.data?.type === 'condition' ? '#0ea5e9' : n.data?.type === 'action' ? '#059669' : '#ca8a04'
              }
            />
          </ReactFlow>
        </div>
        <NodeInspector
          node={selectedNode ?? null}
          variables={variables}
          onClose={() => setSelectedNodeId(null)}
          onEdit={editMode && selectedNodeId ? () => setModalNodeId(selectedNodeId) : undefined}
        />
      </div>

      {modalNodeId && (
        <NodeEditModal
          treeId={treeId}
          node={nodesRecord[modalNodeId] ?? null}
          nodeId={modalNodeId}
          variables={variables}
          onSave={(updated) => handleNodeUpdated(modalNodeId, updated)}
          onClose={() => setModalNodeId(null)}
        />
      )}

      {showVariables && tree && isDmnTree(tree) && (
        <VariableManager
          tree={tree}
          onClose={() => setShowVariables(false)}
          onUpdate={(updatedTree) => updateStoreTree(updatedTree)}
        />
      )}

      {showValidation && (
        <ValidationPanel
          errors={validationErrors}
          onClose={() => setShowValidation(false)}
          onHighlightNode={(nodeId) => setSelectedNodeId(nodeId)}
        />
      )}

      {showTesting && tree && (
        <div className="absolute right-0 top-0 z-10 flex h-full w-96 flex-col border-l border-slate-200 bg-white shadow-lg">
          <TestCaseManager
            treeId={treeId}
            tree={tree}
            onHighlightNode={(nodeId) => setSelectedNodeId(nodeId)}
            onClose={() => setShowTesting(false)}
          />
        </div>
      )}
    </div>
  )
}
