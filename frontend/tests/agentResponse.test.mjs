import assert from 'node:assert/strict'
import test from 'node:test'
import { unavailableAgentResponse } from '../src/api/agentResponse.ts'

const unavailable = {
  status: 'unavailable',
  explanation: 'Provider unavailable; results remain valid at their check time.',
  explanation_is_authoritative: false,
  tool_results: [{ tool: 'check_access', status: 'success', data: { allowed: false, reason: 'Restricted zone' } }],
}

test('preserves a denied policy result without making its explanation authoritative', () => {
  assert.deepEqual(unavailableAgentResponse(unavailable), unavailable)
})

test('preserves proposals as confirmation-required, never as executed actions', () => {
  const response = { ...unavailable, tool_results: [{ tool: 'invite_guest', status: 'confirmation_required', data: { id: 'review-only-proposal' } }] }
  assert.deepEqual(unavailableAgentResponse(response), response)
})

test('accepts an outage before any tool results exist', () => {
  assert.deepEqual(unavailableAgentResponse({ ...unavailable, tool_results: [] })?.tool_results, [])
})

test('rejects ordinary errors, success responses and authoritative model claims', () => {
  for (const value of [null, [], { detail: 'Service unavailable' }, { ...unavailable, status: 'completed' }, { ...unavailable, explanation_is_authoritative: true }]) {
    assert.equal(unavailableAgentResponse(value), undefined)
  }
})

test('rejects malformed tool results instead of partially trusting the response', () => {
  for (const results of [null, {}, [null], [{ tool: 'check_access', status: ['success'], data: {} }], [{ tool: 'check_access', status: 'executed', data: {} }], [{ tool: 'check_access', status: 'success' }]]) {
    assert.equal(unavailableAgentResponse({ ...unavailable, tool_results: results }), undefined)
  }
})

test('does not carry undocumented error metadata into the UI', () => {
  assert.deepEqual(unavailableAgentResponse({ ...unavailable, internal_debug: 'not displayed', tool_results: [{ ...unavailable.tool_results[0], internal_debug: 'not displayed' }] }), unavailable)
})
