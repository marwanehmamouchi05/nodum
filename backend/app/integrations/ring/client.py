"""Documented server-to-server operations. Never follow remote resource links."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.services.errors import DomainError


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RingRemoteError(DomainError):
    def __init__(self, remote_status=None):
        super().__init__(503, "Ring is unavailable or rejected the request; retry or relink")
        self.remote_status = remote_status


class RingClient:
    def __init__(self, settings):
        self.settings = settings
        self.transport = build_opener(NoRedirect())

    def _request(self, method, url, *, token=None, form=None, payload=None):
        headers = {"Accept": "application/json"}
        body = None
        if token:
            headers["Authorization"] = "Bearer " + token
        if form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urlencode(form).encode()
        elif payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        try:
            with self.transport.open(Request(url, data=body, headers=headers, method=method),
                                     timeout=3) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise RingRemoteError()
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise RingRemoteError()
                return result
        except HTTPError as exc:
            # Do not expose/log remote bodies, URLs, codes or tokens.
            raise RingRemoteError(exc.code) from None
        except (URLError, OSError, ValueError):
            raise RingRemoteError() from None

    def exchange(self, *, code=None, refresh_token=None):
        if not self.settings.client_id or not self.settings.client_secret:
            raise DomainError(503, "Ring OAuth credentials are not configured")
        form = {"client_id": self.settings.client_id, "client_secret": self.settings.client_secret}
        if code:
            form.update(grant_type="authorization_code", code=code)
        elif refresh_token:
            form.update(grant_type="refresh_token", refresh_token=refresh_token)
        else:
            raise DomainError(422, "A Ring authorization code or refresh token is required")
        return self._request("POST", self.settings.oauth_token_url, form=form)

    def api(self, method, path, token, payload=None):
        # Paths below are internal constants, never webhook URLs.
        return self._request(method, self.settings.api_base_url.rstrip("/") + path,
                             token=token, payload=payload)

    def profile(self, token):
        return self.api("GET", "/v1/users/me", token)

    def discover(self, token):
        return self.api("GET", "/v1/devices?include=status,capabilities,location,configurations", token)

    def confirm(self, token, identifier, nonce):
        return self.api("POST", "/v1/accounts/me/app-integrations", token,
                        {"account_identifier": identifier, "nonce": nonce})

    def complete(self, token, identifier):
        return self.api("PATCH", "/v1/accounts/me/app-integrations", token,
                        {"account_identifier": identifier, "status": "completed"})
