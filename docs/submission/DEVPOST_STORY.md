# Nodum

Building context for every arrival.

## Inspiration

A doorbell signal is only the beginning of a building workflow. A manager still needs to know who is expected, which unit or business they are visiting, and what action the operator is authorized to take. Residents and businesses need simple ways to arrange visits without seeing each other's private information.

I built Nodum to connect these everyday tasks in one permission-controlled product.

## What it does

Nodum gives building administrators, managers, residents and business tenants their own workspaces. Administrators configure the building and delegate responsibility. Residents schedule visitors, reopen visit records, report maintenance issues and read relevant notices. Business teams manage reception and bounded staff workflows. Managers review arrivals, maintain operational records and see activity in building context.

The building view shows configured floors, apartments, businesses and device locations. It represents configuration and authorized records, rather than claiming a live measured digital twin.

## How Ring is used

Nodum imports official Ring Developers Playground events into its hosted, scoped Ring inbox. The backend discovers the sandbox device and reads its documented event-history API. I verified one device and two on-demand live-view records arriving in Nodum on AWS. Manager Security and Activity label their source as Official Ring sandbox. The dated evidence persists after token expiry and app restart; it does not claim a continuously connected device. The temporary credential stays on the server and is never returned to the browser or stored as a customer-linked account. No physical camera is required for this sandbox workflow.

The arrival demonstration uses a separately labeled Nodum custom simulator. Its signed synthetic motion, doorbell and person events pass through signature verification, normalization, persistence and scoped operator review. These synthetic events are not presented as vendor-origin webhook deliveries. Official Playground history imports and custom event replay are distinct evidence paths. On-demand records are labeled live view, not motion or an identified visitor.

A Ring signal does not establish visitor identity, select a destination or unlock a door. The manager reviews the expected visit and explicitly records the arrival.

## How AWS is used

Amazon Bedrock, through the Boto3 Converse API and Amazon Nova, interprets a question and requests bounded application tools. I verified a real Bedrock response and a successful scoped Manager operations tool call during submission preparation.

The assistant receives authorized context. Write tools produce typed proposals; the user must confirm before backend authorization and policy are checked again. AI explanations are not security decisions. Ordinary forms and the local Guide remain usable when the provider is unavailable.

## How I built it

The product uses React and TypeScript, a FastAPI backend and SQLite persistence. Sessions, exact-origin CSRF protection and resource permissions constrain application access. The judge package serves the interface and APIs from one HTTPS origin on AWS EC2, with a separate persistent synthetic database and private reviewer passwords. Hosted role boundaries, signed simulation, real Bedrock tool use and persistence after a full server reboot were independently checked. The server uses a restricted IAM role rather than a stored AWS access key.

Automated tests cover product workflows, scope boundaries, Ring signature/replay behavior, persistence and failure handling. External service verification is recorded separately from mocked regression tests.

## Challenges and lessons

I learned to distinguish a configured integration from one that actually responds. Bedrock worked on the development computer while the hosted service returned unavailable because the deployment lacked the same credential configuration. Restoring configuration and verifying a real request are separate steps; a hosting outage can delay activation.

I also connected official Ring Playground history to durable, permission-scoped application context while keeping it separate from the custom signed-event simulation. This made the demo's claims more precise and kept temporary sandbox tokens out of customer account-linking flows.

Recent scenario work corrected future event timestamps and delayed Manager refresh so newly generated signals appear promptly and in the right order.

## What is next

Complete production Ring account linking and vendor-origin webhook verification, evaluate supported building hardware, and validate the product with real building teams. Physical credentials, automatic door control and Nodum Edge are not verified capabilities of this demonstration.

## Verification note for final submission

The approved 2:55 video is published as an unlisted YouTube link and saved in the Devpost draft. The AWS-hosted judge installation has passed real inference and reboot checks. Official Ring discovery in the video is earlier sandbox evidence; it does not claim production linking or vendor-origin webhook delivery. Final owner review and submission remain pending.
