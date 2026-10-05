"""Ring simulation adapter.

When RING_MODE=simulation, the Ring Playground simulator feeds events into the
real Nodum Ring pipeline: it builds the documented v1.1 webhook envelope,
signs it with the configured HMAC signing key, and calls
``RingService.receive_event()``. The event goes through the same normalization,
durable inbox, dedup, and operator-review path used by live webhooks.

The simulator never fabricates Ring data outside of this pipeline. It only
seeds a ``completed`` ``RingAccount`` record owned by ``manager-1`` so the
authenticated operator can discover a small device catalog (Doorbell, Camera,
Contact Sensor) and link events back to it without a real OAuth handshake.

Simulation data is identified by the ``source`` prefix ``simulation:`` and by
clearly-labelled UI badges. No live Ring OAuth or remote endpoints are
contacted; the token associated with the Ring integration is not consulted.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any
import uuid

from cryptography.fernet import Fernet

from app.models.ring import RingAccount, RingDevice, RingEvent
from app.repository import Repository
from app.services.errors import DomainError
from app.services.ring import RingService, identity


# A stable, clearly-labelled identifier for the simulated Ring account. The
# environment scope keeps it isolated from any real production record.
SIM_ACCOUNT_ID = "simulation.playground"

# Reserved account owner used by the simulation. The Ring link flow in real
# mode requires a manager/responder to be authenticated; we re-use the seeded
# operator to keep the demo path self-contained.
SIM_OWNER_PERSON_ID = "manager-1"
SIM_OWNER_USERNAME = "simulation-demo"

# Device catalog returned by /ring/simulation/devices and used by the
# simulator when emitting events. Sources are tagged with the ``simulation:``
# prefix so downstream consumers can render a "simulated" badge.
SIM_DEVICES: tuple[dict[str, Any], ...] = (
    {"id": "sim-doorbell-front", "kind": "video_doorbell",
     "name": "Simulated Front Doorbell",
     "zone_id": "lobby",
     "capabilities": ["motion", "button_press", "person_detected", "package_detected"]},
    {"id": "sim-camera-lobby", "kind": "camera",
     "name": "Simulated Lobby Camera",
     "zone_id": "lobby",
     "capabilities": ["motion", "person_detected", "device_online", "device_offline"]},
    {"id": "sim-contact-utility", "kind": "contact_sensor",
     "name": "Simulated Utility Room Contact Sensor",
     "zone_id": "utility-room",
     "capabilities": ["contact_sensor_faulted", "contact_sensor_cleared"]},
)

# Deterministic demo scenarios. Each scenario emits one or more signed v1.1
# webhook envelopes via the same receive_event path live webhooks use.
SCENARIOS: dict[str, dict[str, Any]] = {
    "visitor_arrives": {
        "label": "Visitor arrives",
        "description": "Doorbell press + person detection at the front entrance.",
        "events": (
            {"kind": "motion_detected", "device": "sim-camera-lobby"},
            {"kind": "button_press", "device": "sim-doorbell-front"},
            {"kind": "person_detected", "device": "sim-doorbell-front"},
        ),
    },
    "package_delivery": {
        "label": "Package delivery",
        "description": "Doorbell press followed by a package detection.",
        "events": (
            {"kind": "motion_detected", "device": "sim-doorbell-front"},
            {"kind": "button_press", "device": "sim-doorbell-front"},
            {"kind": "package_detected", "device": "sim-doorbell-front"},
        ),
    },
    "after_hours_person": {
        "label": "After-hours person detection",
        "description": "Repeated person detections in the lobby during off-hours.",
        "events": (
            {"kind": "motion_detected", "device": "sim-camera-lobby"},
            {"kind": "person_detected", "device": "sim-camera-lobby"},
            {"kind": "motion_detected", "device": "sim-camera-lobby"},
            {"kind": "person_detected", "device": "sim-camera-lobby"},
        ),
    },
    "emergency_access": {
        "label": "Emergency / access event",
        "description": "Doorbell press and an emergency access indication.",
        "events": (
            {"kind": "motion_detected", "device": "sim-camera-lobby"},
            {"kind": "button_press", "device": "sim-doorbell-front"},
        ),
    },
    "contact_sensor_sequence": {
        "label": "Contact sensor open / close",
        "description": "Utility room contact sensor faulted then cleared.",
        "events": (
            {"kind": "contact_sensor_faulted", "device": "sim-contact-utility"},
            {"kind": "contact_sensor_cleared", "device": "sim-contact-utility"},
        ),
    },
    "device_lifecycle": {
        "label": "Device online / offline",
        "description": "Camera reports a brief offline then recovery.",
        "events": (
            {"kind": "device_offline", "device": "sim-camera-lobby"},
            {"kind": "device_online", "device": "sim-camera-lobby"},
        ),
    },
}


class RingSimulationService:
    """Builds deterministic signed events and seeds a simulation Ring account.

    The service owns no network or secrets; it only calls ``RingService``
    methods that already perform signature verification and durable persistence.
    """

    def __init__(self, ring_service: RingService):
        self.ring_service = ring_service
        self.repository: Repository = ring_service.repository
        self.settings = ring_service.settings

    # ----- helpers -------------------------------------------------------

    @staticmethod
    def status_payload(settings) -> dict[str, Any]:
        return {"mode": settings.mode}

    def _signing_key(self) -> str:
        key = self.settings.signing_key
        if not key:
            raise DomainError(503, "Ring signing key is not configured; set RING_SIGNING_KEY or RING_WEBHOOK_SECRET")
        return key

    def _account_key(self) -> str:
        return identity(self.settings.environment, SIM_ACCOUNT_ID)

    def _seed_account(self, now: datetime) -> RingAccount:
        """Idempotently provision a completed RingAccount for the demo."""
        account_id = self._account_key()
        existing = self.repository.get_ring_account(account_id)
        if existing and existing.status == "completed":
            return existing
        # Encrypt a self-issued access/refresh token with the configured Fernet
        # key so the storage shape matches real link records. They are not
        # usable against Ring; the simulator never makes outbound calls.
        secret_marker = json.dumps({
            "access_token": "simulation-access-token-not-valid-against-ring",
            "refresh_token": "simulation-refresh-token-not-valid-against-ring",
        }).encode()
        try:
            encrypted = Fernet(self.settings.encryption_key.encode()).encrypt(secret_marker).decode()
        except (ValueError, TypeError):
            raise DomainError(503, "Ring token encryption key is missing or invalid") from None
        record = RingAccount(
            id=account_id,
            environment=self.settings.environment,
            account_id=SIM_ACCOUNT_ID,
            encrypted_tokens=encrypted,
            expires_at=now + timedelta(days=365),
            received_at=now,
            owner_id=SIM_OWNER_PERSON_ID,
            owner_user_id=None,  # Surface clearly as simulation; no real Nodum user.
            link_verified=True,
            status="completed",
        )
        with self.repository.transaction():
            self.repository.save_ring_account(record)
        return record

    def ensure_account(self, now: datetime) -> RingAccount:
        return self._seed_account(now)

    def account_summary(self, now: datetime) -> dict[str, Any]:
        record = self.ensure_account(now)
        return {
            "account_id": record.account_id,
            "environment": record.environment,
            "status": record.status,
            "owner_id": record.owner_id,
            "is_simulation": True,
        }

    def devices(self) -> list[RingDevice]:
        # Match the JSON:API structure returned by normalize_devices so the
        # frontend's existing discovery UI works against simulation output.
        included_status = {device["id"]: {"online": True, "kind": device["kind"]}
                           for device in SIM_DEVICES}
        return [
            RingDevice(
                id=device["id"],
                name=device["name"],
                attributes={
                    "name": device["name"],
                    "kind": device["kind"],
                    "manufacturer": "ring",
                    "is_simulation": True,
                    "zone_hint": device["zone_id"],
                    "capabilities": device["capabilities"],
                },
                related={"status": included_status[device["id"]]},
            )
            for device in SIM_DEVICES
        ]

    # ----- envelope + delivery --------------------------------------------

    def _envelope(self, kind: str, device_id: str, request_id: str, event_id: str,
                  occurred_at: datetime) -> bytes:
        envelope = {
            "meta": {"version": "1.1", "time": occurred_at.isoformat(),
                     "request_id": request_id, "account_id": SIM_ACCOUNT_ID},
            "data": {"id": event_id, "type": kind,
                     "attributes": {"source": device_id, "source_type": "devices",
                                    "timestamp": int(occurred_at.timestamp() * 1000)}},
        }
        return json.dumps(envelope, separators=(",", ":")).encode()

    def _sign(self, raw: bytes, key: str) -> str:
        return "sha256=" + hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()

    def deliver(self, kind: str, device_id: str, now: datetime,
                request_id: str | None = None,
                event_id: str | None = None) -> dict[str, str]:
        """Build, sign, and deliver one simulated Ring event via the real path."""
        if self.settings.mode != "simulation":
            raise DomainError(403, "Ring simulation is only available in RING_MODE=simulation")
        key = self._signing_key()
        self._seed_account(now)
        request_id = request_id or "sim-" + hashlib.sha1(
            (kind + device_id + now.isoformat()).encode()).hexdigest()[:16]
        event_id = event_id or "evt-" + hashlib.sha1(
            (request_id + kind).encode()).hexdigest()[:16]
        raw = self._envelope(kind, device_id, request_id, event_id, now)
        signature = self._sign(raw, key)
        result = self.ring_service.receive_event(raw, signature, now)
        # ``result`` may be a dict (success) or raise; pass it through unchanged.
        return {"status": result["status"], "id": result["id"], "event_type": kind,
                "device_id": device_id, "signal": kind,
                "request_id": request_id, "event_id": event_id,
                "is_simulation": True}

    # ----- scenarios -----------------------------------------------------

    def run_scenario(self, name: str, now: datetime) -> list[dict[str, Any]]:
        if name not in SCENARIOS:
            raise DomainError(404, f"Unknown simulation scenario: {name}")
        scenario = SCENARIOS[name]
        # Each scenario run gets a unique run token so request_id/event_id stay
        # distinct across reruns and the real Ring dedup path treats them as new
        # deliveries. Without this, repeating a demo would 409.
        run_token = uuid.uuid4().hex[:10]
        delivered = []
        step_at = now
        for index, step in enumerate(scenario["events"]):
            # Each step advances the timestamp by one second so distinct
            # events are visible in chronological order.
            step_at = step_at + timedelta(seconds=index + 1)
            delivered.append(self.deliver(step["kind"], step["device"], step_at,
                                          request_id=f"sim-{name}-{run_token}-{index}",
                                          event_id=f"evt-{name}-{run_token}-{index}"))
        return delivered

    def scenarios(self) -> list[dict[str, Any]]:
        return [{"name": name, "label": data["label"],
                 "description": data["description"],
                 "event_count": len(data["events"])}
                for name, data in SCENARIOS.items()]