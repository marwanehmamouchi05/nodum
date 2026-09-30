# Nodum frontend

React + TypeScript building operations interface. No new runtime dependencies.

## Local startup

Copy `.env.example` to `.env.local` and configure `VITE_API_BASE_URL` (default
`http://127.0.0.1:8000`). Run `npm ci`, then `npm run dev` in this directory.
Set the backend `CORS_ALLOWED_ORIGINS` to the exact frontend origin, for example
`http://localhost:5173`. Origins using `127.0.0.1` and `localhost` are different.

For an authenticated cross-origin gateway, set `VITE_API_USE_CREDENTIALS=true`
and configure backend `CORS_ALLOW_CREDENTIALS=true` with an explicit allowed
origin. This does not implement authentication or the Ring session adapter.
Never put AWS/Ring secrets in Vite variables: they are public build-time values.

Production API URL: `https://nodum-production.up.railway.app`. Rebuild after
changing Vite variables, and deploy the read-only `/building/catalog` endpoint
with the backend. The UI was verified against an isolated local SQLite database;
no production data or deployment was changed.

## Verification

- `npm run lint`
- `npx tsc -b --pretty false`
- `npm run build`
- From `backend`: `.\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_frontend_catalog.py tests/test_building_integrations.py --repository-backend=sqlite`

All nine screens were inspected at 390, 820 and 1440 pixels. Browser checks covered
appointment creation/check-in, guest invitations, policy allow/deny, denied NFC
scan, incident creation/assignment/resolution, device status/mapping, Ring
unavailable, AI disabled, backend disconnection/recovery, and both Atlas Dental
paths. The simulated journey produced four actuator events and two confirmed
transitions; the manual path produced no actuator events.

## Boundaries

- Simulator actions and explicit location confirmations are labeled. Ring discovery
  is real API integration code, but live linking requires the backend session and
  token-delivery adapters. No connected Ring hardware is claimed.
- AI text is explanatory. Structured policy results and confirmation-required
  proposals are separate. The existing chat API is single-turn; conversation
  display is local to the Assistant screen.
- Access checks are browser-session history, while scans/actions/journeys/incidents
  persist in the backend. Data refresh is manual; status is a snapshot.
- Generic operations currently use a prototype operator context, not sign-in.
  Deploy behind an authenticated gateway. This UI does not change access policies.
- Device mappings replace the selected zone set. Forms currently support one
  destination per guest invitation and one affected zone per new incident.
- Google Fonts are optional; system sans-serif fallbacks apply offline.
