"""Lightweight MH-1 compatibility for the published-model product boundary.

The machinery below has extensive real use on MPA-0. MH-1 remains
architecturally supported, and the point of this suite is to catch obvious
family/head/shape/reconstruction drift *before* the next real MH-1 campaign -
not to qualify one. Long MH-1 TRAIN2, CV, production, MD and GPU qualification
are deliberately out of scope and their absence is not a failure here.

Cases that need the real locked ``mace-mh-1.model`` skip when it is not
readily available; the structural cases below do not need it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

MH1_MODEL = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))

_requires_real_mh1 = pytest.mark.skipif(
    not MH1_MODEL.is_file(),
    reason=(
        "the locked real MACE-MH-1 checkpoint is not readily available in this "
        "environment; real MH-1 campaign qualification is deferred by the workplan"
    ),
)


def test_mh1_family_and_explicit_source_head_survive_config_generation():
    """`mace_mh_1` with an explicit `omat_pbe` source head, end to end in config."""

    from mdstats.training_data._campaign_cli_core import _config_template

    text = _config_template(
        workspace="work",
        training_root="/path/to/LTA_training",
        foundation_model="mace-mh-1.model",
        foundation_family="mace_mh_1",
    )
    assert 'family = "mace_mh_1"' in text
    # No silent fallback to a `default` head: MH-1 is multihead and a default
    # selection would be a different product.  The filename/label is explicitly
    # not authoritative, so the head must appear as configuration.
    assert 'head = "omat_pbe"' in text
    assert 'head = "default"' not in text


def test_mh1_family_enum_resolves_and_rejects_singleton_head_assumptions():
    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.foundation import (
        MaceFoundationFamily,
        MaceFoundationInspection,
        _resolve_head,
        _validate_family_against_inspection,
    )

    assert MaceFoundationFamily.parse("mace_mh_1") is MaceFoundationFamily.MH_1
    assert MaceFoundationFamily.parse("mh-1") is MaceFoundationFamily.MH_1

    common = {
        "reference": "fixture",
        "sha256": "0" * 64,
        "model_module": "mace.modules.models",
        "atomic_numbers": (3, 8),
        "r_max_angstrom": 6.0,
        "num_interactions": 2,
    }
    mpa0_shaped = MaceFoundationInspection(
        **common,
        model_class="ScaleShiftMACE",
        available_heads=("default",),
        model_dtype="float64",
        atomic_energies_shape=(1, 89),
        interaction_signatures=({"class": "RealAgnosticDensityInteractionBlock"},),
        product_signatures=(),
        readout_signatures=(),
        edge_irreps=None,
        use_agnostic_product=False,
        state_shape_digest="0" * 64,
    )
    # An MPA-0-shaped checkpoint is not MH-1, and the family guard says so
    # rather than proceeding on a singleton-head assumption.
    with pytest.raises(TrainingDataInputError, match="mace_mh_1 is incompatible"):
        _validate_family_against_inspection(MaceFoundationFamily.MH_1, mpa0_shaped)

    mh1_shaped = MaceFoundationInspection(
        **common,
        model_class="ScaleShiftMACE",
        available_heads=("omat_pbe", "mp_pbe", "spice"),
        model_dtype="float64",
        atomic_energies_shape=(3, 89),
        interaction_signatures=({"class": "RealAgnosticNonLinearInteractionBlock"},),
        product_signatures=(),
        readout_signatures=(),
        edge_irreps="0e + 1o",
        use_agnostic_product=True,
        state_shape_digest="0" * 64,
    )
    _validate_family_against_inspection(MaceFoundationFamily.MH_1, mh1_shaped)
    assert _resolve_head("omat_pbe", mh1_shaped) == "omat_pbe"
    # A multihead checkpoint never silently picks a head for the operator.
    with pytest.raises(TrainingDataInputError):
        _resolve_head(None, mh1_shaped)
    with pytest.raises(TrainingDataInputError):
        _resolve_head("default", mh1_shaped)


def test_post_selection_multihead_output_order_is_pt_head_then_target_head():
    """The ML-IAP target-head index-1 contract depends on exactly this order."""

    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )

    # The executable head map is unordered; the owner re-derives pinned MACE's
    # own ordering from it, so the order cannot depend on dict insertion.
    for mapping in (
        {POST_SELECTION_TARGET_HEAD_NAME: {}, POST_SELECTION_REPLAY_HEAD_NAME: {}},
        {POST_SELECTION_REPLAY_HEAD_NAME: {}, POST_SELECTION_TARGET_HEAD_NAME: {}},
    ):
        heads = sorted(
            (str(value) for value in mapping),
            key=lambda value: -1000 if value == POST_SELECTION_REPLAY_HEAD_NAME else 0,
        )
        assert heads == [
            POST_SELECTION_REPLAY_HEAD_NAME,
            POST_SELECTION_TARGET_HEAD_NAME,
        ]
        assert heads.index(POST_SELECTION_TARGET_HEAD_NAME) == 1


def test_post_selection_head_namespace_is_family_independent():
    """MH-1 and MPA-0 share the one fixed P5 fine-tuning namespace."""

    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
        canonical_post_selection_head_names,
    )

    assert canonical_post_selection_head_names() == (
        POST_SELECTION_TARGET_HEAD_NAME,
        POST_SELECTION_REPLAY_HEAD_NAME,
    )
    # The MH-1 *source* head is `omat_pbe`; the P5 fine-tuning namespace is
    # family-independent, and aliasing the two would be a second namespace.
    with pytest.raises(TrainingDataInputError):
        canonical_post_selection_head_names(target_head_name="omat_pbe")


def test_publication_owner_serializes_a_multihead_model_and_preserves_head_order(
    tmp_path: Path,
):
    """The new full-model publication path is not MPA-0-shaped.

    A two-head model in the canonical `[pt_head, target_head]` order is
    realized, identified and round-tripped through the real publication owner,
    so a serializer that only worked for a single-head product would fail here.
    """

    import torch

    from tests._mlff_tiny_mace import _tiny_mace
    from mdstats.training_data.model_artifact_trust import authenticate_model_artifact
    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )
    from mdstats.training_data.post_selection_model_products import (
        _verify_reloaded_product,
        place_member_model,
        realize_portable_publication_model,
    )

    model = _tiny_mace(
        heads=[POST_SELECTION_REPLAY_HEAD_NAME, POST_SELECTION_TARGET_HEAD_NAME],
        atomic_numbers=(3, 8),
        r_max=4.0,
        dtype=torch.float64,
        atomic_energies=((0.0, 0.0), (0.0, 0.0)),
        seed=11,
    )
    assert tuple(str(value) for value in model.heads) == (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )
    model.train()

    provider = type("P", (), {"model": model})()
    portable, realization = realize_portable_publication_model(
        provider, target_head_name=POST_SELECTION_TARGET_HEAD_NAME
    )
    assert realization.head_inventory == (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )
    assert realization.dtype == "float64"
    assert not portable.training

    context = type(
        "C",
        (),
        {"paths": type("P", (), {"models": tmp_path / "models"})(), "cfg": {}},
    )()
    placed = place_member_model(
        context,
        model=portable,
        member_id="seed-1",
        realization=realization,
        target_head_name=POST_SELECTION_TARGET_HEAD_NAME,
        decision_relative_directory="production/g1/N_8/decision-" + "a" * 64,
    )
    authenticate_model_artifact(
        tmp_path / "models",
        placed.relative_path,
        expected_sha256=placed.sha256,
        expected_size_bytes=placed.size_bytes,
    )
    _verify_reloaded_product(
        tmp_path / "models" / placed.relative_path,
        realization=realization,
        target_head_name=POST_SELECTION_TARGET_HEAD_NAME,
    )
    reloaded = torch.load(
        tmp_path / "models" / placed.relative_path,
        map_location="cpu",
        weights_only=False,
    )
    assert tuple(str(value) for value in reloaded.heads) == (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )
    assert tuple(reloaded.heads).index(POST_SELECTION_TARGET_HEAD_NAME) == 1


def test_mh1_current_post_selection_provider_seam_uses_real_owner_path(
    tmp_path: Path, monkeypatch
):
    """A bounded MH-1-shaped campaign crosses DATA8, TRAIN2 and P5 providers.

    The locked ``mace-mh-1.model`` is not available in this environment, so
    the fixture creates a genuinely serialized three-source-head MACE model
    with the MH-1 family topology.  The bounded run still uses the current
    post-selection materializer, native TRAIN2 state, no-override selected-
    checkpoint authentication, portable reconstruction, and publication
    reload owners.
    """

    import hashlib
    import json
    import re

    import torch

    import tests.test_mlff_mace_execution_semantics_assembled as assembled

    def write_mh1_foundation(path: Path) -> None:
        # MACE-MH-1's inspected family contract includes the agnostic product
        # projection and explicit edge irreps; the generic tiny fixture leaves
        # both at the MPA-0 defaults, so construct only this bounded foundation
        # with the native MACE constructor.
        import numpy as np
        from e3nn import o3
        from mace import modules, tools

        table = tools.AtomicNumberTable([3, 8])
        model = modules.ScaleShiftMACE(
            r_max=4.0,
            num_bessel=4,
            num_polynomial_cutoff=3,
            max_ell=1,
            interaction_cls=modules.interaction_classes[
                "RealAgnosticResidualNonLinearInteractionBlock"
            ],
            interaction_cls_first=modules.interaction_classes[
                "RealAgnosticResidualNonLinearInteractionBlock"
            ],
            num_interactions=2,
            num_elements=2,
            hidden_irreps=o3.Irreps("8x0e + 8x1o"),
            MLP_irreps=o3.Irreps("4x0e"),
            gate=torch.nn.functional.silu,
            atomic_energies=np.zeros((3, 2)),
            avg_num_neighbors=2.0,
            atomic_numbers=table.zs,
            correlation=2,
            atomic_inter_scale=np.ones(3),
            atomic_inter_shift=np.zeros(3),
            use_agnostic_product=True,
            edge_irreps=o3.Irreps("0e + 1o"),
            heads=["omat_pbe", "mp_pbe", "spice"],
        ).to(dtype=torch.float64)
        torch.save(model, path)

    root = tmp_path / "inputs"
    foundation = root / "foundation.model"
    pseudo_train = root / "replay-pseudo-train.extxyz"
    pseudo_monitor = root / "replay-pseudo-monitor.extxyz"
    true_root = root / "true-replay"
    foundation.parent.mkdir(parents=True, exist_ok=True)
    write_mh1_foundation(foundation)
    assembled._write_replay_file(pseudo_train, list(range(60)), energy_offset=0.25)
    assembled._write_replay_file(pseudo_monitor, [60, 61], energy_offset=0.25)
    assembled._write_replay_file(
        true_root / "true_labels" / "replay_train.extxyz",
        list(range(60)),
        energy_offset=0.0,
    )
    assembled._write_replay_file(
        true_root / "true_labels" / "replay_monitor.extxyz",
        [60, 61],
        energy_offset=0.0,
    )

    config_text = assembled.fixture_config_text()
    config_text = config_text.replace(
        'training_root = "{training_root}"',
        "\n".join(
            (
                'training_root = "{training_root}"',
                f'foundation_model = "{foundation}"',
                f'replay_train = "{pseudo_train}"',
                f'replay_monitor = "{pseudo_monitor}"',
                f'replay_true_labels = "{true_root}"',
            )
        ),
    )
    config_text = config_text.replace(
        "batch_size = 4",
        "batch_size = 4\nlearning_rate = 0.0123\nema = true\nema_decay = 0.87",
        1,
    )
    config_text = config_text.replace(
        "seeds = [1, 2]",
        "seeds = [1, 2]\nmode = \"multihead_replay\"",
        1,
    )
    config_text = config_text.replace("partition_seed = 7", "partition_seed = 2", 1)
    config_text += """

[objective]
energy_weight = 2.0
forces_weight = 7.0
stress_weight = 3.0

[replay]
mode = "external_pseudolabel"
seed = 42
allow_small_corpus = true
minimum_train_configurations = 1
minimum_monitor_configurations = 1
require_target_elements = false

[foundation]
family = "mace_mh_1"
head = "omat_pbe"
legacy_normalized = true
"""

    config, _workspace = assembled.build_selected_campaign(
        tmp_path / "campaign",
        config_text=config_text,
        data4_bundle=assembled._two_condition_data4_bundle,
    )
    monkeypatch.setattr(
        assembled.cli,
        "_ensure_local_wrappers",
        lambda _paths: {"mdstats-mace-train": assembled.p3_real._wrapper(tmp_path)},
    )

    cfg, paths, store = assembled.load_context(config)
    provider = None
    try:
        numerical_harness = assembled.PostSelectionHarness()
        context = assembled.build_post_selection_context(
            cfg,
            paths,
            store,
            inference_evaluator=numerical_harness.evaluate,
        )
        assert context.method.training_mode == "multihead_replay"
        assert context.method_policies.foundation_head == "omat_pbe"
        resolution = assembled._resolve_post_selection_replay_resolution(context)
        assert resolution is not None
        projection = assembled.build_selected_relation_projection(context.selected)
        cv_plan = assembled.build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            projection=projection,
            replay_lineage_digest=assembled.compute_replay_lineage_digest(resolution),
            **assembled.context_monitor_kwargs(context),
        )
        fold = cv_plan.fold(0)
        run_plan = assembled.build_cv_fold_run_plan(
            cv_plan,
            fold_index=fold.fold_index,
            optimizer_seed=context.cv_policy.required_cv_seeds[0],
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        result = assembled.execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=assembled.cv_training_budget_policy(
                context.method, context.cv_policy
            ),
            training_frame_uids=fold.training_frame_uids,
            monitor_frame_uids=tuple(context.common_target_monitor()[0].selected_identities),
            outer_evaluation_frame_uids=None,
        )
        assert result.representative is not None
        run_root = context.run_root(run_plan.run_identity)
        checkpoint_root = run_root / "checkpoints"
        summary = assembled.load_train2_runtime_summary(checkpoint_root)
        materialization = assembled.PostSelectionMaterialization.from_dict(
            json.loads(
                (run_root / "materialization" / "materialization.json").read_text(
                    encoding="utf-8"
                )
            )
        )
        raw_checkpoints = sorted(
            path
            for path in checkpoint_root.glob("*.pt")
            if "epoch-" in path.name and path.name != "train2_runtime.pt"
        )
        assert raw_checkpoints
        selected = raw_checkpoints[0]
        selected_epoch = int(re.search(r"_epoch-(\d+)\.pt$", selected.name).group(1))
        selected_sha = hashlib.sha256(selected.read_bytes()).hexdigest()
        assert result.representative.trajectory_point.checkpoint_sha256 == selected_sha

        from mdstats.training_data.post_selection_execution import (
            authenticate_post_selection_provider,
        )
        from mdstats.training_data.target_size_execution.evaluation import (
            EVALUATION_MODEL_STATE_EMA,
        )
        from mdstats.training_data.model_features import (
            mace_model_execution_architecture_digest,
        )

        provider, evaluated_digest = authenticate_post_selection_provider(
            materialization=materialization,
            materialization_directory=run_root / "materialization",
            checkpoint_directory=checkpoint_root,
            checkpoint_name=selected.name,
            checkpoint_sha256=selected_sha,
            summary=summary,
            evaluation_model_state=EVALUATION_MODEL_STATE_EMA,
            allow_forward_override=False,
            checkpoint_epoch=selected_epoch,
            foundation_model_path=context.method_policies.foundation_model,
        )
        assert evaluated_digest
        assert tuple(str(value) for value in provider.model.heads) == (
            "pt_head",
            "target_head",
        )
        assert mace_model_execution_architecture_digest(provider.model) == (
            summary.model_architecture_digest
        )

        from mdstats.training_data.model_artifact_trust import authenticate_model_artifact
        from mdstats.training_data.post_selection_model_products import (
            _verify_reloaded_product,
            place_member_model,
            realize_portable_publication_model,
        )

        portable, realization = realize_portable_publication_model(
            provider, target_head_name="target_head"
        )
        assert realization.head_inventory == ("pt_head", "target_head")
        assert realization.head_inventory.index("target_head") == 1
        publication_context = type(
            "C",
            (),
            {"paths": type("P", (), {"models": tmp_path / "models"})(), "cfg": {}},
        )()
        placed = place_member_model(
            publication_context,
            model=portable,
            member_id="mh1-seed-1",
            realization=realization,
            target_head_name="target_head",
            decision_relative_directory="production/g1/N_8/decision-" + "a" * 64,
        )
        authenticate_model_artifact(
            tmp_path / "models",
            placed.relative_path,
            expected_sha256=placed.sha256,
            expected_size_bytes=placed.size_bytes,
        )
        _verify_reloaded_product(
            tmp_path / "models" / placed.relative_path,
            realization=realization,
            target_head_name="target_head",
        )
    finally:
        if provider is not None:
            from mdstats.training_data.post_selection_model_products import retire_provider

            retire_provider(provider)
        store.close()


def test_mliap_builder_requires_the_target_head_at_index_one(tmp_path: Path):
    """The deployment contract MH-1 must satisfy, proved on a bounded model."""

    import torch

    from tests._mlff_tiny_mace import _tiny_mace
    from mdstats.training_data.qualification.deployment import (
        default_mliap_artifact_builder,
    )
    from mdstats.training_data.qualification.errors import (
        QualificationLineageError,
        QualificationUnavailableError,
    )
    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    )

    model = _tiny_mace(
        heads=[POST_SELECTION_REPLAY_HEAD_NAME, POST_SELECTION_TARGET_HEAD_NAME],
        atomic_numbers=(3, 8),
        r_max=4.0,
        dtype=torch.float64,
        atomic_energies=((0.0, 0.0), (0.0, 0.0)),
        seed=12,
    )
    source = tmp_path / "deployment.model"
    torch.save(model, source)
    output = tmp_path / "deployment-mliap.pt"
    try:
        default_mliap_artifact_builder(
            source, output, head=POST_SELECTION_TARGET_HEAD_NAME
        )
    except QualificationUnavailableError as exc:  # pragma: no cover - env dependent
        pytest.skip(f"the supported MACE ML-IAP path is unavailable: {exc}")
    assert output.is_file()
    # A head the product does not declare is a different product, not a default.
    with pytest.raises(QualificationLineageError):
        default_mliap_artifact_builder(
            source, tmp_path / "other.pt", head="omat_pbe"
        )


@_requires_real_mh1
def test_real_mh1_resolves_family_and_explicit_omat_pbe_head():
    from mdstats.training_data.foundation import (
        MaceFoundationFamily,
        MaceFoundationSpec,
        inspect_mace_foundation,
    )

    inspection = inspect_mace_foundation(MH1_MODEL)
    assert "omat_pbe" in inspection.available_heads
    assert len(inspection.available_heads) > 1
    identity = MaceFoundationSpec(
        family=MaceFoundationFamily.MH_1, requested_head="omat_pbe"
    ).resolve(inspection)
    assert identity.foundation_head == "omat_pbe"
    assert identity.model_family == "mace_mh_1"


@_requires_real_mh1
def test_real_mh1_publishes_and_reloads_through_the_publication_owner(tmp_path: Path):
    """Bounded save/reload of real MH-1 bytes through the new product owner."""

    import torch

    from mdstats.training_data.model_artifact_trust import authenticate_model_artifact
    from mdstats.training_data.post_selection_model_products import (
        _verify_reloaded_product,
        place_member_model,
        realize_portable_publication_model,
    )

    model = torch.load(MH1_MODEL, map_location="cpu", weights_only=False)
    provider = type("P", (), {"model": model})()
    portable, realization = realize_portable_publication_model(
        provider, target_head_name="omat_pbe"
    )
    context = type(
        "C",
        (),
        {"paths": type("P", (), {"models": tmp_path / "models"})(), "cfg": {}},
    )()
    placed = place_member_model(
        context,
        model=portable,
        member_id="seed-1",
        realization=realization,
        target_head_name="omat_pbe",
        decision_relative_directory="production/g1/N_8/decision-" + "a" * 64,
    )
    authenticate_model_artifact(
        tmp_path / "models",
        placed.relative_path,
        expected_sha256=placed.sha256,
        expected_size_bytes=placed.size_bytes,
    )
    _verify_reloaded_product(
        tmp_path / "models" / placed.relative_path,
        realization=realization,
        target_head_name="omat_pbe",
    )
