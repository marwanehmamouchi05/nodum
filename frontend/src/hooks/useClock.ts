import { useEffect, useState } from 'react'

/** Display-only clock. Authorization always comes from the backend. */
export function useClock() {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 15000)
    return () => window.clearInterval(timer)
  }, [])
  return now
}
