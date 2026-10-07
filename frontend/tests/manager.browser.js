// Run with Playwright against tests/manager_qa_server.py and Vite on 5175.
// All mutations use the fixture's temporary synthetic SQLite database.
async (page) => {
  const base = 'http://127.0.0.1:8767'
  const check = (condition, message) => { if (!condition) throw new Error(message) }
  const results = []
  const suffix = Date.now()
  const section = name => page.locator('section').filter({ has: page.getByRole('heading', { name, exact: true }) })
  const navigate = async name => {
    if (await page.getByLabel('Manager section', { exact: true }).isVisible()) await page.getByLabel('Manager section', { exact: true }).selectOption(name)
    else await page.getByRole('navigation').getByRole('button', { name, exact: true }).click()
  }
  await page.goto('http://127.0.0.1:5175')
  await page.evaluate(async base => {
    const session = await fetch(base + '/auth/session', { credentials: 'include' }).then(r => r.json())
    const response = await fetch(base + '/auth/login', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token }, body: JSON.stringify({ username: 'qa-manager', password: 'Synthetic-local-QA-only' }) })
    if (!response.ok) throw new Error('Synthetic login failed')
  }, base)
  await page.reload()
  await page.getByRole('heading', { name: 'Building status', exact: true }).waitFor()
  await page.setViewportSize({ width: 1440, height: 1000 })
  check(!(await page.getByRole('navigation').innerText()).includes('Setup'), 'Manager must not expose Admin setup')
  await navigate('People')
  check((await page.locator('main').innerText()).includes('Ahmed Benali'), 'Scoped resident missing')
  results.push('Manager navigation and People')
  await navigate('Maintenance')
  const report = section('Report maintenance')
  const title = 'Browser QA issue ' + suffix
  await report.getByLabel('Issue title').fill(title)
  await report.getByLabel('Description', { exact: true }).fill('Synthetic browser issue')
  await report.getByLabel('Location', { exact: true }).selectOption({ label: 'Apartment 101' })
  await report.getByRole('button', { name: 'Create maintenance request' }).click()
  const request = page.locator('article').filter({ has: page.getByRole('heading', { name: title, exact: true }) })
  await request.getByText('Update request', { exact: true }).click()
  await request.getByLabel('Status', { exact: true }).selectOption('assigned')
  await request.getByLabel('Maintenance person').selectOption({ label: 'Maintenance team (Synthetic)' })
  await request.getByRole('button', { name: 'Save maintenance update' }).click()
  await request.locator('strong').filter({ hasText: /^assigned$/ }).waitFor()
  await request.getByLabel('Status', { exact: true }).selectOption('resolved')
  await request.getByRole('button', { name: 'Save maintenance update' }).click()
  await request.locator('strong').filter({ hasText: /^resolved$/ }).waitFor()
  results.push('Maintenance create, assign, resolve')
  await navigate('Announcements')
  const notice = section('Publish announcement')
  await notice.getByLabel('Title', { exact: true }).fill('Browser QA notice ' + suffix)
  await notice.getByLabel('Message', { exact: true }).fill('Synthetic residential notice')
  await notice.getByLabel('Audience location / building').selectOption({ label: 'Floor 1' })
  await notice.getByLabel('Audience', { exact: true }).selectOption('residential')
  await notice.getByRole('button', { name: 'Save announcement' }).click()
  await page.getByRole('heading', { name: 'Browser QA notice ' + suffix, exact: true }).waitFor()
  results.push('Scoped announcement')
  await navigate('Visitors')
  const visit = section('Invite visitor')
  const times = await page.evaluate(() => {
    const local = offset => { const d = new Date(Date.now() + offset); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
    return { start: local(-600000), end: local(3600000) }
  })
  const visitorName = 'Browser QA visitor ' + suffix
  await visit.getByLabel('Visitor name').fill(visitorName)
  await visit.getByLabel('Destination', { exact: true }).selectOption({ label: 'Business X' })
  await visit.getByLabel('Visit starts').fill(times.start)
  await visit.getByLabel('Visit ends').fill(times.end)
  await visit.getByRole('button', { name: 'Create visit' }).click()
  const visitor = page.locator('article').filter({ has: page.getByRole('heading', { name: visitorName, exact: true }) })
  await visitor.getByRole('button', { name: 'Mark arrived' }).click()
  await visitor.getByText('arrived', { exact: true }).waitFor()
  results.push('Visitor schedule and arrival')
  await navigate('Access')
  await page.getByLabel('Person', { exact: true }).selectOption({ label: 'Marwane (Synthetic)' })
  await page.getByLabel('Area', { exact: true }).selectOption('machine-room')
  await page.getByRole('button', { name: 'Evaluate access', exact: true }).click()
  await page.getByRole('heading', { name: 'DENIED', exact: true }).waitFor()
  check((await page.locator('.policy').innerText()).includes('explicit physical access grant'), 'Access explanation missing')
  results.push('Access denial explanation')
  const ring = await page.evaluate(async base => {
    const read = () => fetch(base + '/manager/snapshot', { credentials: 'include' }).then(r => r.json())
    const before = await read()
    const session = await fetch(base + '/auth/session', { credentials: 'include' }).then(r => r.json())
    for (const scenario of ['visitor_arrives', 'package_delivery', 'after_hours_person', 'emergency_access', 'contact_sensor_sequence', 'device_lifecycle']) {
      const response = await fetch(base + '/ring/simulation/scenarios/' + scenario, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token }, body: '{}' })
      const delivered = await response.json()
      if (!response.ok || !delivered.events.every(e => e.is_simulation)) throw new Error('Ring scenario failed: ' + scenario)
    }
    const after = await read()
    if (JSON.stringify(before.permissions) !== JSON.stringify(after.permissions) || before.visitors.length !== after.visitors.length) throw new Error('Ring changed visitor or access records')
    return after.ring.every(e => e.simulated)
  }, base)
  check(ring, 'Simulation provenance missing')
  await page.reload()
  await navigate('Visitors')
  await page.getByRole('heading', { name: visitorName, exact: true }).waitFor()
  check((await page.locator('main').innerText()).includes('No door was unlocked'), 'Ring safety explanation missing')
  results.push('Six Ring scenarios and persisted visitor; no identity/access mutation')
  const screens = ['Overview', 'People', 'Visitors', 'Access', 'Maintenance', 'Security', 'Activity', 'Announcements']
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    for (const screen of screens) {
      await navigate(screen)
      await page.getByRole('heading', screen === 'Overview' ? { name: 'Building status', exact: true } : { name: screen, exact: true, level: 1 }).waitFor()
      check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), screen + ' overflow at ' + width)
      if (width === 1440 || screen === 'Overview' || width === 390 && ['Maintenance', 'Visitors'].includes(screen)) await page.screenshot({ path: 'C:/dev/nodum/docs/qa/manager-' + screen.toLowerCase() + '-' + width + '.png', fullPage: true, animations: 'disabled', timeout: 10000 })
    }
  }
  results.push('24 responsive screen/width combinations')
  await navigate('Overview')
  await page.getByRole('button', { name: 'Nodum Guide', exact: true }).click()
  await page.getByRole('heading', { name: 'Nodum Guide', exact: true }).waitFor()
  await page.locator('summary').filter({ hasText: 'Ask Nodum about overview' }).click()
  await page.route('**/agent/chat', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ status: 'unavailable', explanation: 'Bedrock unavailable. Use Nodum Guide.', explanation_is_authoritative: false, tool_results: [] }) }))
  await page.getByRole('button', { name: 'Ask Nodum', exact: true }).click()
  await page.getByText('Bedrock unavailable. Use Nodum Guide.', { exact: true }).waitFor()
  check(await page.getByRole('heading', { name: 'Building status' }).isVisible(), 'Core must survive AI outage')
  await page.unroute('**/agent/chat')
  await page.reload()
  await page.getByRole('heading', { name: 'Building status' }).waitFor()
  await page.evaluate(() => document.activeElement?.blur())
  await page.keyboard.press('Tab')
  check(await page.evaluate(() => document.activeElement?.textContent === 'Skip to content' && getComputedStyle(document.activeElement).outlineWidth !== '0px'), 'Skip link needs visible focus')
  await page.keyboard.press('Enter')
  check(await page.evaluate(() => document.activeElement?.id === 'manager-content'), 'Skip link must focus main')
  check(await page.locator('button:visible').evaluateAll(es => es.every(e => e.getBoundingClientRect().height >= 44)), 'Touch targets must be at least 44px')
  results.push('Local Guide, AI outage, keyboard and touch targets')
  return results
}
