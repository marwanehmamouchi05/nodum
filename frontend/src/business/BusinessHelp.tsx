import { useState } from 'react'
import type { FormEvent } from 'react'
import { api, AgentUnavailableError } from '../api/client'
import type { AgentResponse, ToolResult } from '../api/types'
import { Badge } from '../components/ui'
import { date } from '../components/format'
import { businessError } from './model'
import type { BusinessSnapshot, BusinessPage } from './model'
const guidance: Record<BusinessPage,string> = {
  Home:'Today shows your authorized business records. Staff users see their own visitors, maintenance and access. Notices apply to your business, floor or building audience.',
  Visitors:'Invite someone to your assigned business for an exact arrival window. Cancel before arrival to revoke the logical authorization. Confirm arrival manually only when delegated. A Ring signal does not identify a visitor or unlock a door.',
  Staff:'Only delegated Business Admins can create Business Staff accounts and manage business memberships. Permission choices are bounded by your current authority and the Business Staff ceiling. Revocation does not suspend unrelated roles.',
  Maintenance:'Report an issue for your assigned business and follow status updates. Public team replies appear here; private operator notes do not. For emergencies, use your building’s emergency contact procedure.',
  Access:'These are personal physical authorizations and their current evaluation where configured. Application permissions and business affiliation do not grant door access. This page sends no actuator commands.',
  Notices:'Current notices include everyone/business audiences for your building, floor or business. Residential-only, unrelated business and future notices stay hidden. Expired notices are archived.',
  'My Business':'Only permitted registered devices appear. Unverified means no telemetry supports a stronger state. Device registration does not imply a working camera or live video capability.',
}
function record(value:unknown):Record<string,unknown>{return value&&typeof value==='object'?value as Record<string,unknown>:{}}
function Proposal({ result,data,actor,refresh }: { result:ToolResult; data:BusinessSnapshot; actor:string; refresh:()=>Promise<void> }){
  const [busy,setBusy]=useState(false),[done,setDone]=useState(false),[error,setError]=useState('')
  const action=record(result.data),values=record(action.arguments)
  if(!['business_invite_visitor','business_report_maintenance'].includes(result.tool)||values.affiliation_id!==data.affiliation_id||typeof action.id!=='string')return null
  const visit=result.tool==='business_invite_visitor'
  return <article className="business-record"><Badge tone="blue">Review before creating</Badge><h3>{String(visit?values.name:values.title)}</h3><p>{data.name}</p>{visit?<><p>{date(String(values.starts_at))} — {date(String(values.ends_at))}</p><p>No physical building access will be granted.</p></>:<><p>{String(values.description)}</p><p>Priority: {String(values.priority||'normal')}</p></>}<small>Proposal expires {date(String(action.expires_at))}</small>{!done&&<button disabled={busy} onClick={async()=>{setBusy(true);setError('');try{const result=await api.confirm(String(action.id),actor);if(result.status!=='success')throw Error('Unavailable');setDone(true);await refresh()}catch(e){setError(businessError(e))}finally{setBusy(false)}}}>{busy?'Creating…':visit?'Confirm visitor invitation':'Confirm maintenance request'}</button>}{done&&<p role="status" className="success">Created. Your business records have been refreshed.</p>}{error&&<p role="alert" className="error">{error}</p>}</article>
}
export function BusinessHelp({page,data,actor,refresh}:{page:BusinessPage;data:BusinessSnapshot;actor:string;refresh:()=>Promise<void>}){
  const [question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[response,setResponse]=useState<AgentResponse>(),[error,setError]=useState('')
  async function ask(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError('');setResponse(undefined);try{setResponse(await api.chat(question,actor))}catch(e){if(e instanceof AgentUnavailableError)setResponse(e.response);else setError(businessError(e))}finally{setBusy(false)}}
  return <section className="business-help" aria-label="Ask Nodum and Business Guide"><h2>Ask Nodum</h2><div className="business-guide"><Badge tone="blue">Nodum Guide · Always available</Badge><p>{guidance[page]}</p></div>{data.permissions.includes('ai.use')&&<><form onSubmit={ask}><label>Your question<input required maxLength={6000} value={question} onChange={e=>setQuestion(e.target.value)} placeholder={page==='Staff'?'Which staff members are active?':'Who is coming this afternoon?'} /></label><button type="submit" disabled={busy}>{busy?'Asking…':'Ask Nodum'}</button></form><p className="fine">AI uses your authorized business context. Requests may be sent to Amazon Bedrock. Changes require explicit confirmation.</p></>}{error&&<p role="alert" className="error">{error}</p>}{response&&<div aria-live="polite"><Badge>{response.status==='unavailable'?'AI unavailable · Use local Guide':'Nodum explanation'}</Badge><p>{response.explanation}</p>{response.tool_results.filter(r=>r.status==='confirmation_required').map(r=><Proposal key={String(record(r.data).id)} result={r} data={data} actor={actor} refresh={refresh}/>)}</div>}</section>
}
