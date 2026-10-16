"""Bounded, authorized planning only. No deletion or archive operation exists.

An explicit proposed cutoff is a what-if input, never policy approval. Contact
observations share the audit journal: candidates must be archived and their replay
identity preserved before a future, separately reviewed deletion implementation.
"""

from datetime import datetime

from app.models.authorization import Permission as P
from app.services.activity import ActivityService
from app.services.errors import DomainError


def plan_contact_retention(
    authorization, *, scope_id, before, now, max_scan=500, held_ids=()
):
    if (
        not isinstance(before, datetime)
        or before.utcoffset() is None
        or not isinstance(now, datetime)
        or now.utcoffset() is None
        or before > now
        or type(max_scan) is not int
        or not 1 <= max_scan <= 1000
        or not isinstance(scope_id, str)
        or not scope_id
    ):
        raise DomainError(
            422,
            "An explicit scope, past UTC-aware cutoff and scan limit 1–1000 are required",
        )
    held = set(held_ids)
    scanned = candidates = protected = held_count = 0
    cursor = None
    # Keep live permission checks and the bounded observation consistent. No I/O.
    with authorization.repository.transaction():
        authorization.require_scope(P.HARDWARE_CONFIGURE, scope_id)
        authorization.require_scope(P.ACTIVITY_READ, scope_id)
        activity = ActivityService(authorization)
        while scanned < max_scan:
            limit = min(100, max_scan - scanned)
            page = activity.page(scope_id=scope_id, limit=limit, cursor=cursor)
            # Charge the requested candidate budget even for ownership-filtered
            # sparse pages, preventing an unbounded search through hidden records.
            scanned += limit
            for row in page["items"]:
                if row.get("source") != "MQTT contact observation" or row.get(
                    "action"
                ) not in {"sensor.contact.open", "sensor.contact.closed"}:
                    protected += 1
                    continue
                try:
                    at = datetime.fromisoformat(row["at"])
                    if at.utcoffset() is None:
                        raise ValueError()
                except (KeyError, TypeError, ValueError):
                    protected += 1
                    continue
                if row["id"] in held:
                    held_count += 1
                elif at < before:
                    candidates += 1
            cursor = page["next_cursor"]
            if cursor is None:
                break
    return {
        "schema_version": 1,
        "mode": "dry_run",
        "apply_enabled": False,
        "scope_id": scope_id,
        "proposed_before": before.isoformat(),
        "scan_budget_used": scanned,
        "candidate_count": candidates,
        "protected_count": protected,
        "held_count": held_count,
        "truncated": cursor is not None,
        "requires": [
            "owner_policy",
            "verified_archive",
            "durable_replay_identity",
            "authoritative_holds",
            "separately_reviewed_apply",
        ],
    }
