import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { topics, pageHelp } from '../src/guide/topics.ts'
import { answerQuestion, pageSuggestions, nextSteps } from '../src/guide/matching.ts'
import { guideFallback } from '../src/guide/fallback.ts'

test('every maintained question resolves to its own guidance with valid navigation links', () => {
  assert.equal(new Set(topics.map(t => t.id)).size, topics.length)
  for (const topic of topics) {
    const answer = answerQuestion(topic.question, 'Overview')
    assert.equal(answer.matched, true)
    assert.equal(answer.topic.id, topic.id)
    assert.ok(topic.summary.length > 20)
    assert.ok(topic.steps.length >= 2)
    for (const link of topic.links) assert.ok(Object.hasOwn(pageHelp, link.page))
  }
})

test('required workflow questions resolve and preserve the safety distinctions', () => {
  for (const [question, id, text] of [
    ['What is Nodum?', 'nodum', 'deterministic'],
    ['How does the dashboard work?', 'dashboard', 'snapshot'],
    ['How do I connect Ring?', 'ring-connect', 'sign-in'],
    ['How does Ring simulation work?', 'ring-simulation', 'physical'],
    ['How do I run a simulation scenario?', 'ring-scenarios', 'explicit action'],
    ['How do I add/configure a building device?', 'devices', 'mapping'],
    ['How does Access work?', 'access', 'policy'],
    ['How do Visitors work?', 'visitors', 'grants no access'],
    ['How do Emergencies work?', 'emergencies', 'not a physical alarm'],
    ['What is the Activity page?', 'activity', 'session'],
    ['What does a simulation badge mean?', 'simulation-badge', 'physical'],
    ['Why does Ring discovery say no linked account?', 'ring-unlinked', 'signed-in'],
    ['Why is AI/Bedrock unavailable?', 'ai-unavailable', 'system time'],
    ['How do I troubleshoot backend connection problems?', 'backend-connection', 'stale'],
  ]) {
    const answer = answerQuestion(question, 'Overview')
    assert.equal(answer.topic.id, id)
    assert.ok([answer.topic.summary, ...answer.topic.steps].join(' ').includes(text), question)
  }
})

test('suggestions and next steps reflect the selected page', () => {
  for (const page of Object.keys(pageHelp)) {
    assert.equal(pageSuggestions(page)[0].id, 'next')
    assert.equal(nextSteps(page).links[0].page, page)
    assert.equal(answerQuestion('What should I do next on the current page?', page).topic.summary, pageHelp[page].summary)
  }
  assert.ok(pageSuggestions('Integrations').some(t => t.id === 'ring-connect'))
  assert.ok(pageSuggestions('Access').some(t => t.id === 'credential-reader'))
  assert.ok(pageSuggestions('Emergencies').some(t => t.id === 'emergencies'))
})

test('specific troubleshooting matches are not mistaken for general Ring onboarding', () => {
  assert.equal(answerQuestion('Ring account is not linked to this operator', 'Integrations').topic.id, 'ring-unlinked')
  assert.equal(answerQuestion('Run a Ring simulation', 'Integrations').topic.id, 'ring-scenarios')
  assert.equal(answerQuestion('Why is my device unavailable?', 'Integrations').topic.id, 'device-unavailable')
})

test('unknown and action requests receive explicit guidance-only fallback', () => {
  for (const question of ['', 'What is the weather?', 'Unlock the front door now']) {
    const answer = answerQuestion(question, 'Overview')
    assert.equal(answer.matched, false)
    assert.equal(answer.topic.id, 'unknown')
    assert.ok(answer.topic.summary.includes('does not infer live state, run commands'))
  }
})

test('Guide has no runtime API or network dependency or executable topic actions', () => {
  for (const file of ['topics.ts', 'matching.ts', 'fallback.ts', 'GuidePanel.tsx']) {
    const source = readFileSync(new URL(`../src/guide/${file}`, import.meta.url), 'utf8')
    assert.doesNotMatch(source, /\bfetch\s*\(|\bapi\.|from\s+['"][^'"]*api\/client|\bXMLHttpRequest\b|\bWebSocket\b/)
  }
  for (const topic of topics) {
    assert.equal(Object.values(topic).some(value => typeof value === 'function'), false)
    for (const link of topic.links) assert.deepEqual(Object.keys(link).sort(), ['label', 'page'])
  }
})

test('outages offer Guide without treating successful, authentication or validation responses as outages', () => {
  assert.equal(guideFallback(503), 'provider')
  assert.equal(guideFallback(500), 'provider')
  assert.equal(guideFallback(0), 'connection')
  for (const status of [200, 400, 401, 403, 422, undefined]) assert.equal(guideFallback(status), undefined)
})
