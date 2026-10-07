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
import { Badge } from './components/ui'
import { AuthPanel } from './components/AuthPanel'
import { Icon } from './components/Icon'
import type { IconName } from './components/Icon'
import './App.css'
const pages: Page[] = ['Overview', 'Building', 'Visitors', 'Businesses', 'Access', 'Emergencies', 'Integrations', 'Activity', 'AI Assistant']
const symbols: IconName[] = ['overview', 'building', 'visitors', 'business', 'access', 'emergency', 'integrations', 'activity', 'assistant']
const screens = { Overview, Building, Visitors, Businesses, Access, Emergencies, Integrations, Activity, 'AI Assistant': Assistant }
function hashPage(): Page { try { const page = decodeURIComponent(window.location.hash.slice(1)); return pages.includes(page as Page) ? page as Page : 'Overview' } catch { return 'Overview' } }
export default function App() {
  const [page, setPage] = useState<Page>(hashPage)
  const [guideContext, setGuideContext] = useState<Page>('AI Assistant')
  const [guideInitiallyOpen, setGuideInitiallyOpen] = useState(false)
  const [actor, setActor] = useState('manager-1')
  const [decisions, setDecisions] = useState<AccessEntry[]>([])
  const [ringEvents, setRingEvents] = useState<RingEvent[]>([])
  const { data, errors, loading, updated, refresh } = useBuilding()
  useEffect(() => { const listener = () => setPage(hashPage()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener) }, [])
  useEffect(() => {
    const clear = () => { setDecisions([]); setRingEvents([]) }
    window.addEventListener('nodum:signed-out', clear)
    return () => window.removeEventListener('nodum:signed-out', clear)
  }, [])
  const navigate = (next: Page) => { if (next === 'AI Assistant' && page !== 'AI Assistant') { setGuideContext(page); setGuideInitiallyOpen(false) } window.history.pushState(null, '', '#' + encodeURIComponent(next)); setPage(next); window.scrollTo(0, 0) }
  const props: PageProps = { guideContext, guideInitiallyOpen, unavailable: Object.keys(errors) as (keyof typeof data)[], data, actor, refresh, navigate, decisions, recordDecision: entry => setDecisions(previous => [entry, ...previous].slice(0, 100)), ringEvents, setRingEvents }
  const Screen = screens[page]
  return <div className="app-shell"><a className="skip-link" href="#content" onClick={event => { event.preventDefault(); document.getElementById("content")?.focus() }}>Skip to content</a><aside className="sidebar"><a className="brand" href="#Overview"><span className="brand-mark">n</span>nodum<span className="brand-period">.</span></a><div className="building-label"><span className="building-monogram"><Icon name="building" /></span><div><strong>Mixed-use building</strong><small>Building operations</small></div></div><nav aria-label="Main navigation">{pages.map((p, i) => <div className="nav-item" key={p}>{(i === 0 || i === 4 || i === 8) && <span className="nav-group">{i === 0 ? 'Building' : i === 4 ? 'Operations' : 'Intelligence'}</span>}<button key={p} className={page === p ? 'active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => navigate(p)}><Icon name={symbols[i]} />{p}</button></div>)}</nav><div className="sidebar-bottom"><div className="environment"><span className={`status-dot ${Object.keys(errors).length ? 'warning' : ''}`} />{loading ? 'Synchronizing' : Object.keys(errors).length ? 'Some services unavailable' : 'Backend connected'}</div><label>Operator context<select value={actor} onChange={e => setActor(e.target.value)}>{!data.catalog.people.length && <option value="manager-1">manager-1</option>}{data.catalog.people.map(p => <option key={p.id} value={p.id}>{p.name} · {p.role.replaceAll('_', ' ')}</option>)}</select></label><small>Prototype role context, not sign-in.</small></div></aside><div className="workspace"><header className="topbar"><div><span className="breadcrumb">Building operations</span><span>/</span><strong>{page}</strong></div><div>{page !== 'AI Assistant' && <button onClick={() => { navigate('AI Assistant'); setGuideInitiallyOpen(true) }}><Icon name="assistant" size={15} />Page help</button>}<small>{updated ? `Last refresh ${date(updated)}` : 'Connecting to Nodum'}</small><button disabled={loading} onClick={() => void refresh()} aria-label="Refresh building data"><Icon name="refresh" size={15} />{loading ? 'Syncing…' : 'Refresh'}</button></div></header><main id="content" tabIndex={-1}><p className="notice demo-notice"><Badge tone="blue">Demo workspace</Badge> Operator prototype  /  Use synthetic demo data only. Simulated building actions do not control physical hardware.</p>{Object.values(errors).some(message => /Sign in|manager account|authentication/.test(message || '')) && <AuthPanel />}{loading && !updated && page !== 'AI Assistant' ? <div className="loading-state" role="status"><div className="skeleton" /><h2>Opening your building…</h2><p>Loading zones, visits and operational context.</p></div> : <>{Object.entries(errors).length > 0 && <div className="error resource-errors" role="alert"><strong>Some building data could not be refreshed. Counts and records may be incomplete or stale.</strong><details><summary>Connection details</summary>{Object.entries(errors).map(([resource, error]) => <p key={resource}>{resource}: {error}</p>)}</details></div>}<Screen {...props} /></>}</main><footer>NODUM / INTELLIGENT BUILDING OPERATIONS<span>Context → Policy → Action</span></footer></div></div>
}
