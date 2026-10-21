"""Judge hosting preserves existing data, scope and production authentication."""
import os

import pytest

from conftest import NOW
from app.config import AppSettings, ConfigurationError, validate_startup
from app.judge_demo import prepare_judge_demo
from app.sqlite_repository import SQLiteRepository
from app.services.auth import verify_password


@pytest.fixture
def judge(monkeypatch, tmp_path):
    for key, value in {
        "APP_ENV": "production", "AUTH_PUBLIC_ORIGIN": "https://nodum.example",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'synthetic-judge-demo.db'}",
        "NODUM_JUDGE_DEMO": "true", "NODUM_AUTHORIZATION_MODE": "scoped",
        "RING_MODE": "simulation", "RING_SIGNING_KEY": "synthetic-signing-key-for-tests",
        "NODUM_JUDGE_PASSWORD": "Private-synthetic-test-password-2026",
    }.items():
        monkeypatch.setenv(key, value)
    from cryptography.fernet import Fernet
    monkeypatch.setenv("RING_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return tmp_path


def test_judge_install_is_private_persistent_and_does_not_reset(judge):
    validate_startup(AppSettings.from_env())
    repo = SQLiteRepository(os.environ["DATABASE_URL"])
    repo.initialize(seed_demo=False)
    prepare_judge_demo(repo, NOW)
    users = repo.list_auth_users()
    assert users and all(verify_password(os.environ["NODUM_JUDGE_PASSWORD"], u.password_hash) for u in users)
    assert all(not verify_password("Synthetic-demo-only-2026", u.password_hash) for u in users)
    before = [(u.id, u.password_hash) for u in users]
    prepare_judge_demo(repo, NOW)
    assert [(u.id, u.password_hash) for u in repo.list_auth_users()] == before


@pytest.mark.parametrize("key,value", [
    ("NODUM_AUTHORIZATION_MODE", "legacy_demo"), ("RING_MODE", "live"),
    ("NODUM_JUDGE_PASSWORD", "Synthetic-demo-only-2026"),
    ("NODUM_JUDGE_PASSWORD", "short"), ("DATABASE_URL", "sqlite:////data/nodum.db"),
])
def test_judge_install_rejects_unsafe_configuration(judge, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError):
        validate_startup(AppSettings.from_env())


def test_judge_install_preserves_existing_non_demo_data(judge):
    repo = SQLiteRepository(os.environ["DATABASE_URL"])
    repo.initialize()  # legacy fixture is intentionally not an empty judge installation
    count = len(repo.list_people())
    # Existing people alone must also prevent seeding over a different installation.
    with pytest.raises(ConfigurationError):
        prepare_judge_demo(repo, NOW)
    assert len(repo.list_people()) == count
