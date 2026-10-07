import assert from 'node:assert/strict'
import test from 'node:test'
import { residentPages, currentNotices, residentStatus, residentError } from '../src/resident/model.ts'

test('Resident navigation stays personal and small', () => {
  assert.deepEqual(residentPages, ['Home', 'Visitors', 'Maintenance', 'Access', 'Notices'])
})
test('Expired notices do not dominate the current view', () => {
  assert.deepEqual(currentNotices([{id:'old', expired:true}, {id:'new',expired:false}]).map(n=>n.id), ['new'])
})
test('Resident statuses and errors use readable privacy-safe language', () => {
  assert.equal(residentStatus('in_progress'), 'In progress')
  assert.equal(residentStatus('submitted'), 'Submitted')
  for (const status of [401,403,404,409,422,500]) {
    const message = residentError({status, message:'SQL_PRIVATE_SECRET'})
    assert.ok(message.length)
    assert.ok(!message.includes('SQL_PRIVATE_SECRET'))
  }
})
