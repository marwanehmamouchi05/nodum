import json
import sqlite3
from contextlib import closing

import pytest

from app.preflight import main, report
from app.sqlite_repository import SQLiteRepository
from demo_product import seed_demo
from conftest import NOW


@pytest.fixture
def installation(tmp_path, monkeypatch):
    import os
    for key in list(os.environ):
        if key.startswith(('RING_', 'AUTH_', 'CORS_', 'NODUM_', 'AWS_')) or key in {'DATABASE_URL','APP_ENV'}:
            monkeypatch.delenv(key)
    path = tmp_path / 'pilot.db'
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(path))
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('NODUM_AUTHORIZATION_MODE', 'scoped')
    monkeypatch.setenv('AUTH_PUBLIC_ORIGIN', 'https://nodum.example')
    monkeypatch.setenv('NODUM_AI_ENABLED', 'false')
    repo = SQLiteRepository('sqlite:///' + str(path))
    repo.initialize(seed_demo=False)
    seed_demo(repo, NOW)
    return path


def test_read_only_prerequisites_are_not_hardware_readiness(installation):
    before = installation.read_bytes()
    result = report()
    assert result['status'] == 'PASS'
    assert 'Live provider connectivity and hardware' in result['unverified']
    assert installation.read_bytes() == before


@pytest.mark.parametrize('key,value,failed', [
    ('APP_ENV','development','production_mode'),
    ('NODUM_AUTHORIZATION_MODE','legacy_demo','scoped_authorization'),
    ('CORS_ALLOWED_ORIGINS','https://frontend.example','browser_sessions'),
    ('AUTH_BOOTSTRAP_PASSWORD','synthetic-do-not-print-secret','bootstrap_removed'),
    ('NODUM_AI_ENABLED','true','ai_budget'),
    ('AUTH_PUBLIC_ORIGIN','http://private-token.example','configuration'),
])
def test_unsafe_configuration_is_actionable_and_redacted(installation, monkeypatch, key, value, failed, capsys):
    monkeypatch.setenv(key, value)
    assert main([]) == 2
    result = json.loads(capsys.readouterr().out)
    assert any(c['check'] == failed and c['status'] == 'FAIL' for c in result['checks'])
    if key in {'AUTH_PUBLIC_ORIGIN', 'AUTH_BOOTSTRAP_PASSWORD'}:
        assert value not in json.dumps(result)


def test_cross_origin_browser_session_configuration(installation, monkeypatch):
    monkeypatch.setenv('CORS_ALLOWED_ORIGINS', 'https://frontend.example')
    monkeypatch.setenv('AUTH_TRUSTED_ORIGINS', 'https://frontend.example')
    monkeypatch.setenv('CORS_ALLOW_CREDENTIALS', 'true')
    assert report()['status'] == 'PASS'


def test_missing_database_not_created(installation, monkeypatch, tmp_path):
    missing = tmp_path / 'not-created.db'
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(missing))
    assert report()['status'] == 'FAIL'
    assert not missing.exists()


def test_no_seed_or_migration(installation):
    with closing(sqlite3.connect(installation)) as conn:
        conn.execute('DELETE FROM schema_migrations WHERE version=(SELECT MAX(version) FROM schema_migrations)')
        conn.commit()
        before = conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()
    assert report()['status'] == 'FAIL'
    with closing(sqlite3.connect(installation)) as conn:
        assert conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall() == before


def test_empty_installation_requires_onboarding(tmp_path, monkeypatch, installation):
    path = tmp_path / 'empty.db'
    SQLiteRepository('sqlite:///' + str(path)).initialize(seed_demo=False)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(path))
    assert any(c['check'] == 'onboarding_records' and c['status'] == 'FAIL' for c in report()['checks'])
