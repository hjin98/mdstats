"""Isolated worker for one VASP training source.

The production campaign launches this module in a fresh Python interpreter for
one source only.  This bounds parser state, releases XML/ASE memory promptly,
and lets multiple sources be audited concurrently without sharing mutable
scientific state.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping


def ingest_source_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    from .conditions import TemperatureTargetEvidence
    from .frame_cache import write_frame_data_cache_entry
    from .manifest import TrainingDataRunSpec
    from .sources import SourceAuditPolicy, load_vasp_training_source

    run = TrainingDataRunSpec.from_dict(payload["run"])
    source_policy = SourceAuditPolicy.from_dict(payload["source_policy"])
    item = load_vasp_training_source(
        run,
        base_directory=str(payload["base_directory"]),
        source_policy=source_policy,
        strict=True,
    )
    cache_record = write_frame_data_cache_entry(
        run.run_id, item.source, item.frame_data, str(payload["cache_directory"])
    )
    target = item.temperature_target
    if not isinstance(target, TemperatureTargetEvidence):
        raise RuntimeError("Unexpected temperature-target evidence type.")
    return {
        "run_id": run.run_id,
        "source": item.source.to_dict(),
        "temperature_target": {
            "target_start_kelvin": target.target_start_kelvin,
            "target_end_kelvin": target.target_end_kelvin,
            "evidence": target.evidence,
        },
        "cache_record": cache_record,
        "timings": {
            "controls_seconds": item.controls_seconds,
            "frames_seconds": item.frames_seconds,
            "assessment_seconds": item.assessment_seconds,
        },
    }


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Internal one-source MLFF ingestion worker.")
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.request.read_text(encoding="utf-8"))
    _atomic_json(args.result, ingest_source_request(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
