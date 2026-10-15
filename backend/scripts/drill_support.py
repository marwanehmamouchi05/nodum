"""Shared isolation helpers for disposable engineering drills, never deployment."""
import os


def isolated_environment():
    """Keep only OS necessities, excluding inherited provider/server/pip settings."""
    allowed = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'LOCALAPPDATA',
               'APPDATA', 'USERPROFILE', 'HOME', 'COMSPEC', 'LANG', 'LC_ALL'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(APP_ENV='production', NODUM_AUTHORIZATION_MODE='scoped',
               NODUM_AI_ENABLED='false', HOST='127.0.0.1', ACCESS_LOG='false',
               RING_MODE='simulation', RING_REQUIRED='false', FORWARDED_ALLOW_IPS='',
               PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1')
    return env
