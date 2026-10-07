export type AdminPage = 'Setup' | 'Building' | 'Hardware' | 'Integrations' | 'Accounts' | 'Roles & Permissions' | 'Policies' | 'System & Audit'
export const adminPages: AdminPage[] = ['Setup', 'Building', 'Hardware', 'Integrations', 'Accounts', 'Roles & Permissions', 'Policies', 'System & Audit']
export const setupSteps = ['Building', 'Floors & Areas', 'Hardware', 'Device Mapping', 'Accounts', 'Roles & Permissions', 'Policies', 'Review'] as const
export type SetupStep = typeof setupSteps[number]
export type Node = { id: string; name: string; kind: string; organization_id: string; building_id: string | null; parent_id: string | null; scope_id: string; demo: boolean; common: boolean; restricted: boolean; floor_order: number | null; building_type: string; address: string; description: string; connection_path: string | null; integration_id: string | null; device_type: string | null; capabilities: string[] }
export type Account = { id: string; username: string; name: string; person_id: string; active: boolean; scope_id: string }
export type Assignment = { id: string; user_id: string; role: string; scope_id: string; permissions: string[]; active: boolean; expires_at: string | null }
export type Audit = { id: string; action: string; resource_id: string; actor_user_id: string; at: string }
export const roleNames: Record<string, string> = { owner: 'Owner', admin: 'Admin', manager: 'Manager', security: 'Security', maintenance: 'Maintenance', business_admin: 'Business Admin', business_staff: 'Business Staff', resident: 'Resident' }
export const permissionNames: Record<string, string> = {
  'business.staff.manage': 'Manage Business Staff in own business',
  'announcements.read': 'View announcements', 'announcements.publish': 'Publish scoped announcements', 'maintenance.create': 'Report maintenance', 'maintenance.manage': 'Update maintenance requests',
  'ownership.manage': 'Appoint administrators', 'authorization.manage': 'Manage roles and permissions', 'accounts.read': 'View account configuration', 'accounts.manage': 'Create and manage accounts', 'affiliations.manage': 'Assign units and businesses', 'structure.configure': 'Configure building and areas', 'locations.read': 'View building structure', 'hardware.read': 'View hardware inventory', 'hardware.configure': 'Configure hardware and integrations', 'people.read': 'View people', 'businesses.read': 'View businesses', 'camera.view': 'View permitted camera content', 'visitors.read': 'View visitors', 'visitors.invite': 'Invite visitors', 'visitors.check_in': 'Check in visitors', 'access.read': 'View physical access grants', 'access.check': 'Evaluate access', 'maintenance.read': 'View maintenance work', 'incidents.read': 'View security incidents', 'incidents.manage': 'Manage incidents', 'activity.read': 'View activity', 'ring.read': 'View permitted Ring events', 'ring.manage': 'Configure Ring linking', 'ring.process': 'Process Ring events', 'simulation.run': 'Run Ring simulation', 'ai.use': 'Use scoped AI assistance',
}
export function visibleAdminPages(permissions: string[]): AdminPage[] {
  return adminPages.filter(page => page === 'Setup' || ({ Building: ['structure.configure'], Hardware: ['hardware.read', 'hardware.configure'], Integrations: ['hardware.read', 'hardware.configure', 'ring.manage'], Accounts: ['accounts.read', 'accounts.manage'], 'Roles & Permissions': ['authorization.manage', 'ownership.manage'], Policies: ['structure.configure'], 'System & Audit': ['structure.configure'] }[page] || []).some(p => permissions.includes(p)))
}
export function isAdminWorkspace(permissions: string[]) { return ['structure.configure', 'hardware.configure', 'accounts.manage', 'authorization.manage', 'ownership.manage'].some(p => permissions.includes(p)) }
export function blankNode(kind: string, parent: Node, name: string): Node {
  const id = crypto.randomUUID()
  return { id, name, kind, organization_id: parent.organization_id, building_id: kind === 'building' ? id : parent.building_id, parent_id: parent.id, scope_id: ['device', 'integration'].includes(kind) ? parent.scope_id : id, demo: parent.demo, common: false, restricted: false, floor_order: null, building_type: 'mixed_use', address: '', description: '', connection_path: null, integration_id: null, device_type: null, capabilities: [] }
}
export function readiness(nodes: Node[], accounts: Account[]) {
  return { buildings: nodes.filter(n => n.kind === 'building').length, floors: nodes.filter(n => n.kind === 'floor').length, areas: nodes.filter(n => ['location', 'unit', 'business', 'room'].includes(n.kind)).length, devices: nodes.filter(n => n.kind === 'device').length, unassigned: nodes.filter(n => n.kind === 'device' && n.parent_id === n.building_id).length, accounts: accounts.length }
}
