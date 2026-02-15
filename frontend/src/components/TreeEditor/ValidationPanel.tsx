import type { ValidationErrorItem } from '../../api/trees'

type Severity = 'error' | 'warning' | 'info'

function inferSeverity(err: ValidationErrorItem): Severity {
  const c = (err.code ?? '').toLowerCase()
  if (c.includes('missing') || c.includes('cycle') || c.includes('invalid')) return 'error'
  if (c.includes('warn')) return 'warning'
  return 'info'
}

const severityStyles: Record<Severity, string> = {
  error: 'border-red-200 bg-red-50 text-red-800',
  warning: 'border-amber-200 bg-amber-50 text-amber-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
}

interface ValidationPanelProps {
  errors: Array<{ code: string; message: string; node_id?: string }>
  onClose: () => void
  onHighlightNode: (nodeId: string) => void
  onFixAuto?: (error: ValidationErrorItem) => void
}

export function ValidationPanel({ errors, onClose, onHighlightNode, onFixAuto }: ValidationPanelProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <h2 className="text-lg font-semibold text-slate-800">Validation</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
            ✕
          </button>
        </div>

        {errors.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">No issues found.</p>
        ) : (
          <ul className="mt-4 space-y-2">
            {errors.map((err, i) => {
              const severity = inferSeverity(err as ValidationErrorItem)
              const style = severityStyles[severity]
              return (
                <li
                  key={i}
                  className={`flex items-start gap-2 rounded border p-2 text-sm ${style}`}
                >
                  <span className="flex-1">
                    <span className="font-medium">{err.code}</span>
                    {err.node_id && (
                      <button
                        type="button"
                        onClick={() => err.node_id && onHighlightNode(err.node_id)}
                        className="ml-1 text-xs underline hover:no-underline"
                      >
                        #{err.node_id}
                      </button>
                    )}
                    <p className="mt-0.5">{err.message}</p>
                  </span>
                  {onFixAuto && (
                    <button
                      type="button"
                      onClick={() => onFixAuto(err as ValidationErrorItem)}
                      className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs hover:bg-slate-50"
                    >
                      Fix
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
