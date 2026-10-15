"""Explicit-path SQLite backup and restore drill. Never overwrites a database.

python -m app.maintenance backup --source PATH --destination NEW_PATH
python -m app.maintenance verify --source PATH
python -m app.maintenance restore --source BACKUP_PATH --destination NEW_PATH
Protect output files as credentials: databases include private records and sessions.
"""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
from time import monotonic

from app.database import MIGRATIONS


class MaintenanceError(RuntimeError):
    pass


def inspect_database(path, *, timeout=30):
    """Read-only structural verification; no migration or seed side effects."""
    path = Path(path).resolve(strict=True)
    deadline = monotonic() + timeout
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as conn:
        conn.set_progress_handler(lambda: int(monotonic() > deadline), 1000)
        if conn.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise MaintenanceError('Database integrity verification failed')
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise MaintenanceError('Database has foreign key violations')
        versions = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version')]
        if not versions or versions != list(range(1, versions[-1] + 1)) or versions[-1] > MIGRATIONS[-1][0]:
            raise MaintenanceError('Unsupported or incomplete schema history')
    return {'schema_version': versions[-1], 'integrity': 'ok', 'foreign_keys': 'ok'}


def copy_database(source, destination, *, timeout=30):
    """Online consistent snapshot; atomically publish only to an absent path.

    Restore uses the same operation and requires a NEW path. It never replaces a
    running installation. Switching deployment configuration is a separate step.
    """
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise MaintenanceError('Timeout must be greater than zero and at most 300 seconds')
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise MaintenanceError('Destination must be a new file; overwrite is prohibited')
    if not destination.parent.is_dir():
        raise MaintenanceError('Destination directory must already exist')
    deadline = monotonic() + timeout
    handle, temporary = tempfile.mkstemp(prefix='.nodum-snapshot-', suffix='.db', dir=destination.parent)
    os.close(handle)
    temporary = Path(temporary)
    try:
        def progress(status, remaining, total):
            if monotonic() > deadline:
                raise MaintenanceError('Snapshot deadline exceeded; destination was not published')
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=1)) as src:
            with closing(sqlite3.connect(temporary)) as target:
                src.backup(target, pages=256, progress=progress, sleep=.05)
                # A standalone snapshot must not depend on a WAL sidecar.
                target.execute('PRAGMA journal_mode=DELETE')
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise MaintenanceError('Snapshot deadline exceeded; destination was not published')
        report = inspect_database(temporary, timeout=remaining)
        with temporary.open('r+b') as stream:
            digest = sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
            os.fsync(stream.fileno())
        # Unlike replace/rename, linking cannot overwrite a competing destination.
        # Fail safely on filesystems without hard-link support.
        os.link(temporary, destination)
        return report | {'sha256': digest.hexdigest(), 'bytes': destination.stat().st_size}
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'verify', 'restore'])
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination')
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if not math.isfinite(args.timeout) or not 0 < args.timeout <= 300:
            raise MaintenanceError('Timeout must be greater than zero and at most 300 seconds')
        if args.operation == 'verify':
            if args.destination:
                raise MaintenanceError('Verify does not accept a destination')
            report = inspect_database(args.source, timeout=args.timeout)
        else:
            if not args.destination:
                raise MaintenanceError('Backup and restore require a new destination path')
            report = copy_database(args.source, args.destination, timeout=args.timeout)
        print(json.dumps({'operation': args.operation, 'status': 'verified', **report}))
        return 0
    except (OSError, sqlite3.Error, MaintenanceError):
        # SQLite/OS errors can contain filenames, SQL and private data. Do not echo.
        print(json.dumps({'operation': args.operation, 'status': 'failed',
                          'message': 'Check source integrity, schema compatibility, a new destination, directory permissions and timeout. No overwrite was performed.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
