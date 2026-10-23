import { useState } from 'react'
import type { ReactNode } from 'react'
import type { Snapshot, ManagerPage } from './model'
import { Badge, Empty } from '../components/ui'
import { BuildingSection } from '../components/BuildingSection'
import type { SpatialItem } from '../components/BuildingSection'
import { date, human } from '../components/format'
import { Icon } from '../components/Icon'

function asTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}

export function ManagerCommandCenter({ data, onNavigate, tools }: { data: Snapshot; onNavigate: (page: ManagerPage) => void; tools?: ReactNode }) {
  const [selectedBuilding, setSelectedBuilding] = useState(data.buildings[0]?.id || '')
  const [arrivalOpen, setArrivalOpen] = useState(false)
  const [selectedPlace, setSelectedPlace] = useState<string>()
  const building = data.buildings.find(b => b.id === selectedBuilding) || data.buildings[0]
  const nodes = building ? data.nodes.filter(n => n.id === building.id || n.building_id === building.id) : []
  const nodeAt = (identifier?: string | null) => nodes.find(n => n.id === identifier) || nodes.find(n => !['device', 'integration'].includes(n.kind) && n.scope_id === identifier)
  const visibleItems: SpatialItem[] = [
    ...data.maintenance.map(r => ({ id: r.id, location_id: r.location_id, title: r.title, detail: `${r.location_name} · ${human(r.status)}`, category: 'maintenance' as const })),
    ...data.visitors.map(v => ({ id: v.id, location_id: v.location_id, title: v.name, detail: `${v.host} · ${human(v.status)}`, category: 'visitor' as const, simulated: v.source.includes('simulation') })),
    ...data.ring.filter(r => r.signal === 'doorbell' || r.signal === 'person').map(r => ({ id: r.id, location_id: r.location_id, title: 'Arrival signal', detail: `${human(r.signal)} · ${asTime(r.at)} · Identity unverified`, category: 'attention' as const, simulated: r.simulated })),
  ]
  const newestArrival = [...data.ring].sort((a, b) => Date.parse(b.at) - Date.parse(a.at)).find(e => e.signal === 'doorbell' || e.signal === 'person')
  const arrivalAge = newestArrival ? Date.parse(data.at) - Date.parse(newestArrival.at) : Infinity
  const recentArrival = arrivalAge >= 0 && arrivalAge <= 15 * 60 * 1000
  const arrivalLocation = newestArrival && nodeAt(newestArrival.location_id)?.name
  const operational = data.attention.filter(item => !/unverified/i.test(`${item.title} ${item.detail}`)).slice(0, 3)
  const deviceLabel = data.unverified_devices > 0 ? `${data.unverified_devices} unverified` : data.counts.offline > 0 ? `${data.counts.offline} offline` : data.devices.length ? `${data.devices.filter(d => ['online', 'connected'].includes(d.status)).length} reported online` : 'No device records'
  const time = asTime(data.at)
  return <div className="manager-command-center">
    <header className="manager-command-heading"><div><h1>{building?.name || 'Building operations'}</h1><p>Building operations · Updated {time}</p></div><div className="manager-command-heading-actions">{tools}{data.buildings.length > 1 && <label>Building<select aria-label="Building" value={building?.id || ''} onChange={e => setSelectedBuilding(e.target.value)}>{data.buildings.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}</select></label>}<Badge tone={data.status === 'Normal' ? 'mint' : data.status === 'Incident active' || data.status === 'Degraded systems' ? 'red' : 'amber'}>{data.status}</Badge></div></header>
    <div className="manager-command-layout">
      <BuildingSection nodes={nodes} items={visibleItems} title="Building section" selectedId={selectedPlace} onSelect={setSelectedPlace} />
      <aside className="manager-attention-rail" aria-label="Operational attention">
        <div className="manager-rail-heading"><div><h2>Needs attention</h2></div></div>
        <p className="manager-snapshot-note">Items needing your review</p>
        {!operational.length && !newestArrival && <Empty>No open issues in the records you can see.</Empty>}
        {operational.map((item, index) => <button className="manager-attention-item" key={`${item.page}-${item.title}-${index}`} onClick={() => onNavigate(item.page)}><span className="attention-index">{String(index + 1).padStart(2, '0')}</span><span><strong>{item.title}</strong><small>{item.detail}</small><em>Review {item.page.toLowerCase()}</em></span><Icon name="arrow" size={17} /></button>)}
        {newestArrival && <article className={`manager-arrival-card ${newestArrival.simulated ? 'is-simulated' : ''}`}>
          <div className="manager-arrival-top"><span><Icon name="visitors" size={17}/>Arrival signal</span><Badge tone={newestArrival.simulated ? 'blue' : 'amber'}>{newestArrival.simulated ? 'Simulation' : 'Recorded signal'}</Badge></div>
          <strong>{recentArrival ? 'Recent entrance signal' : 'Earlier entrance signal'}</strong>
          <p>{arrivalLocation || 'Location is not mapped to a visible building place.'}</p>
          <div className="manager-arrival-facts"><span>{human(newestArrival.signal)}</span><time>{date(newestArrival.at)}</time><b>Identity unverified</b></div>
          <button type="button" className="primary" aria-expanded={arrivalOpen} onClick={() => { setArrivalOpen(!arrivalOpen); if (!arrivalOpen) setSelectedPlace(nodeAt(newestArrival.location_id)?.id) }}>{arrivalOpen ? 'Close review' : 'Review arrival'}</button>
          {arrivalOpen && <div className="manager-arrival-review"><h3>Received signal</h3><p>Ring reported a {human(newestArrival.signal).toLowerCase()} event. The event does not identify a visitor or authorize entry.</p><p><strong>Expected visits visible to you</strong></p>{data.visitors.filter(v => v.status === 'expected').length ? data.visitors.filter(v => v.status === 'expected').slice(0, 5).map(v => <div className="arrival-visit" key={v.id}><span><strong>{v.name}</strong><small>{v.host} · {v.destination} · {date(v.start)}</small></span><Badge>{human(v.status)}</Badge></div>) : <p>No expected visits are available in this scope.</p>}<p className="fine">Compare visits yourself. Any arrival confirmation must be made from the individual visit record when it is available and within its valid window.</p><button type="button" onClick={() => onNavigate('Visitors')}>Open visitor records</button><div className="arrival-timeline"><span><i/>Signal received</span></div></div>}
        </article>}
          <div className="manager-ops-summary" aria-label="Operational summary">
      <button onClick={() => onNavigate('Visitors')}><small>Visitors today</small><strong>{data.counts.visitors}</strong><span>Scheduled in visible scope</span></button>
      <button onClick={() => onNavigate('Maintenance')}><small>Open maintenance</small><strong>{data.counts.maintenance}</strong><span>Requests needing follow-up</span></button>
      <button onClick={() => onNavigate('Security')}><small>Active incidents</small><strong>{data.counts.incidents}</strong><span>From visible incident records</span></button>
      <button onClick={() => onNavigate('Security')}><small>Device status</small><strong>{deviceLabel}</strong><span>{data.unverified_devices ? 'Hardware status has not been confirmed' : data.counts.offline ? 'Reported offline by connected provider' : 'Based on available provider records'}</span></button>
    </div>
</aside>
    </div>
    <div className="manager-overview-lower"><section className="manager-recent-activity"><div className="manager-section-heading"><h2>Recent activity</h2><button type="button" onClick={() => onNavigate('Activity')}>View activity</button></div>{!data.activity.length && <Empty>No activity in the records you can see.</Empty>}{data.activity.slice(0, 4).map(event => <article className="manager-mini-event" key={event.id}><time>{asTime(event.at)}</time><div><strong>{human(event.what)}</strong><small>{event.who} · {event.where}</small></div>{event.simulated && <Badge tone="blue">{event.who === 'Official Ring sandbox' ? 'Official sandbox' : 'Simulation'}</Badge>}</article>)}</section><section className="manager-quick-actions"><div className="manager-section-heading"><h2>Quick actions</h2></div><div>{data.actions.invite.length > 0 && <button onClick={() => onNavigate('Visitors')}><Icon name="visitors"/>Invite visitor</button>}{data.actions.announce.length > 0 && <button onClick={() => onNavigate('Announcements')}><Icon name="notice"/>Publish notice</button>}{data.actions.maintenance.length > 0 && <button onClick={() => onNavigate('Maintenance')}><Icon name="maintenance"/>Report maintenance</button>}{data.access_people.length > 0 && data.access_zones.length > 0 && <button onClick={() => onNavigate('Access')}><Icon name="lock"/>Review access</button>}</div></section></div>
  </div>
}
