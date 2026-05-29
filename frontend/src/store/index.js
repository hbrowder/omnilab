import { create } from 'zustand'
export const useStore = create((set) => ({
  labs: [], activeLab: null, nodes: [], links: [], templates: [],
  categories: [], systemInfo: null, selectedNode: null,

  // CRE-46 / CRE-47 — AI Lab Builder ("Build with AI") panel state.
  // status: 'idle' | 'building' | 'done' | 'error' | 'cancelled'
  // runId is captured from the early `run_started` SSE event (CRE-47) so the
  // Stop button knows which run to POST to /cancel.
  aiBuild: { status: 'idle', prompt: '', events: [], error: null, labId: null, summary: null, runId: null },
  aiBuildStart: (prompt) => set({
    aiBuild: { status: 'building', prompt, events: [], error: null, labId: null, summary: null, runId: null },
  }),
  aiBuildSetRunId: (runId) => set((s) => ({
    aiBuild: { ...s.aiBuild, runId },
  })),
  aiBuildPushEvent: (event) => set((s) => ({
    aiBuild: { ...s.aiBuild, events: [...s.aiBuild.events, event] },
  })),
  aiBuildDone: (labId, summary) => set((s) => ({
    aiBuild: { ...s.aiBuild, status: 'done', labId, summary },
  })),
  aiBuildError: (error) => set((s) => ({
    aiBuild: { ...s.aiBuild, status: 'error', error },
  })),
  aiBuildCancelled: () => set((s) => ({
    aiBuild: { ...s.aiBuild, status: 'cancelled' },
  })),
  aiBuildReset: () => set({
    aiBuild: { status: 'idle', prompt: '', events: [], error: null, labId: null, summary: null, runId: null },
  }),
  setLabs: (labs) => set({ labs }),
  removeLab: (id) => {
    set((s) => ({ labs: (Array.isArray(s.labs) ? s.labs : []).filter(l => l.id !== id) }))
    try {
      const raw = localStorage.getItem('omnilab_folders')
      if (raw) {
        const data = JSON.parse(raw)
        if (data && Array.isArray(data.folders)) {
          data.folders.forEach(f => {
            if (Array.isArray(f.labIds)) f.labIds = f.labIds.filter(x => x !== id)
          })
          localStorage.setItem('omnilab_folders', JSON.stringify(data))
        }
      }
    } catch (e) { /* ignore */ }
  },
  setActiveLab: (lab) => set({ activeLab: lab }),
  setTopology: ({ nodes, links }) => set({ nodes, links }),
  setTemplates: (t) => set({ templates: t }),
  setCategories: (c) => set({ categories: c }),
  setSystemInfo: (i) => set({ systemInfo: i }),
  setSelectedNode: (n) => set({ selectedNode: n }),
  addNode: (n) => set((s) => ({ nodes: [...s.nodes, n] })),
  removeNode: (id) => set((s) => ({ nodes: s.nodes.filter(n=>n.id!==id), links: s.links.filter(l=>l.src_node_id!==id&&l.dst_node_id!==id) })),
}))
