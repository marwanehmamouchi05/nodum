import type { PageProps } from '../pages/shared'
import { human } from './format'

export function buildingEvents({ data, decisions, ringEvents }: Pick<PageProps, 'data' | 'decisions' | 'ringEvents'>) {
  const zone = (id: string) => data.catalog.zones.find(z => z.id === id)?.name || id
  const device = (id: string) => data.devices.find(d => d.id === id)?.name || id
  return [
    ...data.appointments.flatMap(a => [{ id: 'appointment-' + a.id, at: a.created_at, title: `Appointment scheduled · ${a.visitor_name}`, detail: 'Business visit recorded', location: zone(a.destination_zone_id), kind: 'Visitors', status: 'Scheduled', tone: '', simulated: false }, ...(a.checked_in_at ? [{ id: 'checkin-' + a.id, at: a.checked_in_at, title: `Visitor checked in · ${a.visitor_name}`, detail: 'Visitor check-in recorded', location: zone(a.destination_zone_id), kind: 'Visitors', status: 'Checked in', tone: 'mint', simulated: false }] : [])]),
    ...data.actuators.map(a => ({ id: 'actuator-' + a.id, at: a.at, title: a.message, detail: a.decision.reason, location: `${device(a.device_id)} · ${zone(a.zone_id)}`, kind: 'Building connector', status: a.executed ? 'Executed' : 'Not executed', tone: a.executed ? 'mint' : 'amber', simulated: a.simulated })),
    ...data.scans.map(s => ({ id: 'scan-' + s.id, at: s.at, title: `Credential ${s.result.decision.allowed ? 'allowed' : 'denied'}`, detail: s.result.decision.reason, location: zone(s.zone_id), kind: 'Credential reader', status: s.result.decision.allowed ? 'Allowed' : 'Denied', tone: s.result.decision.allowed ? 'mint' : 'red', simulated: s.result.simulated })),
    ...data.journeys.map(j => ({ id: 'journey-' + j.id, at: j.updated_at, title: j.purpose, detail: `Last confirmed location: ${j.current_confirmed_zone_id ? zone(j.current_confirmed_zone_id) : 'Not confirmed'}`, location: zone(j.destination_zone_id), kind: 'Journey', status: human(j.status), tone: '', simulated: false })),
    ...data.emergencies.flatMap(e => e.history.map((h, i) => ({ id: `emergency-${e.emergency_id}-${i}`, at: h.at, title: `${human(e.emergency_type)} · ${human(h.action)}`, detail: `${e.description} · ${h.actor_id}`, location: e.affected_zone_ids.map(zone).join(', '), kind: 'Emergency', status: `${human(h.action)} · ${human(e.severity)}`, tone: h.action === 'resolved' ? 'mint' : 'amber', simulated: false }))),
    ...decisions.map(d => ({ id: 'decision-' + d.id, at: d.at, title: `Access ${d.decision.allowed ? 'allowed' : 'denied'}`, detail: d.decision.reason, location: `${d.person_id} · ${zone(d.zone_id)}`, kind: 'Access · session', status: d.decision.allowed ? 'Allowed' : 'Denied', tone: d.decision.allowed ? 'mint' : 'red', simulated: false })),
    ...ringEvents.filter((e, i, all) => all.findIndex(other => other.id === e.id) === i).map(e => ({ id: 'ring-' + e.id, at: e.received_at, title: human(e.event_type), detail: 'Received in Ring inbox; downstream action requires operator review.', location: 'Device/location not provided by inbox response', kind: 'Ring inbox', status: e.signal ? human(e.signal) : 'Received', tone: 'blue', simulated: e.is_simulation === true })),
  ].sort((a, b) => b.at.localeCompare(a.at))
}
