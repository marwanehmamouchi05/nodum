# Nodum submission friction log

October 21, 2026. Entries describe actual observations and distinguish integration issues from provider incidents.

## Ring: a temporary Playground session is not a linked application

- Task: demonstrate documented Ring technology inside Nodum without hardware.
- Steps: open the signed-in Ring developer console, generate an approved temporary token, invoke device discovery, then call the same official endpoint through Nodum.
- Expected: demonstrate official runtime use with clear provenance and repeatable setup.
- Actual: device discovery returned HTTP 200 and one sandbox device. The token expires after 30 minutes. This does not establish production account linking or vendor-origin webhook delivery.
- Severity: Important for reproducible review; not an observed Ring API failure.
- Workaround: a restricted, read-only Playground discovery path, separate from customer account linking and clearly separate from the custom signed-event generator.
- Suggestion: a complete documented sandbox-to-app example, with temporary credential lifecycle and signed event provenance.

## Bedrock: local inference succeeded while hosted inference was unavailable

- Task: ask the hosted Nodum chatbot a read-only question.
- Steps: sign in, submit an authenticated chat request, compare server configuration with a real local Converse call.
- Expected: configured credentials/model access in the running deployment and a useful response.
- Actual: hosted chat returned HTTP 503/unavailable; local Nova inference succeeded. Railway lacked AWS credential variables. Credentials were configured privately, but redeployment was blocked by Railway's platform incident. The packaged local app then completed a scoped manager_operations tool call using real Bedrock inference.
- Severity: Important; a deployment configuration/activation issue, not evidence that Bedrock itself was down.
- Workaround: verify the standard credential chain and one real inference request in each environment; keep local Guide/forms functional during failure.
- Suggestion: a deployment preflight example with credential-presence, IAM/model/region and inference checks, without secret disclosure.

## Railway infrastructure incident (separate from Amazon product feedback)

- Task: activate the hosted AWS configuration and publish the judge release.
- Steps: inspect deployment/health, set the missing credentials privately, request a redeploy.
- Expected: a controlled deployment and hosted retest.
- Actual: existing health/login responded, but Railway explicitly rejected redeployment because deployments were paused. Its official status page reported a matching incident.
- Severity: Important for release timing.
- Workaround: prepare and test a secret-free deployment package locally; keep the existing running service and persistent storage unchanged.
- Suggestion: distinguish running-service health from deployment-platform readiness in release instructions.
