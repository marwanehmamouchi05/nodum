import type { Notice, Request, Visit } from '../resident/model'
export type BusinessPage = 'Home' | 'Visitors' | 'Staff' | 'Maintenance' | 'Access' | 'Notices' | 'My Business'
export type Staff = { id: string; name: string; username: string; role: string; active: boolean; permissions: string[]; can_manage: boolean }
export const businessPermissionNames: Record<string,string> = {
  'locations.read':'Open this business workspace', 'businesses.read':'View this business',
  'visitors.read':'View own visits', 'visitors.invite':'Schedule own visitors', 'visitors.check_in':'Confirm own visitor arrivals',
  'maintenance.read':'Track own maintenance requests', 'maintenance.create':'Report maintenance',
  'announcements.read':'Read business notices', 'access.read':'View personal access', 'access.check':'Evaluate personal access',
  'activity.read':'Read own activity', 'ai.use':'Ask Nodum with authorized context',
}
export type BusinessSnapshot = {
  name: string; floor: string | null; affiliation_id: string; role: 'business_admin' | 'business_staff'; demo: boolean; permissions: string[]; at: string;
  visitors: (Visit & { can_arrive: boolean })[]; maintenance: Request[]; notices: Notice[]; staff: Staff[]; staff_options: string[];
  access: { area: string; status: string; reason: string; valid_from: string; valid_until: string }[]; access_status: string;
  devices: { id: string; name: string; status: string; connection_path: string; demo: boolean }[];
  ring: { id: string; at: string; message: string; simulated: boolean }[];
  activity: { id: string; at: string; action: string; who: string; where: string }[]; expected_today: number; open_maintenance: number;
}
export function businessPages(permissions: string[], admin: boolean): BusinessPage[] {
  const allows = (...values: string[]) => values.some(p => permissions.includes(p))
  return (['Home', ...(allows('visitors.read','visitors.invite','ring.read') ? ['Visitors'] : []), ...(admin && allows('people.read','business.staff.manage') ? ['Staff'] : []), ...(allows('maintenance.read','maintenance.create') ? ['Maintenance'] : []), ...(allows('access.read') ? ['Access'] : []), ...(allows('announcements.read') ? ['Notices'] : []), ...(allows('hardware.read') ? ['My Business'] : [])] as BusinessPage[])
}
export function businessError(error: unknown) {
  const status = error && typeof error === 'object' && 'status' in error ? error.status : 0
  return status === 401 ? 'Please sign in again to continue.' : status === 403 ? 'This service is not available for your current business assignment. Contact your building Admin.' : status === 404 ? 'This record is no longer available in your business.' : status === 409 ? 'This record or login name has changed. Refresh and check before trying again.' : status === 422 || status === 400 ? 'Check the required fields, password length and time window, then try again.' : 'Business information is temporarily unavailable. Try refreshing. Check your records before retrying a submission.'
}
export function activityLabel(action: string) {
  if (action === 'staff.updated') return 'Staff membership updated'
  if (action === 'announcement.created') return 'Notice created'
  return ({'visitor.invited':'Visitor scheduled','visitor.arrived':'Visitor arrived','visitor.cancelled':'Visitor cancelled','maintenance.created':'Maintenance request submitted','maintenance.assigned':'Maintenance assigned','maintenance.in_progress':'Maintenance in progress','maintenance.resolved':'Maintenance resolved','maintenance.closed':'Maintenance closed','staff.created':'Staff account created','staff.revoked':'Staff membership revoked','staff.activated':'Staff membership activated'} as Record<string,string>)[action] || 'Business update'
}
