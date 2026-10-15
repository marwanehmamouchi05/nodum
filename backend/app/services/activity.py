"""Versioned, scope-safe pagination for operational journal observations only."""
import base64
from datetime import datetime
import json
import re

from app.models.authorization import Permission as P
from app.services.errors import DomainError


def encode_cursor(record):
    return base64.urlsafe_b64encode(json.dumps([1, record["at"], record["id"]], separators=(",", ":")).encode()).decode().rstrip("=")


def decode_cursor(value):
    if value is None:
        return None
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,768}", value):
            raise ValueError()
        data = json.loads(base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True))
        if (not isinstance(data, list) or len(data) != 3 or type(data[0]) is not int or data[0] != 1
                or not isinstance(data[1], str) or len(data[1]) > 64
                or not isinstance(data[2], str) or not 1 <= len(data[2]) <= 256
                or datetime.fromisoformat(data[1]).utcoffset() is None):
            raise ValueError()
        return tuple(data[1:])
    except (ValueError, TypeError, UnicodeError):
        raise DomainError(422, "Invalid activity cursor") from None


class ActivityService:
    def __init__(self, authorization, *, ai_context=False):
        self.auth = authorization
        self.repo = authorization.repository
        self.ai_context = ai_context

    def page(self, *, cursor=None, limit=100, scope_id=None):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise DomainError(422, "Activity limit must be 1 to 100")
        before = decode_cursor(cursor)
        with self.repo.transaction():
            if scope_id:
                self.auth.require_scope(P.ACTIVITY_READ, scope_id)
            scopes = [s.id for s in self.repo.list_scopes()
                if (scope_id is None or scope_id in self.auth.ancestors(s.id))
                and self.auth.allowed_scope(P.ACTIVITY_READ, s.id)
                and (not self.ai_context or self.auth.allowed_scope(P.AI_USE, s.id))]
            candidates = self.repo.page_operation_activity(scopes, before=before, limit=limit + 1)
            scanned = candidates[:limit]
            items = [r for r in scanned if self.auth.allowed(P.ACTIVITY_READ, "operation_activity", r["id"])
                and (not self.ai_context or self.auth.allowed(P.AI_USE, "operation_activity", r["id"]))]
            # Advance by scanned candidates even for sparse ownership-filtered pages.
            next_cursor = encode_cursor(scanned[-1]) if len(candidates) > limit else None
            return {"schema_version": 1, "items": items, "next_cursor": next_cursor}

    def public_page(self, **kwargs):
        result = self.page(**kwargs)
        fields = {"id", "at", "action", "resource_id", "location_id", "observed_at", "source", "source_event_id", "simulated"}
        result["items"] = [{k: v for k, v in item.items() if k in fields} for item in result["items"]]
        return result
