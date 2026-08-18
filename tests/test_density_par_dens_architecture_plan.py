from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.md"


def test_par_dens0_to_6_are_completed() -> None:
    assert (ROOT / "pyproject.toml").read_text(encoding="utf-8").find(f'version = "{mdstats.__version__}"') >= 0
    text = MANUAL.read_text(encoding="utf-8")
    assert "PAR-DENS0 is `completed` in `mdstats 0.20.120a0`" in text
    assert "PAR-DENS2 are `completed` in `mdstats 0.20.141a0`" in text
    assert "PAR-DENS3 is `completed` in" in text
    assert "`mdstats 0.20.142a0`; PAR-DENS4 is `completed` in `mdstats 0.20.143a0`; PAR-DENS5" in text
    assert "is `completed` in `mdstats 0.20.144a0`; PAR-DENS6 is `completed` in" in text
    assert "`mdstats 0.20.145a0`" in text
    assert "### PAR-DENS0 implementation record (0.20.120a0)" in text
    assert "### PAR-DENS1 implementation record (0.20.141a0)" in text
    assert "### PAR-DENS2 implementation record (0.20.141a0)" in text
    assert "### PAR-DENS3 implementation record (0.20.142a0)" in text
    assert "### PAR-DENS4 implementation record (0.20.143a0)" in text
    assert "### PAR-DENS5 implementation record (0.20.144a0)" in text
    assert "### PAR-DENS6 implementation record (0.20.145a0)" in text


def test_par_dens_gates_are_present_in_normative_order() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    headings = [
        "## PAR-DENS0 - basin-aware, convergence-qualified spread estimation",
        "## PAR-DENS1 - execution-faithful direct/FFT cost calibration",
        "## PAR-DENS2 - global resource-aware density scheduler",
        "## PAR-DENS3 - parallel density planning and realization",
        "## PAR-DENS4 - parallel trajectory preprocessing and geometry reuse",
        "## PAR-DENS5 - optional GPU density backend",
        "## PAR-DENS6 - end-to-end qualification and auto-tuning",
    ]
    offsets = [text.index(heading) for heading in headings]
    assert offsets == sorted(offsets)


def test_par_dens_plan_locks_scientific_and_resource_invariants() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    for token in (
        "within-basin vibrational spread",
        "FinalResidenceInterval.sample_indices",
        "FinalPassageInterval",
        "four independent 128-stratum random replicates",
        "deterministic 256- and 512-stratum midpoint anchors",
        "0.0746859880 Angstrom",
        "3.95%",
        "0.0746753 Angstrom",
        "0.19586 Angstrom",
        "0.07977 Angstrom",
        "0.90N_{\\rm available}",
        "0.80M_{\\rm available}",
        "0.80M_{\\rm GPU,available}",
        "Wall-time models",
        "remain advisory for backend ranking",
        "must not silently coarsen an adaptive grid",
    ):
        assert token in text
