"""Restored post-selection method owners: identity, E0 transfer, monitor, folds.

Every assertion here is made against the real current owner.  Inputs below the
owner (a count matrix, a neutral partition view, a relation authority) are
small constructed values; nothing replaces the owner whose behavior is claimed.
"""

from __future__ import annotations

import hashlib
import math
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from mdstats.training_data._common import TrainingDataInputError, digest
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.online_monitor import (
    CommonTargetMonitorInfeasibleError,
    OnlineTargetMonitorPolicy,
    OnlineMonitorRecord,
    build_common_target_monitor,
    require_common_target_monitor_record,
)
from mdstats.training_data.partition import OuterRole
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_PREPARATION_SCHEMA,
    CompositionTransferResult,
    PostSelectionExecutionError,
    PostSelectionFittedPreparation,
    validate_composition_transfer,
)
from mdstats.training_data.post_selection_identity import (
    DEFAULT_CV_FOLD_COUNT,
    POST_SELECTION_COMPOSITION_TRANSFER_POLICY,
    POST_SELECTION_FOUNDATION_EXPOSURE_POLICY,
    POST_SELECTION_METHOD_RECIPE_VERSION,
    PostSelectionMethodIdentity,
    PostSelectionPreparationPolicy,
    resolve_cv_validation_policy_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
    resolve_post_selection_replay_training_label_mode,
)
from mdstats.training_data.reference_fit import (
    AtomicReferenceFitMode,
    AtomicReferenceFitPolicy,
    solve_atomic_reference_least_squares,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"


# ---------------------------------------------------------------------------
# PostSelectionMethodIdentity / preparation policy
# ---------------------------------------------------------------------------


def _foundation_cfg(tmp_path: Path, **tables) -> dict:
    from tests.test_mlff_target_size_p5_r9_guards import _write_tiny_mace_foundation

    foundation = tmp_path / "foundation.model"
    if not foundation.exists():
        _write_tiny_mace_foundation(foundation)
    cfg = {
        "paths": {"foundation_model": str(foundation)},
        "foundation": {"family": "mace_mpa_0", "head": "default"},
        "training": {"mode": "naive_fine_tuning", "device": "cpu"},
        "acceleration": {"backend": "e3nn"},
    }
    for name, table in tables.items():
        cfg.setdefault(name, {}).update(table)
    return cfg


def test_foundation_identity_binds_fixed_universal_objective_not_p3_policy(tmp_path: Path):
    base = _foundation_cfg(tmp_path)
    policies = resolve_post_selection_method_policies(base, config_dir=tmp_path)
    method = resolve_post_selection_method_identity(base, policies=policies)
    assert method.method_recipe_version == POST_SELECTION_METHOD_RECIPE_VERSION
    assert method.exposure_policy == POST_SELECTION_FOUNDATION_EXPOSURE_POLICY
    assert "common_training_policy_digest" not in method.to_dict()
    objective = policies.objective
    assert (
        objective.loss_family,
        objective.huber_delta,
        objective.energy_weight,
        objective.forces_weight,
        objective.stress_weight,
    ) == ("universal", 0.01, 1.0, 10.0, 1.0)
    payload = objective.to_dict()
    assert payload["dimensional_thresholds"] == {
        "energy": "0.01 eV/atom",
        "force_base": "0.01 eV/Angstrom",
        "stress": "0.01 eV/Angstrom^3",
    }
    preparation = policies.preparation.to_dict()
    assert preparation["atomic_reference_policy"]["fit_mode"] == "foundation_residual"
    assert preparation["composition_transfer_policy"] == POST_SELECTION_COMPOSITION_TRANSFER_POLICY
    assert "configuration_weight_policy" not in preparation
    # A P3-only objective, weighting, or harness edit changes nothing in P5.
    edited = _foundation_cfg(
        tmp_path,
        objective={"energy_weight": 5.0, "forces_weight": 100.0},
        weighting={"event_anchor_multiplier": 9.0},
        training={"harness_validation_frame_count": 12},
    )
    assert (
        resolve_post_selection_method_identity(
            edited,
            policies=resolve_post_selection_method_policies(edited, config_dir=tmp_path),
        ).content_digest
        == method.content_digest
    )
    # A genuine method-bearing change (dtype) invalidates dependent P5 evidence.
    precision = _foundation_cfg(tmp_path, training={"dtype": "float64"})
    assert (
        resolve_post_selection_method_identity(
            precision,
            policies=resolve_post_selection_method_policies(precision, config_dir=tmp_path),
        ).content_digest
        != method.content_digest
    )


def test_scratch_identity_keeps_its_weighted_preparation_and_objective():
    cfg = {"training": {"mode": "scratch", "device": "cpu"}, "acceleration": {"backend": "e3nn"}}
    policies = resolve_post_selection_method_policies(cfg)
    assert policies.objective.loss_family == "stress"
    assert policies.preparation.to_dict()["atomic_reference_policy"]["fit_mode"] == (
        "from_scratch_total_energy"
    )
    heavy = {**cfg, "objective": {"forces_weight": 100.0}}
    assert (
        resolve_post_selection_method_identity(heavy).objective_policy_digest
        != resolve_post_selection_method_identity(cfg).objective_policy_digest
    )


@pytest.mark.parametrize(
    "tables,match",
    (
        ({"training": {"target_head_weight": 5.0}}, "training-head scalar"),
        ({"training": {"replay_head_weight": 1.0}}, "training-head scalar"),
        ({"atomic_references": {"fit_mode": "from_scratch_total_energy"}}, "foundation-residual"),
        ({"atomic_references": {"ridge_lambda": 0.1}}, "prior/anchor"),
    ),
)
def test_foundation_configuration_fails_closed(tmp_path: Path, tables: dict, match: str):
    with pytest.raises(PostSelectionError, match=match):
        resolve_post_selection_method_policies(
            _foundation_cfg(tmp_path, **tables), config_dir=tmp_path
        )


def test_preparation_policy_is_mode_disjoint():
    foundation_fit = AtomicReferenceFitPolicy(fit_mode=AtomicReferenceFitMode.FOUNDATION_RESIDUAL)
    with pytest.raises(PostSelectionError, match="configuration-weight"):
        PostSelectionPreparationPolicy(
            training_mode="multihead_replay",
            atomic_reference_policy=foundation_fit,
            configuration_weight_policy=object(),
            foundation_checkpoint_digest="a" * 64,
            foundation_head="default",
            composition_transfer_policy=POST_SELECTION_COMPOSITION_TRANSFER_POLICY,
        )
    with pytest.raises(PostSelectionError, match="from-scratch"):
        PostSelectionPreparationPolicy(
            training_mode="scratch", atomic_reference_policy=foundation_fit
        )


def test_cv_policy_default_three_folds_and_retired_monitor_budget():
    policy = resolve_cv_validation_policy_identity({})
    assert DEFAULT_CV_FOLD_COUNT == 3 and policy.fold_count == 3
    assert "checkpoint_monitor_components_per_fold" not in policy.to_dict()
    assert resolve_cv_validation_policy_identity(
        {"post_selection": {"cv": {"fold_count": 2}}}
    ).fold_count == 2
    with pytest.raises(PostSelectionError, match="at least two folds"):
        resolve_cv_validation_policy_identity({"post_selection": {"cv": {"fold_count": 1}}})
    with pytest.raises(PostSelectionError, match="retired"):
        resolve_cv_validation_policy_identity(
            {"post_selection": {"cv": {"checkpoint_monitor_components_per_fold": 1}}}
        )


def test_replay_label_defaults_true_dft_and_ambiguous_legacy_omission_fails():
    from mdstats.training_data.replay import (
        ReplayLabelMode,
        normalize_single_source_replay_label_mode,
    )

    assert normalize_single_source_replay_label_mode({}) is ReplayLabelMode.TRUE_DFT
    legacy = {"paths": {"replay_train": "a.xyz", "replay_monitor": "b.xyz"}}
    with pytest.raises(PostSelectionError, match="explicit"):
        resolve_post_selection_replay_training_label_mode(legacy)
    assert (
        resolve_post_selection_replay_training_label_mode(
            {**legacy, "replay": {"mode": "external_pseudolabel"}}
        )
        is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    )


def test_historical_method_identity_payload_is_not_current():
    with pytest.raises(Exception, match="schema"):
        PostSelectionMethodIdentity.from_dict(
            {"schema": "mdstats.post-selection-method-identity.v1"}
        )


# ---------------------------------------------------------------------------
# Composition-level E0 transfer (D2 section 8.4 oracles)
# ---------------------------------------------------------------------------


def _fit(rows: list[list[int]], elements: tuple[int, ...]):
    matrix = np.asarray(rows, dtype=np.float64)
    solve = solve_atomic_reference_least_squares(
        matrix, np.zeros(matrix.shape[0]), AtomicReferenceFitPolicy()
    )
    return SimpleNamespace(rank=solve.rank, element_order=elements)


def _classes(rows: list[list[int]], elements: tuple[int, ...]):
    return [tuple((z, n) for z, n in zip(elements, row) if n) for row in rows]


def _transfer(fit_rows, required_rows, elements=(3, 8)):
    return validate_composition_transfer(
        _fit(fit_rows, elements),
        fit_compositions=_classes(fit_rows, elements),
        required_compositions=_classes(required_rows, elements),
        relative_singular_value_tolerance=1.0e-12,
    )


def test_rank_deficient_fit_transfers_only_row_space_compositions():
    # Fit rows proportional to [1, 1]: elemental coefficients are not unique.
    admissible = _transfer([[1, 1], [2, 2]], [[3, 3]])
    assert admissible.transferable
    assert admissible.exact_rank == 1 and len(admissible.null_space_basis) == 1
    rejected = _transfer([[1, 1], [2, 2]], [[2, 1]])
    assert not rejected.transferable
    assert rejected.non_transferable_compositions == (((3, 2), (8, 1)),)


def test_absent_element_is_non_transferable_without_anchor():
    result = validate_composition_transfer(
        _fit([[1, 1], [1, 2]], (3, 8)),
        fit_compositions=[((3, 1), (8, 1)), ((3, 1), (8, 2))],
        required_compositions=[((3, 1), (8, 1), (11, 1))],
        relative_singular_value_tolerance=1.0e-12,
    )
    assert not result.transferable
    assert result.element_order == (3, 8, 11)


def test_numerical_rank_disagreement_fails_rather_than_interpreting_minimum_norm():
    fit = SimpleNamespace(rank=2, element_order=(3, 8))
    with pytest.raises(PostSelectionExecutionError, match="ill-conditioned"):
        validate_composition_transfer(
            fit,
            fit_compositions=[((3, 1), (8, 1))],
            required_compositions=[((3, 1), (8, 1))],
            relative_singular_value_tolerance=1.0e-12,
        )


def test_transfer_result_rejects_an_anchor_and_round_trips():
    result = _transfer([[1, 1], [1, 2]], [[4, 5]])
    assert CompositionTransferResult.from_dict(result.to_dict()) == result
    payload = result.to_dict()
    payload["anchor_identity"] = "x"
    payload.pop("content_digest")
    with pytest.raises(PostSelectionExecutionError, match="anchor"):
        CompositionTransferResult.from_dict(payload)


@settings(max_examples=60, deadline=None)
@given(
    rows=st.lists(
        st.lists(st.integers(min_value=0, max_value=6), min_size=3, max_size=3),
        min_size=1,
        max_size=4,
    ).filter(lambda rows: any(any(row) for row in rows)),
    coefficients=st.lists(st.integers(min_value=-3, max_value=3), min_size=4, max_size=4),
    null_scale=st.integers(min_value=1, max_value=4),
)
def test_transfer_matches_exact_row_space_membership(rows, coefficients, null_scale):
    """Property: c transfers iff it is an exact rational row-space vector."""

    elements = (3, 8, 11)
    rows = [row for row in rows if any(row)]
    candidate = [
        sum(Fraction(coefficient) * row[i] for coefficient, row in zip(coefficients, rows))
        for i in range(3)
    ]
    if any(v < 0 or v.denominator != 1 for v in candidate) or not any(candidate):
        return
    candidate_row = [int(v) for v in candidate]
    fit = _fit(rows, elements)
    in_space = validate_composition_transfer(
        fit,
        fit_compositions=_classes(rows, elements),
        required_compositions=_classes([candidate_row], elements),
        relative_singular_value_tolerance=1.0e-12,
    )
    assert in_space.transferable
    null = [Fraction(v) for v in in_space.null_space_basis[0]] if in_space.null_space_basis else None
    if null is None:
        return
    shifted = [candidate_row[i] + null_scale * null[i] for i in range(3)]
    if any(v < 0 or v.denominator != 1 for v in shifted) or not any(shifted):
        return
    out_of_space = validate_composition_transfer(
        fit,
        fit_compositions=_classes(rows, elements),
        required_compositions=_classes([[int(v) for v in shifted]], elements),
        relative_singular_value_tolerance=1.0e-12,
    )
    assert not out_of_space.transferable


def test_foundation_preparation_rejects_cross_mode_and_historical_payloads():
    with pytest.raises(Exception, match="schema"):
        PostSelectionFittedPreparation.from_dict(
            {"schema": "mdstats.post-selection-fitted-preparation.v2"}
        )
    with pytest.raises(Exception, match="cross-mode"):
        PostSelectionFittedPreparation.from_dict(
            {
                "schema": POST_SELECTION_PREPARATION_SCHEMA,
                "training_mode": "multihead_replay",
                "fitted_weights_digest": "a" * 64,
            }
        )


# ---------------------------------------------------------------------------
# Exact common target monitor (D2 section 15 oracles)
# ---------------------------------------------------------------------------


def _record(uid: str, run: str, index: int, *, labeled: bool = True):
    return SimpleNamespace(
        frame_uid=uid,
        run_id=run,
        source_frame_index=index,
        has_authoritative_label=labeled,
        energy_present=labeled,
        forces_present=True,
    )


def _authorities(units: dict[str, tuple[str, str, list]]):
    """units: unit_id -> (condition_id, run_id, records)."""

    frames = {record.frame_uid: record for _c, _r, records in units.values() for record in records}
    catalog = SimpleNamespace(
        unit=lambda unit_id: SimpleNamespace(
            condition=SimpleNamespace(condition_id=units[unit_id][0]),
            run_id=units[unit_id][1],
            frame_uids=tuple(record.frame_uid for record in units[unit_id][2]),
        ),
        content_digest="c" * 64,
    )
    partition = SimpleNamespace(
        unit_ids_for_role=lambda role: tuple(units) if role is OuterRole.OUTER_MONITOR else (),
        content_digest="d" * 64,
    )
    return SimpleNamespace(
        neutral_base=SimpleNamespace(outer_partition=partition, unit_catalog=catalog),
        frame_authority=SimpleNamespace(frame=frames.__getitem__, content_digest="e" * 64),
    )


def _independent_monitor(strata: dict[str, list]) -> list[str]:
    """Reconstruct D2 15.2-15.3 without the production helpers."""

    seed, size = 161803, 256
    ordered = {k: sorted(v, key=lambda r: (r.source_frame_index, r.frame_uid)) for k, v in strata.items()}
    order = sorted(
        ordered,
        key=lambda s: (hashlib.sha256(f"{seed}\0quota\0{s}".encode()).hexdigest(), s),
    )
    quotas = {s: 0 for s in ordered}
    assigned = 0
    while assigned < size:
        for s in order:
            if assigned < size and quotas[s] < len(ordered[s]):
                quotas[s] += 1
                assigned += 1
    selected = []
    for s, values in ordered.items():
        n, k = len(values), quotas[s]
        if not k:
            continue
        if k == n:
            positions = range(n)
        else:
            raw = hashlib.sha256(f"{seed}\0target:{s}".encode()).digest()
            u = (int.from_bytes(raw[:8], "big") + 0.5) / 2**64
            positions = [min(n - 1, math.floor((j + u) * n / k)) for j in range(k)]
        selected.extend(values[p] for p in positions)
    selected.sort(key=lambda r: (r.run_id, r.source_frame_index, r.frame_uid))
    return [r.frame_uid for r in selected]


def _uid(label: str) -> str:
    return digest({"frame": label})


def test_common_monitor_reconstructs_d2_sampler_exactly():
    units = {}
    strata = {}
    for condition, run, count in (("c1", "runA", 150), ("c1", "runB", 40), ("c2", "runC", 120)):
        records = [_record(_uid(f"{run}-{i}"), run, i) for i in range(count)]
        units[digest({"unit": run})] = (condition, run, records)
        strata[f"{condition}:{run}"] = records
    record = build_common_target_monitor(_authorities(units))
    require_common_target_monitor_record(record)
    assert record.realized_size == 256 and record.parent_role == "neutral_outer_monitor"
    assert list(record.selected_identities) == _independent_monitor(strata)
    assert {key: selected for key, _available, selected in record.stratum_counts} == {
        "c1:runA": 108, "c1:runB": 40, "c2:runC": 108,
    }


def test_common_monitor_shortfall_after_label_usability_is_infeasible():
    records = [_record(_uid(f"r-{i}"), "run", i, labeled=i >= 10) for i in range(260)]
    with pytest.raises(CommonTargetMonitorInfeasibleError, match="250 label-usable"):
        build_common_target_monitor(_authorities({digest({"u": 1}): ("c", "run", records)}))


def test_monitor_record_requirement_rejects_fallback_and_short_records():
    policy = OnlineTargetMonitorPolicy()
    base = dict(
        role="target", parent_digest="a" * 64, policy_digest=policy.policy_digest,
        requested_size=256, realized_size=255,
        selected_identities=tuple(str(i) for i in range(255)),
        source_indices=tuple(range(255)), stratum_counts=(("s", 300, 255),),
        strategy=policy.strategy, seed=policy.seed, label_mode="true_dft",
        parent_role="neutral_outer_monitor",
    )
    with pytest.raises(CommonTargetMonitorInfeasibleError):
        require_common_target_monitor_record(OnlineMonitorRecord(**base))
    with pytest.raises(CommonTargetMonitorInfeasibleError):
        require_common_target_monitor_record(
            OnlineMonitorRecord(**{**base, "parent_role": "data5_outer_monitor", "realized_size": 256,
                                   "selected_identities": tuple(str(i) for i in range(256)),
                                   "source_indices": tuple(range(256)),
                                   "stratum_counts": (("s", 300, 256),)})
        )
    with pytest.raises(TrainingDataInputError, match="fixed"):
        OnlineTargetMonitorPolicy(size=128)


# ---------------------------------------------------------------------------
# P1 cross-role separation
# ---------------------------------------------------------------------------


def _separation_inputs(groups):
    from mdstats.training_data.neutral_substrate.split_exclusion import (
        NeutralSplitExclusionEvidence,
        NeutralSplitExclusionGroup,
    )

    monitor_uids = [_uid(f"m-{i}") for i in range(256)]
    target_uids = [_uid(f"t-{i}") for i in range(8)]
    evidence = NeutralSplitExclusionEvidence(
        dataset_id="d",
        frame_authority_digest="e" * 64,
        unit_catalog_digest="c" * 64,
        groups=tuple(
            NeutralSplitExclusionGroup(relation_kind=kind, relation_key=str(i), frame_uids=tuple(uids))
            for i, (kind, uids) in enumerate(groups(monitor_uids, target_uids))
        ),
    )
    policy = OnlineTargetMonitorPolicy()
    monitor = OnlineMonitorRecord(
        role="target", parent_digest="a" * 64, policy_digest=policy.policy_digest,
        requested_size=256, realized_size=256, selected_identities=tuple(monitor_uids),
        source_indices=tuple(range(256)), stratum_counts=(("s", 300, 256),),
        strategy=policy.strategy, seed=policy.seed, label_mode="true_dft",
        parent_role="neutral_outer_monitor",
    )
    authorities = SimpleNamespace(
        split_exclusion=evidence,
        frame_authority=SimpleNamespace(content_digest="e" * 64),
        neutral_base=SimpleNamespace(unit_catalog=SimpleNamespace(content_digest="c" * 64)),
    )
    context = SimpleNamespace(
        authorities=authorities,
        binding=SimpleNamespace(split_exclusion_digest=evidence.content_digest),
        selected_membership=tuple(target_uids),
        selected_membership_digest=digest({"frame_uids": target_uids}),
    )
    return context, monitor


def test_transitive_cross_role_relation_through_an_outside_frame_is_a_collision():
    from mdstats.training_data.post_selection_cv_plan import (
        CommonMonitorSeparationError,
        build_common_monitor_separation,
    )

    outside = _uid("outside")
    context, monitor = _separation_inputs(
        lambda m, t: [("correlation_unit", [m[3], outside]), ("replica_lineage", [outside, t[5]])]
    )
    # Exact frame disjointness holds; only the complete relation closure sees it.
    assert not set(monitor.selected_identities) & set(context.selected_membership)
    with pytest.raises(CommonMonitorSeparationError, match="protected-relation"):
        build_common_monitor_separation((context,), monitor)


def test_relation_disjoint_monitor_binds_separation_evidence():
    from mdstats.training_data.post_selection_cv_plan import build_common_monitor_separation

    context, monitor = _separation_inputs(
        lambda m, t: [("correlation_unit", [m[0], m[1]]), ("correlation_unit", [t[0], t[1]])]
    )
    evidence = build_common_monitor_separation((context,), monitor)
    assert evidence.common_monitor_record_digest == monitor.content_digest
    assert evidence.governed_target_membership_digests == (context.selected_membership_digest,)


# ---------------------------------------------------------------------------
# Structural negative evidence for retired current owners
# ---------------------------------------------------------------------------


def test_retired_p5_owners_have_no_current_source_reference():
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in _TRAINING_DATA.glob("*.py")
    }
    for name in (
        "frozen_m3_development_evidence",
        "checkpoint_monitor_components_per_fold",
        "target_head_weight",
        "replay_head_weight",
        "_reevaluate_run_representative_records",
        "MACE_EXECUTABLE_LOSS_FAMILY",
    ):
        holders = sorted(
            file
            for file, text in sources.items()
            if name in text
            and not (file == "post_selection_identity.py" and name in {
                "checkpoint_monitor_components_per_fold", "target_head_weight", "replay_head_weight",
            })
        )
        assert holders == [], (name, holders)
    runtime = sources["campaign_post_selection_runtime.py"]
    assert "mlcv_monitors" not in runtime and "build_target_online_monitor" not in runtime
    patch_source = sources["critical_precision_cli.py"]
    assert "args.loss = 'stress'" not in patch_source


# ---------------------------------------------------------------------------
# Selected-head foundation-residual inputs (real MACE provider)
# ---------------------------------------------------------------------------


def _multihead_foundation(tmp_path: Path):
    torch = pytest.importorskip("torch")
    from tests._mlff_tiny_mace import _tiny_mace
    from mdstats.training_data.post_selection_identity import (
        resolve_post_selection_foundation_identity,
    )

    path = tmp_path / "multihead.model"
    model = _tiny_mace(
        atomic_numbers=(3, 8),
        heads=["first", "selected"],
        seed=3,
        dtype=torch.float64,
        atomic_energies=((-1.0, -2.0), (-3.0, -4.0)),
    )
    # Per-head interaction scale/shift, as in a real multi-head checkpoint.
    model.scale_shift.scale = torch.tensor([1.0, 2.0], dtype=torch.float64)
    model.scale_shift.shift = torch.tensor([0.0, 0.5], dtype=torch.float64)
    torch.save(model, path)

    def identity(head):
        return resolve_post_selection_foundation_identity(
            path, requested_head=head, model_family="mace_custom"
        )

    return path, identity


def _frame_context(count: int = 3):
    from ase import Atoms

    records = {}
    for index in range(count):
        uid = _uid(f"residual-{index}")
        atoms = Atoms(
            "LiO", positions=((0.1 + 0.01 * index, 0.0, 0.0), (1.8, 0.0, 0.0)),
            cell=np.eye(3) * 8.0, pbc=True,
        )
        record = SimpleNamespace(frame_uid=uid, run_id="run", source_frame_index=index)
        data = SimpleNamespace(
            atomic_numbers=atoms.numbers,
            cells_angstrom=[atoms.cell.array],
            fractional_positions=[atoms.get_scaled_positions()],
            pbc=atoms.pbc,
        )
        records[uid] = (record, data, 0)
    return SimpleNamespace(authorities=SimpleNamespace(frame_array_index=records)), tuple(records)


def test_residual_inputs_use_the_selected_head_not_the_first_or_default(tmp_path: Path):
    from mdstats.training_data.post_selection_execution import (
        resolve_foundation_residual_inputs,
    )

    path, identity = _multihead_foundation(tmp_path)
    context, frames = _frame_context()
    selected = resolve_foundation_residual_inputs(
        context, membership=frames, foundation_model_path=path,
        foundation_identity=identity("selected"), foundation_head="selected",
        device="cpu", default_dtype="float64", execution_batch_width=2,
    )
    first = resolve_foundation_residual_inputs(
        context, membership=frames, foundation_model_path=path,
        foundation_identity=identity("first"), foundation_head="first",
        device="cpu", default_dtype="float64", execution_batch_width=2,
    )
    # The E0 table row and the predictions both belong to the selected head.
    assert selected.reference_energies == {3: -3.0, 8: -4.0}
    assert first.reference_energies == {3: -1.0, 8: -2.0}
    assert selected.prediction_energies_ev != first.prediction_energies_ev
    assert selected.prediction_digest != first.prediction_digest
    # A head that disagrees with the authenticated identity fails closed.
    with pytest.raises(PostSelectionExecutionError, match="exact selected"):
        resolve_foundation_residual_inputs(
            context, membership=frames, foundation_model_path=path,
            foundation_identity=identity("first"), foundation_head="selected",
            device="cpu", default_dtype="float64", execution_batch_width=2,
        )
