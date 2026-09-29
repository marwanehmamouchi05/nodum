"""Reviewable agent writes. Bedrock can propose, but cannot confirm actions."""
from datetime import datetime, timedelta
from threading import RLock
from uuid import uuid4

from app.models.agent import PendingAction
from app.services.errors import DomainError


class PendingActionStore:
    """Process-local, bounded, expiring proposals; no building data is duplicated."""
    def __init__(self):
        self._lock = RLock()
        self._actions: dict[str, PendingAction] = {}

    def propose(self, actor_id: str, tool: str, arguments: dict, now: datetime) -> PendingAction:
        with self._lock:
            self._actions = {key: value for key, value in self._actions.items()
                             if value.expires_at > now}
            for action in self._actions.values():
                if (action.actor_id == actor_id and action.tool == tool
                        and action.arguments == arguments):
                    return action.model_copy(deep=True)
            if len(self._actions) >= 1000:
                raise DomainError(429, "Too many pending actions")
            action = PendingAction(id=uuid4().hex, actor_id=actor_id, tool=tool,
                                   arguments=arguments, created_at=now,
                                   expires_at=now + timedelta(minutes=5))
            self._actions[action.id] = action.model_copy(deep=True)
            return action

    def consume(self, action_id: str, actor_id: str, now: datetime) -> PendingAction:
        with self._lock:
            action = self._actions.get(action_id)
            if action is None:
                raise DomainError(404, "Pending action not found or already consumed")
            if actor_id != action.actor_id:
                raise DomainError(403, "Action belongs to a different actor")
            if now < action.created_at:
                raise DomainError(422, "Confirmation time precedes proposal")
            del self._actions[action_id]
            if now >= action.expires_at:
                raise DomainError(410, "Pending action expired")
            # Consume before execution: concurrent/repeated confirmation cannot retry
            # a write. Domain failures require a new proposal; no automatic retry.
            return action.model_copy(deep=True)
