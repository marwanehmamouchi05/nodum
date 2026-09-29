# nodum
Nodum is an AI operating system for smart buildings, combining Ring and AWS to manage access, visitors, businesses, maintenance, emergencies, and intelligent building workflows through agentic AI and policy-based automation.

See [the access and emergency policy](docs/access-policy.md) for the current
in-memory architecture, policy precedence, test commands, and deployment limits.

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
