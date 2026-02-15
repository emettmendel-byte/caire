import type { DecisionNode, DecisionVariable } from '../../types/decisionTree'

interface NodeInspectorProps {
  node: DecisionNode | null
  variables: DecisionVariable[]
  onClose: () => void
  onEdit?: () => void
}

export function NodeInspector({ node, variables, onClose, onEdit }: NodeInspectorProps) {
  if (!node) {
    return (
      <aside className="flex w-80 flex-shrink-0 flex-col border-l border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-slate-700">Node details</h3>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
            ✕
          </button>
        </div>
        <p className="mt-4 text-sm text-slate-500">Select a node to inspect.</p>
      </aside>
    )
  }

  const varInfo = variables.find((v) => v.name === node.condition?.variable)
  const meta = node.metadata ?? {}
  const terminology = (meta.terminology_mapping as Record<string, unknown>) ?? varInfo?.terminology_mapping ?? {}
  const section = (meta.source_guideline_section as string) ?? ''
  const evidenceGrade = (meta.evidence_grade as string) ?? ''

  return (
    <aside className="flex w-80 flex-shrink-0 flex-col border-l border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-slate-700">Node details</h3>
        <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
          ✕
        </button>
      </div>

      <div className="mt-4 space-y-4 text-sm">
        <div>
          <div className="text-xs font-medium uppercase text-slate-500">Type</div>
          <p className="mt-0.5 font-medium text-slate-800">{node.type}</p>
        </div>
        <div>
          <div className="text-xs font-medium uppercase text-slate-500">Label</div>
          <p className="mt-0.5 text-slate-800">{node.label}</p>
        </div>

        {node.condition && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Condition</div>
            <p className="mt-0.5 font-mono text-slate-800">
              {node.condition.variable} {node.condition.operator} {String(node.condition.threshold ?? '')}
              {node.condition.unit ? ` ${node.condition.unit}` : ''}
            </p>
          </div>
        )}

        {node.action && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Recommendation</div>
            <p className="mt-0.5 text-slate-800">{node.action.recommendation}</p>
            {node.action.urgency_level && (
              <p className="mt-1 text-xs text-slate-600">Urgency: {node.action.urgency_level}</p>
            )}
          </div>
        )}

        {Object.keys(terminology).length > 0 && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Terminology</div>
            <ul className="mt-1 list-inside list-disc space-y-0.5 text-slate-700">
              {Object.entries(terminology).map(([sys, codes]) => (
                <li key={sys}>
                  {sys}: {Array.isArray(codes) ? codes.join(', ') : String(codes)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {section && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Source section</div>
            <p className="mt-0.5 text-slate-700">{section}</p>
          </div>
        )}

        {evidenceGrade && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Evidence grade</div>
            <p className="mt-0.5 text-slate-700">{evidenceGrade}</p>
          </div>
        )}

        {node.children && node.children.length > 0 && (
          <div>
            <div className="text-xs font-medium uppercase text-slate-500">Child nodes</div>
            <ul className="mt-1 list-inside list-disc text-slate-700">
              {node.children.map((id) => (
                <li key={id}>{id}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {onEdit && (
        <div className="mt-6 border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm hover:bg-slate-50"
          >
            Edit (placeholder)
          </button>
        </div>
      )}
    </aside>
  )
}
