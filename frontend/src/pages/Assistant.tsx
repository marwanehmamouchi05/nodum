import { Icon } from '../components/Icon'
import { useState } from 'react'
import { api, ApiError, AgentUnavailableError } from '../api/client'
import type { AgentResponse, ToolResult } from '../api/types'
import type { PageProps } from './shared'
import { ActionForm, Badge, TaskButton, Policy } from '../components/ui'
import { GuidePanel } from '../guide/GuidePanel'
import { guideFallback } from '../guide/fallback'
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
export function Assistant({ actor, refresh, navigate, guideContext = 'AI Assistant', guideInitiallyOpen = false }: PageProps) {
  const [conversation, setConversation] = useState<{ prompt: string; response: AgentResponse }[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'ai' | 'guide'>(guideInitiallyOpen ? 'guide' : 'ai')
  const [guideEntry, setGuideEntry] = useState<string>()
  const [fallback, setFallback] = useState<'connection' | 'provider'>()
  async function send(message: string) {
    if (busy) return false
    setBusy(true); setError(''); setFallback(undefined)
    try {
      const response = await api.chat(message, actor)
      setConversation(previous => [...previous, { prompt: message, response }])
      if (response.status === 'unavailable') { setGuideEntry('ai-unavailable'); setFallback('provider'); setMode('guide'); return false }
      return true
    } catch (e) {
      if (e instanceof AgentUnavailableError) {
        setConversation(previous => [...previous, { prompt: message, response: e.response }])
      } else {
        setError(e instanceof Error ? e.message : 'Assistant unavailable')
      }
      const outage = guideFallback(e instanceof ApiError ? e.status : undefined)
      if (outage) { setGuideEntry(outage === 'connection' ? 'backend-connection' : 'ai-unavailable'); setFallback(outage); setMode('guide') }
      // An unavailable response is reviewable, but is never a successful action.
      return false
    } finally {
      setBusy(false)
    }
  }
  return <div className="assistant-page">
    <div className="assistant-emblem"><Icon name="assistant" size={29} /></div>
    <div className="page-intro"><span className="eyebrow">Building intelligence &amp; support</span><h1>AI Assistant</h1><p>Use conversational AI for building requests, or built-in guidance for setup and workflow help.</p></div>
    <div className="assistant-modes" role="group" aria-label="Assistance mode">
      <button aria-pressed={mode === 'ai'} onClick={() => setMode('ai')}><Icon name="assistant" size={18} /><span><strong>AI assistance</strong><small>Powered by Amazon Bedrock</small></span></button>
      <button aria-pressed={mode === 'guide'} onClick={() => setMode('guide')}><Icon name="inbox" size={18} /><span><strong>Nodum Guide</strong><small>Built-in help / works without AI</small></span></button>
    </div>
    {fallback && <div className="notice guide-fallback" role="status"><strong>{fallback === 'connection' ? 'The AI request could not reach Nodum.' : 'AI assistance is unavailable for this request.'}</strong><p>Nodum Guide is ready with local help. It does not execute actions or inspect live building state. You can return to AI assistance and deliberately send another request.</p></div>}
    {error && <p className="error" role="alert">{error}</p>}
    {mode === 'guide' && <GuidePanel initialPage={guideContext} entryTopic={guideEntry} navigate={page => { if (page === 'AI Assistant') setMode('ai'); else navigate(page) }} />}
    {mode === 'ai' && <><div className="prompt-grid">{prompts.map(p => <button disabled={busy} key={p} onClick={() => void send(p)}>{p}<Icon name="arrow" size={17} /></button>)}</div><p className="notice">Your request and relevant tool results are sent to Amazon Bedrock. Do not enter passwords, tokens, or sensitive personal details. AI explanations are not access permissions. Structured policy results are authoritative. Changes require your explicit confirmation.</p><p className="fine">AI availability is checked only when you send a request. Nodum Guide never contacts Bedrock.</p></>}
    {conversation.length > 0 && <section className="assistant-record" aria-label="AI request record"><h2>AI request record</h2><p className="fine">These are AI requests and returned tool results, separate from built-in guidance. Proposals still require explicit review and confirmation.</p><div className="conversation" aria-live="polite">{conversation.map((turn, i) => <article key={i}><div className="user-message">{turn.prompt}</div><div className="ai-message" role={turn.response.status === 'unavailable' ? 'alert' : undefined}><Badge tone={turn.response.status === 'unavailable' ? 'amber' : ''}>{turn.response.status === 'unavailable' ? (turn.response.tool_results.length ? 'AI unavailable / preserved tool results' : 'AI unavailable') : 'AI explanation / ' + turn.response.status}</Badge><p>{turn.response.explanation}</p>{turn.response.tool_results.map((r, n) => <Tool key={n} result={r} actor={actor} refresh={refresh} />)}</div></article>)}</div></section>}
    {busy && <p className="notice" role="status">Nodum is gathering context...</p>}
    {mode === 'ai' && <><ActionForm disabled={busy} submit={busy ? 'Request in progress...' : 'Ask Nodum'} fields={[{ name: 'message', label: 'Your building request' }]} onSubmit={async v => send(v.message)} /><p className="fine">Requests are independent; the existing API does not accept conversation history. Select an operator in the sidebar before proposing changes.</p></>}
  </div>
}
