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
- Wrote project story, five feedback answers, AWS description, factual friction log, video script and owner instructions. Filled factual Additional info fields in the existing Devpost form; personal fields are not fabricated. Browser form values are pending the owner's completion/save.
- Main repository was independently confirmed private using the existing authorized Git credential helper; current branch is main and repository permissions permit pushing. No repository visibility change was made.

## Test evidence

- Full candidate backend before the final three Playground tests: **1,105 passed, 4 SQLite-only skips**.
- Final affected SQLite batch (judge setup, official Playground, hosting, product, Ring simulation, Manager, auth and authorization): **228 passed**.
- Final Playground memory tests: **3 passed**.
- Frontend: **34 passed**, lint, typecheck and packaged production build passed.
- Python correctness lint and changed-file credential-pattern scan passed with no findings. This is a bounded scan, not a complete history/security audit.
- Hosted CI on the published candidate must be checked separately; local tests do not stand in for its outcome.

## Still open

1. Railway rejected two activation attempts with “Deploys have been paused temporarily.” Current live API still uses legacy_demo, so the new hosted UI, scoped synthetic accounts and hosted AWS answer are not yet accepted.
2. Owner reports a trial expiring in nine days or at credit exhaustion. Paid hosting coverage is needed through November 20; no purchase was made.
3. Official Ring production linking, inbound code-delivery transport and vendor-origin signed webhook delivery remain unverified. Playground discovery is a genuine official runtime call, with a temporary token and limited scope. Do not call it full live Ring integration or guaranteed hackathon eligibility.
4. Final animation, recording and public video link are not produced. The 2:50 script is ready; planned animated intro is 25 seconds.
5. Owner must complete factual personal/team declarations and final review in Devpost. The entry remains a draft until saved and submitted.
6. Final private repository reviewer access/invitations need checking against current rules. No third party was granted access by this preparation.
7. No additional public Open Source contribution was created. AWS Builder is the recommended mini-challenge based on verified real inference; winning odds cannot be established.

Use [OWNER_STEPS.md](OWNER_STEPS.md) for the exact remaining actions. Do not record or advertise hosted success until the final deployment passes.
