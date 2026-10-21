"""Build a secret-free Railway upload, preserving the existing backend service root.

Run from the repository root with Python after npm ci in frontend.
The output is artifacts/judge-package/backend; no database or dotenv is copied.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "judge-package")
    output = parser.parse_args().output.resolve()
    if not output.is_relative_to((ROOT / "artifacts").resolve()):
        raise SystemExit("Output must stay in this checkout artifacts directory")
    if output.exists():
        raise SystemExit("Package already exists; choose/archive the previous package before rebuilding")
    environment = dict(os.environ)
    # The production client uses its own origin, never a developer's local API.
    environment["VITE_API_BASE_URL"] = ""
    environment["VITE_API_USE_CREDENTIALS"] = "true"
    npm = "npm.cmd" if os.name == "nt" else "npm"
    subprocess.run([npm, "run", "build", "--", "--base=/app/"], cwd=ROOT / "frontend",
                   env=environment, check=True)
    backend = output / "backend"
    backend.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".env*", "*.db*", "*.sqlite*", "secrets", "product")
    shutil.copytree(ROOT / "backend" / "app", backend / "app", ignore=ignore)
    for name in ("Dockerfile", ".dockerignore", "requirements.txt", "demo_product.py"):
        shutil.copy2(ROOT / "backend" / name, backend / name)
    shutil.copytree(ROOT / "frontend" / "dist", backend / "app" / "web" / "product")
    print(f"Judge upload prepared: {output}")


if __name__ == "__main__":
    main()
