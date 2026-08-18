"""Run Stage-11E8a-S3 structural mapping and temporal preparation."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from mdstats import (
    NaLta300KStructuralTemporalOptions,
    prepare_na_lta_300k_structural_temporal_pilot,
    read_vasp_frames,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vasprun_xml", type=Path)
    parser.add_argument("--output", type=Path, default=Path("stage11e8a_s3_summary.json"))
    args = parser.parse_args()

    collection = read_vasp_frames(str(args.vasprun_xml))
    result = prepare_na_lta_300k_structural_temporal_pilot(
        collection,
        args.vasprun_xml,
        options=NaLta300KStructuralTemporalOptions(),
    )

    mapping_statuses = Counter(item.status.value for item in result.structural_mapping.mappings)
    best_ring_sizes = Counter(item.candidates[0].ring_size for item in result.structural_mapping.mappings)
    passage_outcomes = Counter(item.outcome.value for item in result.temporal_assignment.passages)
    summary = {
        "stage": "11E8a-S3",
        "overall_status": result.report.overall_status.value,
        "missing_required_evidence": list(result.report.missing_required_evidence),
        "ring_count": len(result.structural_mapping.ring_geometries),
        "ring_size_counts": dict(result.structural_mapping.metadata["ring_size_counts"]),
        "mapping_status_counts": dict(sorted(mapping_statuses.items())),
        "best_candidate_ring_size_counts": {str(k): v for k, v in sorted(best_ring_sizes.items())},
        "serrated_polygon_mapping": result.structural_mapping.metadata["serrated_polygon_mapping"],
        "circle_or_ellipse_substitution": result.structural_mapping.metadata["circle_or_ellipse_substitution"],
        "partition_transfer_performed": result.temporal_assignment.metadata["partition_transfer_performed"],
        "full_temporal_sample_count": int(result.temporal_assignment.membership.raw_classification.size),
        "temporal_support_status": result.temporal_assignment.temporal_support_status.value,
        "evidence_pattern": result.temporal_assignment.evidence_pattern.value,
        "passage_outcome_counts": dict(sorted(passage_outcomes.items())),
        "wall_seconds": result.wall_seconds,
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
