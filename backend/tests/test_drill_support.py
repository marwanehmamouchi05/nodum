from scripts.drill_support import isolated_environment


def test_drills_do_not_inherit_live_configuration(monkeypatch):
    for key in ['AWS_PROFILE','RING_SIGNING_KEY','DATABASE_URL','AUTH_PUBLIC_ORIGIN','PIP_INDEX_URL',
                'HTTP_PROXY','HTTPS_PROXY','PYTHONPATH','SSL_CERT_FILE','FORWARDED_ALLOW_IPS']:
        monkeypatch.setenv(key, 'sensitive-test-value')
    env = isolated_environment()
    assert 'sensitive-test-value' not in env.values()
    assert env['NODUM_AI_ENABLED'] == 'false'
    assert env['RING_MODE'] == 'simulation'
    assert env['FORWARDED_ALLOW_IPS'] == ''
