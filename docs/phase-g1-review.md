# Phase G.1 — audit corrections

Review date: October 9, 2026. Branch: `product-platform`.

**Desktop software demo: ready for review. Responsive investor software demo: ready for review.**
These verdicts cover the disclosed synthetic Ring/local Guide demonstration, not live hardware, production commissioning, or submission eligibility.

The interrupted G.1 implementation was preserved and verified against a newly launched disposable SQLite demo on API port 8772 and frontend port 5182. Existing processes and audited runtime data were not changed. This continuation updated the browser regression script for compact Manager navigation and consolidated assistant/Business controls, and added pass reopening and assistant focus checks. No dependencies, migrations, commits, merges, pushes or deployments were added.

## Finding-by-finding results

| Audit finding | Result | Evidence |
|---|---|---|
| Manager panel overlap and account/logo collisions | Fixed | Checked 1440, 1199, 1024, 900, 768, 600 and 390 widths: no document overflow, building/attention overlap or slabs escaping the panel. Desktop/tablet/mobile screenshots inspected. |
| Apparently unmapped Ring signals | Fixed frontend lookup; provider mapping verified not a defect in fresh demo | Fresh signed simulation shows Main entrance zone. Missing mappings remain null in all six backend scenario tests. No mapping authority was broadened. |
| Unsupported arrival milestones and stale signals | Fixed | Fresh event reads Recent arrival signal; aged response fixture reads Historical arrival signal. Review contains only the recorded signal milestone, with identity unverified and no access claim. |
| Visitor passes cannot reopen | Fixed | Fresh Resident visit created through the UI; pass closed, reopened, page reloaded and pass reopened again. Actual cancellation updates the open pass to Cancelled/Revoked and can be reopened via All visits. Expired response fixture updates the open pass to Expired. |
| Assistant opens out of view | Fixed | Mobile activation reveals and focuses the panel; Escape closes it and returns focus. Local Guide and explicit AI-unavailable response verified. |
| Building labels, service crowding and movement | Fixed | Shared building rendering inspected on desktop/tablet/mobile. Apartment labels appear once, services use compact rows, keyboard selection works, and both selected-floor transforms are `none` under reduced motion. |
| Admin preview disconnected from configuration | Fixed | Selecting Floor 2 updates inspector and hierarchy to its businesses; Configure Floor 2 opens its edit form. Unrelated floor contents remain collapsed. Demo initialization is secondary when already seeded. |
| Business duplicate and empty sections | Fixed | One visitor-status summary, one schedule action, compact no-signal text, retained notices and Staff boundaries. Populated arrival presentation checked with an explicit response fixture; backend business-mapping isolation test passed separately. |
| Resident identity hierarchy and initials | Fixed | Profile/credential status separated; initials exclude Synthetic suffix. Long-name/building-name fixture at 390px has no card/name overflow. Primary invitation remains visible in the normal mobile profile. |
| Ordinary login lacks product continuation | Fixed | Actual sign-in returned to frontend and authorized workspace. Targeted auth tests cover exact configured-origin roots and rejected unsafe return destinations; Ring linking remains a separate flow. |

## Validation

- Targeted backend: **167 passed** (auth, Manager, Resident, Business), memory fixture mode. Includes all six Ring scenarios and role/scope regressions. Initial attempt failed because Windows denied access to the default pytest temporary root; a fresh unique temporary directory resolved it without application changes.
- Frontend unit tests: **32 passed**.
- TypeScript check (through production build), lint and production build: **passed**. Lint repeated after browser-script edits: passed.
- Browser suite: **104 standard role/page/width checks**, plus the separate Resident mobile Notices archive path, passed. Six personas at 1440/768/390, button sizing, overflow, keyboard focus, scoped notices and role navigation covered.
- Fresh UI visitor creation, pass reopening after refresh, signed Ring arrival, manual arrival, mapped Activity, no shared-entrance leakage into Business, unchanged identity during switching: **passed**.
- Membership revocation/recovery, unauthorized-session private-data clearing, logout clearing, provider fallback and network recovery: **passed**. No uncaught application exceptions in the completed browser suite.
- Additional seven-width Manager geometry checks, reduced motion, long labels, Admin selection/edit, actual pass cancellation and presentation fixtures: **passed**, with fixture boundaries described above.
- `git diff --check`: **passed**.

Screenshots were saved outside the repository at `C:/Users/marwa/AppData/Local/Temp/nodum-g1-20261009/`. Representative files: `manager-1440.png`, `manager-768.png`, `manager-390.png`, `g-resident-visitor-pass-390.png`, `cancelled-pass-390.png`, `resident-long-name-390.png`, `admin-selected-floor-390.png`, and `business-signal-fixture-390.png`. This temporary directory is local evidence, not a durable release asset. Earlier Phase G screenshots already present in the repository were left untouched.

## Remaining readiness work

- Final submission requirements, deadline, reviewer access and package have not been rechecked or submitted.
- Investor deck, commercial evidence, funding ask and final backup video are not completed by this engineering review.
- Live Ring linking/delivery, real Bedrock inference and physical control remain unverified. Edge remains not installed. The demonstrated visit pass is a record, not a scannable credential.
- This focused continuation did not rerun the entire backend suite in both storage modes or a new vulnerability scan. Phase F totals remain historical evidence, not results for the current changes.
- Historical/expired/populated-Business presentation edge cases used explicit browser response fixtures. Business isolation and unmapped Ring behavior were also tested independently in real backend service tests; no live Business hardware event is claimed.

Next release step: freeze the reviewed demo version, rehearse the short demo from a fresh disposable database, then assemble and verify the submission/pitch materials. Publishing and committing still require explicit authorization.
