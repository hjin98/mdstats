"""Run Stage-11E8a-S4 force-density and path-readiness preparation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats import prepare_na_lta_300k_force_path_pilot, read_vasp_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vasprun_xml", type=Path)
    parser.add_argument("--output", type=Path, default=Path("stage11e8a_s4_summary.json"))
    args = parser.parse_args()

    collection = read_vasp_frames(str(args.vasprun_xml))
    result = prepare_na_lta_300k_force_path_pilot(collection, args.vasprun_xml)
    summary = {
        "stage": "11E8a-S4",
        "overall_status": result.report.overall_status.value,
        "missing_required_evidence": list(result.report.missing_required_evidence),
        "blockers": list(result.report.blockers),
        "force_density_status": result.force_density_agreement.status.value,
        "joint_force_sample_count": result.force_density_agreement.joint_force_sample_count,
        "pmf_force_sample_count": result.force_density_agreement.pmf_force_sample_count,
        "refinement_status_counts": dict(result.force_density_agreement.refinement_status_counts),
        "path_preparation_status": result.transition_path_preparation.status.value,
        "provisional_passage_count": result.transition_path_preparation.provisional_passage_count,
        "provisional_outcome_counts": dict(result.transition_path_preparation.provisional_outcome_counts),
        "provisional_jump_count": result.transition_path_preparation.provisional_jump_count,
        "final_segmentation_executed": result.final_segmentation is not None,
        "transition_paths_executed": result.transition_paths is not None,
        "wall_seconds": result.wall_seconds,
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
