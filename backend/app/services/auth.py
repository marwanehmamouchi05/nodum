"""Small password/session service. Building authorization remains in its services."""
from datetime import timedelta
import hashlib
import hmac
import os
import re
import secrets
from uuid import uuid4

from app.auth_config import AuthSettings
from app.config import ConfigurationError
from app.models.auth import AuthSession, AuthThrottle, NodumUser
from app.repository import Repository
from app.services.errors import DomainError


ITERATIONS = 600_000


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_token(cookie):
    return digest("nodum-csrf:" + cookie)


def hash_password(password):
    if not 12 <= len(password) <= 128:
        raise DomainError(400, "Password must contain 12 to 128 characters")
    salt = secrets.token_hex(32)
    result = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return "$".join(("pbkdf2_sha256", str(ITERATIONS), salt, result.hex()))


def verify_password(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or rounds != str(ITERATIONS):
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


# Equal-cost verification for unknown users, without a usable default password.
DUMMY_HASH = "pbkdf2_sha256$600000$" + "00" * 32 + "$" + "00" * 32


class AuthService:
    def __init__(self, repository: Repository, settings: AuthSettings):
        self.repository = repository
        self.settings = settings

    def create_user(self, username, password, person_id, now):
        username = username.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9@._+-]{2,127}", username):
            raise DomainError(400, "Username must contain 3 to 128 letters, digits or email characters")
        encoded = hash_password(password)
        with self.repository.transaction():
            if not self.repository.get_person(person_id):
                raise DomainError(400, "User must reference an existing Nodum person")
            if any(u.username == username or u.person_id == person_id for u in self.repository.list_auth_users()):
                raise DomainError(409, "Username or person already has a Nodum user")
            user = NodumUser(id=str(uuid4()), username=username, person_id=person_id,
                             password_hash=encoded, created_at=now)
            self.repository.save_auth_user(user)
        return user

    def session(self, cookie, now):
        if not cookie or not re.fullmatch(r"[A-Za-z0-9_-]{43}", cookie):
            return None
        session = self.repository.get_auth_session(digest(cookie))
        if not session or not session.created_at <= now < session.expires_at:
            return None
        return session

    def user(self, cookie, now):
        session = self.session(cookie, now)
        user = self.repository.get_auth_user(session.user_id) if session and session.user_id else None
        if not user or not user.active or not self.repository.get_person(user.person_id):
            return None
        return user

    def issue(self, now, user_id=None, old_cookie=None):
        cookie = secrets.token_urlsafe(32)
        lifetime = timedelta(hours=self.settings.session_hours) if user_id else timedelta(minutes=15)
        with self.repository.transaction():
            if old_cookie:
                self.repository.delete_auth_session(digest(old_cookie))
            for session in self.repository.list_auth_sessions():
                if session.expires_at <= now:
                    self.repository.delete_auth_session(session.id)
            self.repository.save_auth_session(AuthSession(id=digest(cookie), user_id=user_id,
                                                          created_at=now, expires_at=now + lifetime))
        return cookie, int(lifetime.total_seconds())

    def check_csrf(self, cookie, token, origin, now):
        if (not self.session(cookie, now)
                or origin not in (self.settings.public_origin, *self.settings.trusted_origins)
                or not hmac.compare_digest(csrf_token(cookie).encode(), (token or "").encode())):
            raise DomainError(403, "Invalid session or CSRF protection; reload and try again")

    def login(self, username, password, cookie, now, client_ip):
        username = username.strip().lower()
        # Reserve attempts before hashing, including nonexistent users. Persisted
        # account/IP buckets bound brute force and expensive password verification.
        with self.repository.transaction():
            for record in self.repository.list_auth_throttles():
                if record.expires_at <= now:
                    self.repository.delete_auth_throttle(record.id)
            buckets = [(digest("user:" + username), 5), (digest("ip:" + client_ip), 30)]
            records = []
            for key, maximum in buckets:
                record = self.repository.get_auth_throttle(key) or AuthThrottle(
                    id=key, attempts=0, expires_at=now + timedelta(minutes=15))
                if record.attempts >= maximum:
                    raise DomainError(429, "Too many sign-in attempts; try again in 15 minutes")
                records.append(record)
            for record in records:
                record.attempts += 1
                self.repository.save_auth_throttle(record)
        user = next((u for u in self.repository.list_auth_users() if u.username == username), None)
        valid = verify_password(password, user.password_hash if user else DUMMY_HASH)
        if not valid or not user or not user.active or not self.repository.get_person(user.person_id):
            raise DomainError(401, "Invalid username or password")
        with self.repository.transaction():
            if not self.session(cookie, now):
                raise DomainError(403, "Session expired; reload and try again")
            fresh, age = self.issue(now, user.id, cookie)
            self.repository.delete_auth_throttle(digest("user:" + username))
        return user, fresh, age

    def logout(self, cookie):
        self.repository.delete_auth_session(digest(cookie))


def bootstrap_user(repository, now):
    values = [os.getenv("AUTH_BOOTSTRAP_" + key, "") for key in ("USERNAME", "PASSWORD", "PERSON_ID")]
    if not any(values):
        return
    if not all(values):
        raise ConfigurationError("Set all AUTH_BOOTSTRAP_USERNAME, AUTH_BOOTSTRAP_PASSWORD and AUTH_BOOTSTRAP_PERSON_ID")
    settings = AuthSettings.from_env()
    username, password, person_id = values
    with repository.transaction():
        existing = next((u for u in repository.list_auth_users() if u.username == username.strip().lower()), None)
        if existing:
            if existing.person_id != person_id:
                raise ConfigurationError("AUTH_BOOTSTRAP_PERSON_ID conflicts with persisted user")
            return
        try:
            AuthService(repository, settings).create_user(username, password, person_id, now)
        except DomainError:
            raise ConfigurationError("Cannot bootstrap Nodum user; check AUTH_BOOTSTRAP values and existing person") from None
