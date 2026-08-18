from __future__ import annotations

from pathlib import Path
import shutil

import numpy as np
import pytest
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_cli


def _d(ch: str) -> str:
    return ch * 64


def _base_kwargs(mode: str = "foundation_pseudolabel") -> dict:
    return dict(
        label_mode=mode,
        old_source_sha256=_d("a"), new_source_sha256=_d("a"),
        old_geometry_set_digest=_d("b"), new_geometry_set_digest=_d("b"),
        old_source_true_label_payload_digest=_d("c"), new_source_true_label_payload_digest=_d("c"),
        old_prediction_policy_digest=_d("d"), new_prediction_policy_digest=_d("d"),
        old_qualification_policy_digest=_d("e"), new_qualification_policy_digest=_d("e"),
        old_eligible_geometry_set_digest=_d("f"), new_eligible_geometry_set_digest=_d("f"),
        old_split_ratio=(5, 1), new_split_ratio=(5, 1),
        old_split_seed=42, new_split_seed=42,
        requested_roles=("train", "monitor"), existing_materialized_roles=("train", "monitor"),
    )


def test_invalidation_matrix_unchanged_restart_is_zero_work():
    plan = mdstats.build_replay_invalidation_plan(**_base_kwargs())
    assert not plan.reindex_source
    assert not plan.rerun_pseudolabel_inference
    assert not plan.requalify
    assert not plan.resplit
    assert plan.rematerialize_roles == ()
    assert mdstats.ReplayInvalidationPlan.from_dict(plan.to_dict()) == plan


def test_invalidation_matrix_split_change_never_repredicts():
    kw = _base_kwargs(); kw["new_split_ratio"] = (4, 1)
    plan = mdstats.build_replay_invalidation_plan(**kw)
    assert not plan.reindex_source
    assert not plan.rerun_pseudolabel_inference
    assert not plan.requalify
    assert plan.resplit
    assert plan.rematerialize_roles == ("monitor", "train")


def test_invalidation_matrix_threshold_change_requalifies_without_reprediction():
    kw = _base_kwargs(); kw["new_qualification_policy_digest"] = _d("1")
    plan = mdstats.build_replay_invalidation_plan(**kw)
    assert not plan.rerun_pseudolabel_inference
    assert plan.requalify and plan.resplit


def test_invalidation_matrix_true_label_mutation_does_not_trigger_pseudo_inference():
    kw = _base_kwargs(); kw["new_source_sha256"] = _d("2"); kw["new_source_true_label_payload_digest"] = _d("3")
    pseudo = mdstats.build_replay_invalidation_plan(**kw)
    assert pseudo.reindex_source
    assert not pseudo.rerun_pseudolabel_inference
    assert not pseudo.requalify
    assert not pseudo.resplit

    kw["label_mode"] = "true_dft"
    true = mdstats.build_replay_invalidation_plan(**kw)
    assert true.reindex_source
    assert not true.rerun_pseudolabel_inference
    assert true.requalify and true.resplit
    assert true.rematerialize_roles == ("monitor", "train")


def test_invalidation_matrix_foundation_change_requires_reprediction():
    kw = _base_kwargs(); kw["new_prediction_policy_digest"] = _d("4")
    plan = mdstats.build_replay_invalidation_plan(**kw)
    assert plan.rerun_pseudolabel_inference
    assert plan.requalify and plan.resplit


def test_invalidation_matrix_geometry_change_invalidates_all_pseudo_layers():
    kw = _base_kwargs(); kw["new_source_sha256"] = _d("5"); kw["new_geometry_set_digest"] = _d("6")
    plan = mdstats.build_replay_invalidation_plan(**kw)
    assert plan.reindex_source
    assert plan.rerun_pseudolabel_inference
    assert plan.requalify and plan.resplit


def test_invalidation_matrix_additional_view_only_materializes_missing_role():
    kw = _base_kwargs(); kw["existing_materialized_roles"] = ("train",)
    plan = mdstats.build_replay_invalidation_plan(**kw)
    assert not plan.reindex_source and not plan.rerun_pseudolabel_inference
    assert not plan.requalify and not plan.resplit
    assert plan.rematerialize_roles == ("monitor",)


def _frame(marker: float) -> Atoms:
    atoms = Atoms("H2", positions=[[0, 0, 0], [0, 0, marker]], cell=np.eye(3)*5, pbc=True)
    atoms.info["REF_energy"] = -1.0 - marker
    atoms.arrays["REF_forces"] = np.zeros((2, 3))
    atoms.info["REF_stress"] = np.zeros(6)
    return atoms


def test_source_receipt_relocation_rebinds_locator_without_reparse(tmp_path: Path, monkeypatch):
    first = tmp_path / "first.extxyz"
    second = tmp_path / "moved.extxyz"
    write(first, [_frame(0.7), _frame(0.8)], format="extxyz")
    replay_root = tmp_path / ".mdstats" / "replay-unified"
    original = mdstats.inspect_replay_source_extxyz
    calls = {"n": 0}
    def counted(path):
        calls["n"] += 1
        return original(path)
    monkeypatch.setattr(mdstats, "inspect_replay_source_extxyz", counted)
    a = campaign_cli._load_or_inspect_single_replay_source(first, replay_root)
    shutil.copy2(first, second)
    b = campaign_cli._load_or_inspect_single_replay_source(second, replay_root)
    assert calls["n"] == 1
    assert a.content_digest == b.content_digest
    assert Path(b.path) == second.resolve()


def test_duplicate_source_geometry_still_fails_closed(tmp_path: Path):
    path = tmp_path / "dupe.extxyz"
    frame = _frame(0.7)
    write(path, [frame, frame.copy()], format="extxyz")
    with pytest.raises(mdstats.TrainingDataInputError, match="duplicate canonical geometry"):
        mdstats.inspect_replay_source_extxyz(path)
