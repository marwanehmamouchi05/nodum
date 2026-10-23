# Official Ring Playground integration

The hardware-free judge installation imports documented Ring sandbox history.
It does not require a customer camera, subscription or production account link.

An authorized demo operator opens **Demo Mode → Sync official sandbox events**.
The backend calls the official device-list API, then
`GET /v1/history/devices/{id}/events` for up to three discovered devices and twenty
records per device. It never follows URLs supplied by responses. Calls use the
server-only `RING_PLAYGROUND_TOKEN`; the token is never returned to the interface.

Validated events enter the scoped, persistent Ring inbox with
`official_ring_playground_history` provenance. Stable event IDs prevent duplicate
imports. `on_demand` records are labeled live view, not motion or visitor identity.
The Manager Security and Activity views label these records **Official Ring sandbox**.
No customer account, door permission or incident is fabricated by an import.

The evidence panel stores the import timestamp, device names and event summaries.
It remains readable after the temporary token expires and after an app restart.
It explicitly describes stored evidence rather than a current live connection.
Fresh synchronization requires a valid approximately thirty-minute Playground
token, renewed privately through the official console and installed server-side.
Operator permissions, session/CSRF checks and two global syncs per UTC minute apply.

## Hosted acceptance, October 22–23, 2026

The AWS deployment imported one official sandbox device and two `on_demand`
history records at 2026-10-22 23:58:30 UTC. Both entered durable, scoped Nodum
context. Resident and business access were denied; invalid CSRF was rejected.
The separately labeled custom simulator remains available for arrival scenarios.
Production account linking, vendor-origin webhooks and physical door control are
not established by this evidence.

Official references: [event history](https://developer.amazon.com/docs/ring/api-documentation.html#event-history),
[Playground sample](https://github.com/AmazonAppDev/ring-api-helloworld),
[hackathon rules](https://amazonappdev2026.devpost.com/rules).
