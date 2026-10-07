import type { buildingEvents } from './activity'
import { Badge, Empty } from './ui'
import { date } from './format'

export function ActivityTimeline({ events }: { events: ReturnType<typeof buildingEvents> }) {
  if (!events.length) return <Empty>No recorded activity. Schedule a visit or run a simulation to see events here.</Empty>
  return <div className="activity-feed">{events.map(e => <article key={e.id}><time dateTime={e.at}>{date(e.at)}</time><span className="timeline-dot" aria-hidden="true" /><div><div className="event-meta"><Badge>{e.kind}</Badge><Badge tone={e.tone}>{e.status}</Badge>{e.simulated && <Badge tone="amber">Simulation</Badge>}</div><h3>{e.title}</h3><div className="event-location">{e.location}</div><p>{e.detail}</p></div></article>)}</div>
}
