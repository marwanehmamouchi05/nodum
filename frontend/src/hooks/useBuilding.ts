import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, resourcePaths } from '../api/client'
import type { BuildingData } from '../api/types'

const initial: BuildingData = { catalog: { people: [], zones: [], businesses: [], work_orders: [], credentials: [] }, appointments: [], permissions: [], emergencies: [], integrations: [], devices: [], journeys: [], actuators: [], scans: [] }
export function useBuilding() {
  const [data, setData] = useState(initial)
  const [errors, setErrors] = useState<Partial<Record<keyof BuildingData, string>>>({})
  const [loading, setLoading] = useState(true)
  const [updated, setUpdated] = useState<string>()
  const generation = useRef(0)
  const refresh = useCallback(async () => {
    const version = ++generation.current
    setLoading(true)
    const keys = Object.keys(resourcePaths) as (keyof BuildingData)[]
    const results = await Promise.allSettled(keys.map(key => api.resource(key)))
    if (generation.current !== version) return
    const nextErrors: Partial<Record<keyof BuildingData, string>> = {}
    const patch: Partial<BuildingData> = {}
    results.forEach((result, i) => {
      if (result.status === 'fulfilled') Object.assign(patch, { [keys[i]]: result.value })
      else {
        nextErrors[keys[i]] = result.reason instanceof Error ? result.reason.message : 'Unable to load'
        if (result.reason instanceof ApiError && [401, 403].includes(result.reason.status)) {
          Object.assign(patch, { [keys[i]]: initial[keys[i]] })
        }
      }
    })
    setData(previous => ({ ...previous, ...patch }))
    setErrors(nextErrors)
    setUpdated(new Date().toISOString())
    setLoading(false)
  }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => { void refresh() }, 0)
    const clear = () => { generation.current += 1; setData(initial); setErrors({ catalog: 'Sign in to refresh building data.' }) }
    const focus = () => { void refresh() }
    window.addEventListener('nodum:signed-out', clear)
    window.addEventListener('focus', focus)
    return () => {
      window.clearTimeout(timer); generation.current += 1
      window.removeEventListener('nodum:signed-out', clear)
      window.removeEventListener('focus', focus)
    }
  }, [refresh])
  return { data, errors, loading, updated, refresh }
}
