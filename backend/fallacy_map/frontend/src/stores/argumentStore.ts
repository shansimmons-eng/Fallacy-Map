import { create } from 'zustand'

export type VeracityState = 'ignition' | 'healthy' | 'stressed' | 'critical' | 'divide'

export interface Fallacy {
  id: string
  type: string
  claim_text: string
  magnitude: number
  persistence: number
}

export interface Claim {
  id: string
  text: string
  position: [number, number, number]
  is_conclusion: boolean
}

export interface VeracityEvent {
  V_before: number
  V_after: number
  V_cost: number
  type: 'fallacy' | 'bypass' | 'divide' | 'reset'
}

interface ArgumentStore {
  argumentId: string | null
  title: string
  V_active: number
  V_c: number
  state: VeracityState
  inverion_triggered: boolean
  root_fallacy_id: string | null
  bypass_count: number
  
  fallacies: Fallacy[]
  claims: Claim[]
  mesh_data: number[][]
  veracity_events: VeracityEvent[]
  
  setArgumentId: (id: string) => void
  setTitle: (title: string) => void
  setVactive: (v: number) => void
  addFallacy: (fallacy: Fallacy) => void
  addClaim: (claim: Claim) => void
  setMeshData: (data: number[][]) => void
  addVeracityEvent: (event: VeracityEvent) => void
  triggerInverion: (rootId: string) => void
  reset: () => void
  
  getStateFromV: (V: number) => VeracityState
}

export const useArgumentStore = create<ArgumentStore>((set, get) => ({
  argumentId: null,
  title: '',
  V_active: 1.0,
  V_c: 1.0,
  state: 'ignition',
  inverion_triggered: false,
  root_fallacy_id: null,
  bypass_count: 0,
  
  fallacies: [],
  claims: [],
  mesh_data: [],
  veracity_events: [],
  
  setArgumentId: (id) => set({ argumentId: id }),
  setTitle: (title) => set({ title }),
  
  setVactive: (v) => {
    const state = get().getStateFromV(v)
    set({ V_active: v, state })
  },
  
  addFallacy: (fallacy) => set((s) => ({ fallacies: [...s.fallacies, fallacy] })),
  
  addClaim: (claim) => set((s) => ({ claims: [...s.claims, claim] })),
  
  setMeshData: (data) => set({ mesh_data: data }),
  
  addVeracityEvent: (event) => set((s) => ({ veracity_events: [...s.veracity_events, event] })),
  
  triggerInverion: (rootId) => set({ 
    inverion_triggered: true, 
    root_fallacy_id: rootId,
    state: 'divide',
    V_active: 0
  }),
  
  reset: () => set({
    argumentId: null,
    title: '',
    V_active: 1.0,
    state: 'ignition',
    inverion_triggered: false,
    root_fallacy_id: null,
    bypass_count: 0,
    fallacies: [],
    claims: [],
    mesh_data: [],
    veracity_events: []
  }),
  
  getStateFromV: (V) => {
    if (V <= 0) return 'divide'
    if (V <= 0.1) return 'critical'
    if (V <= 0.3) return 'stressed'
    if (V <= 0.8) return 'healthy'
    return 'ignition'
  }
}))