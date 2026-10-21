# Actions requiring the owner or external recovery

## 1. Railway billing — owner action

1. Open the existing [Railway project](https://railway.com/project/72ebaa4a-9247-4771-8a75-ab46fd3e1113).
2. Open your workspace Billing/Plans page. The project currently uses a trial and the reported remaining trial time ends before judging.
3. Review the Hobby plan and actual usage estimate. It has a monthly minimum, and usage above included credit can add cost. Choose the paid arrangement you are comfortable with; enter payment details yourself.
4. Ensure the billing and usage limits will keep the project running through November 20, plus a buffer. AWS charges are separate.
5. Keep the persistent `/data` volume. Do not delete the service, volume or existing database to renew the plan.

No purchase or subscription upgrade has been made by the assistant.

## 2. Railway deployment outage — external dependency

Railway explicitly rejected redeployment with “Deploys have been paused temporarily.” AWS credentials were set privately, but the current running process must be redeployed before using them. This was not reported as a hosted AWS success.

1. Check [Railway status](https://status.railway.com/).
2. Once builds/deployments resume, use the tested submission branch/package and the deployment procedure below. Do not simply change the current service to scoped mode against its old database.
3. Verify the deployed website, login, live Bedrock answer, reviewer scopes and persistence after restart before recording or sharing the final judge URL.

The assistant can execute and verify deployment once the external block clears; no additional permission for the already authorized release is needed.

## 3. Final judge deployment procedure

The source branch is `codex/hackathon-submission-20261021`. The isolated checkout is `C:/Users/marwa/.codex/worktrees/hackathon-submission/nodum`.

1. Verify its checks and selected commit. In `frontend`, run `npm ci`, then return to the checkout root.
2. The reviewed existing package is `artifacts/judge-package-final`; its backend source matches the application candidate and it contains the compiled interface. Reuse it if application source is unchanged. To rebuild, run `python tools/package_submission.py`. Use `--output artifacts/judge-package-new` if the default package already exists. The script copies only source/runtime files and the compiled interface, without dotenv files or databases.
3. Back up the existing Railway configuration/database before the first code deployment, which may apply migrations even before judge activation. Keep the old database path available for recovery. A private configuration snapshot was saved during review; a database backup has NOT been completed. The current CLI requires an SSH key and its backup attempt stopped before execution. Establish an authorized SSH connection or a working Railway service console, then verify the backup. The current trial UI reports no existing backups and requires Pro for managed volume backup creation; no upgrade was purchased. The browser console remained at Connecting during the platform incident. With SSH available, the existing application supports `python -m app.maintenance backup --source /data/nodum.db --destination /data/nodum-before-judge-<unique-date>.db`; choose a new filename and retain the verified result. A configuration snapshot alone is not a database backup.
4. Automatic GitHub deployments were disabled during independent review: the repository backend build omits the locally compiled interface and could overwrite a working judge package after any push. Keep automatic deployments disabled through judging and use the explicit package upload. Deploy the prepared package to the existing Railway service. It preserves the service's `backend` root. An example with explicit identifiers is:

```powershell
railway up artifacts/judge-package-final --path-as-root --no-gitignore --project 72ebaa4a-9247-4771-8a75-ab46fd3e1113 --service nodum --environment production --detach
```

5. After the code deployment succeeds, run `python tools/activate_judge_demo.py` from the checkout root. It checks that the new authenticated endpoint exists, saves a private recovery configuration, generates a private judge password and stages the required settings. The credentials stay in ignored `secrets/judge-reviewer-access.json`. Alternatively, configure these variables privately for the synthetic judge installation. Keep existing Ring signing/encryption keys stable. Generate a private random judge password of at least 24 characters and store it in private testing instructions, never source control.

```text
APP_ENV=production
AUTH_PUBLIC_ORIGIN=https://nodum-production.up.railway.app
NODUM_AUTHORIZATION_MODE=scoped
NODUM_JUDGE_DEMO=true
NODUM_JUDGE_PASSWORD=<private random password>
DATABASE_URL=sqlite:////data/nodum-judge-demo.db
RING_MODE=simulation
NODUM_AI_ENABLED=true
AWS_REGION=eu-north-1
BEDROCK_MODEL_ID=eu.amazon.nova-2-lite-v1:0
```

6. Redeploy to activate the settings. The explicit demo path seeds a separate empty synthetic database once and preserves its records on restart. Existing legacy data is not overwritten. Judge mode bypasses legacy bootstrap-user creation; customer installations retain their normal path.
7. Visit `https://nodum-production.up.railway.app/app/`. Test `demo-presenter`, `demo-resident`, `demo-resident-102`, `demo-business` and `demo-staff` using the private judge password. Check the intended role boundaries.
8. Confirm `/auth/session` reports scoped mode, secure cookies and invalid-CSRF rejection, `/health` responds, and a fresh Bedrock question completes. Refresh the visit record and restart once to verify persistence.
9. Provide the judge URL and synthetic account credentials only in Devpost's private testing field. The main video is public; provider credentials are not.

## 4. Ring Playground token renewal — owner or approved assistant action

An official token was generated with the owner's explicit approval and tested successfully. It lasts 30 minutes. It is not a durable production Ring account link.

1. In the [Ring developer console](https://developer.amazon.com/ring/console/apps), open Playground.
2. Generate a fresh temporary token close to recording time. Do not film its value.
3. Configure it privately as the backend's `RING_PLAYGROUND_TOKEN`. It is used only by the explicit synthetic demo's restricted discovery endpoint, not by the live account-link adapter or custom event signer.
4. Restart/redeploy the backend as appropriate, sign in as a permitted demo operator, and select Demo Mode → Verify official Ring API.
5. Expect a sandbox device response. If expired or unavailable, report that honestly and renew it. Do not claim this verifies vendor-origin webhooks, physical control or durable live linking.
6. Do not put the token into public source, videos, Devpost fields or frontend variables. The stored preparation token is in ignored local secret storage.

## 5. Devpost saved declarations and final owner review

The existing [Nodum draft](https://devpost.com/submit-to/30992-build-ship-shape-amazon-developer-hackathon/manage/submissions/1203526-nodum/additional-info/edit) now reports DRAFT, 3/5 steps done. Solo entrant details, owner-confirmed personal answers/declarations, feedback, repository/friction-log URLs, story and technology tags have been saved. The following is the final review checklist; completed personal fields do not need re-entry. Chrome local file upload permission is enabled. Two product screenshots with captions and the Nodum thumbnail are already saved; do not repeat the upload-permission setup.

1. Choose Individual/Team/Organization accurately; confirm team members and organization details. Use N/A where appropriate.
2. Confirm residence and any Canada-province field accurately.
3. Confirm whether the project existed before August 31 and describe relevant work if necessary. The assistant cannot certify its complete pre-hackathon history for you.
4. Personally verify the age, eligible-jurisdiction and employment/conflict declarations. The assistant will not invent these answers.
5. Choose Ring and AWS Builder if the final evidence remains accurate. Open Source should be No unless an additional qualifying public contribution is actually prepared.
6. Review the actual feedback and story drafts. Complete the learning/career survey in your own words.
7. Add the public final video and tested project/repository links. Review the preview and final confirmation/terms before submitting.

## 6. Recording and video publication

Follow `VIDEO_SCRIPT.md`. The silent 25-second illustrated intro already exists at `artifacts/video/nodum-intro-25s.webm`; the narrated walkthrough and final video remain pending. Final YouTube/Vimeo upload requires a signed-in channel and verification of public playback. A script/storyboard is not a final video.

## 7. Repository access and optional Open Source

The owner selected public access. The existing repository https://github.com/marwanehmamouchi05/nodum is now public, its MIT license is detected, and anonymous access was verified. The repository and friction-log URLs are saved in Devpost. Judges do not need invitations. Public access does not guarantee Railway uptime; the live application must be deployed and verified separately. Preserve the submitted version after the deadline and seek organizer approval for changes when required. A separate public toolkit/contribution needs actual useful work, tests, documentation and license; no separate public project was created solely to claim the mini-challenge. Keep the core submission ahead of that optional work.
