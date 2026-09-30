"""Reviewable agent writes. Bedrock can propose, but cannot confirm actions."""
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.agent import PendingAction
from app.repository import Repository, InMemoryRepository
from app.services.errors import DomainError


class PendingActionStore:
    """Bounded, expiring proposals persisted by the injected repository."""
    def __init__(self, repository: Repository | None = None):
        self.repository = repository if repository is not None else InMemoryRepository()

    def propose(self, actor_id: str, tool: str, arguments: dict, now: datetime) -> PendingAction:
        with self.repository.transaction():
            active = []
            for action in self.repository.list_pending_actions():
                if action.expires_at <= now:
                    self.repository.delete_pending_action(action.id)
                else:
                    active.append(action)
            for action in active:
                if (action.actor_id == actor_id and action.tool == tool
                        and action.arguments == arguments):
                    return action.model_copy(deep=True)
            if len(active) >= 1000:
                raise DomainError(429, "Too many pending actions")
            action = PendingAction(id=uuid4().hex, actor_id=actor_id, tool=tool,
                                   arguments=arguments, created_at=now,
                                   expires_at=now + timedelta(minutes=5))
            self.repository.add_pending_action(action)
            return action

    def consume(self, action_id: str, actor_id: str, now: datetime) -> PendingAction:
        with self.repository.transaction():
            action = self.repository.get_pending_action(action_id)
            if action is None:
                raise DomainError(404, "Pending action not found or already consumed")
            if actor_id != action.actor_id:
                raise DomainError(403, "Action belongs to a different actor")
            if now < action.created_at:
                raise DomainError(422, "Confirmation time precedes proposal")
            self.repository.delete_pending_action(action_id)
        # Commit consumption even on expiry or subsequent domain failure.
        if now >= action.expires_at:
            raise DomainError(410, "Pending action expired")
        return action.model_copy(deep=True)
