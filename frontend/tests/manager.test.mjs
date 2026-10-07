import assert from 'node:assert/strict'
import test from 'node:test'
import { visibleManagerPages, announcementState } from '../src/manager/model.ts'

test('Manager navigation reflects operational grants without Admin configuration', () => {
  assert.deepEqual(visibleManagerPages(['visitors.read', 'maintenance.read', 'activity.read']), ['Overview', 'Visitors', 'Maintenance', 'Activity'])
  assert.deepEqual(visibleManagerPages(['hardware.configure', 'authorization.manage']), ['Overview'])
  assert.deepEqual(visibleManagerPages([]), ['Overview'])
})
test('Announcement presentation handles future, active and expired notices', () => {
  const now = Date.parse('2026-10-07T12:00:00Z')
  assert.equal(announcementState('2026-10-08T12:00:00Z', null, now), 'Scheduled')
  assert.equal(announcementState('2026-10-06T12:00:00Z', null, now), 'Published')
  assert.equal(announcementState('2026-10-06T12:00:00Z', '2026-10-07T12:00:00Z', now), 'Expired')
})
