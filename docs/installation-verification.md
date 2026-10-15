# Isolated backend installation and HTTPS verification

2026-10-15: resumed clean checkpoint `40b4769`. A new Windows Python 3.13 virtual
environment installed the existing pinned `backend/requirements.txt` from the
public package index/cache. `pip check`, the actual recovery/startup drill and the
new HTTPS session drill passed there. This is a fresh environment on the current
machine, not an untouched OS, container, frontend installation or deployed proxy.

From the isolated checkout, choose an environment path that does not exist:

```powershell
python -m venv C:/nodum-test-env
C:/nodum-test-env/Scripts/python.exe -m pip install -r backend/requirements.txt
C:/nodum-test-env/Scripts/python.exe -m pip check
C:/nodum-test-env/Scripts/python.exe backend/scripts/pilot_drill.py
C:/nodum-test-env/Scripts/python.exe backend/scripts/tls_drill.py
```

The TLS drill creates a one-hour loopback certificate/key in a temporary directory,
starts production-mode Uvicorn with TLS and an isolated synthetic scoped database,
and trusts that certificate only in its own test client. It does not change the OS
trust store. It verifies secure HttpOnly host cookies, rotation, authenticated
Manager reads, Origin/CSRF denial, logout/private-data denial and rejection by a
client that has not trusted the temporary certificate. Its services/data/keys are
removed at completion. No provider, live hardware or production configuration is used.

`scripts/drill_support.py` supplies an allowlisted OS environment to both drills,
excluding inherited database/auth/provider/proxy/pip variables. Test broker packages
must use a separate environment: aMQTT's test-only Typer/Click requirements differ
from the application pins. Paho is an optional integration dependency, not a required
core backend dependency.

Still required: real TLS ingress/proxy topology, renewal, same-site frontend
deployment and browser acceptance in that topology, clean target-OS installation,
protected backup/key storage and hardware acceptance. Direct loopback TLS proves
the application session boundary, not a customer deployment.
