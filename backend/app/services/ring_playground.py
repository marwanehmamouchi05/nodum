"""Official sandbox history -> durable, scoped Nodum review context.

This polls Ring's real API with a short-lived Playground credential. It does
not manufacture a webhook, impersonate a linked customer, or promote a live
view session to a person/doorbell detection.
"""
from datetime import datetime, timezone
import json
from urllib.parse import quote

from app.integrations.ring.client import RingClient, RingRemoteError
from app.models.ring import RingEvent
from app.services.errors import DomainError
from app.services.ring import identity
from app.services.scoped_repository import bind_created

ACCOUNT = "official.playground"
SOURCE = "official_ring_playground_history"


def text(value, maximum=200):
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or any(ord(c) < 32 for c in value):
        raise ValueError()
    return value


class PlaygroundService:
    def __init__(self, repository, settings, client=None):
        self.repo, self.settings = repository, settings
        self.client = client or RingClient(settings)

    def evidence(self, scope_id):
        return self.repo.get_admin_settings("ring-playground:" + scope_id) or {
            "source": SOURCE, "stored": True, "checked_at": None, "devices": [], "events": []}

    def sync(self, token, scope_id, now, authorize=None):
        if not token:
            raise DomainError(503, "A fresh temporary Ring Playground token is required to sync. Previously imported sandbox evidence remains available.")
        response = self.client.api("GET", "/v1/devices", token)
        pending, devices = [], []
        try:
            records = response["data"]
            if not isinstance(records, list) or len(records) > 50:
                raise ValueError()
            truncated = len(records) > 3
            for device in records[:3]:
                if device["type"] != "devices":
                    raise ValueError()
                device_id = text(device["id"])
                name = text(device["attributes"]["name"])
                devices.append({"id": device_id, "name": name})
                history = self.client.api("GET", "/v1/history/devices/" + quote(device_id, safe="") + "/events", token)["data"]
                if not isinstance(history, list) or len(history) > 1000:
                    raise ValueError()
                truncated = truncated or len(history) > 20
                for record in history[:20]:
                    if record["type"] != "history-events":
                        raise ValueError()
                    event_id = text(record["id"])
                    attrs = record["attributes"]
                    kind = text(attrs["event_type"], 100)
                    start = attrs["start"]
                    if type(start) is not int or start < 0:
                        raise ValueError()
                    source = record["relationships"]["source"]["data"]
                    if source != {"type": "devices", "id": device_id}:
                        raise ValueError()
                    occurred = datetime.fromtimestamp(start / 1000, timezone.utc)
                    pending.append(RingEvent(
                        id=identity(self.settings.environment, ACCOUNT, device_id, event_id),
                        environment=self.settings.environment, account_id=ACCOUNT,
                        request_id=identity(SOURCE, device_id, event_id), event_id=event_id,
                        event_type="history:" + kind, source="playground:" + device_id, source_type="devices",
                        occurred_at=occurred, received_at=now,
                        signal={"motion": "motion", "ding": "doorbell", "on_demand": "live_view"}.get(kind, "unknown"),
                        raw_payload=json.dumps({"source": SOURCE, "transport": "api_history", "history": record}),
                    ))
        except (ValueError, KeyError, TypeError, OverflowError, OSError):
            raise RingRemoteError() from None
        evidence = {"source": SOURCE, "stored": True, "checked_at": now.isoformat(),
                    "devices": devices, "events": [{"id": e.id, "event_type": e.event_type,
                        "signal": e.signal, "occurred_at": e.occurred_at.isoformat()} for e in pending],
                    "truncated": truncated, "transport": "api_history",
                    "scope": "Official sandbox history, not a vendor webhook or physical-device verification"}
        added = 0
        with self.repo.transaction():
            if authorize and authorize() != scope_id:
                raise DomainError(403, "Sandbox scope changed; retry from your authorized workspace")
            for event in pending:
                old = self.repo.get_ring_event(event.id)
                if old and (old.event_type, old.source, old.occurred_at) != (event.event_type, event.source, event.occurred_at):
                    raise DomainError(409, "Conflicting official sandbox event identity")
                if not old:
                    self.repo.save_ring_event(event)
                    added += 1
                bind_created(self.repo, "ring_event", event.id, scope_id)
            self.repo.save_admin_settings("ring-playground:" + scope_id, scope_id, evidence)
        return {**evidence, "new_events": added}
