# Submission preparation — October 21, 2026

## Completed and independently checked

- Isolated candidate based on released main `ad9e38c`; original working files and the existing release checkout preserved.
- Imported the recent Ring timestamp/refresh corrections while preserving newer hash navigation.
- Added an optional same-origin compiled interface at `/app/`; API-only installations preserve their existing root response.
- Added explicit scoped synthetic judge installation with a separate persistent `*judge-demo.db` path, private passwords, no repeated reset, and production session/CSRF rules retained.
- Added a server-side official Ring Playground device-list check. Operator grants and explicit demo restrictions apply; the temporary token is never returned, no customer account is linked, and discovery does not write Ring events or permissions.
- Official live evidence: Ring API HTTP 200, one sandbox device; Nodum endpoint HTTP 200 with official_ring_playground provenance. Also verified in the Chrome interface.
- AWS live evidence: local Converse response succeeded; the packaged Nodum app completed a real Bedrock question with a successful scoped manager_operations tool result.
- Configured the existing Nodum IAM user's credentials privately in Railway. This is staged configuration, not a claim that the running hosted process has activated it.
- Fresh local UI sign-in, Manager role, official discovery button, custom offline/online scenario and immediate Security signal refresh were exercised. Official discovery and custom signals are visibly separate.
- Prepared a secret-free upload package and activation helper that preserves the existing Railway database and stores reviewer credentials only in ignored local secrets.
- Wrote project story, five feedback answers, AWS description, factual friction log, video script and owner instructions. Filled factual Additional info fields in the existing Devpost form; personal fields are not fabricated. The factual fields, solo entrant selection, repository URL and friction log have been saved in Devpost. Owner-confirmed personal declarations are also saved; Devpost now reports DRAFT, 3/5 steps done. The video remains pending.
- The owner authorized public judging access. The existing repository is now public with a detected MIT license; anonymous GitHub API access returned 200. A scan of 729 historical text blobs found no credential-pattern matches or tracked private material paths.

## Test evidence

- Full candidate backend before the final three Playground tests: **1,105 passed, 4 SQLite-only skips**.
- Final affected SQLite batch (judge setup, official Playground, hosting, product, Ring simulation, Manager, auth and authorization): **228 passed**.
- Final Playground memory tests: **3 passed**.
- Frontend: **34 passed**, lint, typecheck and packaged production build passed.
- Python correctness lint and changed-file credential-pattern scan passed with no findings. This is a bounded scan, not a complete history/security audit.
- GitHub CI passed on final application candidate `5c9a70d`; merged main `c278854` has the same tested tree. Run: https://github.com/marwanehmamouchi05/nodum/actions/runs/39621673735 .

## Still open

1. Railway rejected two activation attempts with “Deploys have been paused temporarily.” Current live API still uses legacy_demo, so the new hosted UI, scoped synthetic accounts and hosted AWS answer are not yet accepted.
2. Owner reports a trial expiring in nine days or at credit exhaustion. Paid hosting coverage is needed through November 20; no purchase was made.
3. Official Ring production linking, inbound code-delivery transport and vendor-origin signed webhook delivery remain unverified. Playground discovery is a genuine official runtime call, with a temporary token and limited scope. Do not call it full live Ring integration or guaranteed hackathon eligibility.
4. A silent 25-second illustrated intro is prepared locally; final recording, narration and public video link remain pending. The 2:50 script is ready.
5. Owner-confirmed personal and solo entrant fields are saved. The entry remains DRAFT, 3/5 steps done, pending the video and final review/submission. Chrome local upload permission is enabled; two captioned screenshots and a thumbnail are saved.
6. Public repository access is complete; judges need no invitations. Keep the repository accessible through judging and preserve the submitted release.
7. No additional public Open Source contribution was created. AWS Builder is the recommended mini-challenge based on verified real inference; winning odds cannot be established.

Use [OWNER_STEPS.md](OWNER_STEPS.md) for the exact remaining actions. Do not record or advertise hosted success until the final deployment passes.

## Independent follow-up review — October 21

- Fetched GitHub: main was `d002e98`; anonymous API confirms public visibility and MIT license. Application source in `artifacts/judge-package-final` matches the reviewed checkout; no dotenv/database/key paths were found in the package.
- Ran focused SQLite checks for judge installation, official Playground permissions, product hosting and authentication origins: **44 passed**. The initial run had 32 passes and 12 fixture errors because the default Windows temporary folder was inaccessible; rerunning with a fresh unique temporary directory passed all 44.
- Local packaged browser on port 8891: custom offline/online scenario saved two events and refreshed Manager Security automatically. At 390 × 844, demo controls and the Resident invitation form are readable and fit the viewport. A new synthetic Review Visitor was scheduled from mobile and remained visible after reload. A fresh local assistant question completed and correctly included that newly saved visitor. This is local evidence, not hosted acceptance.
- Reopened saved Devpost fields: confirmed solo declarations, Ring/AWS selections, Open Source No, five feedback answers, 11 tags and two captioned screenshots. Testing URL and final video are blank. Saved and reopened a story correction explicitly identifying the package as locally verified and hosted activation as blocked; preview confirms it. No hosted credentials were added.
- Railway deployment inventory still identifies `ad9e38c` (October 17) as the running release, with `backend` root, Dockerfile builder and `/data` volume. October 21 18:45 UTC status update still reports paused builds/deployments. API health is 200 but `/app/` and `/ring/playground/devices` are 404.
- Private configuration snapshot saved in ignored secrets. Database backup attempt did not execute because CLI SSH has no configured key. Resolve this and verify a database backup before first deployment; preserve the old database and volume.
- Found and fixed a deployment configuration risk: automatic GitHub deploys were enabled although the repo backend build does not include the generated frontend. Disabled auto deploys and verified the UI state; future judge releases use the prepared package explicitly. The current service was not restarted.
- Managed volume backups show none and require Pro on the current trial; no upgrade was made. The existing browser console remained at Connecting.
- No application-code defect was established by this bounded review. Corrected stale upload/video/setup/repository notes. Hosted authentication, provider inference, restart persistence and responsive verification remain pending platform recovery.

## Current compliance checkpoints

[Official rules](https://amazonappdev2026.devpost.com/rules), rechecked October 21:
submission deadline October 23 at 12:00 PDT (20:00 Africa/Casablanca); judging
November 9–20 at 12:00 PST (21:00 Africa/Casablanca). Keep judging access through
November 20 and preserve the submitted version. Final materials require an English
public YouTube/Vimeo demo under three minutes, runnable source, track runtime use
and product feedback. The Ring segment must show the app with an official simulator
or device; retain official Playground discovery alongside the distinctly labeled
custom event demonstration. AWS Builder needs its service-use description; a public
main repository alone does not qualify as the additional Open Source contribution.
Final submission and legal acceptance remain with the owner.
