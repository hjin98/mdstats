from __future__ import annotations

from pathlib import Path
import ast
import json
import numpy as np
import pytest
import yaml

import mdstats
from tests.test_mlff_data7_fitted_metrics_selection import _inputs
from tests.test_mlff_data8_mace_artifacts import _foundation, _probe, _data7_bundles


def test_foundation_residual_e0_fit_adds_checkpoint_bound_corrections(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, _, _, final = _inputs(tmp_path)
    checkpoint = _foundation(tmp_path)
    # Choose deterministic foundation E0s and residual elemental corrections.
    elements = sorted({int(z) for data in frame_data.values() for z in data.atomic_numbers})
    foundation_e0 = {z: -0.25 * z for z in elements}
    correction = {z: 0.01 * z for z in elements}
    predictions = {}
    for uid in final.frame_uids:
        record = frames.frame(uid)
        data = frame_data[record.run_id]
        numbers = np.asarray(data.atomic_numbers)
        target = float(data.energies_ev[record.source_frame_index])
        delta = sum(np.count_nonzero(numbers == z) * correction[z] for z in elements)
        predictions[uid] = target - delta
    fit = mdstats.fit_foundation_residual_atomic_references(
        frames,
        frame_data,
        data5,
        final,
        foundation_prediction_energy_by_frame=predictions,
        foundation_reference_energies=foundation_e0,
        foundation_checkpoint_digest=checkpoint.sha256,
    )
    assert fit.is_foundation_residual_fit
    assert fit.foundation_checkpoint_digest == checkpoint.sha256
    # The LTA count matrix is rank deficient, so individual corrections are
    # non-unique. The fitted composition-level residuals must nevertheless be exact.
    A = np.asarray(fit.count_matrix, dtype=float)
    observed = A @ np.asarray([fit.correction_mapping[z] for z in fit.element_order])
    expected = np.asarray(fit.target_energies_ev) - np.asarray(fit.foundation_prediction_energies_ev)
    assert np.allclose(observed, expected, atol=1e-10)
    for z in elements:
        assert fit.explicit_mapping[z] == pytest.approx(foundation_e0[z] + fit.correction_mapping[z], abs=1e-10)
    assert mdstats.AtomicReferenceFitRecord.from_dict(fit.to_dict()) == fit


def test_data8_requires_residual_e0_and_portable_paths(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_data8_preparation_bundle(
            sources, frames, frame_data, data5, bundles,
            output_directory=tmp_path / "rejected",
            foundation_checkpoint=_foundation(tmp_path), compatibility_probe=_probe(),
            optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        )
    result = mdstats.build_data8_preparation_bundle(
        sources, frames, frame_data, data5, bundles,
        output_directory=tmp_path / "portable",
        foundation_checkpoint=_foundation(tmp_path), compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
        selection_size=4,
    )
    for job in result.jobs:
        config = yaml.safe_load((tmp_path / "portable" / job.config_relative_path).read_text())
        assert not Path(config["foundation_model"]).is_absolute()
        heads = ast.literal_eval(config["heads"])
        assert not Path(heads["target_head"]["train_file"]).is_absolute()
        assert job.protocol.selection_size == 4
        script = (tmp_path / "portable" / job.command_relative_path).read_text()
        assert "SCRIPT_DIR" in script and 'cd "$SCRIPT_DIR"' in script


def test_mace_source_qualification_uses_the_complete_supplied_environment() -> None:
    root = Path('/mnt/data/work_data9a/mace_src')
    ase = Path('/mnt/data/work_data9a/ase_src')
    if not root.exists() or not ase.exists():
        pytest.skip('supplied source trees are not mounted')
    record = mdstats.qualify_mace_source_environment(root, ase_source_root=ase)
    assert record.source_compile_passed
    assert record.top_level_import_passed
    assert record.mace_version == '0.3.16'
    assert not record.missing_required_dependencies
    assert record.qualified_for_training_smoke
    assert mdstats.InstalledMaceQualificationRecord.from_dict(record.to_dict()) == record
