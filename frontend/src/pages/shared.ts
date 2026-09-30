import type { AccessEntry, BuildingData, RingEvent } from '../api/types'
export type Page = 'Overview' | 'Building' | 'Visitors' | 'Businesses' | 'Access' | 'Emergencies' | 'Integrations' | 'Activity' | 'AI Assistant'
export interface PageProps { unavailable: (keyof BuildingData)[]; data: BuildingData; actor: string; refresh: () => Promise<void>; navigate: (page: Page) => void; decisions: AccessEntry[]; recordDecision: (entry: AccessEntry) => void; ringEvents: RingEvent[]; setRingEvents: (events: RingEvent[]) => void }
export const options = (records: { id: string; name: string }[]) => records.map(r => ({ value: r.id, label: r.name }))
export const key = () => crypto.randomUUID()
