import type { AgentResponse, Appointment, BuildingData, Credential, Decision, Device, DeviceStatus, Incident, Journey, RingDevice, RingEvent, Scan, ToolResult, Transition } from './types'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
export class ApiError extends Error { status: number; constructor(message: string, status: number) { super(message); this.status = status } }
async function request<T>(path: string, method = 'GET', body?: unknown, csrf?: string): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), path.startsWith('/agent/') ? 60000 : 20000)
  try {
    const response = await fetch(`${API_BASE}${path}`, { method, signal: controller.signal, credentials: import.meta.env.VITE_API_USE_CREDENTIALS === 'true' ? 'include' : 'same-origin', headers: { ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(csrf ? { 'X-CSRF-Token': csrf } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      const detail = data?.detail
      const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: { loc?: string[]; msg?: string }) => `${e.loc?.join('.')}: ${e.msg}`).join('; ') : data?.explanation || `Request failed (${response.status})`
      throw new ApiError(message, response.status)
    }
    return data as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(error instanceof DOMException && error.name === 'AbortError' ? 'Request timed out. Refresh before retrying a write; it may have completed.' : 'Cannot reach Nodum. Check the backend URL, connection and CORS configuration.', 0)
  } finally { window.clearTimeout(timer) }
}
const id = encodeURIComponent
export const resourcePaths: Record<keyof BuildingData, string> = { catalog: '/building/catalog', appointments: '/appointments', permissions: '/guests/permissions', emergencies: '/emergencies', integrations: '/building/integrations', devices: '/building/devices', journeys: '/building/journeys', actuators: '/building/actuator-events', scans: '/building/credential-events' }
type Session = { user: { id: string; username: string; person_id: string } | null; csrf_token: string }
async function authenticatedPost<T>(path: string, body: unknown): Promise<T> {
  const session = await request<Session>('/auth/session')
  return request<T>(path, 'POST', body, session.csrf_token)
}
export const api = {
  session: () => request<Session>('/auth/session'),
  logout: () => authenticatedPost('/auth/logout', {}),
  ringAccounts: () => request<{ account_id: string; status: string; environment: string }[]>('/ring/accounts'),
  resource: <K extends keyof BuildingData>(key: K) => request<BuildingData[K]>(resourcePaths[key]),
  check: (person_id: string, zone_id: string, purpose: string) => request<Decision>('/access/check', 'POST', { person_id, zone_id, purpose }),
  appointment: (body: Pick<Appointment, 'id' | 'visitor_id' | 'visitor_name' | 'business_id' | 'destination_zone_id' | 'appointment_time'>) => request<Appointment>('/appointments', 'POST', body),
  checkIn: (a: Appointment) => request<{ appointment: Appointment }>('/appointments/' + id(a.id) + '/check-in', 'POST', { visitor_id: a.visitor_id, visitor_name: a.visitor_name }),
  invite: (body: { resident_id: string; guest_id: string; guest_name: string; allowed_zone_ids: string[]; valid_for_hours: number }) => request('/guests/invite', 'POST', body),
  emergency: (body: { emergency_id: string; emergency_type: string; severity: string; affected_zone_ids: string[]; description: string; created_by: string }) => request<Incident>('/emergencies', 'POST', body),
  resolve: (key: string, actor: string) => request<Incident>(`/emergencies/${id(key)}/resolve`, 'POST', { resolved_by: actor }),
  assign: (key: string, actor: string, responder: string) => request<Incident>(`/emergencies/${id(key)}/responders`, 'POST', { assigned_by: actor, responder_ids: [responder] }),
  configure: (key: string, enabled: boolean, actor_id: string) => request(`/building/integrations/${id(key)}`, 'PATCH', { enabled, actor_id }),
  deviceStatus: (key: string) => request<DeviceStatus>(`/building/devices/${id(key)}/status`),
  map: (key: string, zone_ids: string[], actor_id: string) => request(`/building/devices/${id(key)}/mapping`, 'PUT', { zone_ids, actor_id }),
  credential: (body: { id: string; kind: string; value: string; person_id: string; actor_id: string }) => request<Credential>('/building/credentials', 'POST', body),
  scan: (body: { id: string; reader_id: string; kind: string; value: string; zone_id: string; journey_id?: string }) => request<Scan>('/building/credential-scans', 'POST', body),
  demo: (key: string, actor_id: string, connect_simulators: boolean) => request<Journey>('/building/demo/atlas-dental', 'POST', { id: key, actor_id, connect_simulators }),
  transition: (journey: string, source_device_id: string, zone_id: string) => request<Transition>(`/building/journeys/${id(journey)}/transitions`, 'POST', { id: crypto.randomUUID(), source_device_id, zone_id }),
  transitions: (journey: string) => request<Transition[]>(`/building/journeys/${id(journey)}/transitions`),
  chat: (message: string, actor_id: string) => request<AgentResponse>('/agent/chat', 'POST', { message, actor_id }),
  confirm: (key: string, actor_id: string) => request<ToolResult>(`/agent/actions/${id(key)}/confirm`, 'POST', { actor_id }),
  ringDevices: (account: string) => request<RingDevice[]>(`/ring/accounts/${id(account)}/devices`),
  ringEvents: (account: string) => request<RingEvent[]>(`/ring/accounts/${id(account)}/events`),
  importRing: (account: string, device: string, zone_id: string) => authenticatedPost<Device>(`/building/ring/accounts/${id(account)}/devices/${id(device)}/register`, { zone_id }),
}
