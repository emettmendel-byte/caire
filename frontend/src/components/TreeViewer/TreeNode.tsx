import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { DecisionNode } from '../../types/decisionTree'

export interface TreeNodeData extends Record<string, unknown> {
  label: string
  type: string
  condition?: { variable: string; operator: string; threshold?: unknown }
  action?: { recommendation: string; urgency_level?: string }
  score_expression?: string
}

const typeStyles: Record<string, string> = {
  condition: 'border-clinical-blue bg-sky-50 text-slate-800',
  action: 'border-emerald-500 bg-emerald-50 text-slate-800',
  score: 'border-amber-500 bg-amber-50 text-slate-800',
  root: 'border-slate-400 bg-slate-100 text-slate-800',
  question: 'border-clinical-blue bg-sky-50 text-slate-800',
  outcome: 'border-emerald-500 bg-emerald-50 text-slate-800',
}

function TreeNodeComponent(props: NodeProps) {
  const { data, selected } = props
  const d = (data ?? {}) as TreeNodeData
  const style = typeStyles[d.type] ?? 'border-slate-300 bg-white text-slate-800'
  const conditionLabel = d.condition
    ? `${d.condition.variable} ${d.condition.operator} ${d.condition.threshold ?? ''}`.trim()
    : null

  return (
    <div
      className={`min-w-[160px] max-w-[240px] rounded-lg border-2 px-3 py-2 shadow-sm ${style} ${selected ? 'ring-2 ring-blue-400 ring-offset-1' : ''}`}
      title={conditionLabel ?? undefined}
    >
      <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-2 !border-slate-400 !bg-white" />
      <div className="text-xs font-medium uppercase tracking-wide opacity-80">{d.type}</div>
      <div className="mt-0.5 line-clamp-3 text-sm font-medium">{d.label}</div>
      {conditionLabel && (
        <div className="mt-1 truncate text-xs text-slate-500" title={conditionLabel}>
          {conditionLabel}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-2 !border-slate-400 !bg-white" />
    </div>
  )
}

export const TreeNode = memo(TreeNodeComponent)

export function nodeToData(node: DecisionNode): TreeNodeData {
  return {
    label: node.label,
    type: node.type,
    condition: node.condition,
    action: node.action,
    score_expression: node.score_expression,
  }
}
