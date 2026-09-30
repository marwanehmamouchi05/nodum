"""Idempotent demo inventory. Providers start disabled: Ring-only remains usable."""
from datetime import datetime, timezone

from app.integrations.building import SimulatedCredentialReader
from app.models.integrations import (
    BuildingDevice, BuildingIntegration, CredentialBinding, DeviceMapping, DeviceState,
)


def demo_records():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    integrations = [BuildingIntegration(id="demo-" + kind, name="Simulated " + kind.replace("_", " "),
                    kind=kind, enabled=False, created_at=at, updated_at=at)
                    for kind in ("access_control", "credential_reader", "elevator", "wayfinding")]
    devices = []
    mappings = []
    for identifier, kind, device_type, zone, capabilities, scopes, target in (
        ("demo-entrance", "access_control", "door", "lobby", ["lock", "unlock", "temporary_unlock", "status"], ["lobby"], None),
        ("demo-office-door", "access_control", "smart_lock", "office-106", ["lock", "unlock", "temporary_unlock", "status"], ["office-106"], None),
        ("demo-reader", "credential_reader", "credential_reader", "lobby", ["read_credential", "status"], ["lobby"], "demo-entrance"),
        ("demo-office-reader", "credential_reader", "credential_reader", "office-106", ["read_credential", "status"], ["office-106"], "demo-office-door"),
        ("demo-elevator", "elevator", "elevator", "lobby", ["call_elevator", "authorize_floor", "status"], ["lobby", "office-106", "floor-5", "machine-room", "utility-room"], None),
        ("demo-navigation", "wayfinding", "digital_sign", "lobby", ["illuminate_route", "show_destination", "clear_route", "status"], ["lobby", "office-106"], None),
    ):
        devices.append(BuildingDevice(id=identifier, integration_id="demo-" + kind, provider="simulator",
                       device_type=device_type, name=identifier.replace("demo-", "Simulated "), zone_id=zone,
                       capabilities=capabilities, target_device_id=target, created_at=at))
        mappings.append(DeviceMapping(id=identifier, zone_ids=scopes, updated_at=at, updated_by="manager-1"))
    credentials = [CredentialBinding(id="demo-resident-card", kind="nfc", person_id="resident-1",
                   fingerprint=SimulatedCredentialReader().fingerprint("nfc", "DEMO-RESIDENT-NFC"), created_at=at)]
    return [
        ("save_integration", integrations), ("save_device", devices), ("save_device_mapping", mappings),
        ("save_device_state", [DeviceState(id=d.id, current_floor=0 if d.device_type == "elevator" else None,
                                          updated_at=at) for d in devices]),
        ("save_credential", credentials),
    ]
