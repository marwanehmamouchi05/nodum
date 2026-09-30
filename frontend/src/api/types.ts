export interface Person { id: string; name: string; role: string; guest_zone_ids: string[] }
export interface Zone { id: string; name: string; floor: number | null; zone_type: string; restricted: boolean }
export interface Business { id: string; name: string; destination_zone_ids: string[]; active: boolean }
export interface WorkOrder { id: string; contractor_id: string; description: string; allowed_zone_ids: string[]; active: boolean }
export interface Credential { id: string; kind: string; person_id: string; active: boolean }
export interface Catalog { people: Person[]; zones: Zone[]; businesses: Business[]; work_orders: WorkOrder[]; credentials: Credential[] }
export interface Permission { id: string; person_id: string; allowed_zone_ids: string[]; valid_from: string; valid_until: string; reason: string }
export interface Decision { allowed: boolean; reason: string; permission?: Permission | null }
export interface Appointment { id: string; visitor_id: string; visitor_name: string; business_id: string; destination_zone_id: string; appointment_time: string; access_before_minutes: number; access_after_minutes: number; status: string; created_at: string; checked_in_at: string | null }
export interface Incident { emergency_id: string; emergency_type: string; severity: string; affected_zone_ids: string[]; description: string; status: string; created_at: string; resolved_at: string | null; created_by: string; assigned_responder_ids: string[]; history: { action: string; actor_id: string; at: string; responder_ids: string[] }[] }
export interface Integration { id: string; name: string; kind: string; provider: string; mode: string; enabled: boolean }
export interface Device { id: string; name: string; integration_id: string; provider: string; device_type: string; zone_id: string; capabilities: string[]; connection_status: string; simulated: boolean; external_account_key?: string }
export interface DeviceStatus { device: Device; mapping: { zone_ids: string[] } | null; available: boolean; mode: string; state: { locked: boolean; current_floor: number | null; authorized_floor: number | null; route: string[] } | null }
export interface ActionResult { status: string; simulated: boolean; executed: boolean; decision: Decision; message: string; actuator_event_id: string | null }
export interface Actuator { id: string; device_id: string; command: string; person_id: string; zone_id: string; at: string; executed: boolean; simulated: boolean; message: string; decision: Decision }
export interface Scan { id: string; person_id: string | null; zone_id: string; at: string; kind: string; result: ActionResult }
export interface Journey { id: string; person_id: string; purpose: string; starting_zone_id: string; destination_zone_id: string; appointment_id: string | null; arrival_ring_event_id: string | null; authorized_zone_ids: string[]; current_confirmed_zone_id: string | null; status: string; created_at: string; updated_at: string; route: string[]; steps: { kind: string; zone_id: string; result: ActionResult }[] }
export interface Transition { id: string; journey_id: string; zone_id: string; at: string; simulated: boolean }
export interface ToolResult { tool: string; status: 'success' | 'error' | 'confirmation_required'; data: unknown }
export interface AgentResponse { status: string; explanation: string; explanation_is_authoritative: false; tool_results: ToolResult[] }
export interface RingDevice { id: string; name: string; attributes: Record<string, unknown>; related: Record<string, unknown> }
export interface RingEvent { id: string; event_type: string; received_at: string; occurred_at?: string; signal?: string }
export interface AccessEntry { id: string; at: string; person_id: string; zone_id: string; decision: Decision }
export interface BuildingData { catalog: Catalog; appointments: Appointment[]; permissions: Permission[]; emergencies: Incident[]; integrations: Integration[]; devices: Device[]; journeys: Journey[]; actuators: Actuator[]; scans: Scan[] }
