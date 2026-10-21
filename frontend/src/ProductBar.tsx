import { useEffect, useState } from 'react'
import { api, request } from './api/client'
import type { Session } from './api/client'
import type { Workspace } from './workspaces'
import { human } from './components/format'
import './product.css'
import './product-phase-g.css'

type DemoContext = { available: boolean; building?: string }
export function ProductBar({ session, choices, selected, select }: { session: Session; choices: Workspace[]; selected: Workspace; select: (workspace: Workspace) => void }) {
  const [demo, setDemo] = useState<DemoContext>({ available: false })
  const [open, setOpen] = useState(false)
  const [scenarios, setScenarios] = useState<{ name: string; label: string; description: string }[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const signature = JSON.stringify(session.authorization)
  const canSimulate = session.authorization?.assignments.some(a => a.permissions.includes('simulation.run'))
  useEffect(() => {
    let active = true
    if (canSimulate) void request<DemoContext>('/demo/context').then(value => { if (active) setDemo(value) }).catch(() => { if (active) setDemo({ available: false }) })
    return () => { active = false }
  }, [canSimulate, signature])
  async function openDemo() {
    setOpen(!open)
    if (!open) {
      setMessage('')
      try { setScenarios((await api.ringSimulationStatus()).scenarios) } catch { setMessage('Ring simulation is unavailable. Check the local demo setup and try again.') }
    }
  }
  async function run(name: string) {
    setBusy(true); setMessage('')
    try {
      const result = await api.ringSimulationScenario(name)
      const label = scenarios.find(s => s.name === name)?.label || human(name)
      const signals = result.events.map(event => human(event.signal)).join(', ')
      setMessage(`${label}: ${result.events.length} signed simulation events saved (${signals}). Manager updates automatically; Security and Activity show the latest signals alongside earlier events. Identity is unverified; no door was unlocked.`)
      window.dispatchEvent(new Event('nodum:ring-updated'))
    } catch { setMessage('The scenario could not be confirmed. Refresh before retrying; events may have been received.') }
    finally { setBusy(false) }
  }
  async function checkPlayground() {
    setBusy(true); setMessage('')
    try {
      const result = await request<{ source: string; devices: { name: string }[] }>('/ring/playground/devices')
      setMessage(`Official Ring Playground API responded: ${result.devices.length} sandbox device(s)${result.devices.length ? ': ' + result.devices.map(d => d.name).join(', ') : ''}. Discovery only; webhook delivery, visitor identity and physical control are not verified. Temporary access expires; the event buttons use a separate Nodum custom simulator.`)
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Official Ring Playground is unavailable. Generate a fresh temporary token in the Ring developer console.') }
    finally { setBusy(false) }
  }
  return <div className="product-bar" data-workspace={selected} data-multi-workspace={choices.length > 1} data-demo-controls={demo.available} data-session-version={session.authorization?.context_version}><div className="product-account"><span>Signed in as <strong>{session.user?.username}</strong></span>{demo.available && <span className="product-demo-label">DEMO / Synthetic</span>}{choices.length > 1 && <label>Switch workspace<select aria-label="Switch workspace" value={selected} onChange={e => select(e.target.value as Workspace)}>{choices.map(choice => <option key={choice}>{choice}</option>)}</select></label>}{demo.available && <button onClick={() => void openDemo()} aria-expanded={open}>Demo Mode</button>}<button onClick={async () => { try { await api.logout(); window.dispatchEvent(new Event('nodum:signed-out')) } catch { setMessage('Sign-out could not be confirmed. Reconnect and try again.') } }}>Sign out</button></div>{open && demo.available && <section className="product-demo-panel" aria-label="Ring demo controls"><h2>Ring signal → Nodum workflow</h2><button disabled={busy} onClick={() => void checkPlayground()}>Verify official Ring API</button><p>Official Playground discovery is separate from the custom event scenarios below. It requires a temporary server-side token.</p><p>Schedule a visitor in Resident or Business. Run an arrival signal here, then review it in Manager. Ring does not establish the visitor’s identity or destination.</p><div>{scenarios.map(s => <button key={s.name} disabled={busy} onClick={() => void run(s.name)} title={s.description}>{s.label}</button>)}</div><p>Simulation uses the signed event pipeline. Access remains policy-controlled. Nodum Edge is not installed.</p></section>}{message && <div className="product-feedback"><p role="status">{message}</p><button aria-label="Dismiss demo message" onClick={() => setMessage('')}>Dismiss</button></div>}</div>
}
