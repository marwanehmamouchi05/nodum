"""Scoped read boundary for HTTP and AI. Policy evaluation uses full snapshots.

No filtered emergency/permission snapshot may reach the physical policy engine.
Writes are limited to operations authorized by the request/tool boundary, with
explicit parent ownership for newly-created records.
"""
from contextlib import contextmanager
from app.models.authorization import Permission as P, ResourceBinding
from app.services.errors import DomainError


READS = {
    "get_person": ("person", P.PEOPLE_READ), "list_people": ("person", P.PEOPLE_READ),
    "get_zone": ("location", P.LOCATIONS_READ), "list_zones": ("location", P.LOCATIONS_READ),
    "get_business": ("business", P.BUSINESSES_READ), "list_businesses": ("business", P.BUSINESSES_READ),
    "get_appointment": ("appointment", P.VISITORS_READ), "list_appointments": ("appointment", P.VISITORS_READ),
    "list_permissions": ("access_permission", P.ACCESS_READ),
    "list_work_orders": ("work_order", P.MAINTENANCE_READ),
    "get_emergency": ("incident", P.INCIDENTS_READ), "list_emergencies": ("incident", P.INCIDENTS_READ),
    "get_integration": ("integration", P.HARDWARE_READ), "list_building_integrations": ("integration", P.HARDWARE_READ),
    "get_device": ("device", P.HARDWARE_READ), "list_building_devices": ("device", P.HARDWARE_READ),
    "get_device_mapping": ("device", P.HARDWARE_READ), "list_device_zone_mappings": ("device", P.HARDWARE_READ),
    "get_device_state": ("device", P.ACCESS_READ), "list_device_states": ("device", P.ACCESS_READ),
    "get_credential": ("credential", P.ACCESS_READ), "list_credentials": ("credential", P.ACCESS_READ),
    "get_credential_event": ("credential_event", P.ACTIVITY_READ), "list_credential_events": ("credential_event", P.ACTIVITY_READ),
    "get_actuator_event": ("actuator_event", P.ACTIVITY_READ), "list_actuator_events": ("actuator_event", P.ACTIVITY_READ),
    "get_journey": ("journey", P.ACTIVITY_READ), "list_journeys": ("journey", P.ACTIVITY_READ),
    "get_journey_transition": ("journey_transition", P.ACTIVITY_READ), "list_journey_transitions": ("journey_transition", P.ACTIVITY_READ),
    "get_ring_account": ("ring_account", P.RING_READ), "list_ring_accounts": ("ring_account", P.RING_READ),
    "get_ring_event": ("ring_event", P.RING_READ), "list_ring_events": ("ring_event", P.RING_READ),
}


def record_id(record):
    return getattr(record, "emergency_id", None) or record.id


class ScopedRepository:
    def __init__(self, raw, authorization, *, ai_context=False):
        self.raw, self.authorization = raw, authorization
        self.ai_context = ai_context

    @contextmanager
    def transaction(self):
        with self.raw.transaction():
            yield self

    def __getattr__(self, name):
        if name not in READS:
            raise DomainError(403, "Repository operation is unavailable in scoped context")
        resource_type, permission = READS[name]
        def read(*args, **kwargs):
            with self.raw.transaction():
                result = getattr(self.raw, name)(*args, **kwargs)
                def visible(record):
                    return (record is not None and self.authorization.allowed(permission, resource_type, record_id(record))
                        and (not self.ai_context or self.authorization.allowed(P.AI_USE, resource_type, record_id(record))))
                return [r for r in result if visible(r)] if isinstance(result, list) else result if visible(result) else None
        return read


def bind_created(repository, resource_type, resource_id, scope_id):
    previous = repository.get_resource_binding(resource_type, resource_id)
    if previous and previous.scope_id != scope_id:
        raise DomainError(403, "Existing resource belongs to a different scope")
    repository.save_resource_binding(ResourceBinding(resource_type=resource_type,
        resource_id=resource_id, scope_id=scope_id))
