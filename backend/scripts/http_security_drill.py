"""Two bounded hostile HTTPS bodies against the disposable production fixture."""
import json
from pathlib import Path
import socket
import sys
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPSHandler, ProxyHandler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from scripts.tls_drill import running_fixture


def response_headers(stream):
    data = bytearray()
    while b"\r\n\r\n" not in data:
        chunk = stream.recv(1024)
        if not chunk or len(data) + len(chunk) > 8192:
            raise RuntimeError("Incomplete fixture response headers")
        data.extend(chunk)
    return bytes(data)


def run():
    with running_fixture() as (base, trusted):
        client = build_opener(ProxyHandler({}), HTTPSHandler(context=trusted))
        target = urlsplit(base)
        # Early rejection can reset a client still uploading. Expect/continue lets
        # us observe 413 before sending any oversized body on Windows as well.
        with socket.create_connection(("127.0.0.1", target.port), timeout=5) as raw:
            with trusted.wrap_socket(raw, server_hostname="127.0.0.1") as stream:
                stream.sendall((f"POST /auth/login HTTP/1.1\r\nHost: 127.0.0.1:{target.port}\r\n"
                                "Content-Type: application/json\r\nContent-Length: 1048578\r\n"
                                "Expect: 100-continue\r\n\r\n").encode())
                response = response_headers(stream)
                if not response.startswith(b"HTTP/1.1 413 ") or b"cache-control: no-store" not in response.lower():
                    raise RuntimeError("Oversized HTTPS request was not safely rejected")
        # One partial body, no concurrency or traffic flood. Body deadline is 10s.
        started = time.monotonic()
        with socket.create_connection(("127.0.0.1", target.port), timeout=13) as raw:
            with trusted.wrap_socket(raw, server_hostname="127.0.0.1") as stream:
                stream.sendall((f"POST /auth/login HTTP/1.1\r\nHost: 127.0.0.1:{target.port}\r\n"
                                "Content-Type: application/json\r\nContent-Length: 2\r\n\r\n{").encode())
                status = response_headers(stream).split(b"\r\n", 1)[0]
                if status != b"HTTP/1.1 408 Request Timeout":
                    raise RuntimeError("Partial HTTPS body deadline failed")
        elapsed = time.monotonic() - started
        with client.open(base + "/health", timeout=3) as response:
            if response.status != 200:
                raise RuntimeError("Fixture health did not recover")
        return {"transport": "verified loopback HTTPS / Uvicorn production configuration",
                "declared_oversized_body_before_upload": 413, "partial_body": 408,
                "partial_body_elapsed_seconds": round(elapsed, 2), "health_after_attacks": 200,
                "hostile_requests": 2, "selected_reverse_proxy": "NOT TESTED"}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
