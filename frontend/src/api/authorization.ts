import type { Page } from '../pages/shared'
import type { GuideTopic } from '../guide/topics'

const pagePermissions: Partial<Record<Page, readonly string[]>> = {
  Building: ['locations.read'], Visitors: ['visitors.read', 'visitors.invite'],
  Businesses: ['businesses.read'], Access: ['access.read', 'access.check'],
  Emergencies: ['incidents.read', 'incidents.manage'],
  Integrations: ['hardware.read', 'ring.read', 'ring.manage', 'simulation.run'],
  Activity: ['activity.read'],
}
export function permittedPages(pages: readonly Page[], permissions: readonly string[]): Page[] {
  return pages.filter(page => !pagePermissions[page] || pagePermissions[page]!.some(p => permissions.includes(p)))
}

const topicPermissions: Record<string, string> = {
  'ring-connect': 'ring.manage', 'ring-scenarios': 'simulation.run',
  'ring-simulation': 'simulation.run', devices: 'hardware.configure',
  'device-unavailable': 'hardware.read',
}
export function permittedTopic(topic: GuideTopic, pages?: readonly Page[], permissions?: readonly string[]) {
  return (!pages || topic.links.every(link => pages.includes(link.page)))
    && (!permissions || !topicPermissions[topic.id] || permissions.includes(topicPermissions[topic.id]))
}
