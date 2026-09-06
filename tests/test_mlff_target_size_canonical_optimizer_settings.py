"""Canonical configuration authority for the shared training/optimizer semantics.

Before this closure the same ``[training]`` keys were resolved twice, with
different defaults: once by the executable optimizer construction in the
campaign CLI and once by the P5 method identity.  A recorded "method identity"
could therefore describe a method that never executed, several supported
optimizer keys never reached training at all, common preparation hashed batch
size and learned-model dtype it does not consume, and the target-size screen
hashed generic optimizer fields it does not own.

These tests hold the corrected ownership at the real owners:

* **A** - one canonical resolution feeds P5 method identity, the executable
  ``MaceOptimizerPolicy``, the generated internal MACE config, and the
  executable MACE projection;
* **B** - batch size and learned-model dtype are not common-preparation
  identity, while genuine common-fit inputs still are;
* **C** - target-size scientific currentness keeps the fields that move a
  trajectory and drops the execution-only ones;
* **E** - P5 identity is the method that executes, and old method-recipe
  evidence cannot authorize corrected runs.

Restart across execution-only drift at the real production owner (**D**) lives
in ``test_mlff_target_size_execution_only_drift_restart.py``.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError, digest
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.post_selection_execution import (
    post_selection_mace_run_configuration,
)
from mdstats.training_data.post_selection_identity import (
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TargetSizeCommonTrainingPolicy,
    resolve_target_size_common_training_policy,
)
from mdstats.training_data.target_size_execution.context import (
    seed_neutral_optimizer_policy_digest,
)
from mdstats.training_data.training_settings import (
    CampaignCliError,
    resolve_binary_model_dtype,
    resolve_shared_optimizer_settings,
)


#: Deliberately non-default, mutually distinct values for every shared field.
_DISTINCT = {
    "learning_rate": 7.5e-4,
    "batch_size": 6,
    "valid_batch_size": 3,
    "eval_interval": 5,
    "ema": False,
    "ema_decay": 0.9871,
    "amsgrad": False,
    "weight_decay": 3.25e-5,
    "clip_grad": 42.5,
}

#: The values the executable campaign path applies when configuration omits the
#: key.  These are product truth: they are what training actually did.
_EXECUTABLE_DEFAULTS = {
    "learning_rate": 1.0e-4,
    "batch_size": 2,
    "valid_batch_size": 2,
    "eval_interval": 1,
    "ema": True,
    "ema_decay": 0.99999,
    "amsgrad": True,
    "weight_decay": 1.0e-6,
    "clip_grad": 10.0,
}


def _config(**training):
    base = {
        "policy_generation": "train2",
        "device": "cpu",
        "dtype": "float32",
    }
    base.update(training)
    return {"campaign": {"precision_profile": "single"}, "training": base}


# ---------------------------------------------------------------------------
# A. Canonical shared optimizer parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("explicit", [True, False], ids=["explicit", "omitted"])
def test_a_one_canonical_resolution_reaches_every_shared_consumer(explicit: bool):
    """Resolved settings, P5 identity, policy, and both configs are one method."""

    expected = dict(_DISTINCT) if explicit else dict(_EXECUTABLE_DEFAULTS)
    cfg = _config(**(_DISTINCT if explicit else {}))

    settings = resolve_shared_optimizer_settings(cfg)
    assert settings == expected

    # The executable optimizer construction consumes the canonical resolution.
    policy = cli._optimizer_policy(cfg, seed=11, num_workers=4, planned_epochs=9)
    for field, value in expected.items():
        assert getattr(policy, field) == value, field
    # Role-local inputs stay outside the shared settings.
    assert policy.seed == 11
    assert policy.num_workers == 4
    assert policy.max_num_epochs == 9
    assert "num_workers" not in settings
    assert "seed" not in settings
    assert "max_num_epochs" not in settings

    # The learned-model dtype comes from the one binary precision authority on
    # both sides rather than an independent P5 default of FP64.
    identity = resolve_post_selection_method_identity(cfg)
    assert resolve_binary_model_dtype(cfg) == "float32"
    assert policy.default_dtype == "float32"
    assert identity.default_dtype == "float32"

    # P5 method identity summarises exactly this resolution.
    assert identity.shared_optimizer_settings_digest == digest(
        {"schema": "mdstats.shared-optimizer-settings.v2", **expected}
    )

    # The internal MACE configuration and the executable MACE projection agree.
    internal = _internal_post_selection_config(cfg, policy, identity)
    assert internal["lr"] == expected["learning_rate"]
    assert internal["batch_size"] == expected["batch_size"]
    assert internal["valid_batch_size"] == expected["valid_batch_size"]
    assert internal["eval_interval"] == expected["eval_interval"]
    assert internal["ema"] == expected["ema"]
    assert internal["ema_decay"] == expected["ema_decay"]
    assert internal["amsgrad"] == expected["amsgrad"]
    assert internal["weight_decay"] == expected["weight_decay"]
    assert internal["clip_grad"] == expected["clip_grad"]
    assert internal["default_dtype"] == "float32"

    executable = post_selection_mace_run_configuration(internal)
    assert float(executable["lr"]) == expected["learning_rate"]
    assert int(executable["batch_size"]) == expected["batch_size"]
    assert int(executable["valid_batch_size"]) == expected["valid_batch_size"]
    assert int(executable["eval_interval"]) == expected["eval_interval"]
    assert bool(executable["ema"]) == expected["ema"]
    assert float(executable["ema_decay"]) == expected["ema_decay"]
    assert bool(executable["amsgrad"]) == expected["amsgrad"]
    assert float(executable["weight_decay"]) == expected["weight_decay"]
    assert float(executable["clip_grad"]) == expected["clip_grad"]


def _internal_post_selection_config(cfg, policy, identity):
    """The real internal P5 MACE configuration for a bounded synthetic run."""

    from types import SimpleNamespace

    from mdstats.training_data.post_selection_execution import _post_selection_mace_config

    artifact = SimpleNamespace(relative_path="train.extxyz", atomic_numbers=(3, 8))
    monitor = SimpleNamespace(relative_path="valid.extxyz", atomic_numbers=(3, 8))
    preparation = SimpleNamespace(
        fitted_atomic_references=SimpleNamespace(
            reference_energies_ev=((3, -1.0), (8, -2.0))
        ),
        objective_policy=mdstats.TrainingObjectivePolicy(),
    )
    policies = resolve_post_selection_method_policies(cfg)
    return _post_selection_mace_config(
        run_identity="ab" * 32,
        optimizer_seed=int(policy.seed),
        planned_epochs=int(policy.max_num_epochs),
        preparation=preparation,
        optimizer_policy=policy,
        target_train=artifact,
        monitor=monitor,
        extxyz_policy=policies.extxyz,
        method=identity,
        mace_architecture=policies.mace_architecture,
    )


@pytest.mark.parametrize("field", sorted(_DISTINCT))
def test_a_each_explicit_shared_field_moves_identity_and_execution(field: str):
    """A supported explicit value must change both identity and training."""

    baseline_cfg = _config()
    mutated_cfg = _config(**{field: _DISTINCT[field]})

    baseline_identity = resolve_post_selection_method_identity(baseline_cfg)
    mutated_identity = resolve_post_selection_method_identity(mutated_cfg)
    assert (
        baseline_identity.shared_optimizer_settings_digest
        != mutated_identity.shared_optimizer_settings_digest
    )
    assert baseline_identity.content_digest != mutated_identity.content_digest

    baseline_policy = cli._optimizer_policy(baseline_cfg, seed=1, num_workers=0)
    mutated_policy = cli._optimizer_policy(mutated_cfg, seed=1, num_workers=0)
    executable_field = "learning_rate" if field == "learning_rate" else field
    assert getattr(mutated_policy, executable_field) == _DISTINCT[field]
    assert baseline_policy.policy_digest != mutated_policy.policy_digest


def test_a_worker_count_is_execution_only_for_p5_method_identity():
    """Resource scheduling never enters the shared method."""

    cfg = _config(num_workers=13)
    assert "num_workers" not in resolve_shared_optimizer_settings(cfg)
    assert (
        resolve_post_selection_method_identity(cfg).content_digest
        == resolve_post_selection_method_identity(_config()).content_digest
    )


def test_a_unsupported_optimizer_family_still_fails_closed():
    with pytest.raises(TrainingDataInputError):
        resolve_shared_optimizer_settings({"training": {"optimizer": "rmsprop"}})
    with pytest.raises(TrainingDataInputError):
        resolve_shared_optimizer_settings({"training": {"optimizer": "sgd"}})
    # The one accepted family still resolves.
    assert resolve_shared_optimizer_settings({"training": {"optimizer": "adam"}})


#: Values outside the declared scientific domain of a shared optimizer field.
#:
#: A canonical owner that coerces before validating is not fail-closed: ``nan``
#: passes every ordinary comparison, ``int(2.7)`` silently changes the update
#: geometry the size normalization rests on, Python booleans are integers, and
#: ``bool("false")`` is ``True``.
_INVALID_SHARED_VALUES = [
    # Sign/range violations.
    {"learning_rate": 0.0},
    {"learning_rate": -1.0e-4},
    {"batch_size": 0},
    {"batch_size": -2},
    {"valid_batch_size": 0},
    {"eval_interval": 0},
    {"ema_decay": 1.0},
    {"ema_decay": 0.0},
    {"weight_decay": -1.0},
    {"clip_grad": 0.0},
    # Non-finite reals that survive comparison-only checks.
    {"learning_rate": float("nan")},
    {"learning_rate": float("inf")},
    {"ema_decay": float("nan")},
    {"ema_decay": float("-inf")},
    {"weight_decay": float("nan")},
    {"weight_decay": float("inf")},
    {"clip_grad": float("nan")},
    {"clip_grad": float("inf")},
    # Fractional values that int() would truncate.
    {"batch_size": 2.5},
    {"valid_batch_size": 3.9},
    {"eval_interval": 1.5},
    # Booleans entering integer fields.
    {"batch_size": True},
    {"valid_batch_size": False},
    {"eval_interval": True},
    # Non-booleans entering boolean fields.
    {"ema": "false"},
    {"ema": 0},
    {"ema": 1},
    {"amsgrad": "yes"},
    {"amsgrad": 1},
    # Malformed values that previously escaped as raw conversion errors.
    {"learning_rate": "1e-4"},
    {"batch_size": "4"},
    {"weight_decay": None},
    {"clip_grad": [10.0]},
    {"ema_decay": {"value": 0.99}},
]


@pytest.mark.parametrize(
    "bad", _INVALID_SHARED_VALUES, ids=lambda b: f"{next(iter(b))}={next(iter(b.values()))!r}"
)
def test_b_invalid_shared_values_fail_closed_at_the_canonical_owner(bad: dict):
    """Every rejection is the canonical error type, not a raw coercion error."""

    with pytest.raises(TrainingDataInputError):
        resolve_shared_optimizer_settings({"training": bad})


@pytest.mark.parametrize(
    "bad", _INVALID_SHARED_VALUES, ids=lambda b: f"{next(iter(b))}={next(iter(b.values()))!r}"
)
def test_b_invalid_values_fail_before_identity_or_executable_construction(bad: dict):
    """Failure happens before method identity or any trainer-bound policy."""

    cfg = _config(**bad)
    with pytest.raises(TrainingDataInputError):
        resolve_post_selection_method_identity(cfg)
    with pytest.raises(TrainingDataInputError):
        cli._optimizer_policy(cfg, seed=1, num_workers=0, planned_epochs=3)


def test_b_the_executable_policy_enforces_the_same_domain_directly():
    """Direct or deserialized construction cannot bypass the canonical domain.

    ``MaceOptimizerPolicy`` is independently constructible and independently
    deserialized, so it repeats the domain rather than trusting that every
    caller came through the canonical resolver.
    """

    MaceOptimizerPolicy(device="cpu")  # the accepted default is admissible
    for bad in (
        {"learning_rate": float("nan")},
        {"learning_rate": float("inf")},
        {"ema_decay": float("nan")},
        {"weight_decay": float("inf")},
        {"clip_grad": float("nan")},
        {"batch_size": True},
        {"valid_batch_size": True},
        {"num_workers": True},
        {"eval_interval": True},
        {"ema": 1},
        {"amsgrad": 0},
        {"batch_size": 2.5},
        {"learning_rate": "1e-4"},
    ):
        with pytest.raises(TrainingDataInputError):
            MaceOptimizerPolicy(device="cpu", **bad)


def test_a_unsupported_learned_model_dtype_fails_closed():
    with pytest.raises(CampaignCliError):
        resolve_binary_model_dtype({"training": {"dtype": "bfloat16"}})


# ---------------------------------------------------------------------------
# B. Common-preparation narrowing
# ---------------------------------------------------------------------------


def test_b_batch_and_dtype_are_not_common_preparation_identity():
    """An execution-only edit must not retire prepared P1/P2/common science."""

    from mdstats.training_data.campaign_prepared_generation import (
        preparation_configuration_identity,
    )

    payload = TargetSizeCommonTrainingPolicy()._payload()
    assert "batch_size" not in payload
    assert "default_dtype" not in payload

    baseline = _config()
    for mutation in (
        {"batch_size": 16},
        {"dtype": "float64"},
        {"num_workers": 9},
        {"valid_batch_size": 7},
        {"eval_interval": 4},
    ):
        cfg = _config(**mutation)
        if "dtype" in mutation:
            cfg["campaign"]["precision_profile"] = "double"
        assert (
            resolve_target_size_common_training_policy(cfg).content_digest
            == resolve_target_size_common_training_policy(baseline).content_digest
        ), mutation
        assert (
            preparation_configuration_identity(cfg)["common_training_policy_digest"]
            == preparation_configuration_identity(baseline)[
                "common_training_policy_digest"
            ]
        ), mutation


def test_b_genuine_common_fit_inputs_still_invalidate_common_preparation():
    baseline = resolve_target_size_common_training_policy(_config()).content_digest
    for cfg in (
        {**_config(), "objective": {"forces_weight": 25.0}},
        {**_config(), "weighting": {"degraded_frame_multiplier": 0.25}},
        {**_config(), "atomic_references": {"ridge_lambda": 0.5}},
        _config(harness_validation_frame_count=6),
    ):
        assert (
            resolve_target_size_common_training_policy(cfg).content_digest != baseline
        ), cfg


# ---------------------------------------------------------------------------
# C. Target-size role projection
# ---------------------------------------------------------------------------


def _template(cfg):
    return cli._optimizer_policy(cfg, seed=1, num_workers=0, planned_epochs=10)


def test_c_execution_only_configuration_is_absent_from_screen_identity():
    """General LR/EMA, workers, valid-batch, and eval interval are not the screen."""

    baseline = seed_neutral_optimizer_policy_digest(_template(_config()))
    for mutation in (
        {"learning_rate": 9.0e-3},
        {"ema_decay": 0.9},
        {"num_workers": 12},
        {"valid_batch_size": 9},
        {"eval_interval": 6},
    ):
        assert (
            seed_neutral_optimizer_policy_digest(_template(_config(**mutation)))
            == baseline
        ), mutation


def test_c_scientific_configuration_still_moves_screen_identity():
    baseline = seed_neutral_optimizer_policy_digest(_template(_config()))
    for mutation in (
        {"batch_size": 8},
        {"ema": False},
        {"amsgrad": False},
        {"weight_decay": 2.0e-5},
        {"clip_grad": 5.0},
        {"device": "cuda"},
    ):
        assert (
            seed_neutral_optimizer_policy_digest(_template(_config(**mutation)))
            != baseline
        ), mutation
    double = _config(dtype="float64")
    double["campaign"]["precision_profile"] = "double"
    assert seed_neutral_optimizer_policy_digest(_template(double)) != baseline


def test_c_seed_neutral_projection_excludes_exactly_the_declared_fields():
    """The projection payload is a structural contract, not an accident."""

    from mdstats.training_data.target_size_execution.context import (
        _SEED_NEUTRAL_EXCLUDED_FIELDS,
    )

    assert set(_SEED_NEUTRAL_EXCLUDED_FIELDS) == {
        "seed",
        "acceleration_realization_digest",
        "resolved_acceleration_kernel_mode",
        "learning_rate",
        "ema_decay",
        "num_workers",
        "valid_batch_size",
        "eval_interval",
    }
    policy = MaceOptimizerPolicy(device="cpu")
    payload = dict(policy._payload())
    retained = set(payload) - set(_SEED_NEUTRAL_EXCLUDED_FIELDS) - {"schema"}
    assert retained == {
        "batch_size",
        "max_num_epochs",
        "ema",
        "amsgrad",
        "weight_decay",
        "clip_grad",
        "default_dtype",
        "device",
        "critical_precision_policy",
        "acceleration_policy",
    }


def test_c_target_size_horizon_comes_from_the_screen_schedule():
    """``n3`` is screen policy, not ``[training].max_num_epochs``."""

    cfg = _config(max_num_epochs=97)
    template = cli._optimizer_policy(cfg, seed=1, num_workers=0, planned_epochs=10)
    assert template.max_num_epochs == 10
    assert seed_neutral_optimizer_policy_digest(template) != (
        seed_neutral_optimizer_policy_digest(
            cli._optimizer_policy(cfg, seed=1, num_workers=0, planned_epochs=11)
        )
    )


# ---------------------------------------------------------------------------
# E. P5 method/execution identity cutover
# ---------------------------------------------------------------------------


def test_e_method_recipe_version_is_the_corrected_generation():
    identity = resolve_post_selection_method_identity(_config())
    assert identity.method_recipe_version == "mdstats.post-selection-method.2026-09.v3"


def test_e_old_method_recipe_evidence_cannot_authorize_corrected_runs():
    """Historical identity is not reinterpreted under corrected semantics."""

    current = resolve_post_selection_method_identity(_config())
    historical = replace(
        current, method_recipe_version="mdstats.post-selection-method.2026-08.v1"
    )
    assert historical.content_digest != current.content_digest


def test_e_cv_and_final_role_budgets_stay_independent_of_shared_settings():
    from mdstats.training_data.post_selection_identity import (
        resolve_cv_validation_policy_identity,
    )

    baseline_cv = resolve_cv_validation_policy_identity(_config()).content_digest
    for field, value in _DISTINCT.items():
        assert (
            resolve_cv_validation_policy_identity(
                _config(**{field: value})
            ).content_digest
            == baseline_cv
        ), field


def test_e_there_is_exactly_one_shared_optimizer_resolver():
    """No second, independently defaulted route survives the consolidation."""

    from mdstats.training_data import post_selection_identity as psi
    from mdstats.training_data import training_settings as ts

    assert psi.resolve_shared_optimizer_settings is ts.resolve_shared_optimizer_settings
    assert cli.resolve_shared_optimizer_settings is ts.resolve_shared_optimizer_settings
    assert cli._binary_model_precision_contract is (
        ts.resolve_binary_model_precision_contract
    )
    assert cli.CampaignCliError is ts.CampaignCliError


def test_e_no_module_resolves_shared_optimizer_configuration_a_second_time():
    """Structural guardrail against reintroducing a competing resolution.

    Duplicated *hashing* of a canonically resolved value is allowed; duplicated
    independent *resolution* is what let identity and execution drift apart.
    This scan therefore looks for a direct configuration read of a shared
    optimizer key anywhere in ``mdstats`` outside the canonical owner.

    Scope and limits: it scans every ``.py`` file under the installed
    ``mdstats`` package for ``<expr>.get("<key>", ...)`` and
    ``_cfg(<cfg>, "training", "<key>", ...)`` call sites.  It cannot see a read
    spelled through a computed key or a dynamic lookup, so it complements -
    rather than replaces - the parity assertions above.  The known-positive
    control is the canonical owner itself, which must still contain one read per
    shared field.
    """

    import ast
    from pathlib import Path

    import mdstats as _mdstats
    from mdstats.training_data import training_settings as ts

    shared_keys = set(_EXECUTABLE_DEFAULTS)
    canonical = Path(ts.__file__).resolve()
    root = Path(_mdstats.__file__).resolve().parent

    def _direct_reads(tree: ast.AST) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value in shared_keys
                # A deserialization read of a persisted payload is not a
                # configuration resolution.
                and not _is_payload_read(func.value)
            ):
                found.add(node.args[0].value)
            if (
                isinstance(func, ast.Name)
                and func.id == "_cfg"
                and len(node.args) >= 3
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == "training"
                and isinstance(node.args[2], ast.Constant)
                and node.args[2].value in shared_keys
            ):
                found.add(node.args[2].value)
        return found

    def _is_payload_read(value: ast.AST) -> bool:
        return isinstance(value, ast.Name) and value.id in {"payload", "record"}

    offenders: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        resolved = path.resolve()
        if resolved == canonical:
            continue
        reads = _direct_reads(ast.parse(resolved.read_text(encoding="utf-8")))
        if reads:
            offenders[str(resolved.relative_to(root))] = reads
    assert offenders == {}, (
        "these modules resolve shared optimizer configuration independently of "
        f"the canonical owner: {offenders}"
    )

    # Known-positive control: the scan really does detect these reads.
    canonical_reads = _direct_reads(ast.parse(canonical.read_text(encoding="utf-8")))
    assert canonical_reads == shared_keys
