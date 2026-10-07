import { AuthPanel } from '../components/AuthPanel'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Device, DeviceStatus, RingDevice, RingEvent, RingSimulationDelivery, RingSimulationStatus } from '../api/types'
import type { PageProps } from './shared'
import { options } from './shared'
import { ActionForm, Badge, Empty, Section, TaskButton } from '../components/ui'
import { Icon } from '../components/Icon'
import { date, human } from '../components/format'

function DeviceCard({ device, props }: { device: Device; props: PageProps }) {
  const [status, setStatus] = useState<DeviceStatus>()
  const { data, actor, refresh } = props
  return <article className="device-card"><div className="row"><span className="device-icon"><Icon name={device.device_type.includes('reader') ? 'access' : 'device'} size={26} /></span><Badge tone={device.simulated ? '' : 'blue'}>{device.simulated ? 'Simulation' : 'Ring inventory'}</Badge></div><h3>{device.name}</h3><p>{human(device.device_type)} · {device.provider}</p><small>Located in {data.catalog.zones.find(z => z.id === device.zone_id)?.name || device.zone_id}</small><div className="capabilities">{device.capabilities.map(c => <span key={c}>{human(c)}</span>)}</div><TaskButton run={async () => setStatus(await api.deviceStatus(device.id))}>Inspect status & mapping</TaskButton>{status && <div className="device-state"><Badge tone={status.available ? 'mint' : 'amber'}>{status.available ? 'Available' : 'Unavailable'}</Badge><p>Mapped: {status.mapping?.zone_ids.map(id => data.catalog.zones.find(z => z.id === id)?.name || id).join(', ') || 'Not mapped'}</p>{status.state && <p>{['door', 'smart_lock', 'turnstile'].includes(device.device_type) ? `Simulated lock: ${status.state.locked ? 'locked' : 'unlocked'}` : device.device_type.includes('elevator') ? `Cabin floor: ${status.state.current_floor ?? 'unknown'} · Authorized floor: ${status.state.authorized_floor ?? 'none'}` : status.state.route.join(' → ') || 'No active route'}</p>}<small>Snapshot at inspection, not live telemetry.</small></div>}<details><summary>Edit zone mapping</summary><Mapping device={device} zones={data.catalog.zones} save={async ids => { await api.map(device.id, ids, actor); setStatus(await api.deviceStatus(device.id)); await refresh() }} /></details></article>
}
function Mapping({ device, zones, save }: { device: Device; zones: PageProps['data']['catalog']['zones']; save: (ids: string[]) => Promise<void> }) {
  const [selected, setSelected] = useState<string[]>([])
  return <div className="mapping"><p className="fine">Replaces the mapping. Doors protect exactly one zone.</p>{zones.map(z => <label key={z.id}><input type="checkbox" checked={selected.includes(z.id)} onChange={e => setSelected(previous => e.target.checked ? [...previous, z.id] : previous.filter(id => id !== z.id))} />{z.name}</label>)}<TaskButton run={async () => { if (!selected.length) throw new Error('Choose at least one zone.'); await save(selected) }}>Save mapping for {device.name}</TaskButton></div>
}

function SimulationSection({ props }: { props: PageProps }) {
  const { refresh, setRingEvents, ringEvents } = props
  const [status, setStatus] = useState<RingSimulationStatus | null>(null)
  const [devices, setDevices] = useState<RingDevice[]>([])
  const [simEvents, setSimEvents] = useState<RingEvent[]>([])
  const [last, setLast] = useState<{ scenario: string; events: RingSimulationDelivery[] } | null>(null)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)

  // Auto-load on mount so the panel reflects the actual backend mode without
  // requiring the operator to click a hidden button. setState happens in the
  // .then callback (treated as an external-system update, which the rule allows).
  useEffect(() => {
    if (loaded) return
    let active = true
    Promise.all([
      api.ringSimulationStatus(),
      api.ringSimulationDevices().catch(() => []),
      api.ringSimulationEvents().catch(() => []),
    ]).then(([next, nextDevices, nextEvents]) => {
      if (!active) return
      setStatus(next); setDevices(nextDevices); setSimEvents(nextEvents); setError('')
      setLoaded(true)
    }).catch((e) => {
      if (!active) return
      setError(e instanceof Error ? e.message : 'Could not load simulation status')
      setLoaded(true)
    })
    return () => { active = false }
  }, [loaded])

  async function load() {
    setError('')
    try {
      const [next, nextDevices, nextEvents] = await Promise.all([
        api.ringSimulationStatus(),
        api.ringSimulationDevices().catch(() => []),
        api.ringSimulationEvents().catch(() => []),
      ])
      setStatus(next); setDevices(nextDevices); setSimEvents(nextEvents)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load simulation status')
    }
  }

  async function run(scenario: string) {
    try {
      setError('')
      const result = await api.ringSimulationScenario(scenario)
      setLast({ scenario, events: result.events })
      const next = await api.ringSimulationEvents()
      setSimEvents(next)
      setRingEvents([...next.map(event => ({ ...event, is_simulation: true })), ...ringEvents].slice(0, 100))
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    }
  }

  function renderLive() {
    return <section className="ring-panel"><div className="section-heading"><div><span className="integration-emblem"><Icon name="activity" size={24} /></span><h2>Ring simulation lab</h2></div><Badge tone="amber">RING_MODE=live</Badge></div><p>Deterministic scenarios are only available when the backend is started with <code>RING_MODE=simulation</code>.</p><p className="fine">Live mode expects real Ring webhooks and never fabricates events.</p><p className="fine">Backend reports: <code>{(status || {}).mode || 'unknown'}</code></p><TaskButton run={load}>Reload simulation status</TaskButton></section>
  }

  function renderSimulation() {
    return <section className="ring-panel"><div className="section-heading"><div><span className="integration-emblem"><Icon name="activity" size={24} /></span><h2>Ring simulation lab</h2></div><Badge tone="amber">Simulation environment</Badge></div>
      <p>Send a simulated Ring signal through Nodum's verified event pipeline. Review the received signal and its resulting inbox state before any downstream action.</p>
      <ol className="signal-flow" aria-label="Ring signal processing flow"><li><strong><Icon name="device" size={17} /> Signal</strong><p>A scenario emits a simulated device event.</p></li><li><strong><Icon name="inbox" size={17} /> Nodum receives</strong><p>Verify, normalize and record the event.</p></li><li><strong><Icon name="access" size={17} /> Context &amp; policy</strong><p>Review the signal and confirm the affected zone.</p></li><li><strong><Icon name="check" size={17} /> Action &amp; state</strong><p>Inbox receipt is recorded. Signals never unlock doors.</p></li></ol>
      <details className="pipeline-details"><summary>How this simulation is processed</summary><p className="fine">Scenarios sign a v1.1 webhook envelope and use the existing Ring receive-event path for signature verification, normalization, deduplication and persistent inbox storage. Downstream actions require operator review.</p></details>
      {status && status.account && <p className="fine">Seeded simulation account: <strong>{status.account.account_id}</strong> · status {status.account.status} · environment {status.account.environment}.</p>}
      <h3 className="subsection-title">Choose a signal scenario</h3><div className="scenario-grid">{status && status.scenarios.map(s => <article className="scenario" key={s.name}><div className="row"><strong>{s.label}</strong><Badge tone="amber">simulation</Badge></div><p>{s.description}</p><small>{s.event_count} event{s.event_count === 1 ? '' : 's'} per run · flows into the real Ring inbox</small><TaskButton run={async () => run(s.name)}>Run {s.label}</TaskButton></article>)}</div>
      {last && <div className="scenario-result"><h3>Delivery results / {status?.scenarios.find(s => s.name === last.scenario)?.label || human(last.scenario)}</h3><ul className="delivery-list">{last.events.map(event => <li key={event.id}><div><strong>{human(event.signal)}</strong><small>{devices.find(d => d.id === event.device_id)?.name || event.device_id}</small></div><Badge tone={event.status === 'received' ? 'mint' : 'amber'}>{human(event.status)}</Badge><Badge tone="amber">Simulation</Badge></li>)}</ul><p className="fine">These states describe event delivery, not a completed building action. Flood signals still require operator review before an emergency is created.</p><button onClick={() => props.navigate('Activity')}>View in Activity <Icon name="arrow" size={15} /></button></div>}
      {devices.length > 0 && <details><summary>Simulated device catalog ({devices.length})</summary><ul className="sim-catalog">{devices.map(device => <li key={device.id}><Badge tone="amber">Simulation</Badge> <strong>{device.name}</strong> · <code>{device.id}</code> · kind {human(String((device.attributes as { kind?: string }).kind || 'unknown'))}</li>)}</ul></details>}
      {simEvents.length > 0 && <details open><summary>Simulation inbox ({simEvents.length})</summary><ul className="inbox-list">{[...simEvents].sort((a, b) => b.received_at.localeCompare(a.received_at)).slice(0, 12).map(event => <li key={event.id}><time dateTime={event.received_at}>{date(event.received_at)}</time><div><strong>{human(event.event_type)}</strong><small>Signal: {human(event.signal || 'unknown')} / {event.id.slice(0, 10)}</small></div><Badge tone="amber">Simulation</Badge></li>)}</ul><p className="fine">Latest 12 simulated signals. This demo inbox requires a signed-in manager; raw payloads are excluded.</p></details>}
      <p className="fine">All labels and badges in this section mark data as simulated. Live mode hides the simulator entirely.</p>
      <TaskButton run={load}>Refresh simulation status</TaskButton>
    </section>
  }

  if (!loaded && !error) {
    return <section className="ring-panel"><div className="section-heading"><div><span className="integration-emblem"><Icon name="activity" size={24} /></span><h2>Ring simulation lab</h2></div><Badge tone="amber">CHECKING…</Badge></div><p>Reading backend mode from <code>GET /ring/simulation</code>…</p><p className="fine">Status: <code>pending</code></p><TaskButton run={load}>Retry</TaskButton></section>
  }

  if (error) {
    return <section className="ring-panel"><div className="section-heading"><div><span className="integration-emblem"><Icon name="activity" size={24} /></span><h2>Ring simulation lab</h2></div><Badge tone="amber">API ERROR</Badge></div><p role="alert" className="error">{error}</p><p className="fine">The backend simulator endpoint did not respond. Verify that the API base URL and CORS configuration are correct, and that you are signed in.</p><TaskButton run={load}>Retry</TaskButton></section>
  }

  if (status && status.mode === 'simulation') return renderSimulation()
  return renderLive()
}

export function Integrations(props: PageProps) {
  const { data, actor, refresh, setRingEvents } = props
  const [ringDevices, setRingDevices] = useState<RingDevice[]>([])
  const [account, setAccount] = useState('')
  const [discovered, setDiscovered] = useState(false)
  return <><div className="page-intro"><span className="eyebrow">Signals &amp; orchestration</span><h1>Integrations</h1><p>Sensing establishes context. Policy decides. Connectors carry out authorized actions.</p></div><section className="ring-panel"><div className="section-heading"><div><span className="ring-word">ring</span><h2>Ring account & inventory</h2></div><Badge tone="blue">Partner API adapter</Badge></div><p>Cameras, doorbells, contact and flood/freeze signals. Ring events never unlock a door directly.</p><div className="notice">{data.integrations.some(i => i.mode === 'ring') ? 'Imported Ring inventory exists. Discover again to inspect the account; inventory is not proof of a current connection.' : 'No imported Ring inventory. Account linking and authenticated session setup are required.'}</div><AuthPanel /><ActionForm submit="Discover Ring devices & events" fields={[{ name: 'account', label: 'Linked Ring account ID', value: account }]} onSubmit={async v => { setAccount(v.account); setDiscovered(false); setRingDevices([]); setRingEvents([]); const [devices, events] = await Promise.all([api.ringDevices(v.account), api.ringEvents(v.account)]); setRingDevices(devices); setRingEvents(events); setDiscovered(true) }} /><p className="fine">Ring discovery requires your signed-in Nodum session. An unavailable account does not disable Nodum.</p>{discovered && !ringDevices.length && <Empty>No devices returned by this Ring account.</Empty>}{ringDevices.map(d => <div className="record" key={d.id}><h3>{d.name || d.id}</h3><ActionForm submit="Import & map device" fields={[{ name: 'zone', label: 'Physical zone', options: options(data.catalog.zones) }]} onSubmit={async v => { await api.importRing(account, d.id, v.zone); await refresh() }} /></div>)}</section><SimulationSection props={props} /><Section title="Building connectors" eyebrow="Software simulation"><div className="connector-grid">{data.integrations.filter(i => i.mode === 'simulated').map(i => <article className="connector" key={i.id}><div className="row"><strong>{i.name}</strong><Badge>{i.kind.replace('_', ' ')}</Badge></div><p>Provider: <code>{i.provider}</code> · {i.enabled ? <Badge tone="mint">enabled</Badge> : <Badge tone="amber">disabled</Badge>}</p><TaskButton run={async () => { await api.configure(i.id, !i.enabled, actor); await refresh() }}>{i.enabled ? 'Disable' : 'Enable'} {i.id}</TaskButton></article>)}</div></Section><Section title="Discovered devices" eyebrow="Device inventory"><div className="device-grid">{data.devices.length === 0 ? <Empty>No devices registered. Add a simulator or import a Ring device.</Empty> : data.devices.map(d => <DeviceCard key={d.id} device={d} props={props} />)}</div></Section></>
}
