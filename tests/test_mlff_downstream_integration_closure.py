"""Downstream MLFF integration closure: one configured path, one locator owner.

Every claim here is about the *assembled* downstream chain rather than about a
path helper: the same configured ``[paths].foundation_model`` must mean one file
to ``doctor``, to P5 identity, to P5 execution and to the dependency-facing
launch, from any invocation directory; a byte-identical checkpoint reached
through a different valid locator must keep its method identity and stay
executable; a workspace left behind by a failed pre-repair attempt must recover
without manual deletion; and a frozen multi-size collection must produce a
verdict for every size before a campaign rejection is reduced.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
import tests.test_mlff_target_size_p5_r9_guards as r9

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.campaign_post_selection_runtime import (
    _reclaim_unaccepted_materialization,
    build_post_selection_contexts,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
)
from mdstats.training_data.post_selection_identity import (
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)


# ---------------------------------------------------------------------------
# O1 / 8.1 - one configured-path meaning across every downstream owner
# ---------------------------------------------------------------------------


def _path_forms(foundation: Path, config_dir: Path, home: Path) -> dict[str, str]:
    """The three supported spellings of one and the same checkpoint."""

    return {
        "absolute": str(foundation),
        "tilde": "~/" + str(foundation.relative_to(home)),
        "config_relative": os.path.relpath(foundation, config_dir),
    }


def test_configured_foundation_path_forms_agree_across_owners_from_any_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Absolute, ``~/...`` and ``../...`` name one file for every owner.

    The campaign is invoked from a directory that is deliberately *not* the
    configuration directory, which is what makes the difference between the
    canonical owner and a process-CWD interpretation observable at all.
    """

    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    cfg, paths, files = r9._legacy_fixture(home / "campaign-tree", mode="external_pseudolabel")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: r9._foundation_inspection(Path(path)),
    )
    foundation = files["foundation"]
    canonical = foundation.resolve()

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    identities = set()
    for name, spelling in _path_forms(foundation, paths.config_dir, home).items():
        variant = json.loads(json.dumps(cfg))
        variant["paths"]["foundation_model"] = spelling
        variant_paths = cli.CampaignPaths.from_config(paths.config, variant)

        # The operator-facing `doctor` owner ...
        assert cli._path_cfg(variant, variant_paths, "foundation_model") == canonical, name
        # ... the P5 method policy owner that execution consumes ...
        policies = resolve_post_selection_method_policies(
            variant, config_dir=variant_paths.config_dir
        )
        assert policies.foundation_model == str(canonical), name
        # ... and the authenticated scientific identity itself.
        assert policies.foundation_potential_identity is not None
        identities.add(
            resolve_post_selection_method_identity(
                variant, policies=policies
            ).content_digest
        )

    # The spelling is a locator, so it never reaches the method identity.
    assert len(identities) == 1


def test_relative_foundation_locator_without_a_campaign_directory_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative locator has no campaign meaning without its config directory.

    Silently resolving it against the process CWD is precisely the split-brain
    interpretation this repair removes, so the owner refuses instead.
    """

    cfg, paths, _files = r9._legacy_fixture(tmp_path, mode="external_pseudolabel")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda path: r9._foundation_inspection(Path(path)),
    )
    variant = json.loads(json.dumps(cfg))
    variant["paths"]["foundation_model"] = "relative/foundation.model"
    with pytest.raises(PostSelectionError, match="configuration directory"):
        resolve_post_selection_method_policies(variant)


# ---------------------------------------------------------------------------
# O2 / O3 / 8.2 - the authenticated current locator drives execution
# ---------------------------------------------------------------------------


def _foundation_backed_campaign(
    root: Path, *, foundation: Path, spelling: str
) -> Path:
    """A real selected campaign whose frozen method is foundation-backed."""

    r9._write_tiny_mace_foundation(foundation)
    config_text = fx.fixture_config_text().replace(
        'training_root = "{training_root}"',
        "\n".join(
            (
                'training_root = "{training_root}"',
                f'foundation_model = "{spelling}"',
                'foundation_head = "default"',
            )
        ),
    )
    config, _workspace = fx.build_selected_campaign(root, config_text=config_text)
    return config


@pytest.mark.slow
def test_config_relative_foundation_executes_and_survives_relocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``../`` foundation locator reaches P5 execution from a foreign CWD.

    Relocating the same bytes then keeps the method identity and stays
    executable through the real owner, while changing the bytes fails closed.
    """

    campaign_root = tmp_path / "campaign-root"
    campaign_root.mkdir()
    store_a = tmp_path / "foundation-store"
    store_a.mkdir()
    foundation = store_a / "foundation.model"
    config = _foundation_backed_campaign(
        campaign_root,
        foundation=foundation,
        spelling="../foundation-store/foundation.model",
    )

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert harness.requests
    for request in harness.requests:
        assert Path(request.foundation_model_path) == foundation.resolve()
        # The immutable execution representation never carries the locator.
        payload = json.loads(
            (
                request.materialization_directory
                / request.materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        assert "foundation_model" not in payload
        assert payload["foundation_head"] == "default"

    cfg, paths, campaign_store = fx.load_context(config)
    try:
        before = resolve_post_selection_method_identity(
            cfg, policies=resolve_post_selection_method_policies(
                cfg, config_dir=paths.config_dir
            )
        ).content_digest
    finally:
        campaign_store.close()

    # Byte-identical relocation: the method is the checkpoint's content and
    # head, not the directory it currently sits in.
    store_b = tmp_path / "relocated-store"
    store_b.mkdir()
    moved = store_b / "foundation.model"
    moved.write_bytes(foundation.read_bytes())
    foundation.unlink()
    fx.rewrite_config(
        config,
        'foundation_model = "../foundation-store/foundation.model"',
        'foundation_model = "../relocated-store/foundation.model"',
    )
    cfg, paths, campaign_store = fx.load_context(config)
    try:
        policies = resolve_post_selection_method_policies(
            cfg, config_dir=paths.config_dir
        )
        assert policies.foundation_model == str(moved.resolve())
        assert (
            resolve_post_selection_method_identity(
                cfg, policies=policies
            ).content_digest
            == before
        )
    finally:
        campaign_store.close()

    # ... and the relocated checkpoint still executes/re-closes through the real
    # P5 owner in the same workspace, with no manual intervention.
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0

    # Changed bytes are a different method and must not authenticate as this one.
    moved.write_bytes(moved.read_bytes() + b"\x00")
    cfg, paths, campaign_store = fx.load_context(config)
    try:
        mutated = resolve_post_selection_method_identity(
            cfg,
            policies=resolve_post_selection_method_policies(
                cfg, config_dir=paths.config_dir
            ),
        ).content_digest
    finally:
        campaign_store.close()
    assert mutated != before


# ---------------------------------------------------------------------------
# O4 / 8.3 - the same workspace a pre-repair failure left behind recovers
# ---------------------------------------------------------------------------


class _FailAfterMaterialization:
    """The observed pre-repair failure: it dies *after* materialization exists."""

    def __init__(self) -> None:
        self.roots: list[Path] = []

    def __call__(self, request):
        self.roots.append(Path(request.materialization_directory))
        raise AssertionError(
            "Foundation model file is missing: <pre-repair locator>"
        )


@pytest.mark.slow
def test_pre_repair_materialization_recovers_in_the_same_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed attempt's immutable scratch cannot permanently block a retry.

    The pre-repair representation is reproduced faithfully - the published
    configuration bytes carry the old ``foundation_model`` locator key that the
    current owner no longer writes - so the retry meets exactly the immutable
    create-or-verify conflict the observed failure would leave behind.
    """

    campaign_root = tmp_path / "campaign-root"
    campaign_root.mkdir()
    store_dir = tmp_path / "foundation-store"
    store_dir.mkdir()
    config = _foundation_backed_campaign(
        campaign_root,
        foundation=store_dir / "foundation.model",
        spelling="../foundation-store/foundation.model",
    )

    failing = _FailAfterMaterialization()
    with pytest.raises(AssertionError, match="Foundation model file is missing"):
        p4d._run(
            config,
            "cross-validate",
            _external_post_selection_trainer=failing,
            _external_inference_evaluator=fx.PostSelectionHarness().evaluate,
        )
    assert failing.roots
    material_directory = failing.roots[0]
    config_path = material_directory / "post_selection_mace_config.yaml"
    stale = json.loads(config_path.read_text(encoding="utf-8"))
    assert "foundation_model" not in stale
    stale["foundation_model"] = str(
        config.parent / "~" / "QE" / "mace-mpa-0-medium.model"
    )
    config_path.write_text(
        json.dumps(stale, indent=2, sort_keys=True), encoding="utf-8"
    )

    # No harness deletion of any kind: the corrected owner is handed exactly the
    # workspace the failure left.
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    recovered = json.loads(config_path.read_text(encoding="utf-8"))
    assert "foundation_model" not in recovered

    cfg, paths, campaign_store = fx.load_context(config)
    try:
        context = build_post_selection_contexts(cfg, paths, campaign_store)[0]
        assert resolve_current_cv_acceptance(context).accepted
    finally:
        campaign_store.close()


def test_reclamation_never_touches_accepted_or_restartable_run_state(
    tmp_path: Path,
) -> None:
    """Reclamation is only ever allowed to release pure unaccepted scratch."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        FOLD_ACCEPTANCE_FILENAME,
        RUN_EVIDENCE_FILENAME,
    )

    def _run_root(name: str) -> tuple[Path, Path]:
        root = tmp_path / name
        material = root / "materialization"
        material.mkdir(parents=True)
        (material / "post_selection_mace_config.yaml").write_text("{}", encoding="utf-8")
        return root, material

    # Terminal evidence of either kind keeps the whole tree.
    for terminal in (FOLD_ACCEPTANCE_FILENAME, RUN_EVIDENCE_FILENAME):
        root, material = _run_root(f"accepted-{terminal}")
        (root / terminal).write_text("{}", encoding="utf-8")
        _reclaim_unaccepted_materialization(root, material)
        assert material.is_dir()

    # Restart-authenticatable TRAIN2 progress keeps it too.
    root, material = _run_root("restartable")
    checkpoints = root / "checkpoints"
    checkpoints.mkdir()
    (checkpoints / "train2_runtime.pt").write_bytes(b"state")
    _reclaim_unaccepted_materialization(root, material)
    assert material.is_dir()

    # Only a run root with neither is reclaimed.
    root, material = _run_root("unaccepted")
    (root / "checkpoints").mkdir()
    _reclaim_unaccepted_materialization(root, material)
    assert not material.exists()


# ---------------------------------------------------------------------------
# O6 / 8.4 - every frozen size gets a verdict before the campaign is reduced
# ---------------------------------------------------------------------------


#: A per-component force error that is still admissible (the mandatory
#: checkpoint gate is 0.030 eV/A) but exceeds the strict CV acceptance maximum
#: below, so the size is rejected by the acceptance predicate itself.
_REJECTING_FORCE_OFFSET = 0.02
_STRICT_ACCEPTANCE_MAXIMUM = "acceptance_maximum = 0.005"


def _strict_two_size_campaign(tmp_path: Path) -> Path:
    """Two frozen sizes under a CV acceptance maximum a size can actually miss."""

    from unittest.mock import patch

    import tests.test_mlff_target_size_multi_size_integration as multi

    config_text = fx.fixture_config_text().replace(
        "acceptance_maximum = 0.5", _STRICT_ACCEPTANCE_MAXIMUM
    )
    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    assert multi._select(config, str(multi.FIRST_SIZE), "--horizon", "2") == 0
    assert multi._select(config, str(multi.SECOND_SIZE), "--horizon", "3") == 0
    return config


class _PerSizeHarness(fx.PostSelectionHarness):
    """One bounded numerical seam whose error depends on the frozen size.

    The seam stays strictly below the P5 owner: the real orchestrator still
    enumerates the collection, plans every fold, executes every run and reaches
    its own acceptance verdict.  Only MACE's arithmetic is substituted, and the
    substituted error is keyed by the *binding* the real owner handed the run,
    so a size is rejected on a genuine methodological result.
    """

    def __init__(self, offsets_by_binding_digest) -> None:
        super().__init__()
        self._offsets = offsets_by_binding_digest
        self._binding_by_run: dict[str, str] = {}

    def train(self, request):
        self._binding_by_run[request.run_plan.run_identity] = (
            request.run_plan.selected_binding_digest
        )
        return super().train(request)

    def _offset_for(self, provider) -> float:
        identity = getattr(provider, "checkpoint_identity", None)
        locator = "" if identity is None else str(
            getattr(identity, "checkpoint_locator", "")
        )
        for run_identity, binding in self._binding_by_run.items():
            if run_identity in locator:
                return float(self._offsets[binding])
        raise AssertionError(f"no executed run owns {locator!r}")


@pytest.mark.slow
@pytest.mark.parametrize("rejected_position", [0, 1])
def test_every_frozen_size_is_cross_validated_before_the_campaign_rejects(
    tmp_path: Path, rejected_position: int
) -> None:
    """A methodological rejection of one size never unruns its siblings.

    The frozen collection *is* the experiment, so an operator who requested two
    sizes must be told about both.  Under the superseded implementation the loop
    stopped at the first rejection and the later size was never evaluated.
    """

    import tests.test_mlff_target_size_multi_size_integration as multi

    config = _strict_two_size_campaign(tmp_path)
    cfg, paths, campaign_store = fx.load_context(config)
    try:
        contexts = build_post_selection_contexts(cfg, paths, campaign_store, admit=True)
        bindings = [context.selected.binding.content_digest for context in contexts]
        sizes = [context.selected.n_selected for context in contexts]
    finally:
        campaign_store.close()
    assert sizes == [multi.FIRST_SIZE, multi.SECOND_SIZE]

    # Both errors stay inside mandatory checkpoint admissibility, so the
    # rejected size produces a genuine methodological CV verdict rather than an
    # execution failure that would legitimately abort the command.
    offsets = {digest: 1.0e-4 for digest in bindings}
    offsets[bindings[rejected_position]] = _REJECTING_FORCE_OFFSET

    harness = _PerSizeHarness(offsets)
    with pytest.raises(PostSelectionError, match="cross-validation rejected"):
        fx.run_cross_validate(config, harness)

    cfg, paths, campaign_store = fx.load_context(config)
    try:
        contexts = build_post_selection_contexts(cfg, paths, campaign_store)
        verdicts = []
        for context in contexts:
            plan = resolve_current_cv_plan(context)
            acceptance = resolve_current_cv_acceptance(context)
            assert plan is not None, context.selected.n_selected
            assert acceptance is not None, context.selected.n_selected
            assert (
                acceptance.selected_binding_digest
                == context.selected.binding.content_digest
            )
            verdicts.append(acceptance.accepted)
        # Both frozen sizes hold their own valid verdict ...
        assert verdicts == [
            position != rejected_position for position in range(len(contexts))
        ]
    finally:
        campaign_store.close()

    # ... and the collection-wide production barrier still admits nothing.
    production = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError):
        fx.run_train_production(config, production)
    assert production.runs == []


# ---------------------------------------------------------------------------
# O7 / 8.5 - the explicit P7 reference root is an ordinary campaign path
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize("form", ["absolute", "tilde", "config_relative"])
def test_p7_explicit_reference_root_is_canonical_and_cwd_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, form: str
) -> None:
    """A configured ``[qualification.reference].root`` lands where it says.

    The bounded reference request is published by the real P7 runtime from a
    directory that is not the configuration directory, so a CWD-dependent or
    unexpanded interpretation would put the operator's request somewhere the
    operator cannot find it (``<config-dir>/~/...`` for the tilde form).
    """

    import tests._mlff_qualification_fixture as qfx

    home = tmp_path / "home"
    campaign_root = home / "campaign-root"
    campaign_root.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    intended = home / "qualification-reference"
    spelling = {
        "absolute": str(intended),
        "tilde": "~/qualification-reference",
        "config_relative": "../qualification-reference",
    }[form]
    config_text = qfx.fixture_config_text().replace(
        'protocol = "bounded-analytic-reference.v1"',
        'protocol = "bounded-analytic-reference.v1"\n'
        f'root = "{spelling}"',
    )
    harness = qfx.QualificationHarness()
    config, _workspace = qfx.build_qualified_campaign(
        campaign_root, config_text=config_text, harness=harness
    )

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    assert qfx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, _paths, store, session = qfx.load_session(config, harness)
    try:
        reference_root = Path(session.reference_root)
    finally:
        store.close()
    assert reference_root.is_relative_to(intended.resolve()), reference_root
    assert (reference_root / "reference-request.json").is_file()


# ---------------------------------------------------------------------------
# 8.7 - structural / absence evidence for the removals this repair depends on
# ---------------------------------------------------------------------------

#: The downstream owners this repair rewired.  The absence claims below are
#: scoped to exactly these files; nothing outside them is scanned or asserted.
_DOWNSTREAM_OWNERS = (
    "mdstats/training_data/post_selection_identity.py",
    "mdstats/training_data/campaign_post_selection_runtime.py",
    "mdstats/training_data/post_selection_execution.py",
    "mdstats/training_data/qualification/runtime.py",
    "mdstats/training_data/_campaign_cli_core.py",
)

_REPOSITORY_ROOT = Path(cli.__file__).resolve().parents[2]


def _path_derived_foundation_identity(source: str) -> list[str]:
    """Every ``digest({"foundation_model": ...})``-shaped identity substitute."""

    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(
            node.func, "id", None
        )
        if name != "digest" or not node.args:
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Dict) and any(
            isinstance(key, ast.Constant) and key.value == "foundation_model"
            for key in argument.keys
        ):
            found.append(ast.dump(node))
    return found


def _cwd_resolved_names(source: str) -> list[str]:
    """Names resolved as ``Path(name).resolve()`` without a campaign anchor."""

    found = []
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"resolve", "expanduser"}
        ):
            continue
        inner = node.func.value
        while isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
            inner = inner.func.value
        if (
            isinstance(inner, ast.Call)
            and getattr(inner.func, "id", None) == "Path"
            and inner.args
            and isinstance(inner.args[0], ast.Name)
        ):
            found.append(inner.args[0].id)
    return found


def test_structural_rules_distinguish_known_positive_and_negative_constructs():
    """The absence rules below only mean something if they can find the defect."""

    positive = (
        "from x import digest\n"
        "def f(foundation_model):\n"
        "    return digest({'foundation_model': foundation_model})\n"
    )
    negative = (
        "from x import digest\n"
        "def f(identity):\n"
        "    return digest({'foundation_content_digest': identity})\n"
    )
    assert _path_derived_foundation_identity(positive)
    assert not _path_derived_foundation_identity(negative)

    assert "f_model_raw" in _cwd_resolved_names(
        "from pathlib import Path\n"
        "def f(f_model_raw):\n"
        "    return Path(f_model_raw).resolve()\n"
    )
    assert "f_model_raw" not in _cwd_resolved_names(
        "from pathlib import Path\n"
        "def f(f_model_raw, base):\n"
        "    return resolve_configured_path(f_model_raw, base)\n"
    )


def test_no_downstream_owner_reintroduces_a_second_locator_authority():
    """The removals this repair depends on are absent from the real owners."""

    sources = {
        name: (_REPOSITORY_ROOT / name).read_text(encoding="utf-8")
        for name in _DOWNSTREAM_OWNERS
    }

    for name, source in sources.items():
        assert not _path_derived_foundation_identity(source), name
        # No configured foundation locator is re-derived from a raw config value.
        assert "f_model_raw" not in _cwd_resolved_names(source), name
        # The dead ``PostSelectionMethodPolicies.replay_context`` transport is
        # gone; the config-directory-aware ``_single_source_replay_context``
        # owner it was confused with is not this field and stays.
        assert "replay_context=" not in source, name
        assert ".replay_context" not in source, name

    # The dead transport field is gone from the policy object itself.
    from mdstats.training_data.post_selection_identity import (
        PostSelectionMethodPolicies,
    )

    assert "replay_context" not in PostSelectionMethodPolicies.__dataclass_fields__

    # One canonical configured-path owner, reused rather than reimplemented.
    from mdstats.training_data import _common

    assert cli._resolve_path is _common.resolve_configured_path
    assert "resolve_configured_path" in sources[
        "mdstats/training_data/qualification/runtime.py"
    ]

    # The immutable P5 execution representation carries no runtime locator.
    execution = sources["mdstats/training_data/post_selection_execution.py"]
    assert 'config["foundation_model"]' not in execution
    assert 'internal_payload.get("foundation_model")' not in execution
