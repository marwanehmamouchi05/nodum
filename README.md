# nodum
Nodum is the intelligent operating system for buildings, combining Ring sensing, AWS AI orchestration, and deterministic policies for visitors, businesses, maintenance and emergencies.

The [building connector and journey foundation](docs/building-integrations.md)
adds persistent device mappings and software simulators for access control,
credentials, elevators and wayfinding. The Atlas Dental backend demo verifies
an appointment before simulated entrance, Floor 1 and navigation actions.
Without connectors it reports manual actions. Other manufacturers are not yet
integrated. Ring has a documented Partner API adapter; a live linked account
and event delivery still require separate verification.

See [the access and emergency policy](docs/access-policy.md) for the current
repository architecture, policy precedence, test commands, and deployment limits.

The backend supports guest invitations, business appointments/check-in, and
deterministic emergency incidents with responder assignments and resolution.
Emergency access decisions use explicit policy and work orders, never AI.
Demo maintenance areas include the water utility room and elevator machine room;
no emergency is active at startup.

The optional [Nodum agent layer](docs/agent-layer.md) uses Amazon Bedrock Converse
in eu-north-1 (development model: eu.amazon.nova-2-lite-v1:0) to interpret requests
and call safe tools. AI explanations cannot authorize access. Mutations require
review and confirmation and still pass through existing services. Bedrock outages
do not disable the normal building APIs.

SQLite persistence is enabled by default. DATABASE_URL=sqlite:///./nodum.db stores
data in backend/nodum.db; startup initializes the schema and inserts missing demo
records without resetting existing data. See [database setup and persistence](docs/persistence.md)
for configuration, migrations, backups, and verification commands.

The [Ring integration](docs/ring-integration.md) provides signed webhook ingestion,
an auditable SQLite inbox, encrypted OAuth token storage, nonce-based linking
services, and device discovery. Flood events can enter the existing emergency
workflow after an authenticated operator confirms the affected zone. Ring never
grants access or unlocks doors. [Persisted login and Ring continuation](docs/authentication.md)
now provide secure sessions and explicit account-link confirmation. Deployment configuration
and a Ring-confirmed inbound token-delivery adapter remain required for live linking.

See [backend deployment preparation](docs/deployment.md) for environment-based
startup, production CORS, optional Ring startup validation, Docker build/run
commands, persistent SQLite volumes, and HTTPS ingress requirements. Nothing is
deployed automatically. Production building APIs require a manager session and
CSRF protection; development APIs remain a synthetic-data demo. This is not tenant RBAC.

See the [privacy/security audit](docs/privacy-security.md), [production checklist](docs/production-readiness.md),
and [repository/licensing strategy](docs/repository-strategy.md) before submission or deployment.
