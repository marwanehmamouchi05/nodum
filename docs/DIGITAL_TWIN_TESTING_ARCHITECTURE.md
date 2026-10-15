# Independent lab testing architecture

Phase 1 provides a small external participant, not the full simulator. Start with
[the implemented connection contract](DIGITAL_TWIN_INTEGRATION_CONTRACT.md).

## Implemented split

- `backend/scripts/external_contract_drill.py` owns disposable server resources:
  isolated SQLite, trusted initial organization/recovery authority, Uvicorn HTTPS,
  a separate TLS/password/ACL broker process, and the actual Nodum subscriber.
  Only initial recovery provisioning is done internally. It does not provision the
  test buildings/devices/accounts by direct database writes.
- `tools/contract_client/client.py` is a separate process using standard HTTPS and
  Paho MQTT. No Nodum imports, database path, SQL, subprocesses or shared service
  objects. It provisions two buildings/devices/scoped accounts via authenticated
  APIs, publishes messages and reads actual durable outcomes through HTTPS.
- Small temporary marker files coordinate readiness and broker restart. They carry
  setup IDs/control timing, not product events or verdicts. Product events still
  traverse MQTT; onboarding and observations traverse authenticated HTTPS.
- A deterministic evaluator compares external facts against the emitted samples.
  Its checks do not disappear with Python `-O`. Mutation tests corrupt association,
  state, timestamp, simulation flag, IDs and duplicates to prove it detects failure.
- Server counters supplement the verdict and require both malformed/revoked rejection
  paths; the client never treats those counters as its sole evidence.

The fixture creates temporary secrets and a one-hour loopback certificate. It never
modifies OS trust, uses real providers or sends physical commands. All child processes
are bounded and stopped in finally blocks. Broker connections are capped at eight.
Negative observations have a documented 0.75-second window after positive delivery;
this is not a proof about indefinitely delayed messages.

## Future independent engine

Keep a separate project/package for building profiles, actors, devices, a validated
scenario language, scheduler, protocol transports, fault injection, run artifacts
and invariant evaluator. It may reuse the client as an external transport example,
not import Nodum services or turn marker files into an ingestion shortcut.

AI may propose scenarios and explain failed evidence. A schema/capability validator
must reject unsupported or unauthorized actions before scheduling. Deterministic
invariants decide PASS/FAIL/BLOCKED/NOT TESTED; AI cannot override them. Maintain
explicit budgets for connections, events, duration, payload bytes and disk artifacts.

Separate component tests, protocol acceptance, whole-application scenarios,
deployment tests and hardware acceptance. A simulated unlock is not an acknowledgment
from an actual controller; an acknowledgment is not physical readback. Certified
life-safety behavior remains outside experimental control.

Every run needs: scenario version, seed, relative event timing, capability/evidence
requirements, fixture/software revision, expected invariants, actual observations,
failure reason and reproducible redacted report. Never save passwords, cookies,
raw provider tokens or private resident records in a run artifact. Live authorities
must not be inherited from the developer shell.

Initial scenarios should expand the existing contact proof: valid delivery,
duplicate/conflict, malformed/retained/stale messages, foreign topic and timeline,
grant revocation, broker reconnect, storage failure and capacity. Claims for a
second real protocol require its own adapter and wire fixture. Offline durable
replay, multi-actor frontends and 2D/3D views belong to later phases.
