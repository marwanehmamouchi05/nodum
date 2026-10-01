# Production-readiness checklist

Engineering checklist, 2026-10-01. Not a security certification or legal opinion.
See [privacy and security](privacy-security.md) and [repository strategy](repository-strategy.md).

## Implemented now

- [x] Deterministic guest, contractor, appointment and emergency access rules;
  explicit negative-policy tests. AI and Ring signals do not authorize access.
- [x] Shared services/repositories; versioned SQLite migrations and idempotent demo seed.
- [x] Opaque persisted sessions, password hashing, rotation/logout, production
  secure cookies and CSRF/Origin validation for sensitive session actions.
- [x] Coarse production manager gate for generic operational APIs; owner-bound
  Ring API checks; production HTTP docs disabled; response cache/input redaction.
- [x] Encrypted Ring tokens; signed/idempotent webhook receipt; fail-closed
  inbound token delivery until its transport contract is confirmed.
- [x] Environment-based deployment configuration, explicit CORS and health check.
- [x] Bounded agent loops and sensitive queries; reduced model context; proposals
  require separate confirmation and run through existing services.
- [x] System fonts/local frontend assets; no identified analytics/session replay.
- [x] Simulation/manual states clearly separated from actual hardware execution.
- [x] Secret patterns/history reviewed; ignore rules cover common runtime artifacts.
- [x] Privacy/security inventory, retention recommendations and license/IP strategy.

## Required before real customer deployment

- [ ] Professional security review and adversarial testing: session/CSRF flows,
  concurrency, IDOR, API authorization, webhook replay and provider failures.
- [ ] Privacy/legal review: controller/processor roles, lawful purpose, notices,
  vendor agreements, processing locations, individual rights and retention.
- [ ] Tenant isolation and least-privilege RBAC for managers, staff, residents,
  visitors and contractors. Bind audit actors to authenticated identities.
- [ ] Provisioning/deprovisioning, password recovery/rotation, session inventory,
  MFA/admin recovery and operation procedures without exposing bootstrap secrets.
- [ ] Ingress/global rate limiting, request-body/time limits, model cost budgets
  and distributed abuse protection, including anonymous session creation.
- [ ] Durable storage sizing/concurrency assessment; upgrade SQLite when actual
  load/availability requires it. Do not add a distributed database just for a demo.
- [ ] Managed encryption/key lifecycle, rotation, separation of tenants/environments,
  encrypted backups, restore drills and restricted access to SQLite/WAL copies.
- [ ] Scheduled, dependency-aware retention, legal holds, deletion/export and
  de-identification workflows, including backups and webhook dedupe tombstones.
- [ ] Tamper-resistant audit records and reliable identity attribution.
- [ ] Monitoring, redacted structured logs, alarms, incident response ownership,
  credential-rotation drills and vulnerability/dependency advisory scanning.
- [ ] Professional review of manufacturer terms, adapter certification/testing,
  real device access, retries/idempotency, failure recovery and revocation.
- [ ] Physical safety/egress review, qualified fire/elevator/security personnel,
  fail-safe hardware behavior and manual override. No automated emergency dispatch.
- [ ] Accessibility assessment (keyboard, screen reader, focus, contrast, errors);
  responsive UI verification is not a full accessibility audit.
- [ ] Privacy controls in every user interface; fine-grained exports and consent
  where appropriate; no customer data in a public demo, screenshots or Git.
- [ ] Frontend same-site session deployment or a vetted proxy; exact CORS/trusted
  origins; ingress TLS/proxy configuration and response/log redaction verified.
- [ ] Real Ring linking using a confirmed inbound token contract and verified
  device/simulator events. Mock tests do not prove live Partner connectivity.
- [ ] Reproducible dependency/asset provenance and notices; audit hero artwork,
  demo video/audio, manufacturer marks and contributors' rights.
- [ ] Scope-specific review before public uploads, marketing, billing or
  child-directed features; none is introduced by this audit.

## Demo and submission release gate

1. Keep synthetic identities and events. Do not put real visitor records, Ring
   tokens, cookies, account identifiers or provider consoles in the public video.
2. Use APP_ENV=production for hosted deployments, provision a manager using private
   bootstrap variables, verify the unauthenticated console returns 401, and verify
   logout and CSRF. Remove bootstrap variables after provisioning.
3. Keep Ring callback/HMAC keys private. Record live verification evidence
   separately; label the rest as mocked, simulator, manual or pending.
4. Run both backend suites, TypeScript, lint, production build, pip check, import,
   schema generation and diff check. These are regression gates, not penetration tests.
5. Recheck official submission rules and reviewer access before the deadline.
   No source removal, repository privatization or license change is automatic.

## Honesty review

The Atlas Dental journey uses real backend services with **software simulated**
doors, readers, elevators and wayfinding, or reports manual action required.
No real Kisi, SALTO, HID, elevator controller or smart-light adapter is implemented.
Journey zones are explicit recorded/simulated transitions, not continuous precise
indoor tracking. Emergency incidents change deterministic policy; they do not
dispatch responders or operate alarms autonomously.

Ring is a documented API adapter with mocked regression coverage; live account
linking remains pending its confirmed inbound delivery adapter. Bedrock was
reported working previously by the owner, but no live AWS inference was invoked
or independently reverified in this audit. Describe only evidence actually shown.
No production-grade-security or broad legal-compliance claim is justified.
