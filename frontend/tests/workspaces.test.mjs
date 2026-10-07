import assert from 'node:assert/strict'
import test from 'node:test'
import { workspaceChoices } from '../src/workspaces.ts'
const session = assignments => ({authorization_mode:'scoped',authorization:{assignments}})
const role = (name, permissions=['locations.read']) => ({role:name,scope_id:'private',permissions})
test('Single-role routing and explicitly delegated configuration remain distinct',()=>{
  for(const [name,page] of [['resident','Resident'],['business_admin','Business'],['business_staff','Business'],['manager','Manager']])assert.deepEqual(workspaceChoices(session([role(name)])),[page])
  assert.deepEqual(workspaceChoices(session([role('admin',['structure.configure'])])),['Admin'])
  assert.deepEqual(workspaceChoices(session([role('owner',['ownership.manage'])])),['Admin'])
  assert.deepEqual(workspaceChoices(session([])),[])
})
test('Multi-role choices preserve grants and offer no client-selected authority',()=>{
  const s=session([role('resident'),role('business_admin')]), before=JSON.stringify(s)
  assert.deepEqual(workspaceChoices(s),['Business','Resident']);assert.equal(JSON.stringify(s),before)
  assert.deepEqual(workspaceChoices(session([role('manager',['structure.configure'])])),['Manager','Admin'])
  assert.deepEqual(workspaceChoices({authorization_mode:'legacy_demo'}),['Operator'])
})
