import assert from 'node:assert/strict'
import test from 'node:test'
import { permittedPages, permittedTopic } from '../src/api/authorization.ts'
import { topics } from '../src/guide/topics.ts'

const pages = ['Overview', 'Building', 'Visitors', 'Businesses', 'Access', 'Emergencies', 'Integrations', 'Activity', 'AI Assistant']
test('configuration grants do not expose operational navigation', () => {
  assert.deepEqual(permittedPages(pages, ['locations.read', 'hardware.read', 'authorization.manage']),
    ['Overview', 'Building', 'Integrations', 'AI Assistant'])
})
test('resident navigation follows grants without inheriting manager authority', () => {
  assert.deepEqual(permittedPages(pages, ['visitors.read', 'access.read']),
    ['Overview', 'Visitors', 'Access', 'AI Assistant'])
  assert.deepEqual(permittedPages(pages, []), ['Overview', 'AI Assistant'])
})
test('Guide excludes unauthorized destinations and simulation/configuration workflows', () => {
  const allowed = ['Overview', 'Visitors', 'AI Assistant']
  assert.equal(permittedTopic(topics.find(t => t.id === 'ring-connect'), allowed, ['visitors.read']), false)
  assert.equal(permittedTopic(topics.find(t => t.id === 'ring-scenarios'), pages, ['hardware.read']), false)
  assert.equal(permittedTopic(topics.find(t => t.id === 'ring-scenarios'), pages, ['simulation.run']), true)
  assert.equal(permittedTopic(topics.find(t => t.id === 'devices'), pages, ['hardware.read']), false)
})
test('legacy Guide remains unchanged when no scoped context is supplied', () => {
  assert.ok(topics.every(topic => permittedTopic(topic)))
})
