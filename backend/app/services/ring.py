"""Ring orchestration: encrypted tokens, durable inbox, explicit emergency bridge.

The access engine is unchanged. Device names, payload zone IDs and Ring user
profile fields never confer Nodum identity or authority.
"""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json

from cryptography.fernet import Fernet, InvalidToken
from pydantic import TypeAdapter, ValidationError

from app.integrations.ring.client import RingClient, RingRemoteError
from app.models.access import UTCTimestamp
from app.models.emergency import EmergencyCreateInput
from app.models.ring import RingAccount, RingDevice, RingEvent, RingTokens
from app.repository import Repository
from app.integrations.ring.config import RingSettings
from app.services.emergencies import create_emergency, validate_operator
from app.services.errors import DomainError


SIGNALS = {
    "motion_detected": "motion", "button_press": "doorbell",
    "contact_sensor_faulted": "contact_open", "contact_sensor_cleared": "contact_closed",
    "flood_detected": "water_detected", "flood_cleared": "water_cleared",
    "freeze_detected": "freeze_detected", "freeze_cleared": "freeze_cleared",
    "tamper_detected": "tamper_detected", "tamper_cleared": "tamper_cleared",
    **{key: key for key in ("device_added", "device_removed", "device_online", "device_offline",
                           "app_integration_added", "app_integration_removed")},
}


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, separators=(",", ":")).encode()).hexdigest()


def nonce_for(key, time_ms, account_id):
    digest = hmac.new(key.encode(), f"{time_ms}:{account_id}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def verify_signature(key, raw, signature):
    if not key:
        raise DomainError(503, "Ring signing key is not configured")
    expected = "sha256=" + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected.encode(), (signature or "").encode()):
        raise DomainError(401, "Invalid Ring signature")


def normalize_event(raw, environment, now):
    try:
        payload = json.loads(raw)
        meta, data = payload["meta"], payload["data"]
        attrs = data["attributes"]
        if meta["version"] != "1.1":
            raise ValueError()
        TypeAdapter(UTCTimestamp).validate_python(meta["time"])
        timestamp = attrs["timestamp"]
        if type(timestamp) is not int or timestamp < 0:
            raise ValueError()
        kind = data["type"]
        source_type = attrs["source_type"]
        if kind in SIGNALS:
            expected_source = "users" if kind.startswith("app_integration_") else "devices"
            if source_type != expected_source:
                raise ValueError()
            if expected_source == "users" and attrs["source"] != meta["account_id"]:
                raise ValueError()
        return RingEvent(
            id=identity(environment, meta["account_id"], data["id"]),
            environment=environment, account_id=meta["account_id"], request_id=meta["request_id"],
            event_id=data["id"], event_type=kind, source=attrs["source"], source_type=source_type,
            occurred_at=datetime.fromtimestamp(timestamp / 1000, timezone.utc), received_at=now,
            signal=SIGNALS.get(kind, "unknown"), raw_payload=raw.decode("utf-8"),
        )
    except (ValueError, TypeError, KeyError, OverflowError, OSError):
        raise DomainError(400, "Malformed Ring v1.1 event") from None


def normalize_devices(payload):
    try:
        included = {(item["type"], item["id"]): item["attributes"]
                    for item in payload.get("included", [])}
        if not isinstance(payload["data"], list):
            raise ValueError()
        devices = []
        for item in payload["data"]:
            if item["type"] != "devices":
                raise ValueError()
            related = {}
            for name in ("status", "capabilities", "location", "configurations"):
                ref = item.get("relationships", {}).get(name, {}).get("data")
                if ref:
                    value = included.get((ref["type"], ref["id"]))
                    if value is not None:
                        related[name] = value
            devices.append(RingDevice(id=item["id"], name=item["attributes"].get("name", ""),
                                      attributes=item["attributes"], related=related))
        return devices
    except (ValueError, TypeError, KeyError, AttributeError):
        raise RingRemoteError() from None


class RingService:
    def __init__(self, repository: Repository, settings: RingSettings, client=None):
        self.repository = repository
        self.settings = settings
        self.client = client or RingClient(settings)

    def cipher(self):
        try:
            return Fernet(self.settings.encryption_key.encode())
        except (ValueError, TypeError):
            raise DomainError(503, "Ring token encryption key is missing or invalid") from None

    def account_key(self, account_id):
        return identity(self.settings.environment, account_id)

    def _token_record(self, response, account_id, now, previous=None):
        try:
            tokens = RingTokens.model_validate(response)
            access = tokens.access_token.get_secret_value()
            refresh = tokens.refresh_token.get_secret_value()
            if not access or not refresh:
                raise ValueError()
        except (ValidationError, ValueError):
            raise RingRemoteError() from None
        encrypted = self.cipher().encrypt(json.dumps({
            "access_token": access, "refresh_token": refresh,
        }).encode()).decode()
        fields = dict(id=self.account_key(account_id), environment=self.settings.environment,
                      account_id=account_id, encrypted_tokens=encrypted,
                      expires_at=now + timedelta(seconds=tokens.expires_in), received_at=now)
        if previous:
            fields.update(owner_id=previous.owner_id, status=previous.status,
                          received_at=previous.received_at, link_verified=previous.link_verified)
        return RingAccount(**fields)

    def secrets(self, account):
        try:
            return json.loads(self.cipher().decrypt(account.encrypted_tokens.encode()))
        except (InvalidToken, ValueError):
            raise DomainError(503, "Ring tokens cannot be decrypted; restore key or relink") from None

    def receive_code(self, code, now):
        """Called by a verified inbound transport adapter, not a browser account ID."""
        self.cipher()  # Fail before spending the one-use code if storage is unconfigured.
        response = self.client.exchange(code=code)
        try:
            tokens = RingTokens.model_validate(response)
            profile = self.client.profile(tokens.access_token.get_secret_value())["data"]
            if profile["type"] != "users" or not profile["id"]:
                raise ValueError()
            record = self._token_record(response, profile["id"], now)
        except (ValueError, KeyError, TypeError):
            raise RingRemoteError() from None
        with self.repository.transaction():
            old = self.repository.get_ring_account(record.id)
            if old and old.status not in {"unclaimed", "removed"}:
                raise DomainError(409, "Ring account is already claimed")
            self.repository.save_ring_account(record)
        return {"status": "unclaimed"}

    def claim(self, payload, principal, now):
        validate_operator(self.repository, principal.person_id)
        if not self.settings.signing_key:
            raise DomainError(503, "Ring signing key is not configured")
        age = int(now.timestamp() * 1000) - payload.time
        if not 0 <= age <= 600_000:
            raise DomainError(400, "Ring link timestamp is expired or in the future")
        with self.repository.transaction():
            matches = [a for a in self.repository.list_ring_accounts()
                       if a.environment == self.settings.environment
                       and (a.status == "unclaimed" or
                            (a.status == "awaiting" and a.owner_id == principal.person_id))
                       and hmac.compare_digest(payload.nonce,
                                               nonce_for(self.settings.signing_key, payload.time, a.account_id))]
            if len(matches) != 1:
                raise DomainError(409, "No unclaimed Ring account matches this nonce")
            account = matches[0]
            if account.expires_at <= now:
                raise DomainError(409, "Ring account link expired; reconnect")
            account.owner_id = principal.person_id
            account.status = "awaiting"
            self.repository.save_ring_account(account)
        token = self.secrets(account)["access_token"]
        # Reservation is durable before remote calls. Failure never makes tokens
        # claimable by another user. Same-owner retries can finish a failed PATCH.
        if not account.link_verified:
            result = self.client.confirm(token, principal.masked_account_identifier, payload.nonce)
            self._check_link_response(result, "awaiting")
            with self.repository.transaction():
                current = self.repository.get_ring_account(account.id)
                if current.status != "awaiting" or current.owner_id != principal.person_id:
                    raise DomainError(409, "Ring account changed during linking")
                current.link_verified = True
                self.repository.save_ring_account(current)
        result = self.client.complete(token, principal.masked_account_identifier)
        self._check_link_response(result, "completed")
        with self.repository.transaction():
            current = self.repository.get_ring_account(account.id)
            if current.status != "awaiting" or current.owner_id != principal.person_id:
                raise DomainError(409, "Ring account changed during linking")
            current.status = "completed"
            self.repository.save_ring_account(current)
        return {"account_id": account.account_id, "status": "completed"}

    @staticmethod
    def _check_link_response(result, expected):
        try:
            if (result["data"]["type"] != "app-integrations"
                    or result["data"]["attributes"]["status"] != expected):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise RingRemoteError() from None

    def authorized_account(self, account_id, principal):
        account = self.repository.get_ring_account(self.account_key(account_id))
        if (account is None or account.status != "completed"
                or account.owner_id != principal.person_id):
            raise DomainError(403, "Ring account is not linked to this operator")
        validate_operator(self.repository, principal.person_id)
        return account

    def access_token(self, account_id, principal, now, force=False):
        # Serialize refresh across workers. Bound network timeout limits lock time.
        # Commit rotated credentials before subsequent discovery can fail.
        with self.repository.transaction():
            account = self.authorized_account(account_id, principal)
            secrets = self.secrets(account)
            if force or account.expires_at <= now + timedelta(seconds=60):
                response = self.client.exchange(refresh_token=secrets["refresh_token"])
                account = self._token_record(response, account_id, now, previous=account)
                self.repository.save_ring_account(account)
                secrets = self.secrets(account)
            return secrets["access_token"]

    def discover(self, account_id, principal, now):
        token = self.access_token(account_id, principal, now)
        try:
            payload = self.client.discover(token)
        except RingRemoteError as exc:
            if exc.remote_status != 401:
                raise
            token = self.access_token(account_id, principal, now, force=True)
            payload = self.client.discover(token)
        return normalize_devices(payload)

    def list_events(self, account_id, principal):
        self.authorized_account(account_id, principal)
        return [event for event in self.repository.list_ring_events()
                if event.account_id == account_id and event.environment == self.settings.environment]

    def receive_event(self, raw, signature, now):
        verify_signature(self.settings.signing_key, raw, signature)
        event = normalize_event(raw, self.settings.environment, now)
        with self.repository.ring_receipt_transaction():
            old = self.repository.find_ring_event(event.environment, event.account_id,
                                                  event.request_id, event.event_id)
            if old:
                if (old.event_id != event.event_id or old.event_type != event.event_type
                        or old.source != event.source or old.occurred_at != event.occurred_at):
                    raise DomainError(409, "Conflicting Ring event identity")
                return {"status": "duplicate", "id": old.id}
            # Preserve even unknown/unclaimed account events for audit; they cannot
            # create an emergency until the account is linked and an operator acts.
            self.repository.save_ring_event(event)
            if event.event_type == "app_integration_removed":
                account = self.repository.get_ring_account(self.account_key(event.account_id))
                if account:
                    account.status = "removed"
                    account.encrypted_tokens = ""
                    self.repository.save_ring_account(account)
        return {"status": "received", "id": event.id}

    def process_event(self, event_key, principal, zone_id, now):
        """Explicit authenticated operator review supplies the trusted zone mapping.

        Flood -> existing water_leak service. Freeze has no matching domain type;
        preserve for review. Cleared signals never resolve incidents automatically.
        No responders/work orders/permissions are created by this bridge.
        """
        with self.repository.transaction():
            event = self.repository.get_ring_event(event_key)
            if event is None or event.environment != self.settings.environment:
                raise DomainError(404, "Ring event not found")
            self.authorized_account(event.account_id, principal)
            if event.status in {"processed", "ignored"}:
                return event
            if event.signal == "water_detected":
                if event.occurred_at > now:
                    raise DomainError(422, "Ring event time is in the future; review required")
                if not zone_id:
                    raise DomainError(422, "An operator-confirmed zone is required")
                incident = create_emergency(self.repository, EmergencyCreateInput(
                    emergency_id="ring-" + event.id, emergency_type="water_leak", severity="high",
                    affected_zone_ids=[zone_id], created_by=principal.person_id,
                    description=f"Ring flood detection: device {event.source}; event {event.event_id}; "
                                f"observed {event.occurred_at.isoformat()}; zone confirmed by operator",
                ), now)
                event.emergency_id = incident.emergency_id
                event.status = "processed"
            elif event.signal == "freeze_detected":
                event.status = "review"
            else:
                event.status = "ignored"
            self.repository.save_ring_event(event)
            return event
