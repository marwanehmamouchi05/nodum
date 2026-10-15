import { Badge } from '../components/ui'
import { date } from '../components/format'
import { Icon } from '../components/Icon'
import type { BusinessSnapshot } from './model'

export function BusinessReception({ data, canInvite, onInvite, onReview }: { data: BusinessSnapshot; canInvite: boolean; onInvite: () => void; onReview: () => void }) {
  const today = new Date(data.at).toDateString()
  const visits = data.visitors.filter(v => ['expected', 'arrived', 'active'].includes(v.status) && (v.status !== 'expected' || new Date(v.starts_at).toDateString() === today)).sort((a, b) => a.starts_at.localeCompare(b.starts_at)).slice(0, 5)
  const expected = data.visitors.filter(v => v.status === 'expected' && new Date(v.starts_at).toDateString() === new Date(data.at).toDateString()).length
  const arrived = data.visitors.filter(v => v.status === 'arrived').length
  const active = data.visitors.filter(v => v.status === 'active').length
  const signal = [...data.ring].sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0]
  return <section className="business-reception" aria-label="Reception overview">
    <div className="business-reception-top"><div><span className="business-eyebrow">Reception snapshot</span><h2>Visitor reception</h2><p>{data.floor || 'Business area'} · Updated {date(data.at)}</p></div><div className="business-reception-actions">{canInvite && <button className="primary" onClick={onInvite}><Icon name="visitors"/>Invite visitor</button>}</div></div>
    <div className="business-visit-stats" aria-label="Visitor statuses"><div><strong>{expected}</strong><span>Expected today</span></div><div><strong>{arrived}</strong><span>Arrived</span></div><div><strong>{active}</strong><span>Active visits</span></div></div>
    <div className={`business-reception-grid ${signal ? '' : 'no-signal'}`}>
      <section className="business-today-list"><div className="business-section-title"><h3>Today’s visitors</h3><button onClick={onReview}>All visits</button></div>{visits.length ? visits.map(visit => <article className="business-visit-row" key={visit.id}><time>{new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(visit.starts_at))}</time><div><strong>{visit.name}</strong><small>{visit.destination}</small></div><Badge>{visit.status === 'expected' ? 'Expected' : visit.status === 'arrived' ? 'Arrived' : 'Active'}</Badge></article>) : <p>No visitors expected today.</p>}</section>
      {signal ? <section className="business-arrival-review"><div className="business-section-title"><h3>Arrival signals</h3>{signal?.simulated && <Badge tone="blue">Simulation</Badge>}</div>{signal ? <><strong>Ring arrival signal received</strong><p>{signal.message}</p><small>{date(signal.at)} · Identity unverified</small><button className="primary" onClick={onReview}>Review visitor records</button><p className="fine">This Ring signal does not identify a visitor or unlock a door.</p></> : null}</section> : <p className="fine business-no-signal">No recent Ring arrival signals in this business scope.</p>}
    </div>
  </section>
}
