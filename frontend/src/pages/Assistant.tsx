import { useState } from 'react'
import { api } from '../api/client'
import type { AgentResponse, ToolResult } from '../api/types'
import type { PageProps } from './shared'
import { ActionForm, Badge, TaskButton, Policy } from '../components/ui'
import { date } from '../components/format'
const prompts = ['Who is authorized in the basement?', 'Can Ahmed access the machine room?', 'What emergencies are active?', 'I’m here for Atlas Dental.', 'My guest Youssef is arriving tonight.']
function object(value: unknown): Record<string, unknown> { return value !== null && typeof value === 'object' ? value as Record<string, unknown> : {} }
function Tool({ result, actor, refresh }: { result: ToolResult; actor: string; refresh: () => Promise<void> }) {
  const [confirmed, setConfirmed] = useState<ToolResult>()
  const data = object(result.data)
  const displayed = confirmed || result
  const record = object(displayed.data)
  const isDecision = typeof record.allowed === 'boolean' && typeof record.reason === 'string'
  return <div className="tool-result"><div className="row"><strong>{result.tool.replaceAll('_', ' ')}</strong><Badge tone={displayed.status === 'error' ? 'red' : 'mint'}>{displayed.status.replaceAll('_', ' ')}</Badge></div>{isDecision ? <Policy decision={{ allowed: record.allowed as boolean, reason: record.reason as string }} /> : <><small>Structured backend tool result</small><pre>{JSON.stringify(displayed.data, null, 2)}</pre></>}{result.status === 'confirmation_required' && !confirmed && typeof data.id === 'string' && <><p>Review the exact arguments above. Actor: {String(data.actor_id)} · expires {date(String(data.expires_at))}</p><TaskButton run={async () => { if (data.actor_id !== actor) throw new Error('Select the proposing operator before confirming.'); if (Date.parse(String(data.expires_at)) <= Date.now()) throw new Error('Proposal expired. Ask Nodum for a new proposal.'); const response = await api.confirm(data.id as string, actor); setConfirmed(response); await refresh() }}>Confirm this action</TaskButton></>}</div>
}
export function Assistant({ actor, refresh }: PageProps) {
  const [conversation, setConversation] = useState<{ prompt: string; response: AgentResponse }[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function send(message: string) { if (busy) return false; setBusy(true); setError(''); try { const response = await api.chat(message, actor); setConversation(previous => [...previous, { prompt: message, response }]); return true } catch (e) { setError(e instanceof Error ? e.message : 'Assistant unavailable'); return false } finally { setBusy(false) } }
  return <div className="assistant-page"><div className="assistant-emblem">✳</div><div className="page-intro"><span className="eyebrow">NODUM INTELLIGENCE</span><h1>Start with a reason.</h1><p>“Tell Nodum why you are here. The building handles the rest.”</p></div><div className="prompt-grid">{prompts.map(p => <button disabled={busy} key={p} onClick={() => void send(p)}>{p}<span>↗</span></button>)}</div><p className="notice">AI explanations are not access permissions. Structured policy results are authoritative. Changes require your explicit confirmation.</p><div className="conversation" aria-live="polite">{conversation.map((turn, i) => <article key={i}><div className="user-message">{turn.prompt}</div><div className="ai-message"><Badge>AI EXPLANATION · {turn.response.status}</Badge><p>{turn.response.explanation}</p>{turn.response.tool_results.map((r, n) => <Tool key={n} result={r} actor={actor} refresh={refresh} />)}</div></article>)}{busy && <p className="notice" role="status">Nodum is gathering context…</p>}{error && <p className="error" role="alert">{error} Building APIs remain available.</p>}</div><ActionForm disabled={busy} submit={busy ? 'Request in progress…' : 'Ask Nodum ↗'} fields={[{ name: 'message', label: 'Your building request' }]} onSubmit={async v => send(v.message)} /><p className="fine">Requests are independent; the existing API does not accept conversation history. Select an operator in the sidebar before proposing changes.</p></div>
}
