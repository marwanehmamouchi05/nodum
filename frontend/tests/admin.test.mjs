import assert from 'node:assert/strict'
import test from 'node:test'
import { isAdminWorkspace, visibleAdminPages, readiness, blankNode } from '../src/admin/model.ts'

test('Admin configuration opens a dedicated workspace without operational menus', () => {
  assert.equal(isAdminWorkspace(['authorization.manage']), true)
  assert.equal(isAdminWorkspace(['visitors.read', 'incidents.manage']), false)
  const pages = visibleAdminPages(['structure.configure', 'hardware.configure', 'accounts.manage', 'authorization.manage'])
  assert.deepEqual(pages, ['Setup', 'Building', 'Hardware', 'Integrations', 'Accounts', 'Roles & Permissions', 'Policies', 'System & Audit'])
  assert.ok(!pages.includes('Visitors') && !pages.includes('Activity'))
})
test('Delegated setup rights show only related configuration sections', () => {
  assert.deepEqual(visibleAdminPages(['hardware.configure']), ['Setup', 'Hardware', 'Integrations'])
  assert.deepEqual(visibleAdminPages(['ownership.manage']), ['Setup', 'Roles & Permissions'])
})
test('Readiness distinguishes empty, registered, and unassigned hardware', () => {
  assert.deepEqual(readiness([], []), { buildings: 0, floors: 0, areas: 0, devices: 0, unassigned: 0, accounts: 0 })
  const nodes = [{ kind: 'building', id: 'b' }, { kind: 'floor' }, { kind: 'location' }, { kind: 'device', parent_id: 'b', building_id: 'b' }, { kind: 'device', parent_id: 'l', building_id: 'b' }]
  assert.equal(readiness(nodes, []).unassigned, 1)
  assert.equal(readiness(nodes, []).devices, 2)
})
test('New device records inherit explicit ownership and claim no capabilities', () => {
  const parent = { id: 'location', scope_id: 'location-scope', organization_id: 'org', building_id: 'building', demo: false }
  const device = blankNode('device', parent, 'Camera')
  assert.equal(device.organization_id, 'org')
  assert.equal(device.building_id, 'building')
  assert.equal(device.scope_id, 'location-scope')
  assert.equal(device.parent_id, 'location')
  assert.deepEqual(device.capabilities, [])
  assert.equal(device.connection_path, null)
})
