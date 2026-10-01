# Nodum sessions and Ring linking

This is a small application login for Ring operations. In production, the
operations APIs also require a manager session and CSRF for writes. This coarse
gate is not tenant/resource RBAC: payload actor IDs remain prototype context and
are not reliable audit attribution. The UI operator selector is not a login.
Development mode remains unauthenticated and must use synthetic data only.

## Architecture

The auth service uses the existing Repository contract. Migration **4** adds
auth_users, auth_sessions and auth_throttles, unique username/person indexes,
and an index for the authenticated owner in ring_accounts JSON.
Ring records retain owner_id (building person) and owner_user_id (Nodum user).
Both must match. Legacy claimed records without a user association are not
automatically assigned to a new user.

Passwords use PBKDF2-HMAC-SHA256, 600,000 iterations and independent random
256-bit salts. Passwords are never stored or returned in plaintext. Cookies
contain random 256-bit opaque secrets; only SHA-256 digests are persisted.
Login replaces the pre-login session; logout deletes it. Expiry, inactive users
and missing people fail closed. Five attempts per username and 30 per client IP
per 15 minutes are persisted before password verification. Configure trusted
proxy IPs for correct throttling. Add ingress request rate/body limits.

HTTPS cookies use __Host-nodum_session, Secure, HttpOnly, SameSite=Lax, Path=/,
and no Domain. Local HTTP uses nodum_session. Sessions last eight hours by
default (configurable 1–24); anonymous login sessions last 15 minutes.
No bearer session token is returned in JSON or stored in localStorage.

GET /auth/session returns the public user (or null) and a CSRF token bound to the
HttpOnly cookie. Login, logout, Ring claim and other session-based Ring mutations
require this token in X-CSRF-Token and an explicitly trusted Origin.
Sensitive responses are not cached. The login page disables framing, external
resources and referrer disclosure. Disable/redact Ring query parameters in
reverse-proxy logs as well as keeping application ACCESS_LOG=false.

## Endpoints and browser flow

- GET /auth/login: backend-hosted sign-in/account page.
- GET /auth/session: session bootstrap/context and CSRF token.
- POST /auth/login: username/password JSON with CSRF and Origin.
- GET /auth/me: authenticated public identity, otherwise 401.
- POST /auth/logout: invalidate the current session.
- GET /auth/client.js: first-party login/continuation script.
- GET /ring/link?nonce=...&time=...: render the same page, preserving the query.
  Basic query syntax is checked, but no HMAC matching, freshness decision or
  account claim occurs before authentication.
- POST /ring/link: authenticated, CSRF-protected explicit confirmation.
- GET /ring/accounts: current operator's account IDs/status/environment only.

The user signs in on the same URL, sees the signed-in username, and confirms.
The existing service checks the ten-minute timestamp window and HMAC, durably
reserves both ownership IDs, calls Ring confirmation and completion, and returns
account ID/status only. Ring token encryption remains unchanged.
The browser removes the query from history on success. No arbitrary return URL
is accepted. Expired links must be restarted in Ring. Same-owner retries retain
the reservation; another user cannot take it. Managers/responders remain the
permitted building integration operators. Access policies are unchanged.

The React Integrations screen adds a small sign-in/account panel. Sign-in opens
the backend page; returning users click **Refresh connection**. Discovery still
calls Ring. A completed connection is not live device telemetry.
For separate frontend/API origins on the same site, configure
VITE_API_USE_CREDENTIALS=true, exact backend CORS origins,
CORS_ALLOW_CREDENTIALS=true and AUTH_TRUSTED_ORIGINS.
For unrelated sites, use a same-site domain/reverse proxy; do not weaken cookies
to work around third-party-cookie restrictions. The Ring browser flow runs on
the backend origin and does not depend on React/CORS.

## Railway and provisioning

Set these privately; never put credentials in frontend variables:

| Variable | Requirement |
| --- | --- |
| APP_ENV | production |
| AUTH_PUBLIC_ORIGIN | https://nodum-production.up.railway.app |
| AUTH_SESSION_HOURS | 8 (optional, 1–24) |
| AUTH_BOOTSTRAP_USERNAME | Your chosen username |
| AUTH_BOOTSTRAP_PASSWORD | Unique strong password, 12–128 characters |
| AUTH_BOOTSTRAP_PERSON_ID | Existing operator, e.g. manager-1 |
| DATABASE_URL | Absolute SQLite URL on a mounted volume, e.g. sqlite:////data/nodum.db |
| HOST / PORT | 0.0.0.0 / Railway-provided port |
| ACCESS_LOG | false |
| AUTH_TRUSTED_ORIGINS | Exact frontend origin, if cross-origin sessions are needed |
| CORS_ALLOWED_ORIGINS / CORS_ALLOW_CREDENTIALS | Same exact origin / true, if needed |
| FORWARDED_ALLOW_IPS | Only actual trusted TLS proxy IPs/CIDRs |

Startup applies migrations then optionally provisions one user. Supply all
three bootstrap fields together. Restarting does not duplicate users or reset
passwords; changing the bootstrap password is not password rotation. Remove the
bootstrap variables after provisioning. There is no public registration, reset,
MFA or user-management endpoint. Password rotation requires a trusted operational
script to hash a new password and transactionally delete that user's sessions
through the repository. Back up the volume and encryption key before upgrades.

Missing production auth origin makes auth API calls return a clean 503; core APIs
still start if no bootstrap is configured. Invalid configured bootstrap fails
startup rather than creating an insecure user.

## Remaining live Ring steps

1. **Resolve the inbound delivery contract with Ring first.** The public
   [Partner API reference](https://developer.amazon.com/docs/ring/api-documentation.html)
   describes server-to-server code delivery but does not establish the inbound
   encoding/authentication contract used by this app. Implement and test
   receive_verified_ring_code only after Ring confirms that contract.
   It remains 503, including for a signed-in user. No manual token bypass exists.
2. Deploy with the variables above and persistent storage; provision the operator.
   Verify /auth/login, /auth/me, logout and /health.
3. Set RING_CLIENT_ID, RING_CLIENT_SECRET, RING_SIGNING_KEY, a stable
   RING_ENCRYPTION_KEY (Fernet), and the correct RING_ENVIRONMENT.
   RING_REQUIRED=true enables startup validation. Keep the documented defaults
   RING_API_BASE_URL=https://api.amazonvision.com and
   RING_OAUTH_TOKEN_URL=https://oauth.ring.com/oauth/token unless Ring supplies
   different documented environment endpoints.
4. Register matching HTTPS URLs in Ring's portal and environment:
   RING_ACCOUNT_LINK_URL=https://nodum-production.up.railway.app/ring/link,
   RING_TOKEN_EXCHANGE_URL=https://nodum-production.up.railway.app/ring/token-exchange,
   RING_WEBHOOK_URL=https://nodum-production.up.railway.app/ring/webhooks, and
   RING_HOMEPAGE_URL pointing to the deployed homepage.
   Permit auth/link/static-script and signed webhook/callback routes at ingress.
   Keep generic building APIs private.
5. Start linking from an authorized private-app Ring test account. Verify
   confirmed code delivery creates an encrypted **unclaimed** account, sign in
   after Ring redirects, confirm within ten minutes, and check **completed**.
   Refresh the frontend connection, discover real devices, and deliver a signed
   test event. A live link remains blocked until step 1 is completed.

No guessed callback payload, access authorization or physical actuation is added.
