"""Mutation tests challenge the independent evaluator, not Nodum's self-report."""

import ast
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

CLIENT = Path(__file__).resolve().parents[2] / "tools/contract_client/client.py"
spec = importlib.util.spec_from_file_location("external_contract_client", CLIENT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def records():
    sample = {
        "event_id": "e-1",
        "state": "closed",
        "observed_at": "2026-10-15T12:00:00+00:00",
    }
    record = {
        "id": "opaque-server-id",
        "source": "MQTT contact observation",
        "source_event_id": "e-1",
        "resource_id": "device-a",
        "action": "sensor.contact.closed",
        "observed_at": sample["observed_at"],
        "simulated": True,
    }
    return [record], {"e-1": sample}


@pytest.mark.parametrize(
    "mutation",
    ["missing", "duplicate", "source", "device", "state", "time", "simulation"],
)
def test_oracle_rejects_corrupted_observed_outcomes(mutation):
    observed, expected = records()
    client.evaluate(observed, expected, "device-a")
    changed = deepcopy(observed)
    if mutation == "missing":
        changed.clear()
    elif mutation == "duplicate":
        changed.append(deepcopy(changed[0]))
    elif mutation == "source":
        changed[0]["source_event_id"] = "foreign-event"
    elif mutation == "device":
        changed[0]["resource_id"] = "foreign-device"
    elif mutation == "state":
        changed[0]["action"] = "sensor.contact.open"
    elif mutation == "time":
        changed[0]["observed_at"] = "2026-10-15T11:59:00+00:00"
    elif mutation == "simulation":
        changed[0]["simulated"] = False
    with pytest.raises(AssertionError):
        client.evaluate(changed, expected, "device-a")


def test_client_has_no_nodum_database_or_process_imports():
    tree = ast.parse(CLIENT.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports |= {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imports & {"app", "sqlite3", "subprocess", "demo_product"}


def test_evaluator_does_not_disappear_under_python_optimization():
    script = (
        "import runpy; m=runpy.run_path(" + repr(str(CLIENT)) + "); "
        "m['evaluate']([], {'unexpected': {}}, 'device-a')"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", script], capture_output=True, timeout=5
    )
    assert result.returncode != 0 and b"AssertionError" in result.stderr
