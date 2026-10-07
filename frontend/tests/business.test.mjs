import assert from 'node:assert/strict'
import test from 'node:test'
import { businessPages, businessError, activityLabel, businessPermissionNames } from '../src/business/model.ts'

test('Business Admin navigation follows explicit grants without configuration menus',()=>{
  assert.deepEqual(businessPages(['visitors.read','people.read','maintenance.read','access.read','announcements.read','hardware.read'],true),['Home','Visitors','Staff','Maintenance','Access','Notices','My Business'])
  assert.deepEqual(businessPages(['accounts.manage','authorization.manage'],true),['Home'])
})
test('Business Staff never inherits Staff management navigation',()=>{
  assert.deepEqual(businessPages(['visitors.read','maintenance.create','announcements.read','business.staff.manage'],false),['Home','Visitors','Maintenance','Notices'])
  assert.deepEqual(businessPages([],false),['Home'])
  assert.equal(businessPermissionNames['visitors.read'],'View own visits')
})
test('Ring-only delegated context has a real visitor review destination',()=>{
  assert.deepEqual(businessPages(['ring.read'],true),['Home','Visitors'])
})
test('Business errors remain friendly and activity is operational',()=>{
  for(const status of [400,401,403,404,409,422,500])assert.ok(!businessError({status,message:'PRIVATE_DB_ERROR'}).includes('PRIVATE_DB_ERROR'))
  assert.equal(activityLabel('staff.revoked'),'Staff membership revoked')
  assert.equal(activityLabel('visitor.arrived'),'Visitor arrived')
})
