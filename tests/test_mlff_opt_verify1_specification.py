from __future__ import annotations

from pathlib import Path
import inspect

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_opt_verify1_release_identity_preserves_mlff_compatibility() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert campaign_cli.VERIFICATION_RUNTIME_COMPATIBILITY_VERSION == "0.20.85a0"
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text()


def test_opt_verify1_architecture_and_spec_record_contract() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (
        ROOT
        / "docs/specs/training_data/mlff_opt_verify1_verification_reuse_neighbor_scaling_spec.md"
    ).read_text()
    assert "OPT-VERIFY1 - verification reuse and nearest-pair scaling" in manual
    assert "implemented in mdstats 0.20.102a0" in manual
    assert "OPT-EVAL1 through OPT-CTRL1 is complete" in manual
    assert "Status: implemented in mdstats 0.20.102a0." in spec
    assert "thread-local" in spec.lower()
    assert "neighbor-list" in spec.lower()
    assert "triclinic" in spec.lower()


def test_opt_verify1_verify_path_uses_templates_and_worker_cache() -> None:
    source = inspect.getsource(campaign_cli.command_verify)
    assert "_load_verification_structure_templates" in source
    assert "reuse_worker_calculator=True" in source
    nve = inspect.getsource(campaign_cli._nve_verify)
    assert "_worker_cached_nve_calculator" in nve
    minimum = inspect.getsource(campaign_cli._minimum_distance)
    assert "neighbor_list" in minimum
    assert "get_all_distances" not in minimum
