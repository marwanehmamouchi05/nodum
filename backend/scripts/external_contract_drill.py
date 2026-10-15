"""Server-side disposable lab fixture; external client has no Nodum/SQLite imports.

Only initial trusted organization/recovery provisioning occurs here. Buildings,
devices, accounts, assignments and revocation are created by the external HTTPS client.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import build_opener, HTTPSHandler, ProxyHandler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.drill_support import isolated_environment
from scripts.mqtt_drill import wait_for
from scripts.tls_drill import certificate
from app.maintenance import copy_database
from app.auth_config import AuthSettings
from app.integrations.mqtt_sensor import (
    ContactIngestor,
    ContactSubscriber,
    SensorBinding,
)
from app.models.authorization import Principal, Role, RoleAssignment
from app.models.building import Person
from app.services.auth import AuthService
from app.services.authorization import AuthorizationService, ROLE_CEILINGS
from app.services.structure import StructureService
from app.sqlite_repository import SQLiteRepository


def port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run(broker_python):
    with tempfile.TemporaryDirectory(prefix="nodum-external-lab-") as directory:
        folder = Path(directory)
        cert, key = certificate(folder)
        api_port, mqtt_port = port(), port()
        base = f"https://127.0.0.1:{api_port}"
        trusted = ssl.create_default_context(cafile=str(cert))
        env = isolated_environment()
        env.update(
            DATABASE_URL="sqlite:///" + str(folder / "synthetic.db"),
            AUTH_PUBLIC_ORIGIN=base,
        )
        repo = SQLiteRepository(env["DATABASE_URL"])
        repo.initialize(seed_demo=False)
        now = datetime.now(timezone.utc)
        repo.save_configured_person(
            Person(id="lab-recovery", name="Disposable lab recovery", role="employee")
        )
        root_password = secrets.token_urlsafe(32)
        root = AuthService(repo, AuthSettings(base)).create_user(
            "lab-recovery", root_password, "lab-recovery", now
        )
        authority = AuthorizationService(
            repo, Principal(user_id=root.id, person_id=root.person_id), now
        )
        StructureService(authority).bootstrap_organization(
            "lab-org", "Disposable external contract laboratory", demo=True
        )
        for role in (Role.ADMIN, Role.MANAGER):
            repo.save_role_assignment(
                RoleAssignment(
                    id="lab-recovery-" + role.value,
                    user_id=root.id,
                    role=role,
                    scope_id="lab-org",
                    permissions=list(ROLE_CEILINGS[role]),
                )
            )
        topic = SensorBinding("lab-building-a", "lab-building-a-contact").topic
        publisher_password, collector_password = (
            secrets.token_urlsafe(32),
            secrets.token_urlsafe(32),
        )
        broker_config = {
            "port": mqtt_port,
            "certificate": str(cert),
            "key": str(key),
            "users": {
                "external-publisher": publisher_password,
                "nodum-collector": collector_password,
            },
            "subscriptions": {"nodum-collector": [topic]},
            "publications": {"external-publisher": [topic]},
        }
        config = {
            "base": base,
            "ca_file": str(cert),
            "organization": "lab-org",
            "root_username": "lab-recovery",
            "root_password": root_password,
            "mqtt_port": mqtt_port,
            "mqtt_username": "external-publisher",
            "mqtt_password": publisher_password,
            "coordination": str(folder),
            "seed": 1729,
        }
        broker_path, client_path = folder / "broker.json", folder / "client.json"
        for path, data in ((broker_path, broker_config), (client_path, config)):
            path.write_text(json.dumps(data), encoding="utf-8")
            path.chmod(0o600)
        report_path = folder / "report.json"
        server = broker = client = subscriber = None
        started = time.monotonic()
        try:

            def start_server():
                return subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(api_port),
                        "--ssl-certfile",
                        str(cert),
                        "--ssl-keyfile",
                        str(key),
                        "--no-access-log",
                        "--no-proxy-headers",
                    ],
                    cwd=ROOT / "backend",
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            server = start_server()
            http = build_opener(ProxyHandler({}), HTTPSHandler(context=trusted))

            def api_ready():
                if server.poll() is not None:
                    raise RuntimeError("Fixture API exited")
                try:
                    with http.open(base + "/health", timeout=0.5) as response:
                        return response.status == 200
                except URLError:
                    return False

            wait_for(api_ready)

            def start_broker():
                process = subprocess.Popen(
                    [
                        str(broker_python),
                        str(ROOT / "backend/scripts/mqtt_security_broker.py"),
                        "--config",
                        str(broker_path),
                    ],
                    env=isolated_environment(),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                def ready():
                    if process.poll() is not None:
                        raise RuntimeError("Fixture broker exited")
                    try:
                        with socket.create_connection(
                            ("127.0.0.1", mqtt_port), timeout=0.2
                        ):
                            return True
                    except OSError:
                        return False

                try:
                    wait_for(ready)
                except BaseException:
                    stop(process)
                    raise
                return process

            broker = start_broker()
            client = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "tools/contract_client/client.py"),
                    "--config",
                    str(client_path),
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT / "tools/contract_client",
                env=isolated_environment(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            def client_alive_until(path):
                if client.poll() is not None:
                    result = (
                        json.loads(report_path.read_text(encoding="utf-8"))
                        if report_path.exists()
                        else {}
                    )
                    raise RuntimeError("External client failed: " + json.dumps(result))
                return path.exists()

            ready_path = folder / "ready.json"
            wait_for(lambda: client_alive_until(ready_path))
            provisioned = json.loads(ready_path.read_text(encoding="utf-8"))
            operator = repo.get_auth_user(provisioned["operator_user_id"])

            def auth():
                return AuthorizationService(
                    repo,
                    Principal(user_id=operator.id, person_id=operator.person_id),
                    datetime.now(timezone.utc),
                )

            ingestor = ContactIngestor(
                auth,
                SensorBinding(
                    provisioned["buildings"][0]["building"],
                    provisioned["buildings"][0]["device"],
                ),
            )
            subscriber = ContactSubscriber(
                ingestor,
                host="127.0.0.1",
                port=mqtt_port,
                tls_context=trusted,
                username="nodum-collector",
                password=collector_password,
            )
            subscriber.start()
            wait_for(lambda: subscriber.status == "subscribed")
            folder.joinpath("collector.ready").touch()
            wait_for(lambda: client_alive_until(folder / "restart.request"))
            stop(broker)
            wait_for(lambda: subscriber.status == "disconnected")
            broker = start_broker()
            wait_for(lambda: subscriber.status == "subscribed")
            folder.joinpath("restart.complete").touch()
            wait_for(lambda: client_alive_until(folder / "restore.request"))
            before_restore = dict(subscriber.counts)
            subscriber.stop()
            stop(server)
            stop(broker)
            archive, restored = folder / "archive.db", folder / "restored.db"
            backup = copy_database(folder / "synthetic.db", archive)
            recovery = copy_database(archive, restored)
            if backup["schema_version"] != recovery["schema_version"]:
                raise RuntimeError("Restore schema mismatch")
            env["DATABASE_URL"] = "sqlite:///" + str(restored)
            repo = SQLiteRepository(env["DATABASE_URL"])
            repo.initialize(seed_demo=False)
            server = start_server()
            wait_for(api_ready)
            broker = start_broker()
            subscriber = ContactSubscriber(
                ContactIngestor(auth, ingestor.binding),
                host="127.0.0.1",
                port=mqtt_port,
                tls_context=trusted,
                username="nodum-collector",
                password=collector_password,
            )
            subscriber.start()
            wait_for(lambda: subscriber.status == "subscribed")
            folder.joinpath("restore.complete").touch()
            client.wait(timeout=20)
            result = json.loads(report_path.read_text(encoding="utf-8"))
            if client.returncode or result["verdict"] != "PASS":
                raise RuntimeError("External contract failed: " + json.dumps(result))
            # Supplemental server evidence; external client independently checked API facts.
            if before_restore != {
                "recorded": 3,
                "duplicate": 1,
                "rejected": 2,
                "failed": 0,
            }:
                raise RuntimeError(
                    "Fixture transport counters did not confirm both rejection paths"
                )
            if subscriber.counts != {
                "recorded": 0,
                "duplicate": 0,
                "rejected": 1,
                "failed": 0,
            }:
                raise RuntimeError(
                    "Revocation did not survive full environment restore"
                )
            return result | {
                "elapsed_seconds": round(time.monotonic() - started, 2),
                "supplemental_collector_counts": before_restore,
                "restored_collector_counts": dict(subscriber.counts),
                "recovery": {
                    "integrity": recovery["integrity"],
                    "foreign_keys": recovery["foreign_keys"],
                    "schema_version": recovery["schema_version"],
                    "snapshots_structurally_verified": True,
                },
                "bootstrap": "trusted organization/recovery only",
                "client_process": "standalone; no database path, Nodum imports or shared repository objects",
            }
        finally:
            stop(client)
            if subscriber:
                subscriber.stop()
            stop(broker)
            stop(server)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-python", type=Path, required=True)
    args = parser.parse_args()
    if not args.broker_python.is_file():
        parser.error("Choose an existing isolated broker Python")
    print(json.dumps(run(args.broker_python), indent=2))
