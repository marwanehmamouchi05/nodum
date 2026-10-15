import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'

/** Inline contextual help: reveal it, focus it, and return to its caller on close. */
export function AssistantPanel({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const panel = useRef<HTMLElement>(null)
  useEffect(() => {
    const caller = document.activeElement instanceof HTMLElement ? document.activeElement : null
    panel.current?.focus({ preventScroll: true })
    panel.current?.scrollIntoView({ block: 'start', behavior: 'instant' })
    return () => { if (caller?.isConnected) caller.focus() }
  }, [])
  return <section className="nodum-assistant-panel" aria-label="Ask Nodum" tabIndex={-1} ref={panel}
    onKeyDown={e => { if (e.key === 'Escape') { e.stopPropagation(); onClose() } }}>
    <div className="nodum-assistant-heading"><h2>Ask Nodum</h2><button onClick={onClose}>Close assistant</button></div>
    <p className="fine">Local Guide is available here. AI availability is checked when you ask a question.</p>
    {children}
  </section>
}
