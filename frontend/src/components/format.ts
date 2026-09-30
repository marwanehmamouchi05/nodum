export const human = (value: string) => value.replaceAll('_', ' ')
export const date = (value?: string | null) => value ? new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
