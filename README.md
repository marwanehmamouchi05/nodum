# nodum
Nodum is an AI operating system for smart buildings, combining Ring and AWS to manage access, visitors, businesses, maintenance, emergencies, and intelligent building workflows through agentic AI and policy-based automation.

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
grants access or unlocks doors. Public HTTPS deployment, authenticated linking UI,
and a Ring-confirmed inbound token-delivery adapter are still required for live linking.
