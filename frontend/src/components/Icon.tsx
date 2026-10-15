import type { CSSProperties } from 'react'

const paths = {
  overview: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  building: 'M4 21V3h12v18 M16 9h4v12 M8 7h4 M8 11h4 M8 15h4 M9 21v-3h2v3 M2 21h20',
  visitors: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M16 3a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  business: 'M8 6V3h8v3 M3 6h18v15H3z M3 12h18 M10 12v3h4v-3',
  access: 'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7z M8 12l3 3 5-6',
  emergency: 'M12 3 2 21h20z M12 9v5 M12 17v.01',
  integrations: 'M8 3v5 M16 3v5 M5 8h14v3a7 7 0 0 1-14 0z M12 18v4',
  activity: 'M3 12h4l3-8 4 16 3-8h4',
  assistant: 'M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
  refresh: 'M20 7v5h-5 M4 17v-5h5 M6 6a8 8 0 0 1 14 6 M4 12a8 8 0 0 0 14 6',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  device: 'M5 3h14v18H5z M9 7h6 M9 17h6 M12 12v.01',
  inbox: 'M3 3h18v18H3z M3 14h5l2 3h4l2-3h5',
  check: 'M5 12l4 4L19 6',
  home: 'M3 10.5 12 3l9 7.5 M5 9v12h14V9 M9 21v-7h6v7',
  people: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M10 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M16 11a4 4 0 1 0 0-8 M20 21v-2a4 4 0 0 0-3-3.87',
  maintenance: 'M14.7 6.3a4 4 0 0 0-5.6 5.6l-6.6 6.6a2 2 0 0 0 2.8 2.8l6.6-6.6a4 4 0 0 0 5.6-5.6L15 11l-2-2z',
  notice: 'M4 5h16v12H8l-4 4z M8 9h8 M8 13h5',
  floor: 'M3 5h18v4H3z M5 9v10h14V9 M8 12h3 M13 12h3 M8 16h3 M13 16h3',
  map: 'M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z M9 3v15 M15 6v15',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M12 6v6l4 2',
  alert: 'M12 3 2 21h20z M12 9v5 M12 17v.01',
  lock: 'M5 11h14v10H5z M8 11V7a4 4 0 1 1 8 0v4 M12 15v3',
} as const

export type IconName = keyof typeof paths
export function Icon({ name, size = 20, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" style={style}><path d={paths[name]} /></svg>
}
