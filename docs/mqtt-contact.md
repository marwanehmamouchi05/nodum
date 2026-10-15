# Read-only MQTT contact observations

Status: **PROTOCOL TESTED** with Paho 2.1.0 and a separate aMQTT 0.11.3 loopback
broker over MQTT 3.1.1. No physical sensor, deployed broker TLS/ACL or discovery is
verified. This is an application-specific payload contract, not universal MQTT
device support. No publishing or actuator command is implemented by the collector.

## Contract and authorization

The exact topic is generated from trusted server configuration:
`nodum/v1/contact/{percent-encoded-building-id}/{percent-encoded-device-id}`.
No wildcard subscription or payload-selected destination is accepted.

```json
{"event_id":"sample-123","observed_at":"2026-10-15T12:00:00Z","state":"closed"}
```

The timestamp must be an explicit timezone-aware string, no older than five minutes
and no more than 30 seconds in the future. Maximum application payload is 1024 bytes;
duplicate JSON keys, extra fields, unsupported state and retained delivery are rejected.
`event_id` is 1–128 ASCII letters/digits/underscores/hyphens. IDs are per device.

The device must already be a configured `sensor` in the expected building with a
valid parent location. The server operator needs both `hardware.configure` and
`activity.read` in that sensor scope. Grants/user activity are checked at startup
and freshly for every observation. Admin configuration authority alone does not
grant operational ingestion. Broker publisher identities, TLS and per-device topic
ACLs are separate requirements; payloads cannot authenticate a physical sensor.

Normalized observations use the existing `operation_activity` storage and resource
bindings. No schema migration or changes to physical capabilities are needed.
SQLite commits observation and scope binding together. IDs/digests make replay
idempotent across restart/concurrent connections; conflicting content returns a
rejection. Manager Activity retains its existing scope filter and shows the event;
demo device observations retain the Simulation label. General device health and
physical door state are not asserted by a contact event.

## Optional installation and bounded collection

Install `backend/requirements-mqtt.txt` into the backend environment. Core API
startup never imports Paho or starts a subscriber automatically. Paho is dual
EPL-2.0 / EDL-1.0 licensed; the optional test broker is MIT licensed.

Create private server JSON configuration with `host`, `port` (default 8883),
`ca_file`, `building_id`, `device_id` and `operator_user_id`. Unknown keys fail.
Supply dedicated `MQTT_USERNAME`/`MQTT_PASSWORD` through the process secret facility.
Use a scoped, production-mode installation with an explicit existing SQLite file.

```powershell
python backend/scripts/mqtt_collect.py --config C:/nodum-config/contact.json --seconds 60
```

The tool refuses unverified TLS and missing credentials. It neither migrates nor
seeds storage. Each invocation observes for 1–3600 seconds and reports only local
subscription status/counters. TLS, connection/subscription failure, storage failure
or invalid configuration returns nonzero. Do not run it against live building
hardware before separate owner-approved acceptance. Configure least-privilege
publisher/subscriber ACLs and broker packet/connection/rate limits first.

## Reproducible protocol fixture

Install `requirements-mqtt-broker-test.txt` in a separate virtual environment; its
Click dependency differs from the core pins. Then run from the isolated root:

```powershell
python backend/scripts/mqtt_drill.py --broker-python C:/nodum-broker-env/Scripts/python.exe
```

The fixture starts a real loopback-only anonymous broker in a child process,
publishes synthetic samples from a test publisher, and persists scoped SQLite
activity. It checks retained/malformed rejection, duplicate handling, exact topics,
broker termination/restart and resubscription, grant revocation and Manager activity.
No callback-only mock is used for these transport checks. Both processes stop and
the temporary database is removed. Unit/security tests also cover wrong building,
restricted readers, stale/future observations, conflicting events, concurrent
delivery, SQLite rollback and repository restart.

`--events 1..1000` provides a bounded synthetic burst measurement. It is not a
capacity/SLA certification or proof of long-term retention behavior.

## Remaining limits

- Clean MQTT sessions: observations during disconnect/process downtime can be lost;
  no durable broker session, offline queue or exactly-once guarantee is claimed.
- Valid recorded observations are committed; on unexpected storage failure the
  collector stops. QoS acknowledgments are not a substitute for durable end-to-end delivery.
- The API/Manager activity projection still loads its authorized history; long-term
  pagination/retention needs a separate change before sustained telemetry volume.
- No latest-value/device-health UI, device discovery, hardware commissioning,
  TLS client certificate identity or deployed broker ACL acceptance yet.

Sources: [Paho client](https://github.com/eclipse-paho/paho.mqtt.python),
[aMQTT broker configuration](https://amqtt.readthedocs.io/en/latest/references/broker_config/),
[MQTT specification](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).


### Local TLS and ACL acceptance — 2026-10-15

`backend/scripts/mqtt_security_drill.py` now verifies a disposable aMQTT 0.11.3
TLS/password/ACL broker with two synthetic building topic namespaces. Trust/name
failures, bad/anonymous credentials, foreign/wildcard subscriptions and forbidden
publications were rejected; both legitimate streams delivered. Nodum grant revocation
was checked independently with still-valid broker credentials. See `SECURITY_AUDIT.md`.
This supersedes the local broker TLS gap only: no deployed broker, client-certificate
identity, packet-size/rate policy or physical sensor has been verified. Test broker
must not be treated as deployment configuration.


## Engineering contract update — 2026-10-15

New observations persist optional `source_event_id` for independent correlation.
Authenticated operational-journal pages are available at `GET /manager/activity`;
see DIGITAL_TWIN_INTEGRATION_CONTRACT.md. Manager operational journal no longer
loads the full collection; this does not paginate every other timeline source.

Private collector config now accepts `max_observations` (default 100000, range
1–1000000) per device. SQLite count/reservation/insertion is atomic and survives
restart. New observations at capacity are rejected; exact duplicates still dedupe.
Status `capacity_reached` makes the collector CLI fail. No existing audit data is
deleted; configure consistent budgets between collectors. Fleet disk quotas,
archiving/retention and durable offline delivery still require separate work.
