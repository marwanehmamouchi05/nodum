import { request } from '../api/client'
import type { Node, Account, Assignment, Audit, SetupStep } from './model'
const id = encodeURIComponent
export const adminApi = {
  organizations: () => request<{ id: string }[]>('/admin/organizations'),
  createOrganization: (scope_id: string, name: string, demo = false) => request<Node>('/admin/organizations', 'POST', { scope_id, name, demo }),
  catalog: () => request<{ nodes: Node[] }>('/structure/catalog'),
  saveNode: (node: Node) => request<Node>('/admin/nodes/' + id(node.id), 'PUT', node),
  accounts: () => request<Account[]>('/admin/accounts'),
  createAccount: (values: Record<string, string>) => request<Account>('/admin/accounts', 'POST', values),
  accountState: (key: string, active: boolean) => request('/admin/accounts/' + id(key), 'PATCH', { active }),
  assignments: () => request<Assignment[]>('/authorization/assignments'),
  grantOptions: (scope: string) => request<Record<string, string[]>>('/admin/grant-options/' + id(scope)),
  grant: (assignment: Assignment) => request('/admin/assignments/' + id(assignment.id), 'PUT', assignment),
  revoke: (key: string) => request('/admin/assignments/' + id(key), 'DELETE'),
  affiliations: () => request<{ id: string; user_id: string; role: string; target_id: string; starts_at: string | null; ends_at: string | null; active: boolean }[]>('/structure/affiliations'),
  affiliate: (values: Record<string, unknown>) => request('/admin/affiliations/' + id(String(values.id)), 'PUT', values),
  map: (device: string, location_id: string) => request('/admin/devices/' + id(device) + '/mapping', 'PUT', { location_id }),
  setup: (building: string) => request<{ step: SetupStep; policy_reviewed: boolean; completed: boolean }>('/admin/setup/' + id(building)),
  saveSetup: (building: string, step: SetupStep, policy_reviewed: boolean, completed = false) => request('/admin/setup/' + id(building), 'PUT', { step, policy_reviewed, completed }),
  demo: (organization_id: string) => request('/admin/demo-building', 'POST', { organization_id, confirm_synthetic: true }),
  audit: () => request<Audit[]>('/admin/audit'),
  ring: () => request<{ state: string; discovery_verified: boolean }>('/admin/ring'),
  prepareRing: (building_id: string) => request('/admin/ring/setup', 'POST', { building_id }),
}
