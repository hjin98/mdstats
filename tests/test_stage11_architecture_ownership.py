from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "arch_manuals"
DENSITY = ROOT / "mdstats" / "analysis" / "density"


def test_stage11_manuals_have_disjoint_normative_ownership() -> None:
    part_i = (ARCH / "framework_ring_architecture.md").read_text(encoding="utf-8")
    part_ii = (ARCH / "stage11_site_kinetics_architecture.md").read_text(encoding="utf-8")
    assert "Part I - Periodic Framework Topology" in part_i
    assert "Stage 11 structural completion and Part II handoff" in part_i
    assert "planned Stage 11C" not in part_i
    assert "Revised Stage 11 implementation sequence" not in part_i
    assert "Part II - Registered Statistical Site Discovery" in part_ii
    assert "Part I structural dependency contract" in part_ii
    assert "## Part I structural prerequisites - Stages 11A-D implemented" in part_ii
    status = (ARCH / "stage11_site_kinetics_status_history.md").read_text(encoding="utf-8")
    assert "This appendix contains descriptive release history" in status
    assert "does not define scientific contracts" in status


def test_stage11_architecture_pdfs_exist_and_are_nonempty() -> None:
    minimum_sizes = {
        "framework_ring_architecture.pdf": 100_000,
        "stage11_site_kinetics_architecture.pdf": 100_000,
        "stage11_site_kinetics_status_history.pdf": 20_000,
    }
    for name, minimum_size in minimum_sizes.items():
        path = ARCH / name
        assert path.is_file()
        assert path.stat().st_size > minimum_size


def test_pilot_common_helpers_are_not_duplicated_in_stage_modules() -> None:
    names = {
        "_canonical_json",
        "_digest",
        "_array_payload_bytes",
        "_replace_evidence",
        "_freeze",
        "_json_value",
    }
    offenders: list[tuple[str, str]] = []
    for path in DENSITY.glob("pilot_*.py"):
        if path.name == "_pilot_common.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                offenders.append((path.name, node.name))
    assert not offenders, offenders


def test_stage11_revision48_contract_is_present_and_gated() -> None:
    part_ii = (ARCH / "stage11_site_kinetics_architecture.md").read_text(
        encoding="utf-8"
    )
    assert "architecture revision 48" in part_ii
    assert "Calculation controls, not user labels, define the ensemble" in part_ii
    assert "Stage 11E-ENS0 - source-control bundle and energy-channel reconstruction" in part_ii
    assert "Stage 11E-STAT2 - preliminary ensemble-specific admissibility" in part_ii
    assert "Stage 11E-STAT3 - held-out distribution-stability refinement" in part_ii
    assert "Stage 11E-SAMP3 - partial-catalog scope, novelty, and saturation" in part_ii
    assert "Stage 11E-THERMO4A - optional product-scoped thermodynamic verification" in part_ii
    assert "Stage 11E-THERMO4B - kinetic-thermodynamic consistency" in part_ii
    assert "observed_partial_catalog" in part_ii
    assert "NVE data are not silently converted to a canonical PMF" in part_ii
    assert "population-derived thermodynamics are never validated against the same population" in part_ii
    assert "SimulationRunControls" in part_ii
    assert "SimulationControlCertificate" in part_ii
    assert "`EnsembleCertificate`" not in part_ii
    assert "EvidenceAdmissibilityOverlay" in part_ii
    assert "ProductionRegimeCatalog" in part_ii
    assert "cross-evaluated matrix" in part_ii
    assert "## Stage 11E8a - Na-LTA NVE continuation integration dossier" in part_ii
    assert "tested or assumed stationarity" not in part_ii
    assert "the next implementation boundary" not in " ".join(part_ii.lower().split())
    assert "next mandatory implementation boundary" not in " ".join(part_ii.lower().split())
    assert "## Stage 11E8a - real 300 K Na-LTA pilot" not in part_ii
