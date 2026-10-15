

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
