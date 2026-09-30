"""Run with python -m app.run [--env-file PATH]. One Uvicorn worker for SQLite."""
import argparse
import sys

from app.config import AppSettings, ConfigurationError, validate_startup


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start Nodum backend")
    parser.add_argument("--env-file", help="Optional local dotenv file; existing environment takes precedence")
    args = parser.parse_args(argv)
    if args.env_file:
        from pathlib import Path
        from dotenv import load_dotenv

        if not Path(args.env_file).is_file():
            print("Nodum startup failed: requested environment file does not exist", file=sys.stderr)
            return 2
        load_dotenv(args.env_file, override=False)
    try:
        settings = AppSettings.from_env()
        validate_startup(settings)
    except ConfigurationError as exc:
        print(f"Nodum startup failed: {exc}", file=sys.stderr)
        return 2
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port,
                workers=1, reload=False, log_level=settings.log_level,
                access_log=settings.access_log, server_header=False,
                proxy_headers=bool(settings.forwarded_allow_ips),
                forwarded_allow_ips=settings.forwarded_allow_ips,
                timeout_graceful_shutdown=settings.graceful_shutdown_seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
