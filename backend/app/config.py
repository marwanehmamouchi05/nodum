"""Deployment settings. Errors name variables, never their secret values."""
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import os
from pathlib import Path
from urllib.parse import urlsplit


class ConfigurationError(RuntimeError):
    pass


def boolean(name, default=False):
    value = os.getenv(name, str(default)).lower()
    if value not in {"true", "false"}:
        raise ConfigurationError(f"{name} must be true or false")
    return value == "true"


def integer(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
        if not minimum <= value <= maximum:
            raise ValueError()
        return value
    except ValueError:
        raise ConfigurationError(f"{name} must be an integer from {minimum} to {maximum}") from None


@dataclass(frozen=True)
class AppSettings:
    environment: str
    host: str
    port: int
    log_level: str
    access_log: bool
    cors_origins: tuple[str, ...]
    cors_credentials: bool
    forwarded_allow_ips: str
    graceful_shutdown_seconds: int
    ring_required: bool

    @classmethod
    def from_env(cls):
        environment = os.getenv("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ConfigurationError("APP_ENV must be development or production")
        host = os.getenv("HOST", "127.0.0.1")
        try:
            ip_address(host)
        except ValueError:
            raise ConfigurationError("HOST must be an IPv4 or IPv6 bind address") from None
        log_level = os.getenv("LOG_LEVEL", "info").lower()
        if log_level not in {"critical", "error", "warning", "info", "debug", "trace"}:
            raise ConfigurationError("LOG_LEVEL is not a supported Uvicorn log level")
        origins = tuple(dict.fromkeys(v.strip() for v in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if v.strip()))
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                _ = parsed.port
                if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                        or parsed.path or parsed.query or parsed.fragment or parsed.username
                        or parsed.password or "*" in origin or not origin.isascii()
                        or any(c.isspace() for c in origin)
                        or (environment == "production" and parsed.scheme != "https")):
                    raise ValueError()
            except ValueError:
                raise ConfigurationError(
                    "CORS_ALLOWED_ORIGINS must contain explicit origins without paths or wildcards; "
                    "production origins must use HTTPS") from None
        proxy_ips = os.getenv("FORWARDED_ALLOW_IPS", "").strip()
        if proxy_ips:
            try:
                for value in proxy_ips.split(","):
                    ip_network(value.strip(), strict=False)
            except ValueError:
                raise ConfigurationError("FORWARDED_ALLOW_IPS must contain trusted proxy IPs/CIDRs, never '*'") from None
        return cls(environment=environment, host=host, port=integer("PORT", 8000, 1, 65535),
                   log_level=log_level, access_log=boolean("ACCESS_LOG", environment != "production"),
                   cors_origins=origins, cors_credentials=boolean("CORS_ALLOW_CREDENTIALS"),
                   forwarded_allow_ips=proxy_ips,
                   graceful_shutdown_seconds=integer("GRACEFUL_SHUTDOWN_SECONDS", 30, 1, 300),
                   ring_required=boolean("RING_REQUIRED"))


def validate_startup(settings):
    """No network/credential-chain lookups; optional integrations stay optional."""
    from app.database import database_path

    url = os.getenv("DATABASE_URL", "")
    if settings.environment == "production":
        if not url.startswith("sqlite:///") or not Path(url[len("sqlite:///"):]).is_absolute():
            raise ConfigurationError("Production DATABASE_URL must name an absolute SQLite path on persistent storage")
    try:
        database_path()
    except (ValueError, OSError):
        raise ConfigurationError("DATABASE_URL must name a file-backed sqlite:/// database without URL options") from None
    if settings.ring_required:
        from cryptography.fernet import Fernet
        from app.integrations.ring.config import RingSettings
        from app.services.errors import DomainError

        required = ("RING_CLIENT_ID", "RING_CLIENT_SECRET", "RING_ENCRYPTION_KEY",
                    "RING_ENVIRONMENT", "RING_API_BASE_URL", "RING_OAUTH_TOKEN_URL",
                    "RING_ACCOUNT_LINK_URL", "RING_TOKEN_EXCHANGE_URL", "RING_WEBHOOK_URL", "RING_HOMEPAGE_URL")
        missing = [name for name in required if not os.getenv(name, "").strip()]
        if not (os.getenv("RING_SIGNING_KEY") or os.getenv("RING_WEBHOOK_SECRET", "")).strip():
            missing.append("RING_SIGNING_KEY")
        if missing:
            raise ConfigurationError("RING_REQUIRED=true but configuration is missing: " + ", ".join(missing))
        try:
            ring = RingSettings.from_env()
            Fernet(ring.encryption_key.encode())
        except (DomainError, ValueError, TypeError):
            raise ConfigurationError("Invalid Ring configuration: check HTTPS URLs, RING_ENVIRONMENT and RING_ENCRYPTION_KEY") from None
