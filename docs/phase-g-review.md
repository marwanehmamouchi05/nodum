# Phase G — visual product review

October 9, 2026 · `product-platform` · Phase F checkpoint preserved.

**READY FOR REVIEW**, including owner/Astra visual judgment. This is a software-demo review verdict, not confirmation of investor reaction, submission eligibility or production readiness. The old Phase F design was not restored. No commit, push, merge or deployment was performed.

## 1. Exact files changed

This continuation changed eight implementation files: `frontend/src/admin/AdminWorkspace.tsx`, `frontend/src/admin/admin-phase-g.css`, `frontend/src/components/BuildingSection.tsx`, `frontend/src/components/building-section.css`, `frontend/src/ProductBar.tsx`, `frontend/src/product-phase-g.css`, `frontend/src/manager/manager-phase-g.css`, and `frontend/src/manager/ManagerCommandCenter.tsx`, plus this report. Existing Phase G/G.1 changes were preserved. The full current source/test/document inventory relative to the Phase F checkpoint is recorded below.

## 2. Design system

One navy, teal, white and cool-gray system with system fonts, consistent status semantics, visible focus and reduced motion. The building is the signature visual. No new dependency, external font or analytics was added.

## 3. Shared shell

Existing permission-aware workspace/account bar retained. Single-role mobile accounts now use a compact one-row account/sign-out arrangement. Multi-role controls retain their responsive grid. Admin's secondary toolbar and Building title spacing were reduced. Synthetic state remains visible; individual simulated events retain their label.

## 4. Digital building

Authorized six-level architectural section with aligned slabs, a continuous core, roof edge, shallow structural depth, differentiated underground services and an entrance accent. Attention/Visitors/Maintenance/Devices overlays and keyboard-accessible flat floor list remain. Location matching uses explicit identifiers, not title inference. Reviewing a mapped Manager arrival selects its configured place in the building; an unmapped event does not invent a selection. Admin can omit the embedded inspector because its configuration inspector now occupies the right column.

## 5. Manager command center

Building, current status, freshness, attention and operational summary remain together. Larger figures improve scanning; unverified devices are labeled explicitly. At 1440×900 the complete six-level building and top attention/summary are visible. At compact widths the attention panel leads and the building follows without overlaps.

## 6–7. Resident and profile

Personal Home, visits, maintenance, access and notices preserved. Primary actions stay prominent on mobile. The navy identity card shows name, unit, building and Credential not issued. Initials omit the Synthetic suffix, long labels wrap, and the card makes no scannable-credential claim. Compact single-role account chrome reduces space before the profile.

## 8. Visitor pass

Polished record presentation follows successful scheduling and can reopen from authorized existing visits after refresh. It shows host, destination, building, local time window, current status and the distinction between logical authorization and physical access. No fake QR, NFC credential or unlock behavior.

## 9. Business reception

Visitor status and today's schedule lead Home, followed by useful actions and notices. Duplicate visitor metrics were removed during G.1. Empty Ring context is a quiet line; legitimate arrival context retains simulation and unverified-identity labels. Staff remains narrower than Business Admin.

## 10. Admin configuration

Desktop now uses a left floor/space directory, center digital building and right selected-place configuration inspector. Selecting Floor 2 connects all three and exposes Business X/Y. Configure opens the selected record's existing edit form. Registered devices distinguish registration from connection/physical verification. Smaller widths stack the same controls. Add a floor or space is progressive disclosure instead of a permanently expanded form; the existing setup workflow remains intact.

## 11. Ask Nodum

Consistent Ask Nodum entry wording and shared focusable panel preserved. Opening reveals and focuses it; Escape returns focus. Local Guide and provider unavailability are explicit; proposal confirmation/authorization behavior is unchanged.

## 12. Ring presentation

Fresh synthetic signed delivery, mapped entrance context, identity unverified, manual arrival confirmation and Activity remain functional. Historical signals are distinguished from recent signals. No inferred identity or physical unlock; shared-entrance data does not appear in unrelated Business context.

## 13. Responsive QA

Final browser run passed **104 standard page/width checks plus the separately checked mobile Resident Notices path**, across Owner/Admin/Manager/Resident/Business Admin/Staff at 1440/768/390. No uncaught application errors. Buttons, navigation, keyboard focus, notices isolation, workspace identity, private-data clearing, provider fallback and backend recovery passed.

Additional final Manager geometry checks at **1440/1199/1024/900/768/600/390** found no document overflow, building/attention overlap or escaping floor slabs. Final Admin selection and editor opening checked at 1440/768/390; flat-list mode and Add space disclosure checked. Reduced motion and long-name fixtures passed in the preceding G.1 review; this continuation adds no motion or label contracts.

## 14. Frontend validation

**32 tests passed. Typecheck, lint and production build passed.** Typecheck/lint/build repeated after the final Admin changes. `git diff --check` passed. Browser smoke includes fresh Resident scheduling, pass appearance/reopening after refresh, Business view, Ring visitor_arrives, manual Manager arrival, Activity and workspace switching.

## 15. Backend validation

No backend code or contract changed in this continuation. The immediately preceding G.1 validation passed **167 targeted auth/Manager/Resident/Business tests**, including the six Ring scenarios, using isolated fixtures. Those relevant results are retained without unnecessarily rerunning the complete backend suites. Phase F's full-suite totals are historical, not new results for Phase G.

## 16. Screenshots reviewed

Local evidence directory: `C:/Users/marwa/AppData/Local/Temp/nodum-g1-20261009/`.

- `studio-final-1440.png`, `studio-final-768.png`, `studio-final-390.png`: connected Admin configuration.
- `command-center-final-1440.png`, `command-center-final-768.png`, `command-center-final-390.png`: structural building and operational context.
- `g-demo-resident-390.png`, `g-demo-business-390.png`: final role-specific mobile presentation.
- `g-resident-visitor-pass-390.png`, `g-ring-review-390.png`, `g-activity-390.png`: final workflow captures.
- G.1 supplementary evidence includes long-name, cancelled-pass and explicit Business arrival presentation fixtures.

Screenshots are outside the repository and temporary; existing earlier Phase G captures in the repository were not discarded.

## 17. Remaining visual weaknesses

The building remains a stylized section rather than a true 3D/CAD model. Admin's mobile directory and inspector still require scrolling, although they share selection. Several operational forms retain conventional layouts. Business with no scheduled visitors necessarily has less visual density. Large-volume/very long building structures need a separate design review. The owner/Astra should evaluate whether the overall presentation meets the desired premium/investor standard; automated tests cannot establish that.

## 18. Remaining functional limitations

Physical credentials, automatic real unlock, Edge runtime and live hardware commissioning are absent. Live Ring linking/delivery and Bedrock inference are not verified by this local demo. Some contracts lack mapping identifiers and remain unmapped. Historical/expired/Business arrival presentation edge cases used labeled response fixtures during G.1, with backend isolation tested separately. Pitch deck, commercial validation, submission rules and final recording are outside this frontend review.

## 19. Verdict

**Phase G is READY FOR REVIEW as a materially updated, functional software demo.** Review the running application and screenshots before declaring final visual approval. Stop here; do not commit, push, merge or deploy without further instruction.

## Current Phase G source/test/document inventory


- `backend/app/api/auth.py`
- `backend/app/services/business_workspace.py`
- `backend/app/services/manager.py`
- `backend/app/services/resident.py`
- `backend/app/web/auth.html`
- `backend/app/web/auth.js`
- `backend/demo_product.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_business_workspace.py`
- `backend/tests/test_manager.py`
- `backend/tests/test_resident.py`
- `docs/phase-g-review.md`
- `docs/phase-g1-review.md`
- `frontend/src/App.tsx`
- `frontend/src/ProductBar.tsx`
- `frontend/src/admin/AdminWorkspace.tsx`
- `frontend/src/admin/admin-phase-g.css`
- `frontend/src/admin/admin-responsive-phase-g.css`
- `frontend/src/business/BusinessForms.tsx`
- `frontend/src/business/BusinessReception.tsx`
- `frontend/src/business/BusinessWorkspace.tsx`
- `frontend/src/business/business-phase-g.css`
- `frontend/src/business/model.ts`
- `frontend/src/components/AssistantPanel.tsx`
- `frontend/src/components/BuildingSection.tsx`
- `frontend/src/components/Icon.tsx`
- `frontend/src/components/VisitPass.tsx`
- `frontend/src/components/building-section.css`
- `frontend/src/components/visit-pass.css`
- `frontend/src/design-system.css`
- `frontend/src/main.tsx`
- `frontend/src/manager/ManagerCommandCenter.tsx`
- `frontend/src/manager/ManagerWorkspace.tsx`
- `frontend/src/manager/manager-phase-g.css`
- `frontend/src/manager/manager.css`
- `frontend/src/manager/model.ts`
- `frontend/src/product-phase-g.css`
- `frontend/src/product.css`
- `frontend/src/resident/ResidentForm.tsx`
- `frontend/src/resident/ResidentWorkspace.tsx`
- `frontend/src/resident/model.ts`
- `frontend/src/resident/resident-accessibility-phase-g.css`
- `frontend/src/resident/resident.css`
- `frontend/tests/product.browser.js`
