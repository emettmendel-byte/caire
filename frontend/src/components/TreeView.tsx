import type { DecisionTree, DecisionNode, Edge } from '../types/decisionTree'
import { getTreeNodes, getRootId, isDmnTree } from '../types/decisionTree'

interface TreeViewProps {
  tree: DecisionTree
}

function NodeCard({ node }: { node: DecisionNode }) {
  return (
    <div className="node-card" data-type={node.type}>
      <span className="node-type">{node.type}</span>
      <h4>{node.label}</h4>
      {node.description && <p className="node-desc">{node.description}</p>}
    </div>
  )
}

export function TreeView({ tree }: TreeViewProps) {
  const nodesMap = getTreeNodes(tree)
  const nodeList = Array.isArray(nodesMap) ? nodesMap : Object.values(nodesMap)
  const nodeMap = new Map(nodeList.map((n: DecisionNode) => [n.id, n]))
  const edgesBySource: Record<string, Edge[]> = {}
  if (isDmnTree(tree)) {
    nodeList.forEach((n: DecisionNode) => {
      (n.children ?? []).forEach((targetId) => {
        if (!edgesBySource[n.id]) edgesBySource[n.id] = []
        edgesBySource[n.id].push({ source_id: n.id, target_id: targetId })
      })
    })
  } else {
    const edges = (tree as { edges?: Edge[] }).edges ?? []
    edges.forEach((e: Edge) => {
      if (!edgesBySource[e.source_id]) edgesBySource[e.source_id] = []
      edgesBySource[e.source_id].push(e)
    })
  }

  const rootId = getRootId(tree) ?? nodeList[0]?.id
  const root = rootId ? nodeMap.get(rootId) : null

  if (!root) return <p>No root node.</p>

  return (
    <div className="tree-view">
      <header>
        <h2>{tree.name}</h2>
        <span className="version">v{tree.version}</span>
        {tree.description && <p>{tree.description}</p>}
      </header>
      <div className="nodes">
        <NodeCard node={root} />
        {(edgesBySource[root.id] ?? []).map((edge: Edge) => {
          const target = nodeMap.get(edge.target_id)
          return target ? (
            <div key={edge.source_id + edge.target_id} className="edge-block">
              <span className="edge-label">{edge.label ?? '→'}</span>
              <NodeCard node={target} />
            </div>
          ) : null
        })}
      </div>
    </div>
  )
}
