import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, AgentUnavailableError } from '../api/client'
import type { AgentResponse, ToolResult } from '../api/types'
import type { ResidentPage, Unit } from './model'
import { residentError } from './model'
import { Badge } from '../components/ui'
import { date } from '../components/format'

const guidance: Record<ResidentPage, string> = {
  Home: 'Notices apply to your building, floor or unit. Your visitor and maintenance summaries contain only your records. A missing access configuration does not mean a door is open.',
  Visitors: 'Schedule a visitor for your own unit and their arrival window. A logical visit authorization grants no physical door access. Cancel a future visit before arrival to revoke it. Ring signals do not identify the visitor.',
  Maintenance: 'Describe the issue in your unit, then follow its status here. The building team can share a reply with you. Private operator notes stay private. For emergencies, use your building’s emergency contact procedure.',
  Access: 'This page shows personal authorizations and their current evaluation where configured. Allowed is an access decision, not a door command. Nodum does not infer physical access from residency alone.',
  Notices: 'Current notices include everyone/residential audiences for your assigned building, floor or unit. Scheduled, business-only and unrelated unit notices are hidden. Expired notices are kept in a separate archive.',
}
function record(value: unknown): Record<string, unknown> { return value && typeof value === 'object' ? value as Record<string, unknown> : {} }
function Proposal({ result, units, actor, refresh }: { result: ToolResult; units: Unit[]; actor: string; refresh: () => Promise<void> }) {
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const proposal = record(result.data), values = record(proposal.arguments)
  const unit = units.find(u => u.affiliation_id === values.affiliation_id)
  if (!['resident_invite_visitor', 'resident_report_maintenance'].includes(result.tool) || !unit || typeof proposal.id !== 'string') return null
  const visit = result.tool === 'resident_invite_visitor'
  return <article className="resident-record"><Badge tone="blue">Review before creating</Badge><h3>{String(visit ? values.name : values.title)}</h3><p>{unit.name}</p>{visit ? <><p>{date(String(values.starts_at))} — {date(String(values.ends_at))}</p>{values.note && <p>{String(values.note)}</p>}<p>No physical door access will be granted.</p></> : <><p>{String(values.description)}</p><p>Priority: {String(values.priority || 'normal')}</p></>}<small>Proposal expires {date(String(proposal.expires_at))}</small>{!done && <button disabled={busy} onClick={async () => { setBusy(true); setError(''); try { const r = await api.confirm(String(proposal.id), actor); if (r.status !== 'success') throw new Error('Action unavailable'); setDone(true); await refresh() } catch (e) { setError(residentError(e)) } finally { setBusy(false) } }}>{busy ? 'Creating…' : visit ? 'Confirm visitor invitation' : 'Confirm maintenance request'}</button>}{done && <p role="status" className="success">Created. Your records have been refreshed.</p>}{error && <p role="alert" className="error">{error}</p>}</article>
}
export function ResidentHelp({ page, actor, units, aiAllowed, refresh }: { page: ResidentPage; actor: string; units: Unit[]; aiAllowed: boolean; refresh: () => Promise<void> }) {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<AgentResponse>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(''); setResponse(undefined)
    try { setResponse(await api.chat(question, actor)) }
    catch (e) { if (e instanceof AgentUnavailableError) setResponse(e.response); else setError(residentError(e)) }
    finally { setBusy(false) }
  }
  return <section className="resident-help" aria-label="Ask Nodum and local help"><h2>How can we help?</h2><div className="resident-guide"><Badge tone="blue">Nodum Guide · Always available</Badge><p>{guidance[page]}</p></div>{aiAllowed && <><form onSubmit={ask}><label>Ask Nodum<input value={question} onChange={e => setQuestion(e.target.value)} maxLength={6000} required placeholder={page === 'Visitors' ? 'My cousin is coming tomorrow at 7' : page === 'Maintenance' ? 'My kitchen sink is leaking' : 'When does elevator maintenance finish?'} /></label><button disabled={busy} type="submit">{busy ? 'Asking Nodum…' : 'Ask Nodum'}</button></form><p className="fine">AI uses your authorized records. Requests may be sent to Amazon Bedrock. Changes require your explicit confirmation.</p></>}{error && <p role="alert" className="error">{error}</p>}{response && <div aria-live="polite"><Badge>{response.status === 'unavailable' ? 'AI unavailable · Use local Guide' : 'Nodum explanation'}</Badge><p>{response.explanation}</p>{response.tool_results.filter(r => r.status === 'confirmation_required').map(r => <Proposal key={String(record(r.data).id)} result={r} units={units} actor={actor} refresh={refresh} />)}</div>}</section>
}
