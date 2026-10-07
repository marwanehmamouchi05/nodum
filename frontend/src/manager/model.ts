import type { Node } from '../admin/model'
import type { Appointment } from '../api/types'
export const managerPages = ['Overview', 'People', 'Visitors', 'Access', 'Maintenance', 'Security', 'Activity', 'Announcements'] as const
export type ManagerPage = typeof managerPages[number]
export function visibleManagerPages(permissions: string[]): ManagerPage[] {
  const rules: Record<ManagerPage, string[]> = { Overview: [], People: ['people.read', 'businesses.read'], Visitors: ['visitors.read', 'visitors.invite'], Access: ['access.read', 'access.check'], Maintenance: ['maintenance.read', 'maintenance.create', 'maintenance.manage'], Security: ['incidents.read', 'hardware.read', 'ring.read'], Activity: ['activity.read'], Announcements: ['announcements.read', 'announcements.publish'] }
  return managerPages.filter(p => p === 'Overview' || rules[p].some(rule => permissions.includes(rule)))
}
export type Maintenance = { id: string; title: string; description: string; location_name: string; reporter_name: string; priority: string; status: string; created_at: string; updated_at: string; assignee_id: string | null; assignee_name: string | null; can_manage: boolean; history: { status: string; at: string; note: string; actor_name: string }[] }
export type Visitor = { id: string; name: string; host: string; destination: string; start: string; end: string; status: string; source: string; appointment: Appointment | null; can_arrive?: boolean; can_check_in?: boolean; access_note?: string }
export type Snapshot = { at: string; operator_name: string; buildings: Node[]; nodes: Node[]; status: string; status_note: string; coverage: Record<string, boolean>; counts: { visitors: number; maintenance: number; incidents: number; offline: number }; attention: { title: string; detail: string; page: ManagerPage }[]; unverified_devices: number; can_simulate: boolean;
  people: { id: string; name: string; role: string; location: string; building_id: string; active: boolean; ends_at: string | null }[];
  maintenance: Maintenance[]; announcements: { id: string; title: string; message: string; audience: string; location_id: string; publish_at: string; expires_at: string | null; demo: boolean }[];
  visitors: Visitor[]; devices: { id: string; name: string; status: string; location: string; simulated: boolean }[];
  incidents: { id: string; description: string; status: string; severity: string; locations: string[] }[];
  ring: { id: string; at: string; signal: string; status: string; simulated: boolean; description: string }[];
  activity: { id: string; at: string; what: string; who: string; where: string; result: string; simulated: boolean }[];
  access_people: { id: string; name: string }[]; access_zones: { id: string; name: string }[];
  permissions: { id: string; person: string; zones: string[]; start: string; end: string; reason: string }[];
  actions: Record<'announce' | 'maintenance' | 'invite', string[]> }
export function announcementState(publish: string, expiry: string | null, now = Date.now()) {
  return expiry && Date.parse(expiry) <= now ? 'Expired' : Date.parse(publish) > now ? 'Scheduled' : 'Published'
}
