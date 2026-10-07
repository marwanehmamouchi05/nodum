import { request } from '../api/client'
import type { BusinessSnapshot, Staff } from './model'
import type { Request, Visit } from '../resident/model'
const base = '/business-workspace'
export const businessApi = {
  snapshot: () => request<BusinessSnapshot>(base+'/snapshot'),
  visit: (body: unknown) => request<Visit>(base+'/visitors','POST',body),
  cancel: (id: string) => request<Visit>(base+'/visitors/'+encodeURIComponent(id)+'/cancel','POST',{}),
  arrive: (id: string) => request<Visit>(base+'/visitors/'+encodeURIComponent(id)+'/arrive','POST',{}),
  report: (body: unknown) => request<Request>(base+'/maintenance','POST',body),
  addStaff: (body: unknown) => request<Staff>(base+'/staff','POST',body),
  updateStaff: (id: string, body: unknown) => request<Staff>(base+'/staff/'+encodeURIComponent(id),'PATCH',body),
}
