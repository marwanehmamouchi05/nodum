"""Disposable TLS/file-auth broker. Never use this test runner as a deployment."""
import argparse
import asyncio
import json
from pathlib import Path

from amqtt.broker import Broker
from passlib.apps import custom_app_context


async def serve(config_path):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    port = config["port"]
    if not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("Unprivileged fixture port required")
    passwords = config_path.parent / "passwords.hashed"
    passwords.write_text("".join(
        username + ":" + custom_app_context.hash(password) + "\n"
        for username, password in config["users"].items()), encoding="utf-8")
    passwords.chmod(0o600)
    broker = Broker({
        "listeners": {"default": {
            "type": "tcp", "bind": f"127.0.0.1:{port}", "max_connections": 8,
            "ssl": True, "certfile": config["certificate"], "keyfile": config["key"],
        }},
        "plugins": {
            # AnonymousAuthPlugin is deliberately absent, even allow_anonymous=False.
            "amqtt.plugins.authentication.FileAuthPlugin": {"password_file": str(passwords)},
            "amqtt.plugins.topic_checking.TopicAccessControlListPlugin": {
                "acl": config["subscriptions"], "publish_acl": config["publications"],
            },
        },
    })
    await broker.start()
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    asyncio.run(serve(parser.parse_args().config))
