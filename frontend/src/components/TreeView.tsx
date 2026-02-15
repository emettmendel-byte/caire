import type { DecisionTree, DecisionNode, Edge } from '../types/decisionTree'

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
  const nodeMap = new Map(tree.nodes.map((n) => [n.id, n]))
  const edgesBySource = tree.edges.reduce<Record<string, Edge[]>>((acc, e) => {
    if (!acc[e.source_id]) acc[e.source_id] = []
    acc[e.source_id].push(e)
    return acc
  }, {})

  const rootId = tree.root_id ?? tree.nodes[0]?.id
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
        {(edgesBySource[root.id] ?? []).map((edge) => {
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
