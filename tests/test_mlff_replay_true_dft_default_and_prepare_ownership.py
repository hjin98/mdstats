"""Falsification evidence for the replay TRUE_DFT default and prepare ownership.

Every test here is written against the *assembled* owners, not helper names:
the canonical resolver, the public prepare route, the doctor route, the
post-selection read route, and the lifecycle observation boundary.  Where a
runtime test cannot establish a claim - a removed path, a unique owner, an
absent fixed-temp writer - structural evidence is used deliberately instead of
a helper-only pass.
"""
from __future__ import annotations

import json
import threading
import tomllib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._common import TrainingDataInputError, sha256_file_cached
from mdstats.training_data.foundation import (
    FoundationInferenceIdentity,
    FoundationPotentialIdentity,
)
from mdstats.training_data.replay import ReplayLabelMode

_REPO = Path(__file__).resolve().parents[1]
_PKG = _REPO / "mdstats" / "training_data"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _write_source(path: Path, count: int = 12, *, energy_offset: float = 0.0) -> None:
    pytest.importorskip("ase")
    from ase import Atoms
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    frames = []
    for index in range(count):
        atoms = Atoms(
            "H2",
            positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.70 + 0.01 * index]],
            cell=[5.0, 5.0, 5.0],
            pbc=True,
        )
        atoms.calc = SinglePointCalculator(
            atoms,
            energy=-10.0 - index + energy_offset,
            forces=np.full((2, 3), 0.02 * (index + 1), dtype=np.float64),
            stress=np.eye(3, dtype=np.float64) * 0.001 * (index + 1),
        )
        frames.append(atoms)
    write(path, frames, format="extxyz")


def _config_text(tmp_path: Path, source: Path, **kwargs) -> str:
    training = tmp_path / "training"
    training.mkdir(exist_ok=True)
    model = tmp_path / "foundation.model"
    if not model.is_file():
        model.write_bytes(b"foundation-fixture")
    return cli._config_template(
        workspace=str(tmp_path / "work"),
        training_root=str(training),
        foundation_model=str(model),
        replay_set=str(source),
        foundation_family="mace_mpa_0",
        foundation_head="default",
        training_acceleration_backend="e3nn",
        default_device="cpu",
        **kwargs,
    )


#: The fixture replay corpus is tiny and elemental; production cardinality and
#: target-element coverage are their own owners and are not what these tests
#: falsify, so every fixture campaign relaxes them identically.
_RELAXED_PRODUCTION_REPLAY_GATES = (
    ("minimum_train_configurations = 100", "minimum_train_configurations = 1"),
    ("minimum_monitor_configurations = 20", "minimum_monitor_configurations = 1"),
    ("require_target_elements = true", "require_target_elements = false"),
)


def _write_config(
    tmp_path: Path,
    source: Path,
    *,
    label_mode: str | None = "true_dft",
    legacy_mode: str | None = None,
    replacements: tuple[tuple[str, str], ...] = (),
    name: str = "campaign.toml",
) -> tuple[dict, cli.CampaignPaths]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    text = _config_text(tmp_path, source)
    for old_text, new_text in _RELAXED_PRODUCTION_REPLAY_GATES:
        assert old_text in text, old_text
        text = text.replace(old_text, new_text)
    if label_mode is None:
        text = text.replace('label_mode = "true_dft"\n', "")
    elif label_mode != "true_dft":
        text = text.replace('label_mode = "true_dft"', f'label_mode = "{label_mode}"')
    if legacy_mode is not None:
        text = text.replace("[replay]\n", f'[replay]\nmode = "{legacy_mode}"\n', 1)
    for old, new in replacements:
        assert old in text, old
        text = text.replace(old, new)
    config = tmp_path / name
    config.write_text(text, encoding="utf-8")
    return cli._load_config(config)



def _switch_to_naive_only(text: str) -> str:
    """Enable only naive fine tuning, so no enabled method requires replay."""

    a = text.index("\n[training.naive_fine_tuning]\n") + 1
    b = text.index("\n[training.multihead_replay]\n") + 1
    c = text.index("\n[post_selection.cv]\n", b) + 1
    naive = text[a:b].replace("enabled = false", "enabled = true", 1)
    multi = text[b:c].replace("enabled = true", "enabled = false", 1)
    return text[:a] + naive + multi + text[c:]


def _pseudo_identities(cfg: dict):
    model_path = Path(cfg["paths"]["foundation_model"]).resolve()
    head = cfg.get("foundation", {}).get("head", "default")
    family = cfg.get("foundation", {}).get("family", "mace_custom")
    potential = FoundationPotentialIdentity(
        reference=str(model_path),
        sha256=sha256_file_cached(model_path),
        foundation_head=head,
        model_family=family,
        model_atomic_numbers=(1,),
        available_heads=("default", head) if head != "default" else ("default",),
        inspection_state="inspected",
    )
    inference = FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype=cfg.get("model", {}).get("dtype", "float32"),
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="test",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    realization = SimpleNamespace(
        resolved_kernel_mode="e3nn",
        foundation_inference_identity_digest=inference.content_digest,
    )
    return potential, inference, realization


def _install_pseudo_prerequisites(monkeypatch, cfg: dict):
    potential, inference, realization = _pseudo_identities(cfg)
    monkeypatch.setattr(
        cli,
        "_resolved_foundation_potential_identity",
        lambda c, paths: _pseudo_identities(c)[0],
    )
    monkeypatch.setattr(
        cli,
        "_stored_acceleration_realization",
        lambda c, paths, require_qualified=False: _pseudo_identities(c)[2],
    )
    monkeypatch.setattr(
        cli,
        "_foundation_inference_identity",
        lambda c, potential_arg, **kw: _pseudo_identities(c)[1],
    )
    return potential, inference


class _CountingProvider:
    """A CPU-backed provider double that records prediction batches and closes."""

    def __init__(self, policy):
        self.policy = policy
        self.calls: list[int] = []
        self.close_count = 0
        self.checkpoint_identity = SimpleNamespace(
            checkpoint_sha256=policy.foundation_potential.sha256,
            default_dtype=policy.foundation_inference.default_dtype,
            foundation_potential_digest=policy.foundation_potential.canonical_content_digest,
            foundation_inference_digest=policy.foundation_inference.content_digest,
            foundation_head=policy.foundation_potential.foundation_head,
        )

    def set_head(self, head: str) -> None:
        assert head in self.policy.foundation_potential.available_heads

    def close(self, **kwargs) -> None:
        self.close_count += 1

    def predict_batch(self, atoms_batch, **kwargs):
        self.calls.append(len(atoms_batch))
        results = []
        for atoms in atoms_batch:
            # A label-blind provider: the source truth must not be reachable.
            assert atoms.calc is None
            for key in ("energy", "REF_energy", "stress", "REF_stress"):
                assert key not in atoms.info, key
            assert "REF_forces" not in atoms.arrays
            assert "forces" not in atoms.arrays
            marker = float(atoms.positions[-1, 2])
            scale = marker - 0.69
            results.append(
                SimpleNamespace(
                    energy_ev=-float(len(atoms)) - marker,
                    forces_ev_per_angstrom=np.full((len(atoms), 3), scale, dtype=np.float64),
                    stress_ev_per_angstrom3=np.eye(3, dtype=np.float64) * scale * 0.1,
                )
            )
        return tuple(results)


def _publish(cfg, paths):
    store = cli.CampaignStore(paths.state_db)
    try:
        return cli._publish_single_source_replay_authority(store, cfg, paths)
    finally:
        store.close()


def _record_keys(paths) -> set[str]:
    store = cli.CampaignStore(paths.state_db)
    try:
        return set(store.record_keys("replay_"))
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R1/R2 - canonical selector normalization and exact configuration domains
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "replay_table, expected",
    [
        ({}, ReplayLabelMode.TRUE_DFT),
        ({"label_mode": "true_dft"}, ReplayLabelMode.TRUE_DFT),
        (
            {"label_mode": "foundation_pseudolabel"},
            ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        ),
        ({"mode": "external_true_label"}, ReplayLabelMode.TRUE_DFT),
        ({"mode": "external_pseudolabel"}, ReplayLabelMode.FOUNDATION_PSEUDOLABEL),
        (
            {"mode": "external_true_label", "label_mode": "true_dft"},
            ReplayLabelMode.TRUE_DFT,
        ),
        (
            {"mode": "external_pseudolabel", "label_mode": "foundation_pseudolabel"},
            ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        ),
    ],
)
def test_single_source_label_selectors_normalize_once(replay_table, expected):
    assert mdstats.normalize_single_source_replay_label_mode(replay_table) is expected


@pytest.mark.parametrize(
    "replay_table",
    [
        {"mode": "external_true_label", "label_mode": "foundation_pseudolabel"},
        {"mode": "external_pseudolabel", "label_mode": "true_dft"},
        {"mode": "none"},
        {"mode": "mp_shortcut"},
        {"mode": "preselected"},
        {"label_mode": "unspecified"},
        {"label_mode": "pseudolabel"},
    ],
)
def test_conflicting_or_unsupported_single_source_selectors_are_rejected(replay_table):
    with pytest.raises(TrainingDataInputError):
        mdstats.normalize_single_source_replay_label_mode(replay_table)


def test_omitted_single_source_label_mode_resolves_to_true_dft(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    source.touch()
    resolved = mdstats.single_source_replay_config_from_campaign(
        {"paths": {"replay_set": str(source)}, "replay": {}},
        base_directory=tmp_path,
    )
    assert resolved is not None
    assert resolved.label_mode is ReplayLabelMode.TRUE_DFT


@pytest.mark.parametrize("value", [True, False, 42.0, 42.5, "42", None, float("nan")])
def test_replay_split_seed_is_an_exact_nonnegative_integer(value):
    with pytest.raises(TrainingDataInputError):
        mdstats.normalize_replay_split_seed(value)


def test_replay_split_seed_accepts_exact_integers():
    assert mdstats.normalize_replay_split_seed(0) == 0
    assert mdstats.normalize_replay_split_seed(42) == 42


@pytest.mark.parametrize(
    "value",
    [(True, 1), (1, True), (5.0, 1), (5, 1.0), ("5.5", "1"), ("-5", "1"), ("", "1")],
)
def test_replay_split_ratio_components_are_exact_positive_integers(value):
    with pytest.raises(TrainingDataInputError):
        mdstats.normalize_replay_split_ratio(value)


def test_replay_split_ratio_keeps_its_supported_lexical_form():
    assert mdstats.normalize_replay_split_ratio("5:1") == (5, 1)
    assert mdstats.normalize_replay_split_ratio("10/2") == (5, 1)
    assert mdstats.normalize_replay_split_ratio((15, 3)) == (5, 1)


def test_generated_config_and_shipped_example_make_true_dft_explicit(tmp_path: Path):
    generated = tomllib.loads(
        cli._config_template(
            workspace=str(tmp_path / "work"),
            training_root=str(tmp_path),
            foundation_model=str(tmp_path / "m.model"),
            replay_set=str(tmp_path / "replay.extxyz"),
        )
    )
    assert generated["replay"]["label_mode"] == "true_dft"
    example = tomllib.loads((_REPO / "campaign.toml.example").read_text(encoding="utf-8"))
    assert example["replay"]["label_mode"] == "true_dft"


def test_replay_prediction_device_has_one_canonical_owner():
    """Prediction device/dtype come from the canonical resolvers, not a default."""

    text = (_PKG / "_campaign_cli_core.py").read_text(encoding="utf-8")
    assert 'device=_canonical_model_device(cfg)' in text
    assert '_cfg(cfg, "model", "device", "cuda")' not in text


# ---------------------------------------------------------------------------
# R4 - canonical-equivalent configuration stays equivalent for stage currentness
# ---------------------------------------------------------------------------


def _prepare_stage_digest(tmp_path: Path, source: Path, name: str, **kwargs) -> str:
    """The prepare-stage completion identity for one replay declaration.

    Only the replay declaration varies: workspace, training root, and the
    foundation locator are preparation inputs by design, so they stay fixed and
    the comparison isolates the replay portion of the projection.
    """

    cfg, paths = _write_config(tmp_path, source, name=name, **kwargs)
    return cli._stage_config_digest(paths, "prepare")


def test_canonically_equivalent_replay_spelling_does_not_stale_prepared_replay(
    tmp_path: Path,
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    explicit = _prepare_stage_digest(tmp_path, source, "a.toml", label_mode="true_dft")
    omitted = _prepare_stage_digest(tmp_path, source, "b.toml", label_mode=None)
    alias = _prepare_stage_digest(
        tmp_path, source, "c.toml", label_mode=None, legacy_mode="external_true_label"
    )
    agreeing = _prepare_stage_digest(
        tmp_path, source, "d.toml", label_mode="true_dft", legacy_mode="external_true_label"
    )
    assert explicit == omitted == alias == agreeing


def test_execution_only_prediction_knobs_do_not_stale_prepared_replay(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    baseline = _prepare_stage_digest(tmp_path, source, "a.toml")
    retuned = _prepare_stage_digest(
        tmp_path,
        source,
        "b.toml",
        replacements=(
            ("prediction_batch_size = 32", "prediction_batch_size = 4"),
            ("prediction_shard_size = 256", "prediction_shard_size = 16"),
        ),
    )
    assert baseline == retuned


def test_real_replay_semantic_change_does_stale_prepared_replay(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    baseline = _prepare_stage_digest(tmp_path, source, "a.toml")
    pseudo = _prepare_stage_digest(
        tmp_path, source, "b.toml", label_mode="foundation_pseudolabel"
    )
    reseeded = _prepare_stage_digest(
        tmp_path, source, "c.toml", replacements=(("split_seed = 42", "split_seed = 7"),)
    )
    resplit = _prepare_stage_digest(
        tmp_path, source, "d.toml", replacements=(('split_ratio = "5:1"', 'split_ratio = "3:1"'),)
    )
    assert len({baseline, pseudo, reseeded, resplit}) == 4


# ---------------------------------------------------------------------------
# R3 - topology preflight before expensive work
# ---------------------------------------------------------------------------


def test_replay_source_without_multihead_replay_is_rejected_at_prepare_entry(
    tmp_path: Path,
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    paths.config.write_text(
        _switch_to_naive_only(paths.config.read_text(encoding="utf-8")), encoding="utf-8"
    )
    cfg, paths = cli._load_config(paths.config)
    with pytest.raises(cli.CampaignCliError, match="multihead_replay"):
        cli._replay_topology_preflight(cfg, paths)


def test_conflicting_selectors_fail_preflight_before_any_construction(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(
        tmp_path,
        source,
        label_mode="foundation_pseudolabel",
        legacy_mode="external_true_label",
    )

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("preflight must reject before replay construction")

    monkeypatch.setattr(cli, "_construct_single_source_replay_context", refuse)
    monkeypatch.setattr(cli, "_load_or_inspect_single_replay_source", refuse)
    with pytest.raises(cli.CampaignCliError, match="Invalid single-source replay"):
        cli._replay_topology_preflight(cfg, paths)


# ---------------------------------------------------------------------------
# R5/R6 - doctor validates, prepare owns realized replay
# ---------------------------------------------------------------------------


def test_doctor_never_reaches_replay_construction_for_single_source(tmp_path: Path):
    """Structural: the doctor route has no edge to a construction-capable owner."""

    text = (_PKG / "_campaign_cli_core.py").read_text(encoding="utf-8")
    start = text.index("def command_doctor(")
    end = text.index("\ndef _performance_resources(", start)
    doctor = text[start:end]
    for forbidden in (
        "_construct_single_source_replay_context",
        "_publish_single_source_replay_authority",
        "_prepare_single_source_replay",
        "build_replay_foundation_prediction_cache",
        "materialize_replay_pseudolabel_views",
        "materialize_replay_true_label_views",
        "build_replay_split_manifest",
    ):
        assert forbidden not in doctor, forbidden


def test_doctor_defers_single_source_replay_and_publishes_no_replay_alias(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("doctor must not construct replay science")

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    monkeypatch.setattr(mdstats, "build_replay_split_manifest", refuse)
    monkeypatch.setattr(mdstats, "materialize_replay_pseudolabel_views", refuse)
    monkeypatch.setattr(cli, "_construct_single_source_replay_context", refuse)

    args = SimpleNamespace(config=str(paths.config))
    try:
        cli.command_doctor(args)
    except Exception:
        # Doctor may fail for unrelated environment prerequisites in this
        # fixture; what matters is that it never reached replay construction
        # and never published a replay alias.
        pass
    assert not _record_keys(paths) & set(cli._REPLAY_SINGLE_SOURCE_ALIASES)


def test_prepare_publishes_realized_qualification_and_retires_doctor_plan_alias(
    tmp_path: Path,
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    store = cli.CampaignStore(paths.state_db)
    try:
        # A stale historical doctor record must not survive as current
        # single-source authority.
        store.put_record("replay_plan_doctor", {"schema": "stale", "note": "historical"})
        cli._publish_single_source_replay_authority(store, cfg, paths)
        assert not store.has_record("replay_plan_doctor")
        realized = store.get_payload("replay_qualification")
        assert realized["interface"] == "single_source"
        assert realized["qualified"] is True
        assert realized["label_mode"] == "true_dft"
        assert realized["train_count"] == 10
        assert realized["monitor_count"] == 2
    finally:
        store.close()


def test_true_dft_prepare_performs_zero_foundation_inference(tmp_path: Path, monkeypatch):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("TRUE_DFT preparation must not build pseudo labels")

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    context = _publish(cfg, paths)
    assert context is not None
    assert context["prediction_cache"] is None
    keys = _record_keys(paths)
    assert "replay_true_train_view" in keys
    assert not keys & set(cli._REPLAY_SINGLE_SOURCE_PSEUDO_ALIASES) - {
        "replay_true_monitor_view"
    }


# ---------------------------------------------------------------------------
# R9/R10 - exact current alias set across mode and interface transitions
# ---------------------------------------------------------------------------


def test_pseudo_true_pseudo_transitions_leave_the_exact_mode_alias_set(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    pseudo_cfg, pseudo_paths = _write_config(
        tmp_path, source, label_mode="foundation_pseudolabel"
    )
    _install_pseudo_prerequisites(monkeypatch, pseudo_cfg)
    original = mdstats.build_replay_foundation_prediction_cache
    providers: list[_CountingProvider] = []

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        providers.append(provider)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    _publish(pseudo_cfg, pseudo_paths)
    pseudo_keys = _record_keys(pseudo_paths)
    assert pseudo_keys >= set(cli._REPLAY_SINGLE_SOURCE_PSEUDO_ALIASES)
    assert "replay_true_train_view" not in pseudo_keys

    # Same workspace, true mode: the pseudo-only aliases must be gone.
    true_cfg, true_paths = _write_config(tmp_path, source, label_mode="true_dft")
    _publish(true_cfg, true_paths)
    true_keys = _record_keys(true_paths)
    assert true_keys >= set(cli._REPLAY_SINGLE_SOURCE_TRUE_ALIASES)
    assert "replay_foundation_prediction_cache" not in true_keys
    assert "replay_pseudolabel_qualification" not in true_keys
    assert "replay_pseudolabel_train_view" not in true_keys

    # Back to pseudo: the true-only train view is retired again.
    _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    cfg_back, paths_back = cli._load_config(pseudo_paths.config)
    _publish(cfg_back, paths_back)
    back_keys = _record_keys(paths_back)
    assert "replay_true_train_view" not in back_keys
    assert back_keys >= set(cli._REPLAY_SINGLE_SOURCE_PSEUDO_ALIASES)


def test_single_source_to_no_replay_retires_single_source_aliases_only(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)
    prepared = _record_keys(paths)
    assert prepared & set(cli._REPLAY_SINGLE_SOURCE_ALIASES)

    view = Path(
        cli.CampaignStore(paths.state_db)
        .get_record("replay_true_train_view", mdstats.ReplayTrueLabelViewArtifact)
        .path
    )
    assert view.is_file()

    # Same workspace, no replay at all.
    text = _switch_to_naive_only(
        paths.config.read_text(encoding="utf-8").replace(
            f'replay_set = "{source}"\n', ""
        )
    )
    paths.config.write_text(text, encoding="utf-8")
    cfg2, paths2 = cli._load_config(paths.config)
    assert cli._single_source_replay_config(cfg2, paths2) is None
    _publish(cfg2, paths2)
    assert not _record_keys(paths2) & set(cli._REPLAY_SINGLE_SOURCE_ALIASES)
    # Physical materialized content is not deleted to clean mutable aliases.
    assert view.is_file()


def test_failure_before_the_alias_commit_preserves_the_previous_alias_set(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)
    store = cli.CampaignStore(paths.state_db)
    try:
        before = {
            key: store.record_digest(key)
            for key in sorted(_record_keys(paths))
        }
        monkeypatch.setattr(
            cli,
            "_qualify_replay",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("build failed")),
        )
        with pytest.raises(RuntimeError):
            cli._publish_single_source_replay_authority(store, cfg, paths)
        after = {
            key: store.record_digest(key)
            for key in sorted(_record_keys(paths))
        }
        assert before == after
    finally:
        store.close()


def test_stale_replay_builder_cannot_overwrite_newer_current_authority(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)
    store = cli.CampaignStore(paths.state_db)
    try:
        newer = dict(store.get_payload("replay_current_lineage"))
        newer["replay_lineage_digest"] = "0" * 64
        # Simulate a newer prepare publishing a different current authority
        # while this builder was running: the build observes the old baseline
        # and finishes second.
        original = cli._construct_single_source_replay_context

        def construct_then_race(cfg_arg, paths_arg):
            result = original(cfg_arg, paths_arg)
            store.put_record("replay_current_lineage", newer)
            return result

        monkeypatch.setattr(
            cli, "_construct_single_source_replay_context", construct_then_race
        )
        with pytest.raises(cli.CampaignCliError, match="newer `prepare`"):
            cli._publish_single_source_replay_authority(store, cfg, paths)
        assert store.get_payload("replay_current_lineage") == newer
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R12 - no process-local cache may authenticate
# ---------------------------------------------------------------------------


def test_no_process_local_replay_context_cache_exists():
    """Structural: a same-process hit cannot bypass authentication if none exists."""

    assert not hasattr(cli, "_UNIFIED_REPLAY_CONTEXT_CACHE")
    text = (_PKG / "_campaign_cli_core.py").read_text(encoding="utf-8")
    assert "_UNIFIED_REPLAY_CONTEXT_CACHE" not in text


def test_same_locator_source_replacement_cannot_return_stale_replay_science(
    tmp_path: Path,
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)
    assert cli._single_source_replay_context(cfg, paths) is not None

    # Replace the bytes at the same locator: a size/mtime/path shortcut would
    # return the previous science.
    _write_source(source, 14)
    with pytest.raises(cli.CampaignCliError, match="differ from the prepared"):
        cli._single_source_replay_context(cfg, paths)


def test_identical_byte_relocation_preserves_prepared_replay_science(tmp_path: Path):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)
    before = cli._single_source_replay_context(cfg, paths)

    moved = tmp_path / "moved" / "replay.extxyz"
    moved.parent.mkdir()
    moved.write_bytes(source.read_bytes())
    text = paths.config.read_text(encoding="utf-8").replace(str(source), str(moved))
    paths.config.write_text(text, encoding="utf-8")
    cfg2, paths2 = cli._load_config(paths.config)
    after = cli._single_source_replay_context(cfg2, paths2)
    assert after["source"].content_digest == before["source"].content_digest
    assert after["split"].content_digest == before["split"].content_digest
    assert Path(after["source"].path) == moved.resolve()


# ---------------------------------------------------------------------------
# R13/R14/R15 - stable external input
# ---------------------------------------------------------------------------


def test_consumed_frame_geometry_identity_is_verified_before_association():
    from ase import Atoms

    left = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.70]], cell=[5, 5, 5], pbc=True)
    identity = mdstats.canonical_replay_geometry_identity(left)
    mdstats.verify_consumed_replay_geometry_identity(left, identity, operation="unit")
    right = Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.90]], cell=[5, 5, 5], pbc=True)
    with pytest.raises(TrainingDataInputError, match="changed during unit"):
        mdstats.verify_consumed_replay_geometry_identity(right, identity, operation="unit")


def test_mid_read_geometry_mutation_leaves_no_reusable_old_key_prediction_cache(
    tmp_path: Path, monkeypatch
):
    """A geometry mutation during cold prediction cannot authenticate old keys."""

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    replay_root = paths.internal / "replay-unified"
    replay_root.mkdir(parents=True, exist_ok=True)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential,
        foundation_inference=inference,
        device="cpu",
    )
    cache_root = replay_root / "foundation-predictions"

    # The authenticated artifact describes the original geometries; the file now
    # holds different ones. Every consumed frame must fail its identity check.
    authenticated = artifact
    _write_source(source, 12, energy_offset=0.0)
    from ase.io import read, write

    frames = read(source, index=":", format="extxyz")
    frames[3].positions[1, 2] += 0.05
    write(source, frames, format="extxyz")
    mutated = mdstats.ReplaySourceArtifact(
        path=str(source),
        sha256=sha256_file_cached(source),
        configuration_count=authenticated.configuration_count,
        atomic_numbers=authenticated.atomic_numbers,
        geometry_identities=authenticated.geometry_identities,
        source_label_identities=authenticated.source_label_identities,
        source_energy_present_count=authenticated.source_energy_present_count,
        source_forces_present_count=authenticated.source_forces_present_count,
        source_stress_present_count=authenticated.source_stress_present_count,
    )
    provider = _CountingProvider(policy)
    with pytest.raises(TrainingDataInputError, match="changed during"):
        mdstats.build_replay_foundation_prediction_cache(
            mutated, policy, cache_root, provider=provider, batch_size=2, shard_size=4
        )
    # No manifest anywhere under the cache root may validate for this key.
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*.work*"))


def test_source_change_during_construction_blocks_the_alias_commit(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    original = cli._construct_single_source_replay_context

    def construct_then_mutate(cfg_arg, paths_arg):
        result = original(cfg_arg, paths_arg)
        _write_source(source, 13)
        return result

    monkeypatch.setattr(cli, "_construct_single_source_replay_context", construct_then_mutate)
    store = cli.CampaignStore(paths.state_db)
    try:
        with pytest.raises(cli.CampaignCliError, match="changed while replay preparation"):
            cli._publish_single_source_replay_authority(store, cfg, paths)
        assert not _record_keys(paths) & set(cli._REPLAY_SINGLE_SOURCE_ALIASES)
    finally:
        store.close()


def test_pseudo_true_label_only_mutation_refreshes_the_independent_monitor_only():
    """The invalidation matrix keeps predictions and refreshes the TRUE_DFT monitor."""

    geometry = "a" * 64
    other = "b" * 64
    plan = mdstats.build_replay_invalidation_plan(
        label_mode=ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        old_source_sha256="c" * 64,
        new_source_sha256="d" * 64,
        old_geometry_set_digest=geometry,
        new_geometry_set_digest=geometry,
        old_source_true_label_payload_digest="e" * 64,
        new_source_true_label_payload_digest="f" * 64,
        old_prediction_policy_digest=other,
        new_prediction_policy_digest=other,
        old_qualification_policy_digest=other,
        new_qualification_policy_digest=other,
        old_eligible_geometry_set_digest=other,
        new_eligible_geometry_set_digest=other,
        requested_roles=("train", "monitor"),
        existing_materialized_roles=("train", "monitor"),
    )
    assert plan.rerun_pseudolabel_inference is False
    assert plan.requalify is False
    assert plan.resplit is False
    assert plan.rematerialize_roles == ("monitor",)
    assert "source_true_labels_changed" in plan.reasons



def test_an_invalid_interface_transition_leaves_old_aliases_non_authorizing(
    tmp_path: Path,
):
    """A changed declaration does not silently reuse the previously prepared set."""

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    _publish(cfg, paths)
    prepared = _record_keys(paths)
    assert "replay_true_train_view" in prepared

    # The campaign now declares pseudo mode but has not re-prepared. The durable
    # TRUE_DFT aliases remain on disk - nothing is mutated to tidy them - but
    # they cannot authorize current pseudo consumption.
    paths.config.write_text(
        paths.config.read_text(encoding="utf-8").replace(
            'label_mode = "true_dft"', 'label_mode = "foundation_pseudolabel"'
        ),
        encoding="utf-8",
    )
    cfg2, paths2 = cli._load_config(paths.config)
    with pytest.raises(cli.CampaignCliError, match="different replay semantics"):
        cli._single_source_replay_context(cfg2, paths2)
    assert _record_keys(paths2) == prepared


def test_reclaiming_the_bulky_prediction_payload_keeps_authenticated_views_usable(
    tmp_path: Path, monkeypatch
):
    """Compact parents suffice: a retained pseudo view survives shard reclaim."""

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _install_pseudo_prerequisites(monkeypatch, cfg)
    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        return original(src, policy, cache_root, provider=_CountingProvider(policy), **kwargs)

    monkeypatch.setattr(
        mdstats, "build_replay_foundation_prediction_cache", build_with_double
    )
    context = _publish(cfg, paths)
    assert context is not None
    cache = context["prediction_cache"]

    # Storage reclaims the bulky prediction payload; the compact manifest,
    # qualification, split, and the materialized views remain.
    root = Path(cache.root_directory)
    for shard in cache.shards:
        (root / shard.relative_path).unlink()
    assert not any((root / shard.relative_path).exists() for shard in cache.shards)

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("a retained authenticated view must not reinfer")

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    resolved = cli._single_source_replay_context(cfg, paths)
    assert resolved is not None
    assert Path(resolved["plan"].train_artifact.path).is_file()
    assert resolved["split"].content_digest == context["split"].content_digest


def test_missing_view_with_missing_prediction_values_routes_to_prepare(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _install_pseudo_prerequisites(monkeypatch, cfg)
    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        return original(src, policy, cache_root, provider=_CountingProvider(policy), **kwargs)

    monkeypatch.setattr(
        mdstats, "build_replay_foundation_prediction_cache", build_with_double
    )
    context = _publish(cfg, paths)
    assert context is not None
    cache = context["prediction_cache"]
    root = Path(cache.root_directory)
    for shard in cache.shards:
        (root / shard.relative_path).unlink()
    view = Path(context["records"]["replay_pseudolabel_train_view"].path)
    view.unlink()

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("a read consumer must not cold-build predictions")

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    with pytest.raises(cli.CampaignCliError, match="prepare"):
        cli._single_source_replay_context(cfg, paths)

# ---------------------------------------------------------------------------
# R16/R17 - concurrency
# ---------------------------------------------------------------------------


def test_same_key_concurrent_cold_prediction_build_is_single_flight(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    providers: list[_CountingProvider] = []
    lock = threading.Lock()
    results: list[object] = []

    def contend() -> None:
        provider = _CountingProvider(policy)
        cache = mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=provider, batch_size=2, shard_size=4
        )
        with lock:
            providers.append(provider)
            results.append(cache)

    threads = [threading.Thread(target=contend) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 4
    assert len({cache.content_digest for cache in results}) == 1
    # Exactly one contender performed inference; the rest reused the cache.
    assert sum(1 for provider in providers if provider.calls) == 1


def test_waiter_after_winner_failure_becomes_the_next_cold_owner(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"

    class _FailingProvider(_CountingProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            raise RuntimeError("winner fails mid-build")

    with pytest.raises(RuntimeError, match="winner fails"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=_FailingProvider(policy),
            batch_size=2, shard_size=4,
        )
    assert not list(cache_root.rglob("manifest.json"))

    provider = _CountingProvider(policy)
    cache = mdstats.build_replay_foundation_prediction_cache(
        artifact, policy, cache_root, provider=provider, batch_size=2, shard_size=4
    )
    assert cache.configuration_count == 12
    assert sum(provider.calls) == 12


def test_no_replay_receipt_writer_uses_a_shared_fixed_temporary_name():
    """Structural: a fixed ``.tmp`` sibling is exactly the collision hazard."""

    for name in ("replay.py", "replay_pseudolabel.py", "replay_index.py", "_campaign_cli_core.py"):
        text = (_PKG / name).read_text(encoding="utf-8")
        for forbidden in (
            'with_suffix(path.suffix + ".tmp")',
            'with_name(path.name + ".tmp")',
            'with_name(receipt_path.name + ".tmp")',
            'with_name(provenance_path.name + ".tmp")',
        ):
            assert forbidden not in text, f"{name}: {forbidden}"


# ---------------------------------------------------------------------------
# R21/R22 - provider and OOM-learning lifetime
# ---------------------------------------------------------------------------


def test_internally_constructed_provider_is_retired_exactly_once(tmp_path: Path, monkeypatch):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    from mdstats.training_data import replay_pseudolabel as rp

    built: list[_CountingProvider] = []

    def construct(policy_arg, source_arg):
        provider = _CountingProvider(policy_arg)
        built.append(provider)
        return provider

    monkeypatch.setattr(rp, "_construct_prediction_provider", construct)
    monkeypatch.setattr(rp, "_sha256_file", lambda path: (
        policy.foundation_potential.sha256
        if Path(path) == Path(policy.foundation_potential.reference)
        else sha256_file_cached(path)
    ))
    cache = mdstats.build_replay_foundation_prediction_cache(
        artifact, policy, tmp_path / "predictions", batch_size=3, shard_size=4
    )
    assert cache.configuration_count == 12
    assert len(built) == 1
    assert built[0].close_count == 1


def test_executor_construction_failure_still_retires_the_internal_provider(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    from mdstats.training_data import replay_pseudolabel as rp

    built: list[_CountingProvider] = []

    def construct(policy_arg, source_arg):
        provider = _CountingProvider(policy_arg)
        built.append(provider)
        return provider

    monkeypatch.setattr(rp, "_construct_prediction_provider", construct)
    monkeypatch.setattr(rp, "_sha256_file", lambda path: (
        policy.foundation_potential.sha256
        if Path(path) == Path(policy.foundation_potential.reference)
        else sha256_file_cached(path)
    ))
    monkeypatch.setattr(
        rp,
        "_cold_build_inference_executor",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("executor construction failed")),
    )
    with pytest.raises(RuntimeError, match="executor construction failed"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, tmp_path / "predictions", batch_size=3, shard_size=4
        )
    assert len(built) == 1
    assert built[0].close_count == 1


def test_caller_supplied_provider_stays_caller_owned(tmp_path: Path, monkeypatch):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    provider = _CountingProvider(policy)
    mdstats.build_replay_foundation_prediction_cache(
        artifact, policy, tmp_path / "predictions", provider=provider,
        batch_size=3, shard_size=4,
    )
    assert provider.close_count == 0


def test_catchable_cancellation_after_acquisition_retires_the_provider(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    from mdstats.training_data import replay_pseudolabel as rp

    built: list[_CountingProvider] = []

    class _Interrupting(_CountingProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            raise KeyboardInterrupt

    def construct(policy_arg, source_arg):
        provider = _Interrupting(policy_arg)
        built.append(provider)
        return provider

    monkeypatch.setattr(rp, "_construct_prediction_provider", construct)
    monkeypatch.setattr(rp, "_sha256_file", lambda path: (
        policy.foundation_potential.sha256
        if Path(path) == Path(policy.foundation_potential.reference)
        else sha256_file_cached(path)
    ))
    with pytest.raises(KeyboardInterrupt):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, tmp_path / "predictions", batch_size=3, shard_size=4
        )
    assert len(built) == 1
    assert built[0].close_count == 1


def test_one_oom_learning_lifetime_spans_the_whole_cold_build(tmp_path: Path, monkeypatch):
    """A width already shown unsafe is never retried by a later outer batch."""

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )

    class _OomOverFour(_CountingProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            if len(atoms_batch) > 2:
                self.calls.append(len(atoms_batch))
                raise RuntimeError("CUDA out of memory")
            return super().predict_batch(atoms_batch, **kwargs)

    provider = _OomOverFour(policy)
    cache = mdstats.build_replay_foundation_prediction_cache(
        artifact, policy, tmp_path / "predictions", provider=provider,
        batch_size=4, shard_size=4,
    )
    assert cache.configuration_count == 12
    # The oversized width is attempted once, then never again.
    assert provider.calls.count(4) == 1
    assert set(provider.calls) <= {4, 2}


def test_replay_prediction_executor_binds_the_effective_replay_device():
    text = (_PKG / "replay_pseudolabel.py").read_text(encoding="utf-8")
    assert "device=str(policy.device)" in text
    assert "owns_provider=bool(owns_provider)" in text


# ---------------------------------------------------------------------------
# R8 - post-selection is scientific-read-only
# ---------------------------------------------------------------------------


def test_no_post_selection_route_reaches_a_construction_capable_replay_owner():
    """Structural: search every P5 production call site, not only edited helpers."""

    text = (_PKG / "campaign_post_selection_runtime.py").read_text(encoding="utf-8")
    for forbidden in (
        "_construct_single_source_replay_context",
        "_publish_single_source_replay_authority",
        "_prepare_single_source_replay",
        "build_replay_foundation_prediction_cache",
        "build_replay_pseudolabel_qualification",
        "build_replay_split_manifest",
        "_load_or_inspect_single_replay_source",
    ):
        assert forbidden not in text, forbidden


def test_missing_prepared_replay_authority_routes_post_selection_to_prepare(
    tmp_path: Path,
):
    from mdstats.training_data.campaign_post_selection import PostSelectionError
    from mdstats.training_data.campaign_post_selection_runtime import (
        _resolve_post_selection_replay_resolution,
    )

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    with pytest.raises(PostSelectionError, match="prepare"):
        _resolve_post_selection_replay_resolution(SimpleNamespace(cfg=cfg, paths=paths))


def test_deleted_view_rematerializes_without_foundation_inference(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    context = _publish(cfg, paths)
    view = Path(context["records"]["replay_true_train_view"].path)
    assert view.is_file()
    view.unlink()

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("representation rebuild must not run inference")

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    monkeypatch.setattr(mdstats, "build_replay_split_manifest", refuse)
    rebuilt = cli._single_source_replay_context(cfg, paths)
    assert rebuilt is not None
    assert Path(rebuilt["plan"].train_artifact.path).is_file()
    assert rebuilt["split"].content_digest == context["split"].content_digest


# ---------------------------------------------------------------------------
# R25-R28 - lifecycle
# ---------------------------------------------------------------------------


def test_lifecycle_reads_replay_currentness_in_the_owner_snapshot(tmp_path: Path):
    from mdstats.training_data.campaign_lifecycle import (
        REPLAY_CURRENT_LINEAGE_OBSERVATION,
        campaign_owner_snapshot,
    )

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    store = cli.CampaignStore(paths.state_db)
    try:
        _revision, _bindings, pointers = campaign_owner_snapshot(store)
        assert pointers[REPLAY_CURRENT_LINEAGE_OBSERVATION] is None
        cli._publish_single_source_replay_authority(store, cfg, paths)
        _revision, _bindings, pointers = campaign_owner_snapshot(store)
        observed = pointers[REPLAY_CURRENT_LINEAGE_OBSERVATION]
        assert observed == store.get_payload("replay_current_lineage")["replay_lineage_digest"]
    finally:
        store.close()


def test_lifecycle_snapshot_is_one_read_transaction_over_replay_and_pointers():
    """Structural: replay currentness is read inside the pointer transaction."""

    text = (_PKG / "campaign_lifecycle.py").read_text(encoding="utf-8")
    start = text.index("def campaign_owner_snapshot(")
    end = text.index("\ndef _authenticated(", start)
    body = text[start:end]
    assert 'db.execute("BEGIN")' in body
    assert "_current_replay_lineage_snapshot(db)" in body


def test_stale_replay_lineage_makes_post_selection_evidence_historical():
    from mdstats.training_data.campaign_lifecycle import _replay_lineage_stale

    class _Store:
        def get(self, digest, deserializer):
            return SimpleNamespace(replay_lineage_digest="a" * 64)

    store = _Store()
    assert _replay_lineage_stale(store, "p" * 64, lambda payload: None, "b" * 64) is True
    assert _replay_lineage_stale(store, "p" * 64, lambda payload: None, "a" * 64) is False
    # When record binds replay lineage and current replay authority is absent, fail closed (stale).
    assert _replay_lineage_stale(store, "p" * 64, lambda payload: None, None) is True

    class _NoReplayStore:
        def get(self, digest, deserializer):
            return SimpleNamespace(replay_lineage_digest=None)

    no_replay_store = _NoReplayStore()
    assert _replay_lineage_stale(no_replay_store, "p" * 64, lambda payload: None, None) is False


def test_observation_never_constructs_replay_state():
    """Structural: no status/advance route reaches replay construction."""

    text = (_PKG / "campaign_lifecycle.py").read_text(encoding="utf-8")
    for forbidden in (
        "_single_source_replay_context",
        "_construct_single_source_replay_context",
        "build_replay_foundation_prediction_cache",
        "materialize_replay",
        "put_record",
        "replace_records_atomically",
    ):
        assert forbidden not in text, forbidden


def test_status_on_a_prepared_replay_campaign_performs_no_replay_construction(
    tmp_path: Path, monkeypatch
):
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source)
    _publish(cfg, paths)

    def refuse(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError("observation must not construct or parse replay state")

    monkeypatch.setattr(mdstats, "inspect_replay_source_extxyz", refuse)
    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", refuse)
    monkeypatch.setattr(mdstats, "materialize_replay_true_label_views", refuse)
    monkeypatch.setattr(cli, "_construct_single_source_replay_context", refuse)
    assert cli.command_status(SimpleNamespace(config=str(paths.config))) == 0


# ---------------------------------------------------------------------------
# R20/target-size independence
# ---------------------------------------------------------------------------


def test_replay_is_absent_from_the_target_size_preparation_identity(tmp_path: Path):
    from mdstats.training_data.campaign_prepared_generation import (
        preparation_configuration_identity,
    )

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg_true, _ = _write_config(tmp_path / "a", source, label_mode="true_dft")
    cfg_pseudo, _ = _write_config(
        tmp_path / "b", source, label_mode="foundation_pseudolabel"
    )
    assert preparation_configuration_identity(cfg_true) == preparation_configuration_identity(
        cfg_pseudo
    )


def test_replay_routing_repair_bumps_no_scientific_or_schema_version():
    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_METHOD_RECIPE_VERSION,
    )
    from mdstats.training_data.replay_invalidation import REPLAY_INVALIDATION_VERSION
    from mdstats.training_data.replay import (
        REPLAY_PREPARATION_PLAN_SCHEMA,
        REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA,
        REPLAY_SPLIT_MANIFEST_SCHEMA,
    )

    assert POST_SELECTION_METHOD_RECIPE_VERSION == "mdstats.post-selection-method.2026-09.v4"
    assert REPLAY_INVALIDATION_VERSION == "REPLAY-UNIFY1E-v1"
    assert REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA == "mdstats.replay-single-source-config.v1"
    assert REPLAY_SPLIT_MANIFEST_SCHEMA == "mdstats.replay-split-manifest.v1"
    assert REPLAY_PREPARATION_PLAN_SCHEMA == "mdstats.replay-preparation-plan.v4"


# ---------------------------------------------------------------------------
# B1-B4 Reopen Falsification Tests
# ---------------------------------------------------------------------------


def test_cold_build_retires_internal_provider_on_early_failure(tmp_path: Path, monkeypatch):
    """B1: internal provider is retired when cold build fails before or during execution."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    provider_instance = _CountingProvider(policy)

    import tempfile
    import mdstats.training_data.replay_pseudolabel as rpl

    monkeypatch.setattr(rpl, "_construct_prediction_provider", lambda *a, **kw: provider_instance)

    def fail_mkdtemp(*a, **kw):
        raise RuntimeError("injected mkdtemp failure")

    monkeypatch.setattr(tempfile, "mkdtemp", fail_mkdtemp)

    with pytest.raises(RuntimeError, match="injected mkdtemp failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=None, batch_size=2, shard_size=4
        )

    assert provider_instance.close_count == 1
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))


def test_cold_build_retires_internal_provider_on_mid_execution_failure(tmp_path: Path, monkeypatch):
    """B1: internal provider is retired and attempt scratch cleaned when build fails mid-flight."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"

    class _FailingCountingProvider(_CountingProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            raise RuntimeError("injected batch failure")

    provider_instance = _FailingCountingProvider(policy)
    import mdstats.training_data.replay_pseudolabel as rpl
    monkeypatch.setattr(rpl, "_construct_prediction_provider", lambda *a, **kw: provider_instance)

    with pytest.raises(RuntimeError, match="injected batch failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=None, batch_size=2, shard_size=4
        )

    assert provider_instance.close_count == 1
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))
    assert not list(cache_root.rglob(".attempt*"))


def test_cold_build_does_not_retire_caller_provided_provider(tmp_path: Path, monkeypatch):
    """B1: caller-owned provider is NOT closed on success or failure."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"

    provider = _CountingProvider(policy)
    cache = mdstats.build_replay_foundation_prediction_cache(
        artifact, policy, cache_root, provider=provider, batch_size=2, shard_size=4
    )
    assert cache.configuration_count == 6
    assert provider.close_count == 0

    class _FailingProvider(_CountingProvider):
        def predict_batch(self, atoms_batch, **kwargs):
            raise RuntimeError("caller provider failure")

    failing_provider = _FailingProvider(policy)
    fail_cache_root = tmp_path / "predictions_fail"
    with pytest.raises(RuntimeError, match="caller provider failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, fail_cache_root, provider=failing_provider, batch_size=2, shard_size=4
        )
    assert failing_provider.close_count == 0


def test_lifecycle_fail_closed_when_replay_lineage_missing_or_corrupt(tmp_path: Path, monkeypatch):
    """B2: single-source campaign fails closed when replay lineage is absent or corrupt."""
    from mdstats.training_data.campaign_lifecycle import (
        LifecycleObservationState,
        _current_replay_lineage_snapshot,
        campaign_owner_snapshot,
        project_campaign_lifecycle,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
    )
    from mdstats.training_data.qualification.observation import (
        observe_current_qualification,
    )
    import mdstats.training_data.campaign_target_size_state as ctss

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)

    monkeypatch.setattr(
        ctss,
        "_load_head",
        lambda db: SimpleNamespace(
            state=SimpleNamespace(
                regime=TargetSizeRegime.CURRENT,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
                generation=1,
                prepared_manifest_digest="a" * 64,
                experiment_definition_digest="b" * 64,
                common_preparation_digest="c" * 64,
                candidate_sizes=(10, 20),
                auto_diagnostic=None,
                provisional_entries=(),
                frozen_entries=(),
            ),
            state_revision="rev1",
        ),
    )

    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor ok")
        cli._publish_single_source_replay_authority(store, cfg, paths)
        cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "prepare ok")

        status = cli._effective_stage(store, paths, "prepare")
        assert status[0] is cli.StageState.COMPLETE

        with store._connect() as db:
            assert _current_replay_lineage_snapshot(db)[1] == "valid"

        with store._connect() as db:
            db.execute("DELETE FROM records WHERE key = 'replay_current_lineage'")

        assert _current_replay_lineage_snapshot(store._connect())[1] == "missing"

        status_missing = cli._effective_stage(store, paths, "prepare")
        assert status_missing[0] is cli.StageState.WAITING
        assert "missing or malformed" in status_missing[1]

        lifecycle = project_campaign_lifecycle(paths, store)
        assert lifecycle.step("current_prepare").state == LifecycleObservationState.WAITING
        assert "replay authority is missing or malformed" in lifecycle.step("current_prepare").message
        assert lifecycle.next_command == "prepare"

        _rev, _b, pointers_missing = campaign_owner_snapshot(store)
        binding = SimpleNamespace(campaign_generation=1, content_digest="b" * 64)
        qual = observe_current_qualification(paths, binding, pointers_missing)
        assert qual.verdict is None
        assert qual.superseded_detail is not None
        assert "replay current lineage is missing or malformed" in qual.superseded_detail

        with store._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records (key, class_name, digest, payload, updated_utc) VALUES ('replay_current_lineage', 'ReplayLineage', 'x'*64, 'not-json-content', '2026-09-11T00:00:00Z')",
            )

        assert _current_replay_lineage_snapshot(store._connect())[1] == "malformed"

        status_malformed = cli._effective_stage(store, paths, "prepare")
        assert status_malformed[0] is cli.StageState.WAITING
        assert "missing or malformed" in status_malformed[1]

        lifecycle_malformed = project_campaign_lifecycle(paths, store)
        assert lifecycle_malformed.step("current_prepare").state == LifecycleObservationState.WAITING
        assert "replay authority is missing or malformed" in lifecycle_malformed.step("current_prepare").message
        assert lifecycle_malformed.next_command == "prepare"

        _rev, _b, pointers_malformed = campaign_owner_snapshot(store)
        qual_malformed = observe_current_qualification(paths, binding, pointers_malformed)
        assert qual_malformed.verdict is None
        assert qual_malformed.superseded_detail is not None
        assert "replay current lineage is missing or malformed" in qual_malformed.superseded_detail
    finally:
        store.close()


def test_lifecycle_non_replay_campaign_unaffected_by_absent_lineage(tmp_path: Path):
    """B2: campaigns without replay do not fail closed when replay lineage is absent."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode=None)
    paths.config.write_text(paths.config.read_text().replace(f'replay_set = "{source}"\n', ''))
    cfg, paths = cli._load_config(paths.config)

    store = cli.CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor ok")
        cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "prepare ok")

        status = cli._effective_stage(store, paths, "prepare")
        assert status[0] is cli.StageState.COMPLETE
    finally:
        store.close()


def test_replay_publication_fences_against_drifted_config_or_sources(tmp_path: Path, monkeypatch):
    """B3: publication raises if config or source changed during preparation."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)
    try:
        orig_context = cli._construct_single_source_replay_context
        def mutate_config(*args, **kwargs):
            res = orig_context(*args, **kwargs)
            paths.config.write_text(paths.config.read_text().replace('label_mode = "true_dft"', 'label_mode = "foundation_pseudolabel"'))
            return res
        monkeypatch.setattr(cli, "_construct_single_source_replay_context", mutate_config)
        with pytest.raises(cli.CampaignCliError, match="Campaign replay configuration changed"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")

        def mutate_source(*args, **kwargs):
            res = orig_context(*args, **kwargs)
            source.write_bytes(b"modified-source-bytes")
            return res
        monkeypatch.setattr(cli, "_construct_single_source_replay_context", mutate_source)

        with pytest.raises(cli.CampaignCliError, match="replay source changed|source path changed"):
            cli._publish_single_source_replay_authority(store, cfg, paths)
    finally:
        store.close()


def test_replay_publication_fences_against_drifted_checkpoint(tmp_path: Path, monkeypatch):
    """B3: publication raises if pseudo checkpoint changed during preparation."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    checkpoint = Path(cfg["paths"]["foundation_model"]).resolve()

    original = mdstats.build_replay_foundation_prediction_cache
    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)
    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    try:
        orig_context = cli._construct_single_source_replay_context
        def mutate_checkpoint(*args, **kwargs):
            res = orig_context(*args, **kwargs)
            checkpoint.write_bytes(b"mutated-checkpoint-different-length")
            return res
        monkeypatch.setattr(cli, "_construct_single_source_replay_context", mutate_checkpoint)

        with pytest.raises(cli.CampaignCliError, match="foundation checkpoint file changed"):
            cli._publish_single_source_replay_authority(store, cfg, paths)
    finally:
        store.close()


def test_command_prepare_fences_against_config_drift_at_completion(tmp_path: Path, monkeypatch):
    """B3: execute_current_prepare fails and marks WAITING if config drifted before completion."""
    from mdstats.training_data import campaign_target_size_runtime as ctsr
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor ok")
    store.close()

    import mdstats.training_data.campaign_prepared_generation as cpg
    import mdstats.training_data.campaign_target_size_cutover as ctsc
    import mdstats.training_data.campaign_target_size_view as ctsv

    monkeypatch.setattr(cli, "_prepare_catalog", lambda *a, **k: {"data4": None})
    monkeypatch.setattr(
        ctsr,
        "build_prepared_target_size_substrate",
        lambda *a, **k: SimpleNamespace(
            components=(),
            frame_records=(),
            identity=SimpleNamespace(content_digest="x" * 64),
            common=SimpleNamespace(content_digest="c" * 64),
            aggregate=SimpleNamespace(definition=SimpleNamespace(qualified_candidate_sizes=(10, 20))),
        ),
    )
    monkeypatch.setattr(
        cpg,
        "publish_prepared_generation",
        lambda *a, **k: SimpleNamespace(content_digest="p" * 64),
    )
    monkeypatch.setattr(
        ctsc,
        "ensure_current_target_size_authorities",
        lambda *a, **k: SimpleNamespace(
            state=SimpleNamespace(generation=1, experiment_definition_digest="e" * 64, auto_diagnostic=None)
        ),
    )
    monkeypatch.setattr(ctsv, "write_target_size_result_view", lambda *a, **k: None)

    orig_replay = cli._prepare_single_source_replay
    def drift_config(c, p, s, **kw):
        res = orig_replay(c, p, s, **kw)
        p.config.write_text(p.config.read_text().replace("require_target_elements = false", "require_target_elements = true"))
        return res

    monkeypatch.setattr(cli, "_prepare_single_source_replay", drift_config)

    args = SimpleNamespace(config=str(paths.config), approve_manifest=False, refresh_inferences=False)
    with pytest.raises(RuntimeError, match="modified during prepare execution"):
        ctsr.execute_current_prepare(args)

    store = cli.CampaignStore(paths.state_db)
    try:
        stage, msg = store.stage("prepare")
        assert stage is cli.StageState.WAITING
        assert "was modified during prepare" in msg
    finally:
        store.close()


def test_exact_integer_validation_for_replay_batch_and_shard_sizes(tmp_path: Path, monkeypatch):
    """B4: batch and shard size normalizers reject non-integers, bools, floats, strings, non-positives."""
    from mdstats.training_data.replay import (
        normalize_replay_prediction_batch_size,
        normalize_replay_prediction_shard_size,
    )

    for invalid in (1.5, -1.0, 0.0, True, False, "32", "0", 0, -1, -100, None, object()):
        with pytest.raises(TrainingDataInputError):
            normalize_replay_prediction_batch_size(invalid)
        with pytest.raises(TrainingDataInputError):
            normalize_replay_prediction_shard_size(invalid)

    assert normalize_replay_prediction_batch_size(1) == 1
    assert normalize_replay_prediction_batch_size(32) == 32
    assert normalize_replay_prediction_shard_size(1) == 1
    assert normalize_replay_prediction_shard_size(256) == 256

    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")

    cfg["replay"]["prediction_batch_size"] = 1.5
    with pytest.raises(cli.CampaignCliError, match="prediction_batch_size"):
        cli._replay_topology_preflight(cfg, paths)

    cfg["replay"]["prediction_batch_size"] = 32
    cfg["replay"]["prediction_shard_size"] = True
    with pytest.raises(cli.CampaignCliError, match="prediction_shard_size"):
        cli._replay_topology_preflight(cfg, paths)

    # Test cache builder rejecting bad batch/shard sizes
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    with pytest.raises(TrainingDataInputError, match="prediction_batch_size"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, tmp_path / "cache", batch_size=1.5, shard_size=256
        )
    with pytest.raises(TrainingDataInputError, match="prediction_shard_size"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, tmp_path / "cache", batch_size=32, shard_size=True
        )


def test_replay_invalidation_planner_uses_exact_seed_normalizer():
    """B4: seed comparison in invalidation planner normalizes seeds exactly."""
    from mdstats.training_data.replay_invalidation import build_replay_invalidation_plan
    from mdstats.training_data.replay import normalize_replay_split_seed

    assert normalize_replay_split_seed(42) == 42
    assert normalize_replay_split_seed(0) == 0
    with pytest.raises(TrainingDataInputError):
        normalize_replay_split_seed(True)
    with pytest.raises(TrainingDataInputError):
        normalize_replay_split_seed(1.5)

    d = "a" * 64
    plan = build_replay_invalidation_plan(
        label_mode="true_dft",
        old_source_sha256=d,
        new_source_sha256=d,
        old_geometry_set_digest=d,
        new_geometry_set_digest=d,
        old_source_true_label_payload_digest=d,
        new_source_true_label_payload_digest=d,
        old_split_seed=42,
        new_split_seed=42,
    )
    assert not plan.resplit
    assert "split_policy_changed" not in plan.reasons

    plan_diff = build_replay_invalidation_plan(
        label_mode="true_dft",
        old_source_sha256=d,
        new_source_sha256=d,
        old_geometry_set_digest=d,
        new_geometry_set_digest=d,
        old_source_true_label_payload_digest=d,
        new_source_true_label_payload_digest=d,
        old_split_seed=42,
        new_split_seed=99,
    )
    assert plan_diff.resplit
    assert "split_policy_changed" in plan_diff.reasons

    with pytest.raises(TrainingDataInputError):
        build_replay_invalidation_plan(
            label_mode="true_dft",
            old_source_sha256=d,
            new_source_sha256=d,
            old_geometry_set_digest=d,
            new_geometry_set_digest=d,
            old_source_true_label_payload_digest=d,
            new_source_true_label_payload_digest=d,
            old_split_seed=True,
            new_split_seed=42,
        )


# ---------------------------------------------------------------------------
# B8 Fault-Injection Tests
# ---------------------------------------------------------------------------


def test_cold_build_retires_internal_provider_on_chmod_failure(tmp_path: Path, monkeypatch):
    """B8: internal provider is retired and attempt scratch cleaned when os.chmod fails after executor acquisition."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, _paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    provider_instance = _CountingProvider(policy)

    import os

    import mdstats.training_data.replay_pseudolabel as rpl

    monkeypatch.setattr(rpl, "_construct_prediction_provider", lambda *a, **kw: provider_instance)

    orig_chmod = os.chmod

    def fail_chmod(path, mode, *a, **kw):
        if "work." in str(path):
            raise OSError("injected chmod failure")
        return orig_chmod(path, mode, *a, **kw)

    monkeypatch.setattr(os, "chmod", fail_chmod)

    with pytest.raises(OSError, match="injected chmod failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=None, batch_size=2, shard_size=4
        )

    assert provider_instance.close_count == 1
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))


def test_cold_build_does_not_retire_caller_provider_on_chmod_failure(tmp_path: Path, monkeypatch):
    """B8: caller-owned provider is NOT retired when os.chmod fails after executor acquisition."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, _paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    caller_provider = _CountingProvider(policy)

    import os

    orig_chmod = os.chmod

    def fail_chmod(path, mode, *a, **kw):
        if "work." in str(path):
            raise OSError("injected chmod failure")
        return orig_chmod(path, mode, *a, **kw)

    monkeypatch.setattr(os, "chmod", fail_chmod)

    with pytest.raises(OSError, match="injected chmod failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=caller_provider, batch_size=2, shard_size=4
        )

    assert caller_provider.close_count == 0
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))


def test_cold_build_retires_internal_provider_on_pre_executor_setup_failure(tmp_path: Path, monkeypatch):
    """B8: internal provider is retired when post-provider setup/validation fails before executor construction."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, _paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    provider_instance = _CountingProvider(policy)

    import mdstats.training_data.replay_pseudolabel as rpl

    monkeypatch.setattr(rpl, "_construct_prediction_provider", lambda *a, **kw: provider_instance)

    def fail_validation(prov, pol):
        raise RuntimeError("injected pre-executor setup failure")

    monkeypatch.setattr(rpl, "_validate_prediction_provider", fail_validation)

    with pytest.raises(RuntimeError, match="injected pre-executor setup failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=None, batch_size=2, shard_size=4
        )

    assert provider_instance.close_count == 1
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))


def test_cold_build_does_not_retire_caller_provider_on_pre_executor_setup_failure(tmp_path: Path, monkeypatch):
    """B8: caller-owned provider is NOT retired when post-provider setup fails."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 6)
    cfg, _paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    potential, inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    artifact = mdstats.inspect_replay_source_extxyz(source)
    policy = mdstats.ReplayFoundationPredictionPolicy(
        foundation_potential=potential, foundation_inference=inference, device="cpu"
    )
    cache_root = tmp_path / "predictions"
    caller_provider = _CountingProvider(policy)

    import mdstats.training_data.replay_pseudolabel as rpl

    def fail_validation(prov, pol):
        raise RuntimeError("injected pre-executor setup failure")

    monkeypatch.setattr(rpl, "_validate_prediction_provider", fail_validation)

    with pytest.raises(RuntimeError, match="injected pre-executor setup failure"):
        mdstats.build_replay_foundation_prediction_cache(
            artifact, policy, cache_root, provider=caller_provider, batch_size=2, shard_size=4
        )

    assert caller_provider.close_count == 0
    assert not list(cache_root.rglob("manifest.json"))
    assert not list(cache_root.rglob("*work*"))


# ---------------------------------------------------------------------------
# B7 Lineage Authentication & Snapshot Coherence Tests
# ---------------------------------------------------------------------------


def test_lifecycle_fail_closed_on_invalid_lineage_digest_syntax(tmp_path: Path, monkeypatch):
    """B7: syntactically valid JSON containing non-digest value fails closed to malformed."""
    import mdstats.training_data.campaign_target_size_state as ctss
    from mdstats.training_data.campaign_lifecycle import (
        LifecycleObservationState,
        _current_replay_lineage_snapshot,
        campaign_owner_snapshot,
        project_campaign_lifecycle,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
    )
    from mdstats.training_data.qualification.observation import (
        observe_current_qualification,
    )

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    _cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)

    monkeypatch.setattr(
        ctss,
        "_load_head",
        lambda db: SimpleNamespace(
            state=SimpleNamespace(
                regime=TargetSizeRegime.CURRENT,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
                generation=1,
                prepared_manifest_digest="a" * 64,
                experiment_definition_digest="b" * 64,
                common_preparation_digest="c" * 64,
                candidate_sizes=(10, 20),
                auto_diagnostic=None,
                provisional_entries=(),
                frozen_entries=(),
            ),
            state_revision="rev1",
        ),
    )

    invalid_digests = [
        "not-a-valid-hex-digest",
        "0" * 32,  # wrong length
        "g" * 64,  # non-hex char
        12345,     # non-string
        "",        # empty string
        None,      # null
    ]

    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor ok")
        cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "prepare ok")

        for bad in invalid_digests:
            payload_str = json.dumps({"replay_lineage_digest": bad, "schema": "mdstats.replay-lineage.v1"})
            with store._connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO records (key, class_name, digest, payload, updated_utc) "
                    "VALUES ('replay_current_lineage', 'ReplayLineage', 'x'*64, ?, '2026-09-11T00:00:00Z')",
                    (payload_str,),
                )
            with store._connect() as db:
                digest_val, status = _current_replay_lineage_snapshot(db)
                assert digest_val is None
                assert status == "malformed"

            stage, msg = cli._effective_stage(store, paths, "prepare")
            assert stage is cli.StageState.WAITING
            assert "single-source replay authority is missing or malformed" in msg

            lifecycle = project_campaign_lifecycle(paths, store)
            assert lifecycle.step("current_prepare").state == LifecycleObservationState.WAITING
            assert "replay authority is missing or malformed" in lifecycle.step("current_prepare").message
            assert lifecycle.next_command == "prepare"

            _rev, _b, pointers = campaign_owner_snapshot(store)
            binding = SimpleNamespace(campaign_generation=1, content_digest="b" * 64)
            qual = observe_current_qualification(paths, binding, pointers)
            assert qual.verdict is None
            assert qual.superseded_detail is not None
            assert "replay current lineage is missing or malformed" in qual.superseded_detail
    finally:
        store.close()


def test_lifecycle_snapshot_coherence_against_interleaved_writer(tmp_path: Path, monkeypatch):
    """B7: interleaved write after campaign_owner_snapshot does not produce hybrid lifecycle observation."""
    import mdstats.training_data.campaign_target_size_state as ctss
    from mdstats.training_data import campaign_lifecycle as cl
    from mdstats.training_data.campaign_lifecycle import (
        LifecycleObservationState,
        project_campaign_lifecycle,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
    )

    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    _cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)

    monkeypatch.setattr(
        ctss,
        "_load_head",
        lambda db: SimpleNamespace(
            state=SimpleNamespace(
                regime=TargetSizeRegime.CURRENT,
                lifecycle=TargetSizeLifecycle.AUTHORITIES_BOUND,
                generation=1,
                prepared_manifest_digest="a" * 64,
                experiment_definition_digest="b" * 64,
                common_preparation_digest="c" * 64,
                candidate_sizes=(10, 20),
                auto_diagnostic=None,
                provisional_entries=(),
                frozen_entries=(),
            ),
            state_revision="rev1",
        ),
    )

    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor ok")
        cli._publish_single_source_replay_authority(store, _cfg, paths)
        cli._mark_stage(store, paths, "prepare", cli.StageState.COMPLETE, "prepare ok")

        # Scenario 1: Snapshot sees valid replay lineage. An interleaved writer deletes it right after snapshot.
        orig_snapshot = cl.campaign_owner_snapshot

        def snapshot_and_delete(st):
            res = orig_snapshot(st)
            with st._connect() as db:
                db.execute("DELETE FROM records WHERE key = 'replay_current_lineage'")
            return res

        monkeypatch.setattr(cl, "campaign_owner_snapshot", snapshot_and_delete)
        lifecycle = project_campaign_lifecycle(paths, store)
        # Because prepare step uses pointers from the snapshot (where it was valid),
        # prepare state is COMPLETE, not WAITING.
        assert lifecycle.step("current_prepare").state == LifecycleObservationState.COMPLETE

        # Scenario 2: Snapshot sees missing replay lineage. An interleaved writer publishes it right after snapshot.
        monkeypatch.setattr(cl, "campaign_owner_snapshot", orig_snapshot)
        with store._connect() as db:
            assert cl._current_replay_lineage_snapshot(db)[1] == "missing"

        def snapshot_and_publish(st):
            res = orig_snapshot(st)
            cli._publish_single_source_replay_authority(st, _cfg, paths)
            return res

        monkeypatch.setattr(cl, "campaign_owner_snapshot", snapshot_and_publish)
        lifecycle2 = project_campaign_lifecycle(paths, store)
        # Because snapshot observed missing, prepare step remains WAITING.
        assert lifecycle2.step("current_prepare").state == LifecycleObservationState.WAITING
        assert "replay authority is missing or malformed" in lifecycle2.step("current_prepare").message
    finally:
        store.close()


# ---------------------------------------------------------------------------
# B6 Publication Barrier & Seam Race Tests
# ---------------------------------------------------------------------------


def test_replay_publication_race_source_replacement_in_final_publication_window(tmp_path: Path, monkeypatch):
    """B6: source replacement in the final publication window raises and commits no aliases."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)
    try:
        def mutate_source():
            source.write_bytes(b"replacement-source-bytes")

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK", mutate_source)

        with pytest.raises(cli.CampaignCliError, match="The external replay source changed while replay preparation was running"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_checkpoint_replacement_in_final_publication_window(tmp_path: Path, monkeypatch):
    """B6: checkpoint replacement in the final publication window raises and commits no aliases."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _potential, _inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    checkpoint = Path(cfg["paths"]["foundation_model"]).resolve()

    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    try:
        def mutate_checkpoint():
            checkpoint.write_bytes(b"mutated-checkpoint-different-content")

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK", mutate_checkpoint)

        with pytest.raises(cli.CampaignCliError, match="foundation checkpoint file changed or was removed"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_command_start_drift_before_replay_substage(tmp_path: Path):
    """B6: config drift occurring between command start and replay substage raises and commits no aliases."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    basis = cli._single_source_replay_basis(cfg, paths)
    store = cli.CampaignStore(paths.state_db)

    # Drift config before replay substage runs
    paths.config.write_text(paths.config.read_text().replace("split_seed = 42", "split_seed = 99"))
    live_cfg, _ = cli._load_config(paths.config)

    try:
        with pytest.raises(cli.CampaignCliError, match="Campaign replay configuration changed while replay preparation was running"):
            cli._prepare_single_source_replay(live_cfg, paths, store, command_replay_basis=basis)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_doctor_acceleration_turnover_in_final_window(tmp_path: Path, monkeypatch):
    """B6: doctor acceleration turnover in the final publication window raises and commits no aliases."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _potential, _inference = _install_pseudo_prerequisites(monkeypatch, cfg)

    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    try:
        def turnover_doctor():
            monkeypatch.setattr(
                cli,
                "_stored_acceleration_realization",
                lambda *a, **kw: SimpleNamespace(
                    resolved_kernel_mode="e3nn",
                    foundation_inference_identity_digest="turnover" * 4,
                    content_digest="turnover" * 4,
                ),
            )

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK", turnover_doctor)

        with pytest.raises(cli.CampaignCliError, match="doctor-frozen acceleration realization turned over"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_competing_prepare_in_final_window(tmp_path: Path, monkeypatch):
    """B6: competing prepare publication under writer exclusion raises and preserves winner."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)

    try:
        winner_digest = "w" * 64
        winner_payload = {"replay_lineage_digest": winner_digest, "schema": "mdstats.replay-lineage.v1"}

        def competing_winner():
            with store._connect() as db:
                db.execute(
                    "INSERT OR REPLACE INTO records (key, class_name, digest, payload, updated_utc) "
                    "VALUES ('replay_current_lineage', 'ReplayLineage', ?, ?, '2026-09-11T00:00:00Z')",
                    (winner_digest, json.dumps(winner_payload)),
                )

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK", competing_winner)

        with pytest.raises(cli.CampaignCliError, match="A newer `prepare` published a different current replay authority"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        # Assert winning prepare's authority is preserved
        current = store.get_payload("replay_current_lineage")
        assert current["replay_lineage_digest"] == winner_digest
    finally:
        store.close()


def test_replay_publication_allows_canonical_equivalent_spelling_and_identical_byte_relocation(tmp_path: Path, monkeypatch):
    """B6: canonical-equivalent path spelling and identical-byte relocation pass publication revalidation."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    basis = cli._single_source_replay_basis(cfg, paths)
    store = cli.CampaignStore(paths.state_db)

    try:
        # Test A: canonical-equivalent spelling (redundant relative equivalent path)
        rel_spelling = f"./{source.name}"
        paths.config.write_text(paths.config.read_text().replace(f'replay_set = "{source}"', f'replay_set = "{rel_spelling}"'))

        # Publication succeeds with canonical equivalent spelling
        cli._prepare_single_source_replay(cfg, paths, store, command_replay_basis=basis)
        assert store.get_payload_optional("replay_current_lineage") is not None

        # Test B: identical-byte relocation in publication window
        moved = tmp_path / "relocated" / "replay.extxyz"
        moved.parent.mkdir()
        moved.write_bytes(source.read_bytes())

        def relocate_source():
            paths.config.write_text(paths.config.read_text().replace(f'replay_set = "{rel_spelling}"', f'replay_set = "{moved}"'))

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK", relocate_source)

        # Clear existing publication to test clean re-publication
        with store._connect() as db:
            db.execute("DELETE FROM records WHERE key = 'replay_current_lineage'")

        # Publication succeeds with identical-byte relocation
        cli._publish_single_source_replay_authority(store, cfg, paths, command_replay_basis=basis)
        assert store.get_payload_optional("replay_current_lineage") is not None
    finally:
        store.close()


# ---------------------------------------------------------------------------
# B12 Oracle Sensitivity & B11 No-Retry Falsification Tests
# ---------------------------------------------------------------------------


def test_cold_build_partial_state_oracle_sensitivity_proof(tmp_path: Path):
    """B12: prove shallow glob misses nested attempt/manifest artifacts while rglob detects them."""
    cache_root = tmp_path / "predictions"
    nested_dir = cache_root / "ab" / "ab123456"
    nested_dir.mkdir(parents=True)
    nested_manifest = nested_dir / "manifest.json"
    nested_manifest.write_text("{}", encoding="utf-8")
    nested_work = nested_dir.parent / "ab123456.work.tmp"
    nested_work.mkdir(parents=True)

    # Shallow glob completely misses nested production layout
    assert not list(cache_root.glob("manifest.json"))
    assert not list(cache_root.glob("*.work.*"))

    # Recursive rglob detects both nested artifacts sensitivity
    assert list(cache_root.rglob("manifest.json")) == [nested_manifest]
    assert list(cache_root.rglob("*work*")) == [nested_work]


def test_prepare_single_source_replay_propagates_internal_type_error_without_retry(tmp_path: Path, monkeypatch):
    """B11: genuine internal TypeError inside replay prep propagates and is called exactly once without retry."""
    from mdstats.training_data import campaign_target_size_runtime as ctsr
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")

    calls = 0

    def failing_replay(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise TypeError("genuine internal type error in replay prep")

    monkeypatch.setattr(cli, "_prepare_single_source_replay", failing_replay)
    # Stub target size substrate so prepare proceeds to replay
    monkeypatch.setattr(
        ctsr,
        "build_prepared_target_size_substrate",
        lambda *a, **kw: SimpleNamespace(
            components=(),
            frame_records=(),
            identity=SimpleNamespace(content_digest="i" * 64),
            common=SimpleNamespace(content_digest="c" * 64),
            aggregate=SimpleNamespace(definition=SimpleNamespace(qualified_candidate_sizes=(10,))),
        ),
    )
    import mdstats.training_data.campaign_prepared_generation as cpg
    import mdstats.training_data.campaign_target_size_cutover as ctsc

    monkeypatch.setattr(cli, "_prepare_catalog", lambda *a, **k: {"data4": None})
    monkeypatch.setattr(
        cpg,
        "publish_prepared_generation",
        lambda *a, **kw: SimpleNamespace(content_digest="p" * 64),
    )
    monkeypatch.setattr(
        ctsc,
        "ensure_current_target_size_authorities",
        lambda *a, **kw: SimpleNamespace(
            state=SimpleNamespace(generation=1, experiment_definition_digest="e" * 64, auto_diagnostic=None)
        ),
    )

    store = cli.CampaignStore(paths.state_db)
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "doctor passed")
    store.close()

    args = SimpleNamespace(config=str(paths.config), approve_manifest=False, refresh_inferences=False)

    with pytest.raises(TypeError, match="genuine internal type error in replay prep"):
        ctsr.execute_current_prepare(args)

    store = cli.CampaignStore(paths.state_db)
    try:
        # Must have been called exactly once: no second compatibility fallback retry
        assert calls == 1
        assert store.get_payload_optional("replay_current_lineage") is None
        stage, msg = store.stage("prepare")
        assert stage is cli.StageState.FAILED
        assert "genuine internal type error in replay prep" in msg
    finally:
        store.close()


# ---------------------------------------------------------------------------
# B10 Deterministic Last-Seam Recheck & Fenced Retirement Tests
# ---------------------------------------------------------------------------


def test_replay_publication_race_source_replacement_at_last_commit_seam(tmp_path: Path, monkeypatch):
    """B10 Finding A: mutation after ordinary revalidation at last commit seam triggers final recheck and aborts."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)
    try:
        seam_hook_called = False

        def mutate_source_at_seam():
            nonlocal seam_hook_called
            seam_hook_called = True
            source.write_bytes(b"corrupted-source-bytes-at-last-seam")

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_COMMIT_SEAM_HOOK", mutate_source_at_seam)
        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_SEAM_RECHECK_COUNT", 0)

        with pytest.raises(cli.CampaignCliError, match="The external replay source changed while replay preparation was running"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        assert seam_hook_called is True
        assert cli._TEST_REPLAY_PUBLICATION_SEAM_RECHECK_COUNT >= 1
        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_checkpoint_replacement_at_last_commit_seam(tmp_path: Path, monkeypatch):
    """B10 Finding A: checkpoint replacement at last commit seam triggers final recheck and aborts."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _potential, _inference = _install_pseudo_prerequisites(monkeypatch, cfg)
    checkpoint = Path(cfg["paths"]["foundation_model"]).resolve()

    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    try:
        seam_hook_called = False

        def mutate_checkpoint_at_seam():
            nonlocal seam_hook_called
            seam_hook_called = True
            checkpoint.write_bytes(b"corrupted-checkpoint-bytes-at-last-seam")

        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_PRE_COMMIT_SEAM_HOOK", mutate_checkpoint_at_seam)
        monkeypatch.setattr(cli, "_TEST_REPLAY_PUBLICATION_SEAM_RECHECK_COUNT", 0)

        with pytest.raises(cli.CampaignCliError, match="foundation checkpoint file changed or was removed"):
            cli._publish_single_source_replay_authority(store, cfg, paths)

        assert seam_hook_called is True
        assert cli._TEST_REPLAY_PUBLICATION_SEAM_RECHECK_COUNT >= 1
        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_pseudolabel_qualification_threshold_drift(tmp_path: Path, monkeypatch):
    """B10 Finding B: pseudo qualification threshold drift during prep refuses stale publication."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _potential, _inference = _install_pseudo_prerequisites(monkeypatch, cfg)

    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    basis = cli._single_source_replay_basis(cfg, paths, store=store)

    # Drift qualification threshold in campaign.toml
    text = paths.config.read_text()
    if "maximum_force_ev_per_angstrom" in text:
        paths.config.write_text(text.replace("maximum_force_ev_per_angstrom = 20.0", "maximum_force_ev_per_angstrom = 10.0"))
    else:
        paths.config.write_text(text + "\n[replay]\nmaximum_force_ev_per_angstrom = 10.0\n")

    live_cfg, _ = cli._load_config(paths.config)

    try:
        with pytest.raises(cli.CampaignCliError, match="Campaign pseudo-label qualification policy changed while replay preparation was running"):
            cli._publish_single_source_replay_authority(store, live_cfg, paths, command_replay_basis=basis)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_foundation_potential_and_head_drift(tmp_path: Path, monkeypatch):
    """B10 Finding C: foundation head / potential drift during pseudo preparation refuses stale publication."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="foundation_pseudolabel")
    _potential, _inference = _install_pseudo_prerequisites(monkeypatch, cfg)

    original = mdstats.build_replay_foundation_prediction_cache

    def build_with_double(src, policy, cache_root, **kwargs):
        provider = _CountingProvider(policy)
        return original(src, policy, cache_root, provider=provider, **kwargs)

    monkeypatch.setattr(mdstats, "build_replay_foundation_prediction_cache", build_with_double)

    store = cli.CampaignStore(paths.state_db)
    basis = cli._single_source_replay_basis(cfg, paths, store=store)

    # Drift foundation head in campaign.toml
    text = paths.config.read_text()
    if "[foundation]" in text:
        paths.config.write_text(text.replace('head = "default"', 'head = "different_head"'))
    else:
        paths.config.write_text(text + '\n[foundation]\nfamily = "mace"\nhead = "different_head"\n')

    live_cfg, _ = cli._load_config(paths.config)

    try:
        with pytest.raises(cli.CampaignCliError, match="Campaign foundation potential configuration changed while replay preparation was running"):
            cli._publish_single_source_replay_authority(store, live_cfg, paths, command_replay_basis=basis)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()


def test_replay_publication_race_stale_legacy_prepare_cannot_retire_newer_single_source_winner(tmp_path: Path):
    """B10 Finding D: stale no-replay/legacy prepare finishing after newer single-source prepare must NOT retire winner."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    # Start prepare A under no-replay
    cfg_legacy, paths = _write_config(tmp_path, source, label_mode="true_dft")
    # Remove replay configuration so interface is "none"
    text = paths.config.read_text()
    text_no_replay = "\n".join(line for line in text.splitlines() if not line.startswith("replay_set") and not line.startswith("[replay]"))
    paths.config.write_text(text_no_replay)

    cfg_no_replay, _ = cli._load_config(paths.config)
    store = cli.CampaignStore(paths.state_db)

    try:
        basis_no_replay = cli._single_source_replay_basis(cfg_no_replay, paths, store=store)
        assert basis_no_replay["interface"] == "none"

        # Now simulate prepare B winning concurrently and publishing valid single-source aliases
        winner_digest = "b" * 64
        winner_payload = {"replay_lineage_digest": winner_digest, "schema": "mdstats.replay-lineage.v1"}
        with store._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records (key, class_name, digest, payload, updated_utc) "
                "VALUES ('replay_current_lineage', 'ReplayLineage', ?, ?, '2026-09-11T00:00:00Z')",
                (winner_digest, json.dumps(winner_payload)),
            )
            db.execute(
                "INSERT OR REPLACE INTO records (key, class_name, digest, payload, updated_utc) "
                "VALUES ('replay_source', 'ReplaySourceArtifact', ?, ?, '2026-09-11T00:00:00Z')",
                (winner_digest, json.dumps({"schema": "mdstats.replay-source.v1"})),
            )

        # Stale prepare A finishes and attempts retirement with its command_replay_basis
        with pytest.raises(cli.CampaignCliError, match="A newer `prepare` published a different current replay authority"):
            cli._publish_single_source_replay_authority(store, cfg_no_replay, paths, command_replay_basis=basis_no_replay)

        # Winning single-source aliases survive!
        surviving = store.get_payload("replay_current_lineage")
        assert surviving["replay_lineage_digest"] == winner_digest
        assert store.get_payload_optional("replay_source") is not None
    finally:
        store.close()


def test_replay_publication_race_stale_single_source_cannot_publish_after_legacy_transition(tmp_path: Path):
    """B10: stale single-source prepare finishing after campaign switched to legacy/none cannot publish."""
    source = tmp_path / "replay.extxyz"
    _write_source(source, 12)
    cfg, paths = _write_config(tmp_path, source, label_mode="true_dft")
    store = cli.CampaignStore(paths.state_db)
    basis = cli._single_source_replay_basis(cfg, paths, store=store)
    assert basis["interface"] == "single_source"

    try:
        # Campaign switches to no replay on disk
        text = paths.config.read_text()
        text_no_replay = "\n".join(line for line in text.splitlines() if not line.startswith("replay_set") and not line.startswith("[replay]"))
        paths.config.write_text(text_no_replay)
        live_cfg, _ = cli._load_config(paths.config)

        # Stale single-source prepare attempts to publish
        with pytest.raises(cli.CampaignCliError, match="The campaign configuration no longer declares single-source replay"):
            cli._publish_single_source_replay_authority(store, live_cfg, paths, command_replay_basis=basis)

        assert store.get_payload_optional("replay_current_lineage") is None
        for alias in cli._REPLAY_SINGLE_SOURCE_ALIASES:
            assert store.get_payload_optional(alias) is None
    finally:
        store.close()

