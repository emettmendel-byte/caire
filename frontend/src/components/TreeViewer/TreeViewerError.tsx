interface TreeViewerErrorProps {
  error: Error
  onRetry?: () => void
  onBack?: () => void
}

export function TreeViewerError({ error, onRetry, onBack }: TreeViewerErrorProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-slate-100 p-6">
      <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-left max-w-md">
        <p className="font-medium text-red-800">Failed to load tree</p>
        <p className="mt-1 text-sm text-red-700">{error.message}</p>
      </div>
      <div className="flex gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md bg-clinical-blue px-3 py-2 text-sm font-medium text-white hover:bg-sky-600"
          >
            Retry
          </button>
        )}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Back to list
          </button>
        )}
      </div>
    </div>
  )
}
