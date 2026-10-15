import type { Session } from './api/client'
import { isAdminWorkspace } from './admin/model.ts'

export type Workspace = 'Admin' | 'Manager' | 'Resident' | 'Business' | 'Operator'
/** Restore navigation only; workspaceChoices still checks current authority. */
export function workspaceFromHash(hash: string): Workspace | undefined {
  const name = hash.replace(/^#/, '').split('/')[0]
  return ['Admin', 'Manager', 'Resident', 'Business', 'Operator'].includes(name) ? name as Workspace : undefined
}
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

/** A URL selects a known screen, never permission to read it. */
export function workspacePageFromHash<T extends string>(hash: string, workspace: Workspace, pages: readonly T[], fallback: T): T {
  if (!hash.startsWith('#' + workspace + '/')) return fallback
  try {
    const page = decodeURIComponent(hash.slice(workspace.length + 2)) as T
    return pages.includes(page) ? page : fallback
  } catch { return fallback }
}
