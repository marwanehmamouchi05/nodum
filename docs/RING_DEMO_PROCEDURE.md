# Ring demonstration: evidence and remaining dependency

Independent review update, 2026-10-16: official motion `attributes.sub_type` values
human and package_delivery now normalize to existing person/package signals.
Unknown classifications remain generic motion with raw evidence preserved.
Changed event data under a replayed event identity now returns 409. Tests use
signed local fixtures, not vendor-origin captures. Legacy custom event kinds remain
compatible. No webhook grants visitor identity or operates a door.

The [current hackathon rules](https://amazonappdev2026.devpost.com/rules) accept
Ring APIs/tools/simulators/devices listed in Ring documentation and require a
working demonstration plus runtime technology use in the repository. The target
deadline is October 23, 2026 at 12:00 PDT (20:00 Africa/Casablanca). A custom
Ring-like generator does not establish that evidence. Prepare a working official
tool/device capture, a video under three minutes, repository access and run
instructions; verify all submission requirements with the owner. Nothing has been
submitted or published by this review.

Owner evidence needed: the app's actual portal linking mode and approved scopes,
registered staging URLs, privately provisioned credentials, and the authenticated
inbound code-delivery encoding/authentication contract. Public docs describe POST
delivery but did not resolve that adapter detail. Use official Playground if
available to the authorized account; physical hardware is not intrinsically
required for the hackathon. Do not change linking mode or expose callbacks by guess.

Reviewed 2026-10-15. No authorized Ring portal/account, official simulator run or
physical Ring device was available. Do not describe custom scenarios as official
Ring Playground evidence or infer hackathon eligibility from unit tests.

## Implemented versus verified

Nodum implements a server-side REST client, not a Ring SDK: form-encoded token
exchange/refresh at oauth.ring.com, users/me identity, app-integrations POST/PATCH
confirmation and device discovery at api.amazonvision.com. Services implement
encrypted token storage, HMAC nonce association, signed webhook receipt, deduplication,
owner/event isolation and deliberate operator processing. These have deterministic
mock/signed-simulation regression evidence; none is an authenticated vendor runtime
capture. Live receive_verified_ring_code deliberately returns 503 until the inbound
issuer/body/transport contract is confirmed. Media playback and physical control
are not verified capabilities.

The current [official API guide](https://developer.amazon.com/docs/ring/api-documentation.html)
documents Ring-driven linking and an invitation-only partner-initiated PKCE flow;
only one method may be configured per app. The current implementation follows the
Ring-driven design. Confirm portal mode before any callback change. This source
also documents server-to-server calls and HMAC webhook verification; public code
examples cannot prove our app's account authorization.

The [Configure guide](https://developer.amazon.com/docs/ring/configure.html) requires
app scope selection and account-linking configuration. Obtain the app's actual
approved camera/doorbell or other required scopes rather than guessing strings in
Nodum. Capture registered staging Token Exchange, Account Link and webhook URLs,
issued client ID/secret/signing key, test account consent/device entitlement and
the exact provider-supported delivery contract. If changing to partner-initiated
mode, obtain its invitation/allowlisting and registered redirect URI first.

## Reproduce the existing custom demonstration

1. Follow DEVELOPER_ONBOARDING.md in the isolated engineering checkout. Start
   `backend/.venv/Scripts/python.exe backend/demo_product.py --start`, then start
   the documented frontend on :5178. The launcher supplies ephemeral simulation
   signing/encryption keys and synthetic SQLite data; never copy real credentials.
2. Sign in through the app as `demo-presenter`, using the launcher's documented
   synthetic-only password. Switch to Manager and use Demo Mode's visitor-arrival
   scenario. The corresponding API is POST `/ring/simulation/scenarios/visitor_arrives`
   with `{}`, authenticated session, exact Origin and X-CSRF-Token. See
   `frontend/src/ProductBar.tsx` for the existing control, not a new feature.
3. Review the new entrance signals in Manager Visitors/Overview. They are labeled
   simulation. Inspect the signed scenario result and owner inbox, then manually
   review/match a visit only where the existing workflow allows it. A motion/person
   signal establishes neither identity nor a physical door action.
4. Repeat the current automated Ring/product tests using the root pytest command.
   A signed synthetic webhook traverses normalization/persistence/workflow code;
   the signer and source are Nodum's custom scenario generator.
5. Stop both foreground terminals. The demo's temporary database is disposable;
   use the explicit proxy fixture shutdown procedure for automated staging tests.

## Official acceptance procedure — blocked until access is supplied

Owner supplies an authorized app/test account, portal settings and secret delivery
outside Git. Astra confirms Ring-driven inbound authentication and message encoding
(or separately reviews a permitted PKCE migration). Configure only an authorized
HTTPS staging target; this assignment does not expose a public endpoint.

Use the official developer tool or authorized device to consent/link, select the
shared device, discover it, receive a signed event and observe it under the correct
Nodum owner/building. Record redacted timestamps, event/account correlations and
tool/device provenance. Test code/nonce expiry/replay, wrong client/user, revoked
tokens, refresh and foreign access; preserve the custom scenario separately.

Pass requires that vendor-origin runtime evidence plus the negative controls.
Until then: **official runtime BLOCKED; custom simulation PASS within regression
scope; physical Ring compatibility NOT TESTED**. Exact code/review work is
ASTRA-RING-002 in ASTRA_FINAL_REVIEW_HANDOFF.md. Do not silently enable the inbound
adapter or market the MQTT proof as Ring usage.
