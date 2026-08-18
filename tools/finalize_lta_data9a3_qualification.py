#!/usr/bin/env python3
"""Finalize the DATA9A3 DATA2--DATA5 LTA corpus qualification record.

This source-checkout utility intentionally qualifies only the historical
DATA9A3 target-corpus boundary (DATA2--DATA5).  Later DATA9A9c production gates
also require DATA6--DATA8, profile-extension, foundation-residual, and replay
artifacts and are owned by ``mdstats-mlff-campaign.py prepare``.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mdstats
from mdstats.training_data._common import canonical_json, digest


def _read_gzip(path: Path) -> Mapping[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def _production_plan_for_data9a3(
    *,
    normalization: Mapping[str, Any],
    references: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source: Any,
    frames: Any,
    data5: Any,
    expected_sources: int,
) -> Any:
    """Reconstruct the frozen DATA9A3 DATA2--DATA5 qualification boundary.

    The modern backend requires an immutable :class:`ProductionCorpusPlan`.
    DATA9A3 predates the downstream DATA6--DATA8/full-DATA9A requirements, so
    those requirements are explicitly disabled here instead of fabricating
    readiness for artifacts this utility does not load.
    """

    runs = tuple(evidence.get("runs", ()))
    if len(runs) != int(expected_sources):
        raise ValueError(
            f"Expected {expected_sources} production runs, but run_evidence.json "
            f"contains {len(runs)}."
        )
    expected_runs = tuple(
        mdstats.ProductionExpectedRun(
            run_id=str(item["run_id"]),
            frame_count=int(item["frame_count"]),
            reduced_formula=str(item["reduced_formula"]),
            ensemble=str(item["ensemble"]),
            target_start_kelvin=(
                None
                if item.get("target_start_kelvin") is None
                else float(item["target_start_kelvin"])
            ),
            target_end_kelvin=(
                None
                if item.get("target_end_kelvin") is None
                else float(item["target_end_kelvin"])
            ),
        )
        for item in runs
    )
    fold_count = sum(len(plan.folds) for plan in data5.cross_validation_plans)
    return mdstats.ProductionCorpusPlan(
        plan_id=f"{frames.dataset_id}-data9a3-qualification",
        dataset_id=frames.dataset_id,
        source_catalog_digest=source.content_digest,
        frame_catalog_digest=frames.content_digest,
        normalization_manifest_digest=digest(normalization),
        reference_manifest_digest=digest(references),
        expected_runs=expected_runs,
        expected_cross_validation_fold_count=fold_count,
        required_profile_extensions=(),
        require_foundation_features=False,
        require_foundation_residual_e0=False,
        require_data8_artifacts=False,
        require_replay_corpus=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True, type=Path)
    parser.add_argument("--expected-sources", type=int, default=27)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.artifact_directory
    normalization = json.loads((root / "normalization_records.json").read_text())
    references = json.loads((root / "reference_cohorts.json").read_text())
    evidence = json.loads((root / "run_evidence.json").read_text())
    frame_payload = _read_gzip(root / "frame_catalog.json.gz")
    data4_payload = _read_gzip(root / "data4_feature_bundle.json.gz")
    data5_payload = _read_gzip(root / "data5_partition_bundle.json.gz")

    source = mdstats.TrainingDataSourceCatalog.from_dict(references["source_catalog"])
    frames = mdstats.TrainingFrameCatalog.from_dict(frame_payload)
    data4 = mdstats.Data4FeatureBundle.from_dict(data4_payload)
    data5 = mdstats.Data5PartitionBundle.from_dict(data5_payload)
    production_plan = _production_plan_for_data9a3(
        normalization=normalization,
        references=references,
        evidence=evidence,
        source=source,
        frames=frames,
        data5=data5,
        expected_sources=args.expected_sources,
    )
    result = mdstats.build_production_corpus_qualification_record(
        production_plan=production_plan,
        normalization_manifest=normalization,
        reference_manifest=references,
        run_evidence_manifest=evidence,
        source_catalog=source,
        frame_catalog=frames,
        data4_bundle=data4,
        data5_bundle=data5,
        verified_data4_bundle_digest=str(data4_payload["content_digest"]),
        verified_data5_bundle_digest=str(data5_payload["content_digest"]),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(result.to_dict()) + "\n", encoding="utf-8")
    print(
        canonical_json(
            {
                "status": result.status.value,
                "target_corpus_qualified": result.target_corpus_qualified,
                "full_data9a_passed": result.full_data9a_passed,
                "content_digest": result.content_digest,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
