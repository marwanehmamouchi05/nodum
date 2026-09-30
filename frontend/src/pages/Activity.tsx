import type { PageProps } from './shared'
import { Badge, Empty } from '../components/ui'
import { date, human } from '../components/format'
export function Activity({ data, decisions, ringEvents }: PageProps) {
  const events = [
    ...data.appointments.flatMap(a => [{ id: 'appointment-' + a.id, at: a.created_at, title: `Appointment scheduled · ${a.visitor_name}`, detail: a.destination_zone_id, kind: 'Appointment' }, ...(a.checked_in_at ? [{ id: 'checkin-' + a.id, at: a.checked_in_at, title: `Visitor checked in · ${a.visitor_name}`, detail: a.destination_zone_id, kind: 'Appointment' }] : [])]),
    ...data.actuators.map(a => ({ id: 'actuator-' + a.id, at: a.at, title: a.message, detail: `${a.person_id} → ${a.zone_id}`, kind: 'Simulation' })),
    ...data.scans.map(s => ({ id: 'scan-' + s.id, at: s.at, title: `Credential ${s.result.decision.allowed ? 'allowed' : 'denied'}`, detail: s.result.decision.reason, kind: 'Scan · simulation' })),
    ...data.journeys.map(j => ({ id: 'journey-' + j.id, at: j.updated_at, title: `Journey ${human(j.status)}`, detail: `${j.purpose} · last confirmed: ${j.current_confirmed_zone_id || 'none'}`, kind: 'Journey' })),
    ...data.emergencies.flatMap(e => e.history.map((h, i) => ({ id: `emergency-${e.emergency_id}-${i}`, at: h.at, title: `${human(e.emergency_type)} · ${human(h.action)}`, detail: `${e.description} · ${h.actor_id}`, kind: 'Emergency' }))),
    ...decisions.map(d => ({ id: 'decision-' + d.id, at: d.at, title: `Access ${d.decision.allowed ? 'allowed' : 'denied'}`, detail: `${d.person_id} → ${d.zone_id} · ${d.decision.reason}`, kind: 'Session decision' })),
    ...ringEvents.map(e => ({ id: 'ring-' + e.id, at: e.received_at, title: human(e.event_type), detail: e.signal || 'Verified Ring inbox event', kind: 'Ring' })),
  ].sort((a, b) => b.at.localeCompare(a.at))
  return <><div className="page-intro"><span className="eyebrow">BUILDING ACTIVITY</span><h1>Every action has a story.</h1><p>Recorded events across the building, newest first. Ring events appear after authenticated discovery in Integrations. Access checks are session-only.</p></div>{!events.length && <Empty>No activity yet. Schedule a visit or start a demo journey.</Empty>}<div className="activity-feed">{events.map(e => <article key={e.id}><time>{date(e.at)}</time><span className="timeline-dot" /><div><Badge tone={e.kind === 'Emergency' ? 'amber' : ''}>{e.kind}</Badge><h3>{e.title}</h3><p>{e.detail}</p></div></article>)}</div></>
}
