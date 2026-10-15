import { useState } from 'react'
import type { FormEvent } from 'react'
import { businessApi } from './api'
import { businessError, businessPermissionNames } from './model'
import type { BusinessSnapshot, Staff } from './model'
import type { Visit } from '../resident/model'

function PermissionChoices({ options, selected, change }: { options: string[]; selected: string[]; change: (values: string[]) => void }) {
  return <fieldset className="business-permissions"><legend>Business Staff permissions</legend>{options.map(p => <label key={p}><input type="checkbox" checked={selected.includes(p)} onChange={e => change(e.target.checked ? [...selected,p] : selected.filter(v => v !== p))} />{businessPermissionNames[p] || p}</label>)}<p className="fine">Only permissions delegated to you and permitted for Business Staff can be granted. Application permissions do not grant physical access.</p></fieldset>
}
export function BusinessForm({ kind, data, refresh, onVisitCreated }: { kind: 'visitor' | 'maintenance' | 'staff'; data: BusinessSnapshot; refresh: () => Promise<void>; onVisitCreated?: (visit: Visit) => void }) {
  const [permissions, setPermissions] = useState<string[]>(data.staff_options.filter(p => ['locations.read','announcements.read','visitors.read','maintenance.read','maintenance.create'].includes(p)))
  const [busy,setBusy] = useState(false), [error,setError] = useState(''), [success,setSuccess] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form=event.currentTarget; const values=Object.fromEntries(new FormData(form)) as Record<string,string>
    setBusy(true); setError(''); setSuccess('')
    try {
      if (kind==='visitor') { const visit = await businessApi.visit({affiliation_id:data.affiliation_id,name:values.name,note:values.note,starts_at:new Date(values.starts_at).toISOString(),ends_at:new Date(values.ends_at).toISOString()}); onVisitCreated?.(visit) }
      else if (kind==='maintenance') await businessApi.report({affiliation_id:data.affiliation_id,title:values.title,description:values.description,priority:values.priority})
      else await businessApi.addStaff({name:values.name,username:values.username,password:values.password,permissions})
      form.reset(); setSuccess(kind==='visitor' ? 'Visitor scheduled. Physical building access is not configured automatically.' : kind==='maintenance' ? 'Your maintenance request was submitted.' : 'Staff account created. Share the initial credentials through your approved private channel.'); await refresh()
    } catch(e) { setError(businessError(e)) } finally { setBusy(false) }
  }
  return <form className="business-form" onSubmit={submit}><h2>{kind==='visitor' ? 'Invite visitor' : kind==='maintenance' ? 'Report maintenance' : 'Add Business Staff'}</h2><p>For {data.name}</p><fieldset disabled={busy}>
    {kind==='visitor' ? <><label>Visitor name<input name="name" required maxLength={160} autoComplete="off" /></label><div className="business-date-fields"><label>Arrival window starts<input name="starts_at" type="datetime-local" required /></label><label>Arrival window ends<input name="ends_at" type="datetime-local" required /></label></div><label>Note (optional)<textarea name="note" rows={3} maxLength={1000} /></label><p className="fine">A temporary logical authorization is recorded for your business. No door or elevator access is granted.</p></> : kind==='maintenance' ? <><label>Problem<input name="title" required maxLength={160} placeholder="Air conditioning not cooling" /></label><label>Description<textarea name="description" rows={4} required maxLength={4000} /></label><label htmlFor="business-priority">Priority</label><select id="business-priority" name="priority" defaultValue="normal"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option></select><p className="fine">For emergencies, follow your building’s emergency contact procedure.</p></> : <><label>Staff name<input name="name" required maxLength={200} /></label><label>Login name<input name="username" required minLength={3} maxLength={128} autoComplete="off" /></label><label>Initial password<input name="password" required type="password" minLength={12} maxLength={128} autoComplete="new-password" /></label><p className="fine">Creates a real account using the existing sign-in flow. Email invitations and password reset are not available yet.</p><PermissionChoices options={data.staff_options} selected={permissions} change={setPermissions} /></>}
    <button type="submit" className="primary">{busy ? 'Saving…' : kind==='visitor' ? 'Schedule visitor' : kind==='maintenance' ? 'Submit request' : 'Create staff account'}</button></fieldset>{error && <p role="alert" className="error">{error}</p>}{success && <p role="status" className="success">{success}</p>}</form>
}
export function StaffEditor({ staff, options, refresh }: { staff: Staff; options: string[]; refresh: () => Promise<void> }) {
  const [permissions,setPermissions]=useState(staff.permissions.filter(p=>options.includes(p)))
  const [active,setActive]=useState(staff.active),[busy,setBusy]=useState(false),[error,setError]=useState(''),[success,setSuccess]=useState('')
  return <details><summary>Manage membership</summary><form className="business-form" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');setSuccess('');try {await businessApi.updateStaff(staff.id,{active,permissions});setSuccess('Business membership updated.');await refresh()}catch(e){setError(businessError(e))}finally{setBusy(false)}}}><fieldset disabled={busy}><label className="business-check"><input type="checkbox" checked={active} onChange={e=>setActive(e.target.checked)} />Active business membership</label><p className="fine">Revoking this membership removes access to this business. It does not suspend unrelated roles or restore an account suspended by building Admin.</p><PermissionChoices options={options} selected={permissions} change={setPermissions} /><button type="submit">{busy ? 'Saving…' : 'Save membership'}</button></fieldset>{error&&<p role="alert" className="error">{error}</p>}{success&&<p role="status" className="success">{success}</p>}</form></details>
}
