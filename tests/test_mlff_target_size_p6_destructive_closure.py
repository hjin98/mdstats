"""P6 acceptance: the retired target-size architecture is structurally absent.

Three claims are kept separate here, because none of them may stand in for
another (P6 revision-4 section 5):

* the retired pre-V7 generation is rejected before any campaign record is read;
* a final-P6-created current workspace closes, reopens, and restarts unchanged;
* the retired V5/V6 target-size derived state is rejected before reuse.

The preserved P5A6 workspace claim lives in
``test_mlff_target_size_p6_p5a6_compatibility``.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import (
    load_current_selected_training_context,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_cv_acceptance,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_cutover import (
    QUARANTINE_KEY_PREFIX,
    RETIRED_TARGET_SIZE_RECORD_KEYS,
    TargetSizeCutoverError,
    require_current_target_size_runtime,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_revision,
)

from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    run_cross_validate,
    run_train_production,
)
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

_PACKAGE = Path(mdstats.__file__).resolve().parent

#: Modules deleted by the P6 destructive cutover.  Structural absence, not a
#: runtime guard, is the evidence that no wrapper keeps them reachable.
RETIRED_MODULE_NAMES = (
    "target_size_study",
    "target_data_roles",
    "size_fidelity",
    "production_materialization",
    "work_queue",
    "multi_fidelity_evaluation",
    "lightweight_rank",
    "campaign_execution",
    "data7_bundle",
    "data7_archive",
    "adaptive_full_evaluation",
    "adaptive_migration",
    "adaptive_verification",
    "mlcv_aggregate",
    "mlcv_final",
    "mlcv_migration",
    "mlcv_select",
    "mlcv_verification",
    "target_coverage",
    "target_coverage_store",
    "target_coverage_feasibility",
    "target_coverage_exact_neighborhood",
    "target_coverage_exact_neighborhood_store",
    "target_coverage_sparse_index",
    "target_coverage_sparse_index_store",
    "target_coverage_sparse_forward_view",
    "target_multi_view_selector",
    "target_multi_view_selector_v2",
    "target_multi_view_selector_v2_resume",
    "target_multi_view_selection_state",
    "target_multi_view_selection_state_store",
    "target_multi_view_selection_state_v2",
    "target_multi_view_selection_history_v2",
    "target_multi_view_repair",
    "target_multi_view_repair_v2",
    "target_multi_view_qualification_v2",
    "mvsel2_hardening_runtime",
    "mvsel2_native_backend",
    "mvsel2_native_preflight",
    "mvsel2_phase_a_kernel",
    "mvsel2_phase_b_kernel",
    "mvsel2_repair_checkpoint_runtime",
    "mvsel2_selection_engine",
    "mvsel2_streaming_frontier",
    "mvsel2_v5_runtime",
    "mvidx1_forward_receipt_runtime",
    "mvqual_p2_runtime",
    "_sparse_vector_kernels",
    "_target_coverage_neighborhood",
    "_target_multi_view_scoring",
)

#: Public symbols that named retired target-size authority.
RETIRED_PUBLIC_SYMBOLS = (
    "TargetDataRoleFreeze",
    "TargetDataDomainRoleFreeze",
    "TargetSizeStudyPlan",
    "TargetSizeStudyPolicy",
    "TargetSizeStudyCandidate",
    "FIXED_TARGET_SIZES",
    "FIXED_TARGET_SIZE_CEILING",
    "TargetCoverageReference",
    "TargetCoverageSparseIndex",
    "TargetMultiViewSelectionPlanV2",
    "TargetMultiViewRepairPlanV2",
    "TargetMultiViewQualificationPlanV2",
    "TargetMultiViewSelectionStateCache",
    "Eval2TargetRole",
    "build_target_size_study",
    "build_target_data_role_freeze",
    "build_eval2_size_study_target_role",
    "build_eval2_coarse_size_study_target_role",
    "build_eval2_cv_target_role",
    "validate_target_size_study_authority",
    "materialize_candidate_prefix",
    "materialize_selected_prefix",
    "ProductionMaterializationRecord",
    "ProductionMaterializationPlan",
    "MlcvFinalSelectionRecord",
    "MlcvRoleCatalog",
    "build_mlcv_role_catalog",
    "build_data8_preparation_bundle",
    "TrainingCampaignPlan",
    "AdaptiveMigrationRecord",
)


# --- structural absence ----------------------------------------------------


def test_p6_retired_modules_are_deleted_not_wrapped():
    present = [
        name
        for name in RETIRED_MODULE_NAMES
        if (_PACKAGE / "training_data" / f"{name}.py").exists()
    ]
    assert not present, present
    assert not (_PACKAGE / "_mvsel2_native.c").exists()


def test_p6_retired_public_symbols_are_unexported():
    offenders = [
        name
        for name in RETIRED_PUBLIC_SYMBOLS
        if hasattr(mdstats, name)
        or hasattr(mdstats.training_data, name)
        or name in mdstats.__all__
        or name in mdstats.training_data.__all__
    ]
    assert not offenders, offenders


def test_p6_no_source_file_references_a_retired_target_size_authority():
    """No surviving production module imports or names a retired owner."""

    needles = (
        "TargetDataRoleFreeze",
        "target_size_study",
        "target_multi_view",
        "target_coverage",
        "mvsel2_",
        "mvqual_p2",
        "mvidx1_forward",
        "FIXED_TARGET_SIZES",
        "domain_prefix_digests",
        "size_development_complement",
        "prescribed_target_size_evaluation_frames",
    )
    offenders: list[str] = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        if path.name in {"campaign_target_size_cutover.py", "campaign_cli.py"}:
            # The reject-only obsolete-generation detector must name the retired
            # record keys in order to recognise and quarantine them.  It reads
            # names only and never decodes a retired payload, which
            # `test_p6_quarantined_retired_state_is_never_semantically_decoded`
            # asserts structurally.  The CLI facade docstring records, in prose,
            # which retired runtimes it no longer installs.
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                offenders.append(f"{path.relative_to(_PACKAGE)}: {needle}")
    assert not offenders, offenders


def test_p6_public_command_surface_is_the_current_lifecycle_only():
    parser = cli.build_parser()
    sub = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    assert sorted(sub.choices) == [
        "advance",
        "cross-validate",
        "doctor",
        "guide",
        "init",
        "prepare",
        "select-target-size",
        "status",
        "storage",
        "train-production",
    ]


# --- retired configuration generation: reject before any record is read ----


@pytest.mark.parametrize(
    "generation", ["adaptive_stop_v3", "adaptive", "adaptive_stop", "legacy"]
)
def test_p6_retired_policy_generation_is_rejected_with_reset_guidance(
    tmp_path: Path, generation: str
):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    text = config.read_text(encoding="utf-8").replace(
        'policy_generation = "train2"', f'policy_generation = "{generation}"'
    )
    config.write_text(text, encoding="utf-8")
    with pytest.raises(cli.CampaignCliError) as excinfo:
        p4d._run(config, "prepare")
    message = str(excinfo.value)
    assert "retired" in message
    assert "train2" in message
    assert "prepare" in message


def test_p6_missing_policy_generation_is_rejected(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    text = config.read_text(encoding="utf-8").replace(
        'policy_generation = "train2"\n', ""
    )
    config.write_text(text, encoding="utf-8")
    with pytest.raises(cli.CampaignCliError) as excinfo:
        p4d._run(config, "prepare")
    assert "policy_generation" in str(excinfo.value)


# --- retired derived state: rejected before reuse ---------------------------


def test_p6_retired_target_size_workspace_is_rejected_before_reuse(tmp_path: Path):
    """A workspace holding retired derived target-size records refuses to run.

    The rejection comes from the real currentness owner and happens before any
    retired payload is deserialized: the record is written as an opaque mapping
    that no current loader could decode into V7 authority.
    """

    config, workspace = p4d._fixture_campaign(tmp_path)
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        for key in ("target_size_study", "target_data_role_freeze"):
            store.put_record(
                key,
                {
                    "schema": "mdstats.target-size-study-plan.v11",
                    "selected_target_size": 8192,
                    "qualified_sizes": [128, 256, 512],
                },
            )
        with pytest.raises(TargetSizeCutoverError) as excinfo:
            require_current_target_size_runtime(store)
    finally:
        store.close()
    message = str(excinfo.value)
    assert "retired target-size" in message
    assert "prepare" in message
    assert "never migrated" in message or "not migrated" in message

    # `prepare` performs the destructive cutover: the retired records are
    # quarantined under a namespace no current loader reads, never translated.
    assert cli.main(["--config", str(config), "prepare"]) == 0
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = require_current_target_size_runtime(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        live = set(store.record_keys())
        assert not (live & set(RETIRED_TARGET_SIZE_RECORD_KEYS))
        quarantined = [k for k in live if k.startswith(QUARANTINE_KEY_PREFIX)]
        assert any(k.endswith("target_size_study") for k in quarantined)
        # The retired selected size never becomes current authority.
        assert revision.state.terminal is None
    finally:
        store.close()


def test_p6_quarantined_retired_state_is_never_semantically_decoded():
    """The cutover reads record *names*; it never decodes a retired payload."""

    source = (
        _PACKAGE / "training_data" / "campaign_target_size_cutover.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    inventory = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "inventory_retired_target_size_state"
    )
    called = {
        node.func.attr
        for node in ast.walk(inventory)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "get_record" not in called
    assert "get_payload" not in called
    assert "record_keys" in called


# --- P6 -> P6 restart -------------------------------------------------------


def test_p6_current_workspace_closes_reopens_and_restarts_deterministically(
    tmp_path: Path,
):
    """A workspace created by the final P6 candidate survives close/reopen."""

    config, workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0

    def snapshot() -> dict[str, object]:
        cfg, paths = cli._load_config(config)
        store = CampaignStore(paths.state_db)
        try:
            revision = require_current_target_size_runtime(store)
            selected = load_current_selected_training_context(cfg, paths, store)
            context = build_post_selection_context(cfg, paths, store, trainer=None)
            acceptance = resolve_current_cv_acceptance(context)
            final_plan = resolve_current_final_production_plan(context)
            assert revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
            assert acceptance is not None and acceptance.accepted
            assert final_plan is not None
            return {
                "state": revision.state.content_digest,
                "generation": revision.state.generation,
                "n_selected": selected.n_selected,
                "membership": list(selected.selected_membership),
                "binding": selected.binding.content_digest,
                "method": context.method.content_digest,
                "acceptance": acceptance.content_digest,
                "final": final_plan.content_digest,
            }
        finally:
            store.close()

    first = snapshot()
    second = snapshot()
    assert first == second

    # Rerunning the owning commands on the reopened workspace is a no-op that
    # reauthenticates rather than rebuilding.
    assert run_cross_validate(config, PostSelectionHarness()) == 0
    assert run_train_production(config, PostSelectionHarness()) == 0
    assert snapshot() == first

    # `status` projects the complete current lifecycle from those same owners.
    assert cli.main(["--config", str(config), "status"]) == 0
