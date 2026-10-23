# Official release baseline

Historical foundation maintenance release: [contact timestamp containment](docs/TIMESTAMP_RELEASE_REVIEW.md),
tag `nodum-contact-timestamp-20261017`. Prior foundation checkpoints remain preserved.

[Dated foundation release baseline](docs/NODUM_RELEASE_BASELINE.md): authoritative GitHub branch,
verification, setup and separate Ring/pilot gates. Earlier reports are historical.

# Nodum

**Hosted hackathon demo:** [Open Nodum](https://nodum.54-173-165-46.sslip.io/app/)
and [watch the 2:55 walkthrough](https://youtu.be/ITCj4CzEHEg).
Private synthetic reviewer accounts are supplied to judges through Devpost.
The October 22 AWS deployment passed scoped login/CSRF checks, signed simulation,
real Bedrock/Nova tool use, and persistence after a full server reboot.
See [hosting and recovery](docs/submission/AWS_HOSTING.md) for the tested scope,
credit-funded availability and remaining Ring integration limits.

Hackathon preparation: [current submission work and owner actions](docs/submission/OWNER_STEPS.md),
[current verification status](docs/submission/STATUS.md), [video script](docs/submission/VIDEO_SCRIPT.md), and [project story draft](docs/submission/DEVPOST_STORY.md).
The optional judge package serves the product at `/app/` on the API origin; see
`tools/package_submission.py` and the documented explicit synthetic installation.
The [official Ring Playground integration](docs/ring-playground.md) now imports sandbox history into the hosted Manager Security and Activity views. Its stored, dated evidence survives token expiry; custom signed arrival scenarios remain separately labeled.

Nodum brings building configuration, daily operations, resident services and business tenants into one permission-controlled product. Building teams manage visitors, maintenance and notices; occupants see only information relevant to them.

**Ring supplies arrival/security signals. Nodum adds building context, authorized workflows and deterministic policy.** Signed events are normalized and persisted for review. Ring does not identify a visitor, determine their destination or unlock a door. AI assists through authorized context and confirmed typed actions; it is not the security authority.

## Run the scoped product demo

Prerequisites: Python 3.13 and Node.js 24. From the repository root, create a new environment and install the pinned dependencies:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
```

Then open two PowerShell terminals:

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

**Real versus simulated:** scoped authorization, accounts, visitor/maintenance/notices workflows, persistence and the signed Ring pipeline are implemented. The hosted judge installation has verified real Bedrock/Nova inference and official Ring Playground history imports. Custom arrival scenarios use separately labeled synthetic events; production Ring linking/webhook delivery and physical hardware remain unverified. The local Guide is available as a fallback. Nodum Edge is **Not installed**. Logical visitor authorization does not automatically create physical access.

## Architecture and first run

React/TypeScript → FastAPI → session-derived permissions and ownership → scoped services → SQLite. Ring enters through a signed event inbox. AI proposals pass confirmation and fresh authorization before execution.

- **Admin / Owner:** configuration and delegation; private operations require separate grants.
- **Manager:** operations within delegated authority.
- **Resident:** personal unit, visitors, maintenance, access and notices.
- **Business Admin / Staff:** their business; bounded delegation and personal Staff workflows.

A scoped first installation remains empty. Secure Admin provisioning requires a new, explicitly selected database and rejects audited backend/nodum.db. See [startup and first install](docs/product-release.md#local-startup-and-first-install). The legacy_demo Amazon compatibility path remains separate.

## Review and demonstrate

- [Developer onboarding and quality checks](docs/DEVELOPER_ONBOARDING.md)
- [Architecture and integration boundaries](docs/ARCHITECTURE_OVERVIEW.md)
- [Independent lab connection contract](docs/DIGITAL_TWIN_INTEGRATION_CONTRACT.md) and [Phase 2 handoff](docs/DIGITAL_TWIN_PHASE2_HANDOFF.md)
- [Measured scalability](docs/SCALABILITY_ASSESSMENT.md) and [security readiness](docs/SECURITY_READINESS.md)

- [Architecture, startup, security, tests and limitations](docs/product-release.md)
- [Amazon clicks and investor walkthrough](docs/demo-playbook.md)
- [Final Phase F review report](docs/phase-f-release.md)
- Foundations: [authorization](docs/phase-a-authorization.md), [hierarchy](docs/phase-b-structure.md), [Admin](docs/phase-c-admin.md), [Manager](docs/phase-d-manager.md), [Resident](docs/phase-e1-resident.md), [Business](docs/phase-e2-business.md)
- Details: [Ring](docs/ring-integration.md), [AI](docs/agent-layer.md), [connectors](docs/building-integrations.md), [auth](docs/authentication.md), [persistence](docs/persistence.md), [deployment preparation](docs/deployment.md)

Historical connector examples describe legacy software-simulated journeys, not a physical bridge for configured units/businesses. These instructions perform no deployment.


Historical engineering milestones: [Phase 1 final report](docs/PHASE1_FINAL_REPORT.md),
[classified closure backlog](docs/PHASE1_CLOSURE_BACKLOG.md) and
[bounded Astra handoff](docs/ASTRA_FINAL_REVIEW_HANDOFF.md). Foundation complete with
external blockers; pilot not approved. [Local proxy/browser procedure](docs/DEPLOYMENT_VERIFICATION.md),
[Ring demo evidence](docs/RING_DEMO_PROCEDURE.md) and [data lifecycle boundary](docs/DATA_LIFECYCLE.md)
record exact tested scope. The [independent review](docs/ASTRA_INDEPENDENT_REVIEW.md) and
[resolution log](docs/ASTRA_RESOLUTION_LOG.md) are complete. The
[readiness decision](docs/PHASE2_READINESS_DECISION.md) permits separately authorized
simulator development on the verified HTTPS/contact boundary; official Ring and
physical pilot readiness remain blocked. No Phase 2 work, merge or deployment occurred.
