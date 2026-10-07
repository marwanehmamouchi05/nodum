import type { Session } from './api/client'
import { isAdminWorkspace } from './admin/model.ts'

export type Workspace = 'Admin' | 'Manager' | 'Resident' | 'Business' | 'Operator'
/** Presentation choices only. Never filter or replace authenticated grants. */
export function workspaceChoices(session: Session): Workspace[] {
  if (session.authorization_mode !== 'scoped') return ['Operator']
  const grants = session.authorization?.assignments || []
  const permissions = grants.flatMap(a => a.permissions)
  const choices: Workspace[] = []
  if (grants.some(a => ['admin', 'owner'].includes(a.role)) && isAdminWorkspace(permissions)) choices.push('Admin')
  if (grants.some(a => a.role === 'manager')) choices.push('Manager')
  if (!choices.includes('Admin') && isAdminWorkspace(permissions)) choices.push('Admin')
  if (grants.some(a => ['business_admin', 'business_staff'].includes(a.role))) choices.push('Business')
  if (grants.some(a => a.role === 'resident')) choices.push('Resident')
  if (!choices.length && permissions.length) choices.push('Operator')
  return choices
}
