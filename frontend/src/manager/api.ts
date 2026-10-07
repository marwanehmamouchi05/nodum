import { request } from '../api/client'
import type { Snapshot } from './model'
export const managerApi = {
  snapshot: () => request<Snapshot>('/manager/snapshot'),
  announce: (body: unknown) => request('/manager/announcements', 'POST', body),
  report: (body: unknown) => request('/manager/maintenance', 'POST', body),
  update: (id: string, body: unknown) => request('/manager/maintenance/' + encodeURIComponent(id), 'PATCH', body),
  invite: (body: unknown) => request('/manager/visitors', 'POST', body),
  arrive: (id: string) => request('/manager/visitors/' + encodeURIComponent(id) + '/arrive', 'POST', {}),
}
