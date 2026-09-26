"""P5 TRAIN2 construction foundation versus scientific source foundation.

For a multi-head source (MH-1) under a phase-separated TRAIN2 realization,
the scientific source identity stays the raw multi-head checkpoint and its
selected head, while TRAIN2 is constructed -- and reconstructed -- from the
doctor-qualified selected-head checkpoint frozen in the stored
``TrainingAccelerationRealizationRecord``.  Every fixture here uses distinct
files with distinct SHA-256 values for the two roles.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
import yaml

import mdstats
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.campaign_post_selection_runtime import PostSelectionContext
from mdstats.training_data.post_selection_identity import PostSelectionError
from tests.test_mlff_mh1_publication_integration import (
    build_mh1_shaped_campaign,
    write_mh1_shaped_foundation,
)

_PHASE_SEPARATED_E3NN = """

[acceleration]
backend = "e3nn"
training_backend = "e3nn"

[profile]
all_atomic_numbers = [3, 8]
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _lio_structures():
    from ase import Atoms

    return (
        Atoms("LiO", positions=[[0, 0, 0], [1.9, 0, 0]], cell=[7, 7, 7], pbc=True),
        Atoms(
            "Li2O",
            positions=[[0, 0, 0], [1.9, 0.2, 0], [0.9, 1.6, 0.3]],
            cell=[8, 8, 8],
            pbc=True,
        ),
    )


# ---------------------------------------------------------------------------
# The current-owner resolver: fail-closed ancestry of the TRAIN2 checkpoint
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def selected_head_lineage(tmp_path_factory):
    """Real EXTRACT1 extraction/qualification of a three-head MH-1-shaped source."""

    root = tmp_path_factory.mktemp("mh1-lineage")
    source = root / "mh1-shaped.model"
    write_mh1_shaped_foundation(source)
    potential = mdstats.MaceFoundationSpec(
        family="mace_mh_1", requested_head="omat_pbe"
    ).resolve_file(source)
    derived = root / "mh1-shaped-omat_pbe.model"
    extraction, _evidence = mdstats.extract_mace_selected_foundation_head(
        source, derived, source_identity=potential
    )
    qualification = mdstats.qualify_mace_selected_foundation_head(
        source,
        extraction,
        _lio_structures(),
        policy=mdstats.MaceSelectedHeadParityPolicy(default_dtype="float64"),
        device="cpu",
    )
    assert qualification.training_qualified
    return SimpleNamespace(
        source=source, derived=derived, potential=potential, qualification=qualification
    )


def _phase_separated_cfg() -> dict:
    return {
        "acceleration": {"backend": "e3nn", "training_backend": "e3nn"},
        "training": {"device": "cpu", "dtype": "float64"},
    }


def _realization(checkpoint: Path, *, qualification_digest: str | None, **overrides):
    values = dict(
        requested_backend="e3nn",
        training_kernel_mode="e3nn",
        device="cpu",
        dtype="float64",
        training_checkpoint_reference=str(checkpoint),
        training_checkpoint_sha256=_sha256(checkpoint),
        selected_head_qualification_digest=qualification_digest,
        mace_version=None,
        qualified=True,
    )
    values.update(overrides)
    return mdstats.TrainingAccelerationRealizationRecord(**values)


def _campaign_state(tmp_path: Path, *, realization=None, qualification=None):
    paths = SimpleNamespace(state_db=tmp_path / "state.sqlite")
    store = cli.CampaignStore(paths.state_db)
    try:
        if realization is not None:
            store.put_record("training_acceleration_realization", realization)
        if qualification is not None:
            store.put_record("selected_head_qualification", qualification)
    finally:
        store.close()
    return paths


def test_current_selected_head_realization_is_the_train2_foundation(
    tmp_path: Path, selected_head_lineage
) -> None:
    lineage = selected_head_lineage
    assert _sha256(lineage.derived) != lineage.potential.sha256
    realization = _realization(
        lineage.derived, qualification_digest=lineage.qualification.content_digest
    )
    paths = _campaign_state(
        tmp_path, realization=realization, qualification=lineage.qualification
    )
    resolved = cli._current_train2_foundation_realization(
        _phase_separated_cfg(), paths, lineage.potential
    )
    assert resolved == realization
    assert Path(resolved.training_checkpoint_reference) == lineage.derived
    # The raw source checkpoint stays the scientific identity, untouched.
    assert lineage.potential.sha256 == _sha256(lineage.source)
    assert lineage.potential.foundation_head == "omat_pbe"


def test_train2_foundation_resolution_fails_closed_without_current_ancestry(
    tmp_path: Path, selected_head_lineage
) -> None:
    lineage = selected_head_lineage
    cfg = _phase_separated_cfg()
    digest = lineage.qualification.content_digest
    valid = _realization(lineage.derived, qualification_digest=digest)

    def resolve(case: str, *, realization=valid, qualification=lineage.qualification,
                potential=lineage.potential):
        paths = _campaign_state(
            tmp_path / case, realization=realization, qualification=qualification
        )
        return cli._current_train2_foundation_realization(cfg, paths, potential)

    # Missing / unqualified / byte-changed stored realization.
    with pytest.raises(cli.CampaignCliError, match="missing"):
        resolve("missing", realization=None)
    with pytest.raises(cli.CampaignCliError, match="not qualified"):
        resolve(
            "unqualified",
            realization=replace(valid, qualified=False, failure_reason="fixture"),
        )
    tampered = tmp_path / "tampered.model"
    shutil.copyfile(lineage.derived, tampered)
    tampered_record = _realization(tampered, qualification_digest=digest)
    tampered.write_bytes(tampered.read_bytes() + b"\0")
    with pytest.raises(cli.CampaignCliError, match="bytes changed"):
        resolve("tampered", realization=tampered_record)

    # Wrong or absent selected-head qualification binding.
    ancestry = "does not descend from the current selected-head qualification"
    for case, kwargs in {
        "no-digest": {"realization": replace(valid, selected_head_qualification_digest=None)},
        "wrong-digest": {"realization": replace(valid, selected_head_qualification_digest="a" * 64)},
        "no-qualification": {"qualification": None},
    }.items():
        with pytest.raises(cli.CampaignCliError, match=ancestry):
            resolve(case, **kwargs)

    # A qualification that does not bind the current source potential digest,
    # raw source SHA, or source head.
    for case, potential in {
        "source-digest": replace(lineage.potential, model_atomic_numbers=(3, 8, 11)),
        "source-sha": replace(lineage.potential, sha256="0" * 64),
        "source-head": replace(lineage.potential, foundation_head="mp_pbe"),
    }.items():
        with pytest.raises(cli.CampaignCliError, match=ancestry):
            resolve(case, potential=potential)

    # A byte-valid, correctly bound record whose checkpoint is not the one the
    # qualification derived.
    other = tmp_path / "other.model"
    other.write_bytes(lineage.derived.read_bytes() + b"other")
    with pytest.raises(cli.CampaignCliError, match=ancestry):
        resolve("derived-sha", realization=_realization(other, qualification_digest=digest))

    # Never an implicit fallback to the raw source checkpoint.
    with pytest.raises(cli.CampaignCliError, match=ancestry):
        resolve("raw-source", realization=_realization(lineage.source, qualification_digest=digest))


def test_train2_foundation_resolution_preserves_collapsed_and_scratch_modes(
    tmp_path: Path, selected_head_lineage
) -> None:
    lineage = selected_head_lineage
    single_head = replace(lineage.potential, available_heads=("omat_pbe",))
    source_record = _realization(lineage.source, qualification_digest=None)
    cfg = _phase_separated_cfg()

    # A single-head source's TRAIN2 realization is that source checkpoint.
    paths = _campaign_state(tmp_path / "single", realization=source_record)
    assert cli._current_train2_foundation_realization(cfg, paths, single_head) == source_record
    for case, record in {
        "foreign": _realization(lineage.derived, qualification_digest=None),
        "spurious-digest": replace(source_record, selected_head_qualification_digest="b" * 64),
    }.items():
        paths = _campaign_state(tmp_path / case, realization=record)
        with pytest.raises(cli.CampaignCliError, match="must be that source checkpoint"):
            cli._current_train2_foundation_realization(cfg, paths, single_head)

    # Non-phase-separated and foundation-free methods carry no TRAIN2 record.
    empty = _campaign_state(tmp_path / "empty")
    assert cli._current_train2_foundation_realization(
        {"acceleration": {"backend": "e3nn"}}, empty, lineage.potential
    ) is None
    assert cli._current_train2_foundation_realization(cfg, empty, None) is None

    train2_path = PostSelectionContext.train2_foundation_path.fget

    def context(foundation_model, realization, acceleration):
        return SimpleNamespace(
            cfg={"acceleration": acceleration},
            method_policies=SimpleNamespace(foundation_model=foundation_model),
            train2_foundation_realization=realization,
        )

    assert train2_path(context(None, None, {"backend": "e3nn"})) is None
    assert train2_path(
        context(str(lineage.source), None, {"backend": "e3nn"})
    ) == lineage.source
    with pytest.raises(PostSelectionError, match="never a TRAIN2 construction fallback"):
        train2_path(context(str(lineage.source), None, _phase_separated_cfg()["acceleration"]))


# ---------------------------------------------------------------------------
# Assembled P5: launch, reconstruction, source-only consumers, restart
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_phase_separated_mh1_p5_trains_and_reconstructs_from_selected_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real P5 TRAIN2 over an MH-1-shaped source under phase-separated TRAIN2.

    The selected-head checkpoint comes from the real doctor owners.  A
    pre-repair-shaped failure first leaves execution-local launch payload
    naming the raw source; the same workspace then retries through the real
    owner, trains from the selected-head checkpoint, reconstructs every TRAIN2
    provider from it, and keeps source-only consumers on the raw source.
    """

    import tests.test_mlff_mace_execution_semantics_assembled as assembled
    from tests import test_mlff_target_size_p4d_runtime_cutover as p4d
    import mdstats.training_data.campaign_post_selection_runtime as runtime
    import mdstats.training_data.post_selection_execution as execution

    fixture_campaign = p4d._fixture_campaign

    def campaign_with_doctor_train2_realization(*args, **kwargs):
        # The doctor owners, exactly: EXTRACT1 qualification of the selected
        # head, then TRAIN2 realization of that derived checkpoint.
        config, workspace = fixture_campaign(*args, **kwargs)
        cfg, paths = cli._load_config(config)
        store = cli.CampaignStore(paths.state_db)
        try:
            potential = cli._resolved_foundation_potential_identity(cfg, paths)
            corpus = cli._doctor_acceleration_corpus(cli._doctor_sample_atoms(cfg, paths))
            qualification = cli._qualify_selected_head_training_foundation(
                cfg, paths, store, potential, corpus
            )
            assert qualification is not None
            realization, _parity = mdstats.qualify_training_acceleration_realization(
                backend="e3nn",
                training_model_path=qualification.extraction.derived_checkpoint_reference,
                training_head=potential.foundation_head,
                structures=corpus,
                device=str(cli._cfg(cfg, "training", "device", "cuda")),
                dtype=str(cli._cfg(cfg, "training", "dtype", "float32")),
                selected_head_qualification_digest=qualification.content_digest,
            )
            assert realization.qualified, realization.failure_reason
            store.put_record("training_acceleration_realization", realization)
        finally:
            store.close()
        return config, workspace

    monkeypatch.setattr(p4d, "_fixture_campaign", campaign_with_doctor_train2_realization)
    config, foundation = build_mh1_shaped_campaign(
        tmp_path, monkeypatch, extra_config=_PHASE_SEPARATED_E3NN
    )

    calls: dict[str, list] = {"provider": [], "residual": [], "baseline": []}

    def spy(name, owner, key):
        def wrapped(*args, **kwargs):
            calls[name].append(kwargs.get(key))
            return owner(*args, **kwargs)
        return wrapped

    monkeypatch.setattr(
        runtime, "authenticate_post_selection_provider",
        spy("provider", runtime.authenticate_post_selection_provider, "foundation_model_path"),
    )
    monkeypatch.setattr(
        runtime, "resolve_foundation_residual_inputs",
        spy("residual", runtime.resolve_foundation_residual_inputs, "foundation_model_path"),
    )
    monkeypatch.setattr(
        execution, "build_post_selection_foundation_baseline_provider",
        spy("baseline", execution.build_post_selection_foundation_baseline_provider, "foundation_path"),
    )

    cfg, paths, store = assembled.load_context(config)
    try:
        context = assembled.build_post_selection_context(
            cfg, paths, store, inference_evaluator=assembled.PostSelectionHarness().evaluate
        )
        source = context.method_policies.foundation_potential_identity
        derived = context.train2_foundation_path
        # 1. The method/source identity is the raw multi-head source + head.
        assert context.method_policies.foundation_model == str(foundation.resolve())
        assert source.sha256 == _sha256(foundation)
        assert len(source.available_heads) == 3
        assert context.method_policies.foundation_head == "omat_pbe"
        # The TRAIN2 construction checkpoint is the distinct doctor artifact.
        assert derived == Path(context.train2_foundation_realization.training_checkpoint_reference)
        assert derived.parent == paths.internal / "foundation-selected-head"
        assert _sha256(derived) != source.sha256
        assert mdstats.inspect_mace_foundation(derived).available_heads == ("omat_pbe",)

        resolution = assembled._resolve_post_selection_replay_resolution(context)
        cv_plan = assembled.build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            projection=assembled.build_selected_relation_projection(context.selected),
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

        def execute(trainer):
            return assembled.execute_post_selection_run(
                replace(context, trainer=trainer),
                run_plan=run_plan,
                budget_policy=assembled.cv_training_budget_policy(
                    context.method, context.cv_policy
                ),
                training_frame_uids=fold.training_frame_uids,
                monitor_frame_uids=tuple(context.common_target_monitor()[0].selected_identities),
                outer_evaluation_frame_uids=None,
            )

        # A pre-repair-shaped zero-update failure: execution-local launch
        # payload names the raw source, then MACE dies before any update.
        def pre_repair_failure(request):
            payload = json.loads(
                (request.materialization_directory
                 / request.materialization.mace_config_relative_path).read_text(encoding="utf-8")
            )
            stale = execution.post_selection_mace_run_configuration(
                payload, foundation_model_path=foundation
            )
            (request.materialization_directory / "mace_run_config.yaml").write_text(
                yaml.safe_dump(stale, sort_keys=False), encoding="utf-8"
            )
            raise AssertionError("stock remove_pt_head failed on the raw source")

        with pytest.raises(AssertionError, match="remove_pt_head"):
            execute(pre_repair_failure)
        run_root = context.run_root(run_plan.run_identity)
        materialization_bytes = (run_root / "materialization" / "materialization.json").read_bytes()

        requests = []

        def real_trainer(request):
            requests.append(request)
            return context.trainer(request)

        result = execute(real_trainer)
        assert result.representative is not None
        # The retry reused the immutable materialization; only the
        # execution-local launch payload was recreated.
        assert (run_root / "materialization" / "materialization.json").read_bytes() == materialization_bytes
        # 2-3. The real MACE launch names the selected-head checkpoint and
        # keeps the accepted source head.
        assert requests
        for request in requests:
            assert request.foundation_identity == source
            assert Path(request.foundation_model_path) == derived
            assert request.training_realization == context.train2_foundation_realization
        executable = yaml.safe_load(
            (run_root / "materialization" / "mace_run_config.yaml").read_text(encoding="utf-8")
        )
        assert executable["foundation_model"] == str(derived.resolve())
        assert executable["foundation_head"] == "omat_pbe"
        summary = assembled.load_train2_runtime_summary(run_root / "checkpoints")
        assert summary.completed_updates > 0
        # 11. Every TRAIN2 reconstruction used the same checkpoint.
        assert calls["provider"] and set(map(Path, calls["provider"])) == {derived}
        # 12. Source-only consumers stayed on the scientific source.
        assert calls["residual"] and set(map(str, calls["residual"])) == {str(foundation.resolve())}
        assert calls["baseline"] and set(map(str, calls["baseline"])) == {str(foundation.resolve())}

        # 4-6, 8. The real trainer authenticates the two identities
        # independently and rejects each substitution before any launch.
        request = requests[0]
        realization = request.training_realization
        tampered = tmp_path / "tampered-selected-head.model"
        shutil.copyfile(derived, tampered)
        tampered_realization = replace(
            realization,
            training_checkpoint_reference=str(tampered),
            training_checkpoint_sha256=_sha256(tampered),
        )
        tampered_request = replace(
            request,
            foundation_model_path=tampered,
            training_realization=tampered_realization,
            optimizer_policy=replace(
                request.optimizer_policy,
                acceleration_realization_digest=tampered_realization.content_digest,
            ),
        )
        tampered.write_bytes(tampered.read_bytes() + b"\0")
        unqualified = replace(realization, qualified=False, failure_reason="fixture")
        for message, bad in {
            "bytes do not match the stored TRAIN2 training realization": tampered_request,
            "scientific source foundation identity": replace(request, training_realization=None),
            "do not match the stored TRAIN2": replace(request, foundation_model_path=foundation),
            "not the realization bound by the optimizer policy": replace(
                request,
                optimizer_policy=replace(
                    request.optimizer_policy, acceleration_realization_digest="6" * 64
                ),
            ),
            "unqualified": replace(request, training_realization=unqualified),
        }.items():
            with pytest.raises(execution.PostSelectionExecutionError, match=message):
                context.trainer(bad)
    finally:
        store.close()


def test_every_p5_train2_reconstruction_uses_the_invocation_binding() -> None:
    """Structural closure of O4/O5 over the production P5 modules.

    Every P5 call that reconstructs TRAIN2 state receives the invocation's
    TRAIN2 construction checkpoint, every launch carries the same realization,
    and no P5/TRAIN2/EVAL2 module re-runs EXTRACT1.
    """

    import ast

    import mdstats.training_data as package

    root = Path(package.__file__).resolve().parent
    reconstruction_sites = 0
    for name in (
        "campaign_post_selection_runtime.py",
        "post_selection_model_products.py",
        "post_selection_execution.py",
    ):
        source = (root / name).read_text(encoding="utf-8")
        assert "extract_mace_selected_foundation_head" not in source, name
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call):
                continue
            callee = getattr(node.func, "id", getattr(node.func, "attr", None))
            keywords = {kw.arg: ast.unparse(kw.value) for kw in node.keywords}
            if callee == "authenticate_post_selection_provider":
                reconstruction_sites += 1
                assert keywords["foundation_model_path"] == "context.train2_foundation_path", name
            if callee == "PostSelectionRungRequest":
                assert keywords["foundation_model_path"] == "context.train2_foundation_path", name
                assert keywords["training_realization"] == "context.train2_foundation_realization", name
    assert reconstruction_sites == 3
