"""Bounded MQTT TLS/auth/ACL attacks on a disposable loopback broker only."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.drill_support import isolated_environment
from scripts.mqtt_drill import wait_for
from scripts.tls_drill import certificate
from app.integrations.mqtt_sensor import ContactIngestor, ContactSubscriber, SensorBinding
from app.models.authorization import Principal
from app.services.authorization import AuthorizationService
from app.sqlite_repository import SQLiteRepository
from demo_product import seed_demo, PREFIX


def run(broker_python):
    import paho.mqtt.client as mqtt
    with tempfile.TemporaryDirectory(prefix="nodum-mqtt-security-") as directory:
        folder = Path(directory)
        cert, key = certificate(folder)
        trusted = ssl.create_default_context(cafile=str(cert))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        own = SensorBinding(PREFIX + "building", PREFIX + "machine-room-sensor")
        other = SensorBinding("isolated-building-b", "isolated-sensor-b")
        users = {name: secrets.token_urlsafe(32) for name in ("publisher-a", "publisher-b", "collector-a", "collector-b")}
        config = {
            "port": port, "certificate": str(cert), "key": str(key), "users": users,
            "subscriptions": {"collector-a": [own.topic], "collector-b": [other.topic]},
            # A nonempty publish map is essential: absent/empty means legacy allow-all.
            "publications": {"publisher-a": [own.topic], "publisher-b": [other.topic]},
        }
        config_path = folder / "fixture.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        config_path.chmod(0o600)
        env = isolated_environment()
        env.update(APP_ENV="development", AUTH_PUBLIC_ORIGIN="http://127.0.0.1",
                   DATABASE_URL="sqlite:///" + str(folder / "synthetic.db"))
        previous = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        broker = None
        clients = []
        subscriber = None
        try:
            broker = subprocess.Popen([str(broker_python), str(ROOT / "backend/scripts/mqtt_security_broker.py"),
                                       "--config", str(config_path)], env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            def ready():
                if broker.poll() is not None:
                    raise RuntimeError("Secure broker exited before readiness")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=.2):
                        return True
                except OSError:
                    return False

            wait_for(ready)
            tls_checks = []
            for context, hostname in ((ssl.create_default_context(), "127.0.0.1"), (trusted, "localhost")):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=2) as raw:
                        with context.wrap_socket(raw, server_hostname=hostname):
                            pass
                except ssl.SSLCertVerificationError:
                    tls_checks.append("rejected")
                else:
                    raise RuntimeError("TLS trust/hostname attack succeeded")

            def client(username=None, password=None, accepted=True):
                connection = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
                clients.append(connection)
                connection.tls_set_context(trusted)
                if username:
                    connection.username_pw_set(username, password)
                result = []
                arrived = threading.Event()

                def connected(_client, _userdata, _flags, reason, _properties):
                    result.append(not reason.is_failure)
                    arrived.set()

                def disconnected(_client, _userdata, _flags, _reason, _properties):
                    # aMQTT 0.11.3 closes rejected authentication without CONNACK.
                    if not arrived.is_set():
                        result.append(False)
                        arrived.set()

                connection.on_connect = connected
                connection.on_disconnect = disconnected
                connection.connect("127.0.0.1", port, keepalive=10)
                connection.loop_start()
                if not arrived.wait(5) or result != [accepted]:
                    raise RuntimeError("Broker credential acceptance mismatch")
                if not accepted:
                    connection.disconnect()
                    connection.loop_stop()
                return connection

            client(accepted=False)
            client("publisher-a", secrets.token_urlsafe(32), accepted=False)
            client("unknown-user", secrets.token_urlsafe(32), accepted=False)
            publisher_a = client("publisher-a", users["publisher-a"])
            publisher_b = client("publisher-b", users["publisher-b"])
            observer = client("collector-b", users["collector-b"])
            observed = []
            observer.on_message = lambda _c, _u, message: observed.append(message.payload)

            def subscribe(connection, topic, allowed):
                completed = threading.Event()
                outcomes = []

                def acknowledged(_c, _u, _mid, reasons, _properties):
                    outcomes.append(bool(reasons) and all(not reason.is_failure for reason in reasons))
                    completed.set()

                connection.on_subscribe = acknowledged
                connection.subscribe(topic, qos=1)
                if not completed.wait(5) or outcomes != [allowed]:
                    raise RuntimeError("Broker subscription ACL mismatch")

            subscribe(observer, other.topic, True)
            for forbidden in (own.topic, "#", "nodum/#", "nodum/+/devices/+/contact"):
                subscribe(observer, forbidden, False)

            repo = SQLiteRepository()
            repo.initialize(seed_demo=False)
            accounts = seed_demo(repo, datetime.now(timezone.utc))
            principal = accounts["demo-presenter"]

            def auth():
                return AuthorizationService(repo, Principal(user_id=principal.id, person_id=principal.person_id),
                                            datetime.now(timezone.utc))

            ingestor = ContactIngestor(auth, own)
            subscriber = ContactSubscriber(ingestor, host="127.0.0.1", port=port, tls_context=trusted,
                                           username="collector-a", password=users["collector-a"])
            subscriber.start()
            wait_for(lambda: subscriber.status == "subscribed")

            def sample(identifier):
                return json.dumps({"event_id": identifier, "observed_at": datetime.now(timezone.utc).isoformat(),
                                   "state": "open"}).encode()

            def publish(connection, topic, payload):
                connection.publish(topic, payload, qos=1).wait_for_publish(5)

            first = sample("secure-positive-control")
            publish(publisher_a, own.topic, first)
            wait_for(lambda: subscriber.counts["recorded"] == 1)
            # A PUBACK alone is NOT proof of ACL acceptance/rejection; verify receivers.
            publish(publisher_a, other.topic, b"forbidden-cross-building")
            publish(publisher_b, own.topic, sample("spoofed-device"))
            publish(observer, other.topic, b"forbidden-read-only-publication")
            publish(publisher_b, other.topic, b"positive-building-b")
            publish(publisher_a, own.topic, first)
            wait_for(lambda: observed == [b"positive-building-b"] and subscriber.counts["duplicate"] == 1)
            time.sleep(.5)  # bounded negative-observation window, after positive controls
            if observed != [b"positive-building-b"] or subscriber.counts["recorded"] != 1:
                raise RuntimeError("Cross-building publish ACL bypass")

            # Independently test Nodum's live authority even with valid broker credentials.
            for assignment in repo.list_role_assignments():
                if assignment.user_id == principal.id and assignment.role.value == "manager":
                    repo.save_role_assignment(assignment.model_copy(update={"active": False}))
            publish(publisher_a, own.topic, sample("revoked-application-grant"))
            wait_for(lambda: subscriber.counts["rejected"] == 1)
            if repo.list_actuator_events():
                raise RuntimeError("Unexpected actuator activity")
            return {"broker": "aMQTT 0.11.3 disposable fixture", "transport": "verified TLS / MQTT 3.1.1",
                    "untrusted_certificate": tls_checks[0], "wrong_hostname": tls_checks[1],
                    "anonymous_wrong_unknown_credentials": "rejected",
                    "foreign_and_wildcard_subscriptions": "rejected (4)",
                    "cross_building_and_read_only_publications": "blocked at receivers (3)",
                    "positive_controls": "both building topics delivered",
                    "nodum_revocation_independent_of_broker": "PASS", "counts": dict(subscriber.counts),
                    "physical_hardware": "NOT TESTED", "deployment_broker": "NOT TESTED"}
        finally:
            if subscriber:
                subscriber.stop()
            for connection in clients:
                connection.disconnect()
                connection.loop_stop()
            if broker:
                broker.terminate()
                try:
                    broker.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    broker.kill()
                    broker.wait(timeout=5)
            os.environ.clear()
            os.environ.update(previous)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker-python", type=Path, required=True)
    args = parser.parse_args()
    if not args.broker_python.is_file():
        parser.error("Choose the existing isolated broker Python")
    print(json.dumps(run(args.broker_python), indent=2))
