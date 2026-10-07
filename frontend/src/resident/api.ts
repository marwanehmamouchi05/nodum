import { request } from '../api/client'
import type { ResidentSnapshot, Visit, Request } from './model'
export const residentApi = {
  snapshot: () => request<ResidentSnapshot>('/resident/snapshot'),
  visit: (body: unknown) => request<Visit>('/resident/visitors', 'POST', body),
  cancel: (id: string) => request<Visit>('/resident/visitors/' + encodeURIComponent(id) + '/cancel', 'POST', {}),
  report: (body: unknown) => request<Request>('/resident/maintenance', 'POST', body),
}
