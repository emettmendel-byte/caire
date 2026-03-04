/**
 * Extract text from a PDF file in the browser using PDF.js (no backend).
 */

import * as pdfjsLib from 'pdfjs-dist'
// Resolve worker URL so Vite bundles it and we get correct path in production
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl
}

export async function pdfToText(file: File): Promise<string> {
  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const parts: string[] = []
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i)
    const content = await page.getTextContent()
    const strings = (content.items as { str?: string }[])
      .map((item) => item.str ?? '')
      .filter(Boolean)
    parts.push(strings.join(' '))
  }
  return parts.join('\n\n')
}
