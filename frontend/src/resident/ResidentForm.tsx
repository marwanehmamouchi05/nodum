import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Unit } from './model'
import type { Visit } from './model'
import { residentError } from './model'
import { residentApi } from './api'

export function ResidentForm({ kind, units, refresh, onVisitorCreated }: { kind: 'visitor' | 'maintenance'; units: Unit[]; refresh: () => Promise<void>; onVisitorCreated?: (visit: Visit) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const choices = units.filter(u => kind === 'visitor' ? u.can_invite : u.can_report)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form)) as Record<string, string>
    setBusy(true); setError(''); setSuccess('')
    try {
      const target = { affiliation_id: choices.length === 1 ? choices[0].affiliation_id : values.affiliation_id }
      if (kind === 'visitor') {
        const visit = await residentApi.visit({ ...target, name: values.name, note: values.note,
          starts_at: new Date(values.starts_at).toISOString(), ends_at: new Date(values.ends_at).toISOString() })
        onVisitorCreated?.(visit)
      }
      else await residentApi.report({ ...target, title: values.title, description: values.description, priority: values.priority })
      form.reset(); setSuccess(kind === 'visitor' ? 'Visitor scheduled. No physical door access was granted.' : 'Your maintenance request was submitted.'); await refresh()
    } catch (e) { setError(residentError(e)) } finally { setBusy(false) }
  }
  if (!choices.length) return <p>No permission to {kind === 'visitor' ? 'invite visitors' : 'report an issue'} is assigned to your unit. Contact your building team.</p>
  return <form className="resident-form" onSubmit={submit}><h2>{kind === 'visitor' ? 'Invite a visitor' : 'Report an issue'}</h2><p>{choices.length === 1 ? `For ${choices[0].name}` : 'Choose one of your units.'}</p><fieldset disabled={busy}>
    {choices.length > 1 && <label>Your unit<select name="affiliation_id" required>{choices.map(u => <option key={u.affiliation_id} value={u.affiliation_id}>{u.name}</option>)}</select></label>}
    {kind === 'visitor' ? <><label>Visitor name<input name="name" maxLength={160} required autoComplete="off" /></label><div className="resident-form-times"><label>Arrival window starts<input name="starts_at" type="datetime-local" required /></label><label>Arrival window ends<input name="ends_at" type="datetime-local" required /></label></div><label>Note (optional)<textarea name="note" maxLength={1000} rows={3} /></label><p className="fine">This records a temporary visit authorization for your unit. Physical door access is not configured through this invitation.</p></> : <><label>Problem<input name="title" maxLength={160} required placeholder="For example: Kitchen sink leaking" /></label><label>Description<textarea name="description" rows={4} maxLength={4000} required /></label><label>Priority<select name="priority" defaultValue="normal"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option></select></label><p className="fine">For an emergency, use your building’s emergency contact procedure. This form submits a maintenance request.</p></>}
    <button className="primary" type="submit">{busy ? 'Saving…' : kind === 'visitor' ? 'Schedule visitor' : 'Submit request'}</button></fieldset>{error && <p className="error" role="alert">{error}</p>}{success && <p className="success" role="status">{success}</p>}</form>
}
