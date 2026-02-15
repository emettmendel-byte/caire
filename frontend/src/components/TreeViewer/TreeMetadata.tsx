import type { DecisionTree } from '../../types/decisionTree'
import { isDmnTree } from '../../types/decisionTree'

interface TreeMetadataProps {
  tree: DecisionTree
  testSummary?: { passed: number; failed: number }
}

const statusBadgeClass: Record<string, string> = {
  draft: 'bg-slate-200 text-slate-800',
  under_review: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  published: 'bg-emerald-100 text-emerald-800',
}

export function TreeMetadata({ tree, testSummary }: TreeMetadataProps) {
  const status = (tree.metadata as { approval_status?: string })?.approval_status ?? (tree as { status?: string }).status ?? 'draft'
  const domain = isDmnTree(tree) ? tree.domain : undefined
  const created = (tree.metadata as { created_date?: string })?.created_date
  const authors = (tree.metadata as { authors?: string[] })?.authors ?? []

  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-slate-900">{tree.name}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600">
          <span>v{tree.version}</span>
          {domain && <span>{domain.replace(/_/g, ' ')}</span>}
          {created && <span>Created {typeof created === 'string' ? created : (created as Date)?.toString?.()}</span>}
          {authors.length > 0 && <span>By {authors.join(', ')}</span>}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass[status] ?? 'bg-slate-100 text-slate-700'}`}>
          {status.replace(/_/g, ' ')}
        </span>
        {testSummary != null && (
          <span className="text-xs text-slate-500">
            Tests: <span className="font-medium text-emerald-600">{testSummary.passed} passed</span>
            {testSummary.failed > 0 && <span className="ml-1 font-medium text-red-600">, {testSummary.failed} failed</span>}
          </span>
        )}
      </div>
    </header>
  )
}
