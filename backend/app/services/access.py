from datetime import datetime

from app.models.access import AccessCheckInput, AccessRequest
from app.repository import Repository
from app.services.access_engine import evaluate_access
from app.services.errors import DomainError


def check_access(repository: Repository, payload: AccessCheckInput, now: datetime):
    with repository.transaction():
        person = repository.get_person(payload.person_id)
        zone = repository.get_zone(payload.zone_id)
        if person is None:
            raise DomainError(404, "Person not found")
        if zone is None:
            raise DomainError(404, "Zone not found")
        return evaluate_access(
            AccessRequest(**payload.model_dump(), requested_at=now), person, zone,
            repository.list_permissions(), repository.list_work_orders(),
        )
