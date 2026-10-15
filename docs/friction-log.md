

## 2026-10-15 isolated pilot loop
- Resolved: Windows fsync on read-only temporary snapshot handle raised bad descriptor; writable handle repaired; 54 recovery/persistence tests passed.
- Protected: original worktree has extensive uncommitted Phase G changes; copied/hash-verified into isolated worktree, private configs/database backed up outside Git. No existing environment copied into development runtime.
- Deferred external integration blockers: live actuator reconciliation and confirmed Ring inbound delivery; exact handoffs in ASTRA_HANDOFF.md. No repeated protocol guessing or hardware commands.
