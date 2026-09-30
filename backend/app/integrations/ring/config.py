import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from app.services.errors import DomainError


@dataclass(frozen=True)
class RingSettings:
    environment: str = "staging"
    client_id: str = ""
    client_secret: str = field(default="", repr=False)
    signing_key: str = field(default="", repr=False)
    encryption_key: str = field(default="", repr=False)
    api_base_url: str = "https://api.amazonvision.com"
    oauth_token_url: str = "https://oauth.ring.com/oauth/token"
    account_link_url: str = ""
    token_exchange_url: str = ""
    webhook_url: str = ""
    homepage_url: str = ""

    @classmethod
    def from_env(cls):
        values = {name: os.getenv("RING_" + name.upper(), default)
                  for name, default in (
                      ("environment", "staging"), ("client_id", ""), ("client_secret", ""),
                      ("signing_key", os.getenv("RING_WEBHOOK_SECRET", "")),
                      ("encryption_key", ""), ("api_base_url", "https://api.amazonvision.com"),
                      ("oauth_token_url", "https://oauth.ring.com/oauth/token"),
                      ("account_link_url", ""), ("token_exchange_url", ""),
                      ("webhook_url", ""), ("homepage_url", ""))}
        settings = cls(**values)
        if settings.environment not in {"staging", "production"}:
            raise DomainError(503, "Invalid Ring environment configuration")
        for url in (settings.api_base_url, settings.oauth_token_url,
                    settings.account_link_url, settings.token_exchange_url,
                    settings.webhook_url, settings.homepage_url):
            if url:
                parts = urlsplit(url)
                if (parts.scheme != "https" or not parts.hostname or parts.username
                        or parts.password or parts.query or parts.fragment):
                    raise DomainError(503, "Ring URLs must be HTTPS without credentials, query or fragment")
        return settings
