import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { refineNode } from '../../api/trees'
import type { DecisionNode, DecisionVariable, ActionSpec } from '../../types/decisionTree'

type NodeTypeOption = 'condition' | 'action' | 'score'
const OPERATORS = ['==', '!=', '<', '>', '<=', '>=', 'contains'] as const
const URGENCY_OPTIONS = ['routine', 'urgent', 'emergency', 'deferred', 'other'] as const
const EVIDENCE_GRADES = ['A', 'B', 'C', 'D'] as const

interface FormValues {
  label: string
  type: NodeTypeOption
  variable: string
  operator: string
  threshold: string
  recommendation: string
  urgency_level: string
  source_guideline_section: string
  evidence_grade: string
}

interface NodeEditModalProps {
  treeId: string
  node: DecisionNode | null
  nodeId: string
  variables: DecisionVariable[]
  onSave: (updated: DecisionNode) => void
  onClose: () => void
}

export function NodeEditModal({ treeId, node, nodeId, variables, onSave, onClose }: NodeEditModalProps) {
  const [suggesting, setSuggesting] = useState(false)
  const [suggestError, setSuggestError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      label: '',
      type: 'condition',
      variable: '',
      operator: '==',
      threshold: '',
      recommendation: '',
      urgency_level: 'routine',
      source_guideline_section: '',
      evidence_grade: '',
    },
  })

  const nodeType = watch('type')

  useEffect(() => {
    if (!node) return
    reset({
      label: node.label ?? '',
      type: (node.type as NodeTypeOption) ?? 'condition',
      variable: node.condition?.variable ?? '',
      operator: node.condition?.operator ?? '==',
      threshold: node.condition?.threshold != null ? String(node.condition.threshold) : '',
      recommendation: node.action?.recommendation ?? '',
      urgency_level: node.action?.urgency_level ?? 'routine',
      source_guideline_section: (node.metadata?.source_guideline_section as string) ?? '',
      evidence_grade: (node.metadata?.evidence_grade as string) ?? '',
    })
  }, [node, reset])

  const onSubmit = (data: FormValues) => {
    const updated: DecisionNode = {
      ...node!,
      id: nodeId,
      label: data.label,
      type: data.type,
      condition:
        data.type === 'condition'
          ? {
              variable: data.variable,
              operator: data.operator,
              threshold: data.threshold ? (Number(data.threshold) || data.threshold) : undefined,
            }
          : undefined,
      action:
        data.type === 'action'
          ? {
              recommendation: data.recommendation,
              urgency_level: data.urgency_level as ActionSpec['urgency_level'],
            }
          : undefined,
      metadata: {
        ...node?.metadata,
        source_guideline_section: data.source_guideline_section || undefined,
        evidence_grade: data.evidence_grade || undefined,
      },
    }
    onSave(updated)
  }

  const handleSuggest = async () => {
    setSuggestError(null)
    setSuggesting(true)
    try {
      const instruction = 'Suggest concise improvements for clarity and clinical accuracy. Return only the improved node fields (label, condition, action, metadata) where relevant.'
      const refined = await refineNode(treeId, nodeId, instruction)
      if (refined.label) setValue('label', refined.label)
      if (refined.condition) {
        setValue('variable', refined.condition.variable)
        setValue('operator', refined.condition.operator)
        setValue('threshold', refined.condition.threshold != null ? String(refined.condition.threshold) : '')
      }
      if (refined.action) {
        setValue('recommendation', refined.action.recommendation)
        setValue('urgency_level', refined.action.urgency_level ?? 'routine')
      }
      if (refined.metadata) {
        setValue('source_guideline_section', (refined.metadata.source_guideline_section as string) ?? '')
        setValue('evidence_grade', (refined.metadata.evidence_grade as string) ?? '')
      }
    } catch (e) {
      setSuggestError(e instanceof Error ? e.message : 'Suggest failed')
    } finally {
      setSuggesting(false)
    }
  }

  if (!node) return null

  const variableNames = variables.map((v) => v.name)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <h2 className="text-lg font-semibold text-slate-800">Edit node</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Label</label>
            <input
              {...register('label', { required: 'Label is required' })}
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            />
            {errors.label && <p className="mt-0.5 text-xs text-red-600">{errors.label.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Type</label>
            <select {...register('type')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
              <option value="condition">condition</option>
              <option value="action">action</option>
              <option value="score">score</option>
            </select>
          </div>

          {nodeType === 'condition' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700">Variable</label>
                <input
                  {...register('variable')}
                  list="variable-list"
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
                <datalist id="variable-list">
                  {variableNames.map((name) => (
                    <option key={name} value={name} />
                  ))}
                </datalist>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Operator</label>
                <select {...register('operator')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  {OPERATORS.map((op) => (
                    <option key={op} value={op}>{op}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Threshold</label>
                <input
                  {...register('threshold')}
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
              </div>
            </>
          )}

          {nodeType === 'action' && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700">Recommendation</label>
                <textarea
                  {...register('recommendation')}
                  rows={3}
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700">Urgency</label>
                <select {...register('urgency_level')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  {URGENCY_OPTIONS.map((u) => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className="border-t border-slate-200 pt-2">
            <div className="text-xs font-medium uppercase text-slate-500">Metadata</div>
            <div className="mt-2 space-y-2">
              <div>
                <label className="block text-sm text-slate-600">Source guideline section</label>
                <input
                  {...register('source_guideline_section')}
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-600">Evidence grade</label>
                <select {...register('evidence_grade')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5 text-sm">
                  <option value="">—</option>
                  {EVIDENCE_GRADES.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={handleSuggest}
              disabled={suggesting}
              className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {suggesting ? 'Suggesting…' : 'Suggest improvements'}
            </button>
            {suggestError && <p className="text-xs text-red-600">{suggestError}</p>}
            <span className="flex-1" />
            <button type="button" onClick={onClose} className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-clinical-blue px-3 py-1.5 text-sm text-white hover:opacity-90"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
