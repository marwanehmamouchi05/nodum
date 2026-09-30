import { useState } from 'react'
import type { ReactNode, FormEvent } from 'react'
import type { Decision } from '../api/types'

export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span> }
export function Empty({ children }: { children: ReactNode }) { return <div className="empty"><span>◌</span><p>{children}</p></div> }
export function Section({ title, eyebrow, children, action }: { title: string; eyebrow?: string; children: ReactNode; action?: ReactNode }) { return <section className="panel"><div className="section-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2></div>{action}</div>{children}</section> }
export function Policy({ decision }: { decision: Decision }) { return <div className={`policy ${decision.allowed ? 'allow' : 'deny'}`}><strong>{decision.allowed ? '✓ ALLOW' : '⊘ DENY'}</strong><span>{decision.reason}</span><small>Deterministic policy result</small></div> }
export type Field = { name: string; label: string; type?: string; options?: { value: string; label: string }[]; value?: string; optional?: boolean; min?: number; max?: number }
export function ActionForm({ title, fields, submit, onSubmit, disabled = false }: { disabled?: boolean; title?: string; fields: Field[]; submit: string; onSubmit: (values: Record<string, string>) => Promise<unknown> }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  async function send(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setBusy(true); setError(''); setSuccess(false)
    const values = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>
    try { const outcome = await onSubmit(values); setSuccess(outcome !== false) } catch (e) { setError(e instanceof Error ? e.message : 'Request failed') } finally { setBusy(false) }
  }
  return <form onSubmit={send} className="action-form">{title && <h3>{title}</h3>}<div className="form-grid">{fields.map(f => <label key={f.name}>{f.label}{f.options ? <select name={f.name} required={!f.optional} defaultValue={f.value || ''}><option value="">Select…</option>{f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select> : <input name={f.name} type={f.type || 'text'} defaultValue={f.value} required={!f.optional} min={f.min} max={f.max} />}</label>)}</div><button className="primary" disabled={busy || disabled}>{busy ? 'Working…' : submit}</button>{error && <p className="error" role="alert">{error}</p>}{success && <p className="success" role="status">Request completed.</p>}</form>
}
export function TaskButton({ children, run, className = '' }: { children: ReactNode; run: () => Promise<unknown>; className?: string }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  return <div className="task"><button className={className} disabled={busy} onClick={async () => { setBusy(true); setError(''); try { await run() } catch (e) { setError(e instanceof Error ? e.message : 'Request failed') } finally { setBusy(false) } }}>{busy ? 'Working…' : children}</button>{error && <p className="error" role="alert">{error}</p>}</div>
}
