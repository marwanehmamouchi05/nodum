# Hardware compatibility and evidence

Reviewed 2026-10-15. Status applies to Nodum, not a manufacturer's advertised
capability. No device is HARDWARE VERIFIED by this session. Public documentation
research is not a tested adapter. Firmware, model, license and deployment must be
checked for the selected pilot equipment. No network scans or physical commands ran.

| Family / category | Connection, authentication and licensing | Available scope / feasibility | Nodum status / evidence | Pilot dependency and limitation |
|---|---|---|---|---|
| Ring cameras / doorbells | Cloud; authorized account, encrypted tokens, signed delivery; provider approval/account required | Device/event APIs; account ownership boundaries; no visitor identity inference | SIMULATION TESTED; `test_ring.py`, `test_ring_simulation.py`, product release tests; documented adapter exists | Live delivery/linking unverified; confirmed inbound contract and authorized account required |
| Local door, reader, elevator, light/sign simulators | In-process only; server-owned registry, deterministic policy | Simulated commands, credential fingerprints and recorded route/floor requests | SIMULATION TESTED; `app/integrations/building.py`, `test_building_integrations.py` | No manufacturer compatibility, real relay or elevator movement demonstrated |
| ONVIF IP cameras / VMS, video intercoms | Local IP; device account and supported profiles; model-specific firmware/license | Profile T video and conditional controls; M metadata/events; access profiles A/C/D have distinct responsibilities | RESEARCHED [ONVIF profiles](https://www.onvif.org/profiles/) | Need exact conformant device/profile, credentials, test VLAN; video alone is not identity or intercom call integration |
| RTSP streaming | Local/network; server-specific auth/TLS and permitted camera account | Media session control; separate from access permissions and analytics | RESEARCHED [RTSP standard](https://www.rfc-editor.org/info/rfc7826/) | Version/codec/TLS support varies; not a discovery or door-control API |
| OSDP readers, RFID/NFC readers, keypads | Reader-panel serial link; Secure Channel keys and explicit commissioning; integrator/spec access requirements | Peripheral communication; requires controller/gateway integration, not a generic cloud endpoint | RESEARCHED [SIA OSDP](https://www.securityindustry.org/industry-standards/open-supervised-device-protocol/) | Need licensed/spec-compatible implementation and bench reader/controller; verify secure mode rather than assume it |
| Wiegand legacy badge/keypad links | Electrical reader-controller interface; use existing supported panel integration | Credential signaling, not a complete authenticated building API | RESEARCHED [SIA comparison](https://www.securityindustry.org/2022/10/06/dont-be-intimidated-by-osdp/) | Do not connect GPIO/USB readers directly to an operational door; existing panel/vendor boundary needed |
| MQTT contact, motion, environment and energy sensors | Broker TCP/TLS; per-device identities, topic ACLs, broker entitlement/deployment | Pub/sub transport; payload semantics, discovery and command models are application-specific | PROTOCOL TESTED for explicit MQTT 3.1.1 contact contract only; Paho 2.1.0 + aMQTT 0.11.3 loopback fixture, SQLite persistence and scoped Manager Activity | See mqtt-contact.md. No physical device, deployed broker TLS/ACL, general discovery or universal payload support. |
| BACnet HVAC, lighting and building automation | IP/MS-TP or BACnet/SC; SC certificate infrastructure; network/point permissions and vendor engineering tools | Object/property reads, events and supported writes; controller point lists required | RESEARCHED [BACnet/SC](https://bacnet.org/wp-content/uploads/sites/4/2022/06/B-SC-Whitepaper-v15_Final_20190521.pdf) | Start read-only; exact PICS/points and bench controller required; no life-safety writes |
| Modbus meters, relays and HVAC gateways | TCP or serial; security varies; TLS variant exists; vendor register documentation required | Register/coil reads and writes with device-specific scaling/address maps | RESEARCHED [Modbus Security](https://www.modbus.org/news/modbus-security-new-protocol-to-improve-control-system-security) | No device semantics inferred from register numbers; license/spec access to confirm; isolated read-only fixture first |
| Matter smart locks, lights, switches and sensors | IP, commissioned fabric/controller; device attestation and operational credentials; ecosystem/certification requirements | Supported device types/clusters; bridges may expose other networks | RESEARCHED [CSA Matter](https://csa-iot.org/all-solutions/matter/) | Commissioning credentials/controller and exact cluster support required; Bluetooth commissioning is not a BLE lock API |
| Zigbee lights, relays and sensors | Coordinator/mesh, network security and device commissioning; product/stack requirements | Device/cluster-dependent commands and attributes | RESEARCHED [CSA Zigbee](https://csa-iot.org/all-solutions/zigbee/) | Need supported coordinator/bridge and device quirks; not interchangeable with Matter |
| Z-Wave locks/sensors | Controller, regional radio configuration, secure inclusion; certification/SDK terms to verify | Supported command classes vary by product | RESEARCHED [Z-Wave specification](https://z-wavealliance.org/development-resources-overview/specification-for-developers/) | Exact controller/product and security inclusion needed; no radio implementation installed |
| BLE mobile access / smart locks | Local radio, pairing/bonding or vendor authorization; SDK/mobile entitlement may be needed | GATT services are device/application-specific | RESEARCHED [Bluetooth GATT](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-61/out/en/host/generic-attribute-profile--gatt-.html) | Do not infer lock operations from proximity or a generic Bluetooth label |
| NFC mobile credentials / badges | Reader/card interaction; issuer keys, supported credential application, mobile platform entitlement | Credential exchange; identity/authorization remain separate | RESEARCHED [NFC access](https://nfc-forum.org/learn/use-cases/access-control/) | Requires authorized credential issuer/reader integration; tag UID is not a secure credential |
| Axis door panels, locks, barriers and intercom equipment | Local documented VAPIX services; model-specific accounts/permissions, firmware and licenses | Access-control service can expose supported controller/peripheral models | RESEARCHED [Axis physical access](https://developer.axis.com/vapix/physical-access-control/) | A bench controller and exact firmware/API required. Gate/barrier/intercom functions depend on connected equipment |
| Vendor REST APIs / webhooks / SDKs; elevators and parking | Vendor-specific local/cloud authorization, signed events, license/partner contracts | Only documented event/command functions; no common universal command set | RESEARCHED feasibility class only; choose an exact vendor before implementation | BLOCKED for actual elevator/parking pilot: no selected model, contract, sandbox or safety-approved bench |

## Existing architecture and next integration

Reuse `ConnectorRegistry`, `CommandContext`, service policy enforcement and scoped
device bindings. Do not add public dynamic adapter loading or arbitrary device URLs.
Current actuator contracts are pure simulator state transformations within database
transactions. Physical I/O must not be inserted into those transactions: uncertain
network outcomes and command replay need durable reconciliation first (ASTRA-HW-001).

The first read-only MQTT contact integration is now protocol tested against a
loopback broker. The fixed topic/payload, explicit device/building binding,
retained-message rejection, timestamp/replay bounds and reconnect behavior are
implemented; see `mqtt-contact.md`. Next, validate real broker TLS/authentication
and per-topic ACLs, then design durable offline delivery and retention before
sustained operational use. No command publication is implemented. Physical contact
sensor acceptance still requires selected equipment, an owner-approved bench and
recorded evidence before any HARDWARE VERIFIED label.

## Real-hardware acceptance procedure

Record model/serial privately, firmware, profile/API/SDK version, entitlements,
approved network and assigned building. Begin with read-only discovery/status.
Compare generated events against actual device behavior; test disconnect/reconnect,
malformed/duplicate delivery and tenant isolation. Keep provider identifiers out of
public logs. Any actuator test needs explicit owner authorization, a dedicated bench,
manual override and defined command/retry semantics. Never test against occupied
building access, alarm, elevator or emergency systems during automated development.


## 2026-10-15 contact-collector evidence update
The read-only contact adapter now exists in `backend/app/integrations/mqtt_sensor.py`. Actual loopback broker messages, retained rejection, duplicate/conflicting IDs, broker restart and resubscription, operator grant revocation, SQLite rollback/restart and scoped Manager activity are tested. Bounded burst: 250 samples in 3.678 seconds; 251 observations persisted including the reconnect sample, latest 100 visible by design. This measures the local fixture, not a production SLA. Hardware remains unverified. Existing device-health labels remain unchanged. See [contract and reproduction](mqtt-contact.md).


## Engineering-foundation evidence update — 2026-10-15

Local verified-TLS broker authentication/topic ACL and independent application
revocation passed at the security checkpoint. A separate external client now
provisions two buildings/devices/accounts through authenticated HTTPS, sends real
MQTT contact messages and verifies durable correlation, isolation, malformed/duplicate
handling and post-broker-restart delivery. No client database access or internal
Nodum imports. Other simulated categories remain component-tested only. Universal
protocol/category research and risk classification are consolidated in
UNIVERSAL_HARDWARE_ARCHITECTURE.md. No physical compatibility label is upgraded.
