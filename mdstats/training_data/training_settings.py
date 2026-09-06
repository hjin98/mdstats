"""Canonical resolution of the shared campaign training/optimizer semantics.

One campaign configuration describes one training method.  Before this module
existed the same ``[training]`` keys were read independently by the executable
optimizer construction in the campaign CLI and by the P5 method identity, with
different defaults, so a recorded "method identity" could describe a method
that never executed.  Every consumer that claims those semantics now derives
them here, once.

The module is deliberately low level and free of campaign-path/store
dependencies so identity owners, execution owners, and the CLI can all import
it without a cycle.  It owns exactly the shared scientific optimizer semantics
plus the binary learned-model precision contract; optimizer seed, role-specific
epoch budgets, worker counts, target-size normalization references, candidate
``N``, CV fold state, and acceleration realization are owned elsewhere.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._common import TrainingDataInputError


class CampaignCliError(RuntimeError):
    """A concise, user-actionable campaign failure."""


#: The only optimizer family the accepted MACE training method implements.
_SUPPORTED_OPTIMIZER_FAMILIES = {"adam", ""}
_RECOGNIZED_OPTIMIZER_FAMILIES = {"adam", "adamw", "sgd", "amsgrad", ""}

SHARED_OPTIMIZER_SETTINGS_SCHEMA = "mdstats.shared-optimizer-settings.v2"

BINARY_PRECISION_DTYPES = {"single": "float32", "double": "float64"}
RETIRED_PRECISION_PROFILES = {"refine", "mixed"}


def _training_table(config: Mapping[str, Any]) -> Mapping[str, Any]:
    training = config.get("training", {})
    if not isinstance(training, Mapping):
        raise TrainingDataInputError("[training] must be a table.")
    return training


def resolve_shared_optimizer_settings(config: Mapping[str, Any]) -> dict[str, Any]:
    """The one canonical resolution of the shared scientific optimizer semantics.

    These are exactly the optimizer fields a campaign may configure that both
    describe the method and change what training does.  The optimizer *seed*,
    the role-specific epoch *budget*, and worker counts are excluded on
    purpose: seeds are per-run identity, budgets are role-specific policy, and
    worker counts are a resource choice with no scientific meaning.

    Defaults are the values the executable campaign path actually applies.  An
    identity-only default that execution never used is not product truth, so it
    is not preserved here.
    """

    training = _training_table(config)
    if "optimizer" in training:
        opt_raw = str(training.get("optimizer")).strip().lower()
        if opt_raw not in _RECOGNIZED_OPTIMIZER_FAMILIES:
            raise TrainingDataInputError(f"Unsupported [training].optimizer: {opt_raw}")
        if opt_raw not in _SUPPORTED_OPTIMIZER_FAMILIES:
            raise TrainingDataInputError(f"Unsupported [training].optimizer: {opt_raw}")
    settings = {
        "learning_rate": float(training.get("learning_rate", 1.0e-4)),
        "batch_size": int(training.get("batch_size", 2)),
        "valid_batch_size": int(training.get("valid_batch_size", 2)),
        "eval_interval": int(training.get("eval_interval", 1)),
        "ema": bool(training.get("ema", True)),
        "ema_decay": float(training.get("ema_decay", 0.99999)),
        "amsgrad": bool(training.get("amsgrad", True)),
        "weight_decay": float(training.get("weight_decay", 1.0e-6)),
        "clip_grad": float(training.get("clip_grad", 10.0)),
    }
    if settings["learning_rate"] <= 0.0:
        raise TrainingDataInputError("[training].learning_rate must be positive.")
    if settings["batch_size"] <= 0 or settings["valid_batch_size"] <= 0:
        raise TrainingDataInputError(
            "[training].batch_size and [training].valid_batch_size must be positive."
        )
    if settings["eval_interval"] <= 0:
        raise TrainingDataInputError("[training].eval_interval must be positive.")
    if not (0.0 < settings["ema_decay"] < 1.0):
        raise TrainingDataInputError("[training].ema_decay must lie strictly in (0, 1).")
    if settings["weight_decay"] < 0.0:
        raise TrainingDataInputError("[training].weight_decay must be non-negative.")
    if settings["clip_grad"] <= 0.0:
        raise TrainingDataInputError("[training].clip_grad must be positive.")
    return settings


def shared_optimizer_settings_payload(config: Mapping[str, Any]) -> dict[str, Any]:
    """The canonical resolved settings tagged with their identity schema."""

    return {"schema": SHARED_OPTIMIZER_SETTINGS_SCHEMA, **resolve_shared_optimizer_settings(config)}


def _cfg(cfg: Mapping[str, Any], section: str, key: str, default: Any = None) -> Any:
    table = cfg.get(section, {})
    if not isinstance(table, Mapping):
        return default
    return table.get(key, default)


def legacy_precision_schedule_policy(cfg: Mapping[str, Any]) -> Any | None:
    """Deserialize the pre-ADAPT-PREC1 staged schedule without authorizing it.

    Historical schedule records remain readable for status/storage/reporting.  New
    production execution must use :func:`resolve_binary_model_precision_contract`,
    which rejects staged/refine semantics and never returns this policy to
    DATA8/runtime.
    """

    import mdstats

    training = cfg.get("training", {})
    precision = training.get("precision")
    if precision is None:
        return None
    if not isinstance(precision, Mapping):
        raise CampaignCliError("[training.precision] must be a TOML table.")
    stage_payloads = precision.get("stage")
    if not isinstance(stage_payloads, list) or not stage_payloads:
        raise CampaignCliError(
            "[training.precision] requires one or more [[training.precision.stage]] tables."
        )
    try:
        stages = tuple(
            mdstats.PrecisionStage(
                dtype=str(item["dtype"]),
                fraction=float(item["fraction"]),
                learning_rate_scale=float(item.get("learning_rate_scale", 1.0)),
            )
            for item in stage_payloads
        )
        profile = str(_cfg(cfg, "campaign", "precision_profile", "custom")).strip() or "custom"
        policy = mdstats.PrecisionSchedulePolicy(
            requested_profile=profile,
            stages=stages,
            minimum_final_stage_epochs=int(precision.get("minimum_final_stage_epochs", 0)),
            minimum_final_stage_gradient_updates=int(
                precision.get("minimum_final_stage_gradient_updates", 0)
            ),
            preserve_optimizer_state=bool(precision.get("preserve_optimizer_state", True)),
            preserve_scheduler_state=bool(precision.get("preserve_scheduler_state", True)),
            preserve_ema_state=bool(precision.get("preserve_ema_state", True)),
            model_dtype=str(_cfg(cfg, "model", "dtype", training.get("dtype", "float32"))),
            critical_operation_dtype=str(
                precision.get("critical_operation_dtype", "float64")
            ),
            evaluation_dtype=str(_cfg(cfg, "evaluation", "dtype", training.get("dtype", "float32"))),
            verification_dtype=str(_cfg(cfg, "verification", "dtype", training.get("dtype", "float32"))),
            export_dtype=str(cfg.get("export", {}).get("dtype", training.get("dtype", "float32"))),
        )
    except Exception as exc:
        raise CampaignCliError(f"Invalid historical staged precision configuration: {exc}") from exc
    training_dtype = str(training.get("dtype", stages[0].dtype))
    if training_dtype != stages[0].dtype:
        raise CampaignCliError(
            "[training].dtype must equal the first historical [[training.precision.stage]].dtype."
        )
    mode = str(precision.get("mode", policy.mode))
    if mode != policy.mode:
        raise CampaignCliError(
            f"[training.precision].mode={mode!r} disagrees with the historical stage count; "
            f"expected {policy.mode!r}."
        )
    return policy


def resolve_binary_model_precision_contract(
    cfg: Mapping[str, Any],
    *,
    allow_historical_refine: bool = False,
) -> dict[str, Any]:
    """Resolve the ADAPT-PREC1 learned-model dtype and validate all inference surfaces.

    The precision mode controls only learned-model arithmetic.  mdstats-owned critical
    reductions/statistics/MD bookkeeping remain FP64 and are not a user-selectable mode.

    This is the single learned-model precision authority: executable optimizer
    construction, target-size screen identity, and P5 method identity all read
    the dtype from here rather than defaulting it independently.
    """

    campaign = cfg.get("campaign", {})
    training = cfg.get("training", {})
    model = cfg.get("model", {})
    requested = campaign.get("precision_profile")
    requested_text = "" if requested is None else str(requested).strip().lower()

    historical = legacy_precision_schedule_policy(cfg)
    if requested_text in RETIRED_PRECISION_PROFILES or (
        historical is not None and len(historical.stages) > 1
    ):
        if allow_historical_refine:
            if historical is None:
                raise CampaignCliError(
                    "Historical staged precision evidence is incomplete: the configuration names "
                    f"{requested_text!r} but contains no explicit schedule."
                )
            return {
                "requested_profile": historical.requested_profile,
                "model_dtype": historical.model_dtype,
                "historical_schedule": historical,
                "historical_read_only": True,
            }
        raise CampaignCliError(
            "The staged `refine`/`mixed` precision mode is retired for production campaigns. "
            "Choose `single` (FP32 learned model) or `double` (FP64 learned model). "
            "Historical staged evidence remains readable through status/storage/reporting, "
            "but cannot be resumed or silently reinterpreted under the binary precision contract."
        )

    # Pre-PREC/one-stage configurations are scientifically equivalent when every
    # learned-model inference surface already agrees on one dtype.  Infer the binary
    # label only when the profile is absent/legacy; explicit unknown profile names fail.
    if requested_text in BINARY_PRECISION_DTYPES:
        profile = requested_text
        expected_dtype = BINARY_PRECISION_DTYPES[profile]
        source = "explicit"
    elif requested_text in {"", "legacy", "legacy_custom", "custom"}:
        inferred_dtype = str(training.get("dtype", model.get("dtype", "float32")))
        if inferred_dtype not in {"float32", "float64"}:
            raise CampaignCliError(f"Unsupported learned-model dtype {inferred_dtype!r}.")
        profile = "single" if inferred_dtype == "float32" else "double"
        expected_dtype = inferred_dtype
        source = "legacy_inferred"
    else:
        raise CampaignCliError(
            f"Unsupported precision profile {requested_text!r}. New campaigns support only "
            "`single` and `double`."
        )

    observed = {
        "[model].dtype": str(model.get("dtype", expected_dtype)),
        "[training].dtype": str(training.get("dtype", expected_dtype)),
        "[evaluation].dtype": str(cfg.get("evaluation", {}).get("dtype", expected_dtype)),
        "[verification].dtype": str(cfg.get("verification", {}).get("dtype", expected_dtype)),
        "[export].dtype": str(cfg.get("export", {}).get("dtype", expected_dtype)),
    }
    mismatches = [f"{name}={value!r}" for name, value in observed.items() if value != expected_dtype]
    if mismatches:
        raise CampaignCliError(
            f"Precision profile `{profile}` requires learned-model dtype {expected_dtype} for "
            "training and every model-inference/export surface; mismatches: " + ", ".join(mismatches)
        )

    # Old single/double TOMLs may still contain a one-stage [training.precision]
    # table. Validate it, but deliberately do not return it to DATA8/runtime; this
    # makes staged transition machinery unreachable from the binary production path.
    if historical is not None:
        if len(historical.stages) != 1:
            raise CampaignCliError("Binary precision cannot carry a staged training schedule.")
        stage = historical.stages[0]
        if stage.dtype != expected_dtype or abs(stage.fraction - 1.0) > 1.0e-12:
            raise CampaignCliError(
                "Historical one-stage precision metadata disagrees with the binary model dtype."
            )
        if abs(stage.learning_rate_scale - 1.0) > 1.0e-12:
            raise CampaignCliError(
                "Binary precision does not support a precision-stage learning-rate scale."
            )

    return {
        "requested_profile": profile,
        "model_dtype": expected_dtype,
        "source": source,
        "historical_schedule": historical,
        "historical_read_only": False,
    }


def resolve_binary_model_dtype(cfg: Mapping[str, Any]) -> str:
    """The canonical learned-model dtype for this campaign configuration."""

    return str(resolve_binary_model_precision_contract(cfg)["model_dtype"])


__all__ = [
    "BINARY_PRECISION_DTYPES",
    "CampaignCliError",
    "RETIRED_PRECISION_PROFILES",
    "SHARED_OPTIMIZER_SETTINGS_SCHEMA",
    "legacy_precision_schedule_policy",
    "resolve_binary_model_dtype",
    "resolve_binary_model_precision_contract",
    "resolve_shared_optimizer_settings",
    "shared_optimizer_settings_payload",
]
