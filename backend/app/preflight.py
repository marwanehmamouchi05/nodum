"""Read-only pilot checks. Never starts services, migrates, seeds or calls providers."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from app.auth_config import AuthSettings
from app.config import AppSettings, boolean, validate_startup
from app.database import database_path, MIGRATIONS
from app.maintenance import inspect_database
from app.services.authorization import authorization_mode


def report():
    checks = []
    def add(name, ok, message):
        checks.append({'check': name, 'status': 'PASS' if ok else 'FAIL', 'message': message})
    try:
        settings = AppSettings.from_env()
        validate_startup(settings)
        auth = AuthSettings.from_env()
        add('configuration', True, 'Application and authentication settings validated locally.')
        add('production_mode', settings.environment == 'production', 'A hosted pilot requires production mode.')
        add('scoped_authorization', authorization_mode() == 'scoped', 'Pilot use requires explicit scoped authorization.')
        browser_origins = set(settings.cors_origins) - {auth.public_origin}
        add('browser_sessions', not browser_origins or (
            settings.cors_credentials and browser_origins <= set(auth.trusted_origins)),
            'Separate frontend origins require credentialed CORS and matching trusted auth origins.')
        add('bootstrap_removed', not any(os.getenv(key) for key in (
            'AUTH_BOOTSTRAP_USERNAME', 'AUTH_BOOTSTRAP_PASSWORD', 'AUTH_BOOTSTRAP_PERSON_ID')),
            'Remove bootstrap credentials after explicit first-install provisioning.')
        add('ai_budget', not boolean('NODUM_AI_ENABLED', True),
            'Automated pilot checks require AI disabled; enabling it needs a separate provider/cost validation.')
    except (ValueError, RuntimeError, TypeError):
        # Even parsing errors can embed an origin or secret; emit fixed text only.
        add('configuration', False, 'Invalid application/auth configuration. Review named variables in the pilot template.')
    try:
        if not os.getenv('DATABASE_URL'):
            raise ValueError('Explicit database required')
        path = database_path()
        verified = inspect_database(path)
        add('database', verified['schema_version'] == MIGRATIONS[-1][0],
            'Database must exist, pass structural checks and match the current schema; preflight never migrates it.')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)) as conn:
            users = conn.execute('SELECT COUNT(*) FROM auth_users').fetchone()[0]
            assignments = conn.execute('SELECT COUNT(*) FROM application_role_assignments').fetchone()[0]
            buildings = conn.execute("SELECT COUNT(*) FROM product_structure WHERE json_extract(data, '$.kind')='building'").fetchone()[0]
        add('onboarding_records', bool(users and assignments and buildings),
            'User, role and building records must exist. This does not prove effective permissions or commissioning.')
    except (ValueError, OSError, RuntimeError, sqlite3.Error):
        add('database', False, 'Database unavailable, invalid or incompatible. Provision or recover separately; no data was changed.')
    return {'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
            'scope': 'local software prerequisites only', 'checks': checks,
            'unverified': ['TLS/proxy and browser session deployment', 'Backup storage and completed recovery drill',
                           'Live provider connectivity and hardware', 'Building safety and emergency egress',
                           'Full tenant isolation and user workflow acceptance']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', help='Optional explicit local configuration; exported variables win')
    args = parser.parse_args(argv)
    if args.env_file:
        from dotenv import load_dotenv
        if not Path(args.env_file).is_file():
            print(json.dumps({'status': 'FAIL', 'message': 'Requested configuration file does not exist.'}))
            return 2
        load_dotenv(args.env_file, override=False)
    result = report()
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
