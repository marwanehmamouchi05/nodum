# Nodum architecture

Engineering checkpoint, 2026-10-15. Read with [security readiness](SECURITY_READINESS.md),
[ADR 0001](decisions/0001-operational-activity-pages.md) and [architecture findings](ARCHITECTURE_AUDIT.md).

## Components and responsibilities

| Area | Actual code | Responsibility |
|---|---|---|
| Product UI | `frontend/src` | React/TypeScript workspaces, typed requests, role-aware navigation; server remains authoritative |
| HTTP composition | `backend/app/main.py`, `app/api` | Validation, dependencies, request limits, session/CSRF, thin resource routes |
| Domain services | `backend/app/services` | Building topology, accounts, visitors, maintenance, role/resource policy, workflow invariants |
| Contracts | `backend/app/models` | Pydantic records and explicit versioned/typed inputs; reject extra authority fields |
| Data boundary | `app/repository.py`, `*_repository.py`, `sqlite_repository.py` | Explicit service-facing protocol, scoped resource bindings, parameterized SQLite persistence |
| Transactions | `app/database.py` | Versioned additive migrations, WAL, FK checks, nested savepoints, serialized validation/write |
| Integration ports | `app/integrations/building.py`, `ring/`, `mqtt_sensor.py` | Pure simulator adapters; bounded Ring client; optional read-only MQTT transport |
| Operations | `app/maintenance.py`, `backend/scripts` | Preflight, safe backup/restore, isolated wire drills and bounded benchmarks |
| Independent participant | `tools/contract_client/client.py` | Separate HTTPS/MQTT process; no Nodum imports, database path or direct DB access |

This remains a modular monolith. No microservices, message bus, discovery framework,
remote plugin loading or production database replacement was introduced.

## Main flows

Browser → secure session → fresh role ceiling + active scope ancestry + resource
binding + personal/business ownership → service transaction → repository → SQLite.
Client-selected role labels, scope fields or identifiers never replace those checks.
AI proposals use the same services and require confirmation/fresh authorization.

MQTT publisher → independently authenticated TLS broker/topic ACL → exact bound
subscriber → strict contact payload/time validation → fresh device/operator authority
→ duplicate/conflict check + storage budget → journal and binding committed together.
`GET /manager/activity` is the external observer of the resulting durable journal;
MQTT PUBACK or collector subscription does not mean application acceptance.

Ring signed delivery → verified inbox receipt → normalization → explicit operator
review/workflow. Ring arrival signals never establish visitor identity or access.
The live inbound linking contract is still gated; [Ring review](ring-integration.md).

## Integration inventories are deliberately distinct

Configured `StructureNode` is the product's building hierarchy, not proof of a
working adapter. Its capability array remains empty and configured hardware status
unverified. Historical `BuildingDevice`/`ConnectorRegistry` represents pure software
simulators and read-only discovered Ring inventory. Do not silently bridge these
inventories or turn a configured lock into a live actuator. The new activity page
connects supported observations to product context without making that claim.

## Persistence and concurrency

SQLite is the production repository in this checkpoint. Memory storage is a test
double whose transaction is a lock, not rollback. Migration 9 indexes activity
keyset reads; migration 10 indexes contact budget checks. Migration history is
append-only. Backup/restore and an upgrade/restart regression cover the new schema.

Reads still use the repository's `BEGIN IMMEDIATE` transaction to keep authority and
data coherent. That can contend with ingestion; this is not a high-concurrency SLA.
The journal is paged, but Ring/actuator/appointment histories and some workspace
projections still scan collections. Contact quotas bound each configured collector
device's retained observations; they are not a global disk quota or retention policy.

## Team and release boundaries

Frontend engineers work against API/models; integration engineers extend documented
ports/fixtures; backend engineers maintain service invariants/repositories. New
physical I/O requires a separate durable command lifecycle and approved bench.
Follow [onboarding](DEVELOPER_ONBOARDING.md) and [PR checklist](../.github/pull_request_template.md).
CI runs tests, correctness lint and frontend type/build checks; its hosted execution
is pending the first authorized push. No local success implies remote CI success.
