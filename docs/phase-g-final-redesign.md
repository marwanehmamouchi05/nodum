# Phase G final visual redesign — resumed review

October 10, 2026. Existing `product-platform` worktree preserved. No commit, push, merge or deployment.

## 1. Interruption point

The audit and remediation plan were complete. Manager's separate toolbar had been removed, creation forms placed in disclosures, visitor records restructured and Ring signals condensed. Shared ActionForm success behavior was partially implemented. These files passed typecheck on resume; the broader visual composition had not been finished.

## 2. Work already present

Phase G/G.1 included the shared building component, role workspaces, scoped projections, reopened visitor passes, assistant focus handling, Ring mapping, safe login continuation, accessibility fixes and earlier QA reports. All were preserved. `phase-g-review.md`, `phase-g1-review.md`, the working diff and existing screenshot evidence were reviewed. Older repository captures were not treated as the final baseline.

## 3. Completed after resume

Added final composition styles in `frontend/src/experience.css`; completed Resident and Business Home composition, Admin studio/disclosures, Manager record presentation and clean presentation seeding. Reviewed rendered screens, corrected tablet navigation and compact selection alignment, validated forms and saved new evidence in `docs/qa/final-*.png`.

## 4. Core problems

Repeated bordered containers obscured hierarchy. Full-width identity cards and forms used space without adding meaning. Multiple header layers competed with content. The building read as detached beveled cards. Demo records contained QA names, timestamps and repeated simulations. Admin's compact sidebar could sit beneath the shared account bar.

## 5. Strategy

Make the building and current work dominant. Use one white work surface with internal separators. Keep creation, configuration and supporting explanations behind explicit controls. Give Manager, Business, Resident and Admin different compositions while preserving the same visual language and permissions.

## 6. Removed or simplified

Removed the Manager secondary toolbar, building bevels, empty default building inspector, duplicate Business destination text, repeated welcome/name heading, prominent Quick actions container and full-width Resident identity banner. Converted visitor cards to rows and repeated Ring paragraphs to a signal log. Reduced repeated integration copy, collapsed hardware editors and added dismissible demo feedback.

## 7. Design system and color

Warm neutral canvas `#F4F5F3`, white work surfaces, graphite/green navigation `#1D2C29`, restrained action color `#17645B`, neutral borders and semantic status colors. System fonts retained. Fewer shadows, smaller corner radii, consistent typography, 44px action targets and visible keyboard focus. No external fonts, dependencies or analytics.

## 8. Building result

One aligned structural envelope with continuous sides, roof and foundation; thin shared floor divisions; differentiated service level. Existing floor/space relationships and explicit mapped records only. Selection reveals details; flat-list mode remains. No invented occupancy, geometry, device state or physical readiness. Compact selected-floor alignment was checked explicitly after the final CSS correction.

## 9. Manager

Building and attention share one work surface. Status and update time remain visible. Operational totals use compact rows. Visitors default to current records, sort by start time and expose details on demand. Maintenance creation and announcements start collapsed; request updates remain available. Ring retains simulation labels and manual identity/arrival review.

## 10. Business

Reception dominates Home, with expected visitors and time/status rows. Notices and secondary actions occupy a quieter supporting column on desktop, then stack on smaller screens. Two real synthetic Business visits demonstrate the workflow. Business Staff remains narrower than Business Admin; unrelated entrance signals stay out of the Business scope.

## 11. Resident

Compact personal profile beside daily information on desktop, stacked on mobile. Invite visitor is the primary action. Credential status no longer crowds the name. The pass remains a truthful visit record, can reopen after refresh, and has a constrained desktop width. The home visit label distinguishes an arrived visit from an upcoming visit.

## 12. Admin

Directory, building and inspector share one surface. Compact widths use a collapsible floor directory; selecting a floor updates the inspector and closes the directory. Hardware location forms and record creation are disclosed only when needed. Ring connection requirements are expandable. Tablet navigation no longer hides beneath the account bar.

## 13. Navigation and disclosure

Existing role-aware navigation and backend authority remain intact. Manager tools sit beside the page heading. Admin compact navigation scrolls horizontally; the floor directory has an explicit expanded state. Successful disclosed ActionForms close and return focus to their summary; failed submissions remain open. A real maintenance submission verified this behavior.

## 14. Demo data

Added optional `presentation=True` seeding, enabled by the disposable demo launcher. It creates four synthetic visits through the actual Resident/Business services with real affiliation-derived destinations and relative time windows. Ordinary test seeding stays unchanged. No existing runtime database was edited or purged. A fresh disposable local database replaced the QA-heavy demo created during this run. Current demo also contains the clean Salma visitor and entrance-signage request created during workflow QA; no timestamp-based QA names remain in that instance.

## 15. Screenshot evidence

Final capture families, each at 1440, 768 and 390: `final-manager-overview`, `final-manager-visitors`, `final-manager-maintenance`, `final-manager-access`, `final-business-home`, `final-resident-home`, `final-admin-building`, `final-admin-hardware`, `final-admin-integrations`, `final-schedule`, `final-pass`, and `final-ring`. Earlier `final-qa-*` captures belong to the automated regression run and contain test-generated records. The final named captures supersede earlier unqualified `final-manager-*`/`final-admin-*` captures.

Visual review led to narrower profile/pass composition, tighter operational rows, smaller hardware records, collapsed compact directory and corrected selected-floor alignment. Screenshot timestamps use the browser's locale; no live hardware state is inferred.

## 16. Responsive and browser QA

104 role/page/width checks passed, plus the separately exercised mobile Resident notice archive. The full suite covered six personas at 1440/768/390, overflow, button sizing, navigation and focus. Fresh scheduling, pass reopening, signed Ring simulation, manual arrival, Activity mapping, unchanged identity during switching, membership revocation/recovery, 401 clearing, logout, Guide fallback and network recovery passed without uncaught application errors.

After final styling changes, 18 affected Manager/Admin page-width checks passed without document overflow. Additional compact directory selection, Admin editor opening, actual maintenance submission and pass reopening passed. Latest selected-slab positions were identical at 390px. Final minor styling did not require repeating the entire backend or full browser matrix.

## 17. Frontend validation

32 unit tests passed. Typecheck, lint and production build passed; typecheck/lint/build were repeated after the final component changes. `git diff --check` passed. No dependencies added.

## 18. Backend validation

Six focused `test_product_release.py` tests passed, including a new presentation-seed test proving scoped visitor isolation, expected state, no physical access and no fabricated Ring events. This run changed only disposable demo seeding, not authorization or API contracts. Earlier G.1's 167 backend tests are historical supporting evidence, not rerun totals.

## 19. Remaining visual weaknesses

The building is a schematic, not a measured architectural model. Large buildings and high record volumes need separate visual evaluation. Mobile Admin still requires scrolling between building and inspector. Account/role controls remain visible in the multi-role presenter demo. Secondary account, policy and audit screens retain conventional administrative patterns. The aesthetic is restrained rather than cinematic.

## 20. Truthful limitations

No verified physical credentials, QR/NFC credential, automatic unlock, face recognition, Edge runtime or commissioned hardware health. Ring flow here is signed simulation, explicitly labeled. Live Ring account linking/delivery and real AI provider inference were not established by these checks. The building represents configuration and authorized records, not a live digital twin. Submission package, deck, commercial evidence and production readiness are outside this visual task.

## 21. Investor readiness judgment

Yes for a guided, explicitly synthetic investor software demonstration. This is a visual/product judgment from the rendered screens and working workflow, not a claim that every screen is a finished premium reference or that the company is ready for investment/submission.

## 22. Why

The opening screen explains the building; each role has a clear purpose; reception and invitations show useful work; configuration has spatial continuity; the UI no longer relies on large repeated cards to suggest substance. A presenter can demonstrate building context, schedule a visit, review an entrance signal manually and show the recorded result without implying unsupported capabilities.

Local preview: http://127.0.0.1:5183/ (API 8773). Processes and data are disposable and local. Work stopped after review and documentation; nothing published.
