# Pilot preflight

Use a separate configuration file based on `pilot.env.example`; never overwrite an
existing installation's environment. From `backend` run:

```powershell
python -m app.preflight --env-file C:/nodum-config/pilot.env
```

Exported variables take precedence. Exit 0 means only that local prerequisites
passed; exit 2 means the JSON report lists failures. The check does not initialize
databases, migrate, seed, contact Ring/AWS, discover devices or send commands.

It requires production mode, scoped authorization, explicit existing supported
SQLite storage, valid authentication settings, appropriate cross-origin browser
credentials, removed bootstrap credentials, disabled AI during automated validation,
and basic onboarding records. The onboarding check establishes record presence,
not effective role permissions. Test actual role workflows separately.

An empty/missing installation intentionally fails. Use the existing explicit
`provision_admin.py` workflow and Admin building setup, then rerun. Back up before
updates; preflight will not silently upgrade an older schema. See
`backup-recovery.md` for recovery drills.

Passing does not verify proxy TLS, backup protection, tenant acceptance, notifications,
provider account linking, device health, physical access, emergency egress or a real
pilot. Those remain separate evidence gates in `PILOT_READINESS.md`.
