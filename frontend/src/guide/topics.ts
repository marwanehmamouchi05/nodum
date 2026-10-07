import type { Page } from '../pages/shared'

export interface GuideTopic {
  id: string
  question: string
  summary: string
  steps: readonly string[]
  links: readonly { page: Page; label: string }[]
  aliases: readonly string[]
  matchGroups: readonly (readonly string[])[]
}

// Maintained help, not API responses. Links only open existing sections;
// Guide has no access to credentials, live building data or action handlers.
export const topics: readonly GuideTopic[] = [
  {
    id: 'nodum', question: 'What is Nodum?',
    summary: 'Nodum brings building context, device signals and deterministic policy into one operations dashboard. AI can explain and propose; building policy decides what is allowed.',
    steps: ['Start in Overview for incidents, visits, configured integrations and recent activity.', 'Use each operational section to inspect records or deliberately submit an action. This demo uses synthetic data and simulated hardware.'],
    links: [{ page: 'Overview', label: 'Open Overview' }], aliases: ['about nodum', 'what does nodum do'], matchGroups: [['what', 'nodum'], ['about', 'nodum']],
  },
  {
    id: 'dashboard', question: 'How does the dashboard work?',
    summary: 'Overview summarizes the data returned by building APIs. Counts reflect recorded events or configuration, not proof of live physical telemetry.',
    steps: ['Review the incident banner and any connection warnings before relying on counts.', 'Open the building diagram for zones, or follow a metric to its operational section.', 'Refresh building data for a new snapshot. Operator context is prototype role context, not sign-in.'],
    links: [{ page: 'Overview', label: 'Open Overview' }, { page: 'Building', label: 'Inspect building zones' }], aliases: ['overview help'], matchGroups: [['dashboard'], ['overview']],
  },
  {
    id: 'ring-unlinked', question: 'Why does Ring discovery say no linked account?',
    summary: 'Discovery requires a completed Ring account link owned by the signed-in Nodum user. Selecting an operator in the sidebar does not sign you in or claim an account.',
    steps: ['In Integrations, check the signed-in account and use Refresh connection after signing in.', 'If no account is listed, begin linking from Ring and complete the explicit Nodum confirmation. Restart an expired link from Ring.', 'Use an account belonging to the signed-in user. The simulation lab has a separate device catalog and inbox; its seeded account is not proof of a live account link.'],
    links: [{ page: 'Integrations', label: 'Review Ring account status' }], aliases: ['ring account is not linked to this operator', 'no ring account linked', 'ring discovery no linked account'], matchGroups: [['ring', 'no', 'account'], ['ring', 'not', 'linked'], ['ring', 'unlinked']],
  },
  {
    id: 'ring-connect', question: 'How do I connect Ring?',
    summary: 'Ring linking uses the secure backend sign-in and confirmation flow. Live linking also requires a deployed Ring Partner integration; the dashboard cannot create it from an account ID alone.',
    steps: ['Open Integrations and sign in to Nodum from the Ring account panel.', 'Start account linking from Ring, then review and confirm on the Nodum page. Preserve the supplied link parameters.', 'Return to Integrations, refresh the connection and discover devices using the linked account ID. Import a discovered device and choose its physical zone.', 'If live linking is not provisioned, use the separately labeled simulation lab. Never paste AWS or Ring secrets into the Guide or AI Assistant.'],
    links: [{ page: 'Integrations', label: 'Open Ring integration' }], aliases: ['ring setup'], matchGroups: [['ring', 'connect'], ['ring', 'link'], ['ring', 'setup']],
  },
  {
    id: 'ring-scenarios', question: 'How do I run a simulation scenario?',
    summary: 'The Ring simulation lab sends signed synthetic events through the real event-receiving pipeline. Nodum Guide only explains the steps; running a scenario is an explicit action in Integrations.',
    steps: ['Open Integrations and locate Ring simulation lab. The backend must be in simulation mode.', 'Sign in to access the simulation catalog and inbox. Choose a scenario card and press its Run button once.', 'Review Delivery results and Simulation inbox. Received means an event reached the inbox, not that a door opened or an emergency was created.', 'Open Activity for events loaded into this session. Downstream emergency actions still need operator review.'],
    links: [{ page: 'Integrations', label: 'Go to Ring simulation lab' }, { page: 'Activity', label: 'Open Activity' }], aliases: ['run a ring simulation', 'run simulation', 'run a scenario'], matchGroups: [['ring', 'simulation', 'run'], ['simulation', 'run'], ['simulation', 'scenario'], ['scenario']],
  },
  {
    id: 'ring-simulation', question: 'How does Ring simulation work?',
    summary: 'Simulated motion, doorbell, person, package, contact and device-lifecycle signals use the real signed Ring ingestion and persistent inbox path. They do not represent observations from physical devices.',
    steps: ['Follow Signal, Nodum receives, Context & policy, then Action & state in the simulation lab.', 'Signature verification, normalization and duplicate handling happen in the backend.', 'Live mode disables scenario generation. A received signal does not grant access or directly unlock a door.'],
    links: [{ page: 'Integrations', label: 'Explore Ring simulation' }], aliases: ['ring playground'], matchGroups: [['ring', 'simulation'], ['ring', 'simulator'], ['ring', 'playground']],
  },
  {
    id: 'device-unavailable', question: 'Why is my device unavailable?',
    summary: 'Device availability depends on its connector configuration and supported mapping. Imported inventory and an enabled connector are not proof that a physical device is online.',
    steps: ['In Integrations, find the device and use Inspect status & mapping for a snapshot.', 'Check whether its software connector is enabled and its zone mapping fits the device. Doors protect exactly one zone.', 'If the inspection fails, review backend connection and sign-in status. Do not repeatedly submit actions while their outcome is unknown.'],
    links: [{ page: 'Integrations', label: 'Inspect devices and connectors' }], aliases: ['device offline'], matchGroups: [['device', 'unavailable'], ['device', 'offline'], ['device', 'not', 'working']],
  },
  {
    id: 'devices', question: 'How do I add or configure a building device?',
    summary: 'Integrations manages the seeded software connectors and discovered device mappings. The current dashboard supports Ring imports; it does not provide a universal hardware onboarding wizard.',
    steps: ['Enable or disable an existing software connector in Building connectors when appropriate.', 'For Ring inventory, discover a linked account, then use Import & map device and select a physical zone.', 'For a registered device, inspect its status, open Edit zone mapping and deliberately save the chosen zones. This replaces its mapping.', 'Other physical manufacturers require a supported adapter; Guide cannot register or configure hardware.'],
    links: [{ page: 'Integrations', label: 'Open device inventory' }, { page: 'Building', label: 'Review physical zones' }], aliases: ['building connectors', 'configure device'], matchGroups: [['device', 'add'], ['device', 'configure'], ['device', 'mapping'], ['connector']],
  },
  {
    id: 'temporary-access', question: 'How does temporary access work?',
    summary: 'Temporary guest permissions specify allowed zones and a validity window. A permission is evaluated by deterministic access policy; it is not a blanket grant to the building.',
    steps: ['In Visitors, use Invite a temporary guest with the inviter, guest, allowed zone and duration.', 'Review the recorded permission and whether it is future, in its window or expired.', 'Use Access to evaluate a specific person, zone and purpose. Restrictions and emergency policy still apply.'],
    links: [{ page: 'Visitors', label: 'Review guest invitations' }, { page: 'Access', label: 'Open Access' }], aliases: ['guest access'], matchGroups: [['temporary', 'access'], ['guest', 'permission'], ['guest', 'access']],
  },
  {
    id: 'credential-reader', question: 'What does a credential reader do?',
    summary: 'A credential reader submits a credential and requested zone for policy evaluation. In this demo an allowed scan may execute a simulated connector command; a denied scan does not actuate.',
    steps: ['Review the Credential registry in Access. Do not enter credential values into Guide or AI chat.', 'Use Simulate a credential scan with a reader, credential type, value and zone. Business lobby transit may require a journey.', 'Review the returned decision and recorded command evidence. Simulated execution is not a physical door action.'],
    links: [{ page: 'Access', label: 'Review credential workflows' }], aliases: ['credential scans'], matchGroups: [['credential'], ['reader'], ['badge', 'scan']],
  },
  {
    id: 'access', question: 'How does Access work?',
    summary: 'Access evaluates a person, requested zone and purpose against deterministic building policy. AI explanations and Ring signals cannot authorize access.',
    steps: ['Use Check authorization in Access to inspect an explicit policy decision.', 'Read the allowed or denied result and its reason. Session checks are separate from persistent scan and actuator records.', 'A denial is a policy outcome. Do not switch identities or routes to bypass it. Guide cannot grant access or execute commands.'],
    links: [{ page: 'Access', label: 'Open Access control' }], aliases: ['access control', 'permission denied'], matchGroups: [['access'], ['permission', 'denied']],
  },
  {
    id: 'visitors', question: 'How do Visitors work?',
    summary: 'Visitors combines business appointments, check-in, temporary guests and the Atlas Dental journey demo. Scheduling an appointment alone grants no access.',
    steps: ['Create a business appointment for the correct business destination and local appointment time.', 'Check in within the permitted window. The backend validates destination ownership and timing.', 'Review temporary guest permissions separately. The Atlas Dental demo creates real demo records and may enable software simulators when you explicitly start it.'],
    links: [{ page: 'Visitors', label: 'Open Visitors' }, { page: 'Businesses', label: 'Review business destinations' }], aliases: ['appointments', 'visitor check in'], matchGroups: [['visitor'], ['visitors'], ['appointment'], ['check', 'in']],
  },
  {
    id: 'emergencies', question: 'How do Emergencies work?',
    summary: 'The incident register records affected zones, severity, responder assignments and incident history. Deterministic safety policy evaluates access during an active incident.',
    steps: ['Review active incidents and their affected zones before making access decisions.', 'An authorized operator can deliberately report an incident, assign a responder or resolve an incident on Emergencies.', 'Ring flood signals require operator review before entering the emergency workflow. Guide does not report, assign or resolve incidents.', 'This prototype is not a physical alarm or evacuation system. For a real emergency, follow the building emergency plan and contact the appropriate emergency services.'],
    links: [{ page: 'Emergencies', label: 'Open emergency register' }], aliases: ['what happens during an emergency'], matchGroups: [['emergency'], ['emergencies'], ['incident']],
  },
  {
    id: 'activity', question: 'What is the Activity page?',
    summary: 'Activity combines recorded visits, connector commands, credential scans, journeys, incident history, session access checks and Ring events, newest first.',
    steps: ['Read the timestamp, source, event, available location and outcome together.', 'Ring events appear after discovery or a simulation run in the current session. Some API responses do not include device or location information.', 'Access checks are session-only. Snapshot outcomes do not establish a current access grant or live device status.'],
    links: [{ page: 'Activity', label: 'Open operational timeline' }], aliases: ['timeline', 'recent activity'], matchGroups: [['activity'], ['timeline']],
  },
  {
    id: 'simulation-badge', question: 'What does a simulation badge mean?',
    summary: 'A Simulation label marks synthetic signals, software devices or simulated actions. It does not claim that physical hardware detected a person, unlocked a door or moved an elevator.',
    steps: ['Simulation events can still create real demo records in the Nodum backend.', 'Distinguish delivery receipt, policy decisions and recorded simulated execution.', 'Use synthetic data only. Review the label and state before describing the demo to others.'],
    links: [{ page: 'Integrations', label: 'Review simulation labels' }, { page: 'Activity', label: 'Review event outcomes' }], aliases: ['simulation labels'], matchGroups: [['simulation', 'badge'], ['simulation', 'label'], ['simulated', 'mean']],
  },
  {
    id: 'ai-unavailable', question: 'Why is AI or Bedrock unavailable?',
    summary: 'AI may be disabled or unable to reach its model because of credentials, permissions, region/model configuration, service errors or incorrect system time. A generic outage message does not identify the cause.',
    steps: ['Use Nodum Guide for setup and workflow help while AI is unavailable. Guide does not need AWS or inspect live state.', 'An operator should check system UTC, the backend AWS credential chain, model/region configuration and AI enablement. Never share keys or tokens here.', 'Previously returned policy results are snapshots. Any preserved proposal still requires explicit review and confirmation; Guide never executes it.', 'Retry AI only when you choose to send another request. There are no automatic Guide inference calls.'],
    links: [{ page: 'AI Assistant', label: 'Open AI Assistant' }], aliases: ['ai offline', 'bedrock offline', 'bedrock is unavailable', 'ai is disabled'], matchGroups: [['bedrock'], ['ai', 'unavailable'], ['ai', 'offline'], ['ai', 'disabled']],
  },
  {
    id: 'backend-connection', question: 'How do I troubleshoot backend connection problems?',
    summary: 'Connection warnings mean some building records may be missing or stale. Nodum Guide remains local help; it cannot restore a connection or verify server health.',
    steps: ['Check that the backend is running and the frontend is configured for the correct API address.', 'Review Connection details in the dashboard. For separate frontend/API origins, the operator should verify allowed origins, credentials and trusted-origin configuration.', 'For sign-in or authorization failures, use the existing sign-in flow. Do not weaken authentication or cookies to work around errors.', 'Once connectivity is restored, refresh building data. Before retrying a timed-out write, inspect records: the original action may have completed.'],
    links: [{ page: 'Overview', label: 'Review dashboard connection details' }, { page: 'Integrations', label: 'Review account status' }], aliases: ['cannot reach nodum', 'backend offline', 'connection failed'], matchGroups: [['backend'], ['connection', 'problem'], ['connection', 'failed'], ['network'], ['cannot', 'reach']],
  },
]

export const pageHelp: Record<Page, { summary: string; next: readonly string[]; suggestions: readonly string[] }> = {
  Overview: { summary: 'An operational snapshot of safety, visits, integrations and recent events.', next: ['Review the incident banner and connection warnings.', 'Open a metric or zone for detail; use Activity for the recorded sequence.'], suggestions: ['dashboard', 'nodum', 'activity', 'simulation-badge'] },
  Building: { summary: 'Zones, people and maintenance responsibilities for this building.', next: ['Inspect the zone diagram and its restrictions.', 'Review people and active work orders before evaluating access.'], suggestions: ['dashboard', 'devices', 'access', 'nodum'] },
  Visitors: { summary: 'Appointments, check-ins, guest permissions and the visitor journey demo.', next: ['Review appointment time and destination before checking in.', 'Use the invitation form for temporary guests; starting the demo creates records.'], suggestions: ['visitors', 'temporary-access', 'access', 'simulation-badge'] },
  Businesses: { summary: 'Business destinations and their appointment records.', next: ['Identify the correct business and destination zone.', 'Open Visitors to manage appointments for that business.'], suggestions: ['visitors', 'access', 'dashboard', 'nodum'] },
  Access: { summary: 'Deterministic authorization checks, credential scans and recorded outcomes.', next: ['Check a specific person, zone and purpose.', 'Review the policy reason before deliberately running a simulated scan.'], suggestions: ['access', 'temporary-access', 'credential-reader', 'simulation-badge'] },
  Emergencies: { summary: 'The incident register, affected zones, responders and safety-policy workflow.', next: ['Review active incidents and affected zones.', 'Use the existing operator controls to report, assign or resolve only when appropriate.'], suggestions: ['emergencies', 'access', 'activity', 'backend-connection'] },
  Integrations: { summary: 'Ring linking, the simulation lab, software connectors and device mappings.', next: ['Check the signed-in account before attempting Ring discovery.', 'For a demo, use a labeled simulation scenario and inspect delivery results.'], suggestions: ['ring-connect', 'ring-scenarios', 'device-unavailable', 'ring-unlinked'] },
  Activity: { summary: 'A timeline of signals, visits, policy decisions and recorded outcomes.', next: ['Compare timestamps, source, location and outcome.', 'Follow the related operational section to investigate; the timeline does not execute actions.'], suggestions: ['activity', 'simulation-badge', 'ring-simulation', 'access'] },
  'AI Assistant': { summary: 'Optional Bedrock assistance alongside built-in, deterministic help.', next: ['Choose Nodum Guide for local setup help without an AI request.', 'Choose AI assistance for an explicit model request; review any proposal before confirming it.'], suggestions: ['ai-unavailable', 'nodum', 'backend-connection', 'access'] },
}
