import { useCallback, useEffect, useRef, useState } from 'react'
import type { Session } from '../api/client'
import { Badge } from '../components/ui'
import { date } from '../components/format'
import { residentApi } from './api'
import { residentPages, currentNotices, residentStatus, residentError } from './model'
import type { ResidentPage, ResidentSnapshot, Notice } from './model'
import { ResidentForm } from './ResidentForm'
import { ResidentHelp } from './ResidentHelp'
import './resident.css'

export function ResidentWorkspace({ session }: { session: Session }) {
  const [page, setPage] = useState<ResidentPage>('Home')
  const [data, setData] = useState<ResidentSnapshot>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [help, setHelp] = useState(false)
  const [form, setForm] = useState(false)
  const [actionError, setActionError] = useState('')
  const [cancelBusy, setCancelBusy] = useState('')
  const [visitFilter, setVisitFilter] = useState('current')
  const generation = useRef(0)
  const refresh = useCallback(async () => {
    const version = ++generation.current
    setBusy(true)
    try { const next = await residentApi.snapshot(); if (generation.current === version) { setData(next); setError('') } }
    catch (e) { if (generation.current === version) { setData(undefined); setHelp(false); setError(residentError(e)) } }
    finally { if (generation.current === version) setBusy(false) }
  }, [])
  useEffect(() => {
    const initial = setTimeout(() => void refresh(), 0)
    const clear = () => { generation.current++; setData(undefined); setHelp(false); setForm(false) }
    const focused = () => void refresh()
    const timer = setInterval(focused, 60000)
    window.addEventListener('focus', focused); window.addEventListener('nodum:signed-out', clear)
    return () => { clear(); clearTimeout(initial); clearInterval(timer); window.removeEventListener('focus', focused); window.removeEventListener('nodum:signed-out', clear) }
  }, [refresh])
  function navigate(next: ResidentPage, openForm = false) { setPage(next); setHelp(false); setForm(openForm); setActionError(''); document.getElementById('resident-content')?.focus(); window.scrollTo(0, 0) }
  const notices = data ? currentNotices(data.notices) : []
  const canInvite = data?.units.some(u => u.can_invite)
  const canReport = data?.units.some(u => u.can_report)
  const aiAllowed = session.authorization?.assignments.some(a => a.permissions.includes('ai.use')) || false
  const notice = (n: Notice) => <article className="resident-notice" key={n.id}><h3>{n.title}</h3><p>{n.message}</p><small>Published {date(n.published_at)}{n.expires_at && ` · Until ${date(n.expires_at)}`}</small></article>
  return <div className="resident-shell"><a className="skip-link" href="#resident-content">Skip to content</a><header className="resident-header"><a href="#" onClick={e => { e.preventDefault(); navigate('Home') }} className="resident-brand">nodum<span>.</span></a><span>Your home</span><button disabled={busy} onClick={() => void refresh()} aria-label="Refresh your information">{busy ? 'Refreshing…' : 'Refresh'}</button></header><nav className="resident-nav" aria-label="Resident navigation">{residentPages.map(p => <button key={p} aria-current={page === p ? 'page' : undefined} onClick={() => navigate(p)}>{p}</button>)}</nav><main id="resident-content" tabIndex={-1}>
    {error && <div role="alert" className="error"><h1>We can’t open your home right now</h1><p>{error}</p><button onClick={() => void refresh()}>Try again</button></div>}
    {!data && !error && <div role="status" className="resident-loading"><h1>Welcome home</h1><p>Opening your information…</p></div>}
    {data && <>{data.units.some(u => u.demo) && <p className="resident-demo"><Badge tone="blue">Demo / Synthetic</Badge> Example home. No physical hardware is controlled.</p>}
    <div className="resident-heading"><h1>{page === 'Home' ? `Welcome, ${data.name}` : page === 'Visitors' ? 'Your visitors' : page === 'Maintenance' ? 'Your maintenance' : page === 'Access' ? 'Your building access' : 'Building notices'}</h1><p>{data.units.map(u => u.name).join(', ') || 'Your unit assignment is not available'}{page === 'Home' && data.units[0]?.floor && ` · ${data.units[0].floor}`}</p></div>
    {!data.units.length && <p className="notice">Your building team needs to assign an active unit and portal permissions before you can use these services.</p>}
    {page === 'Home' && <><section className="resident-section"><div className="resident-section-title"><h2>Building notices</h2><button onClick={() => navigate('Notices')}>View notices</button></div>{notices.length ? notices.slice(0, 2).map(notice) : <p>No current building notices.</p>}</section><div className="resident-home-summaries"><button onClick={() => navigate('Visitors')}><span>Your visitors</span><strong>{data.expected_today} expected today</strong><small>View your visits</small></button><button onClick={() => navigate('Maintenance')}><span>Maintenance</span><strong>{data.open_maintenance} open {data.open_maintenance === 1 ? 'request' : 'requests'}</strong><small>Follow your requests</small></button></div><section className="resident-section"><h2>Quick actions</h2><div className="resident-quick">{canInvite && <button className="primary" onClick={() => navigate('Visitors', true)}>Invite visitor</button>}{canReport && <button onClick={() => navigate('Maintenance', true)}>Report maintenance issue</button>}<button onClick={() => setHelp(true)}>Ask Nodum</button></div></section><div className="resident-access-summary"><strong>Access: {data.access_status}</strong><button onClick={() => navigate('Access')}>View your access</button></div></>}
    {page === 'Visitors' && <>{canInvite && <button className="primary" aria-expanded={form} onClick={() => setForm(!form)}>{form ? 'Close invitation form' : 'Invite visitor'}</button>}{form && <ResidentForm kind="visitor" units={data.units} refresh={refresh} />}<label className="resident-filter">Show visits<select value={visitFilter} onChange={e => setVisitFilter(e.target.value)}><option value="current">Current and expected</option><option value="all">All visits</option></select></label>{!data.visitors.filter(v => visitFilter === 'all' || !['expired', 'completed', 'cancelled'].includes(v.status)).length && <p className="resident-empty">No visitors scheduled.</p>}{data.visitors.filter(v => visitFilter === 'all' || !['expired', 'completed', 'cancelled'].includes(v.status)).map(v => <article className="resident-record" key={v.id}><div className="resident-record-title"><h2>{v.name}</h2><Badge>{residentStatus(v.status)}</Badge></div><p>{v.destination}</p><p>{date(v.starts_at)} — {date(v.ends_at)}</p>{v.note && <p>{v.note}</p>}<p className="fine">Visit authorization: {v.logical_authorization}. No physical door access granted.</p>{v.can_cancel && <details><summary>Cancel this visit</summary><p>Revoke this visitor’s logical authorization? This does not operate a door.</p><button disabled={cancelBusy === v.id} onClick={async () => { setCancelBusy(v.id); setActionError(''); try { await residentApi.cancel(v.id); await refresh() } catch (e) { setActionError(residentError(e)) } finally { setCancelBusy('') } }}>{cancelBusy === v.id ? 'Cancelling…' : 'Confirm cancellation'}</button></details>}</article>)}{data.ring.map(r => <article key={r.id} className="resident-record"><h2>Doorbell signal</h2><p>{r.message}</p><small>{date(r.at)}</small>{r.simulated && <Badge tone="blue">Simulation</Badge>}<p>No door was unlocked automatically.</p></article>)}{actionError && <p className="error" role="alert">{actionError}</p>}</>}
    {page === 'Maintenance' && <>{canReport && <button className="primary" aria-expanded={form} onClick={() => setForm(!form)}>{form ? 'Close issue form' : 'Report an issue'}</button>}{form && <ResidentForm kind="maintenance" units={data.units} refresh={refresh} />}{!data.maintenance.length && <p className="resident-empty">No maintenance requests.</p>}{data.maintenance.map(r => <article className="resident-record" key={r.id}><div className="resident-record-title"><h2>{r.title}</h2><Badge>{residentStatus(r.status)}</Badge></div><p>{r.location}</p><p>{r.description}</p><small>Reported {date(r.created_at)} · {r.priority} priority</small><details><summary>Updates ({r.updates.length})</summary>{!r.updates.length && <p>No updates yet. Your request has been submitted.</p>}{r.updates.map((u, i) => <div className="resident-update" key={i}><strong>{residentStatus(u.status)}</strong><small>{date(u.at)}</small>{u.message && <p>{u.message}</p>}</div>)}</details></article>)}</>}
    {page === 'Access' && <><p>Your personal access information. This page does not control doors.</p>{!data.access.length && <div className="resident-empty"><h2>Access information is not configured</h2><p>Residency alone does not grant physical door access. Contact your building team to verify your access.</p></div>}{data.access.map((a, i) => <article className="resident-record" key={i}><div className="resident-record-title"><h2>{a.area}</h2><Badge tone={a.status === 'Allowed' ? 'mint' : ''}>{a.status}</Badge></div><p>{a.reason}</p><small>{date(a.valid_from)} — {date(a.valid_until)}</small></article>)}</>}
    {page === 'Notices' && <>{notices.length ? notices.map(notice) : <p className="resident-empty">No current building notices.</p>}{data.notices.some(n => n.expired) && <details className="resident-archive"><summary>Expired notices</summary>{data.notices.filter(n => n.expired).map(notice)}</details>}</>}
    {page !== 'Home' && <button className="resident-help-link" aria-expanded={help} onClick={() => setHelp(!help)}>Ask Nodum / Get help</button>}{help && <ResidentHelp key={page + JSON.stringify(session.authorization)} page={page} actor={session.user!.person_id} units={data.units} aiAllowed={aiAllowed} refresh={refresh} />}
    </>}
  </main><footer className="resident-footer">Nodum · Your resident portal</footer></div>
}
