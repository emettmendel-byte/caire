import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { compileApi, guidelinesApi } from '../../api/client'
import { SplitPane } from '../Layout/SplitPane'

type GuidelineRow = {
  id: string
  filename: string
  domain?: string
  created_at: string
  processed_at?: string | null
}

interface CreateTreesSectionProps {
  onOpenTree: (treeId: string) => void
}

export function CreateTreesSection({ onOpenTree }: CreateTreesSectionProps) {
  const [subTab, setSubTab] = useState<'view' | 'compile'>('view')
  const [guidelines, setGuidelines] = useState<GuidelineRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [selectedGuidelineId, setSelectedGuidelineId] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [compileJobId, setCompileJobId] = useState<string | null>(null)
  const [compileRawOutput, setCompileRawOutput] = useState<string>('')
  const [compileSnapshot, setCompileSnapshot] = useState<string>('')
  const [systemPromptPreview, setSystemPromptPreview] = useState<string>('')
  const [userPromptPreview, setUserPromptPreview] = useState<string>('')
  const fileRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(() => {
    setLoading(true)
    setError(null)
    guidelinesApi
      .list()
      .then((rows) => setGuidelines(rows as GuidelineRow[]))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const sorted = useMemo(() => {
    return [...guidelines].sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
  }, [guidelines])

  useEffect(() => {
    if (!selectedGuidelineId || subTab !== 'compile') return
    compileApi
      .getPromptPreview(selectedGuidelineId)
      .then((p) => {
        setSystemPromptPreview(p.system_prompt || '')
        setUserPromptPreview(p.user_prompt || '')
      })
      .catch((e) => {
        setSystemPromptPreview('')
        setUserPromptPreview('')
        setError(e.message)
      })
  }, [selectedGuidelineId, subTab])

  const handleUploadPdf = async (file: File) => {
    setBusy(true)
    setStatus('Uploading…')
    setError(null)
    // Preview local file immediately
    const localUrl = URL.createObjectURL(file)
    setPreviewUrl(localUrl)
    try {
      const doc = await guidelinesApi.upload(file, 'general')
      const guidelineId = doc.id as string
      setSelectedGuidelineId(guidelineId)
      setStatus(`Uploaded to library (${guidelineId}).`)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus(null)
    } finally {
      setBusy(false)
    }
  }

  const handleCompileSelected = async () => {
    if (!selectedGuidelineId) return
    setBusy(true)
    setError(null)
    setCompileRawOutput('')
    setCompileSnapshot('')
    setStatus(`Starting compilation for ${selectedGuidelineId}…`)
    try {
      const { job_id } = await compileApi.trigger(selectedGuidelineId)
      setCompileJobId(job_id)
      let attempts = 0
      while (attempts < 180) {
        const st = await compileApi.getStatus(job_id)
        setStatus(`Compiling (job ${job_id})… ${st.progress_message || ''}`)
        setCompileRawOutput(st.llm_raw_output || '')
        setCompileSnapshot(st.parsed_tree_snapshot ? JSON.stringify(st.parsed_tree_snapshot, null, 2) : '')
        if (st.status === 'completed' && st.result_tree_id) {
          setStatus(`Compiled → tree ${st.result_tree_id}`)
          onOpenTree(st.result_tree_id)
          break
        }
        if (st.status === 'failed') {
          throw new Error(st.error_message || 'Compilation failed')
        }
        await new Promise((r) => setTimeout(r, 1500))
        attempts++
      }
      if (attempts >= 180) throw new Error('Compilation timed out')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStatus(null)
    } finally {
      setBusy(false)
    }
  }

  const onFilePicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file.')
      return
    }
    await handleUploadPdf(file)
  }

  return (
    <div className="section create-split">
      <div className="section-header">
        <h2>Create trees (Full pipeline)</h2>
        <p>Upload a PDF → ingest → compile into a decision tree.</p>
      </div>

      <div className="card">
        <div className="tabs sub-tabs">
          <button type="button" className={subTab === 'view' ? 'tab active' : 'tab'} onClick={() => setSubTab('view')}>
            View
          </button>
          <button type="button" className={subTab === 'compile' ? 'tab active' : 'tab'} onClick={() => setSubTab('compile')}>
            Compile (technical)
          </button>
        </div>
        <div className="row">
          {subTab === 'view' ? (
            <>
              <button
                type="button"
                className="btn-primary"
                disabled={busy}
                onClick={() => fileRef.current?.click()}
              >
                {busy ? 'Working…' : 'Upload PDF'}
              </button>
              <input ref={fileRef} type="file" accept=".pdf" className="sr-only" onChange={onFilePicked} />
              <button type="button" className="btn-secondary" onClick={refresh} disabled={busy || loading}>
                Refresh library
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn-primary"
                onClick={handleCompileSelected}
                disabled={busy || !selectedGuidelineId}
              >
                {busy ? 'Compiling…' : 'Compile selected PDF'}
              </button>
              {compileJobId && <span className="status">job: {compileJobId}</span>}
            </>
          )}
          <span className="flex-1" />
          {status && <span className="status">{status}</span>}
        </div>
        {error && <p className="error">{error}</p>}
      </div>

      {subTab === 'view' ? (
        <div className="create-grid">
          <SplitPane
            storageKey="split:create:view"
            minLeftPx={300}
            minRightPx={420}
            initialLeftPx={460}
            left={(
              <div className="card">
                <h3>PDF library</h3>
                {loading ? (
                  <p className="loading">Loading…</p>
                ) : sorted.length === 0 ? (
                  <p className="hint">No PDFs uploaded yet.</p>
                ) : (
                  <ul className="library">
                    {sorted.map((g) => (
                      <li
                        key={g.id}
                        className={g.id === selectedGuidelineId ? 'library-item selected' : 'library-item'}
                      >
                        <button
                          type="button"
                          className="library-button"
                          onClick={() => {
                            setSelectedGuidelineId(g.id)
                            setPreviewUrl(`/api/guidelines/${encodeURIComponent(g.id)}/file`)
                          }}
                        >
                          <div className="library-title">{g.filename}</div>
                          <div className="library-meta">
                            Uploaded {new Date(g.created_at).toLocaleString()}
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            right={(
              <div className="card pdf-viewer">
                <h3>PDF preview</h3>
                {previewUrl ? (
                  <object data={previewUrl} type="application/pdf" className="pdf-frame" aria-label="PDF preview">
                    <embed src={previewUrl} type="application/pdf" className="pdf-frame" />
                  </object>
                ) : (
                  <p className="hint">Select a PDF from the library (or upload one) to preview it here.</p>
                )}
              </div>
            )}
          />
        </div>
      ) : (
        <div className="create-grid">
          <SplitPane
            storageKey="split:create:compile"
            minLeftPx={320}
            minRightPx={500}
            initialLeftPx={420}
            left={(
              <div className="card">
                <h3>Guideline source</h3>
                {loading ? (
                  <p className="loading">Loading…</p>
                ) : sorted.length === 0 ? (
                  <p className="hint">Upload PDFs in the View tab first.</p>
                ) : (
                  <ul className="library">
                    {sorted.map((g) => (
                      <li key={g.id} className={g.id === selectedGuidelineId ? 'library-item selected' : 'library-item'}>
                        <button
                          type="button"
                          className="library-button"
                          onClick={() => setSelectedGuidelineId(g.id)}
                        >
                          <div className="library-title">{g.filename}</div>
                          <div className="library-meta">Uploaded {new Date(g.created_at).toLocaleString()}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            right={(
              <div className="card technical-compile">
                <h3>Prompts and model output</h3>
                <p className="hint">Inspect exactly what is sent to the model and what it returned.</p>
                <label className="technical-label">System prompt</label>
                <textarea className="json technical-block" value={systemPromptPreview} readOnly rows={8} />
                <label className="technical-label">User prompt</label>
                <textarea className="json technical-block" value={userPromptPreview} readOnly rows={8} />
                <label className="technical-label">Raw LLM output</label>
                <textarea className="json technical-block" value={compileRawOutput} readOnly rows={10} />
                <label className="technical-label">Parsed tree snapshot (JSON)</label>
                <textarea className="json technical-block" value={compileSnapshot} readOnly rows={12} />
              </div>
            )}
          />
        </div>
      )}
    </div>
  )
}

