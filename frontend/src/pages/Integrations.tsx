import { AuthPanel } from '../components/AuthPanel'
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Device, DeviceStatus, RingDevice, RingEvent, RingSimulationDelivery, RingSimulationStatus } from '../api/types'
import type { PageProps } from './shared'
import { options } from './shared'
import { ActionForm, Badge, Empty, Section, TaskButton } from '../components/ui'
import { date, human } from '../components/format'

function DeviceCard({ device, props }: { device: Device; props: PageProps }) {
  const [status, setStatus] = useState<DeviceStatus>()
  const { data, actor, refresh } = props
  return <article className="device-card"><div className="row"><span className="device-icon">{device.device_type.includes('elevator') ? '↕' : device.device_type.includes('reader') ? '▣' : device.provider === 'ring' ? '◉' : '⌑'}</span><Badge tone={device.simulated ? '' : 'blue'}>{device.simulated ? 'Simulation' : 'Ring inventory'}</Badge></div><h3>{device.name}</h3><p>{human(device.device_type)} · {device.provider}</p><small>Located in {data.catalog.zones.find(z => z.id === device.zone_id)?.name || device.zone_id}</small><div className="capabilities">{device.capabilities.map(c => <span key={c}>{human(c)}</span>)}</div><TaskButton run={async () => setStatus(await api.deviceStatus(device.id))}>Inspect status & mapping</TaskButton>{status && <div className="device-state"><Badge tone={status.available ? 'mint' : 'amber'}>{status.available ? 'Available' : 'Unavailable'}</Badge><p>Mapped: {status.mapping?.zone_ids.map(id => data.catalog.zones.find(z => z.id === id)?.name || id).join(', ') || 'Not mapped'}</p>{status.state && <p>{['door', 'smart_lock', 'turnstile'].includes(device.device_type) ? `Simulated lock: ${status.state.locked ? 'locked' : 'unlocked'}` : device.device_type.includes('elevator') ? `Cabin floor: ${status.state.current_floor ?? 'unknown'} · Authorized floor: ${status.state.authorized_floor ?? 'none'}` : status.state.route.join(' → ') || 'No active route'}</p>}<small>Snapshot at inspection, not live telemetry.</small></div>}<details><summary>Edit zone mapping</summary><Mapping device={device} zones={data.catalog.zones} save={async ids => { await api.map(device.id, ids, actor); setStatus(await api.deviceStatus(device.id)); await refresh() }} /></details></article>
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
      setRingEvents([...next, ...ringEvents].slice(0, 100))
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed')
    }
  }

  function renderLive() {
    return <section className="ring-panel"><div className="section-heading"><div><span className="ring-word">sim</span><h2>Ring Playground Simulation</h2></div><Badge tone="amber">RING_MODE=live</Badge></div><p>Deterministic scenarios are only available when the backend is started with <code>RING_MODE=simulation</code>.</p><p className="fine">Live mode expects real Ring webhooks and never fabricates events.</p><p className="fine">Backend reports: <code>{(status || {}).mode || 'unknown'}</code></p><TaskButton run={load}>Reload simulation status</TaskButton></section>
  }

  function renderSimulation() {
    return <section className="ring-panel"><div className="section-heading"><div><span className="ring-word">sim</span><h2>Ring Playground Simulation</h2></div><Badge tone="amber">SIMULATION</Badge></div>
      <p>Deterministic demo scenarios. Every click signs a v1.1 webhook envelope with <code>RING_SIGNING_KEY</code> and feeds it through the real <code>RingService.receive_event()</code> path: signature verification, normalization, dedup, persistent inbox, and downstream operator review. No frontend-only fakes.</p>
      {status && status.account && <p className="fine">Seeded simulation account: <strong>{status.account.account_id}</strong> · status {status.account.status} · environment {status.account.environment}.</p>}
      <div className="scenario-grid">{status && status.scenarios.map(s => <article className="scenario" key={s.name}><div className="row"><strong>{s.label}</strong><Badge tone="amber">simulation</Badge></div><p>{s.description}</p><small>{s.event_count} event{s.event_count === 1 ? '' : 's'} per run · flows into the real Ring inbox</small><TaskButton run={async () => run(s.name)}>Run scenario</TaskButton></article>)}</div>
      {last && <div className="scenario-result"><h3>Last run · {last.scenario}</h3><ul>{last.events.map(event => <li key={event.id}><Badge tone="amber">{event.signal}</Badge> <code>{event.event_type}</code> on <code>{event.device_id}</code> → <code>{event.status}</code></li>)}</ul><p className="fine">Open the Activity page to see these events in the unified timeline; process flood events via the existing /ring/events endpoint.</p></div>}
      {devices.length > 0 && <details><summary>Simulated device catalog ({devices.length})</summary><ul>{devices.map(device => <li key={device.id}><Badge tone="amber">sim</Badge> <strong>{device.name}</strong> · <code>{device.id}</code> · kind {human(String((device.attributes as { kind?: string }).kind || 'unknown'))}</li>)}</ul></details>}
      {simEvents.length > 0 && <details open><summary>Simulation inbox ({simEvents.length})</summary><ul>{simEvents.slice(0, 12).map(event => <li key={event.id}><Badge>{event.signal || 'unknown'}</Badge> <code>{event.event_type}</code> · {date(event.received_at)} · <code>{event.id.slice(0, 10)}</code></li>)}</ul><p className="fine">Use <code>GET /ring/simulation/events</code> for the full owner-only inbox. Raw payload excluded.</p></details>}
      <p className="fine">All labels and badges in this section mark data as simulated. Live mode hides the simulator entirely.</p>
      <p><TaskButton run={load}>Refresh simulation status</TaskButton></p>
    </section>
  }

  if (!loaded && !error) {
    return <section className="ring-panel"><div className="section-heading"><div><span className="ring-word">sim</span><h2>Ring Playground Simulation</h2></div><Badge tone="amber">CHECKING…</Badge></div><p>Reading backend mode from <code>GET /ring/simulation</code>…</p><p className="fine">Status: <code>pending</code></p><TaskButton run={load}>Retry</TaskButton></section>
  }

  if (error) {
    return <section className="ring-panel"><div className="section-heading"><div><span className="ring-word">sim</span><h2>Ring Playground Simulation</h2></div><Badge tone="amber">API ERROR</Badge></div><p role="alert" className="error">{error}</p><p className="fine">The backend simulator endpoint did not respond. Verify that the API base URL and CORS configuration are correct, and that you are signed in.</p><TaskButton run={load}>Retry</TaskButton></section>
  }

  if (status && status.mode === 'simulation') return renderSimulation()
  return renderLive()
}

export function Integrations(props: PageProps) {
  const { data, actor, refresh, setRingEvents } = props
  const [ringDevices, setRingDevices] = useState<RingDevice[]>([])
  const [account, setAccount] = useState('')
  const [discovered, setDiscovered] = useState(false)
  return <><div className="page-intro"><span className="eyebrow">ONE BUILDING. MANY SYSTEMS.</span><h1>Connected by Nodum.</h1><p>Sensing establishes context. Policy decides. Connectors carry out authorized actions.</p></div><section className="ring-panel"><div className="section-heading"><div><span className="ring-word">ring</span><h2>The building’s human entry point.</h2></div><Badge tone="blue">PARTNER API ADAPTER</Badge></div><p>Cameras, doorbells, contact and flood/freeze signals. Ring events never unlock a door directly.</p><div className="notice">{data.integrations.some(i => i.mode === 'ring') ? 'Imported Ring inventory exists. Discover again to inspect the account; inventory is not proof of a current connection.' : 'No imported Ring inventory. Account linking and authenticated session setup are required.'}</div><AuthPanel /><ActionForm submit="Discover Ring devices & events" fields={[{ name: 'account', label: 'Linked Ring account ID', value: account }]} onSubmit={async v => { setAccount(v.account); setDiscovered(false); setRingDevices([]); setRingEvents([]); const [devices, events] = await Promise.all([api.ringDevices(v.account), api.ringEvents(v.account)]); setRingDevices(devices); setRingEvents(events); setDiscovered(true) }} /><p className="fine">Ring discovery requires your signed-in Nodum session. An unavailable account does not disable Nodum.</p>{discovered && !ringDevices.length && <Empty>No devices returned by this Ring account.</Empty>}{ringDevices.map(d => <div className="record" key={d.id}><h3>{d.name || d.id}</h3><ActionForm submit="Import & map device" fields={[{ name: 'zone', label: 'Physical zone', options: options(data.catalog.zones) }]} onSubmit={async v => { await api.importRing(account, d.id, v.zone); await refresh() }} /></div>)}</section><SimulationSection props={props} /><Section title="Building connectors" eyebrow="SOFTWARE SIMULATORS"><div className="connector-grid">{data.integrations.filter(i => i.mode === 'simulated').map(i => <article className="connector" key={i.id}><div className="row"><strong>{i.name}</strong><Badge>{i.kind.replace('_', ' ')}</Badge></div><p>Provider: <code>{i.provider}</code> · {i.enabled ? <Badge tone="mint">enabled</Badge> : <Badge tone="amber">disabled</Badge>}</p><TaskButton run={async () => { await api.configure(i.id, !i.enabled, actor); await refresh() }}>{i.enabled ? 'Disable' : 'Enable'} {i.id}</TaskButton></article>)}</div></Section><Section title="Discovered devices" eyebrow="BUILDING INVENTORY"><div className="device-grid">{data.devices.length === 0 ? <Empty>No devices registered. Add a simulator or import a Ring device.</Empty> : data.devices.map(d => <DeviceCard key={d.id} device={d} props={props} />)}</div></Section></>
}