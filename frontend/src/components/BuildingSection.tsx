import { useMemo, useState } from 'react'
import type { Node } from '../admin/model'
import { Badge } from './ui'
import { Icon } from './Icon'
import './building-section.css'

export type SpatialItem = { id: string; location_id?: string | null; title: string; detail: string; category: 'attention' | 'visitor' | 'maintenance' | 'device'; simulated?: boolean }
type Space = { node: Node; wrapper?: Node; aliases: string[]; devices: Node[] }
type Floor = { node: Node; spaces: Space[] }

export function BuildingSection({ nodes, items = [], title = 'Building section', selectedId, onSelect, onConfigure, hideInspector = false }: { nodes: Node[]; items?: SpatialItem[]; title?: string; selectedId?: string; onSelect?: (id: string) => void; onConfigure?: (node: Node) => void; hideInspector?: boolean }) {
  const [overlay, setOverlay] = useState<SpatialItem['category']>('attention')
  const [view, setView] = useState<'section' | 'list'>('section')
  const [floorId, setFloorId] = useState('')
  const [localSelected, setSelected] = useState<{ name: string; detail: string; ids: string[] }>()
  const topology = useMemo<Floor[]>(() => nodes.filter(n => n.kind === 'floor').sort((a, b) => (b.floor_order ?? 0) - (a.floor_order ?? 0)).map(floor => {
    const wrappers = nodes.filter(n => n.kind === 'location' && n.parent_id === floor.id)
    const spaces: Space[] = wrappers.flatMap(wrapper => {
      const leaves = nodes.filter(n => n.parent_id === wrapper.id && ['unit', 'business', 'room'].includes(n.kind))
      return (leaves.length ? leaves.map(node => ({ node, wrapper: wrapper as Node | undefined })) : [{ node: wrapper, wrapper: undefined as Node | undefined }]).map(entry => ({
        ...entry,
        aliases: [entry.node.id, entry.node.scope_id, ...(entry.wrapper ? [entry.wrapper.id, entry.wrapper.scope_id] : [])],
        devices: nodes.filter(n => n.kind === 'device' && (n.parent_id === entry.node.id || n.parent_id === entry.wrapper?.id)),
      }))
    })
    const direct = nodes.filter(n => n.parent_id === floor.id && ['unit', 'business', 'room'].includes(n.kind))
    spaces.push(...direct.map(node => ({ node, aliases: [node.id, node.scope_id], devices: nodes.filter(n => n.kind === 'device' && n.parent_id === node.id) })))
    return { node: floor, spaces }
  }), [nodes])
  const external = nodes.find(n => n.id === selectedId)
  const externalSpace = topology.flatMap(f => f.spaces).find(s => s.node.id === selectedId)
  const selected = external ? { name: external.name, detail: external.kind === 'unit' ? 'Residential unit' : external.kind, ids: externalSpace?.aliases || [external.id, external.scope_id] } : localSelected
  const activeFloor = external ? topology.find(f => f.node.id === external.id || f.spaces.some(s => s.aliases.includes(external.id) || s.devices.some(d => d.id === external.id)))?.node.id : floorId
  const visibleItems = overlay === 'device' ? [] : items.filter(item => item.category === overlay)
  const allIds = new Set(topology.flatMap(f => [f.node.id, f.node.scope_id, ...f.spaces.flatMap(s => s.aliases)]))
  const located = (space: Space) => visibleItems.filter(item => item.location_id && space.aliases.includes(item.location_id))
  const unmapped = visibleItems.filter(item => !item.location_id || !allIds.has(item.location_id))
  const devicesUnmapped = nodes.filter(n => n.kind === 'device' && !nodes.some(parent => parent.id === n.parent_id && (parent.kind === 'floor' || parent.kind === 'location' || parent.kind === 'unit' || parent.kind === 'business' || parent.kind === 'room')))
  function chooseSpace(space: Space) {
    onSelect?.(space.node.id)
    setSelected({ name: space.node.name, detail: [space.wrapper?.name, space.node.kind === 'unit' ? 'Residential unit' : space.node.kind].filter(Boolean).join(' · '), ids: space.aliases })
  }
  function spaceName(space: Space) {
    return space.node.name || space.wrapper?.name.replace(/\s+zone$/i, '') || 'Configured area'
  }
  const controls = <div className="building-controls"><div role="group" aria-label="Building overlay">{(['attention', 'visitor', 'maintenance', 'device'] as const).map(category => <button key={category} type="button" aria-pressed={overlay === category} onClick={() => setOverlay(category)}>{category === 'visitor' ? 'Visitors' : category === 'device' ? 'Devices' : category[0].toUpperCase() + category.slice(1)}</button>)}</div><div role="group" aria-label="Building view"><button type="button" aria-pressed={view === 'section'} onClick={() => setView('section')}>Section</button><button type="button" aria-pressed={view === 'list'} onClick={() => setView('list')}>Floor list</button></div></div>
  return <section className="building-section-panel" aria-label={title}>
    <div className="building-section-heading"><div><h2>{title}</h2><p>Configured places and mapped records</p></div>{controls}</div>
    {!topology.length ? <div className="building-no-floors">No configured floors are available in your permitted view.</div> : <div className={`building-section-view ${view}`}>
      <div className="building-stack" aria-label="Building floors from roof to underground">
        {topology.map(floor => <div className={`building-floor-row ${floor.node.id === activeFloor ? 'is-selected' : ''} ${floor.node.floor_order === -1 ? 'is-service' : ''} ${floor.node.floor_order === 0 ? 'is-ground' : ''} ${floor.node.floor_order === 4 ? 'is-roof' : ''}`} key={floor.node.id}>
          <button className="building-floor-label" type="button" aria-pressed={floor.node.id === activeFloor} onClick={() => { setFloorId(floor.node.id); onSelect?.(floor.node.id); setSelected({ name: floor.node.name, detail: 'Configured floor', ids: [floor.node.id, floor.node.scope_id] }) }}><span>{floor.node.name}</span><small>{floor.spaces.length} {floor.spaces.length === 1 ? 'space' : 'spaces'}</small></button>
          <div className="building-slab" role="group" aria-label={`${floor.node.name} spaces`}>
            <div className="building-spaces">{floor.spaces.map(space => {
              const matches = overlay === 'device' ? space.devices : located(space)
              const count = matches.length
              const label = spaceName(space).replace(/\s+zone$/i, '')
              const apartment = label.match(/^Apartment\s+(.+)$/i)
              const compact = ({ 'Elevator machine room': 'Machine room', 'Electrical generators': 'Generators', 'Maintenance areas': 'Maintenance' } as Record<string, string>)[label] || label
              const meta = ['unit', 'business'].includes(space.node.kind) ? '' : space.node.kind === 'room' ? 'Service area' : space.node.common ? 'Shared area' : 'Area'
              return <button className={`building-space ${space.node.kind} ${/entrance/i.test(label) ? 'entrance-space' : ''} ${count ? `has-${overlay}` : ''}`} type="button" aria-label={label} key={space.node.id} aria-pressed={selected?.ids.some(id => space.aliases.includes(id)) || false} onClick={() => { setFloorId(floor.node.id); chooseSpace(space) }}>
                <span className="space-name">{apartment ? <><span>Apt.</span><span>{apartment[1]}</span></> : compact}</span>
                {meta && <span className="space-meta">{meta}</span>}
                {count > 0 && <span className={`space-marker ${overlay}`} aria-label={`${count} ${overlay} ${count === 1 ? 'record' : 'records'}`}>{count}</span>}
              </button>
            })}</div>
          </div>
        </div>)}
        <div className="building-base"><span>Building structure</span><span>Places shown from authorized configuration</span></div>
      </div>
      {view === 'list' && <div className="building-flat-list" aria-label="Flat floor list">{topology.map(floor => <section key={floor.node.id}><button type="button" aria-pressed={activeFloor === floor.node.id} onClick={() => { setFloorId(floor.node.id); onSelect?.(floor.node.id); setSelected({ name: floor.node.name, detail: 'Configured floor', ids: [floor.node.id, floor.node.scope_id] }) }}><Icon name="floor" />{floor.node.name}</button><div>{floor.spaces.map(space => <button key={space.node.id} type="button" onClick={() => { setFloorId(floor.node.id); chooseSpace(space) }}>{spaceName(space)} <small>{space.node.kind}</small></button>)}</div></section>)}</div>}
      {!hideInspector && selected && <aside className="building-inspector" aria-live="polite"><span className="building-inspector-label">Selected place</span><strong>{selected?.name || 'Choose a floor or space'}</strong><p>{selected?.detail || 'Select any configured place to inspect its mapped records.'}</p>{external && onConfigure && <button onClick={() => onConfigure(external)}>Configure {external.name}</button>}{selected && <div className="building-inspector-items">{overlay === 'device' ? nodes.filter(n => n.kind === 'device' && selected.ids.includes(n.parent_id || '')).map(device => <div key={device.id}><Icon name="device" /><button type="button" onClick={() => onSelect?.(device.id)}>{device.name}</button><Badge>Unverified</Badge></div>) : visibleItems.filter(item => item.location_id && selected.ids.includes(item.location_id)).map(item => <div key={item.id}><Icon name={item.category === 'visitor' ? 'visitors' : item.category === 'maintenance' ? 'maintenance' : 'alert'} /><span>{item.title}<small>{item.detail}</small></span>{item.simulated && <Badge tone="blue">Simulation</Badge>}</div>)}</div>}</aside>}
      {(overlay === 'device' ? devicesUnmapped.length > 0 : unmapped.length > 0) && <div className="building-unmapped"><strong>Not placed on the building</strong><p>These records do not have an explicit relationship to a configured space.</p>{overlay === 'device' ? devicesUnmapped.map(record => <div key={record.id}><Icon name="device" />{record.name} <Badge tone="amber">Unmapped</Badge></div>) : unmapped.slice(0, 5).map(record => <div key={record.id}><Icon name={record.category === 'visitor' ? 'visitors' : record.category === 'maintenance' ? 'maintenance' : 'alert'} />{record.title} <Badge tone="amber">Location not mapped</Badge></div>)}</div>}
    </div>}
  </section>
}
