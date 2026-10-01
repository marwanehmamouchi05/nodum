# Privacy and security engineering audit

Reviewed 2026-10-01, starting from 9399197 (public main, authentication work).
This is engineering risk reduction, not legal advice, certification, a penetration
test, or a finding of GDPR/HIPAA/COPPA compliance. Use synthetic demo data only.

## Scope and evidence

- Inspected all 18 reachable Git commits, 209 unique historical blobs and 120
  historical paths, plus tracked working files, commit messages, examples,
  fixtures, frontend source and the rebuilt bundle. GitHub main matched local HEAD
  before this audit; unauthenticated GitHub metadata confirmed the repo is public.
- Used local pattern checks for AWS IDs, private keys, GitHub tokens, JWTs,
  credentials in URLs, sensitive literal assignments and historical secret/data
  filenames. Reviewed matches: fixture passwords/tokens, invalid-URL tests, and
  runtime-generated Fernet test keys. No confirmed live secret was identified.
- No tracked historical .env, database, private-key or certificate file was found.
  Local .env is ignored; example secret fields are empty. Build configuration has
  public API URLs only. No AWS, Ring or password material belongs in VITE variables.
- This is a heuristic/manual audit, not proof that no secret exists. It does not
  cover unavailable/deleted remote refs, forks, GitHub Actions logs/artifacts,
  Railway variables/logs, AWS invocation logging, browser profiles or backups.
  No secret values were copied into this report. No history was rewritten.
- Expanded ignore rules for local AWS configuration, database backups, SQL dumps,
  browser HAR captures and pytest cache. Docker already allowlists app code and
  requirements and excludes normal secret/database files.

No credential rotation is indicated by the identified test fixtures alone.
Never reuse those fixture passwords/tokens in a real environment. If an owner
recognizes any test value as a reused credential, treat it as exposed.

### If a real secret is discovered

1. Restrict the affected deployment and revoke/rotate at the issuer immediately;
   removal from Git is not revocation. Disable compromised AWS keys, replace Ring
   client/signing keys through the provider, revoke/relink compromised OAuth
   tokens, and reset affected user passwords plus invalidate their sessions.
2. For encryption-key exposure, assume the corresponding encrypted token store
   could be readable. Coordinate new key/re-encryption or relinking; do not just
   overwrite the key and strand stored tokens. Restrict backups and rotate
   underlying provider credentials as appropriate.
3. Review issuer/deployment access logs for misuse; record affected key IDs,
   paths and commits privately without publishing secret values.
4. Remove the value from current files, use private environment configuration,
   and scan again. With explicit owner authorization, coordinate history cleanup,
   collaborators, forks and hosting-provider caches. Never silently force-push.
5. Verify old credentials fail, new credentials work, artifacts/backups are
   addressed, and relevant incident/privacy professionals have reviewed impact.

## Data inventory and minimization

All persisted application records below use SQLite JSON tables. Except encrypted
Ring tokens and hashed passwords/session secrets/credential values, SQLite is not
application-level encrypted. IDs and hashes can still be personal data.
The retention periods are proposed engineering defaults for owner/legal review,
not statutory deadlines or implemented scheduled deletion.

| Data | Purpose and storage | Sent to Bedrock? | Frontend scope / minimization | Proposed retention |
| --- | --- | --- | --- | --- |
| Residents and other people | Identity/role/guest-zone authority in people | Specific name/ID search; another person's guest authority omitted | Manager console only in production; no public directory | Active relationship; review/delete or de-identify within 30 days of departure, subject to dependencies/holds |
| Guests and temporary permissions | Invitation identity, inviter, zones, validity in people/permissions | User request, targeted search, proposed invitation | Manager workflow; never public visitor history | Review 30 days after expiry; permission validity is not deletion |
| Business visitors and appointments | Identity, business/destination, appointment/check-in times/status in appointments/people | Requires visitor ID; no unfiltered business visitor export | Manager scheduling/check-in; minimum identity needed to verify visitor | Review 30 days after completed/cancelled visit |
| Contractors and work orders | Contractor/zone authorization and work description in work_orders/people | Contractor-scoped summaries; work descriptions omitted | Operational staff, not other residents | Active work plus 90 days, then review/de-identify |
| Access decisions | Deterministic result/reason; direct checks in browser memory, related scans/actions in credential_events/actuator_events | Explicit check_access result | Manager console; reason is authoritative only at check time | Browser session; persisted access audit 30–90 days |
| Zone/location and journeys | Zone/floor metadata, requested route and simulated confirmed transitions in zones/journeys/journey_transitions/device_states | Zone search; journey history is not an AI tool | Manager-only; not continuous indoor tracking | Building layout while used; identified movement 30 days |
| Ring account credentials | OAuth tokens encrypted in ring_accounts; user/person ownership/status | No Ring/token tool exposed to AI | Account ID/status only; no token response | While linked; remove/revoke on disconnect; backups follow key/revocation policy |
| Ring events and camera/doorbell metadata | Normalized signals and signed raw body in ring_events; device data on discovery/import | Not exposed through agent tools | HTTP event summaries now omit raw payload; device provider attributes remain owner-visible | Raw body suggested 7 days; normalized events 30 days; minimal dedupe tombstones retained separately before any purge |
| Credentials | SHA-256 credential fingerprint/binding in credentials; raw value transient on enrollment/scan | No credential tool | Fingerprints excluded from catalog; never display raw values | Revoke on departure/loss; remove binding after operational review |
| Emergencies | Type/severity/zones, descriptions, actors, assignments and history in emergencies/emergency_events | Active summaries only: no narrative, actor names or audit history | Managers; Ring owner bridge retains its separate operator checks | Review 90 days after resolution; longer documented incident hold when justified |
| Agent prompts/results | Request and bounded tool loop in process; independent turns in React memory | Yes: prompt, actor ID, required tool results | Warning before use; never enter secrets or sensitive narratives | No server conversation table; discard at end of request/browser component lifetime; verify AWS logs separately |
| Pending AI actions | Proposed arguments/actor/timestamps in pending_actions | Model receives proposal status, not pending action ID or duplicated arguments | Exact proposal remains visible for explicit user confirmation | Five-minute validity; removed on consume or later proposal cleanup |
| Nodum users/passwords | Username, person mapping, active flag, salted PBKDF2 hash in auth_users | No | Public user summary only after authentication; no hashes | Active account; disable immediately on departure, review deletion/dependencies |
| Sessions/login attempts | Hashed opaque session IDs and expiry in auth_sessions; hashed username/IP buckets in auth_throttles | No | HttpOnly cookie; CSRF token is intentionally readable, not a bearer session secret | 8-hour session default (1–24 configurable), 15-minute pre-login/throttle window; cleanup is lazy |

Ring metadata may imply presence, home routines or device placement. There is no
camera recording download, face recognition or biometric identification feature.
Raw signed events can contain provider fields Nodum does not need; restricting
browser disclosure does not remove that server-side collection risk.
SHA-256 is not anonymization, and short badge values are guessable offline;
these credential readers remain simulators, not production authentication hardware.

## Security boundaries and changes

- Existing deterministic policies, confirmation, Ring HMAC verification and
  encrypted token storage remain authoritative and unchanged.
- Production generic building/agent APIs now require a valid **manager** session;
  writes also require the existing CSRF token and trusted Origin. Normal resident,
  guest and contractor logins cannot view the full directory/history.
- Ring-specific routes retain their owner-bound manager/responder rules,
  including the building Ring import route. The undocumented token-delivery
  adapter remains 503. No guessed callback or manual token bypass was added.
- Production interactive API docs/schema HTTP endpoints are disabled. Offline
  OpenAPI generation works. API responses use no-store and no-referrer.
- Validation responses omit submitted input/context so a malformed credential is
  not echoed. Ring inbox/process responses omit the stored raw webhook body.
- Password hashing uses salted PBKDF2-SHA256 (600,000 iterations). Production
  cookies are Secure/HttpOnly/host-only/SameSite=Lax. Login rotates the session;
  logout revokes it. Per-username/IP login attempt limits persist.
- The UI clears cached building data on authorization rejection and local logout;
  it refreshes when focused. System fonts replace external Google Fonts.
- Agent tools require targeted people/work-order/appointment queries and cap
  personal-record results at ten. Incident summaries exclude narrative/history.
  This minimizes context; it does not make free-text prompts anonymous.

### Material limitations

The manager gate is not tenant isolation or per-record RBAC. Within the operator
console, request actor IDs are still selectable and are not trustworthy audit
attribution. Read endpoints remain broad for managers. Development mode is
intentionally unguarded for synthetic fixtures; never expose it with real data.
The deployed Railway instance was not changed or penetration-tested by this
audit. These protections take effect only after this work is reviewed/deployed.

Anonymous session creation, distributed abuse, expensive hash requests and
Bedrock cost abuse still need ingress rate/body/time limits and monitoring.
No MFA, self-service password reset, account recovery or hardened admin UI exists.
There is no durable scheduled purge, tenant key separation, durable outbound
hardware delivery guarantee or tamper-proof audit store. Backups/WAL files can
retain deleted material. Do not mechanically purge records involved in active
permissions, referential history or webhook idempotency.

## Third parties and runtime assets

Removed the Google Fonts CSS import (which requested fonts.googleapis.com and
fonts.gstatic.com). The final frontend source/build uses system fonts, local
assets, React/React DOM/Scheduler and the configured Nodum API. No analytics,
advertising pixel, session replay, CDN script or telemetry SDK was identified.
No new tracker was added. Runtime destinations were reviewed through source and
build inspection; this was not a network capture or browser-extension audit.

Backend outbound services are Ring and AWS Bedrock as configured. User-written
prompts may themselves contain sensitive data; no semantic redactor guarantees
otherwise. Check provider agreements, regional/cross-region inference routing,
account logging settings and processing locations before using customer data.
An eu-north-1 client setting alone does not establish every processing location.
Railway receives normal hosting traffic/log metadata; deployment configuration
and external ingress logging remain the operator's responsibility.

## Product scope requiring future review

- No public file/image upload, public content-sharing or media-hosting workflow
  exists. Private text fields/prompts are not a public publishing platform.
  DMCA agent registration is not a current core engineering work item, **not a
  legal exemption determination**. Before public uploads/content sharing, seek
  counsel on notices, moderation, rights, takedown and applicable safe-harbor
  conditions; see the [US Copyright Office resources](https://www.copyright.gov/512/).
- No promotional email, campaigns, checkout, subscriptions, recurring billing or
  automatic renewal exists. Review consent/unsubscribe, disclosure and billing
  obligations before adding any of these; no such features were added.
- This is not designed as a child-directed consumer product. No cosmetic age gate
  or biometric feature was added. Child-specific accounts/data or intentional
  child-directed use require a dedicated privacy/product/legal review.
- Statements in this document are a technical inventory and recommendations.
  Professional advice must establish applicable requirements, not this audit.
