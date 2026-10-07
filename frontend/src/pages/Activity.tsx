import type { PageProps } from './shared'
import { ActivityTimeline } from '../components/ActivityTimeline'
import { buildingEvents } from '../components/activity'

export function Activity(props: PageProps) {
  return <><div className="page-intro"><span className="eyebrow">Operational record</span><h1>Building activity</h1><p>Signals, visits and policy outcomes in one timeline, newest first. Ring events appear after discovery or simulation; access checks remain session-only.</p></div><ActivityTimeline events={buildingEvents(props)} /></>
}
