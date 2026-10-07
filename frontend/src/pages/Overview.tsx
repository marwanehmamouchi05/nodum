import { useClock } from '../hooks/useClock'
import type { Page, PageProps } from './shared'
import { BuildingView } from '../components/BuildingView'
import { JourneyPanel } from '../components/JourneyPanel'
import { Badge, Empty, Section } from '../components/ui'
import { Icon } from '../components/Icon'
import type { IconName } from '../components/Icon'
import { ActivityTimeline } from '../components/ActivityTimeline'
import { buildingEvents } from '../components/activity'

export function Overview(props: PageProps) {
  const { data, navigate, unavailable } = props
  const active = data.emergencies.filter(e => e.status === 'active')
  const now = useClock()
  const visitors = data.appointments.filter(a => a.status === 'checked_in' && new Date(a.appointment_time).getTime() + a.access_after_minutes * 60000 > now)
  const metrics: { count: number | string; label: string; detail: string; page: Page; icon: IconName }[] = [
    { count: unavailable.includes('emergencies') ? '—' : active.length, label: 'Active incidents', detail: 'Emergency register', page: 'Emergencies', icon: 'emergency' },
    { count: unavailable.includes('appointments') ? '—' : visitors.length, label: 'Active business visits', detail: 'Checked in / within access window', page: 'Visitors', icon: 'visitors' },
    { count: unavailable.includes('scans') ? '—' : data.scans.length, label: 'Credential events', detail: 'Recorded scans / all time', page: 'Access', icon: 'access' },
    { count: unavailable.includes('integrations') ? '—' : data.integrations.filter(i => i.enabled).length, label: 'Enabled integrations', detail: 'Configuration / not live telemetry', page: 'Integrations', icon: 'integrations' },
  ]
  return <><div className="operations-heading"><div><span className="eyebrow">Mixed-use building</span><h1>Operations overview</h1><p>A clear view of arrivals, safety and connected building systems.</p></div><button onClick={() => navigate('AI Assistant')}><Icon name="assistant" size={17} /> Ask Nodum</button></div>
    <div className={`building-status ${active.length || unavailable.length ? 'attention' : ''}`}><span className="status-emblem"><Icon name={active.length || unavailable.length ? 'emergency' : 'check'} size={24} /></span><div><strong>{unavailable.length ? 'Building data needs attention' : active.length ? `${active.length} active incident${active.length === 1 ? '' : 's'} require attention` : 'No active incidents reported'}</strong><p>{unavailable.length ? 'Some resources are unavailable. Review connection details above before relying on counts.' : active.length ? 'Review affected zones and responder assignments in the emergency register.' : 'Emergency register is clear. Device states are snapshots; physical systems are not monitored live.'}</p></div><button onClick={() => navigate(active.length ? 'Emergencies' : 'Building')}>{active.length ? 'Review incidents' : 'View building'}<Icon name="arrow" size={16} /></button></div>
    <div className="operations-metrics">{metrics.map(m => <button key={m.label} onClick={() => navigate(m.page)}><div className="metric-label"><Icon name={m.icon} size={18} /><span>{m.label}</span></div><strong>{m.count}</strong><small>{m.detail}</small></button>)}</div>
    <div className="overview-grid"><Section title="Building & zones" action={<Badge tone="blue">Spatial context</Badge>}><BuildingView data={data} compact /></Section><div className="stack"><Section title="Connected systems" action={<button onClick={() => navigate('Integrations')}>Manage <Icon name="arrow" size={14} /></button>}><p className="fine">Enabled configuration and imported inventory. Connection and device availability are verified separately.</p>{!data.integrations.length && <Empty>No integrations loaded. Open Integrations to inspect connectors.</Empty>}<div className="system-list">{data.integrations.map(i => <div className="row" key={i.id}><div><strong>{i.name}</strong><small>{i.mode === 'ring' ? 'Ring inventory snapshot' : 'Software simulation'}</small></div><Badge tone={i.enabled ? 'mint' : ''}>{i.enabled ? 'Enabled' : 'Disabled'}</Badge></div>)}</div></Section><Section title="Incident watch" action={<Badge tone={unavailable.includes('emergencies') || active.length ? 'amber' : 'mint'}>{unavailable.includes('emergencies') ? 'Unavailable' : active.length ? 'Attention required' : 'Clear'}</Badge>}>{active.length ? active.slice(0, 3).map(e => <div className="list-row" key={e.emergency_id}><div><strong>{e.description}</strong><small>{e.affected_zone_ids.map(id => data.catalog.zones.find(z => z.id === id)?.name || id).join(', ')}</small></div><Badge tone="amber">{e.severity}</Badge></div>) : <p>{unavailable.includes('emergencies') ? 'Incident data could not be refreshed.' : 'No active incidents in the current register.'}</p>}<button onClick={() => navigate('Emergencies')}>Open emergency register <Icon name="arrow" size={14} /></button></Section></div></div>
    <Section title="Recent activity" action={<button onClick={() => navigate('Activity')}>Full timeline <Icon name="arrow" size={14} /></button>}><ActivityTimeline events={buildingEvents(props).slice(0, 5)} /></Section><JourneyPanel {...props} />
  </>
}
