import { useEffect, useState } from 'react'
import type { AccessEntry, RingEvent } from './api/types'
import { api } from './api/client'
import type { Session } from './api/client'
import { permittedPages } from './api/authorization'
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
import { ManagerWorkspace } from './manager/ManagerWorkspace'
import { ResidentWorkspace } from './resident/ResidentWorkspace'
import { BusinessWorkspace } from './business/BusinessWorkspace'
import { AdminWorkspace } from './admin/AdminWorkspace'
import { API_BASE } from './api/client'
import { workspaceChoices } from './workspaces'
import type { Workspace } from './workspaces'
import { ProductBar } from './ProductBar'
const pages: Page[] = ['Overview', 'Building', 'Visitors', 'Businesses', 'Access', 'Emergencies', 'Integrations', 'Activity', 'AI Assistant']
const symbols: IconName[] = ['overview', 'building', 'visitors', 'business', 'access', 'emergency', 'integrations', 'activity', 'assistant']
const screens = { Overview, Building, Visitors, Businesses, Access, Emergencies, Integrations, Activity, 'AI Assistant': Assistant }
function hashPage(): Page { try { const page = decodeURIComponent(window.location.hash.slice(1)); return pages.includes(page as Page) ? page as Page : 'Overview' } catch { return 'Overview' } }
function OperatorWorkspace() {
  const [session, setSession] = useState<Session>()
  const scoped = session?.authorization_mode === 'scoped'
  const permissions = scoped ? [...new Set(session?.authorization?.assignments.flatMap(a => a.permissions) || [])] : undefined
  const allowedPages = permissions ? permittedPages(pages, permissions) : pages
  const [page, setPage] = useState<Page>(hashPage)
  const [guideContext, setGuideContext] = useState<Page>('AI Assistant')
  const [guideInitiallyOpen, setGuideInitiallyOpen] = useState(false)
  const [actor, setActor] = useState('manager-1')
  const [decisions, setDecisions] = useState<AccessEntry[]>([])
  const [ringEvents, setRingEvents] = useState<RingEvent[]>([])
  const { data, errors, loading, updated, refresh } = useBuilding()
  useEffect(() => {
    let generation = 0
    let contextSignature: string | undefined
    let scopedContext = false
    const load = () => {
      const version = ++generation
      void api.session().then(next => {
        if (version !== generation) return
        scopedContext = next.authorization_mode === 'scoped'
        const signature = scopedContext ? JSON.stringify(next.authorization) : 'legacy'
        if (scopedContext && signature !== contextSignature) window.dispatchEvent(new Event('nodum:authorization-changed'))
        contextSignature = signature
        setSession(next)
        if (next.authorization_mode === 'scoped') setActor(next.user?.person_id || '')
      }).catch(() => {
        if (version !== generation) return
        if (scopedContext) { contextSignature = undefined; window.dispatchEvent(new Event('nodum:authorization-changed')) }
        setSession(previous => previous?.authorization_mode === 'scoped' ? { ...previous, user: null, authorization: null } : previous)
      })
    }
    const clear = () => { generation++; contextSignature = undefined; setSession(previous => previous ? { ...previous, user: null, authorization: null } : previous) }
    load()
    window.addEventListener('focus', load)
    window.addEventListener('nodum:signed-out', clear)
    return () => { generation++; window.removeEventListener('focus', load); window.removeEventListener('nodum:signed-out', clear) }
  }, [])
  useEffect(() => { const listener = () => setPage(hashPage()); window.addEventListener('hashchange', listener); return () => window.removeEventListener('hashchange', listener) }, [])
  useEffect(() => {
    const clear = () => { setDecisions([]); setRingEvents([]) }
    window.addEventListener('nodum:signed-out', clear)
    window.addEventListener('nodum:authorization-changed', clear)
    return () => { window.removeEventListener('nodum:signed-out', clear); window.removeEventListener('nodum:authorization-changed', clear) }
  }, [])
  const navigate = (next: Page) => { if (!allowedPages.includes(next)) return; if (next === 'AI Assistant' && page !== 'AI Assistant') { setGuideContext(page); setGuideInitiallyOpen(false) } window.history.pushState(null, '', '#' + encodeURIComponent(next)); setPage(next); window.scrollTo(0, 0) }
  const props: PageProps = { allowedPages: scoped ? allowedPages : undefined, applicationPermissions: permissions, guideContext, guideInitiallyOpen, unavailable: Object.keys(errors) as (keyof typeof data)[], data, actor, refresh, navigate, decisions, recordDecision: entry => setDecisions(previous => [entry, ...previous].slice(0, 100)), ringEvents, setRingEvents }
  const Screen = screens[page]
  return <div className="app-shell"><a className="skip-link" href="#content" onClick={event => { event.preventDefault(); document.getElementById("content")?.focus() }}>Skip to content</a><aside className="sidebar"><a className="brand" href="#Overview"><span className="brand-mark">n</span>nodum<span className="brand-period">.</span></a><div className="building-label"><span className="building-monogram"><Icon name="building" /></span><div><strong>Mixed-use building</strong><small>Building operations</small></div></div><nav aria-label="Main navigation">{pages.map((p, i) => allowedPages.includes(p) && <div className="nav-item" key={p}>{(i === 0 || i === 4 || i === 8) && <span className="nav-group">{i === 0 ? 'Building' : i === 4 ? 'Operations' : 'Intelligence'}</span>}<button key={p} className={page === p ? 'active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => navigate(p)}><Icon name={symbols[i]} />{p}</button></div>)}</nav><div className="sidebar-bottom"><div className="environment"><span className={`status-dot ${Object.keys(errors).length ? 'warning' : ''}`} />{loading ? 'Synchronizing' : Object.keys(errors).length ? 'Some services unavailable' : 'Backend connected'}</div>{scoped ? <p>Signed in as {session?.user?.username || 'No account'}<small>Permissions are enforced by the server.</small></p> : <><label>Operator context<select value={actor} onChange={e => setActor(e.target.value)}>{!data.catalog.people.length && <option value="manager-1">manager-1</option>}{data.catalog.people.map(p => <option key={p.id} value={p.id}>{p.name} · {p.role.replaceAll('_', ' ')}</option>)}</select></label><small>Prototype role context, not sign-in.</small></>}</div></aside><div className="workspace"><header className="topbar"><div><span className="breadcrumb">Building operations</span><span>/</span><strong>{page}</strong></div><div>{page !== 'AI Assistant' && <button onClick={() => { navigate('AI Assistant'); setGuideInitiallyOpen(true) }}><Icon name="assistant" size={15} />Page help</button>}<small>{updated ? `Last refresh ${date(updated)}` : 'Connecting to Nodum'}</small><button disabled={loading} onClick={() => void refresh()} aria-label="Refresh building data"><Icon name="refresh" size={15} />{loading ? 'Syncing…' : 'Refresh'}</button></div></header><main id="content" tabIndex={-1}><p className="notice demo-notice"><Badge tone="blue">Demo workspace</Badge> Operator prototype  /  Use synthetic demo data only. Simulated building actions do not control physical hardware.</p>{Object.values(errors).some(message => /Sign in|manager account|authentication/.test(message || '')) && <AuthPanel />}{loading && !updated && page !== 'AI Assistant' ? <div className="loading-state" role="status"><div className="skeleton" /><h2>Opening your building…</h2><p>Loading zones, visits and operational context.</p></div> : <>{Object.entries(errors).length > 0 && <div className="error resource-errors" role="alert"><strong>Some building data could not be refreshed. Counts and records may be incomplete or stale.</strong><details><summary>Connection details</summary>{Object.entries(errors).map(([resource, error]) => <p key={resource}>{resource}: {error}</p>)}</details></div>}{allowedPages.includes(page) ? <Screen key={scoped ? JSON.stringify(session?.authorization) : 'legacy'} {...props} /> : <p role="status">This section is outside your current permissions.</p>}</>}</main><footer>NODUM / INTELLIGENT BUILDING OPERATIONS<span>Context → Policy → Action</span></footer></div></div>
}


export default function App() {
  const [session, setSession] = useState<Session>()
  const [error, setError] = useState('')
  const [preferred, setPreferred] = useState<Workspace>()
  useEffect(() => {
    let generation = 0
    const load = () => {
      const version = ++generation
      void api.session().then(value => { if (version === generation) { setSession(value); setError('') } }).catch(() => { if (version === generation) { setSession(previous => previous?.authorization_mode === 'scoped' ? undefined : previous); setError('Nodum could not check your session. Reconnect and refresh this page.') } })
    }
    const clear = () => { generation++; setPreferred(undefined); setSession(previous => previous ? { ...previous, user: null, authorization: null } : previous) }
    load()
    window.addEventListener('focus', load)
    window.addEventListener('nodum:signed-out', clear)
    window.addEventListener('nodum:session-expired', clear)
    window.addEventListener('nodum:session-check', load)
    const timer = window.setInterval(load, 30000)
    return () => { generation++; window.clearInterval(timer); window.removeEventListener('focus', load); window.removeEventListener('nodum:signed-out', clear); window.removeEventListener('nodum:session-expired', clear); window.removeEventListener('nodum:session-check', load) }
  }, [])
  if (!session) return <main><h1>Nodum</h1><p role={error ? 'alert' : 'status'}>{error || 'Opening your workspace…'}</p>{error && <button onClick={() => location.reload()}>Try again</button>}</main>
  if (session.authorization_mode === 'scoped') {
    if (!session.user) return <main><h1>Welcome to Nodum</h1><p>Sign in to open your authorized workspace.</p><a href={API_BASE + '/auth/login'}>Sign in to Nodum</a></main>
    const choices = workspaceChoices(session)
    if (!choices.length) return <main><h1>Your account is ready</h1><p>An administrator must assign permissions before you can open a workspace.</p><button onClick={async () => { await api.logout(); window.dispatchEvent(new Event('nodum:signed-out')) }}>Sign out</button></main>
    const selected = preferred && choices.includes(preferred) ? preferred : choices[0]
    const key = session.user.id + JSON.stringify(session.authorization) + selected
    const select = (workspace: Workspace) => { if (!choices.includes(workspace)) return; history.replaceState(null, '', '#' + workspace + '/Home'); setPreferred(workspace); window.scrollTo(0, 0) }
    return <><ProductBar key={session.user.id + JSON.stringify(session.authorization)} session={session} choices={choices} selected={selected} select={select} />{selected === 'Admin' ? <AdminWorkspace key={key} session={session} /> : selected === 'Manager' ? <ManagerWorkspace key={key} session={session} /> : selected === 'Business' ? <BusinessWorkspace key={key} session={session} /> : selected === 'Resident' ? <ResidentWorkspace key={key} session={session} /> : <OperatorWorkspace key={key} />}</>
  }
  return <OperatorWorkspace />
}
