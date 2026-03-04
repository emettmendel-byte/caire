/**
 * Build a minimal placeholder decision tree from extracted guideline text (no backend).
 * Same shape as backend/compiler.py stub: root + one outcome with text snippet.
 */

import type { DecisionTreeLegacy, DecisionNode, Edge } from '../types/decisionTree'

export function buildPlaceholderTreeFromText(
  rawText: string,
  treeId: string,
  name: string
): DecisionTreeLegacy {
  const rootId = 'root'
  const outcomeId = 'outcome_1'
  const snippet = rawText.trim().slice(0, 500)
  const nodes: DecisionNode[] = [
    {
      id: rootId,
      type: 'root',
      label: 'Start triage',
      description: 'Begin assessment',
    },
    {
      id: outcomeId,
      type: 'outcome',
      label: 'Review guideline for full logic',
      description: snippet || undefined,
    },
  ]
  const edges: Edge[] = [
    { source_id: rootId, target_id: outcomeId, label: 'Continue' },
  ]
  return {
    id: treeId,
    version: '0.1.0',
    name,
    description: 'Generated from guideline (browser-only placeholder)',
    nodes,
    edges,
    root_id: rootId,
  }
}
