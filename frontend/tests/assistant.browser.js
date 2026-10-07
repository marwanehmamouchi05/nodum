// Playwright MCP regression function. Every chat response is mocked: no Bedrock
// inference or confirmation request is authorized by this test.
async (page) => {
  const results = []
  const writes = []
  let scenario = 'success'
  let chatRequests = 0
  const check = (condition, message) => { if (!condition) throw new Error(message) }
  const onRequest = request => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) writes.push(new URL(request.url()).pathname)
  }
  const unavailable = {
    status: 'unavailable', explanation: 'Verification fixture: Bedrock unavailable. No proposed action was executed.',
    explanation_is_authoritative: false,
    tool_results: [
      { tool: 'check_access', status: 'success', data: { allowed: false, reason: 'Guide verification: denied' } },
      { tool: 'invite_guest', status: 'confirmation_required', data: { id: 'guide-review-only', actor_id: 'manager-1', expires_at: new Date(Date.now() + 600000).toISOString(), arguments: { guest_name: 'Synthetic test guest' } } },
    ],
  }
  const aiButton = () => page.getByRole('group', { name: 'Assistance mode' }).getByRole('button', { name: /^AI assistance/ })
  const guideButton = () => page.getByRole('group', { name: 'Assistance mode' }).getByRole('button', { name: /^Nodum Guide/ })
  const submitAI = async message => {
    await aiButton().click()
    await page.getByLabel('Your building request').fill(message)
    await page.getByRole('button', { name: 'Ask Nodum', exact: true }).click()
  }
  const findHelp = async question => {
    await page.getByLabel('Find local help').fill(question)
    await page.getByRole('button', { name: 'Find guidance', exact: true }).click()
  }
  page.on('request', onRequest)
  await page.route('**/agent/chat', async route => {
    chatRequests++
    if (scenario === 'success') return route.fulfill({ status: 200, json: { status: 'completed', explanation: 'Verification fixture: successful AI response', explanation_is_authoritative: false, tool_results: [] } })
    if (scenario === 'auth') return route.fulfill({ status: 403, json: { detail: 'Verification fixture: authentication required' } })
    return route.fulfill({ status: 503, json: unavailable })
  })
  await page.route('**/auth/session', route => route.fulfill({ status: 200, json: { user: null, csrf_token: 'verification-only-csrf' } }))
  try {
    await page.goto('http://127.0.0.1:5174/#AI%20Assistant')
    await page.getByRole('heading', { name: 'AI Assistant', exact: true }).waitFor()
    await submitAI('Mocked success verification')
    await page.getByText('Verification fixture: successful AI response', { exact: true }).waitFor()
    check(await aiButton().getAttribute('aria-pressed') === 'true', 'AI success must keep AI mode')
    check(await page.locator('.guide-panel').count() === 0, 'AI success must not trigger fallback')
    results.push('Bedrock-success response path preserved')

    scenario = 'unavailable'
    await submitAI('Mocked provider-outage verification')
    await page.locator('.guide-panel').waitFor()
    await page.getByText('Guide verification: denied', { exact: true }).waitFor()
    check(await guideButton().getAttribute('aria-pressed') === 'true', '503 must open Guide')
    check(await page.locator('.tool-result').count() === 2, '503 tool results must remain visible')
    check(await page.locator('.policy.deny').isVisible(), 'Denied result must stay denied')
    check(await page.getByRole('button', { name: 'Confirm this action', exact: true }).count() === 1, 'Proposal remains review-only')
    check(await page.getByText('Request completed.', { exact: true }).count() === 0, '503 must not claim success')
    results.push('503 opens Guide and preserves structured policy/proposal results')

    scenario = 'auth'
    await submitAI('Mocked authentication verification')
    await page.getByText('Verification fixture: authentication required', { exact: true }).waitFor()
    check(await aiButton().getAttribute('aria-pressed') === 'true', '403 must remain an auth error, not a provider outage')
    results.push('Authentication failures still reject')

    await page.getByRole('navigation').getByRole('button', { name: 'Integrations', exact: true }).click()
    await page.getByRole('button', { name: 'Page help', exact: true }).click()
    await page.locator('.guide-panel').waitFor()
    check(await page.getByLabel('Help for this section').inputValue() === 'Integrations', 'Page help must carry source context')
    await page.locator('.guide-questions').getByRole('button', { name: 'How do I connect Ring?', exact: true }).click()
    await page.locator('.guide-answer').getByRole('heading', { name: 'How do I connect Ring?', exact: true }).waitFor()
    await page.setViewportSize({ width: 1440, height: 1100 })
    await page.screenshot({ path: 'artifacts/ui-polish/qa-guide-desktop.png', fullPage: true })
    results.push('Integrations contextual help and section links')

    await page.getByLabel('Help for this section').selectOption('Access')
    await page.locator('.guide-questions').getByRole('button', { name: 'What does a credential reader do?', exact: true }).click()
    await page.locator('.guide-answer').getByRole('heading', { name: 'What does a credential reader do?', exact: true }).waitFor()
    await page.getByLabel('Help for this section').selectOption('Emergencies')
    await page.locator('.guide-questions').getByRole('button', { name: 'How do Emergencies work?', exact: true }).click()
    await page.locator('.guide-answer').getByRole('heading', { name: 'How do Emergencies work?', exact: true }).waitFor()
    results.push('Access and Emergencies suggestions')

    await findHelp('Unlock the front door now')
    await page.getByRole('heading', { name: 'No matching help topic', exact: true }).waitFor()
    check(chatRequests === 3, 'Guide must not send chat requests')
    results.push('Unknown/action question gets guidance-only fallback')

    await page.unroute('**/auth/session')
    await page.context().setOffline(true)
    await findHelp('How does Ring simulation work?')
    await page.locator('.guide-answer').getByRole('heading', { name: 'How does Ring simulation work?', exact: true }).waitFor()
    await submitAI('Offline request verification')
    await page.locator('.guide-panel').waitFor()
    await page.locator('.guide-answer').getByRole('heading', { name: 'How do I troubleshoot backend connection problems?', exact: true }).waitFor()
    check(chatRequests === 3, 'Offline failure must not reach Bedrock')
    check(writes.every(path => path === '/agent/chat'), 'Guide must never submit building actions')
    results.push('Offline Guide and unreachable-backend fallback; no building writes')

    await page.setViewportSize({ width: 390, height: 900 })
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
    check(!overflow, 'Guide must not overflow on mobile')
    await page.screenshot({ path: 'artifacts/ui-polish/qa-guide-mobile.png', fullPage: true })
    results.push('Mobile layout has no horizontal overflow')
    const helpUrl = page.url()
    await page.getByRole('link', { name: 'Skip to content', exact: true }).focus()
    await page.keyboard.press('Enter')
    check(page.url() === helpUrl, 'Skip link must preserve the selected page')
    check(await page.evaluate(() => document.activeElement?.id === 'content'), 'Skip link must focus main content')
    results.push('Keyboard skip link focuses content without changing pages')
    return { passed: results, mockedChatRequests: chatRequests, buildingWrites: writes.filter(path => path !== '/agent/chat') }
  } finally {
    await page.context().setOffline(false)
    page.off('request', onRequest)
    await page.unroute('**/auth/session')
    // Keep a guard until the QA page is closed; do not leave accidental live AI enabled.
    await page.unroute('**/agent/chat')
    await page.route('**/agent/chat', route => route.fulfill({ status: 503, json: { detail: 'Browser verification finished; no live inference authorized' } }))
  }
}
