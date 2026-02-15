/**
 * Zustand store for TreeEditor: current tree, dirty, undo/redo, sync status.
 */

import { create } from 'zustand'
import type { DecisionTree } from '../../types/decisionTree'

export type SyncStatus = 'idle' | 'saving' | 'saved' | 'error'

const MAX_HISTORY = 50

interface TreeEditorState {
  tree: DecisionTree | null
  lastSavedTree: DecisionTree | null
  dirty: boolean
  past: DecisionTree[]
  future: DecisionTree[]
  syncStatus: SyncStatus
  syncError: string | null
  selectedNodeId: string | null
  /** Version from last fetch/save for display */
  version: string
  /** Set tree (e.g. after fetch) and optionally push to history. */
  setTree: (tree: DecisionTree | null, pushUndo?: boolean) => void
  /** Replace current tree and mark dirty; push current to past. */
  updateTree: (next: DecisionTree) => void
  undo: () => void
  redo: () => void
  /** After save success: set lastSavedTree = tree, clear dirty, set version. */
  markSaved: (tree: DecisionTree) => void
  setSyncStatus: (status: SyncStatus, error?: string) => void
  setSelectedNodeId: (id: string | null) => void
  setVersion: (v: string) => void
  revertToLastSaved: () => void
  canUndo: () => boolean
  canRedo: () => boolean
  reset: () => void
}

const emptyState = {
  tree: null,
  lastSavedTree: null,
  dirty: false,
  past: [] as DecisionTree[],
  future: [] as DecisionTree[],
  syncStatus: 'idle' as SyncStatus,
  syncError: null as string | null,
  selectedNodeId: null as string | null,
  version: '',
}

export const useTreeEditorStore = create<TreeEditorState>((set, get) => ({
  ...emptyState,

  setTree(tree, pushUndo = false) {
    set((s) => {
      const past = pushUndo && s.tree ? [s.tree, ...s.past].slice(0, MAX_HISTORY) : s.past
      return {
        tree,
        lastSavedTree: tree,
        dirty: false,
        past,
        future: [],
        syncStatus: 'idle',
        syncError: null,
        version: tree?.version ?? '',
      }
    })
  },

  updateTree(next) {
    set((s) => ({
      tree: next,
      dirty: true,
      past: s.tree ? [s.tree, ...s.past].slice(0, MAX_HISTORY) : s.past,
      future: [],
    }))
  },

  undo() {
    const { past, tree } = get()
    if (past.length === 0 || !tree) return
    set({
      tree: past[0],
      past: past.slice(1),
      future: [tree, ...get().future],
      dirty: true,
    })
  },

  redo() {
    const { future, tree } = get()
    if (future.length === 0 || !tree) return
    set({
      tree: future[0],
      future: future.slice(1),
      past: tree ? [tree, ...get().past] : get().past,
      dirty: true,
    })
  },

  markSaved(tree) {
    set({
      lastSavedTree: tree,
      dirty: false,
      syncStatus: 'saved',
      syncError: null,
      version: tree.version ?? get().version,
    })
  },

  setSyncStatus(status, error) {
    set({ syncStatus: status, syncError: error ?? null })
  },

  setSelectedNodeId(id) {
    set({ selectedNodeId: id })
  },

  setVersion(v) {
    set({ version: v })
  },

  revertToLastSaved() {
    const { lastSavedTree } = get()
    if (!lastSavedTree) return
    set({
      tree: lastSavedTree,
      dirty: false,
      future: [],
      syncStatus: 'idle',
      syncError: null,
    })
  },

  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,

  reset() {
    set(emptyState)
  },
}))
