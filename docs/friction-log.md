

## 2026-10-15 isolated pilot loop
- Resolved: Windows fsync on read-only temporary snapshot handle raised bad descriptor; writable handle repaired; 54 recovery/persistence tests passed.
- Protected: original worktree has extensive uncommitted Phase G changes; copied/hash-verified into isolated worktree, private configs/database backed up outside Git. No existing environment copied into development runtime.
- Deferred external integration blockers: live actuator reconciliation and confirmed Ring inbound delivery; exact handoffs in ASTRA_HANDOFF.md. No repeated protocol guessing or hardware commands.


## 2026-10-15 resume loop
Resolved test-only broker Click pin conflict by separating broker and app environments and restoring the app pin; both pip checks pass. Initial burst assertion ignored Manager latest-100 cap; fixed drill checks storage and projection separately. Initial point-read test missed a fixture import; repaired and SQLite test passed. No production workaround or security bypass used. Remaining actual broker TLS/ACL and history retention gaps are explicit.


## 2026-10-15 engineering mission

- Root-level pytest originally could not resolve app; added explicit root pytest
  configuration. Both root and backend invocation now work without global PYTHONPATH.
- Additive indexes exposed hard-coded schema-8 assertions in recovery/release tests.
  Replaced them with migration-history checks, retaining no-side-effect preflight proof.
- Correctness lint flagged deleting a closure-captured body buffer; clearing it keeps
  allocation bounded and avoids an undefined-name pattern. Existing attack tests pass.
- External client no longer relies on assert statements that Python -O can remove;
  deterministic mutation/optimization tests cover evaluator failure behavior.
- Broker remains a separate environment; no application pin changes to resolve its
  dependency constraints. Temporary coordination files carry timing/IDs only, never
  substitute for actual API/protocol events.
- Official Ring evidence and physical command semantics remain concrete external
  dependencies; no fabricated success or repeated protocol guessing.


Phase 1 closure fixes: browser refresh lost a multi-role workspace and non-Admin
section; URL restoration now validates known screens and retains server authority.
The Windows shared pytest temp root denies access, so onboarding selects a fresh
unique --basetemp without deleting or changing its ACLs. Caddy published checksums
are SHA-512. SQLite online backup changes file-header bookkeeping: compare logical
API outcomes plus structural integrity, not identical hashes between two valid
backup copies. An empty authorized collection may correctly return 200; use an
explicit denied resource for a 403 browser oracle. All final acceptance runs pass.

---

# Nodum submission friction log

October 21, 2026. Entries describe actual observations and distinguish integration issues from provider incidents.

## Ring: a temporary Playground session is not a linked application

- Task: demonstrate documented Ring technology inside Nodum without hardware.
- Steps: open the signed-in Ring developer console, generate an approved temporary token, invoke device discovery, then call the same official endpoint through Nodum.
- Expected: demonstrate official runtime use with clear provenance and repeatable setup.
- Actual: device discovery returned HTTP 200 and one sandbox device. The token expires after 30 minutes. This does not establish production account linking or vendor-origin webhook delivery.
- Severity: Important for reproducible review; not an observed Ring API failure.
- Workaround: a restricted, read-only Playground discovery path, separate from customer account linking and clearly separate from the custom signed-event generator.
- Suggestion: a complete documented sandbox-to-app example, with temporary credential lifecycle and signed event provenance.

## Bedrock: local inference succeeded while hosted inference was unavailable

- Task: ask the hosted Nodum chatbot a read-only question.
- Steps: sign in, submit an authenticated chat request, compare server configuration with a real local Converse call.
- Expected: configured credentials/model access in the running deployment and a useful response.
- Actual: hosted chat returned HTTP 503/unavailable; local Nova inference succeeded. Railway lacked AWS credential variables. Credentials were configured privately, but redeployment was blocked by Railway's platform incident. The packaged local app then completed a scoped manager_operations tool call using real Bedrock inference.
- Severity: Important; a deployment configuration/activation issue, not evidence that Bedrock itself was down.
- Workaround: verify the standard credential chain and one real inference request in each environment; keep local Guide/forms functional during failure.
- Suggestion: a deployment preflight example with credential-presence, IAM/model/region and inference checks, without secret disclosure.

## Railway infrastructure incident (separate from Amazon product feedback)

- Task: activate the hosted AWS configuration and publish the judge release.
- Steps: inspect deployment/health, set the missing credentials privately, request a redeploy.
- Expected: a controlled deployment and hosted retest.
- Actual: existing health/login responded, but Railway explicitly rejected redeployment because deployments were paused. Its official status page reported a matching incident.
- Severity: Important for release timing.
- Workaround: prepare and test a secret-free deployment package locally; keep the existing running service and persistent storage unchanged.
- Suggestion: distinguish running-service health from deployment-platform readiness in release instructions.
