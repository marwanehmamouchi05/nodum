# Phase F — final integration and demo readiness

**READY FOR REVIEW — October 7, 2026.** Amazon/investor software demonstrations are ready with explicit simulation/fallback disclosures. This is not physical commissioning or live-provider certification. Work remains uncommitted on product-platform; A–E2 changes are preserved. Main/HEAD remain 71927dd60294b7570756d906d7b339d543956c41. No commit, merge, push, deployment, video or physical-hardware work.

## 1. Files changed in Phase F

20 source/test/documentation files plus 23 screenshots:

- README.md — current product, startup and truthful capabilities
- backend/app/api/demo.py — read-only authorized synthetic control discovery
- backend/app/api/authorization.py — own-affiliation cache generation
- backend/app/main.py — demo router
- backend/app/services/manager.py — mapped/readable Ring Activity and grouped attention
- backend/demo_product.py — opted-in disposable full-persona demo
- backend/scripts/release_checks.py — secret-pattern/public PyPI advisory checks
- backend/tests/test_product_release.py — five integration/membership/migration gates
- frontend/src/App.tsx — workspace selection/session freshness and clearing
- frontend/src/ProductBar.tsx — account/switch/demo controls
- frontend/src/workspaces.ts — role/permission-derived presentation choices
- frontend/src/product.css — touch/focus/sidebar-aware layouts
- frontend/src/api/client.ts — expiry/recheck notifications and membership marker type
- frontend/src/admin/AdminWorkspace.tsx — Owner recovery/reads, focus and terminology
- frontend/package-lock.json — source-map-js 1.2.1 → 1.2.2 only
- frontend/tests/workspaces.test.mjs — single/multiple-role routing
- frontend/tests/product.browser.js — final responsive/workflow/privacy/outage QA
- docs/product-release.md — architecture/startup/security/testing/limitations
- docs/demo-playbook.md — exact Amazon/investor clicks
- docs/phase-f-release.md — this record

## 2–5. Migrations, roles, switching, Demo Mode

No migration added; 1–8 unchanged. Owner recovery, Admin configuration, delegated Manager operations, personal Resident, Business Admin and personal Staff remain distinct. Backend grants/resource ownership/dates remain authoritative.

Multiple workspace choices expose a native selector. It changes presentation only; identity/grants/scope are unchanged and private page state unmounts. Choices are workspace types, not multiple unit/business contexts. Reload uses default precedence. Single-role accounts land directly. Owner-only entry skips unreadable structure and misleading zero-building counts.

Explicit `demo_product.py --start` uses temporary SQLite, ephemeral Ring keys, synthetic accounts and localhost. No inherited bootstrap credentials or audited runtime DB. Control discovery requires scoped/development/simulation mode, a demo-marked bound structure and simulation authority. Tenant/config-only accounts see no prominent simulation control. Empty scoped startup remains unseeded. Admin's explicit Load synthetic demo building is separate and creates no accounts/access grants.

## 6–7. Ring hero and all scenarios

Real browser: Resident schedules visitor → three signed simulation events normalize/persist → Manager sees separate expected visit and arrival signals → identity stays unverified → operator manually marks arrived → Activity records both. Backend tests prove physical grants/states/actuators unchanged. Shared entrance signals do not appear for tenants without private association. Source/account mapping supplies configured Manager location, never visitor identity/destination.

All six actual browser controls returned HTTP 200:

| Scenario | Events | Result |
|---|---:|---|
| visitor_arrives | 3 | Passed |
| package_delivery | 3 | Passed |
| after_hours_person | 4 | Passed |
| emergency_access | 2 | Passed |
| contact_sensor_sequence | 2 | Passed |
| device_lifecycle | 2 | Passed |

Controls are unobstructed and fit at 1440/768/390. No automatic visitor arrival, incident, access grant, identity recognition or unlock. The scenario-name focused run passed 11 tests; the existing six-scenario parametrization is preserved in full suites.

## 8–12. Workspace final state

Admin retains persisted eight-step setup, hierarchy/hardware/accounts/permissions/policy/audit. Area terminology and affiliation separators are clearer; navigation/account chrome remains visible. Owner-only users open administrator recovery without fetching structure they cannot read.

Manager retains operational Overview, People, Visitors, Access, Maintenance, Security, Activity and Announcements. Status respects limited authority and unverified systems. Repeated Ring arrival signals group into one attention item. Configuration requires separate delegation.

Resident retains calm mobile Home, personal visitors/maintenance/access and relevant notices. Unit/reporter derive from session; no implicit physical bridge.

Business Admin retains company Home, bounded Staff delegation, visits, maintenance, access, notices and permitted devices. Staff remains a personal subset without automatic team/account management. All earlier tenant boundaries remain enforced.

## 13–17. AI, hardware, Activity, privacy and auth

AI uses filtered authenticated context, typed proposals, confirmation and fresh execution authorization/ownership/scope/expiry checks. At-most-once behavior remains tested. Browser provider failure leaves Guide usable. Launcher makes no AWS calls; live inference/provider linking remains unverified.

Cloud Ring adapter and signed pipeline exist; Simulation is labeled; Edge is Not installed. No discovery/protocol/vendor/actuator capability is invented. Configured devices stay Unverified without telemetry; hierarchy and physical zones remain separate.

Activity supplies readable Ring labels and authorized explicit location association; unknown location stays unverified. Who/what/where/when/result use projections without rewriting the event store. Other operational activity is preserved.

Privacy gates retain Admin/private-operation separation, Manager/Admin separation, Resident 101/102 isolation, same-floor X/Y isolation, Staff escalation denial, multi-role non-borrowing, guessed IDs, list/detail/mutation parity, AI and Ring ownership. Sensitive route review adds no mutation/provider bypass: demo discovery is read-only/session-derived; existing ingestion retains signatures; mutations retain permission/scope/CSRF.

Session/login/logout/CSRF/CORS/throttling/suspension/revocation/expiry tests pass. 401/logout clear private DOM data. Account/grant changes remount. Own-affiliation cache generation also invalidates edits/revocation/expiry with unchanged grants. Real browser revocation cleared unit data and restoration recovered it; workspace selection kept the account ID. Backend denial is immediate; idle display invalidation normally occurs within 30 seconds on session refresh, not push.

## 18–19. Browser/failure/request audit

105 combinations: Owner 2 pages, Admin 8, Manager 8, Resident 5, Business Admin 7, Staff 5, at each of 1440/768/390. No horizontal overflow; visible buttons meet 44px height. Skip links, keyboard/native selects, visible focus and text statuses pass. Actual mobile visitor submission works. Completed run had no uncaught application exceptions; intentional denial/outage responses are expected.

Browser directly checked empty tenant visits/maintenance/access, audience notices, loaded/loading views, provider fallback, backend interruption/recovery, actual affiliation revocation/recovery, 401 clearing and logout. Empty installation/secure provisioning/no permissions/unassigned devices/misconfigured Ring/suspension/expiry remain in isolated backend regressions and preserved UI behavior. Not every failure permutation was manually clicked at every width.

Owner configuration over-fetch was removed. Shared chrome uses session metadata and authorized demo discovery; it does not fetch other workspace snapshots for labels. Existing role projections remain bounded. No premature optimization/dependency additions.

## 20–23. Final gate results

| Gate | Exact result |
|---|---|
| Full memory suite after Manager polish | **931 passed**, 72.63s |
| Full SQLite suite after Manager polish | **931 passed**, 229.73s |
| Explicit authorization/Admin/Manager/Resident/Business/release/AI/Ring gate | **322 passed** |
| Final release + Manager focused gate including Owner fixture | **37 passed** |
| Scenario-name focused gate | **11 passed**, 10 deselected |
| New release tests | **5 passed**, included above |
| Frontend | **32 passed** |
| Typecheck / lint / production build | Passed |
| Browser roles/widths | **105 passed**, plus six controls and hero/session/outage workflows |
| Migration clean install / 7→8 upgrade / restart | Passed |
| SQLite FK / foreign_key_check / integrity_check | Enabled / empty / ok |
| pip check | No broken requirements |
| OSV public PyPI pins | **30 checked**, no advisories |
| npm audit | **161 packages**, zero vulnerabilities after narrow patch |
| Changed/untracked secret-pattern scan | **121 text files**, zero findings |
| git diff --check | Passed |

Gitleaks/pip-audit are unavailable. A reproducible pattern scan and direct OSV checks were used; this is not claimed as Gitleaks. The existing public synthetic auth fixture is narrowly recognized; matched secret contents are never printed. Advisory databases/pattern scans are bounded evidence, not certification of all vulnerabilities. All databases were isolated; audited runtime data was untouched.

## 24. Limitations

No verified physical access bridge/actuator, complete provider import, live video, live Ring certification/delivery or live Bedrock verification. Edge, elevator integration, facial recognition, billing/payments, receptionist/hotel/native-mobile products, extensive vendors, production video, lease/CAD, email/SMS/push and full password reset are deferred. Staff credentials are not delivered invitations. Photos, multiple-business context selection and push invalidation remain future work. Workspace labels are types, not unit names. Idle freshness is normally 30 seconds. Legacy simulated journeys remain separate.

## 25–27. Demos, documentation and captures

[Exact Amazon (~2:40) and investor (6–8 min) sequences](demo-playbook.md): Admin Building → Resident schedule → Demo Mode Visitor arrives → Manager review/manual arrival → Activity → Business → Guide → Admin Integrations/Edge. Investor sequence additionally uses narrow single-role profiles; the privileged presenter is not the tenant-isolation proof. No revenue numbers/final video are created.

README now leads with product problem, Ring role, startup, real/simulated boundaries and architecture. [Current release guide](product-release.md) covers roles/hierarchy/security/AI/Ring/hardware/first install/tests/limits. Historical phase/provider docs remain linked with compatibility context.

23 screenshots: each of six personas at three widths, mobile Ring review/Activity, and controls at three widths. Examples:

- [Admin](qa/f-demo-admin-1440.png): configuration checklist/readiness.
- [Manager mobile](qa/f-demo-manager-390.png): status/attention/actions.
- [Resident mobile](qa/f-demo-resident-390.png): notices/personal workflows.
- [Business mobile](qa/f-demo-business-390.png), [Staff mobile](qa/f-demo-staff-390.png): company versus personal view.
- [Owner](qa/f-demo-owner-390.png): narrow recovery authority.
- [Ring review](qa/f-ring-review-390.png), [Activity](qa/f-activity-390.png), [six controls](qa/f-demo-controls-1440.png).

## 28–30. Readiness

**AMAZON DEMO READY: YES**, for the disclosed signed software-simulation/local-Guide story. Live Ring/AWS/physical presentation is not certified.

**INVESTOR DEMO READY: YES**, with capability disclosures and narrow personas.

**PHASE F READY FOR REVIEW: YES.** Stop. No commit/merge/push/deployment/physical work.
