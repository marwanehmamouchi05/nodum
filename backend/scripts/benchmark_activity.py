"""Bounded SQLite operational-page benchmark, not a whole-building capacity test."""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.models.auth import NodumUser
from app.models.authorization import Scope, RoleAssignment, Principal
from app.models.building import Person
from app.services.activity import ActivityService
from app.services.authorization import AuthorizationService
from app.services.manager import ManagerService
from app.services.scoped_repository import bind_created
from app.sqlite_repository import SQLiteRepository


def measure(operation, samples):
    durations, cpu = [], []
    tracemalloc.start()
    try:
        for _ in range(samples):
            started, cpu_started = time.perf_counter(), time.process_time()
            rows = operation()
            cpu.append(time.process_time() - cpu_started)
            durations.append(time.perf_counter() - started)
            assert rows and all(r["scope_id"] == "building-000" for r in rows)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    ordered = sorted(durations)
    return {
        "samples": samples,
        "p50_ms": round(statistics.median(durations) * 1000, 3),
        "p95_ms": round(ordered[math.ceil(samples * 0.95) - 1] * 1000, 3),
        "mean_cpu_ms": round(statistics.mean(cpu) * 1000, 3),
        "python_peak_bytes": peak,
        "sequential_queries_per_second": round(1 / statistics.mean(durations), 2),
        "errors": 0,
    }


def run(events=100, samples=3):
    results = []
    now = datetime.now(timezone.utc)
    for buildings in (1, 10, 100):
        with tempfile.TemporaryDirectory(prefix="nodum-activity-bench-") as directory:
            path = Path(directory) / "bench.db"
            repo = SQLiteRepository("sqlite:///" + str(path))
            repo.initialize(seed_demo=False)
            started = time.perf_counter()
            with repo.transaction():
                repo.save_configured_person(
                    Person(id="observer", name="Synthetic observer", role="employee")
                )
                repo.save_auth_user(
                    NodumUser(
                        id="observer",
                        username="observer",
                        person_id="observer",
                        password_hash="fixture-no-login",
                        created_at=now,
                    )
                )
                repo.save_scope(
                    Scope(id="org", organization_id="org", kind="organization")
                )
                for building in range(buildings):
                    scope = f"building-{building:03}"
                    repo.save_scope(
                        Scope(
                            id=scope,
                            organization_id="org",
                            kind="building",
                            parent_id="org",
                        )
                    )
                    for i in range(events):
                        record = {
                            "id": f"activity-{building:03}-{i:06}",
                            "scope_id": scope,
                            "at": now.isoformat(),
                            "action": "sensor.contact.open",
                            "actor_id": "observer",
                            "resource_id": f"sensor-{building:03}",
                            "location_id": scope,
                            "simulated": True,
                        }
                        repo.save_operational_record("operation_activity", record)
                        bind_created(repo, "operation_activity", record["id"], scope)
                repo.save_role_assignment(
                    RoleAssignment(
                        id="observer-grant",
                        user_id="observer",
                        role="manager",
                        scope_id="building-000",
                        permissions=["activity.read"],
                    )
                )
            seeded = time.perf_counter() - started
            auth = AuthorizationService(
                repo, Principal(user_id="observer", person_id="observer"), now
            )

            # Keep the legacy baseline transaction comparable to snapshot's transaction.
            def legacy():
                with repo.transaction():
                    return ManagerService(auth).records(
                        "operation_activity", "activity.read"
                    )

            def paged():
                return ActivityService(auth).page()["items"]

            before, after = measure(legacy, samples), measure(paged, samples)
            results.append(
                {
                    "building_scopes": buildings,
                    "events_per_scope": events,
                    "total_events": buildings * events,
                    "authorized_scopes": 1,
                    "seed_elapsed_seconds": round(seeded, 3),
                    "fixture_writes_per_second": round(buildings * events / seeded, 2),
                    "database_and_wal_bytes": sum(
                        p.stat().st_size for p in Path(directory).glob("bench.db*")
                    ),
                    "legacy_full_history": before,
                    "indexed_page": after,
                    "scope": "operational activity only; no full dashboard, HTTP, concurrent load or physical devices",
                }
            )
    return {
        "schema_version": 1,
        "scenario": "activity-pages-v1",
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "processor": platform.processor(),
            "logical_cpus": os.cpu_count(),
        },
        "limits": {
            "maximum_events": 100 * events,
            "samples_per_query": samples,
            "concurrency": 1,
            "memory_metric": "Python traced allocations only, not process RSS",
        },
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-per-building", type=int, default=100)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.events_per_building <= 200 or not 1 <= args.samples <= 5:
        parser.error("Use 1–200 events/building and 1–5 samples")
    result = run(args.events_per_building, args.samples)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
