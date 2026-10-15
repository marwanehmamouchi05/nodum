import type { Visit } from '../resident/model'
import { useEffect, useRef } from 'react'
import { residentStatus } from '../resident/model'
import { Badge } from './ui'
import './visit-pass.css'

function visitWindow(visit: Visit) {
  const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'local time'
  const format = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: zone, timeZoneName: 'short' })
  return { zone, start: format.format(new Date(visit.starts_at)), end: format.format(new Date(visit.ends_at)) }
}

export function VisitPass({ visit, host, building, onClose }: { visit: Visit; host: string; building: string; onClose?: () => void }) {
  const window = visitWindow(visit)
  const card = useRef<HTMLElement>(null)
  useEffect(() => {
    const caller = document.activeElement instanceof HTMLElement ? document.activeElement : null
    card.current?.focus({ preventScroll: true })
    card.current?.scrollIntoView({ block: 'center', behavior: 'instant' })
    return () => { if (caller?.isConnected) caller.focus() }
  }, [visit.id])
  return <article ref={card} tabIndex={-1} className="visit-pass" aria-label="Visitor pass record">
    <div className="visit-pass-edge" aria-hidden="true"><span/><span/><span/><span/><span/></div>
    <div className="visit-pass-header"><div><span className="visit-pass-label">Visitor pass</span><h2>{visit.name}</h2></div><Badge tone={visit.status === 'cancelled' || visit.status === 'expired' ? 'amber' : visit.status === 'arrived' ? 'mint' : ''}>{residentStatus(visit.status)}</Badge></div>
    <div className="visit-pass-grid"><div><small>Host</small><strong>{host}</strong></div><div><small>Destination</small><strong>{visit.destination}</strong></div><div><small>Building</small><strong>{building}</strong></div><div><small>Valid window</small><strong>{window.start}<br/>to {window.end}</strong><small>Times shown in {window.zone}</small></div></div>
    <div className="visit-pass-truth"><strong>Visit record only</strong><p>{visit.logical_authorization === 'Active' || visit.logical_authorization === 'Scheduled' ? `Logical visit authorization: ${visit.logical_authorization.toLowerCase()}.` : `Logical visit authorization: ${visit.logical_authorization}.`} No scannable visitor credential is issued, and this pass does not unlock a door.</p></div>
    {onClose && <button type="button" onClick={onClose}>Close pass</button>}
  </article>
}
