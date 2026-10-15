// Playwright callback. Navigate page to the proxy fixture origin first, using
// an isolated ignoreHTTPSErrors context for its temporary certificate only.
async (page) => {
  const base = new URL(page.url()).origin
  const check = (condition, message) => { if (!condition) throw Error(message) }
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base)
  await page.getByRole('link', { name: 'Sign in to Nodum' }).click()
  await page.getByLabel('Username').fill('demo-presenter')
  await page.getByLabel('Password').fill('Synthetic-demo-only-2026')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL(base + '/')
  await page.getByLabel('Switch workspace').selectOption('Resident')
  await page.getByRole('button', { name: 'Invite visitor', exact: true }).click()
  const name = 'Phase 1 browser visitor ' + Date.now()
  await page.getByLabel('Visitor name').fill(name)
  const localInput = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
  await page.getByLabel('Arrival window starts').fill(localInput(new Date(Date.now() + 3600000)))
  await page.getByLabel('Arrival window ends').fill(localInput(new Date(Date.now() + 7200000)))
  await page.getByRole('button', { name: 'Schedule visitor', exact: true }).click()
  await page.getByText('Visitor pass', { exact: true }).waitFor()
  await page.getByRole('button', { name: 'Close pass', exact: true }).click()
  await page.getByRole('navigation', { name: 'Resident navigation', exact: true }).getByRole('button', { name: 'Visitors', exact: true }).click()
  await page.reload()
  await page.getByRole('navigation', { name: 'Resident navigation', exact: true }).waitFor()
  check(await page.getByLabel('Switch workspace').inputValue() === 'Resident', 'Refresh lost workspace')
  await page.getByText(name, { exact: true }).waitFor()
  const cookie = (await page.context().cookies()).find(cookie => cookie.name === '__Host-nodum_session')
  check(cookie?.secure && cookie.httpOnly && cookie.sameSite === 'Lax' && cookie.path === '/', 'Cookie flags')
  const responses = await page.evaluate(async () => {
    const session = await fetch('/api/auth/session').then(r => r.json())
    const missing = await fetch('/api/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
    const invalid = await fetch('/api/resident/visitors', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token }, body: '{}' })
    const absent = await fetch('/api/does-not-exist')
    return { missingCsrf: missing.status, invalidBody: invalid.status, absent: absent.status, csrf: session.csrf_token }
  })
  check(responses.missingCsrf === 403 && responses.invalidBody === 422 && responses.absent === 404, 'Browser API rejection statuses')
  const hostile = await page.context().request.post(base + '/api/auth/logout', {
    headers: { Origin: 'https://untrusted.example', 'X-CSRF-Token': responses.csrf }, data: {},
  })
  check(hostile.status() === 403, 'Wrong Origin accepted')
  await page.goto(base + '/app/deep-link#Resident/Visitors')
  await page.getByText(name, { exact: true }).waitFor()
  check(await page.getByLabel('Switch workspace').inputValue() === 'Resident', 'SPA fallback lost workspace')
  for (const [role, section, heading] of [['Manager', 'Maintenance', 'Maintenance'], ['Business', 'Visitors', 'Business visitors']]) {
    await page.getByLabel('Switch workspace').selectOption(role)
    await page.getByRole('navigation', { name: role + ' navigation', exact: true }).getByRole('button', { name: section, exact: true }).click()
    await page.reload()
    await page.locator('main').getByRole('heading', { name: heading, exact: true }).first().waitFor()
    check(await page.getByLabel('Switch workspace').inputValue() === role && page.url().endsWith('#' + role + '/' + section), 'Role section refresh mismatch')
  }
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await page.getByRole('link', { name: 'Sign in to Nodum' }).waitFor()
  check((await page.context().request.get(base + '/api/manager/snapshot')).status() === 401, 'Logout left authority')
  await page.getByRole('link', { name: 'Sign in to Nodum' }).click()
  await page.getByLabel('Username').fill('demo-resident')
  await page.getByLabel('Password').fill('Synthetic-demo-only-2026')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.waitForURL(base + '/')
  await page.goto(base + '/#Admin/Building')
  await page.getByRole('navigation', { name: 'Resident navigation', exact: true }).waitFor()
  check((await page.context().request.get(base + '/api/admin/setup/demo:reference:building')).status() === 403, 'URL granted Admin authority')
  check(errors.length === 0, 'Browser runtime error')
  return { verdict: 'PASS', checks: ['actual browser login and redirect', 'Resident invitation and pass',
    'Resident workspace and visit survive refresh', 'SPA deep path fallback', 'secure HttpOnly SameSite cookie',
    'missing CSRF 403', 'wrong Origin 403', 'invalid body 422', 'unknown API 404', 'logout then API 401',
    'Manager and Business section refresh', 'Resident forged Admin URL remains denied',
    'zero browser runtime errors'], certificate: 'isolated browser context ignores temporary fixture certificate; OS trust unchanged' }
}
