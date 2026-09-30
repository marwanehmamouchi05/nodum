import { useEffect, useState } from 'react'
import type { AccessEntry, RingEvent } from './api/types'
import { useBuilding } from './hooks/useBuilding'
import type { Page, PageProps } from './pages/shared'
import { Overview } from './pages/Overview'
import { Building } from './pages/Building'
import { Visitors } from './pages/Visitors'
import { Businesses } from './pages/Businesses'
import { Access } from './pages/Access'
import { Emergencies } from './pages/Emergencies'
import { Integrations } from './pages/Integrations'
import { Activity } from './pages/Activity'
import { Assistant } from './pages/Assistant'
import { date } from './components/format'
import './App.css'
const pages: Page[] = ['Overview', 'Building', 'Visitors', 'Businesses', 'Access', 'Emergencies', 'Integrations', 'Activity', 'AI Assistant']
const symbols = ['◫', '▥', '♧', '▦', '⌘', '△', '⊞', '≋', '✳']
const screens = { Overview, Building, Visitors, Businesses, Access, Emergencies, Integrations, Activity, 'AI Assistant': Assistant }
function hashPage(): Page { try { const page = decodeURIComponent(window.location.hash.slice(1)); return pages.includes(page as Page) ? page as Page : 'Overview' } catch { return 'Overview' } }
export default function App() {
  const [page, setPage] = useState<Page>(hashPage)
  const [actor, setActor] = useState('manager-1')
  const [decisions, setDecisions] = useState<AccessEntry[]>([])
  const [ringEvents, setRingEvents] = useState<RingEvent[]>([])
  const { data, errors, loading, updated, refresh } = useBuilding()
  useEffect(() => { const listener = () => setPage(hashPage()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener) }, [])
  const navigate = (next: Page) => { window.history.pushState(null, '', '#' + encodeURIComponent(next)); setPage(next); window.scrollTo(0, 0) }
  const props: PageProps = { unavailable: Object.keys(errors) as (keyof typeof data)[], data, actor, refresh, navigate, decisions, recordDecision: entry => setDecisions(previous => [entry, ...previous].slice(0, 100)), ringEvents, setRingEvents }
  const Screen = screens[page]
  return <div className="app-shell"><a className="skip-link" href="#content">Skip to content</a><aside className="sidebar"><a className="brand" href="#Overview"><span className="brand-mark">n</span>nodum<span className="brand-period">.</span></a><div className="building-label"><span className="building-monogram">N / 01</span><div><strong>Mixed-use building</strong><small>Building operations</small></div></div><nav aria-label="Main navigation">{pages.map((p, i) => <button key={p} className={page === p ? 'active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => navigate(p)}><span>{symbols[i]}</span>{p}{p === 'AI Assistant' && <i>↗</i>}</button>)}</nav><div className="sidebar-bottom"><div className="environment"><span className={`status-dot ${Object.keys(errors).length ? 'warning' : ''}`} />{loading ? 'Synchronizing' : Object.keys(errors).length ? 'Some services unavailable' : 'Backend connected'}</div><label>Operator context<select value={actor} onChange={e => setActor(e.target.value)}>{!data.catalog.people.length && <option value="manager-1">manager-1</option>}{data.catalog.people.map(p => <option key={p.id} value={p.id}>{p.name} · {p.role.replaceAll('_', ' ')}</option>)}</select></label><small>Prototype role context, not sign-in.</small></div></aside><div className="workspace"><header className="topbar"><div><span className="breadcrumb">WORKSPACE</span><span>/</span><strong>{page}</strong></div><div><small>{updated ? `Last refresh ${date(updated)}` : 'Connecting to Nodum'}</small><button disabled={loading} onClick={() => void refresh()} aria-label="Refresh building data">{loading ? 'Syncing…' : '↻ Refresh'}</button></div></header><main id="content" tabIndex={-1}>{loading && !updated ? <div className="loading-state" role="status"><div className="skeleton" /><h2>Opening your building…</h2><p>Loading zones, visits and operational context.</p></div> : <>{Object.entries(errors).length > 0 && <div className="error resource-errors" role="alert"><strong>Some building data could not be refreshed. Counts and records may be incomplete or stale.</strong><details><summary>Connection details</summary>{Object.entries(errors).map(([resource, error]) => <p key={resource}>{resource}: {error}</p>)}</details></div>}<Screen {...props} /></>}</main><footer>NODUM / INTELLIGENT BUILDING OPERATIONS<span>Context → Policy → Action</span></footer></div></div>
}
