"""Malformed auth configuration fails closed and never echoes its value."""
import pytest

from app.auth_config import AuthSettings
from app.config import ConfigurationError


@pytest.mark.parametrize('variable', ['AUTH_PUBLIC_ORIGIN', 'AUTH_TRUSTED_ORIGINS'])
@pytest.mark.parametrize('origin', [
    'https://*.example', 'https://private.example:secret', 'https://private.example:65536',
    'https://private.example:0', 'https://private.example:', 'https://private.example:-1',
    'https://private.example\n', 'https://private .example', 'https://[broken',
    'https://privaté.example', 'https://private.example\\other', 'https://private%2eexample',
    'https://private.example?', 'https://private.example#',
])
def test_invalid_origin_rejected_without_value(monkeypatch, variable, origin):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('AUTH_PUBLIC_ORIGIN', 'https://valid.example')
    monkeypatch.delenv('AUTH_TRUSTED_ORIGINS', raising=False)
    monkeypatch.setenv(variable, origin)
    # Trusted-origin entries intentionally trim outer whitespace, as before.
    if variable == 'AUTH_TRUSTED_ORIGINS' and origin.endswith('\n'):
        assert AuthSettings.from_env().trusted_origins == (origin.strip(),)
        return
    with pytest.raises(ConfigurationError) as caught:
        AuthSettings.from_env()
    assert 'private' not in str(caught.value)


@pytest.mark.parametrize('origin', ['https://nodum.example','https://nodum.example:443','https://127.0.0.1:8443','https://[::1]:8443'])
def test_valid_explicit_origins_unchanged(monkeypatch, origin):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('AUTH_PUBLIC_ORIGIN', origin)
    monkeypatch.delenv('AUTH_TRUSTED_ORIGINS', raising=False)
    assert AuthSettings.from_env().public_origin == origin
