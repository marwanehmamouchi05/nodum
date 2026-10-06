# Nodum Guide

Guide is local, maintained help. It uses no API, AWS SDK, inference, embeddings,
storage or network transport. It does not consume building records, credentials
or AI tool results. Its only external callback navigates to an existing page.

- `topics.ts`: authored workflow guidance, page context and suggested topics.
- `matching.ts`: normalized exact questions/aliases, followed by explicit keyword
  groups. The most specific matching group wins; ties follow authored topic order.
  Unknown questions get a clearly labeled help-topic fallback.
- `fallback.ts`: classifies errors from an explicitly submitted AI request.
  Connection failures and server errors offer Guide. Auth/validation errors remain
  errors; there is no readiness ping or automatic retry.
- `GuidePanel.tsx`: local topic browsing, search and section navigation, distinct
  from the separate AI request record and confirmation controls.

Page help opens Guide with the originating section as context. The section
selector can change that context without navigating or contacting a service.
Guide is available while initial building data is loading. Once the frontend
assets are loaded, Guide works without network access; cold-start offline asset
caching is not provided by this feature.

Maintain content against the existing UI and workflow documentation. Do not add
actions, fake operational data, credential diagnostics or model invocations to
this module. AI explanations, decisions and proposals belong to the AI record,
not to Guide. Existing confirmation checks remain in the AI Assistant component.

Run `npm test` on the project's Node 24 environment for local matching, safety
and preserved-response tests. `tests/assistant.browser.js` is a Playwright MCP
regression function: it mocks AI responses, checks offline Guide and verifies
that no real chat request or building action is sent. It does not invoke Bedrock.
