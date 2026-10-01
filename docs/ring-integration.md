# Ring Partner integration

## Verified contract and scope

Reviewed 2026-09-30 against the official [Ring Partner API](https://developer.amazon.com/docs/ring/api-documentation.html),
[Configure guide](https://developer.amazon.com/docs/ring/configure.html), and
[private-app FAQ](https://developer.amazon.com/docs/ring/developer-faq.html).

This implements the Ring-driven flow. Outbound token exchange/refresh uses
`POST https://oauth.ring.com/oauth/token` with form encoding. Identity comes from
`GET /v1/users/me`; nonce verification uses HMAC-SHA256 over `time:account_id`,
URL-safe Base64 without padding, and a ten-minute freshness window. Confirmation
uses `POST /v1/accounts/me/app-integrations`, then `PATCH` to `completed`.
Discovery uses `GET /v1/devices?include=status,capabilities,location,configurations`.
Related resources are joined by JSON:API type and ID, never array position.

Webhooks use `X-Signature: sha256=<hex>` over the exact raw body. Ring's v1.1
envelope supplies `meta.account_id`, `meta.request_id`, `data.id`, `data.type`,
and `data.attributes.source/source_type/timestamp`. Event timestamps are epoch
milliseconds; identifiers are opaque. Ring expects a response within five seconds
and retries transient server errors. These contracts are from the API reference above.

**Documentation gap:** the consulted reference, Configure guide, and official
[token exchange sequence diagram](https://m.media-amazon.com/images/G/01/ring-docs/token_exchange_sequence.svg)
describe Ring POSTing a code but do not specify the inbound body encoding, field
names, or authentication. Nodum does not fabricate that contract. The outbound
exchange service is implemented and tested; inbound live delivery remains gated.

## Architecture and persistence

- `app/integrations/ring/`: environment configuration and bounded HTTP client.
  HTTPS only, no redirects, no remote error-body disclosure, three-second socket
  timeout, bounded responses. Only documented operations are exposed.
- `app/services/ring.py`: token lifecycle, linking, discovery, normalization,
  durable receipt, and explicit emergency bridge. No access-engine changes.
- `app/models/ring.py`: UTC records and request models.
- Shared `Repository` implementations store accounts/events. Migration 2 adds
  `ring_accounts` and `ring_events`, with unique environment/account/request and
  environment/account/event indexes. Migration 1 is unchanged. Startup remains
  offline and idempotent; no Ring account or active incident is seeded.
- Access/refresh token pairs are Fernet-encrypted with an independent deployment
  key. Plaintext tokens and authorization codes are not API responses or logs.
  A refresh commits the rotated pair before attempting discovery. A 401 permits
  one refresh and discovery retry; other failures surface as 503 without tight retries.
- Account claims reserve ownership before network calls. A failed completion
  PATCH can be retried by the same owner within the nonce window, skipping an
  already-confirmed POST. Nonce replay after completion cannot reassign ownership.

## Nodum endpoints

| Endpoint | Purpose / protection |
| --- | --- |
| `POST /ring/token-exchange` | Exchange code from a verified Ring transport adapter; returns only status |
| `GET /ring/link?nonce=...&time=...` | Ring browser redirect; preserves required query parameters; login and explicit confirmation page |
| `POST /ring/link` | `{nonce, time}`; verified manager/responder session; identity never comes from the body |
| `GET /ring/accounts/{account_id}/devices` | Discover devices for the linked account's owner |
| `POST /ring/webhooks` | Public signed webhook receipt, max 1 MiB; no synchronous network/emergency calls |
| `GET /ring/accounts/{account_id}/events` | Owner-only audit inbox, including original JSON |
| `POST /ring/events/{event_id}/process` | Owner/operator review; `{zone_id}` explicitly confirms the affected zone |

Ring operations now use the persisted, CSRF-protected Nodum session described in
[Authentication and linking](authentication.md). Identity never comes from request
person IDs or unsigned headers. Only existing managers/responders may link and
manage integrations. GET /ring/link presents login/confirmation while preserving
nonce/time; POST claims only after authentication and CSRF verification.

The inbound receive_verified_ring_code dependency still returns 503 until Ring
confirms the delivery contract and a verified adapter is supplied. Do not guess
that it uses the webhook envelope. Tests override this boundary; deployment does not.

## Events and deterministic safety

The [generic building inventory](building-integrations.md) can import a device
returned by this owner-authenticated discovery service through
`POST /building/ring/accounts/{account_id}/devices/{device_id}/register`.
It remains read-only sensing inventory, clearly separate from simulator actuators.
Verified motion/doorbell event IDs may supply journey arrival context but never
identity proof, permission or confirmed indoor location.

Normalized signals cover motion, doorbell button, contact open/closed, flood
detected/cleared, freeze detected/cleared, tamper detected/cleared, device
added/removed/online/offline, and integration added/removed. Unknown signed types
are retained as `unknown` for forward-compatible review. Original JSON retains
attributes such as motion subtype and camera component IDs. No network follows
URLs or relationships in event payloads.

Verified events are acknowledged only after durable insertion. Both delivery and
event identity are deduplicated under a transaction; a duplicate returns 200.
Conflicting identities return 409. Busy SQLite receipt fails with 503 after about
one second so Ring can retry. No asynchronous in-process task is relied on for
durability. Events remain in the inbox until an authenticated operator processes
them; there is deliberately no automatic emergency worker in this version.

Flood processing requires a completed account owned by the authenticated operator
and an existing, explicitly confirmed Nodum zone. It calls `create_emergency`
with type `water_leak`, records the device/event/time/operator, and commits the
incident and processing result together. Processing the same event cannot create
another incident. Raw payload zone IDs and device names never determine mapping.
Future-dated flood observations cannot create incidents.

Freeze detection remains `review`: Nodum has no freeze incident type and does not
mislabel freezing as an observed leak. Cleared signals do not resolve incidents;
normal authenticated emergency resolution remains necessary. Integration removal
disables the local account and clears stored token ciphertext. Device lifecycle
events are auditable notifications; discovery is queried afresh rather than
maintaining a potentially stale device cache.

No Ring path creates permissions, work orders, assignments, or door commands.
The [existing policy precedence](access-policy.md) still applies: fail-closed
context checks, manager/responder behavior, emergency restrictions, contractor
work-order/assignment rules, guest and appointment permission restrictions.
An existing contractor work order alone cannot bypass a Ring-derived incident.

## Configuration and deployment

Copy the names in `.env.example` into the backend process environment (the example
file itself is not automatically loaded). Set `RING_CLIENT_ID`,
`RING_CLIENT_SECRET`, `RING_SIGNING_KEY`, and `RING_ENCRYPTION_KEY` using a secret
store. `RING_WEBHOOK_SECRET` is a compatibility alias only when the signing-key
variable is absent or empty. Generate an independent encryption key with:

```powershell
cd C:\dev\nodum\backend
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this key stable and back it up separately from SQLite. Losing it requires
restoring the key or relinking accounts. Do not commit generated secrets.
`RING_ENVIRONMENT=staging|production` separates record identities. Configure API
and OAuth URLs explicitly if Ring provides different environment endpoints;
Nodum does not invent staging hostnames. Use separate databases, deployment keys,
and webhook URLs for staging and production.

After deploying HTTPS, register token exchange, webhook, authenticated account-link
UI, and homepage URLs in the portal. Supply these as `RING_TOKEN_EXCHANGE_URL`,
`RING_WEBHOOK_URL`, `RING_ACCOUNT_LINK_URL`, and `RING_HOMEPAGE_URL`; they document
deployment configuration and are not automatically registered with Ring. Complete
private-app connection/consent for an authorized Ring account and selected devices.

## Verification and remaining limits

Run the complete suite with both repository backends:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider --repository-backend=sqlite
.\.venv\Scripts\python.exe -m pip check
```

Live linking and real devices have not been tested. HTTPS deployment configuration
and a verified inbound token-delivery adapter remain necessary. Core APIs retain their existing lack
of authentication and must not be exposed publicly alongside Ring without an
appropriate gateway. Configure ingress rate limits, request timeouts, and TLS;
monitor delivery latency, inbox growth, and failed linking/refresh operations.

There is no scheduled refresh job, cleanup/retention policy, paginated audit API,
automated device-to-zone provisioning, or encrypted-key rotation tooling yet.
Discovery refreshes tokens on demand. A crash after Ring rotates a token but
before local persistence, or during code/profile retrieval, can require relinking;
SQLite cannot atomically commit with Ring. Persistent linkage failure outside the
nonce window needs operator recovery/reconnection. Separate signed flood events
create separate incidents, even for the same physical leak; incident correlation
is a future workflow. This integration does not turn sensor data into access authority.
