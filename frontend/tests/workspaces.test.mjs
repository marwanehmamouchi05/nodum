import assert from 'node:assert/strict'
import test from 'node:test'
import { workspaceChoices, workspaceFromHash, workspacePageFromHash } from '../src/workspaces.ts'
const session = assignments => ({authorization_mode:'scoped',authorization:{assignments}})
const role = (name, permissions=['locations.read']) => ({role:name,scope_id:'private',permissions})

test('Refresh restores only a recognized workspace; current grants remain authoritative',()=>{
  assert.equal(workspaceFromHash('#Resident/Visitors'),'Resident')
  assert.equal(workspaceFromHash('#Manager/Maintenance'),'Manager')
  for(const hash of ['', '#Unknown/Home', '#%52esident/Home'])assert.equal(workspaceFromHash(hash),undefined)
  const choices=workspaceChoices(session([role('resident')]))
  assert.equal(choices.includes(workspaceFromHash('#Admin/Building')),false)
})
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

test('Workspace page refresh preserves known screens and rejects malformed URLs',()=>{
  const pages=['Home','Visitors']
  assert.equal(workspacePageFromHash('#Resident/Visitors','Resident',pages,'Home'),'Visitors')
  for(const hash of ['#Admin/Visitors','#Resident/%E0%A4','#Resident/Unknown'])assert.equal(workspacePageFromHash(hash,'Resident',pages,'Home'),'Home')
})
