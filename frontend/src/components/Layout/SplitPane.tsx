import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

interface SplitPaneProps {
  left: ReactNode
  right: ReactNode
  minLeftPx?: number
  minRightPx?: number
  initialLeftPx?: number
  storageKey?: string
  className?: string
}

export function SplitPane({
  left,
  right,
  minLeftPx = 260,
  minRightPx = 360,
  initialLeftPx = 360,
  storageKey,
  className,
}: SplitPaneProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const [leftPx, setLeftPx] = useState<number>(() => {
    if (!storageKey) return initialLeftPx
    const raw = localStorage.getItem(storageKey)
    const n = raw ? Number(raw) : NaN
    return Number.isFinite(n) ? n : initialLeftPx
  })
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    if (!storageKey) return
    localStorage.setItem(storageKey, String(leftPx))
  }, [leftPx, storageKey])

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const root = rootRef.current
      if (!root) return
      const rect = root.getBoundingClientRect()
      const maxLeft = Math.max(minLeftPx, rect.width - minRightPx)
      const next = Math.min(Math.max(e.clientX - rect.left, minLeftPx), maxLeft)
      setLeftPx(next)
    }
    const onUp = () => setDragging(false)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging, minLeftPx, minRightPx])

  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const rect = root.getBoundingClientRect()
    const maxLeft = Math.max(minLeftPx, rect.width - minRightPx)
    if (leftPx > maxLeft) setLeftPx(maxLeft)
    if (leftPx < minLeftPx) setLeftPx(minLeftPx)
  }, [leftPx, minLeftPx, minRightPx])

  const safeLeft = useMemo(() => `${leftPx}px`, [leftPx])

  return (
    <div ref={rootRef} className={className ? `split-pane ${className}` : 'split-pane'}>
      <div className="split-pane-left" style={{ width: safeLeft, minWidth: minLeftPx }}>
        {left}
      </div>
      <div
        className={`split-pane-divider${dragging ? ' dragging' : ''}`}
        role="separator"
        aria-orientation="vertical"
        onMouseDown={() => setDragging(true)}
      />
      <div className="split-pane-right" style={{ minWidth: minRightPx }}>
        {right}
      </div>
    </div>
  )
}

