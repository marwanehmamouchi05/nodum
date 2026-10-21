"""Activate the synthetic judge installation after its code is deployed.

Run from this checkout root. Requires the existing authorized Railway CLI session.
Writes private reviewer access and a recovery configuration under ignored secrets/.
Never prints passwords, provider credentials or cloud configuration values.
"""
from pathlib import Path
import json
import os
import secrets
import subprocess
from urllib.error import HTTPError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://nodum-production.up.railway.app"
PROJECT = "72ebaa4a-9247-4771-8a75-ab46fd3e1113"
RAILWAY = "railway.cmd" if os.name == "nt" else "railway"
TARGET = ["--project", PROJECT, "--service", "nodum", "--environment", "production"]


def main():
    with urlopen(BASE + "/app/", timeout=20) as response:
        if response.status != 200 or "text/html" not in response.headers.get("Content-Type", ""):
            raise SystemExit("Deploy and verify the judge package before activating it")
    try:
        urlopen(BASE + "/ring/playground/devices", timeout=20).close()
    except HTTPError as error:
        if error.code != 401:
            raise SystemExit("Judge API code is not deployed; existing settings were preserved") from None
    else:
        raise SystemExit("Judge API must require authentication before activation")
    private = ROOT / "secrets"
    private.mkdir(exist_ok=True)
    current = subprocess.run([RAILWAY, "variable", "list", *TARGET, "--json"],
                             capture_output=True, text=True, check=True)
    configuration = json.loads(current.stdout)
    recovery = private / "railway-before-judge.json"
    if not recovery.exists():
        recovery.write_text(json.dumps(configuration, indent=2))
    credential_file = private / "judge-reviewer-access.json"
    if credential_file.exists():
        password = json.loads(credential_file.read_text())["password"]
    else:
        password = secrets.token_urlsafe(32)
        credential_file.write_text(json.dumps({"url": BASE + "/app/", "username": "demo-presenter",
                                               "password": password}, indent=2))
    values = {
        "APP_ENV": "production", "AUTH_PUBLIC_ORIGIN": BASE,
        "NODUM_AUTHORIZATION_MODE": "scoped", "NODUM_JUDGE_DEMO": "true",
        "NODUM_JUDGE_PASSWORD": password, "DATABASE_URL": "sqlite:////data/nodum-judge-demo.db",
        "RING_MODE": "simulation", "NODUM_AI_ENABLED": "true",
        "AWS_REGION": "eu-north-1", "BEDROCK_MODEL_ID": "eu.amazon.nova-2-lite-v1:0",
    }
    for key, value in values.items():
        result = subprocess.run([RAILWAY, "variable", "set", key, "--stdin", "--skip-deploys", *TARGET],
                                input=value, capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(f"Could not set {key}; review private recovery configuration before retrying")
    result = subprocess.run([RAILWAY, "redeploy", *TARGET, "--yes"], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("Settings are staged; Railway did not activate them. Check platform status and redeploy after recovery")
    print("Redeployment requested. Verify completion, scoped login, persistence and real AI before sharing the judge URL.")
    print("Private reviewer access: secrets/judge-reviewer-access.json. Do not commit or publish this file.")


if __name__ == "__main__":
    main()
