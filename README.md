# nodum
Nodum is an AI operating system for smart buildings, combining Ring and AWS to manage access, visitors, businesses, maintenance, emergencies, and intelligent building workflows through agentic AI and policy-based automation.

See [the access and emergency policy](docs/access-policy.md) for the current
in-memory architecture, policy precedence, test commands, and deployment limits.

The backend supports guest invitations, business appointments/check-in, and
deterministic emergency incidents with responder assignments and resolution.
Emergency access decisions use explicit policy and work orders, never AI.
Demo maintenance areas include the water utility room and elevator machine room;
no emergency is active at startup.
