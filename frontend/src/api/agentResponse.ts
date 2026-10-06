import type { AgentResponse, ToolResult } from './types'

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

// Only the documented fail-closed agent response is eligible for recovery.
// Ordinary API errors and malformed responses must still reject the request.
export function unavailableAgentResponse(value: unknown): AgentResponse | undefined {
  if (!record(value) || value.status !== 'unavailable' ||
      typeof value.explanation !== 'string' || value.explanation_is_authoritative !== false ||
      !Array.isArray(value.tool_results)) return undefined

  const results: ToolResult[] = []
  for (const result of value.tool_results) {
    if (!record(result) || typeof result.tool !== 'string' || typeof result.status !== 'string' ||
        !['success', 'error', 'confirmation_required'].includes(result.status) ||
        !Object.hasOwn(result, 'data')) return undefined
    results.push({ tool: result.tool, status: result.status as ToolResult['status'], data: result.data })
  }
  return { status: 'unavailable', explanation: value.explanation,
    explanation_is_authoritative: false, tool_results: results }
}
