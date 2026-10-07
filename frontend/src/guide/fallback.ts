// This is an outcome of an explicit AI request, never a readiness probe.
// Auth/validation failures stay errors and must not be mislabeled as an outage.
export function guideFallback(status: number | undefined): 'connection' | 'provider' | undefined {
  if (status === 0) return 'connection'
  if (status !== undefined && status >= 500 && status <= 599) return 'provider'
  return undefined
}
