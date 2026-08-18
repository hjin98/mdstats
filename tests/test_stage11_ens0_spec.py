from pathlib import Path

import mdstats


def test_ens0_permanent_spec_and_module_ownership():
    root = Path(__file__).resolve().parents[1]
    spec = root / "docs/specs/io/vasp_run_controls_spec.md"
    text = spec.read_text(encoding="utf-8")
    assert "Stage 11E-ENS0" in text
    assert "SYSTEM" in text and "comment_only" in text
    assert "FrameEnergyCatalog" in text
    assert "NumericalMDQualityControls" in text
    assert "ENS1, not ENS0" in text
    assert (root / "mdstats/io/source_controls.py").is_file()
    assert (root / "mdstats/io/vasp_controls.py").is_file()


def test_ens0_public_api_contract():
    assert callable(mdstats.read_vasp_run_controls)
    assert mdstats.VASP_RUN_CONTROLS_SCHEMA == "mdstats.vasp-run-controls.v1"
    assert "VaspSourceControlBundle" in mdstats.__all__
