"""External contract participant: HTTPS + MQTT only. No Nodum imports or database access."""

import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from ipaddress import ip_address
import json
from pathlib import Path
import random
import secrets
import ssl
import threading
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import (
    build_opener,
    HTTPSHandler,
    HTTPCookieProcessor,
    ProxyHandler,
    HTTPRedirectHandler,
    Request,
)

LAST_STEP = "configuration"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Redirects are not supported by the local contract client")


def wait_for(predicate, seconds=12):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.1)
    raise RuntimeError("External contract observation deadline exceeded")


class API:
    def __init__(self, base, context):
        parsed = urlsplit(base)
        if (
            parsed.scheme != "https"
            or not ip_address(parsed.hostname).is_loopback
            or parsed.path
            or parsed.username
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Fixture HTTPS origin must be a loopback IP without a path"
            )
        self.base, self.csrf = base, None
        self.client = build_opener(
            ProxyHandler({}),
            NoRedirect(),
            HTTPSHandler(context=context),
            HTTPCookieProcessor(CookieJar()),
        )

    def request(self, method, path, data=None, expected=200):
        headers = {}
        if method not in {"GET", "HEAD"}:
            headers = {
                "Content-Type": "application/json",
                "Origin": self.base,
                "X-CSRF-Token": self.csrf or "",
            }
        request = Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            method=method,
            headers=headers,
        )
        try:
            response = self.client.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read(1024 * 1024 + 1)
            if len(payload) > 1024 * 1024 or response.status != expected:
                raise RuntimeError(
                    f"Contract response mismatch: {method} expected {expected}, got {response.status}"
                )
            return json.loads(payload)

    def login(self, username, password):
        self.csrf = self.request("GET", "/auth/session")["csrf_token"]
        result = self.request(
            "POST", "/auth/login", {"username": username, "password": password}
        )
        self.csrf = result["csrf_token"]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def evaluate(records, expected, device_id):
    """Deterministic oracle checks facts from external observations, not status labels."""
    contacts = [r for r in records if r.get("source") == "MQTT contact observation"]
    require(
        len({r["id"] for r in contacts}) == len(contacts), "Duplicate persisted IDs"
    )
    require(
        {r.get("source_event_id") for r in contacts} == set(expected),
        "Missing or unexpected source events",
    )
    require(len(contacts) == len(expected), "Duplicate source-event delivery")
    for record in contacts:
        sample = expected[record["source_event_id"]]
        require(record["resource_id"] == device_id, "Wrong device association")
        require(
            record["action"] == "sensor.contact." + sample["state"],
            "Wrong normalized state",
        )
        require(
            record["observed_at"] == sample["observed_at"], "Wrong source timestamp"
        )
        require(record["simulated"] is True, "Fixture observation not marked simulated")


def run(config):
    global LAST_STEP
    import paho.mqtt.client as mqtt

    seed = config.get("seed", 1729)
    rng = random.Random(seed)
    context = ssl.create_default_context(cafile=config["ca_file"])
    root = API(config["base"], context)
    LAST_STEP = "initial authentication"
    root.login(config["root_username"], config["root_password"])
    folder = Path(config["coordination"])
    organization = config["organization"]
    created, observers = [], []
    LAST_STEP = "authenticated building and account onboarding"
    for suffix in ("a", "b"):
        building = f"lab-building-{suffix}"
        identifiers = {
            "building": building,
            "floor": building + "-floor",
            "location": building + "-room",
            "integration": building + "-mqtt",
            "device": building + "-contact",
        }
        for kind in ("building", "floor", "location", "integration", "device"):
            identifier = identifiers[kind]
            parent = (
                organization
                if kind == "building"
                else building
                if kind in {"floor", "integration"}
                else identifiers["floor"]
                if kind == "location"
                else identifiers["location"]
            )
            record = {
                "id": identifier,
                "name": "External fixture " + identifier,
                "kind": kind,
                "organization_id": organization,
                "building_id": building,
                "parent_id": parent,
                "scope_id": parent if kind in {"integration", "device"} else identifier,
                "demo": True,
            }
            if kind in {"integration", "device"}:
                record["connection_path"] = "simulation"
            if kind == "device":
                record.update(
                    integration_id=identifiers["integration"], device_type="sensor"
                )
            root.request("PUT", "/admin/nodes/" + identifier, record)
        password = secrets.token_urlsafe(24)
        username = "observer-" + suffix
        account = root.request(
            "POST",
            "/admin/accounts",
            {
                "name": username,
                "username": username,
                "password": password,
                "scope_id": building,
            },
        )
        root.request(
            "PUT",
            "/authorization/assignments/observer-" + suffix,
            {
                "id": "observer-" + suffix,
                "user_id": account["id"],
                "role": "manager",
                "scope_id": building,
                "permissions": ["activity.read", "locations.read", "hardware.read"],
            },
        )
        observer = API(config["base"], context)
        observer.login(username, password)
        observers.append(observer)
        created.append(identifiers)
    collector = root.request(
        "POST",
        "/admin/accounts",
        {
            "name": "Contact collector",
            "username": "contact-collector",
            "password": secrets.token_urlsafe(24),
            "scope_id": created[0]["building"],
        },
    )
    root.request(
        "PUT",
        "/authorization/assignments/contact-collector",
        {
            "id": "contact-collector",
            "user_id": collector["id"],
            "role": "manager",
            "scope_id": created[0]["building"],
            "permissions": ["activity.read", "hardware.configure"],
        },
    )
    folder.joinpath("ready.json").write_text(
        json.dumps({"buildings": created, "operator_user_id": collector["id"]}),
        encoding="utf-8",
    )
    LAST_STEP = "collector readiness"
    wait_for(lambda: folder.joinpath("collector.ready").exists(), seconds=20)
    topic = (
        "nodum/v1/contact/"
        + quote(created[0]["building"], safe="")
        + "/"
        + quote(created[0]["device"], safe="")
    )
    publisher = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311, clean_session=True
    )
    publisher.tls_set_context(context)
    publisher.username_pw_set(config["mqtt_username"], config["mqtt_password"])
    connected = threading.Event()
    publisher.on_connect = lambda _c, _u, _f, reason, _p: (
        connected.set() if not reason.is_failure else None
    )
    publisher.on_disconnect = lambda *_args: connected.clear()
    publisher.reconnect_delay_set(min_delay=1, max_delay=2)
    expected = {}
    try:
        LAST_STEP = "mqtt connection"
        publisher.connect("127.0.0.1", config["mqtt_port"], keepalive=10)
        publisher.loop_start()
        wait_for(connected.is_set)

        def samples():
            return observers[0].request(
                "GET", "/manager/activity?scope_id=" + created[0]["building"]
            )["items"]

        def publish(identifier):
            payload = {
                "event_id": identifier,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "state": rng.choice(["open", "closed"]),
            }
            publisher.publish(
                topic, json.dumps(payload).encode(), qos=1
            ).wait_for_publish(5)
            return payload

        LAST_STEP = "first durable observation"
        expected["external-first"] = publish("external-first")
        wait_for(lambda: len(samples()) == 1)
        evaluate(samples(), expected, created[0]["device"])
        LAST_STEP = "duplicate and malformed observations"
        publisher.publish(
            topic, json.dumps(expected["external-first"]).encode(), qos=1
        ).wait_for_publish(5)
        publisher.publish(
            topic, b'{"event_id":"malformed","state":"unlock"}', qos=1
        ).wait_for_publish(5)
        expected["external-barrier"] = publish("external-barrier")
        wait_for(lambda: len(samples()) >= 2)
        evaluate(samples(), expected, created[0]["device"])
        LAST_STEP = "foreign timeline and guessed device isolation"
        require(
            observers[1].request("GET", "/manager/activity")["items"] == [],
            "Foreign timeline leakage",
        )
        observers[1].request(
            "GET", "/manager/activity?scope_id=" + created[0]["building"], expected=403
        )
        observers[1].request(
            "GET", "/structure/nodes/" + created[0]["device"], expected=403
        )
        LAST_STEP = "broker restart and resumed delivery"
        folder.joinpath("restart.request").touch()
        wait_for(lambda: folder.joinpath("restart.complete").exists(), seconds=25)
        wait_for(connected.is_set)
        expected["external-reconnected"] = publish("external-reconnected")
        wait_for(lambda: len(samples()) >= 3)
        evaluate(samples(), expected, created[0]["device"])
        LAST_STEP = "application grant revocation"
        root.request("DELETE", "/authorization/assignments/contact-collector")
        publish("external-revoked")
        time.sleep(0.75)  # negative observation, after a successful transport barrier
        evaluate(samples(), expected, created[0]["device"])
        LAST_STEP = "complete environment stop and restored API observation"
        publisher.disconnect()
        publisher.loop_stop()
        folder.joinpath("restore.request").touch()
        wait_for(lambda: folder.joinpath("restore.complete").exists(), seconds=35)
        # Observe the restored database through HTTPS only. The fixture alone
        # owns backups; the independent client never receives a database path.
        evaluate(samples(), expected, created[0]["device"])
        require(
            observers[1].request("GET", "/manager/activity")["items"] == [],
            "Restored foreign timeline leakage",
        )
        observers[1].request(
            "GET", "/structure/nodes/" + created[0]["device"], expected=403
        )
        publisher.connect("127.0.0.1", config["mqtt_port"], keepalive=10)
        publisher.loop_start()
        wait_for(connected.is_set)
        publish("external-revoked-after-restore")
        time.sleep(0.75)
        evaluate(samples(), expected, created[0]["device"])
        folder.joinpath("finished").touch()
        return {
            "verdict": "PASS",
            "scenario": "external-contact-v1",
            "seed": seed,
            "buildings_provisioned_via_https": 2,
            "persisted_source_events": len(expected),
            "checks": [
                "authenticated onboarding",
                "event correlation and normalized values",
                "duplicate and malformed rejection",
                "foreign timeline and guessed-device denial",
                "broker restart and new delivery",
                "application grant revocation",
                "full stop, backup/new-path restore, durable API observations and retained revocation",
            ],
            "negative_observation_seconds": 0.75,
            "physical_execution": "NOT TESTED",
            "official_ring": "NOT TESTED",
        }
    finally:
        publisher.disconnect()
        publisher.loop_stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        result = run(config)
    except Exception as error:
        # Never include exception text: HTTP/TLS errors may contain private config.
        result = {
            "verdict": "FAIL",
            "error_class": type(error).__name__,
            "stage": LAST_STEP,
        }
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    raise SystemExit(0 if result["verdict"] == "PASS" else 1)
