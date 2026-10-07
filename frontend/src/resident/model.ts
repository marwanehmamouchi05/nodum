export const residentPages = ['Home', 'Visitors', 'Maintenance', 'Access', 'Notices'] as const
export type ResidentPage = typeof residentPages[number]
export type Unit = { affiliation_id: string; name: string; floor: string | null; demo: boolean; can_invite: boolean; can_report: boolean }
export type Visit = { id: string; name: string; destination: string; starts_at: string; ends_at: string; note: string; status: string; logical_authorization: string; physical_access: false; can_cancel: boolean; demo: boolean }
export type Request = { id: string; title: string; description: string; location: string; priority: string; status: string; created_at: string; updated_at: string; updates: { at: string; status: string; message: string }[] }
export type Notice = { id: string; title: string; message: string; published_at: string; expires_at: string | null; expired: boolean; audience: string; demo: boolean }
export type ResidentSnapshot = { name: string; units: Unit[]; visitors: Visit[]; maintenance: Request[]; notices: Notice[]; access: { area: string; status: string; reason: string; valid_from: string; valid_until: string }[]; access_status: string; ring: { id: string; at: string; message: string; simulated: boolean }[]; at: string; expected_today: number; open_maintenance: number }
export function currentNotices(notices: Notice[]) { return notices.filter(n => !n.expired) }
export function residentStatus(status: string) { return ({ submitted: 'Submitted', expected: 'Expected', arrived: 'Arrived', active: 'Active', completed: 'Completed', expired: 'Expired', cancelled: 'Cancelled', assigned: 'Assigned', in_progress: 'In progress', resolved: 'Resolved', closed: 'Closed' } as Record<string, string>)[status] || status }
export function residentError(error: unknown) {
  const status = error && typeof error === 'object' && 'status' in error ? error.status : 0
  return status === 401 ? 'Please sign in again to continue.' : status === 403 ? 'This action is not available for your current unit. Contact your building team.' : status === 404 ? 'This record is no longer available.' : status === 409 ? 'This record has changed. Refresh and check its current status.' : status === 422 ? 'Check the required fields and time window, then try again.' : 'Building information is temporarily unavailable. Try refreshing. Before retrying a submission, check whether it was saved.'
}
