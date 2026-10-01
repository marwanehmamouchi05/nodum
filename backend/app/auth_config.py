"""Canonical origins are configured, never inferred from an untrusted Host."""
from dataclasses import dataclass
import os
from urllib.parse import urlsplit
from app.config import ConfigurationError, integer


@dataclass(frozen=True)
class AuthSettings:
    public_origin: str
    trusted_origins: tuple[str, ...] = ()
    secure: bool = False
    session_hours: int = 8

    @property
    def cookie_name(self):
        return "__Host-nodum_session" if self.secure else "nodum_session"

    @classmethod
    def from_env(cls):
        production = os.getenv("APP_ENV", "development") == "production"
        origin = os.getenv("AUTH_PUBLIC_ORIGIN", "" if production else "http://127.0.0.1:8000")
        origins = tuple(filter(None, (v.strip() for v in os.getenv("AUTH_TRUSTED_ORIGINS", "").split(","))))
        for value in (origin, *origins):
            parsed = urlsplit(value)
            if (not parsed.hostname or parsed.scheme not in ({"https"} if production else {"http", "https"})
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
                raise ConfigurationError("Set AUTH_PUBLIC_ORIGIN and AUTH_TRUSTED_ORIGINS to explicit origins (HTTPS in production, no trailing slash)")
        return cls(origin, origins, production or origin.startswith("https:"),
                   integer("AUTH_SESSION_HOURS", 8, 1, 24))
