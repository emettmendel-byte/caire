import { useMemo, useState } from 'react'
import type { DecisionTreeDmn, DecisionVariable } from '../../types/decisionTree'

function collectVariableUsage(tree: DecisionTreeDmn): Set<string> {
  const used = new Set<string>()
  Object.values(tree.nodes).forEach((node) => {
    const v = node.condition?.variable
    if (v) used.add(v)
  })
  return used
}

interface VariableManagerProps {
  tree: DecisionTreeDmn
  onClose: () => void
  onUpdate: (updated: DecisionTreeDmn) => void
}

export function VariableManager({ tree, onClose, onUpdate }: VariableManagerProps) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState<'numeric' | 'boolean' | 'categorical'>('numeric')
  const [newUnits, setNewUnits] = useState('')
  const [newSource, setNewSource] = useState('')

  const variables = tree.variables ?? []
  const used = useMemo(() => collectVariableUsage(tree), [tree])

  const handleAdd = () => {
    const name = newName.trim()
    if (!name) return
    if (variables.some((v) => v.name === name)) return
    const next: DecisionVariable = {
      name,
      type: newType,
      units: newUnits.trim() || undefined,
      source: newSource.trim() || undefined,
    }
    onUpdate({
      ...tree,
      variables: [...variables, next],
    })
    setNewName('')
    setNewUnits('')
    setNewSource('')
  }

  const handleUpdate = (index: number, patch: Partial<DecisionVariable>) => {
    const next = [...variables]
    next[index] = { ...next[index], ...patch }
    onUpdate({ ...tree, variables: next })
    setEditingId(null)
  }

  const handleDelete = (v: DecisionVariable) => {
    if (used.has(v.name)) {
      if (!window.confirm(`Variable "${v.name}" is used in the tree. Remove anyway?`)) return
    }
    onUpdate({
      ...tree,
      variables: variables.filter((x) => x.name !== v.name),
    })
    setEditingId(null)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg border border-slate-200 bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <h2 className="text-lg font-semibold text-slate-800">Variables</h2>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-700">
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2 rounded border border-slate-200 bg-slate-50 p-2">
            <input
              placeholder="Name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <select
              value={newType}
              onChange={(e) => setNewType(e.target.value as 'numeric' | 'boolean' | 'categorical')}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
            >
              <option value="numeric">numeric</option>
              <option value="boolean">boolean</option>
              <option value="categorical">categorical</option>
            </select>
            <input
              placeholder="Units"
              value={newUnits}
              onChange={(e) => setNewUnits(e.target.value)}
              className="w-24 rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <input
              placeholder="Source"
              value={newSource}
              onChange={(e) => setNewSource(e.target.value)}
              className="w-32 rounded border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              type="button"
              onClick={handleAdd}
              disabled={!newName.trim()}
              className="rounded bg-clinical-blue px-2 py-1 text-sm text-white hover:opacity-90 disabled:opacity-50"
            >
              Add
            </button>
          </div>

          <ul className="space-y-2">
            {variables.map((v, index) => (
              <li
                key={v.name}
                className="flex items-center gap-2 rounded border border-slate-200 bg-white p-2 text-sm"
              >
                {editingId === v.name ? (
                  <>
                    <input
                      defaultValue={v.name}
                      onBlur={(e) => handleUpdate(index, { name: e.target.value.trim() || v.name })}
                      className="flex-1 rounded border border-slate-300 px-2 py-0.5"
                    />
                    <select
                      defaultValue={v.type}
                      onChange={(e) => handleUpdate(index, { type: e.target.value as DecisionVariable['type'] })}
                      className="rounded border border-slate-300 px-2 py-0.5"
                    >
                      <option value="numeric">numeric</option>
                      <option value="boolean">boolean</option>
                      <option value="categorical">categorical</option>
                    </select>
                    <input
                      defaultValue={v.units}
                      onBlur={(e) => handleUpdate(index, { units: e.target.value.trim() || undefined })}
                      placeholder="Units"
                      className="w-20 rounded border border-slate-300 px-2 py-0.5"
                    />
                    <input
                      defaultValue={v.source}
                      onBlur={(e) => handleUpdate(index, { source: e.target.value.trim() || undefined })}
                      placeholder="Source"
                      className="w-24 rounded border border-slate-300 px-2 py-0.5"
                    />
                    <button type="button" onClick={() => setEditingId(null)} className="text-slate-500">
                      Done
                    </button>
                  </>
                ) : (
                  <>
                    <span className="font-medium text-slate-800">{v.name}</span>
                    <span className="text-slate-500">{v.type}</span>
                    {v.units && <span className="text-slate-500">{v.units}</span>}
                    {v.source && <span className="text-slate-500">{v.source}</span>}
                    {used.has(v.name) && <span className="text-xs text-amber-600">in use</span>}
                    <span className="flex-1" />
                    <button
                      type="button"
                      onClick={() => setEditingId(v.name)}
                      className="text-slate-600 hover:text-slate-800"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(v)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
