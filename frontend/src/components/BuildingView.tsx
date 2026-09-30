import { useState } from 'react'
import type { BuildingData } from '../api/types'
import { Badge, Empty } from './ui'
import { human } from './format'

export function BuildingView({ data, compact = false }: { data: BuildingData; compact?: boolean }) {
  const [selected, setSelected] = useState('')
  const floors = [...new Set(data.catalog.zones.map(z => z.floor))].sort((a, b) => (b ?? -100) - (a ?? -100))
  const chosen = data.catalog.zones.find(z => z.id === selected)
  const active = data.emergencies.filter(e => e.status === 'active')
  if (!floors.length) return <Empty>No zone inventory available. Connect to the backend to view the building.</Empty>
  return <div className={`building-view ${compact ? 'compact' : ''}`}><div className="building-schematic"><div className="roof"><span>N O D U M</span><i /></div>{floors.map(floor => <div className="floor" key={String(floor)}><div className="floor-number">{floor === null ? '—' : floor < 0 ? 'B' + Math.abs(floor) : String(floor).padStart(2, '0')}<small>{floor === 0 ? 'GROUND' : floor !== null && floor < 0 ? 'SERVICE' : 'FLOOR'}</small></div><div className="floor-rooms">{data.catalog.zones.filter(z => z.floor === floor).map(zone => { const affected = active.some(e => e.affected_zone_ids.includes(zone.id)); const confirmed = data.journeys.filter(j => j.current_confirmed_zone_id === zone.id); return <button key={zone.id} onClick={() => setSelected(zone.id)} className={`room ${zone.zone_type} ${selected === zone.id ? 'selected' : ''} ${affected ? 'affected' : ''}`} aria-pressed={selected === zone.id}><span className="room-windows" aria-hidden="true">▯ ▯ ▯ ▯</span><strong>{zone.name}</strong><small>{affected ? 'Incident active' : human(zone.zone_type)}{confirmed.length > 0 && ` · ${confirmed.length} last confirmed`}</small></button> })}</div></div>)}<div className="foundation"><span>Building section</span><span>Zone-based context · not live tracking</span></div></div>{chosen && <div className="zone-detail"><div><Badge>{human(chosen.zone_type)}</Badge><h3>{chosen.name}</h3><p>{chosen.restricted ? 'Restricted zone · explicit authorization required' : 'Access governed by deterministic policy'}</p></div><div><small>LOCATED DEVICES</small><p>{data.devices.filter(d => d.zone_id === chosen.id).map(d => d.name).join(', ') || 'None registered'}</p><small>LAST CONFIRMED JOURNEYS</small><p>{data.journeys.filter(j => j.current_confirmed_zone_id === chosen.id).map(j => data.catalog.people.find(p => p.id === j.person_id)?.name || j.person_id).join(', ') || 'No confirmed transitions'}</p></div></div>}</div>
}
