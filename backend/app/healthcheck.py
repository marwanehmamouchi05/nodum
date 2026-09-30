"""Container-local health probe; never route through environment HTTP proxies."""
import json
from urllib.request import ProxyHandler, build_opener

from app.config import AppSettings


def main():
    settings = AppSettings.from_env()
    host = settings.host
    if host == "0.0.0.0":
        host = "127.0.0.1"
    elif host == "::":
        host = "::1"
    if ":" in host:
        host = f"[{host}]"
    with build_opener(ProxyHandler({})).open(f"http://{host}:{settings.port}/health", timeout=3) as response:
        if response.status != 200 or json.loads(response.read(1024)) != {"status": "healthy"}:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
