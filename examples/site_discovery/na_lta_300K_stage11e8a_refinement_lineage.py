"""Run the Stage-11E8a-S2 spatial refinement pilot on a VASP trajectory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mdstats import (
    NaLta300KRefinementLineageOptions,
    prepare_na_lta_300k_refinement_lineage_pilot,
    read_vasp_frames,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("vasprun_xml", type=Path)
    parser.add_argument("--output", type=Path, default=Path("stage11e8a_s2_summary.json"))
    args = parser.parse_args()

    collection = read_vasp_frames(str(args.vasprun_xml))
    result = prepare_na_lta_300k_refinement_lineage_pilot(
        collection,
        args.vasprun_xml,
        options=NaLta300KRefinementLineageOptions(),
    )
    summary = {
        "stage": "11E8a-S2",
        "overall_status": result.report.overall_status.value,
        "missing_required_evidence": list(result.report.missing_required_evidence),
        "bandwidth_attractor_counts": [len(c.attractors) for c in result.lineage_catalogs],
        "bandwidth_saddle_counts": [len(c.saddles) for c in result.lineage_catalogs],
        "scale_status": result.scale_consensus.status.value,
        "grid_refinement_status": result.grid_refinement.certificate.status.value,
        "reference_cell_accepted": result.reference_cell_sensitivity.accepted,
        "wall_seconds": result.wall_seconds,
    }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
