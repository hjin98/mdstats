"""Optional source-tree/installed-wheel parity check for the observable registry."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from mdstats.analysis import list_observable_capabilities


def _source_payload() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    manual_index = json.loads(
        (root / "mdstats" / "data" / "observable_owner_manuals.json").read_text(encoding="utf-8")
    )
    return {
        "capabilities": [capability.to_dict() for capability in list_observable_capabilities()],
        "manual_index": manual_index,
    }


def test_source_and_wheel_observable_registry_parity() -> None:
    wheel_value = os.environ.get("MDSTATS_TEST_WHEEL")
    if not wheel_value:
        pytest.skip("Set MDSTATS_TEST_WHEEL to exercise built-wheel registry parity.")
    wheel = Path(wheel_value).resolve()
    assert wheel.is_file(), wheel

    script = r'''
import importlib.resources
import json
from mdstats.analysis import list_observable_capabilities
manual_path = importlib.resources.files("mdstats").joinpath("data/observable_owner_manuals.json")
payload = {
    "capabilities": [capability.to_dict() for capability in list_observable_capabilities()],
    "manual_index": json.loads(manual_path.read_text(encoding="utf-8")),
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
'''
    env = os.environ.copy()
    inherited = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    # The wheel must precede the source checkout while retaining dependency paths.
    source_root = str(Path(__file__).resolve().parents[1])
    inherited = [entry for entry in inherited if Path(entry).resolve() != Path(source_root).resolve()]
    env["PYTHONPATH"] = os.pathsep.join([str(wheel), *inherited])
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=wheel.parent,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel_payload = json.loads(completed.stdout)
    assert wheel_payload == _source_payload()
