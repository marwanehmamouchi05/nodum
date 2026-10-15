"""Disposable Caddy HTTPS + built frontend + private HTTP API acceptance fixture.

Never installs certificates, exposes public listeners, or uses an existing DB.
Requires an explicitly supplied official Caddy executable and installed frontend.
"""

import argparse
import json
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.drill_support import isolated_environment
from scripts.external_contract_drill import port, stop
from scripts.tls_drill import certificate


def run(caddy, ready_file, serve_seconds):
    with tempfile.TemporaryDirectory(prefix="nodum-proxy-") as directory:
        folder = Path(directory)
        cert, key = certificate(folder)
        api_port, public_port = port(), port()
        base = f"https://127.0.0.1:{public_port}"
        env = isolated_environment()
        env.update(
            DATABASE_URL="sqlite:///" + str(folder / "synthetic.db"),
            AUTH_PUBLIC_ORIGIN=base,
            PORT=str(api_port),
            FORWARDED_ALLOW_IPS="127.0.0.1",
        )
        # Seed only this disposable DB, with the same documented demo workflow.
        seed = (
            "from app.sqlite_repository import SQLiteRepository; from demo_product import seed_demo; "
            "from datetime import datetime,timezone; r=SQLiteRepository(); r.initialize(seed_demo=False); "
            "seed_demo(r,datetime.now(timezone.utc),presentation=True)"
        )
        subprocess.run(
            [sys.executable, "-c", seed],
            cwd=ROOT / "backend",
            env=env,
            check=True,
            capture_output=True,
            timeout=40,
        )
        dist = folder / "frontend"
        build_env = isolated_environment()
        build_env.update(
            VITE_API_BASE_URL=base + "/api", VITE_API_USE_CREDENTIALS="true"
        )
        subprocess.run(
            [
                shutil.which("node"),
                str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                "build",
                "--outDir",
                str(dist),
            ],
            cwd=ROOT / "frontend",
            env=build_env,
            check=True,
            capture_output=True,
            timeout=90,
        )
        # The server-rendered login intentionally uses /auth absolute paths.
        # Preserve that same-origin namespace alongside the /api frontend prefix.
        config = folder / "Caddyfile"
        config.write_text(
            f'''{{
    admin off
    persist_config off
    auto_https off
}}
{base} {{
    bind 127.0.0.1
    tls "{cert.as_posix()}" "{key.as_posix()}"
    handle_path /api/* {{
        reverse_proxy 127.0.0.1:{api_port}
    }}
    handle /auth/* {{
        reverse_proxy 127.0.0.1:{api_port}
    }}
    handle {{
        root * "{dist.as_posix()}"
        try_files {{path}} /index.html
        file_server
    }}
}}
''',
            encoding="utf-8",
        )
        proxy_env = isolated_environment()
        proxy_env.update(
            XDG_DATA_HOME=str(folder / "caddy-data"),
            XDG_CONFIG_HOME=str(folder / "caddy-config"),
        )
        server = proxy = None
        try:
            server = subprocess.Popen(
                [sys.executable, "-m", "app.run"],
                cwd=ROOT / "backend",
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            proxy = subprocess.Popen(
                [str(caddy), "run", "--config", str(config), "--adapter", "caddyfile"],
                cwd=folder,
                env=proxy_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            http = build_opener(
                ProxyHandler({}),
                HTTPSHandler(context=ssl.create_default_context(cafile=str(cert))),
            )
            for _ in range(100):
                if server.poll() is not None or proxy.poll() is not None:
                    raise RuntimeError("Disposable proxy/API failed to start")
                try:
                    with http.open(base + "/api/health", timeout=0.5) as response:
                        if response.status == 200:
                            break
                except URLError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Proxy startup timed out")
            for path, expected in (
                ("/", 200),
                ("/app/deep-link", 200),
                ("/api/manager/snapshot", 401),
                ("/api/does-not-exist", 404),
                ("/api/docs", 404),
                ("/auth/client.js", 200),
            ):
                try:
                    response = http.open(base + path, timeout=3)
                except HTTPError as error:
                    response = error
                with response:
                    if response.status != expected:
                        raise RuntimeError("Proxy routing acceptance mismatch")
            # Misconfigured wildcard trust must fail before startup.
            bad = env | {"FORWARDED_ALLOW_IPS": "*"}
            invalid = subprocess.run(
                [sys.executable, "-m", "app.run"],
                cwd=ROOT / "backend",
                env=bad,
                capture_output=True,
                timeout=5,
            )
            if invalid.returncode != 2:
                raise RuntimeError("Unsafe proxy configuration accepted")
            result = {
                "base": base,
                "fixture": "disposable Caddy HTTPS/static frontend/private HTTP API",
                "wire_routing": "PASS",
                "wildcard_proxy_trust": "REJECTED",
                "browser": "PENDING",
                "production_deployment": "NOT TESTED",
            }
            ready_file.parent.mkdir(parents=True, exist_ok=True)
            ready_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result), flush=True)
            until = time.monotonic() + serve_seconds
            while time.monotonic() < until:
                if ready_file.with_suffix(".stop").exists():
                    break
                if server.poll() is not None or proxy.poll() is not None:
                    raise RuntimeError("Disposable fixture exited unexpectedly")
                time.sleep(0.25)
        finally:
            stop(proxy)
            stop(server)
            ready_file.with_suffix(".stop").unlink(missing_ok=True)
            if ready_file.exists():
                report = json.loads(ready_file.read_text(encoding="utf-8"))
                report["fixture_stopped"] = True
                ready_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caddy", type=Path, required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--serve-seconds", type=int, default=600)
    args = parser.parse_args()
    if not args.caddy.is_file() or not 1 <= args.serve_seconds <= 1800:
        parser.error("Supply an existing Caddy binary and duration 1..1800 seconds")
    run(args.caddy.resolve(), args.ready_file.resolve(), args.serve_seconds)
