# Nodum demo video — target 2:50

Record only the final verified application. Use synthetic records. No API keys, provider-account screens with visible tokens, passwords or real personal data should appear.

## 0:00–0:25 — animated scenario

Visual: a simple mixed-use building; a resident schedules a visitor; a doorbell signal reaches a manager; the expected visit provides context. Keep animation illustrative and avoid depicting an automatic unlock.

Narration: “A visitor arrives at a building. The doorbell can tell us there is activity, but the manager still needs context: who is expected, where they are going, and what to do next. Nodum connects building teams, residents and businesses around that everyday workflow.”

## 0:25–0:45 — show the real application

Show the building, then Resident → Visitors. Schedule a synthetic visitor with a current time window and show the saved visit record.

Narration: “A resident schedules a visit for their own unit. The visit is saved with its destination and time window, without exposing another tenant's information.”

## 0:45–1:10 — prove official Ring runtime use

Manager → Demo Mode → Verify official Ring API. Use a fresh private server-side Playground token during recording. Show the returned sandbox device name inside Nodum. Never film the token field in the Ring console.

Narration: “Here Nodum calls the official Ring device API using the Ring Developers Playground. The response appears inside our app. This verifies sandbox discovery; it is separate from account linking and webhook delivery.”

## 1:10–1:45 — demonstrate arrival review

Run Visitor arrives. Show the saved signals in Manager → Visitors or Security. Review the scheduled visit, manually mark arrived, then open Activity.

Narration: “For the arrival workflow, these clearly labeled synthetic events use our signed event pipeline. The manager sees the entrance signal alongside expected visits. A signal does not identify the visitor or unlock a door. The operator reviews the person and records the arrival, which appears in Activity.”

## 1:45–2:15 — demonstrate real AWS assistance

Close Demo Mode. Ask Nodum: “Who is expected today?” Show the real Bedrock response. Use a read-only question so recording does not depend on a speculative proposal.

Narration: “Amazon Bedrock and Amazon Nova help the manager ask questions about authorized building information. Nodum supplies scoped tools. The assistant explains; backend permissions and policy remain in charge. Proposed changes require confirmation.”

## 2:15–2:40 — show who benefits

Briefly show Business Home and Resident Maintenance. Keep this section short; do not tour every menu.

Narration: “Businesses get their own reception view. Residents can report maintenance and follow relevant notices. Administrators configure the building and delegate responsibility, while each workspace stays within its granted scope.”

## 2:40–2:50 — closing

Return to Manager Overview and the building.

Narration: “Nodum turns disconnected building tasks into a clear, reviewable workflow. Building context for every arrival.”

## Recording and editing checklist

1. Fresh synthetic data and current visit windows; rehearse once.
2. Verify Ring token and Bedrock immediately before recording.
3. Record the browser only at a readable desktop size; hide personal tabs and notifications.
4. Capture the real interface before producing the animation so the story matches working behavior.
5. Use the 25-second intro, application footage and English narration/captions. Aim for 2:50; stay strictly below 3:00.
6. Preserve the distinction between official API discovery and custom signed-event simulation in both narration and captions.
7. Review the exported video with sound and captions. Confirm no credentials, unsupported hardware claims or unreadable screens.
8. Upload publicly to YouTube/Vimeo, verify signed-out playback, then place the link in Devpost.

The animation is a planned asset; this document is not a claim that a final animation or video has been produced.
