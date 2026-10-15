"""Recovery uses disposable files, including committed records still in WAL."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

import pytest

from app.maintenance import copy_database, inspect_database, main, MaintenanceError
from app.sqlite_repository import SQLiteRepository


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'source.db'
    SQLiteRepository('sqlite:///' + str(path)).initialize(seed_demo=False)
    return path


def test_wal_backup_and_restored_repository_preserve_records(source, tmp_path):
    backup, restore = tmp_path / 'backup.db', tmp_path / 'restored.db'
    with closing(sqlite3.connect(source)) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.execute('PRAGMA wal_autocheckpoint=0')
        writer.execute('INSERT INTO people VALUES (?, ?)', ('synthetic-person', json.dumps({'id': 'synthetic-person', 'name': 'Synthetic person', 'role': 'employee'})))
        writer.commit()
        assert Path(str(source) + '-wal').stat().st_size > 0
        report = copy_database(source, backup)
        assert report['integrity'] == 'ok' and len(report['sha256']) == 64
    copy_database(backup, restore)
    repo = SQLiteRepository('sqlite:///' + str(restore))
    assert repo.get_person('synthetic-person').name == 'Synthetic person'
    assert not Path(str(backup) + '-wal').exists()


def test_no_overwrite_or_same_file(source, tmp_path):
    before = source.read_bytes()
    with pytest.raises(MaintenanceError):
        copy_database(source, source)
    destination = tmp_path / 'existing.db'
    destination.write_bytes(b'preserve')
    with pytest.raises(MaintenanceError):
        copy_database(source, destination)
    assert destination.read_bytes() == b'preserve' and source.read_bytes() == before


@pytest.mark.parametrize('damage', ['corrupt', 'future', 'gap', 'foreign_key'])
def test_invalid_snapshot_never_published(source, tmp_path, damage):
    if damage == 'corrupt':
        source.write_bytes(b'not a database')
    else:
        with closing(sqlite3.connect(source)) as conn:
            if damage == 'future':
                conn.execute("INSERT INTO schema_migrations VALUES (9, 'synthetic')")
            elif damage == 'gap':
                conn.execute('DELETE FROM schema_migrations WHERE version=2')
            else:
                conn.execute('INSERT INTO work_orders VALUES (?, ?, ?)', ('bad', 'missing', '{}'))
            conn.commit()
    destination = tmp_path / 'rejected.db'
    with pytest.raises((MaintenanceError, sqlite3.Error)):
        copy_database(source, destination)
    assert not destination.exists()
    assert not list(tmp_path.glob('.nodum-snapshot-*'))


def test_destination_race_preserves_other_file(source, tmp_path, monkeypatch):
    import app.maintenance as module
    destination = tmp_path / 'raced.db'
    link = module.os.link
    def raced_link(a, b):
        destination.write_bytes(b'other writer')
        link(a, b)
    monkeypatch.setattr(module.os, 'link', raced_link)
    with pytest.raises(FileExistsError):
        copy_database(source, destination)
    assert destination.read_bytes() == b'other writer'
    assert not list(tmp_path.glob('.nodum-snapshot-*'))


def test_deadline_cleanup(source, tmp_path, monkeypatch):
    import app.maintenance as module
    ticks = iter([0, 2])
    monkeypatch.setattr(module, 'monotonic', lambda: next(ticks, 2))
    with pytest.raises(MaintenanceError, match='deadline'):
        copy_database(source, tmp_path / 'timeout.db', timeout=1)
    assert not (tmp_path / 'timeout.db').exists()
    assert not list(tmp_path.glob('.nodum-snapshot-*'))


def test_cli_failure_redacts_paths_and_does_not_create_missing_source(tmp_path, capsys):
    private = tmp_path / 'private-sensitive-filename.db'
    assert main(['backup', '--source', str(private), '--destination', str(tmp_path / 'out.db')]) == 2
    output = capsys.readouterr().out
    assert 'private-sensitive' not in output and json.loads(output)['status'] == 'failed'
    assert not private.exists()


def test_cli_verify_is_read_only(source, capsys):
    before = source.read_bytes()
    assert main(['verify', '--source', str(source)]) == 0
    assert json.loads(capsys.readouterr().out)['schema_version'] == 8
    assert source.read_bytes() == before


@pytest.mark.parametrize('version', [1000000000, 'invalid'])
def test_untrusted_schema_versions_are_bounded_and_redacted(tmp_path, version, capsys):
    source = tmp_path / 'untrusted.db'
    with closing(sqlite3.connect(source)) as conn:
        conn.execute('CREATE TABLE schema_migrations (version)')
        conn.execute('INSERT INTO schema_migrations VALUES (?)', (version,))
        conn.commit()
    assert main(['verify', '--source', str(source)]) == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'failed'
