# Backup and restore drill

Run from `backend` with the installed Python environment. These commands never
load `.env`, seed data, run migrations, contact providers or overwrite files.
Use explicit filesystem paths, not DATABASE_URL strings.

```powershell
python -m app.maintenance backup --source C:/nodum-data/pilot.db --destination C:/nodum-backups/pilot-20261015.db
python -m app.maintenance verify --source C:/nodum-backups/pilot-20261015.db
python -m app.maintenance restore --source C:/nodum-backups/pilot-20261015.db --destination C:/nodum-recovery/drill.db
```

Create restricted backup/recovery directories first. The tool uses SQLite's
online backup API so committed WAL records are included. It checks integrity,
foreign keys and contiguous supported migration history before publishing a
standalone file. Existing destinations, including symlinks, are rejected. Filesystems
without hard links fail safely. Default deadline is 30 seconds; `--timeout` accepts
up to 300. Nonzero exit status means the operation was not verified. JSON output
contains status, schema version, and backup digest/size, never records or secrets.

Restore ALWAYS writes a new file. For a drill, start an isolated backend using that
file and synthetic accounts. For real recovery, obtain owner approval, stop the
affected service, retain its previous database, point configuration to the new
verified file, validate startup and scoped authorization, and only then reopen
ingress. Never switch a live service or replace its database during ordinary tests.

Backups contain private data, password hashes, sessions and encrypted provider
tokens. Use OS access restrictions and encrypted storage; this tool does not encrypt
archives, schedule retention or provision keys. Back up the Ring encryption key
separately through the installation's secret-management process. Restore can revive
old sessions or grants: revoke restored sessions and reconcile users/permissions
before reopening real access. Do not test restored provider credentials against
live devices during drills. A structural verification is not proof of every
business workflow or hardware commissioning.

Test evidence: online WAL snapshot, restored repository read, corruption/schema/FK
rejection, destination race, overwrite refusal, deadline cleanup and redacted CLI
errors. Python API reference: https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
