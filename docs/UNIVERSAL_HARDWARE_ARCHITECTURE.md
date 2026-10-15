# Hardware extensibility: implemented boundaries and future categories

2026-10-15. Universal extensibility is a design target, not a compatibility claim.
The detailed evidence matrix is [HARDWARE_COMPATIBILITY.md](HARDWARE_COMPATIBILITY.md).
No physical device was verified in this mission.

## Existing contracts to reuse

`app/integrations/building.py`: typed access, elevator, reader and wayfinding ports,
`CommandContext`, pure simulator implementations and a server-owned registry.
`app/models/integrations.py`: inventory, declared capability allowlists, simulated
state, command correlation and audit. `BuildingService` validates policy, mapped
zone, supported command and current integration state before invoking an adapter.
Unknown providers are rejected. No public request can import code or set arbitrary
network endpoints. Keep network I/O out of its current simulator transaction.

`app/integrations/mqtt_sensor.py`: MQTT 3.1.1 contact observations, exact per-device
topic, schema/time/replay validation, fresh scoped authority, atomic persistence and
per-device capacity. Paho is optional. Transport credentials are separate from the
Nodum operator's grants. These are software/protocol tests, not physical identity.

`app/integrations/ring/`: bounded HTTPS client, protected account tokens and signed
event contract; see [Ring limitations](ring-integration.md). A Nodum custom scenario
is neither an official Ring simulator nor a manufacturer device.

Two meaningfully different categories already have executable contracts: contact
monitoring (real MQTT wire fixture) and wayfinding/displays (pure simulator route
state). Access/credential and elevator-request simulators are also tested by
`test_building_integrations.py`. The elevator contract records requests/authorization,
not physical motion. Only contact currently has the new independent external proof.

## Category coverage and risk

| Family | Candidate boundary | Current Nodum evidence / risk |
|---|---|---|
| Doorbell, intercom, camera, NVR | Vendor API, ONVIF profile, RTSP/media adapter | Ring simulation/client; other interfaces researched; private audio/video require separate entitlements |
| Lock, door, reader/keypad, panel, parking gate/garage | Panel/gateway API; OSDP/Wiegand remain reader-controller links | Simulated access/credentials only; security-sensitive actuation blocked |
| Intrusion/alarm monitoring | Read-only events from supported certified controller | Architecture target; no installed adapter |
| Lights, dimmers, switches, relays, blinds/windows | KNX/DALI/Matter/vendor gateway | Wayfinding light/sign simulation only; real switching not implemented |
| HVAC, temperature, air quality, occupancy | BACnet/SC, Modbus, MQTT or vendor API | Contact-only MQTT semantics; no environmental or HVAC adapter |
| Energy/water meters, leaks, equipment maintenance sensors | Documented registers/events or broker schema | Architecture target; no meter/valve control; Ring flood signals are not water-system integration |
| Elevators/escalators | Authorized read-only monitoring or approved vendor access interface | Elevator software requests only; no direct lift control |
| Signage, screens, wayfinding, notices | Display API/SDK with explicit content/privacy rules | Pure route/display simulator; no physical screen adapter |
| Workplace rooms, loading docks, kiosks, commercial parking | Specific vendor/controller integration | Building/visitor domain exists; equipment adapters absent |
| Fire, smoke, emergency-lighting/system notifications | Read-only certified-system gateway | No experimental override, suppression or egress control; certified controller remains authoritative |

Risk classes: read-only monitoring; low-risk reversible actions; security-sensitive
physical operations; operationally critical equipment; life-safety systems. Classify
the actual capability, not its marketing device name. Even monitoring can disclose
private occupancy/video. Higher classes require independent safety/vendor review.

## Protocol strategy

| Interface | Actual implication and dependency |
|---|---|
| REST/webhooks/vendor SDKs | Exact vendor schemas, identity, signatures, rate/size budgets and entitlement; no generic discovery guarantee |
| MQTT | Pub/sub transport only. Current fixed contact v1 schema; TLS, auth and topic ACLs separately verified locally |
| ONVIF / RTSP | Exact conformant profiles/media version/codecs; streams are not visitor identity or lock authorization |
| BACnet/IP / BACnet Secure Connect | Controller object/point lists and network permissions; SC adds certificate/hub commissioning; start read-only |
| Modbus TCP/RTU | Vendor register/coil maps, scaling and gateway security; no inferred semantics or arbitrary writes |
| KNX | Engineered building automation installation, commissioning tools and appropriate secure gateway; not a generic HTTP peripheral |
| DALI/DALI-2 | Lighting control gear/devices and certified components/application controller; gateway commissioning required |
| Matter | Commissioned fabric/controller and supported device-type clusters; certification/attestation requirements |
| Zigbee / Z-Wave | Supported coordinator/controller, secure inclusion and product clusters/command classes; regional/licensing constraints |
| OSDP / Wiegand | Peripheral-to-panel links; OSDP Secure Channel must be commissioned; use an authorized controller integration |
| OPC UA | Information model, secured endpoint, certificate/user trust and explicit read/write subscriptions; not universal point semantics |
| Bluetooth/BLE | Vendor-specific GATT/services and pairing/issuer rights; proximity is not access approval |

Existing primary-source links for these families are in the compatibility matrix.
Additional references reviewed this session:
[KNX](https://www.knx.org/explore-knx/what-is-knx),
[DALI Alliance](https://www.dali-alliance.org/dali/),
[OPC Foundation](https://opcfoundation.org/about/opc-technologies/opc-ua/).
These references establish research scope only; exact models, licensing and gateways
must be selected and tested. No protocol sharing implies full interoperability.

## Extension procedure

1. Select the exact model/API/protocol and ownership boundary; obtain authorized
   fixture/bench documentation. Define only observable/commandable capabilities.
2. Version the wire contract. Specify source ID, timestamp, freshness, correlation,
   duplicate/conflict semantics, trust and location mapping. Never accept scope from
   an untrusted payload as authority.
3. Implement transport/normalization in an adapter; domain permissions remain in
   services. Use an explicit repository method and additive migration only if needed.
4. Supply malformed, duplicate, revoked, wrong-building and reconnect fixtures, then
   an external participant and deterministic oracle. Measure resource limits.
5. Keep simulation labels. Connection or broker acknowledgment is not device health
   or physical confirmation. Document what offline intervals lose.
6. Real commands require reviewed queued/sent/acknowledged/unknown/failed semantics,
   reconciliation and safety evidence (ASTRA-HW-001). Current ports do not implement
   a durable physical command runner. Do not plug live I/O into pure simulators.
