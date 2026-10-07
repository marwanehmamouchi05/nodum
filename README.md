# Nodum

Nodum brings building configuration, daily operations, resident services and business tenants into one permission-controlled product. Building teams manage visitors, maintenance and notices; occupants see only information relevant to them.

**Ring supplies arrival/security signals. Nodum adds building context, authorized workflows and deterministic policy.** Signed events are normalized and persisted for review. Ring does not identify a visitor, determine their destination or unlock a door. AI assists through authorized context and confirmed typed actions; it is not the security authority.

## Run the scoped product demo

With backend dependencies installed in backend/.venv and frontend dependencies installed with npm ci, open two PowerShell terminals:

```powershell
cd backend
.venv/Scripts/python.exe demo_product.py --start
```

```powershell
cd frontend
$env:VITE_API_BASE_URL='http://127.0.0.1:8770'
$env:VITE_API_USE_CREDENTIALS='true'
npm run dev -- --host 127.0.0.1 --port 5178 --strictPort
```

Open **http://127.0.0.1:5178**, choose Sign in, and use a synthetic account printed by the launcher. demo-presenter has genuine Admin, Manager, Resident and Business roles and a workspace selector. Single-role accounts demonstrate narrower boundaries. The disposable demo never opens the audited runtime database.

**Real versus simulated:** scoped authorization, accounts, visitor/maintenance/notices workflows, persistence and the signed Ring pipeline are implemented. This demo explicitly uses synthetic Ring events and local Guide fallback. Ring cloud and Bedrock integrations exist; live linking/delivery, physical hardware and real AWS inference are not verified by this demo. Nodum Edge is **Not installed**. Logical visitor authorization does not automatically create physical access.

## Architecture and first run

React/TypeScript → FastAPI → session-derived permissions and ownership → scoped services → SQLite. Ring enters through a signed event inbox. AI proposals pass confirmation and fresh authorization before execution.

- **Admin / Owner:** configuration and delegation; private operations require separate grants.
- **Manager:** operations within delegated authority.
- **Resident:** personal unit, visitors, maintenance, access and notices.
- **Business Admin / Staff:** their business; bounded delegation and personal Staff workflows.

A scoped first installation remains empty. Secure Admin provisioning requires a new, explicitly selected database and rejects audited backend/nodum.db. See [startup and first install](docs/product-release.md#local-startup-and-first-install). The legacy_demo Amazon compatibility path remains separate.

## Review and demonstrate

- [Architecture, startup, security, tests and limitations](docs/product-release.md)
- [Amazon clicks and investor walkthrough](docs/demo-playbook.md)
- [Final Phase F review report](docs/phase-f-release.md)
- Foundations: [authorization](docs/phase-a-authorization.md), [hierarchy](docs/phase-b-structure.md), [Admin](docs/phase-c-admin.md), [Manager](docs/phase-d-manager.md), [Resident](docs/phase-e1-resident.md), [Business](docs/phase-e2-business.md)
- Details: [Ring](docs/ring-integration.md), [AI](docs/agent-layer.md), [connectors](docs/building-integrations.md), [auth](docs/authentication.md), [persistence](docs/persistence.md), [deployment preparation](docs/deployment.md)

Historical connector examples describe legacy software-simulated journeys, not a physical bridge for configured units/businesses. These instructions perform no deployment.