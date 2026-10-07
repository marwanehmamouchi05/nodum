"""Provision a first Owner + Admin into an explicitly selected EMPTY scoped DB.

Run from backend: .venv/Scripts/python.exe provision_admin.py --name NAME --username LOGIN
DATABASE_URL and NODUM_AUTHORIZATION_MODE=scoped must be explicitly configured.
Password is collected privately; it is never an argument or printed.
"""
import argparse
import os
from getpass import getpass
from datetime import datetime, timezone
from app.database import database_path, BACKEND_DIRECTORY
from app.sqlite_repository import SQLiteRepository
from app.services.admin_provisioning import provision_first_admin
from app.services.errors import DomainError


def main():
    parser = argparse.ArgumentParser(description="Provision an empty scoped Nodum installation")
    parser.add_argument("--name", required=True)
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    if os.getenv("NODUM_AUTHORIZATION_MODE") != "scoped" or not os.getenv("DATABASE_URL"):
        parser.error("Explicit DATABASE_URL and NODUM_AUTHORIZATION_MODE=scoped are required")
    if database_path().resolve() == (BACKEND_DIRECTORY / "nodum.db").resolve():
        parser.error("The audited default runtime database cannot be used")
    password = getpass("Initial password (12–128 characters): ")
    if password != getpass("Confirm initial password: "):
        parser.error("Passwords do not match")
    repo = SQLiteRepository(os.environ["DATABASE_URL"])
    # Verify the target is empty before applying migrations to an existing file.
    path = database_path().resolve()
    if path.exists() and path.stat().st_size:
        parser.error("Choose a new, empty database file for first-install provisioning")
    repo.initialize(seed_demo=False)
    try:
        provision_first_admin(repo, args.name, args.username, password, datetime.now(timezone.utc))
    except DomainError as error:
        parser.error(error.detail)
    print("Owner and Admin provisioned. Sign in to configure your organization and building.")


if __name__ == "__main__":
    main()
