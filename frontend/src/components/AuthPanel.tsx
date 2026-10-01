import { useEffect, useState } from 'react'
import { API_BASE, api } from '../api/client'
import { Badge, TaskButton } from './ui'

async function loadAccount() {
  const session = await api.session()
  return { user: session.user, accounts: session.user ? await api.ringAccounts() : [] }
}

export function AuthPanel() {
  const [user, setUser] = useState<{ username: string } | null>(null)
  const [accounts, setAccounts] = useState<{ account_id: string; status: string }[]>([])
  const [state, setState] = useState('Checking your Nodum session…')
  async function refresh() {
    try {
      const result = await loadAccount()
      setUser(result.user)
      setAccounts(result.accounts)
      setState(result.user ? '' : 'Sign in to connect or inspect your Ring account.')
    } catch (error) {
      setUser(null); setAccounts([])
      setState(error instanceof Error ? error.message : 'Could not check your session.')
    }
  }
  useEffect(() => {
    let active = true
    loadAccount().then(result => {
      if (!active) return
      setUser(result.user); setAccounts(result.accounts)
      setState(result.user ? '' : 'Sign in to connect or inspect your Ring account.')
    }).catch((error: unknown) => {
      if (active) setState(error instanceof Error ? error.message : 'Could not check your session.')
    })
    return () => { active = false }
  }, [])
  return <div className="notice">
    <strong>{user ? 'Signed in as ' + user.username : 'Nodum account'}</strong>
    {state && <p role="status">{state}</p>}
    {accounts.map(account => <p key={account.account_id}><Badge tone={account.status === 'completed' ? 'mint' : 'amber'}>{account.status === 'completed' ? 'Ring connected' : account.status}</Badge> <span>{account.account_id}</span></p>)}
    {user && accounts.length === 0 && <p>No Ring account linked to this user. Start linking in Ring, then confirm on the Nodum page.</p>}
    <p><a href={API_BASE + '/auth/login'} target="_blank" rel="noopener noreferrer">{user ? 'Manage sign-in' : 'Sign in to Nodum'}</a></p>
    <TaskButton run={refresh}>Refresh connection</TaskButton>
    {user && <TaskButton run={async () => { await api.logout(); await refresh() }}>Sign out</TaskButton>}
    <p className="fine">Ring opens a secure sign-in and confirmation page that keeps its link parameters. A connected account does not imply a device is online.</p>
  </div>
}
