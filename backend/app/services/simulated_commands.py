"""Validate pure simulator output against the service-authorized command.

This is not a physical acknowledgment or delivery protocol. Adapters may only
change fields owned by this command and cannot widen the authorized context.
"""

from app.models.integrations import Command, DeviceState


def validate_simulated_result(command, before, after, context):
    after = DeviceState.model_validate(after.model_dump())
    allowed = {"last_command_id", "updated_at"}
    if command in {Command.LOCK, Command.UNLOCK, Command.TEMPORARY_UNLOCK}:
        allowed |= {"locked", "unlocked_until"}
        if after.locked != (command == Command.LOCK):
            raise ValueError("Invalid simulated lock result")
        if command == Command.LOCK:
            if after.unlocked_until is not None:
                raise ValueError("Locked state cannot retain an unlock lease")
        elif (
            after.unlocked_until is None
            or not context.at < after.unlocked_until <= context.expires_at
        ):
            raise ValueError("Unlock lease exceeds authorized interval")
    elif command == Command.CALL:
        allowed.add("requested_floor")
        if after.requested_floor != context.floor:
            raise ValueError("Unexpected requested floor")
    elif command in {Command.AUTHORIZE_FLOOR, Command.ILLUMINATE, Command.SHOW}:
        allowed |= {
            "authorized_zone_id",
            "authorized_person_id",
            "authorization_expires_at",
        }
        if (
            after.authorized_zone_id != context.zone_id
            or after.authorized_person_id != context.person_id
            or after.authorization_expires_at is None
            or not context.at < after.authorization_expires_at <= context.expires_at
        ):
            raise ValueError("Adapter expanded authorization")
        if command == Command.AUTHORIZE_FLOOR:
            allowed.add("authorized_floor")
            if after.authorized_floor != context.floor:
                raise ValueError("Unexpected authorized floor")
        else:
            allowed |= {"route", "destination_label"}
            if (
                after.route != list(context.route)
                or after.destination_label != context.destination_label
            ):
                raise ValueError("Unexpected route")
    elif command == Command.CLEAR:
        allowed |= {"route", "destination_label"}
        if after.route or after.destination_label is not None:
            raise ValueError("Route was not cleared")
    else:
        raise ValueError("Unknown simulated command")
    if after.last_command_id != context.command_id or after.updated_at != context.at:
        raise ValueError("Invalid command correlation")
    before_fields, after_fields = before.model_dump(), after.model_dump()
    if any(
        after_fields[key] != value
        for key, value in before_fields.items()
        if key not in allowed
    ):
        raise ValueError("Adapter modified unrelated device state")
    return after
