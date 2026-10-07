// Playwright MCP regression: synthetic HTTP fixtures only, no live backend/AWS.
async (page) => {
  const check = (condition, message) => { if (!condition) throw new Error(message) }
  const user = { id: 'fixture-resident', username: 'resident-fixture', person_id: 'resident-1' }
  let revoked = false
  let limited = false
  let writes = 0
  const handler = async route => {
    const path = new URL(route.request().url()).pathname
    if (route.request().method() !== 'GET') writes++
    const assignments = revoked ? [] : [{ role: 'resident', scope_id: 'fixture-home', permissions: limited ? ['visitors.read'] : ['people.read', 'visitors.read'] }]
    const json = path === '/auth/session' ? { user, csrf_token: 'fixture-only', authorization_mode: 'scoped', authorization: { principal: { user_id: user.id, person_id: user.person_id }, assignments } }
      : path === '/building/catalog' ? { people: limited ? [] : [{ id: 'resident-1', name: 'Synthetic resident', role: 'resident', guest_zone_ids: [] }], zones: [], businesses: [], work_orders: [], credentials: [] } : []
    if (path === '/building/catalog' && limited) await new Promise(resolve => setTimeout(resolve, 2000))
    await route.fulfill({ status: 200, json })
  }
  await page.route(/http:\/\/127\.0\.0\.1:(8000|8765|8766)\//, handler)
  try {
    await page.goto('about:blank')
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('http://127.0.0.1:5174/#AI%20Assistant')
    await page.getByRole('heading', { name: 'Nodum Guide', exact: true }).waitFor()
    check(await page.getByText('Signed in as resident-fixture').count() === 1, 'Scoped identity must come from session')
    check(await page.getByText('Operator context', { exact: true }).count() === 0, 'Scoped mode must hide actor selector')
    check(await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Integrations', exact: true }).count() === 0, 'Configuration navigation must be hidden')
    check(await page.getByRole('group', { name: 'Assistance mode' }).getByRole('button', { name: /^AI assistance/ }).count() === 0, 'No AI grant must keep help local')
    await page.getByLabel('Find local help').fill('How do I connect Ring?')
    await page.getByRole('button', { name: 'Find guidance', exact: true }).click()
    await page.getByRole('heading', { name: 'Help for your permitted workspace', exact: true }).waitFor()
    check(writes === 0, 'Guide must never perform mutations or inference')
    await page.setViewportSize({ width: 390, height: 844 })
    check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile workspace must not overflow')
    await page.goto('http://127.0.0.1:5174/#Integrations')
    await page.getByText('This section is outside your current permissions.', { exact: true }).waitFor()
    await page.goto('http://127.0.0.1:5174/#Visitors')
    await page.getByRole('heading', { name: 'Visitors', exact: true }).waitFor()
    await page.getByRole('combobox', { name: 'Inviter', exact: true }).getByRole('option', { name: 'Synthetic resident', exact: true, includeHidden: true }).waitFor({ state: 'attached' })
    limited = true
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await page.getByRole('combobox', { name: 'Inviter', exact: true }).getByRole('option', { name: 'Synthetic resident', exact: true, includeHidden: true }).waitFor({ state: 'detached', timeout: 750 })
    revoked = true
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await page.getByRole('heading', { name: 'Your account is ready', exact: true }).waitFor()
    check(await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Visitors', exact: true }).count() === 0, 'Revoked navigation must disappear')
    return { passed: true, checks: ['session identity', 'hidden actor selector', 'scoped navigation', 'local permission-aware Guide', 'mobile overflow', 'direct URL denial', 'cache invalidation before delayed refresh', 'revocation'], writes }
  } finally {
    await page.unroute(/http:\/\/127\.0\.0\.1:(8000|8765|8766)\//, handler)
  }
}
