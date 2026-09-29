# Nodum agent layer

The optional agent interprets natural-language requests, resolves names, reads
building context, proposes actions, and explains service results. It never
authorizes entry. Only the existing deterministic access service/engine decides
whether a person may enter a zone at the time of the check.

## Architecture

- A lazy Bedrock adapter calls the AWS Converse API with a fixed tool registry.
  It uses boto3's standard credential provider chain; no credential values are
  embedded in code, returned to clients, or passed to the model.
- The orchestrator validates model tool requests, limits the conversation to five
  model calls and twelve tools, and returns structured service results separately
  from model-generated explanation. Tools are sequential. AWS calls use a
  three-second connection timeout, 25-second read timeout, and two total attempts.
- The adapter and SDK are initialized only when an agent request needs inference.
  Importing FastAPI, generating OpenAPI, and calling normal APIs need no Bedrock
  availability or AWS credentials.
- Read tools delegate to existing services or defensive repository reads. Write
  tools only produce proposals. No business rules are reimplemented in the agent.
- The application owns a bounded, locked in-memory pending-action store. It stores
  only short-lived proposals, not copies of building entities.
- An explicit confirmation endpoint consumes a proposal once and invokes the
  existing domain service with its exact stored arguments and fresh server time.
  Service validation runs again against current state. Confirmation itself needs
  no AI and is not in the model's tool registry.

No Bedrock Agents/AgentCore resources, Lambda functions, external agent framework,
database, deployment, or hardware integration are required for this implementation.

## Configuration

Install the backend requirements in the project virtual environment. The new AWS
SDK dependencies are pinned alongside the existing requirements.

    AWS_REGION=eu-north-1
    BEDROCK_MODEL_ID=eu.amazon.nova-2-lite-v1:0
    NODUM_AI_ENABLED=true

These are also the development defaults. Set NODUM_AI_ENABLED=false to disable
inference without affecting normal APIs or confirmation of an existing proposal.
AWS_DEFAULT_REGION is the region fallback when AWS_REGION is unset.

Use an AWS profile/SSO session, workload role, or another supported SDK credential
provider. AWS_PROFILE can select a profile. The application does not read or print
credential files and never overrides the credential chain with explicit keys.
Credential setup and Bedrock IAM/model permissions must exist in the environment
running the backend. Some credential methods may require their own SDK extras.

Environment variables are read at agent-request time. To use the repository .env
file during local development, run from backend:

    .\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file ../.env --reload

Never commit the real .env file. Without --env-file, export variables in the
backend process environment; the application does not load .env implicitly.

The adapter follows AWS documentation for
[client-side Converse tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html)
and the [boto3 credential chain](https://docs.aws.amazon.com/boto3/latest/guide/credentials.html).

## Tools

| Tool | Behavior |
| --- | --- |
| find_people | Search IDs/names; includes role and resident guest-zone authority |
| find_zones | Search zone IDs/names, type and floor |
| find_businesses | Search businesses and destination IDs |
| list_work_orders | Read work orders, optionally by contractor |
| list_appointments | Read appointments, optionally by visitor/business |
| list_active_emergencies | Read active incidents |
| check_access | Call the current deterministic access service |
| invite_guest | Propose arguments for the existing guest invitation service |
| create_appointment | Propose arguments for the existing appointment service |
| check_in_visitor | Propose arguments for the existing check-in service |

There are no tools for granting arbitrary permissions, changing roles/work orders,
resolving emergencies, confirming actions, running code, accessing credentials,
or fetching arbitrary URLs. Unknown tools and extra input fields are rejected.
The model cannot supply the clock or force an access decision.

Read searches default to 20 records and cap at 100. Emergency context caps at 100;
results indicate truncation. Large tool output is not forwarded to the model.

## API

POST /agent/chat:

    {
      "message": "Can Ahmed access the machine room?",
      "actor_id": "resident-1"
    }

actor_id is optional for read requests. The response contains:

- status: completed, limited, or unavailable.
- explanation: model-generated prose, always non-authoritative.
- explanation_is_authoritative: always false.
- tool_results: server-produced tool names, statuses, and structured results.

For access questions, clients must use the allowed/reason fields of a successful
check_access tool result, never parse the explanation as permission. No access
decision is implied when no successful check_access result exists. A result is a
snapshot, not a door-unlock command; physical entry requires a fresh policy check.

Missing credentials, denied/throttled/timed-out Bedrock calls, missing SDK, and
disabled inference return HTTP 503 with a sanitized unavailable response.
Malformed/truncated model responses or loop limits return limited. Previous tool
results and proposals are retained in the response even when a later model call
fails. No sensitive write has run merely because a proposal was created.

Each chat request is stateless. To answer a clarification, include the original
request plus the additional details in the next message. Raw conversation/system
history and model selection cannot be supplied through the request body.

### Review and confirmation

A write-tool result has status confirmation_required and includes a pending
action with id, tool, exact arguments, actor_id, created_at and expires_at. Display
those server-produced fields for review. A proposal is not a successful invitation
or check-in and is not a guarantee that domain validation will pass.

POST /agent/actions/{action_id}/confirm:

    {"actor_id": "resident-1"}

The endpoint does not accept replacement arguments. The proposal expires after
five minutes; repeated/concurrent confirmations cannot repeat the write.
An action is consumed before execution, including domain failures, so failed
actions require a new proposal. This is at-most-once consumption in one process,
not durable exactly-once delivery. Repeated identical pending proposals are
deduplicated for that actor. The store retains at most 1,000 unexpired actions.

The agent requires inviter ID to match the request actor. Agent appointment
creation requires an existing manager actor. Check-in must match the request
visitor ID or be confirmed by a manager. These capability checks supplement,
and never replace, the existing services' identity, zone, time, and policy rules.
They do not change the normal domain API contracts.

## Initial scenarios

- “Can Ahmed access the machine room?”: find person/zone, call check_access,
  explain the returned decision. Active emergency restrictions still apply.
- “I have an appointment with Atlas Dental.”: resolve the business and visitor,
  find the appointment, ask for missing identity details, then propose check-in.
  Only a confirmed valid check-in creates a destination-scoped permission.
- “What emergencies are currently active?”: read active incidents.
- “My guest is coming to my floor.”: inspect the actor's guest-zone authority,
  ask for missing guest/destination details, then propose an invitation.

Names, descriptions, and user messages are treated as untrusted context. The
system prompt instructs the model to clarify ambiguity and never evade denials.
The tool allowlist and confirmation boundary enforce the write restrictions
independently of whether the model follows those instructions.

## Verification and limits

Tests use mocked Converse responses and a mocked SDK client. They cover the
initial scenarios, SDK configuration, model/tool validation, outage isolation,
confirmation expiry/concurrency, service denials, and engine precedence.
No paid/live Bedrock inference is performed by the automated suite.

Model understanding and prose accuracy are not proven by mocked conversations;
live evaluation with the configured model is still needed. Explanations can
hallucinate or misstate a denial; the structured service result is authoritative.

Caller authentication and tenant-scoped authorization are still absent from
Nodum. actor_id is a client assertion, not proof of identity. Confirmation is an
explicit intent boundary, not authentication. Read tools expose building/person/
appointment context to the caller and to AWS; keep this development API private
until identity, privacy scoping, and rate limits are implemented.

Tool/model counts and timeouts bound each request, but there is no account-wide
rate limit or cost budget in application code. Multiple requests may still incur
cost or exhaust worker threads. Proposals and building state are process-local
and disappear on restart; use one backend process for this prototype.
