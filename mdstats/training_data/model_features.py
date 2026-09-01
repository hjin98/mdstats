"""Optional checkpoint-bound MACE descriptors and model predictions for DATA6.

MACE is imported lazily. The public records remain usable without PyTorch or
MACE installed. Descriptor semantics follow the MACE calculator descriptor API
(atomic rows; invariant-only output by default).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from functools import lru_cache
from importlib import metadata as importlib_metadata
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event, Lock, RLock, Thread
import weakref
import hashlib
import io
import gc
import math
import time
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

import numpy as np

from ._npz_mmap import load_npz_members_mmap
from ase.data import chemical_symbols

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import ase_atoms_for_frame, build_frame_array_index
from .mace_compatibility import mace_runtime_warning_handled
from .critical_precision import (
    MaceCriticalPrecisionPolicy,
    activate_mace_critical_precision_policy,
)

MODEL_CHECKPOINT_IDENTITY_SCHEMA = "mdstats.model-checkpoint-identity.v2"
MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA = "mdstats.model-checkpoint-identity.v1"
MACE_DESCRIPTOR_POLICY_SCHEMA = "mdstats.mace-descriptor-policy.v1"
MACE_DESCRIPTOR_FILE_RECORD_SCHEMA = "mdstats.mace-descriptor-file-record.v2"
MACE_DESCRIPTOR_FILE_RECORD_LEGACY_SCHEMA = "mdstats.mace-descriptor-file-record.v1"
MACE_DESCRIPTOR_MANIFEST_SCHEMA = "mdstats.mace-descriptor-manifest.v2"
MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA = "mdstats.mace-descriptor-manifest.v1"
MACE_DESCRIPTOR_SIGNATURE_SCHEMA = "mdstats.mace-descriptor-signature.v1"
MACE_BATCH_CAPACITY_CALIBRATION_SCHEMA = "mdstats.mace-batch-capacity-calibration.v2"
MACE_BATCH_CAPACITY_CALIBRATION_V1_SCHEMA = "mdstats.mace-batch-capacity-calibration.v1"
MACE_BATCH_CAPACITY_PROBE_SCHEMA = "mdstats.mace-batch-capacity-probe.v1"
MODEL_PREDICTION_SUMMARY_SCHEMA = "mdstats.model-prediction-summary.v1"
MACE_DESCRIPTOR_POLICY_VERSION = "mdstats.mlff-data6.mace-descriptor.2026-08.v2"
MACE_ADAPTER_VERSION = "mdstats.mlff-data6.mace-calculator.2026-08.v2"
MACE_MONITOR_GRAPH_CACHE_SCHEMA = "mdstats.mace-monitor-graph-cache.v1"
MACE_MONITOR_GRAPH_POLICY_VERSION = "mdstats.mlff-opt-eval3.graph.2026-08.v1"
# G6/G7 requalification amendment (R17A): one canonical, versioned execution-
# architecture authority.  Bumping any of these schema strings deliberately
# invalidates every persisted digest/profile/graph-policy identity that was
# computed under the prior (weaker) definition.
MACE_MODEL_EXECUTION_ARCHITECTURE_SCHEMA = "mdstats.mace-model-execution-architecture.v1"
MACE_PROVIDER_SHELL_EXECUTION_POLICY_SCHEMA = "mdstats.mace-provider-shell-execution-policy.v1"
MACE_RUNTIME_ARCHITECTURE_SCHEMA = "mdstats.mace-runtime-architecture.v2"
MACE_CANDIDATE_ARCHITECTURE_SCHEMA = "mdstats.target-size.mace-architecture.v1"
STATIC_INFERENCE_RUNTIME_PROFILE_SCHEMA = "mdstats.static-inference-runtime-profile.v6"
STATIC_INFERENCE_EVIDENCE_SEMANTICS = (
    "persistent-provider-required-residency-plus-2d-failure-learning.v6"
)


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _array_content_digest(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    hasher = hashlib.sha256()
    hasher.update(b"mdstats.array.v1\0")
    hasher.update(values.dtype.str.encode("ascii"))
    hasher.update(b"\0")
    hasher.update(repr(tuple(int(v) for v in values.shape)).encode("ascii"))
    hasher.update(b"\0")
    hasher.update(memoryview(values).cast("B"))
    return hasher.hexdigest()


_MACE_GRAPH_BATCH_CACHE: "OrderedDict[tuple[Any, ...], tuple[tuple[weakref.ReferenceType[Any], ...], Any, np.ndarray, int]]" = OrderedDict()
_MACE_GRAPH_BATCH_CACHE_BYTES = 0
_MACE_GRAPH_BATCH_CACHE_LOCK = RLock()
# MACE 0.3.x accelerator conversion (CuEq/OEq/hybrid) uses PyTorch FX tracing.
# FX installs process-global tracing hooks/flags, so two conversions in sibling
# threads can cross-observe modules from different model trees and raise
# ``NameError: module is not installed as a submodule``.  Keep model I/O and
# CUDA inference parallel, but serialize only the third-party graph-rewrite
# functions themselves.
_MACE_ACCELERATOR_CONVERSION_LOCK = RLock()
_MACE_ACCELERATOR_PATCH_LOCK = RLock()


def _install_thread_safe_mace_accelerator_conversion(mace_calculator_module: Any) -> None:
    """Serialize MACE accelerator graph rewrites without serializing model loading.

    MACECalculator resolves ``run_e3nn_to_*`` from ``mace.calculators.mace`` at
    call time.  Wrapping those conversion functions once lets independent
    calculators load checkpoints and move tensors concurrently while preventing
    overlapping PyTorch-FX graph rewrites, whose tracing state is process-global.
    """

    with _MACE_ACCELERATOR_PATCH_LOCK:
        for name in ("run_e3nn_to_cueq", "run_e3nn_to_oeq", "run_e3nn_to_hybrid"):
            original = getattr(mace_calculator_module, name, None)
            if original is None or bool(getattr(original, "_mdstats_fx_serialized", False)):
                continue

            def locked_conversion(*args: Any, _original: Any = original, **kwargs: Any) -> Any:
                with _MACE_ACCELERATOR_CONVERSION_LOCK:
                    return _original(*args, **kwargs)

            locked_conversion.__name__ = getattr(original, "__name__", name)
            locked_conversion.__doc__ = getattr(original, "__doc__", None)
            locked_conversion._mdstats_fx_serialized = True  # type: ignore[attr-defined]
            locked_conversion._mdstats_original = original  # type: ignore[attr-defined]
            setattr(mace_calculator_module, name, locked_conversion)

_MACE_GRAPH_BATCH_CACHE_MAX_BYTES = max(
    0, int(os.environ.get("MDSTATS_MACE_GRAPH_CACHE_BYTES", str(512 * 1024**2)))
)


def _graph_tensor_bytes(value: Any) -> int:
    total = 0
    try:
        for key in value.keys:
            item = value[key]
            if hasattr(item, "numel") and hasattr(item, "element_size"):
                total += int(item.numel()) * int(item.element_size())
    except Exception:
        return 0
    return max(total, 1)


# --- R17A canonical execution-architecture identity --------------------
#
# One canonical authority determines both hot-swap eligibility and every
# downstream compatibility projection (runtime-architecture digest,
# calibration-profile identity, graph-policy identity).  It is layered:
#
#   1. model execution architecture (`_mace_model_execution_architecture_descriptor`)
#      -- scientific/forward-pass structure independent of learned weights;
#   2. provider/shell execution policy (`_mace_provider_shell_execution_policy_descriptor`)
#      -- calculator/runtime settings that can alter the executable shell.
#
# Buffers registered on a real MACE ``torch.nn.Module`` are the model's own
# non-learned, architecture-derived tensors (cutoff radius, atomic-number
# table/order, radial-basis and cutoff-function construction, symmetric-
# contraction matrices, structural masks) and are therefore bound by VALUE.
# ``torch.nn.Parameter`` tensors are the excluded learned weights and are
# bound only by structure (name/shape/dtype) so genuinely same-architecture
# checkpoints with different weights remain hot-swap eligible.  A small,
# explicit set of MACE blocks stores dataset/training calibration constants
# (E0 atomic-energy references, energy scale/shift) as buffers rather than
# parameters purely because they are not updated by backprop; those buffers
# are checkpoint-specific like weights and are therefore also excluded from
# value comparison, bound only by structure.
_MACE_CALIBRATION_BUFFER_BLOCK_TYPES = frozenset(
    {
        "mace.modules.blocks.AtomicEnergiesBlock",
        "mace.modules.blocks.ScaleShiftBlock",
    }
)


def _mace_buffer_value_digest(tensor: Any) -> str:
    array = (
        tensor.detach().contiguous().cpu().numpy()
        if hasattr(tensor, "detach")
        else np.asarray(tensor)
    )
    return _array_content_digest(np.ascontiguousarray(array))


def _mace_model_execution_architecture_descriptor(model: Any) -> dict[str, Any]:
    """Canonical, weight-independent execution-architecture descriptor.

    Binds every property capable of changing forward computation, graph
    construction, or retained-shell execution semantics -- exact model class,
    cutoff/neighbor-radius semantics, species/atomic-number table and order,
    head structure, radial-basis/embedding and cutoff-function construction,
    interaction-block architecture/count, product/correlation architecture,
    readout structure, and precision/dtype -- while deliberately excluding
    learned parameter values (and checkpoint-specific calibration buffer
    values) so same-architecture checkpoints with different weights remain
    hot-swap eligible.  Unknown/unsupported model objects fail closed rather
    than silently reporting an empty descriptor.
    """

    if not hasattr(model, "named_parameters") or not hasattr(model, "named_modules"):
        raise TrainingDataInputError(
            "MACE execution architecture identity requires a torch model."
        )
    parameters = [
        {
            "name": str(name),
            "shape": [int(value) for value in tensor.shape],
            "dtype": str(tensor.dtype),
        }
        for name, tensor in sorted(model.named_parameters(), key=lambda item: item[0])
    ]
    buffers: list[dict[str, Any]] = []
    for module_name, submodule in sorted(model.named_modules(), key=lambda item: item[0]):
        owner_type = f"{type(submodule).__module__}.{type(submodule).__qualname__}"
        value_excluded = owner_type in _MACE_CALIBRATION_BUFFER_BLOCK_TYPES
        for leaf_name, tensor in submodule.named_buffers(recurse=False):
            full_name = f"{module_name}.{leaf_name}" if module_name else str(leaf_name)
            entry: dict[str, Any] = {
                "name": full_name,
                "shape": [int(value) for value in tensor.shape],
                "dtype": str(tensor.dtype),
            }
            if not value_excluded:
                entry["value"] = _mace_buffer_value_digest(tensor)
            buffers.append(entry)
    buffers.sort(key=lambda item: item["name"])
    modules_census = [
        (str(name), f"{type(submodule).__module__}.{type(submodule).__qualname__}")
        for name, submodule in sorted(model.named_modules(), key=lambda item: item[0])
    ]
    interaction_avg_num_neighbors = [
        float(getattr(interaction, "avg_num_neighbors", float("nan")))
        for interaction in getattr(model, "interactions", ())
    ]
    heads = [str(value) for value in getattr(model, "heads", ())]
    primary_dtype = ""
    for _, tensor in model.named_parameters():
        primary_dtype = str(tensor.dtype)
        break
    return {
        "schema": MACE_MODEL_EXECUTION_ARCHITECTURE_SCHEMA,
        "model_class": f"{type(model).__module__}.{type(model).__qualname__}",
        "primary_dtype": primary_dtype,
        "heads": heads,
        "interaction_avg_num_neighbors": interaction_avg_num_neighbors,
        "modules": modules_census,
        "parameters": parameters,
        "buffers": buffers,
    }


def mace_model_execution_architecture_digest(model: Any) -> str:
    """Return the shared weight-independent identity of one MACE model.

    TRAIN2 persists this model-only identity alongside its continuation state.
    The provider uses the same descriptor after reconstructing the model from
    candidate configuration, so a configuration change such as ``r_max`` is
    rejected before checkpoint state can reach inference.
    """

    return digest(_mace_model_execution_architecture_descriptor(model))


def _mace_candidate_architecture_from_args(args: Any) -> dict[str, Any]:
    """Project the pinned MACE parser namespace into JSON-safe architecture data."""

    interaction_first = str(getattr(args, "interaction_first", ""))
    # MACE 0.3.16's ``_build_model`` normalizes the residual default for the
    # first block when the model family is ``MACE``.  Persist the realized
    # value, not the parser spelling that would be silently rewritten.
    if interaction_first not in {
        "RealAgnosticInteractionBlock",
        "RealAgnosticDensityInteractionBlock",
    }:
        interaction_first = "RealAgnosticInteractionBlock"
    radial_mlp = getattr(args, "radial_MLP", "[64, 64, 64]")
    if isinstance(radial_mlp, str):
        import ast

        try:
            radial_mlp = ast.literal_eval(radial_mlp)
        except (SyntaxError, ValueError) as exc:
            raise TrainingDataInputError(
                "MACE candidate architecture radial_MLP is not a literal sequence."
            ) from exc
    return {
        "schema": MACE_CANDIDATE_ARCHITECTURE_SCHEMA,
        "model": str(getattr(args, "model", "MACE")),
        "r_max": float(getattr(args, "r_max", 5.0)),
        "num_radial_basis": int(getattr(args, "num_radial_basis", 8)),
        "num_cutoff_basis": int(getattr(args, "num_cutoff_basis", 5)),
        "max_ell": int(getattr(args, "max_ell", 3)),
        "interaction": str(
            getattr(args, "interaction", "RealAgnosticResidualInteractionBlock")
        ),
        "interaction_first": interaction_first,
        "num_interactions": int(getattr(args, "num_interactions", 2)),
        "hidden_irreps": str(getattr(args, "hidden_irreps", "")),
        "edge_irreps": (
            None
            if getattr(args, "edge_irreps", None) is None
            else str(getattr(args, "edge_irreps"))
        ),
        "num_channels": (
            None
            if getattr(args, "num_channels", None) is None
            else int(getattr(args, "num_channels"))
        ),
        "max_L": (
            None
            if getattr(args, "max_L", None) is None
            else int(getattr(args, "max_L"))
        ),
        "MLP_irreps": str(getattr(args, "MLP_irreps", "16x0e")),
        "radial_MLP": [int(value) for value in radial_mlp],
        "radial_type": str(getattr(args, "radial_type", "bessel")),
        "pair_repulsion": bool(getattr(args, "pair_repulsion", False)),
        "distance_transform": (
            None
            if getattr(args, "distance_transform", None) in (None, "None")
            else str(getattr(args, "distance_transform"))
        ),
        "apply_cutoff": bool(getattr(args, "apply_cutoff", True)),
        "correlation": int(getattr(args, "correlation", 3)),
        "gate": str(getattr(args, "gate", "silu")),
        "use_reduced_cg": bool(getattr(args, "use_reduced_cg", False)),
        "use_so3": bool(getattr(args, "use_so3", False)),
        "use_edge_irreps_first": bool(
            getattr(args, "use_edge_irreps_first", False)
        ),
        "use_agnostic_product": bool(
            getattr(args, "use_agnostic_product", False)
        ),
        "use_embedding_readout": bool(
            getattr(args, "use_embedding_readout", False)
        ),
        "use_last_readout_only": bool(
            getattr(args, "use_last_readout_only", False)
        ),
        "embedding_specs": getattr(args, "embedding_specs", None),
        "avg_num_neighbors": float(getattr(args, "avg_num_neighbors", 1.0)),
        # ``no_scaling`` makes construction independent of a data loader while
        # keeping the scale/shift an explicit part of the accepted config.
        "scaling": "no_scaling",
        "mean": 0.0,
        "std": 1.0,
        "loss": "universal",
        "heads": ["target_head"],
    }


def _validate_mace_candidate_architecture(
    value: Mapping[str, Any],
) -> dict[str, Any]:
    """Canonicalize candidate architecture without creating a model."""

    if value.get("schema") != MACE_CANDIDATE_ARCHITECTURE_SCHEMA:
        raise TrainingDataSerializationError(
            "Unsupported target-size MACE architecture schema."
        )
    required = {
        "schema",
        "model",
        "r_max",
        "num_radial_basis",
        "num_cutoff_basis",
        "max_ell",
        "interaction",
        "interaction_first",
        "num_interactions",
        "hidden_irreps",
        "edge_irreps",
        "num_channels",
        "max_L",
        "MLP_irreps",
        "radial_MLP",
        "radial_type",
        "pair_repulsion",
        "distance_transform",
        "apply_cutoff",
        "correlation",
        "gate",
        "use_reduced_cg",
        "use_so3",
        "use_edge_irreps_first",
        "use_agnostic_product",
        "use_embedding_readout",
        "use_last_readout_only",
        "embedding_specs",
        "avg_num_neighbors",
        "scaling",
        "mean",
        "std",
        "loss",
        "heads",
    }
    if set(value) != required:
        missing = sorted(required.difference(value))
        extra = sorted(set(value).difference(required))
        raise TrainingDataInputError(
            "Target-size MACE architecture keys are not exact; "
            f"missing={missing}, extra={extra}."
        )
    if str(value["model"]) != "MACE":
        raise TrainingDataInputError(
            "Target-size P3 reconstruction accepts only the pinned MACE model family."
        )
    try:
        r_max = float(value["r_max"])
        avg_num_neighbors = float(value["avg_num_neighbors"])
        mean = float(value["mean"])
        std = float(value["std"])
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "Target-size MACE architecture contains a non-numeric scalar."
        ) from exc
    if not math.isfinite(r_max) or r_max <= 0.0:
        raise TrainingDataInputError("Target-size MACE architecture r_max must be positive and finite.")
    if not math.isfinite(avg_num_neighbors) or avg_num_neighbors <= 0.0:
        raise TrainingDataInputError(
            "Target-size MACE architecture avg_num_neighbors must be positive and finite."
        )
    if not math.isfinite(mean) or not math.isfinite(std) or std <= 0.0:
        raise TrainingDataInputError(
            "Target-size MACE architecture mean/std must be finite with std > 0."
        )
    integer_fields = (
        "num_radial_basis",
        "num_cutoff_basis",
        "max_ell",
        "num_interactions",
        "correlation",
    )
    integers: dict[str, int] = {}
    for name in integer_fields:
        raw = value[name]
        lower_bound = 0 if name == "max_ell" else 1
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < lower_bound:
            raise TrainingDataInputError(
                f"Target-size MACE architecture {name} must be a non-negative integer."
                if name == "max_ell"
                else f"Target-size MACE architecture {name} must be a positive integer."
            )
        integers[name] = int(raw)
    hidden_irreps = str(value["hidden_irreps"]).strip()
    mlp_irreps = str(value["MLP_irreps"]).strip()
    if not hidden_irreps or not mlp_irreps:
        raise TrainingDataInputError(
            "Target-size MACE architecture requires hidden_irreps and MLP_irreps."
        )
    radial_mlp = value["radial_MLP"]
    if not isinstance(radial_mlp, (list, tuple)) or not radial_mlp:
        raise TrainingDataInputError("Target-size MACE architecture radial_MLP is invalid.")
    radial_mlp_values: list[int] = []
    for item in radial_mlp:
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
            raise TrainingDataInputError(
                "Target-size MACE architecture radial_MLP values must be positive integers."
            )
        radial_mlp_values.append(int(item))
    heads = value["heads"]
    if not isinstance(heads, (list, tuple)) or tuple(str(item) for item in heads) != (
        "target_head",
    ):
        raise TrainingDataInputError(
            "Target-size P3 MACE reconstruction requires exactly the target_head head."
        )
    boolean_fields = (
        "pair_repulsion",
        "apply_cutoff",
        "use_reduced_cg",
        "use_so3",
        "use_edge_irreps_first",
        "use_agnostic_product",
        "use_embedding_readout",
        "use_last_readout_only",
    )
    for name in boolean_fields:
        if not isinstance(value[name], bool):
            raise TrainingDataInputError(
                f"Target-size MACE architecture {name} must be boolean."
            )
    if str(value["scaling"]) != "no_scaling" or str(value["loss"]) != "universal":
        raise TrainingDataInputError(
            "Target-size MACE architecture must use the accepted no_scaling/universal realization."
        )
    interaction_first = str(value["interaction_first"])
    if interaction_first not in {
        "RealAgnosticInteractionBlock",
        "RealAgnosticDensityInteractionBlock",
    }:
        raise TrainingDataInputError(
            "Target-size MACE architecture interaction_first is not realizable by MACE 0.3.16."
        )
    distance_transform = value["distance_transform"]
    if distance_transform not in (None, "Agnesi", "Soft"):
        raise TrainingDataInputError(
            "Target-size MACE architecture distance_transform is unsupported."
        )
    edge_irreps = value["edge_irreps"]
    if edge_irreps is not None and not str(edge_irreps).strip():
        edge_irreps = None
    num_channels = value["num_channels"]
    max_l = value["max_L"]
    if num_channels is not None and (
        isinstance(num_channels, bool) or not isinstance(num_channels, int) or num_channels <= 0
    ):
        raise TrainingDataInputError("Target-size MACE architecture num_channels is invalid.")
    if max_l is not None and (
        isinstance(max_l, bool) or not isinstance(max_l, int) or max_l < 0
    ):
        raise TrainingDataInputError("Target-size MACE architecture max_L is invalid.")
    result = {
        "schema": MACE_CANDIDATE_ARCHITECTURE_SCHEMA,
        "model": "MACE",
        "r_max": r_max,
        **integers,
        "interaction": str(value["interaction"]),
        "interaction_first": interaction_first,
        "hidden_irreps": hidden_irreps,
        "edge_irreps": None if edge_irreps is None else str(edge_irreps),
        "num_channels": None if num_channels is None else int(num_channels),
        "max_L": None if max_l is None else int(max_l),
        "MLP_irreps": mlp_irreps,
        "radial_MLP": radial_mlp_values,
        "radial_type": str(value["radial_type"]),
        "pair_repulsion": bool(value["pair_repulsion"]),
        "distance_transform": distance_transform,
        "apply_cutoff": bool(value["apply_cutoff"]),
        "gate": str(value["gate"]),
        "use_reduced_cg": bool(value["use_reduced_cg"]),
        "use_so3": bool(value["use_so3"]),
        "use_edge_irreps_first": bool(value["use_edge_irreps_first"]),
        "use_agnostic_product": bool(value["use_agnostic_product"]),
        "use_embedding_readout": bool(value["use_embedding_readout"]),
        "use_last_readout_only": bool(value["use_last_readout_only"]),
        "embedding_specs": value["embedding_specs"],
        "avg_num_neighbors": avg_num_neighbors,
        "scaling": "no_scaling",
        "mean": mean,
        "std": std,
        "loss": "universal",
        "heads": ["target_head"],
    }
    return result


def mace_candidate_architecture_defaults() -> dict[str, Any]:
    """Return the pinned MACE 0.3.16 candidate architecture defaults.

    The candidate materialization records this projection as its explicit
    configuration authority.  It is derived from the same parser/build owner
    used to instantiate the real model, so the target-size path does not carry
    a second hand-written MACE compatibility definition.
    """

    try:
        from mace.tools import build_default_arg_parser
        from mace.tools.arg_parser_tools import check_args
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "Target-size MACE materialization requires the pinned mace-torch dependency."
        ) from exc
    try:
        args = build_default_arg_parser().parse_args(["--name", "target-size"])
        args, _messages = check_args(args)
        return _validate_mace_candidate_architecture(
            _mace_candidate_architecture_from_args(args)
        )
    except (AssertionError, TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "Pinned MACE parser defaults cannot form a valid target-size architecture."
        ) from exc


def canonicalize_mace_candidate_architecture(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a strict JSON-safe target-size MACE architecture projection."""

    if value is None:
        return mace_candidate_architecture_defaults()
    if not isinstance(value, Mapping):
        raise TrainingDataInputError("Target-size MACE architecture must be a mapping.")
    return _validate_mace_candidate_architecture(value)


def build_mace_model_from_configuration(config_payload: Mapping[str, Any]) -> Any:
    """Construct one real MACE 0.3.16 model from candidate configuration.

    This is the shared construction owner used by target-size EVAL2.  It uses
    MACE's own parser/configuration builder and never consumes a checkpoint
    state dictionary or a continuation companion as an architecture source.
    """

    if not isinstance(config_payload, Mapping):
        raise TrainingDataInputError("MACE model configuration must be a mapping.")
    architecture = canonicalize_mace_candidate_architecture(
        config_payload.get("mace_architecture")
    )
    try:
        atomic_numbers = tuple(
            sorted({int(value) for value in config_payload["atomic_numbers"]})
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "MACE model configuration must provide atomic_numbers."
        ) from exc
    if not atomic_numbers or any(value <= 0 for value in atomic_numbers):
        raise TrainingDataInputError(
            "MACE model configuration atomic_numbers must be positive and non-empty."
        )
    e0_payload = config_payload.get("E0s")
    if not isinstance(e0_payload, Mapping):
        raise TrainingDataInputError("MACE model configuration must provide E0s.")
    try:
        atomic_energies = np.asarray(
            [float(e0_payload[str(z)] if str(z) in e0_payload else e0_payload[z]) for z in atomic_numbers],
            dtype=np.float64,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "MACE model configuration E0s do not cover atomic_numbers."
        ) from exc
    if np.any(~np.isfinite(atomic_energies)):
        raise TrainingDataInputError("MACE model configuration E0s must be finite.")
    device = str(config_payload.get("device", "")).strip()
    default_dtype = str(config_payload.get("default_dtype", "")).strip()
    if device not in {"cpu", "cuda", "mps", "xpu"}:
        raise TrainingDataInputError("MACE model configuration device is unsupported.")
    if default_dtype not in {"float32", "float64"}:
        raise TrainingDataInputError(
            "MACE model configuration default_dtype must be float32 or float64."
        )
    try:
        import torch
        from mace import tools
        from mace.tools.model_script_utils import configure_model
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "Real target-size MACE reconstruction requires mace-torch."
        ) from exc

    try:
        args = tools.build_default_arg_parser().parse_args(
            ["--name", str(config_payload.get("name", "target-size"))]
        )
        args.model = architecture["model"]
        args.device = device
        args.default_dtype = default_dtype
        args.r_max = architecture["r_max"]
        args.num_radial_basis = architecture["num_radial_basis"]
        args.num_cutoff_basis = architecture["num_cutoff_basis"]
        args.max_ell = architecture["max_ell"]
        args.interaction = architecture["interaction"]
        args.interaction_first = architecture["interaction_first"]
        args.num_interactions = architecture["num_interactions"]
        args.hidden_irreps = architecture["hidden_irreps"]
        args.edge_irreps = architecture["edge_irreps"]
        args.num_channels = architecture["num_channels"]
        args.max_L = architecture["max_L"]
        args.MLP_irreps = architecture["MLP_irreps"]
        args.radial_MLP = repr(architecture["radial_MLP"])
        args.radial_type = architecture["radial_type"]
        args.pair_repulsion = architecture["pair_repulsion"]
        args.distance_transform = architecture["distance_transform"]
        args.apply_cutoff = architecture["apply_cutoff"]
        args.correlation = architecture["correlation"]
        args.gate = architecture["gate"]
        args.use_reduced_cg = architecture["use_reduced_cg"]
        args.use_so3 = architecture["use_so3"]
        args.use_edge_irreps_first = architecture["use_edge_irreps_first"]
        args.use_agnostic_product = architecture["use_agnostic_product"]
        args.use_embedding_readout = architecture["use_embedding_readout"]
        args.use_last_readout_only = architecture["use_last_readout_only"]
        args.embedding_specs = architecture["embedding_specs"]
        args.avg_num_neighbors = architecture["avg_num_neighbors"]
        args.scaling = architecture["scaling"]
        args.mean = architecture["mean"]
        args.std = architecture["std"]
        args.loss = architecture["loss"]
        args.heads = list(architecture["heads"])
        args.compute_energy = True
        args.compute_forces = True
        args.compute_dipole = False
        args.compute_polarizability = False
        z_table = tools.AtomicNumberTable(list(atomic_numbers))
        requested_dtype = torch.float32 if default_dtype == "float32" else torch.float64
        previous_dtype = torch.get_default_dtype()
        torch.set_default_dtype(requested_dtype)
        try:
            model, _output_args = configure_model(
                args,
                None,
                atomic_energies,
                model_foundation=None,
                heads=list(architecture["heads"]),
                z_table=z_table,
                head_configs=None,
            )
        finally:
            torch.set_default_dtype(previous_dtype)
        model = model.to(device="cpu", dtype=requested_dtype)
    except (AssertionError, AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise TrainingDataInputError(
            "Candidate MACE configuration could not reconstruct a real MACE model."
        ) from exc
    if not all(
        hasattr(model, name)
        for name in ("r_max", "atomic_numbers", "interactions", "products")
    ):
        raise TrainingDataInputError(
            "Candidate MACE configuration did not produce a deployable MACE architecture."
        )
    return model


def _mace_provider_shell_execution_policy_descriptor(calculator: Any) -> dict[str, Any]:
    """Canonical calculator/runtime shell-policy layer of the execution identity.

    Covers calculator-level settings that can alter the executable shell or
    its graph/compiled behavior without necessarily changing model state:
    compile mode and equivariant-acceleration backend (CuEq/OEq) policy.
    """

    return {
        "schema": MACE_PROVIDER_SHELL_EXECUTION_POLICY_SCHEMA,
        "calculator_class": f"{type(calculator).__module__}.{type(calculator).__qualname__}",
        "model_type": str(getattr(calculator, "model_type", "")),
        "default_dtype": str(getattr(calculator, "default_dtype", "")),
        "use_compile": bool(getattr(calculator, "use_compile", False)),
        "enable_cueq": bool(getattr(calculator, "_enable_cueq", False)),
        "enable_oeq": bool(getattr(calculator, "_enable_oeq", False)),
        "pad_num_atoms": int(getattr(calculator, "pad_num_atoms", 0)),
        "pad_num_edges": int(getattr(calculator, "pad_num_edges", 0)),
        "num_models": int(getattr(calculator, "num_models", 0) or 0),
        "available_heads": [str(value) for value in getattr(calculator, "available_heads", ())],
    }


def _mace_provider_execution_architecture_descriptor(
    calculator: Any, *, model_version: str, adapter_version: str
) -> dict[str, Any]:
    """Composed canonical execution-architecture authority for one provider."""

    models = getattr(calculator, "models", None)
    if not isinstance(models, (tuple, list)) or not models:
        raise TrainingDataInputError(
            "MACE runtime architecture identity requires calculator model state."
        )
    try:
        import torch as _torch_runtime

        torch_version = str(getattr(_torch_runtime, "__version__", ""))
    except ModuleNotFoundError:  # pragma: no cover - provider already requires torch
        torch_version = ""
    return {
        "schema": MACE_RUNTIME_ARCHITECTURE_SCHEMA,
        "adapter_version": str(adapter_version),
        "model_version": str(model_version),
        "torch_version": torch_version,
        "models": [
            _mace_model_execution_architecture_descriptor(model) for model in models
        ],
        "shell_policy": _mace_provider_shell_execution_policy_descriptor(calculator),
    }


def _mace_graph_affecting_model_projection(model: Any) -> tuple[float, tuple[int, ...]]:
    """Cutoff/species projection derived from the canonical architecture authority.

    Graph/neighbor-list construction is governed by the model's own cutoff and
    atomic-number-table buffers -- the same source the canonical descriptor
    reads -- rather than a separately cached calculator attribute that can go
    stale after a checkpoint state replacement.
    """

    r_max_buffer = getattr(model, "r_max", None)
    r_max = (
        float(r_max_buffer.item())
        if hasattr(r_max_buffer, "item")
        else float(r_max_buffer or 0.0)
    )
    atomic_numbers_buffer = getattr(model, "atomic_numbers", None)
    atomic_numbers = (
        tuple(int(value) for value in atomic_numbers_buffer.tolist())
        if hasattr(atomic_numbers_buffer, "tolist")
        else tuple(int(value) for value in (atomic_numbers_buffer or ()))
    )
    return r_max, atomic_numbers


def _mace_graph_policy_key(calc: Any) -> tuple[Any, ...]:
    models = getattr(calc, "models", None)
    primary_model = models[0] if isinstance(models, (tuple, list)) and models else None
    if primary_model is not None:
        r_max, z_values = _mace_graph_affecting_model_projection(primary_model)
    else:
        r_max = float(getattr(calc, "r_max", 0.0))
        z_values = tuple(int(value) for value in getattr(getattr(calc, "z_table", None), "zs", ()))
    return (
        f"{type(calc).__module__}.{type(calc).__qualname__}",
        r_max,
        str(calc.default_dtype),
        str(calc.head),
        z_values,
        tuple(str(value) for value in getattr(calc, "available_heads", ())),
        tuple(sorted((str(key), str(value)) for key, value in getattr(calc, "info_keys", {}).items())),
        tuple(sorted((str(key), str(value)) for key, value in getattr(calc, "arrays_keys", {}).items())),
    )


def _graph_batch_cache_key(calc: Any, atoms_batch: Sequence[Any]) -> tuple[Any, ...]:
    # Cached monitor objects are immutable in the evaluation path. Object identity
    # therefore avoids rescanning all coordinates merely to find an existing graph.
    return (_mace_graph_policy_key(calc), tuple(id(atoms) for atoms in atoms_batch))


def _cached_graph_batch(calc: Any, atoms_batch: Sequence[Any]) -> tuple[Any, np.ndarray] | None:
    key = _graph_batch_cache_key(calc, atoms_batch)
    with _MACE_GRAPH_BATCH_CACHE_LOCK:
        cached = _MACE_GRAPH_BATCH_CACHE.get(key)
        if cached is None:
            return None
        references, batch, counts, _ = cached
        if len(references) != len(atoms_batch) or any(
            reference() is not atoms
            for reference, atoms in zip(references, atoms_batch, strict=True)
        ):
            global _MACE_GRAPH_BATCH_CACHE_BYTES
            _, _, _, removed_bytes = _MACE_GRAPH_BATCH_CACHE.pop(key)
            _MACE_GRAPH_BATCH_CACHE_BYTES -= removed_bytes
            return None
        _MACE_GRAPH_BATCH_CACHE.move_to_end(key)
        return batch.clone().to(calc.device), counts.copy()


def _cached_graph_batch_cpu(calc: Any, atoms_batch: Sequence[Any]) -> tuple[Any, np.ndarray] | None:
    key = _graph_batch_cache_key(calc, atoms_batch)
    with _MACE_GRAPH_BATCH_CACHE_LOCK:
        cached = _MACE_GRAPH_BATCH_CACHE.get(key)
        if cached is None:
            return None
        references, batch, counts, _ = cached
        if len(references) != len(atoms_batch) or any(
            reference() is not atoms
            for reference, atoms in zip(references, atoms_batch, strict=True)
        ):
            global _MACE_GRAPH_BATCH_CACHE_BYTES
            _, _, _, removed_bytes = _MACE_GRAPH_BATCH_CACHE.pop(key)
            _MACE_GRAPH_BATCH_CACHE_BYTES -= removed_bytes
            return None
        _MACE_GRAPH_BATCH_CACHE.move_to_end(key)
        return batch.clone().cpu(), counts.copy()


def _store_graph_batch(calc: Any, atoms_batch: Sequence[Any], batch: Any, counts: np.ndarray) -> None:
    global _MACE_GRAPH_BATCH_CACHE_BYTES
    if _MACE_GRAPH_BATCH_CACHE_MAX_BYTES <= 0:
        return
    try:
        references = tuple(weakref.ref(atoms) for atoms in atoms_batch)
        cpu_batch = batch.clone().cpu()
    except (TypeError, AttributeError):
        return
    resident_bytes = _graph_tensor_bytes(cpu_batch) + int(counts.nbytes)
    if resident_bytes > _MACE_GRAPH_BATCH_CACHE_MAX_BYTES:
        return
    key = _graph_batch_cache_key(calc, atoms_batch)
    with _MACE_GRAPH_BATCH_CACHE_LOCK:
        previous = _MACE_GRAPH_BATCH_CACHE.pop(key, None)
        if previous is not None:
            _MACE_GRAPH_BATCH_CACHE_BYTES -= previous[3]
        _MACE_GRAPH_BATCH_CACHE[key] = (references, cpu_batch, counts.copy(), resident_bytes)
        _MACE_GRAPH_BATCH_CACHE_BYTES += resident_bytes
        while (
            _MACE_GRAPH_BATCH_CACHE
            and _MACE_GRAPH_BATCH_CACHE_BYTES > _MACE_GRAPH_BATCH_CACHE_MAX_BYTES
        ):
            _, (_, _, _, removed_bytes) = _MACE_GRAPH_BATCH_CACHE.popitem(last=False)
            _MACE_GRAPH_BATCH_CACHE_BYTES -= removed_bytes


def clear_mace_graph_batch_cache() -> None:
    """Release cached CPU graph batches used across checkpoint evaluations."""

    global _MACE_GRAPH_BATCH_CACHE_BYTES
    with _MACE_GRAPH_BATCH_CACHE_LOCK:
        _MACE_GRAPH_BATCH_CACHE.clear()
        _MACE_GRAPH_BATCH_CACHE_BYTES = 0
    clear_mace_monitor_graph_cache()


_MACE_MONITOR_GRAPH_CACHE: "OrderedDict[str, tuple[Any, np.ndarray, int]]" = OrderedDict()
_MACE_MONITOR_GRAPH_CACHE_BYTES = 0
_MACE_MONITOR_GRAPH_CACHE_LOCK = RLock()
_MACE_MONITOR_GRAPH_CACHE_MAX_BYTES = max(
    0, int(os.environ.get("MDSTATS_MACE_MONITOR_GRAPH_CACHE_BYTES", str(1024 * 1024**2)))
)
_MACE_MONITOR_GRAPH_KEY_LOCKS: dict[str, RLock] = {}


@lru_cache(maxsize=None)
def _dependency_version(distribution: str) -> str:
    try:
        return str(importlib_metadata.version(distribution))
    except importlib_metadata.PackageNotFoundError:
        return "unavailable"


def _mace_monitor_graph_policy_payload(calc: Any) -> dict[str, Any]:
    """Return model-independent graph-construction identity for one calculator."""

    try:
        import mace
    except Exception:  # pragma: no cover - only reachable without optional dependency
        mace_version = "unavailable"
    else:
        mace_version = str(getattr(mace, "__version__", "unknown"))
    try:
        import torch
    except Exception:  # pragma: no cover
        torch_version = "unavailable"
    else:
        torch_version = str(getattr(torch, "__version__", "unknown"))
    z_values = tuple(int(value) for value in getattr(getattr(calc, "z_table", None), "zs", ()))
    return {
        "schema": MACE_MONITOR_GRAPH_CACHE_SCHEMA,
        "policy_version": MACE_MONITOR_GRAPH_POLICY_VERSION,
        "calculator_class": f"{type(calc).__module__}.{type(calc).__qualname__}",
        "r_max": float(calc.r_max),
        "default_dtype": str(calc.default_dtype),
        "head": str(calc.head),
        "z_table": list(z_values),
        "available_heads": [str(value) for value in getattr(calc, "available_heads", ())],
        "info_keys": sorted((str(key), str(value)) for key, value in getattr(calc, "info_keys", {}).items()),
        "arrays_keys": sorted((str(key), str(value)) for key, value in getattr(calc, "arrays_keys", {}).items()),
        "mace_version": mace_version,
        "torch_version": torch_version,
        "dependency_versions": {
            "ase": _dependency_version("ase"),
            "e3nn": _dependency_version("e3nn"),
            "matscipy": _dependency_version("matscipy"),
            "numpy": _dependency_version("numpy"),
            "torch_geometric": _dependency_version("torch-geometric"),
        },
    }


def _mace_monitor_graph_token(calc: Any, geometry_identities: Sequence[str]) -> tuple[str, str]:
    geometry_values = tuple(str(value) for value in geometry_identities)
    if not geometry_values:
        raise TrainingDataInputError("Monitor graph shard requires geometry identities.")
    policy_digest = digest(_mace_monitor_graph_policy_payload(calc))
    token = digest(
        {
            "schema": MACE_MONITOR_GRAPH_CACHE_SCHEMA,
            "policy_digest": policy_digest,
            "geometry_identities": list(geometry_values),
        }
    )
    return token, policy_digest


def _mace_monitor_graph_paths(root_directory: str | Path, token: str) -> tuple[Path, Path]:
    root = Path(root_directory).resolve()
    directory = root / token[:2]
    return directory / f"{token}.json", directory / f"{token}.pt"


def _monitor_graph_memory_get(token: str, calc: Any) -> tuple[Any, np.ndarray] | None:
    with _MACE_MONITOR_GRAPH_CACHE_LOCK:
        cached = _MACE_MONITOR_GRAPH_CACHE.get(token)
        if cached is None:
            return None
        batch, counts, _ = cached
        _MACE_MONITOR_GRAPH_CACHE.move_to_end(token)
        try:
            return batch.clone().to(calc.device), counts.copy()
        except Exception:
            return None


def _monitor_graph_memory_get_cpu(token: str) -> tuple[Any, np.ndarray] | None:
    with _MACE_MONITOR_GRAPH_CACHE_LOCK:
        cached = _MACE_MONITOR_GRAPH_CACHE.get(token)
        if cached is None:
            return None
        batch, counts, _ = cached
        _MACE_MONITOR_GRAPH_CACHE.move_to_end(token)
        try:
            return batch.clone().cpu(), counts.copy()
        except Exception:
            return None


def _monitor_graph_memory_store(token: str, batch: Any, counts: np.ndarray) -> None:
    global _MACE_MONITOR_GRAPH_CACHE_BYTES
    if _MACE_MONITOR_GRAPH_CACHE_MAX_BYTES <= 0:
        return
    try:
        cpu_batch = batch.clone().cpu()
    except Exception:
        return
    resident = _graph_tensor_bytes(cpu_batch) + int(counts.nbytes)
    if resident > _MACE_MONITOR_GRAPH_CACHE_MAX_BYTES:
        return
    with _MACE_MONITOR_GRAPH_CACHE_LOCK:
        previous = _MACE_MONITOR_GRAPH_CACHE.pop(token, None)
        if previous is not None:
            _MACE_MONITOR_GRAPH_CACHE_BYTES -= previous[2]
        _MACE_MONITOR_GRAPH_CACHE[token] = (cpu_batch, counts.copy(), resident)
        _MACE_MONITOR_GRAPH_CACHE_BYTES += resident
        while (
            _MACE_MONITOR_GRAPH_CACHE
            and _MACE_MONITOR_GRAPH_CACHE_BYTES > _MACE_MONITOR_GRAPH_CACHE_MAX_BYTES
        ):
            _, (_, _, removed) = _MACE_MONITOR_GRAPH_CACHE.popitem(last=False)
            _MACE_MONITOR_GRAPH_CACHE_BYTES -= removed


def _monitor_graph_key_lock(token: str) -> RLock:
    with _MACE_MONITOR_GRAPH_CACHE_LOCK:
        return _MACE_MONITOR_GRAPH_KEY_LOCKS.setdefault(token, RLock())


def _load_persistent_monitor_graph(
    root_directory: str | Path | None,
    *,
    token: str,
    policy_digest: str,
    geometry_identities: Sequence[str],
    calc: Any,
) -> tuple[Any, np.ndarray] | None:
    if root_directory is None:
        return None
    metadata_path, data_path = _mace_monitor_graph_paths(root_directory, token)
    if not metadata_path.is_file() or not data_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            payload.get("schema") != MACE_MONITOR_GRAPH_CACHE_SCHEMA
            or payload.get("token") != token
            or payload.get("policy_digest") != policy_digest
            or tuple(str(value) for value in payload.get("geometry_identities", ()))
            != tuple(str(value) for value in geometry_identities)
            or sha256_file_cached(data_path) != payload.get("file_sha256")
        ):
            return None
        import torch

        loaded = torch.load(data_path, map_location="cpu", weights_only=False)
        batch = loaded["batch"]
        counts = np.asarray(loaded["counts"], dtype=np.int64)
        if counts.shape != (len(geometry_identities),) or np.any(counts <= 0):
            return None
        if int(getattr(batch, "num_graphs", len(counts))) != len(counts):
            return None
        _monitor_graph_memory_store(token, batch, counts)
        return batch.clone().to(calc.device), counts.copy()
    except Exception:
        return None


def _load_persistent_monitor_graph_cpu(
    root_directory: str | Path | None,
    *,
    token: str,
    policy_digest: str,
    geometry_identities: Sequence[str],
) -> tuple[Any, np.ndarray] | None:
    if root_directory is None:
        return None
    metadata_path, data_path = _mace_monitor_graph_paths(root_directory, token)
    if not metadata_path.is_file() or not data_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            payload.get("schema") != MACE_MONITOR_GRAPH_CACHE_SCHEMA
            or payload.get("token") != token
            or payload.get("policy_digest") != policy_digest
            or tuple(str(value) for value in payload.get("geometry_identities", ()))
            != tuple(str(value) for value in geometry_identities)
            or sha256_file_cached(data_path) != payload.get("file_sha256")
        ):
            return None
        import torch
        loaded = torch.load(data_path, map_location="cpu", weights_only=False)
        batch = loaded["batch"]
        counts = np.asarray(loaded["counts"], dtype=np.int64)
        _monitor_graph_memory_store(token, batch, counts)
        return batch.clone().cpu(), counts.copy()
    except Exception:
        return None


def _write_persistent_monitor_graph(
    root_directory: str | Path | None,
    *,
    token: str,
    policy_digest: str,
    geometry_identities: Sequence[str],
    batch: Any,
    counts: np.ndarray,
) -> None:
    if root_directory is None:
        return
    metadata_path, data_path = _mace_monitor_graph_paths(root_directory, token)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    import torch

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{data_path.name}.", suffix=".tmp", dir=data_path.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        torch.save({"batch": batch.clone().cpu(), "counts": np.asarray(counts, dtype=np.int64)}, temporary)
        file_sha = sha256_file_cached(temporary)
        os.replace(temporary, data_path)
        metadata = {
            "schema": MACE_MONITOR_GRAPH_CACHE_SCHEMA,
            "token": token,
            "policy_digest": policy_digest,
            "geometry_identities": [str(value) for value in geometry_identities],
            "file_sha256": file_sha,
            "configuration_count": len(geometry_identities),
        }
        fd, metadata_name = tempfile.mkstemp(
            prefix=f".{metadata_path.name}.", suffix=".tmp", dir=metadata_path.parent
        )
        os.close(fd)
        metadata_temporary = Path(metadata_name)
        try:
            metadata_temporary.write_text(
                json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8"
            )
            os.replace(metadata_temporary, metadata_path)
        finally:
            metadata_temporary.unlink(missing_ok=True)
    finally:
        temporary.unlink(missing_ok=True)


def clear_mace_monitor_graph_cache() -> None:
    """Release in-memory monitor graph shards; persistent cache remains reconstructable."""

    global _MACE_MONITOR_GRAPH_CACHE_BYTES
    with _MACE_MONITOR_GRAPH_CACHE_LOCK:
        _MACE_MONITOR_GRAPH_CACHE.clear()
        _MACE_MONITOR_GRAPH_KEY_LOCKS.clear()
        _MACE_MONITOR_GRAPH_CACHE_BYTES = 0


def _file_identity(path: Path) -> tuple[str, int, int, int, int, int]:
    stat = path.stat()
    return (
        str(path.resolve()),
        int(stat.st_dev),
        int(stat.st_ino),
        int(stat.st_size),
        int(stat.st_mtime_ns),
        int(getattr(stat, "st_ctime_ns", 0)),
    )


@lru_cache(maxsize=6)
def _load_descriptor_shard_cached(
    identity: tuple[str, int, int, int, int, int],
    expected_sha256: str,
    members: tuple[str, ...],
) -> Mapping[str, np.ndarray]:
    """Authenticate one descriptor shard and materialize only requested members.

    ``numpy.load`` opens an NPZ lazily.  The former implementation iterated over
    ``archive.files`` and therefore decompressed the full atomic descriptor
    tensor even when DATA7 requested only compact per-frame summaries.  Binding
    the cache key to the exact member set keeps summary-only and descriptor-only
    paths bounded by the bytes they actually consume.
    """

    path = Path(identity[0])
    if _sha256_file(path) != expected_sha256:
        raise TrainingDataSerializationError("MACE descriptor shard SHA-256 mismatch.")
    requested = tuple(dict.fromkeys(str(name) for name in members))
    if not requested:
        raise TrainingDataSerializationError("Descriptor shard member request is empty.")
    try:
        result = load_npz_members_mmap(path, requested)
    except KeyError as exc:
        raise TrainingDataSerializationError(
            f"MACE descriptor shard is missing members: {tuple(exc.args[0])}."
        ) from exc
    except Exception as exc:
        raise TrainingDataSerializationError("Cannot read MACE descriptor shard.") from exc
    return result


def _load_descriptor_shard(
    path: Path,
    expected_sha256: str,
    members: Sequence[str],
) -> Mapping[str, np.ndarray]:
    return _load_descriptor_shard_cached(
        _file_identity(path), expected_sha256, tuple(str(name) for name in members)
    )


def _validate_float_array(
    value: Any,
    *,
    name: str,
    shape: tuple[int, ...] | None = None,
) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if shape is not None and result.shape != shape:
        raise TrainingDataInputError(f"{name} has shape {result.shape}, expected {shape}.")
    if np.any(~np.isfinite(result)):
        raise TrainingDataInputError(f"{name} contains non-finite values.")
    return result


@dataclass(frozen=True, slots=True)
class ModelCheckpointIdentity:
    """Checkpoint-bound DATA6 execution identity.

    v2 can bind a generic model as before, but source-foundation DATA6 paths
    additionally carry the canonical scientific potential identity and its
    execution identity.  Legacy v1 payloads preserve their historical payload
    and digest when round-tripped.
    """

    model_family: str
    checkpoint_locator: str
    checkpoint_sha256: str
    calculator_class: str
    model_version: str
    adapter_version: str = MACE_ADAPTER_VERSION
    supported_atomic_numbers: tuple[int, ...] = ()
    device: str = "cpu"
    default_dtype: str = "float64"
    metadata: tuple[tuple[str, str], ...] = ()
    foundation_potential_digest: str | None = None
    foundation_inference_digest: str | None = None
    foundation_head: str | None = None
    model_supported_atomic_numbers: tuple[int, ...] = ()
    requested_atomic_numbers: tuple[int, ...] = ()
    serialization_schema: str = field(default=MODEL_CHECKPOINT_IDENTITY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "model_family", "checkpoint_locator", "calculator_class",
            "model_version", "adapter_version", "device", "default_dtype",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        supported = tuple(sorted(set(int(v) for v in self.supported_atomic_numbers)))
        model_supported = tuple(sorted(set(int(v) for v in self.model_supported_atomic_numbers)))
        requested = tuple(sorted(set(int(v) for v in self.requested_atomic_numbers)))
        for name, values in (
            ("supported_atomic_numbers", supported),
            ("model_supported_atomic_numbers", model_supported),
            ("requested_atomic_numbers", requested),
        ):
            if any(v <= 0 for v in values):
                raise TrainingDataInputError(f"{name} must contain positive atomic numbers.")
        # The historical public field remains a compatibility alias.  New
        # foundation identities set it to the actual model support table.
        if not model_supported and supported:
            model_supported = supported
        if not supported and model_supported:
            supported = model_supported
        if requested and model_supported and not set(requested).issubset(model_supported):
            missing = sorted(set(requested) - set(model_supported))
            raise TrainingDataInputError(
                f"requested_atomic_numbers are not supported by the model: {missing}."
            )
        metadata = tuple(sorted((str(k), str(v)) for k, v in self.metadata))
        if len({k for k, _ in metadata}) != len(metadata):
            raise TrainingDataInputError("Checkpoint metadata keys must be unique.")
        potential = self.foundation_potential_digest
        inference = self.foundation_inference_digest
        head = None if self.foundation_head is None else str(self.foundation_head).strip()
        if potential is not None:
            potential = validate_digest(str(potential), name="foundation_potential_digest")
        if inference is not None:
            inference = validate_digest(str(inference), name="foundation_inference_digest")
        bound = (potential is not None, inference is not None, bool(head))
        if any(bound) and not all(bound):
            raise TrainingDataInputError(
                "Foundation-bound ModelCheckpointIdentity requires potential digest, inference digest, and head together."
            )
        if self.serialization_schema not in {MODEL_CHECKPOINT_IDENTITY_SCHEMA, MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA}:
            raise TrainingDataInputError("Unsupported model-checkpoint serialization schema.")
        if self.serialization_schema == MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA and any(bound):
            raise TrainingDataInputError("Legacy v1 model-checkpoint identity cannot carry foundation bindings.")
        object.__setattr__(self, "supported_atomic_numbers", supported)
        object.__setattr__(self, "model_supported_atomic_numbers", model_supported)
        object.__setattr__(self, "requested_atomic_numbers", requested)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "foundation_potential_digest", potential)
        object.__setattr__(self, "foundation_inference_digest", inference)
        object.__setattr__(self, "foundation_head", head or None)

    @property
    def foundation_bound(self) -> bool:
        return self.foundation_potential_digest is not None

    def _v1_payload(self) -> dict[str, Any]:
        return {
            "schema": MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA,
            "model_family": self.model_family,
            "checkpoint_locator": self.checkpoint_locator,
            "checkpoint_sha256": self.checkpoint_sha256,
            "calculator_class": self.calculator_class,
            "model_version": self.model_version,
            "adapter_version": self.adapter_version,
            "supported_atomic_numbers": list(self.supported_atomic_numbers),
            "device": self.device,
            "default_dtype": self.default_dtype,
            "metadata": dict(self.metadata),
        }

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema == MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA:
            return self._v1_payload()
        return {
            "schema": MODEL_CHECKPOINT_IDENTITY_SCHEMA,
            "model_family": self.model_family,
            "checkpoint_locator": self.checkpoint_locator,
            "checkpoint_sha256": self.checkpoint_sha256,
            "calculator_class": self.calculator_class,
            "model_version": self.model_version,
            "adapter_version": self.adapter_version,
            "supported_atomic_numbers": list(self.supported_atomic_numbers),
            "model_supported_atomic_numbers": list(self.model_supported_atomic_numbers),
            "requested_atomic_numbers": list(self.requested_atomic_numbers),
            "foundation_potential_digest": self.foundation_potential_digest,
            "foundation_inference_digest": self.foundation_inference_digest,
            "foundation_head": self.foundation_head,
            "device": self.device,
            "default_dtype": self.default_dtype,
            "metadata": dict(self.metadata),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelCheckpointIdentity":
        schema = str(payload.get("schema", ""))
        if schema not in {MODEL_CHECKPOINT_IDENTITY_SCHEMA, MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported model-checkpoint identity schema.")
        if schema == MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA:
            result = cls(
                model_family=str(payload["model_family"]),
                checkpoint_locator=str(payload["checkpoint_locator"]),
                checkpoint_sha256=str(payload["checkpoint_sha256"]),
                calculator_class=str(payload["calculator_class"]),
                model_version=str(payload["model_version"]),
                adapter_version=str(payload["adapter_version"]),
                supported_atomic_numbers=tuple(int(v) for v in payload.get("supported_atomic_numbers", ())),
                device=str(payload["device"]),
                default_dtype=str(payload["default_dtype"]),
                metadata=tuple((str(k), str(v)) for k, v in payload.get("metadata", {}).items()),
                serialization_schema=MODEL_CHECKPOINT_IDENTITY_V1_SCHEMA,
            )
        else:
            result = cls(
                model_family=str(payload["model_family"]),
                checkpoint_locator=str(payload["checkpoint_locator"]),
                checkpoint_sha256=str(payload["checkpoint_sha256"]),
                calculator_class=str(payload["calculator_class"]),
                model_version=str(payload["model_version"]),
                adapter_version=str(payload["adapter_version"]),
                supported_atomic_numbers=tuple(int(v) for v in payload.get("supported_atomic_numbers", ())),
                model_supported_atomic_numbers=tuple(int(v) for v in payload.get("model_supported_atomic_numbers", ())),
                requested_atomic_numbers=tuple(int(v) for v in payload.get("requested_atomic_numbers", ())),
                foundation_potential_digest=(None if payload.get("foundation_potential_digest") in (None, "") else str(payload["foundation_potential_digest"])),
                foundation_inference_digest=(None if payload.get("foundation_inference_digest") in (None, "") else str(payload["foundation_inference_digest"])),
                foundation_head=(None if payload.get("foundation_head") in (None, "") else str(payload["foundation_head"])),
                device=str(payload["device"]),
                default_dtype=str(payload["default_dtype"]),
                metadata=tuple((str(k), str(v)) for k, v in payload.get("metadata", {}).items()),
                serialization_schema=MODEL_CHECKPOINT_IDENTITY_SCHEMA,
            )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Model-checkpoint identity digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceDescriptorPolicy:
    invariants_only: bool = True
    num_layers: int | None = None
    output_dtype: str = "float64"
    require_two_dimensional: bool = True
    policy_version: str = MACE_DESCRIPTOR_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.num_layers is not None and self.num_layers <= 0:
            raise TrainingDataInputError("num_layers must be positive when present.")
        try:
            dtype = np.dtype(self.output_dtype)
        except TypeError as exc:
            raise TrainingDataInputError("output_dtype is invalid.") from exc
        if dtype.kind != "f":
            raise TrainingDataInputError("MACE descriptor output_dtype must be floating point.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "output_dtype", dtype.name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DESCRIPTOR_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "invariants_only": self.invariants_only,
            "num_layers": self.num_layers,
            "output_dtype": self.output_dtype,
            "require_two_dimensional": self.require_two_dimensional,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDescriptorPolicy":
        if payload.get("schema") != MACE_DESCRIPTOR_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE descriptor-policy schema.")
        result = cls(
            invariants_only=bool(payload["invariants_only"]),
            num_layers=None if payload.get("num_layers") is None else int(payload["num_layers"]),
            output_dtype=str(payload["output_dtype"]),
            require_two_dimensional=bool(payload["require_two_dimensional"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE descriptor-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceDescriptorSignature:
    """Runtime-qualified shape/architecture contract for MACE DATA6 descriptors.

    The signature is policy-specific.  It deliberately records observed model
    architecture/descriptor dimensions instead of assuming MPA-0 widths, while
    leaving DATA7's PCA/metric mathematics model-agnostic.
    """

    model_class: str
    architecture_signature: str
    selected_head: str
    num_interactions: int
    per_layer_raw_dimensions: tuple[int, ...]
    invariant_features_per_layer: int
    per_atom_invariant_dimension: int
    per_atom_full_dimension: int
    returned_per_atom_dimension: int
    global_summary_dimension: int
    species_summary_dimension: int
    invariants_only: bool
    num_layers: int
    adapter_version: str = MACE_ADAPTER_VERSION
    policy_version: str = MACE_DESCRIPTOR_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.model_class.strip() or not self.selected_head.strip():
            raise TrainingDataInputError("MACE descriptor signature identifiers must be non-empty.")
        object.__setattr__(
            self,
            "architecture_signature",
            validate_digest(self.architecture_signature, name="architecture_signature"),
        )
        if self.num_interactions <= 0 or self.num_layers <= 0:
            raise TrainingDataInputError("MACE descriptor interaction/layer counts must be positive.")
        raw = tuple(int(v) for v in self.per_layer_raw_dimensions)
        if len(raw) != self.num_interactions or any(v <= 0 for v in raw):
            raise TrainingDataInputError("MACE descriptor per-layer dimensions are invalid.")
        if self.num_layers > self.num_interactions:
            raise TrainingDataInputError("MACE descriptor num_layers exceeds the model interaction count.")
        for name in (
            "invariant_features_per_layer",
            "per_atom_invariant_dimension",
            "per_atom_full_dimension",
            "returned_per_atom_dimension",
            "global_summary_dimension",
            "species_summary_dimension",
        ):
            if int(getattr(self, name)) <= 0:
                raise TrainingDataInputError(f"{name} must be positive.")
        expected_invariant = self.num_layers * int(self.invariant_features_per_layer)
        expected_full = int(sum(raw[: self.num_layers]))
        if self.per_atom_invariant_dimension != expected_invariant:
            raise TrainingDataInputError("MACE invariant descriptor dimension is inconsistent with layer metadata.")
        if self.per_atom_full_dimension != expected_full:
            raise TrainingDataInputError("MACE full descriptor dimension is inconsistent with layer metadata.")
        expected_returned = expected_invariant if self.invariants_only else expected_full
        if self.returned_per_atom_dimension != expected_returned:
            raise TrainingDataInputError("MACE returned descriptor dimension is inconsistent with policy metadata.")
        if self.global_summary_dimension != 2 * expected_returned:
            raise TrainingDataInputError("MACE global descriptor-summary dimension is inconsistent.")
        if self.species_summary_dimension != expected_returned:
            raise TrainingDataInputError("MACE species descriptor-summary dimension is inconsistent.")
        if not self.adapter_version.strip() or not self.policy_version.strip():
            raise TrainingDataInputError("MACE descriptor signature version identifiers must be non-empty.")
        object.__setattr__(self, "per_layer_raw_dimensions", raw)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DESCRIPTOR_SIGNATURE_SCHEMA,
            "model_class": self.model_class,
            "architecture_signature": self.architecture_signature,
            "selected_head": self.selected_head,
            "num_interactions": self.num_interactions,
            "per_layer_raw_dimensions": list(self.per_layer_raw_dimensions),
            "invariant_features_per_layer": self.invariant_features_per_layer,
            "per_atom_invariant_dimension": self.per_atom_invariant_dimension,
            "per_atom_full_dimension": self.per_atom_full_dimension,
            "returned_per_atom_dimension": self.returned_per_atom_dimension,
            "global_summary_dimension": self.global_summary_dimension,
            "species_summary_dimension": self.species_summary_dimension,
            "invariants_only": self.invariants_only,
            "num_layers": self.num_layers,
            "adapter_version": self.adapter_version,
            "policy_version": self.policy_version,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDescriptorSignature":
        if payload.get("schema") != MACE_DESCRIPTOR_SIGNATURE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE descriptor-signature schema.")
        result = cls(
            model_class=str(payload["model_class"]),
            architecture_signature=str(payload["architecture_signature"]),
            selected_head=str(payload["selected_head"]),
            num_interactions=int(payload["num_interactions"]),
            per_layer_raw_dimensions=tuple(int(v) for v in payload["per_layer_raw_dimensions"]),
            invariant_features_per_layer=int(payload["invariant_features_per_layer"]),
            per_atom_invariant_dimension=int(payload["per_atom_invariant_dimension"]),
            per_atom_full_dimension=int(payload["per_atom_full_dimension"]),
            returned_per_atom_dimension=int(payload["returned_per_atom_dimension"]),
            global_summary_dimension=int(payload["global_summary_dimension"]),
            species_summary_dimension=int(payload["species_summary_dimension"]),
            invariants_only=bool(payload["invariants_only"]),
            num_layers=int(payload["num_layers"]),
            adapter_version=str(payload["adapter_version"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE descriptor-signature digest mismatch.")
        return result


class MaceBatchWorkloadMode(str, Enum):
    """Execution mode whose device-memory pressure is being calibrated."""

    DESCRIPTOR_ONLY = "descriptor_only"
    PREDICTION_ONLY = "prediction_only"
    COMBINED_EVALUATE = "combined_evaluate"


@dataclass(frozen=True, slots=True)
class MaceBatchCapacityProbe:
    """One workload-specific batch-capacity probe.

    CUDA allocator counters are process-local while ``driver_free_*`` is the
    device-global free-memory view returned by ``cudaMemGetInfo``.  CPU probes
    leave device-memory fields unset but still retain timing and throughput.
    """

    batch_size: int
    elapsed_seconds: float
    structures_per_second: float
    success: bool
    oom: bool = False
    baseline_allocated_bytes: int | None = None
    baseline_reserved_bytes: int | None = None
    peak_allocated_bytes: int | None = None
    peak_reserved_bytes: int | None = None
    post_allocated_bytes: int | None = None
    post_reserved_bytes: int | None = None
    driver_free_before_bytes: int | None = None
    driver_free_after_bytes: int | None = None
    driver_total_bytes: int | None = None

    def __post_init__(self) -> None:
        if int(self.batch_size) <= 0:
            raise TrainingDataInputError("MACE batch probe size must be positive.")
        if float(self.elapsed_seconds) < 0.0 or not np.isfinite(float(self.elapsed_seconds)):
            raise TrainingDataInputError("MACE batch probe elapsed time must be finite and nonnegative.")
        if float(self.structures_per_second) < 0.0 or not np.isfinite(float(self.structures_per_second)):
            raise TrainingDataInputError("MACE batch probe throughput must be finite and nonnegative.")
        if bool(self.success) and bool(self.oom):
            raise TrainingDataInputError("A successful MACE batch probe cannot also be OOM.")
        for name in (
            "baseline_allocated_bytes", "baseline_reserved_bytes",
            "peak_allocated_bytes", "peak_reserved_bytes",
            "post_allocated_bytes", "post_reserved_bytes",
            "driver_free_before_bytes", "driver_free_after_bytes",
            "driver_total_bytes",
        ):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative when present.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_BATCH_CAPACITY_PROBE_SCHEMA,
            "batch_size": int(self.batch_size),
            "elapsed_seconds": float(self.elapsed_seconds),
            "structures_per_second": float(self.structures_per_second),
            "success": bool(self.success),
            "oom": bool(self.oom),
            "baseline_allocated_bytes": self.baseline_allocated_bytes,
            "baseline_reserved_bytes": self.baseline_reserved_bytes,
            "peak_allocated_bytes": self.peak_allocated_bytes,
            "peak_reserved_bytes": self.peak_reserved_bytes,
            "post_allocated_bytes": self.post_allocated_bytes,
            "post_reserved_bytes": self.post_reserved_bytes,
            "driver_free_before_bytes": self.driver_free_before_bytes,
            "driver_free_after_bytes": self.driver_free_after_bytes,
            "driver_total_bytes": self.driver_total_bytes,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceBatchCapacityProbe":
        if payload.get("schema") != MACE_BATCH_CAPACITY_PROBE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE batch-capacity probe schema.")
        result = cls(
            batch_size=int(payload["batch_size"]),
            elapsed_seconds=float(payload["elapsed_seconds"]),
            structures_per_second=float(payload["structures_per_second"]),
            success=bool(payload["success"]),
            oom=bool(payload.get("oom", False)),
            baseline_allocated_bytes=None if payload.get("baseline_allocated_bytes") is None else int(payload["baseline_allocated_bytes"]),
            baseline_reserved_bytes=None if payload.get("baseline_reserved_bytes") is None else int(payload["baseline_reserved_bytes"]),
            peak_allocated_bytes=None if payload.get("peak_allocated_bytes") is None else int(payload["peak_allocated_bytes"]),
            peak_reserved_bytes=None if payload.get("peak_reserved_bytes") is None else int(payload["peak_reserved_bytes"]),
            post_allocated_bytes=None if payload.get("post_allocated_bytes") is None else int(payload["post_allocated_bytes"]),
            post_reserved_bytes=None if payload.get("post_reserved_bytes") is None else int(payload["post_reserved_bytes"]),
            driver_free_before_bytes=None if payload.get("driver_free_before_bytes") is None else int(payload["driver_free_before_bytes"]),
            driver_free_after_bytes=None if payload.get("driver_free_after_bytes") is None else int(payload["driver_free_after_bytes"]),
            driver_total_bytes=None if payload.get("driver_total_bytes") is None else int(payload["driver_total_bytes"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE batch-capacity probe digest mismatch.")
        return result


def recommend_mace_batch_size_from_probes(
    probes: Sequence[MaceBatchCapacityProbe],
    *,
    max_device_fraction: float,
    reserve_bytes: int,
    throughput_tolerance_fraction: float,
    device_budget_bytes: int | None = None,
) -> int:
    """Choose the smallest safe probe within tolerance of peak throughput.

    This pure decision helper is intentionally independent of CUDA so VRAM1's
    throughput/headroom rule can be unit-tested without an accelerator.
    """
    records = tuple(probes)
    successful = tuple(probe for probe in records if probe.success)
    if not successful:
        raise TrainingDataInputError("No successful MACE batch-capacity probe is available.")
    safe: list[MaceBatchCapacityProbe] = []
    for probe in successful:
        total = probe.driver_total_bytes
        peak_reserved = probe.peak_reserved_bytes
        free_after = probe.driver_free_after_bytes
        if total is None or peak_reserved is None or free_after is None:
            continue
        if peak_reserved > int(float(max_device_fraction) * int(total)):
            continue
        if free_after < int(reserve_bytes):
            continue
        if device_budget_bytes is not None:
            incremental = max(1, int(peak_reserved) - int(probe.baseline_reserved_bytes or 0))
            if incremental > int(device_budget_bytes):
                continue
        safe.append(probe)
    if not safe:
        return min(probe.batch_size for probe in successful)
    max_throughput = max(probe.structures_per_second for probe in safe)
    floor = max_throughput * (1.0 - float(throughput_tolerance_fraction))
    near_best = [probe for probe in safe if probe.structures_per_second >= floor]
    return min(probe.batch_size for probe in near_best)


@dataclass(frozen=True, slots=True)
class MaceBatchCapacityCalibration:
    """Workload-specific DATA6 batch-capacity evidence.

    Version 2 distinguishes descriptor-only, prediction-only, and derivative-
    bearing combined evaluation.  Historical v1 records remain readable and
    retain their descriptor-only meaning.
    """

    descriptor_signature_digest: str
    device: str
    requested_max_batch_size: int
    probed_batch_sizes: tuple[int, ...]
    successful_batch_sizes: tuple[int, ...]
    recommended_batch_size: int
    descriptor_bytes_per_structure: int
    graph_bytes_per_structure: int
    prediction_bytes_per_structure: int = 0
    peak_device_bytes_per_structure: int | None = None
    device_budget_bytes: int | None = None
    calibration_method: str = "model_aware_probe_v2"
    workload_mode: MaceBatchWorkloadMode = MaceBatchWorkloadMode.DESCRIPTOR_ONLY
    checkpoint_identity_digest: str | None = None
    calibration_frame_digests: tuple[str, ...] = ()
    probes: tuple[MaceBatchCapacityProbe, ...] = ()
    max_device_fraction: float = 0.80
    reserve_bytes: int = 4 * 1024**3
    throughput_tolerance_fraction: float = 0.05
    post_cleanup_allocated_bytes: int | None = None
    post_cleanup_reserved_bytes: int | None = None
    post_cleanup_free_bytes: int | None = None
    post_cleanup_total_bytes: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "descriptor_signature_digest",
            validate_digest(self.descriptor_signature_digest, name="descriptor_signature_digest"),
        )
        if self.checkpoint_identity_digest is not None:
            object.__setattr__(
                self, "checkpoint_identity_digest",
                validate_digest(self.checkpoint_identity_digest, name="checkpoint_identity_digest"),
            )
        object.__setattr__(self, "workload_mode", MaceBatchWorkloadMode(self.workload_mode))
        if not self.device.strip() or not self.calibration_method.strip():
            raise TrainingDataInputError("MACE batch calibration identifiers must be non-empty.")
        probed = tuple(int(v) for v in self.probed_batch_sizes)
        successful = tuple(int(v) for v in self.successful_batch_sizes)
        frames = tuple(validate_digest(v, name="calibration_frame_digest") for v in self.calibration_frame_digests)
        probes = tuple(self.probes)
        if self.requested_max_batch_size <= 0 or self.recommended_batch_size <= 0:
            raise TrainingDataInputError("MACE batch calibration sizes must be positive.")
        if any(v <= 0 for v in probed + successful):
            raise TrainingDataInputError("MACE batch calibration probe sizes must be positive.")
        if successful and self.recommended_batch_size not in successful:
            raise TrainingDataInputError("Recommended MACE batch size was not successfully probed.")
        if probes and tuple(v.batch_size for v in probes) != probed:
            raise TrainingDataInputError("MACE batch probes must exactly match probed_batch_sizes in order.")
        if probes and tuple(v.batch_size for v in probes if v.success) != successful:
            raise TrainingDataInputError("Successful MACE batch probes do not match successful_batch_sizes.")
        for name in ("descriptor_bytes_per_structure", "graph_bytes_per_structure"):
            if int(getattr(self, name)) <= 0:
                raise TrainingDataInputError(f"{name} must be positive.")
        if int(self.prediction_bytes_per_structure) < 0:
            raise TrainingDataInputError("prediction_bytes_per_structure must be nonnegative.")
        if self.peak_device_bytes_per_structure is not None and self.peak_device_bytes_per_structure <= 0:
            raise TrainingDataInputError("peak_device_bytes_per_structure must be positive when present.")
        if self.device_budget_bytes is not None and self.device_budget_bytes <= 0:
            raise TrainingDataInputError("device_budget_bytes must be positive when present.")
        if not (0.0 < float(self.max_device_fraction) <= 1.0):
            raise TrainingDataInputError("max_device_fraction must lie in (0, 1].")
        if int(self.reserve_bytes) < 0:
            raise TrainingDataInputError("reserve_bytes must be nonnegative.")
        if not (0.0 <= float(self.throughput_tolerance_fraction) < 1.0):
            raise TrainingDataInputError("throughput_tolerance_fraction must lie in [0, 1).")
        for name in (
            "post_cleanup_allocated_bytes", "post_cleanup_reserved_bytes",
            "post_cleanup_free_bytes", "post_cleanup_total_bytes",
        ):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise TrainingDataInputError(f"{name} must be nonnegative when present.")
        object.__setattr__(self, "probed_batch_sizes", probed)
        object.__setattr__(self, "successful_batch_sizes", successful)
        object.__setattr__(self, "calibration_frame_digests", frames)
        object.__setattr__(self, "probes", probes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_BATCH_CAPACITY_CALIBRATION_SCHEMA,
            "descriptor_signature_digest": self.descriptor_signature_digest,
            "device": self.device,
            "requested_max_batch_size": self.requested_max_batch_size,
            "probed_batch_sizes": list(self.probed_batch_sizes),
            "successful_batch_sizes": list(self.successful_batch_sizes),
            "recommended_batch_size": self.recommended_batch_size,
            "descriptor_bytes_per_structure": self.descriptor_bytes_per_structure,
            "graph_bytes_per_structure": self.graph_bytes_per_structure,
            "prediction_bytes_per_structure": int(self.prediction_bytes_per_structure),
            "peak_device_bytes_per_structure": self.peak_device_bytes_per_structure,
            "device_budget_bytes": self.device_budget_bytes,
            "calibration_method": self.calibration_method,
            "workload_mode": self.workload_mode.value,
            "checkpoint_identity_digest": self.checkpoint_identity_digest,
            "calibration_frame_digests": list(self.calibration_frame_digests),
            "probes": [probe.to_dict() for probe in self.probes],
            "max_device_fraction": float(self.max_device_fraction),
            "reserve_bytes": int(self.reserve_bytes),
            "throughput_tolerance_fraction": float(self.throughput_tolerance_fraction),
            "post_cleanup_allocated_bytes": self.post_cleanup_allocated_bytes,
            "post_cleanup_reserved_bytes": self.post_cleanup_reserved_bytes,
            "post_cleanup_free_bytes": self.post_cleanup_free_bytes,
            "post_cleanup_total_bytes": self.post_cleanup_total_bytes,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceBatchCapacityCalibration":
        schema = payload.get("schema")
        if schema not in {MACE_BATCH_CAPACITY_CALIBRATION_SCHEMA, MACE_BATCH_CAPACITY_CALIBRATION_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE batch-capacity calibration schema.")
        if schema == MACE_BATCH_CAPACITY_CALIBRATION_V1_SCHEMA:
            result = cls(
                descriptor_signature_digest=str(payload["descriptor_signature_digest"]),
                device=str(payload["device"]),
                requested_max_batch_size=int(payload["requested_max_batch_size"]),
                probed_batch_sizes=tuple(int(v) for v in payload.get("probed_batch_sizes", ())),
                successful_batch_sizes=tuple(int(v) for v in payload.get("successful_batch_sizes", ())),
                recommended_batch_size=int(payload["recommended_batch_size"]),
                descriptor_bytes_per_structure=int(payload["descriptor_bytes_per_structure"]),
                graph_bytes_per_structure=int(payload["graph_bytes_per_structure"]),
                prediction_bytes_per_structure=0,
                peak_device_bytes_per_structure=None if payload.get("peak_device_bytes_per_structure") is None else int(payload["peak_device_bytes_per_structure"]),
                device_budget_bytes=None if payload.get("device_budget_bytes") is None else int(payload["device_budget_bytes"]),
                calibration_method=str(payload.get("calibration_method", "model_aware_probe_v1")),
                workload_mode=MaceBatchWorkloadMode.DESCRIPTOR_ONLY,
                max_device_fraction=1.0,
                reserve_bytes=0,
                throughput_tolerance_fraction=0.0,
            )
            legacy = {
                "schema": MACE_BATCH_CAPACITY_CALIBRATION_V1_SCHEMA,
                "descriptor_signature_digest": result.descriptor_signature_digest,
                "device": result.device,
                "requested_max_batch_size": result.requested_max_batch_size,
                "probed_batch_sizes": list(result.probed_batch_sizes),
                "successful_batch_sizes": list(result.successful_batch_sizes),
                "recommended_batch_size": result.recommended_batch_size,
                "descriptor_bytes_per_structure": result.descriptor_bytes_per_structure,
                "graph_bytes_per_structure": result.graph_bytes_per_structure,
                "peak_device_bytes_per_structure": result.peak_device_bytes_per_structure,
                "device_budget_bytes": result.device_budget_bytes,
                "calibration_method": result.calibration_method,
            }
            if payload.get("content_digest") not in (None, digest(legacy)):
                raise TrainingDataSerializationError("MACE batch-capacity calibration digest mismatch.")
            return result
        result = cls(
            descriptor_signature_digest=str(payload["descriptor_signature_digest"]),
            device=str(payload["device"]),
            requested_max_batch_size=int(payload["requested_max_batch_size"]),
            probed_batch_sizes=tuple(int(v) for v in payload.get("probed_batch_sizes", ())),
            successful_batch_sizes=tuple(int(v) for v in payload.get("successful_batch_sizes", ())),
            recommended_batch_size=int(payload["recommended_batch_size"]),
            descriptor_bytes_per_structure=int(payload["descriptor_bytes_per_structure"]),
            graph_bytes_per_structure=int(payload["graph_bytes_per_structure"]),
            prediction_bytes_per_structure=int(payload.get("prediction_bytes_per_structure", 0)),
            peak_device_bytes_per_structure=None if payload.get("peak_device_bytes_per_structure") is None else int(payload["peak_device_bytes_per_structure"]),
            device_budget_bytes=None if payload.get("device_budget_bytes") is None else int(payload["device_budget_bytes"]),
            calibration_method=str(payload.get("calibration_method", "model_aware_probe_v2")),
            workload_mode=MaceBatchWorkloadMode(str(payload.get("workload_mode", "descriptor_only"))),
            checkpoint_identity_digest=None if payload.get("checkpoint_identity_digest") is None else str(payload["checkpoint_identity_digest"]),
            calibration_frame_digests=tuple(str(v) for v in payload.get("calibration_frame_digests", ())),
            probes=tuple(MaceBatchCapacityProbe.from_dict(v) for v in payload.get("probes", ())),
            max_device_fraction=float(payload.get("max_device_fraction", 0.80)),
            reserve_bytes=int(payload.get("reserve_bytes", 4 * 1024**3)),
            throughput_tolerance_fraction=float(payload.get("throughput_tolerance_fraction", 0.05)),
            post_cleanup_allocated_bytes=None if payload.get("post_cleanup_allocated_bytes") is None else int(payload["post_cleanup_allocated_bytes"]),
            post_cleanup_reserved_bytes=None if payload.get("post_cleanup_reserved_bytes") is None else int(payload["post_cleanup_reserved_bytes"]),
            post_cleanup_free_bytes=None if payload.get("post_cleanup_free_bytes") is None else int(payload["post_cleanup_free_bytes"]),
            post_cleanup_total_bytes=None if payload.get("post_cleanup_total_bytes") is None else int(payload["post_cleanup_total_bytes"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE batch-capacity calibration digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomicModelPrediction:
    energy_ev: float
    forces_ev_per_angstrom: np.ndarray
    stress_ev_per_angstrom3: np.ndarray | None

    def __post_init__(self) -> None:
        energy = float(self.energy_ev)
        if not np.isfinite(energy):
            raise TrainingDataInputError("Predicted energy must be finite.")
        forces = _validate_float_array(self.forces_ev_per_angstrom, name="predicted forces")
        if forces.ndim != 2 or forces.shape[1] != 3:
            raise TrainingDataInputError("Predicted forces must have shape (n_atoms, 3).")
        stress = None
        if self.stress_ev_per_angstrom3 is not None:
            stress = _validate_float_array(
                self.stress_ev_per_angstrom3,
                name="predicted stress",
                shape=(3, 3),
            )
        forces = np.array(forces, copy=True)
        forces.setflags(write=False)
        if stress is not None:
            stress = np.array(stress, copy=True)
            stress.setflags(write=False)
        object.__setattr__(self, "energy_ev", energy)
        object.__setattr__(self, "forces_ev_per_angstrom", forces)
        object.__setattr__(self, "stress_ev_per_angstrom3", stress)


class AtomicModelProvider(Protocol):
    @property
    def checkpoint_identity(self) -> ModelCheckpointIdentity: ...

    def get_descriptors(self, atoms: Any, policy: MaceDescriptorPolicy) -> np.ndarray: ...

    def predict(self, atoms: Any) -> AtomicModelPrediction: ...

    def evaluate_batch(
        self, atoms_batch: Sequence[Any], policy: MaceDescriptorPolicy
    ) -> tuple[tuple[np.ndarray, ...], tuple[AtomicModelPrediction, ...]]: ...


class _MaceDescriptorAdapter:
    """One implementation of the MACE 0.3.16 descriptor contract.

    Both descriptor-only and combined descriptor/prediction batching use this
    object so architecture interpretation cannot drift between the two paths.
    """

    def __init__(self, calculator: Any, checkpoint_identity: ModelCheckpointIdentity):
        try:
            from e3nn import o3
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise TrainingDataInputError("MACE descriptor adapter requires e3nn.") from exc
        if int(getattr(calculator, "num_models", len(getattr(calculator, "models", ())))) != 1:
            raise TrainingDataInputError("Qualified native descriptor adapter requires exactly one MACE model.")
        model = calculator.models[0]
        if not hasattr(model, "products") or not model.products:
            raise TrainingDataInputError("MACE model does not expose product irreps required for descriptors.")
        self.calculator = calculator
        self.model = model
        self.checkpoint_identity = checkpoint_identity
        self.num_interactions = int(model.num_interactions)
        irreps_out = o3.Irreps(str(model.products[0].linear.irreps_out))
        self.irreps_out = irreps_out
        self.l_max = int(irreps_out.lmax)
        divisor = (self.l_max + 1) ** 2
        if irreps_out.dim % divisor != 0:
            raise TrainingDataInputError("MACE product irreps cannot be decomposed into invariant feature channels.")
        self.invariant_features = int(irreps_out.dim // divisor)
        raw = [int(irreps_out.dim) for _ in range(self.num_interactions)]
        raw[-1] = self.invariant_features
        self.per_layer_raw_dimensions = tuple(raw)
        architecture = dict(checkpoint_identity.metadata).get("foundation_architecture_signature")
        if architecture is None:
            state_shapes = [
                (str(key), tuple(int(v) for v in tensor.shape), str(tensor.dtype))
                for key, tensor in model.state_dict().items()
            ]
            architecture = digest(
                {
                    "model_class": f"{type(model).__module__}.{type(model).__qualname__}",
                    "num_interactions": self.num_interactions,
                    "product_irreps_out": str(irreps_out),
                    "state_shapes": state_shapes,
                }
            )
        self.architecture_signature = validate_digest(
            str(architecture), name="descriptor_architecture_signature"
        )

    def _num_layers(self, policy: MaceDescriptorPolicy) -> int:
        value = self.num_interactions if policy.num_layers is None else int(policy.num_layers)
        if value <= 0 or value > self.num_interactions:
            raise TrainingDataInputError(
                f"Requested {value} MACE descriptor layers for a {self.num_interactions}-interaction model."
            )
        return value

    def signature(self, policy: MaceDescriptorPolicy) -> MaceDescriptorSignature:
        num_layers = self._num_layers(policy)
        invariant_dimension = num_layers * self.invariant_features
        full_dimension = int(sum(self.per_layer_raw_dimensions[:num_layers]))
        returned = invariant_dimension if policy.invariants_only else full_dimension
        return MaceDescriptorSignature(
            model_class=f"{type(self.model).__module__}.{type(self.model).__qualname__}",
            architecture_signature=self.architecture_signature,
            selected_head=str(self.calculator.head),
            num_interactions=self.num_interactions,
            per_layer_raw_dimensions=self.per_layer_raw_dimensions,
            invariant_features_per_layer=self.invariant_features,
            per_atom_invariant_dimension=invariant_dimension,
            per_atom_full_dimension=full_dimension,
            returned_per_atom_dimension=returned,
            global_summary_dimension=2 * returned,
            species_summary_dimension=returned,
            invariants_only=bool(policy.invariants_only),
            num_layers=num_layers,
            adapter_version=self.checkpoint_identity.adapter_version,
            policy_version=policy.policy_version,
        )

    def transform_node_feats(self, node_feats: Any, policy: MaceDescriptorPolicy) -> Any:
        try:
            from mace.modules.utils import extract_invariant
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE descriptor transformation dependencies are unavailable.") from exc
        signature = self.signature(policy)
        descriptor = node_feats
        if policy.invariants_only:
            descriptor = extract_invariant(
                descriptor,
                num_layers=signature.num_layers,
                num_features=self.invariant_features,
                l_max=self.l_max,
            )
        descriptor = descriptor[:, : signature.returned_per_atom_dimension]
        if int(descriptor.shape[1]) != signature.returned_per_atom_dimension:
            raise TrainingDataInputError(
                "MACE node-feature payload does not match the qualified descriptor signature."
            )
        return descriptor

    def validate_array(
        self,
        descriptor: np.ndarray,
        *,
        atom_count: int,
        policy: MaceDescriptorPolicy,
    ) -> np.ndarray:
        signature = self.signature(policy)
        value = np.asarray(descriptor, dtype=np.dtype(policy.output_dtype))
        if value.ndim != 2 or value.shape != (int(atom_count), signature.returned_per_atom_dimension):
            raise TrainingDataInputError(
                "MACE descriptor payload does not match its runtime-qualified signature: "
                f"observed={value.shape}, expected=({atom_count}, {signature.returned_per_atom_dimension})."
            )
        if np.any(~np.isfinite(value)):
            raise TrainingDataInputError("MACE descriptors must be finite.")
        return np.ascontiguousarray(value)


class MaceModelStateCompatibilityError(TrainingDataInputError):
    """A model cannot safely reuse an existing mutable MACE shell."""


class _AuthenticatedParameterShell:
    """Small provider-owned shell for bounded forward-override qualification.

    TRAIN2's raw continuation companion intentionally stores parameter state,
    not a deployable MACE whole-model serialization.  A real MACE model is
    therefore required for production prediction, but bounded CPU tests still
    need to exercise the same provider/state-authentication owner while
    replacing only the expensive forward arithmetic.  This shell is accepted
    solely by ``from_authenticated_parameter_state(...,
    allow_forward_override=True)``; its calculator cannot perform prediction
    and is never a production fallback.
    """

    def __init__(self, parameters: Sequence[Any]):
        import torch

        values = tuple(parameters)
        if not values:
            raise TrainingDataInputError(
                "Authenticated provider state requires at least one parameter."
            )
        self._parameter_list = torch.nn.ParameterList(
            [torch.nn.Parameter(torch.zeros_like(value, device="cpu")) for value in values]
        )

    def named_parameters(self, prefix: str = "", recurse: bool = True):
        return self._parameter_list.named_parameters(prefix=prefix, recurse=recurse)

    def named_modules(self, memo: Any = None, prefix: str = ""):
        # The canonical architecture authority only needs a deterministic
        # module census.  Keep the shell deliberately minimal and explicit.
        del memo
        yield prefix, self

    def named_buffers(self, prefix: str = "", recurse: bool = True):
        del prefix, recurse
        return iter(())

    def parameters(self, recurse: bool = True):
        return self._parameter_list.parameters(recurse=recurse)


class _AuthenticatedParameterCalculator:
    """Non-predicting calculator wrapper used only below the test seam."""

    model_type = "authenticated-parameter-shell"
    num_models = 1
    use_compile = False
    _enable_cueq = False
    _enable_oeq = False
    pad_num_atoms = 0
    pad_num_edges = 0
    available_heads: tuple[str, ...] = ()

    def __init__(self, model: Any, *, device: str, default_dtype: str):
        self.models = [model]
        self.device = str(device)
        self.default_dtype = str(default_dtype)

    def get_descriptors(self, *_args: Any, **_kwargs: Any) -> Any:
        raise TrainingDataInputError(
            "The authenticated parameter shell has no production descriptor calculator; "
            "use a deployable MACE model for numerical prediction."
        )


class MaceCalculatorProvider:
    """Lazy optional adapter around a MACE ASE calculator."""

    def __init__(self, calculator: Any, checkpoint_identity: ModelCheckpointIdentity):
        if not hasattr(calculator, "get_descriptors"):
            raise TrainingDataInputError("Calculator does not expose get_descriptors().")
        self._calculator = calculator
        self._checkpoint_identity = checkpoint_identity
        self._descriptor_adapter_cache: _MaceDescriptorAdapter | None = None
        self._runtime_architecture_digest_cache: str | None = None
        self._state_hot_swap_qualified = False
        # R17A 3.5 hot-swap transaction: a failed/partial state replacement
        # must never leave a contaminated shell available for later
        # inference.  ``_poisoned`` is permanent for this instance; recovery
        # is safe reconstruction from an authenticated checkpoint, never an
        # ad hoc reverse mutation of this provider.
        self._poisoned = False
        self._poison_reason: str | None = None

    @property
    def checkpoint_identity(self) -> ModelCheckpointIdentity:
        return self._checkpoint_identity

    def _raise_if_poisoned(self) -> None:
        if self._poisoned:
            raise MaceModelStateCompatibilityError(
                "MACE provider shell is poisoned after a failed checkpoint "
                f"state transaction and cannot be reused: {self._poison_reason}"
            )

    def _execution_architecture_descriptor(self) -> dict[str, Any]:
        calculator = self._calculator
        if calculator is None:
            raise TrainingDataInputError(
                "Closed MACE provider has no runtime architecture identity."
            )
        return _mace_provider_execution_architecture_descriptor(
            calculator,
            model_version=self._checkpoint_identity.model_version,
            adapter_version=MACE_ADAPTER_VERSION,
        )

    @property
    def runtime_architecture_digest(self) -> str:
        """Return weight-independent execution architecture identity.

        This is the same canonical R17A execution-architecture authority used
        to gate checkpoint hot swapping (``load_compatible_model_state``).
        Static inference calibration and graph-policy identity characterize
        tensor/graph execution shape, not scientific checkpoint weights: the
        digest binds exact model class, cutoff/species/head/radial/cutoff-
        function/interaction/product/readout architecture, dtype, and
        calculator shell policy (compile/CuEq/OEq) while deliberately
        excluding learned parameter values and checkpoint SHA.  Hardware,
        head selection, precision policy, and workload shape remain separate
        compatibility-key dimensions at the runtime-authority owner.
        """

        cached = self._runtime_architecture_digest_cache
        if cached is not None:
            return cached
        self._raise_if_poisoned()
        cached = digest(self._execution_architecture_descriptor())
        self._runtime_architecture_digest_cache = cached
        return cached

    @property
    def closed(self) -> bool:
        """Whether the provider has released its calculator ownership."""

        return self._calculator is None

    def close(self, *, release_cuda_memory: bool = True) -> None:
        """Release calculator/model ownership at an explicit stage boundary.

        DATA6 may construct a CUDA-backed MACE calculator whose model remains
        resident as long as this provider is referenced.  DATA7/DATA8 are
        CPU/I/O stages, so production callers close the provider after the
        final DATA6 consumer instead of relying on function-scope garbage
        collection.  The method is deliberately idempotent.
        """

        calculator = self._calculator
        if calculator is None:
            return
        torch_module = None
        if release_cuda_memory:
            try:
                import torch as torch_module
            except ModuleNotFoundError:  # pragma: no cover - optional dependency
                torch_module = None
            if torch_module is not None:
                try:
                    if torch_module.cuda.is_available():
                        # Finish pending device work while the model/calculator is
                        # still live, then drop all Python owners before asking the
                        # allocator to release unused blocks.
                        torch_module.cuda.synchronize()
                except Exception:
                    # Cleanup must remain best-effort during exception unwinding.
                    pass
        self._descriptor_adapter_cache = None
        self._calculator = None
        clear_mace_graph_batch_cache()
        del calculator
        gc.collect()
        if torch_module is None:
            return
        try:
            if torch_module.cuda.is_available():
                torch_module.cuda.empty_cache()
                torch_module.cuda.synchronize()
        except Exception:
            # The live model references were already released above.
            return

    def _descriptor_adapter(self) -> _MaceDescriptorAdapter:
        cached = self._descriptor_adapter_cache
        if cached is None:
            cached = _MaceDescriptorAdapter(self._calculator, self._checkpoint_identity)
            self._descriptor_adapter_cache = cached
        return cached

    def descriptor_signature(self, policy: MaceDescriptorPolicy) -> MaceDescriptorSignature:
        return self._descriptor_adapter().signature(policy)

    def calibrate_batch_capacity(
        self,
        atoms_samples: Sequence[Any],
        policy: MaceDescriptorPolicy,
        *,
        maximum_batch_size: int,
        device_budget_bytes: int | None = None,
        workload_mode: MaceBatchWorkloadMode | str = MaceBatchWorkloadMode.DESCRIPTOR_ONLY,
        max_device_fraction: float = 0.80,
        reserve_bytes: int = 4 * 1024**3,
        throughput_tolerance_fraction: float = 0.05,
        stress_sample_count: int = 4,
    ) -> MaceBatchCapacityCalibration:
        """Calibrate DATA6 batching against the actual production workload.

        CUDA probes record allocator-resident and driver-global memory, then the
        provider performs one deterministic cleanup and re-clamps the selected
        batch against the fresh post-cleanup memory budget.  CPU runs retain a
        batch-one fallback and serve only as control-plane qualification.
        """

        samples = tuple(atoms_samples)
        if not samples:
            raise TrainingDataInputError("MACE batch calibration requires at least one structure.")
        mode = MaceBatchWorkloadMode(workload_mode)
        maximum = max(1, int(maximum_batch_size))
        if not (0.0 < float(max_device_fraction) <= 1.0):
            raise TrainingDataInputError("max_device_fraction must lie in (0, 1].")
        if int(reserve_bytes) < 0:
            raise TrainingDataInputError("reserve_bytes must be nonnegative.")
        if not (0.0 <= float(throughput_tolerance_fraction) < 1.0):
            raise TrainingDataInputError("throughput_tolerance_fraction must lie in [0, 1).")
        stress_count = max(1, min(int(stress_sample_count), len(samples)))
        signature = self.descriptor_signature(policy)

        def atoms_digest(atoms: Any) -> str:
            numbers = np.ascontiguousarray(np.asarray(atoms.numbers, dtype="<i4"))
            positions = np.ascontiguousarray(np.asarray(atoms.positions, dtype="<f8"))
            cell = np.ascontiguousarray(np.asarray(atoms.cell.array, dtype="<f8"))
            pbc = np.ascontiguousarray(np.asarray(atoms.pbc, dtype=np.uint8))
            h = hashlib.sha256()
            h.update(b"mdstats.mace-batch-calibration-frame.v1\0")
            for value in (numbers, positions, cell, pbc):
                h.update(value.dtype.str.encode("ascii")); h.update(b"\0")
                h.update(repr(tuple(int(v) for v in value.shape)).encode("ascii")); h.update(b"\0")
                h.update(memoryview(value).cast("B"))
            return h.hexdigest()

        # Rank candidate calibration structures by realized graph footprint first,
        # then atom count and immutable geometry identity.  This is deterministic
        # and stress-oriented rather than "first four frames" sampling.
        ranked: list[tuple[int, int, str, Any]] = []
        for atoms in samples:
            identity = atoms_digest(atoms)
            graph_bytes = 1
            try:
                graph, _ = self._native_batch_cpu((atoms,))
                graph_bytes = max(1, _graph_tensor_bytes(graph))
                del graph
            except Exception:
                graph_bytes = max(1, len(atoms))
            ranked.append((int(graph_bytes), int(len(atoms)), identity, atoms))
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        stress = tuple(item[3] for item in ranked[:stress_count])
        stress_digests = tuple(item[2] for item in ranked[:stress_count])

        descriptor_bytes_per_structure = max(
            len(atoms) * signature.returned_per_atom_dimension * np.dtype(policy.output_dtype).itemsize
            for atoms in stress
        )
        graph_bytes_per_structure = max(1, max(item[0] for item in ranked[:stress_count]))
        # Persistence can retain descriptors and predictions concurrently with the
        # next CPU graph.  Serialized prediction arrays are canonical float64, so
        # account for one energy scalar, per-atom forces, and a full 3x3 stress.
        max_atoms_per_structure = max(int(len(atoms)) for atoms in stress)
        prediction_bytes_per_structure = 8 + max_atoms_per_structure * 3 * 8 + 9 * 8

        try:
            import torch
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE batch calibration requires torch.") from exc

        device = str(getattr(self._calculator, "device", "cpu"))
        is_cuda = device.startswith("cuda") and torch.cuda.is_available()
        if is_cuda:
            probe_sizes: list[int] = []
            value = 1
            while value < maximum:
                probe_sizes.append(value)
                value *= 2
            probe_sizes.append(maximum)
            probe_sizes = sorted(set(probe_sizes))
        else:
            probe_sizes = [1]

        probes: list[MaceBatchCapacityProbe] = []
        peak_per_structure: int | None = None

        def run_workload(batch_atoms: Sequence[Any]) -> None:
            if mode is MaceBatchWorkloadMode.DESCRIPTOR_ONLY:
                result = self.get_descriptors_batch(batch_atoms, policy)
                if len(result) != len(batch_atoms):
                    raise TrainingDataInputError("Descriptor calibration returned an incomplete batch.")
            elif mode is MaceBatchWorkloadMode.PREDICTION_ONLY:
                result = self.predict_batch(batch_atoms)
                if len(result) != len(batch_atoms):
                    raise TrainingDataInputError("Prediction calibration returned an incomplete batch.")
            else:
                descriptors, predictions = self.evaluate_batch(batch_atoms, policy)
                if len(descriptors) != len(batch_atoms) or len(predictions) != len(batch_atoms):
                    raise TrainingDataInputError("Combined calibration returned an incomplete batch.")

        for batch_size in probe_sizes:
            batch_atoms = tuple(stress[index % len(stress)] for index in range(batch_size))
            baseline_allocated = baseline_reserved = None
            free_before = total_bytes = None
            if is_cuda:
                torch.cuda.synchronize()
                baseline_allocated = int(torch.cuda.memory_allocated(device))
                baseline_reserved = int(torch.cuda.memory_reserved(device))
                free_before, total_bytes = (int(v) for v in torch.cuda.mem_get_info(device))
                torch.cuda.reset_peak_memory_stats(device)
            started = time.perf_counter()
            success = False
            oom = False
            try:
                run_workload(batch_atoms)
                success = True
            except RuntimeError as exc:
                text = str(exc).lower()
                if is_cuda and ("out of memory" in text or ("cuda" in text and "memory" in text)):
                    oom = True
                else:
                    raise
            if is_cuda:
                torch.cuda.synchronize()
            elapsed = max(0.0, time.perf_counter() - started)
            post_allocated = post_reserved = peak_allocated = peak_reserved = None
            free_after = None
            if is_cuda:
                peak_allocated = int(torch.cuda.max_memory_allocated(device))
                peak_reserved = int(torch.cuda.max_memory_reserved(device))
                post_allocated = int(torch.cuda.memory_allocated(device))
                post_reserved = int(torch.cuda.memory_reserved(device))
                free_after, total_after = (int(v) for v in torch.cuda.mem_get_info(device))
                if total_bytes is None:
                    total_bytes = total_after
                incremental = max(1, peak_allocated - int(baseline_allocated or 0))
                per_structure = int(np.ceil(incremental / float(batch_size)))
                peak_per_structure = max(peak_per_structure or 0, per_structure)
            probes.append(
                MaceBatchCapacityProbe(
                    batch_size=batch_size,
                    elapsed_seconds=elapsed,
                    structures_per_second=(0.0 if not success or elapsed <= 0.0 else batch_size / elapsed),
                    success=success,
                    oom=oom,
                    baseline_allocated_bytes=baseline_allocated,
                    baseline_reserved_bytes=baseline_reserved,
                    peak_allocated_bytes=peak_allocated,
                    peak_reserved_bytes=peak_reserved,
                    post_allocated_bytes=post_allocated,
                    post_reserved_bytes=post_reserved,
                    driver_free_before_bytes=free_before,
                    driver_free_after_bytes=free_after,
                    driver_total_bytes=total_bytes,
                )
            )
            if oom:
                break

        successful_records = [probe for probe in probes if probe.success]
        if not successful_records:
            raise TrainingDataInputError("MACE batch-capacity calibration could not evaluate even one structure.")

        # One-time deterministic cleanup before production.  This releases probe-
        # local outputs/graphs and resets the caching allocator high-water state;
        # normal production batches do not repeatedly empty the cache.
        gc.collect()
        post_cleanup_allocated = post_cleanup_reserved = None
        post_cleanup_free = post_cleanup_total = None
        if is_cuda:
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            post_cleanup_allocated = int(torch.cuda.memory_allocated(device))
            post_cleanup_reserved = int(torch.cuda.memory_reserved(device))
            post_cleanup_free, post_cleanup_total = (int(v) for v in torch.cuda.mem_get_info(device))

        if not is_cuda:
            recommended = 1
        else:
            safe: list[MaceBatchCapacityProbe] = []
            for probe in successful_records:
                total = probe.driver_total_bytes or post_cleanup_total
                peak_reserved = probe.peak_reserved_bytes
                free_after = probe.driver_free_after_bytes
                if total is None or peak_reserved is None or free_after is None:
                    continue
                if peak_reserved > int(float(max_device_fraction) * total):
                    continue
                if free_after < int(reserve_bytes):
                    continue
                if device_budget_bytes is not None:
                    incremental = max(1, peak_reserved - int(probe.baseline_reserved_bytes or 0))
                    if incremental > int(device_budget_bytes):
                        continue
                safe.append(probe)
            if not safe:
                safe = [min(successful_records, key=lambda probe: probe.batch_size)]
            max_throughput = max(probe.structures_per_second for probe in safe)
            floor = max_throughput * (1.0 - float(throughput_tolerance_fraction))
            near_best = [probe for probe in safe if probe.structures_per_second >= floor]
            recommended = min(probe.batch_size for probe in near_best)

            # Fresh post-cleanup clamp.  The stricter of absolute free-memory
            # reserve, fractional process occupancy, and configured device budget
            # determines how much *incremental* memory production may consume.
            if post_cleanup_total is not None and post_cleanup_free is not None:
                absolute_incremental = max(0, int(post_cleanup_free) - int(reserve_bytes))
                fractional_incremental = max(
                    0,
                    int(float(max_device_fraction) * post_cleanup_total)
                    - int(post_cleanup_reserved or 0),
                )
                incremental_budget = min(absolute_incremental, fractional_incremental)
                if device_budget_bytes is not None:
                    incremental_budget = min(incremental_budget, int(device_budget_bytes))
                selected = next(probe for probe in safe if probe.batch_size == recommended)
                selected_incremental = max(
                    1, int(selected.peak_reserved_bytes or 1) - int(selected.baseline_reserved_bytes or 0)
                )
                per_structure_reserved = max(1, int(np.ceil(selected_incremental / float(selected.batch_size))))
                fresh_cap = max(1, incremental_budget // per_structure_reserved)
                allowed = [probe.batch_size for probe in safe if probe.batch_size <= fresh_cap]
                if allowed:
                    recommended = min(recommended, max(allowed))
                else:
                    recommended = min(probe.batch_size for probe in safe)

        successful = tuple(probe.batch_size for probe in probes if probe.success)
        return MaceBatchCapacityCalibration(
            descriptor_signature_digest=signature.content_digest,
            checkpoint_identity_digest=self._checkpoint_identity.content_digest,
            device=device,
            workload_mode=mode,
            requested_max_batch_size=maximum,
            calibration_frame_digests=stress_digests,
            probed_batch_sizes=tuple(probe.batch_size for probe in probes),
            successful_batch_sizes=successful,
            recommended_batch_size=int(recommended),
            descriptor_bytes_per_structure=int(descriptor_bytes_per_structure),
            graph_bytes_per_structure=int(graph_bytes_per_structure),
            prediction_bytes_per_structure=int(prediction_bytes_per_structure),
            peak_device_bytes_per_structure=peak_per_structure,
            device_budget_bytes=device_budget_bytes,
            probes=tuple(probes),
            max_device_fraction=float(max_device_fraction),
            reserve_bytes=int(reserve_bytes),
            throughput_tolerance_fraction=float(throughput_tolerance_fraction),
            post_cleanup_allocated_bytes=post_cleanup_allocated,
            post_cleanup_reserved_bytes=post_cleanup_reserved,
            post_cleanup_free_bytes=post_cleanup_free,
            post_cleanup_total_bytes=post_cleanup_total,
        )

    def set_head(self, head: str | None) -> None:
        """Select a MACE head without reloading the checkpoint weights."""

        self._raise_if_poisoned()
        if head is None:
            return
        requested = str(head)
        if self._checkpoint_identity.foundation_bound:
            frozen = str(self._checkpoint_identity.foundation_head)
            if requested != frozen:
                raise TrainingDataInputError(
                    f"Foundation-bound provider is frozen to head {frozen!r}; cannot switch to {requested!r}."
                )
        available = tuple(str(value) for value in getattr(
            self._calculator, "available_heads", ()
        ))
        if available and requested not in available:
            raise TrainingDataInputError(
                f"MACE checkpoint does not provide head {requested!r}."
            )
        if not hasattr(self._calculator, "head"):
            raise TrainingDataInputError(
                "MACE calculator does not expose a selectable head."
            )
        self._calculator.head = requested

    def load_compatible_model_state(
        self,
        model_path: str | Path,
        *,
        expected_sha256: str | None = None,
    ) -> ModelCheckpointIdentity:
        """Load one canonically same-architecture model into this validated shell.

        PERF-P5 keeps this optimization deliberately narrow: it is enabled only
        for providers constructed from an unaccelerated deployable MACE model,
        never for canonical source-foundation providers and never for CuEq/OEq/
        compiled calculator shells.

        R17A requires proving equality of the complete forward/graph-affecting
        execution architecture -- not merely state-key/shape/dtype structure --
        before any retained shell is mutated (see
        ``_mace_model_execution_architecture_descriptor``).  State-structure
        equality remains a secondary mutation-safety guard applied after that
        primary architecture-identity gate.  The replacement itself is a
        transaction (R17A 3.5): any failure after mutation has begun poisons
        this shell so it can never be returned to inference, and the caller
        must reconstruct a fresh provider from an authenticated checkpoint.
        """

        self._raise_if_poisoned()
        if not self._state_hot_swap_qualified or self._checkpoint_identity.foundation_bound:
            raise MaceModelStateCompatibilityError(
                "This MACE provider is not qualified for checkpoint state hot swapping."
            )
        path = Path(model_path).resolve()
        if not path.is_file():
            raise TrainingDataInputError(f"MACE checkpoint does not exist: {path!s}.")
        # Step 1: authenticate the incoming checkpoint under the existing
        # checkpoint authority path before anything is derived from it.
        observed_sha = _sha256_file(path)
        if expected_sha256 is not None and observed_sha != validate_digest(
            expected_sha256, name="expected_sha256"
        ):
            raise TrainingDataInputError("Hot-swap model bytes differ from the expected checkpoint identity.")
        try:
            import torch
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE checkpoint hot swapping requires torch.") from exc
        try:
            source = torch.load(path, map_location="cpu", weights_only=False)
        except TypeError:  # pragma: no cover - older torch
            source = torch.load(path, map_location="cpu")
        if isinstance(source, (tuple, list)):
            if len(source) != 1:
                raise MaceModelStateCompatibilityError("Checkpoint hot swapping does not support model ensembles.")
            source = source[0]
        if not hasattr(source, "state_dict"):
            raise MaceModelStateCompatibilityError("Hot-swap source is not a deployable torch model.")
        target_models = getattr(self._calculator, "models", None)
        if not isinstance(target_models, (tuple, list)) or len(target_models) != 1:
            raise MaceModelStateCompatibilityError("Checkpoint hot swapping requires exactly one calculator model.")
        target = target_models[0]

        # Step 2/3: derive the canonical execution-architecture descriptor for
        # the incoming checkpoint (loaded in isolation, target not yet
        # touched) and for the currently retained shell.
        incoming_descriptor = _mace_model_execution_architecture_descriptor(source)
        retained_descriptor = _mace_model_execution_architecture_descriptor(target)
        incoming_architecture_digest = digest(incoming_descriptor)
        retained_architecture_digest = digest(retained_descriptor)

        # Step 4: compare the complete canonical execution identity.  Any
        # difference -- including a cutoff/`r_max` difference invisible to
        # state-key/shape/dtype structure -- rejects the hot swap outright.
        # Unknown/unprovable compatibility must never fail open.
        if incoming_architecture_digest != retained_architecture_digest:
            raise MaceModelStateCompatibilityError(
                "Checkpoint hot-swap execution-architecture identity differs from the "
                "validated model shell; safe reconstruction is required."
            )

        # Step 5: existing exact model-class/state-key/shape/dtype guards
        # remain as a secondary mutation-safety guard.
        source_type = f"{type(source).__module__}.{type(source).__qualname__}"
        target_type = f"{type(target).__module__}.{type(target).__qualname__}"
        if source_type != target_type:
            raise MaceModelStateCompatibilityError(
                f"Checkpoint hot-swap model class mismatch: {source_type!r} != {target_type!r}."
            )
        source_state = source.state_dict()
        target_state = target.state_dict()
        if set(source_state) != set(target_state):
            raise MaceModelStateCompatibilityError("Checkpoint hot-swap state keys differ from the validated model shell.")
        for key in sorted(source_state):
            incoming = source_state[key]
            resident = target_state[key]
            if tuple(incoming.shape) != tuple(resident.shape):
                raise MaceModelStateCompatibilityError(f"Checkpoint hot-swap shape mismatch for state key {key!r}.")
            if incoming.dtype != resident.dtype:
                raise MaceModelStateCompatibilityError(f"Checkpoint hot-swap dtype mismatch for state key {key!r}.")

        # Step 6: the mutation transaction.  No concurrent inference may
        # observe the shell during replacement; this provider is single-owner
        # for the duration of one hot-swap call.  Any failure from here on
        # poisons the shell rather than returning a partially mutated one.
        try:
            target.load_state_dict(source_state, strict=True)
            post_swap_digest = digest(_mace_model_execution_architecture_descriptor(target))
            if post_swap_digest != incoming_architecture_digest:
                raise MaceModelStateCompatibilityError(
                    "Post-swap execution-architecture invariant failed: the mutated "
                    "shell no longer matches the incoming checkpoint architecture."
                )
        except Exception as exc:
            self._poisoned = True
            self._poison_reason = str(exc)
            self._descriptor_adapter_cache = None
            self._runtime_architecture_digest_cache = None
            raise MaceModelStateCompatibilityError(
                "Checkpoint hot-swap transaction failed after mutation began; the "
                "shell is poisoned and must be discarded and reconstructed from an "
                f"authenticated checkpoint: {exc}"
            ) from exc

        self._checkpoint_identity = replace(
            self._checkpoint_identity,
            checkpoint_locator=str(path),
            checkpoint_sha256=observed_sha,
        )
        self._descriptor_adapter_cache = None
        # Same-architecture weight swaps deliberately exclude weight values
        # from the digest, so the cached digest remains valid; clear it
        # anyway so any future divergence is recomputed rather than trusted.
        self._runtime_architecture_digest_cache = None
        return self._checkpoint_identity

    @classmethod
    def from_calculator(
        cls,
        calculator: Any,
        *,
        checkpoint_identity: ModelCheckpointIdentity,
    ) -> "MaceCalculatorProvider":
        return cls(calculator, checkpoint_identity)

    @classmethod
    def from_authenticated_model(
        cls,
        model: Any,
        *,
        checkpoint_locator: str | Path,
        checkpoint_sha256: str,
        device: str,
        default_dtype: str,
        supported_atomic_numbers: Sequence[int] = (),
        requested_atomic_numbers: Sequence[int] = (),
        allow_forward_override: bool = False,
        calculator_kwargs: Mapping[str, Any] | None = None,
    ) -> "MaceCalculatorProvider":
        """Construct one provider around an already authenticated model shell.

        The model instance passed here is the sole state owner used for both
        live/EMA authentication and subsequent prediction.  Full MACE models
        are wrapped by the real ``MACECalculator``.  The only non-MACE path is
        the explicit bounded forward-override shell described above; it fails
        closed when no override is supplied.
        """

        if not hasattr(model, "named_parameters") or not hasattr(model, "named_modules"):
            raise TrainingDataInputError(
                "Authenticated provider model must expose named_parameters() and named_modules()."
            )
        requested_device = str(device)
        if requested_device.startswith("cuda"):
            try:
                import torch
            except ModuleNotFoundError as exc:  # pragma: no cover - provider requires torch
                raise TrainingDataInputError(
                    "CUDA provider realization requires torch."
                ) from exc
            if not bool(torch.cuda.is_available()):
                raise TrainingDataInputError(
                    "Authenticated provider requested CUDA, but CUDA is unavailable on this host."
                )
        active_kwargs = dict(calculator_kwargs or {})
        model_is_mace = all(
            hasattr(model, name)
            for name in ("r_max", "atomic_numbers", "interactions", "products")
        )
        if model_is_mace:
            try:
                from mace.calculators import MACECalculator
            except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
                raise TrainingDataInputError(
                    "Authenticated MACE provider construction requires mace-torch."
                ) from exc
            try:
                calculator = MACECalculator(
                    models=[model],
                    device=requested_device,
                    default_dtype=str(default_dtype),
                    **active_kwargs,
                )
            except (AttributeError, RuntimeError, TypeError, ValueError) as exc:
                raise TrainingDataInputError(
                    "Authenticated MACE model cannot be realized by the shared calculator owner."
                ) from exc
        else:
            if not allow_forward_override:
                raise TrainingDataInputError(
                    "A deployable MACE model is required when no bounded forward override is supplied."
                )
            calculator = _AuthenticatedParameterCalculator(
                model, device=requested_device, default_dtype=str(default_dtype)
            )

        try:
            import mace

            model_version = str(getattr(mace, "__version__", "unknown"))
        except ModuleNotFoundError:  # pragma: no cover - calculator construction already imports MACE
            model_version = "unknown"
        identity = ModelCheckpointIdentity(
            model_family="MACE",
            checkpoint_locator=str(checkpoint_locator),
            checkpoint_sha256=validate_digest(
                checkpoint_sha256, name="checkpoint_sha256"
            ),
            calculator_class=f"{type(calculator).__module__}.{type(calculator).__qualname__}",
            model_version=model_version,
            supported_atomic_numbers=tuple(int(value) for value in supported_atomic_numbers),
            model_supported_atomic_numbers=tuple(int(value) for value in supported_atomic_numbers),
            requested_atomic_numbers=tuple(int(value) for value in requested_atomic_numbers),
            device=requested_device,
            default_dtype=str(default_dtype),
            metadata=(
                ("authenticated_state_owner", "provider_model"),
                ("forward_override_allowed", str(bool(allow_forward_override)).lower()),
                ("acceleration_backend", "eager"),
            ),
        )
        return cls(calculator, identity)

    @classmethod
    def from_authenticated_parameter_state(
        cls,
        parameters: Sequence[Any],
        *,
        checkpoint_locator: str | Path,
        checkpoint_sha256: str,
        device: str,
        default_dtype: str,
        supported_atomic_numbers: Sequence[int] = (),
        requested_atomic_numbers: Sequence[int] = (),
        allow_forward_override: bool = False,
    ) -> "MaceCalculatorProvider":
        """Build a provider shell and authenticate a parameter sequence once."""

        import torch

        values = tuple(parameters)
        if not values:
            raise TrainingDataInputError(
                "Authenticated provider state requires at least one parameter."
            )
        if any(not torch.is_tensor(value) for value in values):
            raise TrainingDataInputError(
                "Authenticated provider parameters must be tensors."
            )
        model = _AuthenticatedParameterShell(values)
        provider = cls.from_authenticated_model(
            model,
            checkpoint_locator=checkpoint_locator,
            checkpoint_sha256=checkpoint_sha256,
            device=device,
            default_dtype=default_dtype,
            supported_atomic_numbers=supported_atomic_numbers,
            requested_atomic_numbers=requested_atomic_numbers,
            allow_forward_override=allow_forward_override,
        )
        provider.load_authenticated_parameter_state(values, state_name="live")
        return provider

    @property
    def model(self) -> Any:
        self._raise_if_poisoned()
        models = getattr(self._calculator, "models", None)
        if not isinstance(models, (tuple, list)) or len(models) != 1:
            raise TrainingDataInputError(
                "Authenticated MACE provider must own exactly one model."
            )
        return models[0]

    @property
    def device(self) -> str:
        self._raise_if_poisoned()
        return str(getattr(self._calculator, "device", self._checkpoint_identity.device))

    @property
    def default_dtype(self) -> str:
        self._raise_if_poisoned()
        return str(
            getattr(self._calculator, "default_dtype", self._checkpoint_identity.default_dtype)
        )

    @property
    def backend_policy(self) -> str:
        self._raise_if_poisoned()
        calculator = self._calculator
        if bool(getattr(calculator, "use_compile", False)):
            return "compile"
        if bool(getattr(calculator, "_enable_cueq", False)):
            return "cueq"
        if bool(getattr(calculator, "_enable_oeq", False)):
            return "oeq"
        return "eager"

    def load_authenticated_parameter_state(
        self,
        values: Sequence[Any] | Mapping[str, Any],
        *,
        state_name: str,
    ) -> tuple[Any, ...]:
        """Validate and apply one complete ordered state to the provider model.

        All compatibility checks happen before mutation.  A mutation failure
        poisons the provider so a partially changed shell cannot reach forward.
        """

        self._raise_if_poisoned()
        import torch

        named = tuple(self.model.named_parameters())
        if not named:
            raise MaceModelStateCompatibilityError(
                "Authenticated provider model has no parameters."
            )
        if isinstance(values, Mapping):
            observed_names = tuple(str(name) for name in values.keys())
            expected_names = tuple(str(name) for name, _ in named)
            if observed_names != expected_names:
                raise MaceModelStateCompatibilityError(
                    f"{state_name} parameter keys/order differ from the provider model."
                )
            incoming = tuple(values[name] for name, _ in named)
        else:
            incoming = tuple(values)
        if len(incoming) != len(named):
            raise MaceModelStateCompatibilityError(
                f"{state_name} parameter cardinality differs from the provider model."
            )
        for index, ((name, resident), source) in enumerate(zip(named, incoming, strict=True)):
            if not torch.is_tensor(source):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} parameter {name!r} at index {index} is not a tensor."
                )
            if tuple(source.shape) != tuple(resident.shape):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} parameter {name!r} shape differs from the provider model."
                )
            if source.dtype != resident.dtype:
                raise MaceModelStateCompatibilityError(
                    f"{state_name} parameter {name!r} dtype differs from the provider model."
                )
            if not bool(torch.isfinite(source.detach()).all().item()):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} parameter {name!r} contains non-finite values."
                )
        try:
            with torch.no_grad():
                for (_, resident), source in zip(named, incoming, strict=True):
                    resident.copy_(source.detach().to(device=resident.device))
        except Exception as exc:
            self._poisoned = True
            self._poison_reason = str(exc)
            self._descriptor_adapter_cache = None
            self._runtime_architecture_digest_cache = None
            raise MaceModelStateCompatibilityError(
                f"{state_name} parameter application failed; the provider shell is poisoned."
            ) from exc
        self._descriptor_adapter_cache = None
        self._runtime_architecture_digest_cache = None
        return tuple(resident for _, resident in named)

    def load_authenticated_model_state_dict(
        self,
        values: Mapping[str, Any],
        *,
        state_name: str = "checkpoint model state",
    ) -> tuple[Any, ...]:
        """Strictly authenticate and apply one complete MACE ``state_dict``.

        MACE 0.3.16 TRAIN2 checkpoints store ``checkpoint["model"]`` as this
        mapping, not as a deployable model.  The model shell is already owned
        by this provider and is never inferred from the mapping.  Validation
        is completed before mutation; a failed mutation permanently poisons
        the provider just like the existing parameter-state transaction.
        """

        self._raise_if_poisoned()
        import torch

        if not isinstance(values, Mapping) or not values:
            raise MaceModelStateCompatibilityError(
                f"{state_name} must be a non-empty state-dict mapping."
            )
        resident_state = self.model.state_dict()
        expected_names = tuple(str(name) for name in resident_state.keys())
        observed_names = tuple(str(name) for name in values.keys())
        if observed_names != expected_names:
            raise MaceModelStateCompatibilityError(
                f"{state_name} keys/order differ from the reconstructed provider model."
            )
        for name, resident in resident_state.items():
            source = values[name]
            if not torch.is_tensor(source):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} entry {name!r} is not a tensor."
                )
            if tuple(source.shape) != tuple(resident.shape):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} entry {name!r} shape differs from the provider model."
                )
            if source.dtype != resident.dtype:
                raise MaceModelStateCompatibilityError(
                    f"{state_name} entry {name!r} dtype differs from the provider model."
                )
            if torch.is_floating_point(source) and not bool(
                torch.isfinite(source.detach()).all().item()
            ):
                raise MaceModelStateCompatibilityError(
                    f"{state_name} entry {name!r} contains non-finite values."
                )
        try:
            self.model.load_state_dict(dict(values), strict=True)
        except Exception as exc:
            self._poisoned = True
            self._poison_reason = str(exc)
            self._descriptor_adapter_cache = None
            self._runtime_architecture_digest_cache = None
            raise MaceModelStateCompatibilityError(
                f"{state_name} application failed; the provider shell is poisoned."
            ) from exc
        self._descriptor_adapter_cache = None
        self._runtime_architecture_digest_cache = None
        return tuple(self.model.state_dict()[name] for name in expected_names)

    @classmethod
    @mace_runtime_warning_handled("MACE descriptor calculator construction")
    def from_model_path(
        cls,
        model_path: str | Path,
        *,
        device: str = "cpu",
        default_dtype: str = "float64",
        critical_precision_policy: MaceCriticalPrecisionPolicy | None = None,
        enforce_critical_fp64: bool = True,
        model_family: str = "MACE",
        supported_atomic_numbers: Sequence[int] = (),
        requested_atomic_numbers: Sequence[int] = (),
        foundation_potential_identity: Any | None = None,
        foundation_inference_identity: Any | None = None,
        **calculator_kwargs: Any,
    ) -> "MaceCalculatorProvider":
        path = Path(model_path)
        if not path.is_file():
            raise TrainingDataInputError(f"MACE checkpoint does not exist: {path!s}.")
        try:
            import mace
            import mace.calculators.mace as mace_calculator_module
            from mace.calculators import MACECalculator
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise TrainingDataInputError(
                "MACE descriptor extraction requires the optional mace-torch package."
            ) from exc
        active_critical_policy = (
            MaceCriticalPrecisionPolicy()
            if critical_precision_policy is None
            else critical_precision_policy
        )
        if enforce_critical_fp64:
            activate_mace_critical_precision_policy(active_critical_policy)
        if foundation_potential_identity is not None:
            expected_sha = str(getattr(foundation_potential_identity, "sha256", ""))
            if expected_sha != _sha256_file(path):
                raise TrainingDataInputError("Foundation checkpoint bytes do not match the supplied scientific identity.")
            resolved_head = str(getattr(foundation_potential_identity, "foundation_head", "")).strip()
            if not resolved_head:
                raise TrainingDataInputError("Foundation scientific identity has no resolved head.")
            existing_head = calculator_kwargs.get("head")
            if existing_head not in (None, "", resolved_head):
                raise TrainingDataInputError("Calculator head conflicts with the supplied foundation scientific identity.")
            calculator_kwargs["head"] = resolved_head
            if foundation_inference_identity is None:
                raise TrainingDataInputError("Foundation-backed provider requires a FoundationInferenceIdentity.")
            expected_potential = str(getattr(foundation_inference_identity, "foundation_potential_digest", ""))
            if expected_potential != str(getattr(foundation_potential_identity, "canonical_content_digest", "")):
                raise TrainingDataInputError("Foundation inference identity does not bind the supplied potential identity.")

        if any(
            (
                bool(calculator_kwargs.get("enable_cueq", False)),
                bool(calculator_kwargs.get("enable_oeq", False)),
                calculator_kwargs.get("compile_mode") is not None,
            )
        ):
            _install_thread_safe_mace_accelerator_conversion(mace_calculator_module)
        try:
            calculator = MACECalculator(
                model_paths=str(path),
                device=device,
                default_dtype=default_dtype,
                **calculator_kwargs,
            )
        except AttributeError as exc:
            if "'dict' object has no attribute 'to'" in str(exc):
                raise TrainingDataInputError(
                    "MACECalculator received a raw training checkpoint dictionary. "
                    "Reconstruct a deployable whole-model serialization from the "
                    "checkpoint and immutable training config before inference."
                ) from exc
            raise
        model_numbers = tuple(int(v) for v in supported_atomic_numbers)
        if foundation_potential_identity is not None:
            model_numbers = tuple(int(v) for v in getattr(foundation_potential_identity, "model_atomic_numbers", ()))
            model_family = str(getattr(foundation_potential_identity, "model_family", model_family))
        identity = ModelCheckpointIdentity(
            model_family=model_family,
            checkpoint_locator=str(path),
            checkpoint_sha256=_sha256_file(path),
            calculator_class=f"{type(calculator).__module__}.{type(calculator).__qualname__}",
            model_version=str(getattr(mace, "__version__", "unknown")),
            supported_atomic_numbers=model_numbers,
            model_supported_atomic_numbers=model_numbers,
            requested_atomic_numbers=tuple(int(v) for v in requested_atomic_numbers),
            foundation_potential_digest=(None if foundation_potential_identity is None else str(foundation_potential_identity.canonical_content_digest)),
            foundation_inference_digest=(None if foundation_inference_identity is None else str(foundation_inference_identity.content_digest)),
            foundation_head=(None if foundation_potential_identity is None else str(foundation_potential_identity.foundation_head)),
            device=device,
            default_dtype=default_dtype,
            metadata=(
                ("critical_fp64_enforced", str(bool(enforce_critical_fp64)).lower()),
                ("critical_precision_policy_digest", active_critical_policy.policy_digest),
                ("energy_accumulation_dtype", active_critical_policy.energy_accumulation_dtype),
                ("virial_accumulation_dtype", active_critical_policy.virial_accumulation_dtype),
                ("observable_output_dtype", active_critical_policy.observable_output_dtype),
                ("md_state_dtype", active_critical_policy.md_state_dtype),
                ("training_force_jacobian_dtype", active_critical_policy.training_force_jacobian_dtype),
                ("tf32_allowed", str(active_critical_policy.allow_tf32).lower()),
                ("acceleration_backend", "cueq" if bool(calculator_kwargs.get("enable_cueq", False)) else "e3nn"),
                ("enable_cueq", str(bool(calculator_kwargs.get("enable_cueq", False))).lower()),
            ),
        )
        result = cls(calculator, identity)
        result._state_hot_swap_qualified = bool(
            foundation_potential_identity is None
            and not bool(calculator_kwargs.get("enable_cueq", False))
            and not bool(calculator_kwargs.get("enable_oeq", False))
            and calculator_kwargs.get("compile_mode") is None
        )
        return result

    def get_descriptors(self, atoms: Any, policy: MaceDescriptorPolicy) -> np.ndarray:
        self._raise_if_poisoned()
        kwargs: dict[str, Any] = {"invariants_only": policy.invariants_only}
        if policy.num_layers is not None:
            kwargs["num_layers"] = policy.num_layers
        try:
            raw = self._calculator.get_descriptors(atoms, **kwargs)
        except TypeError as exc:
            raise TrainingDataInputError(
                "MACE calculator descriptor signature is incompatible with the locked adapter."
            ) from exc
        if self._native_batch_supported():
            return self._descriptor_adapter().validate_array(
                np.asarray(raw), atom_count=len(atoms), policy=policy
            )
        descriptor = np.asarray(raw, dtype=np.dtype(policy.output_dtype))
        if descriptor.ndim != 2 or descriptor.shape[0] != len(atoms):
            raise TrainingDataInputError(
                "MACE descriptors must have shape (n_atoms, n_descriptors)."
            )
        if descriptor.shape[1] <= 0 or np.any(~np.isfinite(descriptor)):
            raise TrainingDataInputError("MACE descriptors must be finite and non-empty.")
        return np.ascontiguousarray(descriptor)

    def predict(self, atoms: Any) -> AtomicModelPrediction:
        self._raise_if_poisoned()
        local = atoms.copy()
        local.calc = self._calculator
        energy = float(local.get_potential_energy())
        forces = np.asarray(local.get_forces(), dtype=np.float64)
        stress = None
        try:
            stress = np.asarray(local.get_stress(voigt=False), dtype=np.float64)
        except (NotImplementedError, RuntimeError, KeyError):
            stress = None
        return AtomicModelPrediction(energy, forces, stress)

    def _native_batch_supported(self) -> bool:
        calc = self._calculator
        return bool(
            getattr(calc, "model_type", None) == "MACE"
            and hasattr(calc, "models")
            and hasattr(calc, "z_table")
            and hasattr(calc, "r_max")
            and hasattr(calc, "device")
            and not bool(getattr(calc, "use_compile", False))
            and int(getattr(calc, "pad_num_atoms", 0)) == 0
            and int(getattr(calc, "pad_num_edges", 0)) == 0
        )

    def _native_batch_cpu(
        self,
        atoms_batch: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
        graph_cache_directory: str | Path | None = None,
    ) -> tuple[Any, np.ndarray]:
        """Construct/reuse one native MACE graph batch on CPU only."""
        from .inference_parallel import report_inference_worker_phase

        if not atoms_batch:
            raise TrainingDataInputError("MACE batch must contain at least one structure.")
        if geometry_identities is not None and len(geometry_identities) != len(atoms_batch):
            raise TrainingDataInputError("Monitor graph identity count mismatch.")
        if not self._native_batch_supported():
            raise TrainingDataInputError("This MACE calculator cannot use the qualified native batch path.")
        try:
            from mace import data as mace_data
            from mace.tools import torch_geometric, torch_tools
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE native batching requires mace-torch.") from exc
        calc = self._calculator
        calc.arrays_keys.update({calc.charges_key: "charges"})

        stable_token = None
        stable_policy_digest = None
        if geometry_identities is not None:
            stable_token, stable_policy_digest = _mace_monitor_graph_token(calc, geometry_identities)
            cached = _monitor_graph_memory_get_cpu(stable_token)
            if cached is not None:
                report_inference_worker_phase("graph cache hit: memory")
                return cached
            cached = _load_persistent_monitor_graph_cpu(
                graph_cache_directory, token=stable_token,
                policy_digest=stable_policy_digest, geometry_identities=geometry_identities,
            )
            if cached is not None:
                report_inference_worker_phase("graph cache hit: persistent")
                return cached
        else:
            cached = _cached_graph_batch_cpu(calc, atoms_batch)
            if cached is not None:
                report_inference_worker_phase("graph cache hit: calculator-local")
                return cached

        lock = _monitor_graph_key_lock(stable_token) if stable_token is not None else _MACE_GRAPH_BATCH_CACHE_LOCK
        with lock:
            if stable_token is not None:
                cached = _monitor_graph_memory_get_cpu(stable_token)
                if cached is None:
                    cached = _load_persistent_monitor_graph_cpu(
                        graph_cache_directory, token=stable_token,
                        policy_digest=stable_policy_digest or "",
                        geometry_identities=geometry_identities or (),
                    )
                if cached is not None:
                    report_inference_worker_phase("graph cache hit: synchronized")
                    return cached
            report_inference_worker_phase("graph cache miss: building CPU monitor graphs")
            keyspec = mace_data.KeySpecification(
                info_keys=calc.info_keys, arrays_keys=calc.arrays_keys
            )
            graphs = []
            counts = []
            with torch_tools.default_dtype(calc.default_dtype):
                for atoms in atoms_batch:
                    config = mace_data.config_from_atoms(
                        atoms, key_specification=keyspec, head_name=calc.head
                    )
                    graph = mace_data.AtomicData.from_config(
                        config, z_table=calc.z_table, cutoff=calc.r_max,
                        heads=calc.available_heads,
                    )
                    graphs.append(graph)
                    counts.append(len(atoms))
            cpu_batch = torch_geometric.Batch.from_data_list(graphs)
            count_array = np.asarray(counts, dtype=np.int64)
            if stable_token is not None:
                _monitor_graph_memory_store(stable_token, cpu_batch, count_array)
                _write_persistent_monitor_graph(
                    graph_cache_directory, token=stable_token,
                    policy_digest=stable_policy_digest or "",
                    geometry_identities=geometry_identities or (),
                    batch=cpu_batch, counts=count_array,
                )
            else:
                _store_graph_batch(calc, atoms_batch, cpu_batch, count_array)
            return cpu_batch, count_array

    def _native_batch(
        self,
        atoms_batch: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
        graph_cache_directory: str | Path | None = None,
    ) -> tuple[Any, np.ndarray]:
        cpu_batch, counts = self._native_batch_cpu(
            atoms_batch, geometry_identities=geometry_identities,
            graph_cache_directory=graph_cache_directory,
        )
        return cpu_batch.to(self._calculator.device), counts

    def prepare_evaluate_batch(self, atoms_batch: Sequence[Any]) -> tuple[Any, np.ndarray, tuple[int, ...]]:
        """Prepare a derivative-bearing DATA6 batch without touching the model/device."""
        if not self._native_batch_supported():
            raise TrainingDataInputError("Prepared MACE batching requires the qualified native batch path.")
        cpu_batch, counts = self._native_batch_cpu(atoms_batch)
        return cpu_batch, counts, tuple(int(len(atoms)) for atoms in atoms_batch)

    def evaluate_prepared_batch(
        self, prepared: tuple[Any, np.ndarray, tuple[int, ...]], policy: MaceDescriptorPolicy
    ) -> tuple[tuple[np.ndarray, ...], tuple[AtomicModelPrediction, ...]]:
        """Execute a CPU-prepared native graph batch on the configured device."""
        cpu_batch, counts, atom_counts = prepared
        return self._evaluate_native_batch(
            cpu_batch.to(self._calculator.device), counts, atom_counts, policy
        )

    def get_descriptors_batch(
        self, atoms_batch: Sequence[Any], policy: MaceDescriptorPolicy
    ) -> tuple[np.ndarray, ...]:
        """Extract descriptors in one graph batch when MACE 0.3.16 permits it."""

        self._raise_if_poisoned()
        if len(atoms_batch) <= 1 or not self._native_batch_supported():
            return tuple(self.get_descriptors(atoms, policy) for atoms in atoms_batch)
        try:
            import torch
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE descriptor batching dependencies are unavailable.") from exc
        calc = self._calculator
        batch, counts = self._native_batch(atoms_batch)
        if int(getattr(calc, "num_models", len(calc.models))) != 1:
            return tuple(self.get_descriptors(atoms, policy) for atoms in atoms_batch)
        model = calc.models[0]
        adapter = self._descriptor_adapter()
        model_dtype = next(model.parameters()).dtype
        for key in batch.keys:
            value = batch[key]
            if torch.is_tensor(value) and torch.is_floating_point(value):
                batch[key] = value.to(dtype=model_dtype)
        # Descriptor extraction is a forward-only operation.  MACE defaults
        # ``compute_force=True`` and would otherwise call ``torch.autograd.grad``
        # inside this ``no_grad`` scope, which fails on PyTorch 2.x.  Disable
        # every derivative-bearing output explicitly while retaining the
        # low-memory descriptor-only execution contract.
        with torch.no_grad():
            descriptor = model(
                batch.to_dict(),
                training=False,
                compute_force=False,
                compute_virials=False,
                compute_stress=False,
                compute_displacement=False,
                compute_hessian=False,
                compute_edge_forces=False,
                compute_atomic_stresses=False,
            )["node_feats"]
        descriptor = adapter.transform_node_feats(descriptor, policy)
        array = descriptor.detach().cpu().numpy()
        offsets = np.concatenate(([0], np.cumsum(counts)))
        result = []
        for index, atoms in enumerate(atoms_batch):
            selected = adapter.validate_array(
                array[offsets[index]:offsets[index + 1]],
                atom_count=len(atoms),
                policy=policy,
            )
            result.append(selected)
        return tuple(result)

    def _evaluate_native_batch(
        self, batch: Any, counts: np.ndarray, atom_counts: Sequence[int],
        policy: MaceDescriptorPolicy,
    ) -> tuple[tuple[np.ndarray, ...], tuple[AtomicModelPrediction, ...]]:
        try:
            import torch
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("Combined MACE batching dependencies are unavailable.") from exc
        calc = self._calculator
        model = calc.models[0]
        adapter = self._descriptor_adapter()
        model_dtype = next(model.parameters()).dtype
        for key in batch.keys:
            value = batch[key]
            if torch.is_tensor(value) and torch.is_floating_point(value):
                batch[key] = value.to(dtype=model_dtype)
        with torch.enable_grad():
            output = model(
                batch.to_dict(), compute_stress=True, training=False,
                compute_edge_forces=False, compute_atomic_stresses=False,
            )
        descriptor = adapter.transform_node_feats(output["node_feats"], policy)
        descriptor_array = descriptor.detach().cpu().numpy()
        energies_np = output["energy"].detach().cpu().numpy() * float(calc.energy_units_to_eV)
        forces_np = output["forces"].detach().cpu().numpy() * float(
            calc.energy_units_to_eV / calc.length_units_to_A
        )
        stress_tensor = output.get("stress")
        stresses_np = None if stress_tensor is None else stress_tensor.detach().cpu().numpy() * float(
            calc.energy_units_to_eV / calc.length_units_to_A**3
        )
        offsets = np.concatenate(([0], np.cumsum(counts)))
        descriptors: list[np.ndarray] = []
        predictions: list[AtomicModelPrediction] = []
        for index, atom_count in enumerate(atom_counts):
            selected = adapter.validate_array(
                descriptor_array[offsets[index]:offsets[index + 1]],
                atom_count=int(atom_count), policy=policy,
            )
            descriptors.append(selected)
            stress = None if stresses_np is None else np.asarray(stresses_np[index], dtype=float)
            predictions.append(AtomicModelPrediction(
                energy_ev=float(np.asarray(energies_np[index]).reshape(())),
                forces_ev_per_angstrom=np.asarray(
                    forces_np[offsets[index]:offsets[index + 1]], dtype=float
                ),
                stress_ev_per_angstrom3=stress,
            ))
        return tuple(descriptors), tuple(predictions)

    def evaluate_batch(
        self, atoms_batch: Sequence[Any], policy: MaceDescriptorPolicy
    ) -> tuple[tuple[np.ndarray, ...], tuple[AtomicModelPrediction, ...]]:
        """Extract descriptors and predictions from one derivative-enabled pass.

        DATA6 normally requests both artifacts for the same development frames.
        Running a forward-only descriptor pass and then a second autograd pass
        for energy/forces/stress nearly doubles MACE work.  A single-model
        native MACE batch already returns ``node_feats`` together with those
        observables, so reuse that graph when the exact qualified path is
        available.  Unsupported calculators retain the former two-call path.
        """

        if not atoms_batch:
            return (), ()
        calc = self._calculator
        if (
            not self._native_batch_supported()
            or int(getattr(calc, "num_models", len(getattr(calc, "models", ())))) != 1
        ):
            return (
                self.get_descriptors_batch(atoms_batch, policy),
                self.predict_batch(atoms_batch),
            )
        batch, counts = self._native_batch(atoms_batch)
        return self._evaluate_native_batch(
            batch, counts, tuple(int(len(atoms)) for atoms in atoms_batch), policy
        )

    def predict_batch(
        self,
        atoms_batch: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
        graph_cache_directory: str | Path | None = None,
    ) -> tuple[AtomicModelPrediction, ...]:
        """Evaluate structures using stable monitor graph shards when identified."""

        if not self._native_batch_supported() or (
            len(atoms_batch) <= 1 and geometry_identities is None
        ):
            return tuple(self.predict(atoms) for atoms in atoms_batch)
        try:
            import torch
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("MACE prediction batching requires torch.") from exc
        calc = self._calculator
        batch, counts = self._native_batch(
            atoms_batch,
            geometry_identities=geometry_identities,
            graph_cache_directory=graph_cache_directory,
        )
        outputs = []
        model_count = len(calc.models)
        with torch.enable_grad():
            for model_index, model in enumerate(calc.models):
                # A single-model calculator owns this freshly materialized device
                # batch, so cloning it only doubles device traffic and allocation.
                # Ensembles retain isolation between model passes.
                local = batch if model_count == 1 else batch.clone()
                model_dtype = next(model.parameters()).dtype
                for key in local.keys:
                    value = local[key]
                    if torch.is_tensor(value) and torch.is_floating_point(value):
                        local[key] = value.to(dtype=model_dtype)
                outputs.append(
                    model(
                        local.to_dict(),
                        compute_stress=True,
                        training=False,
                        compute_edge_forces=False,
                        compute_atomic_stresses=False,
                    )
                )
        energies = torch.stack([out["energy"] for out in outputs]).mean(dim=0)
        forces = torch.stack([out["forces"] for out in outputs]).mean(dim=0)
        stress_values = [out.get("stress") for out in outputs]
        stresses = None
        if all(value is not None for value in stress_values):
            stresses = torch.stack(stress_values).mean(dim=0)
        energies_np = energies.detach().cpu().numpy() * float(calc.energy_units_to_eV)
        forces_np = forces.detach().cpu().numpy() * float(calc.energy_units_to_eV / calc.length_units_to_A)
        stresses_np = None
        if stresses is not None:
            stresses_np = stresses.detach().cpu().numpy() * float(
                calc.energy_units_to_eV / calc.length_units_to_A**3
            )
        offsets = np.concatenate(([0], np.cumsum(counts)))
        result = []
        for index, _atoms in enumerate(atoms_batch):
            stress = None if stresses_np is None else np.asarray(stresses_np[index], dtype=np.float64)
            result.append(
                AtomicModelPrediction(
                    float(energies_np[index]),
                    np.asarray(forces_np[offsets[index]:offsets[index + 1]], dtype=np.float64),
                    stress,
                )
            )
        return tuple(result)


def _current_process_rss_bytes() -> int:
    """Return current RSS, never the process-lifetime high-water mark."""

    try:
        pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
        return pages * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, ValueError, IndexError):
        return 0


class _StaticInferenceResourceMonitor:
    """Point-scoped conservative RSS/device peak sampler.

    ``peak_ram_bytes`` is the baseline-to-peak process RSS contribution during
    this execution region. ``peak_vram_bytes`` is the baseline-to-peak device
    residency contribution observed by live telemetry or the allocator peak
    delta, whichever is larger. These meanings are deliberately
    versioned by ``STATIC_INFERENCE_EVIDENCE_SEMANTICS``.
    """

    def __init__(self, device: str, *, interval_seconds: float = 0.002) -> None:
        self.device = str(device)
        self.interval_seconds = max(0.0005, float(interval_seconds))
        self._stop = Event()
        self._thread: Thread | None = None
        self._baseline_rss = 0
        self._peak_rss = 0
        self._baseline_vram: int | None = None
        self._peak_vram: int | None = None
        self._torch = None
        self._baseline_allocator_reserved = 0

    def _sample(self) -> None:
        rss = _current_process_rss_bytes()
        self._peak_rss = max(self._peak_rss, rss)
        if not self.device.startswith("cuda"):
            return
        try:
            from .training_parallel import query_gpu_telemetry

            sample = query_gpu_telemetry(self.device)
            if sample is not None:
                used = int(sample.used_bytes)
                if self._baseline_vram is None:
                    self._baseline_vram = used
                self._peak_vram = max(self._peak_vram or 0, used)
        except Exception:
            pass

    def _poll(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def start(self) -> None:
        self._baseline_rss = _current_process_rss_bytes()
        self._peak_rss = self._baseline_rss
        self._sample()
        if self.device.startswith("cuda"):
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.synchronize(self.device)
                    self._baseline_allocator_reserved = int(
                        torch.cuda.memory_reserved(self.device)
                    )
                    torch.cuda.reset_peak_memory_stats(self.device)
                    self._torch = torch
            except Exception:
                self._torch = None
        self._thread = Thread(
            target=self._poll, name="mdstats-static-resource-monitor", daemon=True
        )
        self._thread.start()

    def finish(self) -> tuple[int, int | None]:
        self._sample()
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(0.05, 4.0 * self.interval_seconds))
        if self._torch is not None:
            try:
                self._torch.cuda.synchronize(self.device)
                allocator_delta = max(
                    0,
                    int(self._torch.cuda.max_memory_reserved(self.device))
                    - int(self._baseline_allocator_reserved),
                )
                telemetry_delta = max(
                    0, int(self._peak_vram or 0) - int(self._baseline_vram or 0)
                )
                self._peak_vram = max(allocator_delta, telemetry_delta)
            except Exception:
                pass
        ram_delta = max(0, int(self._peak_rss) - int(self._baseline_rss))
        vram_delta = (
            None if self._peak_vram is None else max(
                0, int(self._peak_vram) - int(self._baseline_vram or 0)
            )
        ) if self._torch is None else self._peak_vram
        return ram_delta, vram_delta


@dataclass(frozen=True, slots=True)
class StaticInferenceOperatingPointEvidence:
    """Measured persistent-pool and steady-state operating-point evidence.

    ``peak_*`` is the conservative fresh-process requirement: persistent private
    provider residency plus the peak incremental cost of one synchronized wave.
    The components remain explicit so a warm steady-state throughput measurement
    cannot erase the cost of materializing the selected private provider pool.
    """

    batch_size: int
    concurrent_model_jobs: int
    structures_per_second: float
    peak_ram_bytes: int
    peak_vram_bytes: int | None
    feasible: bool = True
    failure_kind: str | None = None
    completed_structures: int = 0
    elapsed_seconds: float = 0.0
    observed_max_active_jobs: int = 1
    provider_pool_resident_ram_bytes: int = 0
    provider_pool_resident_vram_bytes: int | None = None
    execution_peak_ram_bytes: int = 0
    execution_peak_vram_bytes: int | None = None
    provider_pool_observed_ram_bytes: int = 0
    provider_pool_observed_vram_bytes: int | None = None

    def __post_init__(self) -> None:
        if int(self.batch_size) <= 0 or int(self.concurrent_model_jobs) <= 0:
            raise TrainingDataInputError("Static inference operating-point sizes must be positive.")
        if not np.isfinite(float(self.structures_per_second)) or float(self.structures_per_second) < 0:
            raise TrainingDataInputError("Static inference throughput must be finite and nonnegative.")
        if int(self.peak_ram_bytes) < 0 or (
            self.peak_vram_bytes is not None and int(self.peak_vram_bytes) < 0
        ):
            raise TrainingDataInputError("Static inference peak memory must be nonnegative.")
        for value in (
            self.provider_pool_resident_ram_bytes,
            self.execution_peak_ram_bytes,
        ):
            if int(value) < 0:
                raise TrainingDataInputError("Static inference resource components must be nonnegative.")
        for value in (
            self.provider_pool_resident_vram_bytes,
            self.execution_peak_vram_bytes,
        ):
            if value is not None and int(value) < 0:
                raise TrainingDataInputError("Static inference resource components must be nonnegative.")
        if int(self.completed_structures) < 0 or float(self.elapsed_seconds) < 0.0:
            raise TrainingDataInputError("Static inference measurement dimensions must be nonnegative.")
        if int(self.observed_max_active_jobs) <= 0:
            raise TrainingDataInputError("Observed static inference concurrency must be positive.")
        if self.feasible and (
            int(self.completed_structures) <= 0 or float(self.elapsed_seconds) <= 0.0
        ):
            raise TrainingDataInputError(
                "Feasible static inference evidence requires real completed work and wall time."
            )
        if self.feasible and int(self.observed_max_active_jobs) != int(self.concurrent_model_jobs):
            raise TrainingDataInputError(
                "Recorded static inference concurrency must equal actually observed concurrency."
            )
        if int(self.completed_structures) > 0 and float(self.elapsed_seconds) > 0.0:
            measured = int(self.completed_structures) / float(self.elapsed_seconds)
            if not math.isclose(
                measured, float(self.structures_per_second), rel_tol=1.0e-9, abs_tol=1.0e-12
            ):
                raise TrainingDataInputError(
                    "Static inference throughput must equal completed work / joint wall time."
                )
        if self.feasible:
            if int(self.peak_ram_bytes) != (
                int(self.provider_pool_resident_ram_bytes)
                + int(self.execution_peak_ram_bytes)
            ):
                raise TrainingDataInputError(
                    "Feasible static inference RAM evidence must equal residency plus execution peak."
                )
            if self.peak_vram_bytes is not None:
                if (
                    self.provider_pool_resident_vram_bytes is None
                    or self.execution_peak_vram_bytes is None
                    or int(self.peak_vram_bytes) != (
                        int(self.provider_pool_resident_vram_bytes)
                        + int(self.execution_peak_vram_bytes)
                    )
                ):
                    raise TrainingDataInputError(
                        "Feasible static inference VRAM evidence must equal residency plus execution peak."
                    )
            if int(self.concurrent_model_jobs) == 1 and int(
                self.provider_pool_resident_ram_bytes
            ) != 0:
                raise TrainingDataInputError(
                    "One-job static inference evidence cannot retain private-provider residency."
                )
            if (
                int(self.concurrent_model_jobs) == 1
                and self.peak_vram_bytes is not None
                and int(self.provider_pool_resident_vram_bytes or 0) != 0
            ):
                raise TrainingDataInputError(
                    "One-job static inference evidence cannot retain private-provider VRAM residency."
                )
        object.__setattr__(self, "batch_size", int(self.batch_size))
        object.__setattr__(self, "concurrent_model_jobs", int(self.concurrent_model_jobs))
        object.__setattr__(self, "structures_per_second", float(self.structures_per_second))
        object.__setattr__(self, "peak_ram_bytes", int(self.peak_ram_bytes))
        object.__setattr__(
            self, "peak_vram_bytes",
            None if self.peak_vram_bytes is None else int(self.peak_vram_bytes),
        )
        object.__setattr__(
            self, "failure_kind",
            None if self.failure_kind is None else str(self.failure_kind).strip() or None,
        )
        object.__setattr__(self, "completed_structures", int(self.completed_structures))
        object.__setattr__(self, "elapsed_seconds", float(self.elapsed_seconds))
        object.__setattr__(self, "observed_max_active_jobs", int(self.observed_max_active_jobs))
        object.__setattr__(self, "provider_pool_resident_ram_bytes", int(self.provider_pool_resident_ram_bytes))
        object.__setattr__(
            self, "provider_pool_resident_vram_bytes",
            None if self.provider_pool_resident_vram_bytes is None else int(self.provider_pool_resident_vram_bytes),
        )
        object.__setattr__(self, "execution_peak_ram_bytes", int(self.execution_peak_ram_bytes))
        object.__setattr__(
            self, "execution_peak_vram_bytes",
            None if self.execution_peak_vram_bytes is None else int(self.execution_peak_vram_bytes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "concurrent_model_jobs": self.concurrent_model_jobs,
            "structures_per_second": self.structures_per_second,
            "peak_ram_bytes": self.peak_ram_bytes,
            "peak_vram_bytes": self.peak_vram_bytes,
            "feasible": bool(self.feasible),
            "failure_kind": self.failure_kind,
            "completed_structures": self.completed_structures,
            "elapsed_seconds": self.elapsed_seconds,
            "observed_max_active_jobs": self.observed_max_active_jobs,
            "provider_pool_resident_ram_bytes": self.provider_pool_resident_ram_bytes,
            "provider_pool_resident_vram_bytes": self.provider_pool_resident_vram_bytes,
            "provider_pool_required_ram_bytes": self.provider_pool_resident_ram_bytes,
            "provider_pool_required_vram_bytes": self.provider_pool_resident_vram_bytes,
            "aggregate_required_ram_bytes": self.peak_ram_bytes,
            "aggregate_required_vram_bytes": self.peak_vram_bytes,
            "execution_peak_ram_bytes": self.execution_peak_ram_bytes,
            "execution_peak_vram_bytes": self.execution_peak_vram_bytes,
            "provider_pool_observed_ram_bytes": self.provider_pool_observed_ram_bytes,
            "provider_pool_observed_vram_bytes": self.provider_pool_observed_vram_bytes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StaticInferenceOperatingPointEvidence":
        if bool(payload.get("feasible", True)):
            required = (
                "provider_pool_required_ram_bytes",
                "execution_peak_ram_bytes",
            )
            missing = [name for name in required if name not in payload]
            if payload.get("peak_vram_bytes") is not None:
                missing.extend(
                    name
                    for name in (
                        "provider_pool_required_vram_bytes",
                        "execution_peak_vram_bytes",
                    )
                    if name not in payload
                )
            if missing:
                raise TrainingDataSerializationError(
                    "Feasible v5 static-inference evidence omits required resource components: "
                    + ", ".join(missing)
                )
        return cls(
            batch_size=int(payload["batch_size"]),
            concurrent_model_jobs=int(payload["concurrent_model_jobs"]),
            structures_per_second=float(payload["structures_per_second"]),
            peak_ram_bytes=int(payload.get("aggregate_required_ram_bytes", payload["peak_ram_bytes"])),
            peak_vram_bytes=(
                None if payload.get("aggregate_required_vram_bytes", payload.get("peak_vram_bytes")) is None
                else int(payload.get("aggregate_required_vram_bytes", payload["peak_vram_bytes"]))
            ),
            feasible=bool(payload.get("feasible", True)),
            failure_kind=(
                None if payload.get("failure_kind") is None
                else str(payload["failure_kind"])
            ),
            completed_structures=int(payload.get("completed_structures", 0)),
            elapsed_seconds=float(payload.get("elapsed_seconds", 0.0)),
            observed_max_active_jobs=int(payload.get("observed_max_active_jobs", 1)),
            provider_pool_resident_ram_bytes=int(payload.get("provider_pool_required_ram_bytes", payload.get("provider_pool_resident_ram_bytes", 0))),
            provider_pool_resident_vram_bytes=(
                None if payload.get("provider_pool_required_vram_bytes", payload.get("provider_pool_resident_vram_bytes")) is None
                else int(payload.get("provider_pool_required_vram_bytes", payload["provider_pool_resident_vram_bytes"]))
            ),
            execution_peak_ram_bytes=int(payload.get("execution_peak_ram_bytes", 0)),
            execution_peak_vram_bytes=(
                None if payload.get("execution_peak_vram_bytes") is None
                else int(payload["execution_peak_vram_bytes"])
            ),
            provider_pool_observed_ram_bytes=int(payload.get("provider_pool_observed_ram_bytes", 0)),
            provider_pool_observed_vram_bytes=(
                None if payload.get("provider_pool_observed_vram_bytes") is None
                else int(payload["provider_pool_observed_vram_bytes"])
            ),
        )


@dataclass(frozen=True, slots=True)
class StaticInferenceRuntimeProfile:
    """Runtime-only compatible result of bounded joint operating-point search."""

    compatibility_digest: str
    selected_batch_size: int
    selected_concurrent_model_jobs: int
    learned_safe_batch_ceiling: int
    evidence: tuple[StaticInferenceOperatingPointEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "compatibility_digest",
            validate_digest(self.compatibility_digest, name="compatibility_digest"),
        )
        for value in (
            self.selected_batch_size,
            self.selected_concurrent_model_jobs,
            self.learned_safe_batch_ceiling,
        ):
            if int(value) <= 0:
                raise TrainingDataInputError("Static inference profile sizes must be positive.")
        object.__setattr__(self, "selected_batch_size", int(self.selected_batch_size))
        object.__setattr__(
            self, "selected_concurrent_model_jobs", int(self.selected_concurrent_model_jobs)
        )
        object.__setattr__(
            self, "learned_safe_batch_ceiling", int(self.learned_safe_batch_ceiling)
        )
        object.__setattr__(self, "evidence", tuple(self.evidence))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STATIC_INFERENCE_RUNTIME_PROFILE_SCHEMA,
            "evidence_semantics": STATIC_INFERENCE_EVIDENCE_SEMANTICS,
            "compatibility_digest": self.compatibility_digest,
            "selected_batch_size": self.selected_batch_size,
            "selected_concurrent_model_jobs": self.selected_concurrent_model_jobs,
            "learned_safe_batch_ceiling": self.learned_safe_batch_ceiling,
            "evidence": [value.to_dict() for value in self.evidence],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StaticInferenceRuntimeProfile":
        if payload.get("schema") != STATIC_INFERENCE_RUNTIME_PROFILE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported static-inference runtime profile schema.")
        if payload.get("evidence_semantics") != STATIC_INFERENCE_EVIDENCE_SEMANTICS:
            raise TrainingDataSerializationError(
                "Unsupported static-inference runtime-profile evidence semantics."
            )
        result = cls(
            compatibility_digest=str(payload["compatibility_digest"]),
            selected_batch_size=int(payload["selected_batch_size"]),
            selected_concurrent_model_jobs=int(payload["selected_concurrent_model_jobs"]),
            learned_safe_batch_ceiling=int(payload["learned_safe_batch_ceiling"]),
            evidence=tuple(
                StaticInferenceOperatingPointEvidence.from_dict(value)
                for value in payload.get("evidence", ())
            ),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("Static-inference runtime profile digest mismatch.")
        return result

    @classmethod
    def load_compatible(
        cls, path: str | Path, *, compatibility_digest: str
    ) -> "StaticInferenceRuntimeProfile | None":
        candidate = Path(path)
        if not candidate.is_file():
            return None
        try:
            result = cls.from_dict(json.loads(candidate.read_text(encoding="utf-8")))
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            TrainingDataInputError,
            TrainingDataSerializationError,
        ):
            return None
        return (
            result
            if result.compatibility_digest == compatibility_digest
            else None
        )

    def write_atomic(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, sort_keys=True, separators=(",", ":"))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


class StaticInferenceRuntimeAuthority:
    """Single owner for static batch/job search, reuse, re-clamp, and OOM learning."""

    def __init__(
        self,
        *,
        compatibility_digest: str,
        maximum_batch_size: int,
        maximum_concurrent_model_jobs: int,
        live_ram_budget_bytes: int,
        live_vram_budget_bytes: int | None,
        ram_policy_fraction: float = 0.80,
        vram_policy_fraction: float = 0.90,
        estimated_provider_resident_ram_bytes: int | None = None,
        estimated_provider_resident_vram_bytes: int | None = None,
        cold_start_batch_size: int = 8,
        throughput_tolerance_fraction: float = 0.05,
        compatible_profile: StaticInferenceRuntimeProfile | None = None,
    ) -> None:
        self.compatibility_digest = validate_digest(
            compatibility_digest, name="compatibility_digest"
        )
        self.maximum_batch_size = int(maximum_batch_size)
        self.maximum_concurrent_model_jobs = int(maximum_concurrent_model_jobs)
        self.live_ram_budget_bytes = int(live_ram_budget_bytes)
        self.live_vram_budget_bytes = (
            None if live_vram_budget_bytes is None else int(live_vram_budget_bytes)
        )
        self.initial_incremental_ram_cap_bytes = int(live_ram_budget_bytes)
        self.initial_incremental_vram_cap_bytes = (
            None if live_vram_budget_bytes is None else int(live_vram_budget_bytes)
        )
        self.ram_policy_fraction = float(ram_policy_fraction)
        self.vram_policy_fraction = float(vram_policy_fraction)
        self.throughput_tolerance_fraction = float(throughput_tolerance_fraction)
        if (
            self.maximum_batch_size <= 0
            or self.maximum_concurrent_model_jobs <= 0
            or self.live_ram_budget_bytes <= 0
            or (self.live_vram_budget_bytes is not None and self.live_vram_budget_bytes <= 0)
            or not 0.0 < self.ram_policy_fraction <= 1.0
            or not 0.0 < self.vram_policy_fraction <= 1.0
            or not 0.0 <= self.throughput_tolerance_fraction < 1.0
        ):
            raise TrainingDataInputError("Static inference runtime authority limits are invalid.")
        cold = min(self.maximum_batch_size, max(1, int(cold_start_batch_size)))
        ascending: list[int] = []
        value = cold
        while value < self.maximum_batch_size:
            ascending.append(value)
            value = min(self.maximum_batch_size, value * 2)
        ascending.append(self.maximum_batch_size)
        descending: list[int] = []
        value = cold // 2
        while value >= 1:
            descending.append(value)
            value //= 2
        self.candidate_batch_sizes = tuple(dict.fromkeys((*ascending, *descending, 1)))
        self.learned_safe_batch_ceiling = self.maximum_batch_size
        # This estimate is deliberately independent of a one-job execution
        # transient.  It is the conservative outer-envelope fallback until a
        # private shell has actually been measured by the executor.
        self.private_provider_growth_available = (
            estimated_provider_resident_ram_bytes is not None
            and (
                self.initial_incremental_vram_cap_bytes is None
                or estimated_provider_resident_vram_bytes is not None
            )
        )
        self.estimated_provider_resident_ram_bytes = max(
            1,
            int(estimated_provider_resident_ram_bytes)
            if estimated_provider_resident_ram_bytes is not None
            else 1,
        )
        self.estimated_provider_resident_vram_bytes = (
            None
            if self.initial_incremental_vram_cap_bytes is None
            else (
                None
                if estimated_provider_resident_vram_bytes is None
                else max(
                1,
                int(estimated_provider_resident_vram_bytes),
                )
            )
        )
        self.failed_provider_concurrency: set[int] = set()
        self.failed_execution_boundaries: set[tuple[int, int]] = set()
        self.evidence: list[StaticInferenceOperatingPointEvidence] = []
        self.selected_point: StaticInferenceOperatingPointEvidence | None = None
        self.reused_compatible_profile = False
        if (
            compatible_profile is not None
            and compatible_profile.compatibility_digest == self.compatibility_digest
        ):
            self.learned_safe_batch_ceiling = min(
                self.maximum_batch_size, compatible_profile.learned_safe_batch_ceiling
            )
            self.evidence.extend(compatible_profile.evidence)
            for point in self.evidence:
                if not point.feasible and point.failure_kind == "provider-pool-oom":
                    self.failed_provider_concurrency.add(point.concurrent_model_jobs)
                elif not point.feasible and point.failure_kind == "execution-oom":
                    if point.concurrent_model_jobs == 1:
                        self.learned_safe_batch_ceiling = min(
                            self.learned_safe_batch_ceiling, max(1, point.batch_size // 2)
                        )
                    else:
                        self.failed_execution_boundaries.add(
                            (point.batch_size, point.concurrent_model_jobs)
                        )
            self._select()
            self.reused_compatible_profile = self.selected_point is not None

    @staticmethod
    def compatibility_key(payload: Mapping[str, Any]) -> str:
        """Hash conservative hardware/runtime/model/workload-shape identity.

        Bumped to v4 for the G6/G7 requalification amendment (R18A): the
        embedded ``runtime_architecture_identity`` now derives from the
        strengthened canonical execution-architecture authority
        (``MACE_RUNTIME_ARCHITECTURE_SCHEMA`` v2), so persisted profiles
        computed under the legacy weaker digest are deliberately unreachable
        even if their other payload fields happen to coincide.
        """

        return digest({
            "schema": "mdstats.static-inference-compatibility.v4",
            "evidence_semantics": STATIC_INFERENCE_EVIDENCE_SEMANTICS,
            **dict(payload),
        })

    def _safe(self, point: StaticInferenceOperatingPointEvidence) -> bool:
        return bool(
            point.feasible
            and point.batch_size <= self.learned_safe_batch_ceiling
            and point.batch_size <= self.maximum_batch_size
            and point.concurrent_model_jobs <= self.maximum_concurrent_model_jobs
            and point.peak_ram_bytes <= self.initial_incremental_ram_cap_bytes
            and (
                self.initial_incremental_vram_cap_bytes is None
                or point.peak_vram_bytes is not None
                and point.peak_vram_bytes <= self.initial_incremental_vram_cap_bytes
            )
            and not any(
                point.concurrent_model_jobs >= failed
                for failed in self.failed_provider_concurrency
            )
            and not any(
                point.concurrent_model_jobs >= failed_jobs
                and point.batch_size >= failed_batch
                for failed_batch, failed_jobs in self.failed_execution_boundaries
            )
        )

    def admits_requirement(
        self,
        *,
        ram_bytes: int,
        vram_bytes: int | None,
        concurrent_model_jobs: int = 1,
    ) -> bool:
        """Return whether a fresh live budget admits a material transition."""

        return bool(
            int(ram_bytes) <= self.live_ram_budget_bytes
            and (
                (
                    self.initial_incremental_vram_cap_bytes is None
                )
                or vram_bytes is not None
                and self.live_vram_budget_bytes is not None
                and int(vram_bytes) <= self.live_vram_budget_bytes
                or (
                    int(concurrent_model_jobs) <= 1
                    and (
                        vram_bytes is None
                        or self.live_vram_budget_bytes is None
                    )
                )
            )
        )

    def provider_residency_estimate(self) -> tuple[int, int | None]:
        """Return the conservative next-private-slot residency estimate."""

        return (
            int(self.estimated_provider_resident_ram_bytes),
            None
            if self.estimated_provider_resident_vram_bytes is None
            else int(self.estimated_provider_resident_vram_bytes),
        )

    def observe_provider_residency(self, *, ram_bytes: int, vram_bytes: int | None) -> None:
        """Tighten the next-slot estimate without ever substituting zero."""

        self.estimated_provider_resident_ram_bytes = max(
            self.estimated_provider_resident_ram_bytes, max(1, int(ram_bytes))
        )
        if self.initial_incremental_vram_cap_bytes is not None:
            if vram_bytes is None:
                self.estimated_provider_resident_vram_bytes = None
            elif self.estimated_provider_resident_vram_bytes is not None:
                self.estimated_provider_resident_vram_bytes = max(
                    self.estimated_provider_resident_vram_bytes, max(1, int(vram_bytes))
                )

    def _select(self) -> StaticInferenceOperatingPointEvidence | None:
        safe = tuple(point for point in self.evidence if self._safe(point))
        if not safe:
            self.selected_point = None
            return None
        peak = max(point.structures_per_second for point in safe)
        floor = peak * (1.0 - self.throughput_tolerance_fraction)
        near = tuple(point for point in safe if point.structures_per_second >= floor)
        self.selected_point = min(
            near,
            key=lambda point: (
                point.peak_ram_bytes,
                -1 if point.peak_vram_bytes is None else point.peak_vram_bytes,
                point.concurrent_model_jobs,
                point.batch_size,
                -point.structures_per_second,
            ),
        )
        return self.selected_point

    def next_batch_size(self, remaining: int) -> int:
        if self.reused_compatible_profile and self.selected_point is not None:
            return min(int(remaining), self.selected_point.batch_size)
        measured = {point.batch_size for point in self.evidence}
        for candidate in self.candidate_batch_sizes:
            if candidate <= self.learned_safe_batch_ceiling and candidate not in measured:
                return min(int(remaining), candidate)
        selected = self._select()
        return min(int(remaining), 1 if selected is None else selected.batch_size)

    @property
    def candidate_concurrencies(self) -> tuple[int, ...]:
        """Bounded geometric job-count candidates, including the configured cap."""

        # Without a configured or observed conservative requirement, materializing
        # even the first private shell is not a safe automatic decision.  Do not
        # leak intermediate geometric candidates when the configured cap is >2.
        if not self.private_provider_growth_available:
            return (1,)
        values = [1]
        candidate = 2
        while candidate < self.maximum_concurrent_model_jobs:
            values.append(candidate)
            candidate *= 2
        values.append(self.maximum_concurrent_model_jobs)
        return tuple(dict.fromkeys(values))

    def candidate_operating_points(
        self, *, available_structures: int, concurrency_available: bool
    ) -> tuple[tuple[int, int], ...]:
        """Return bounded, genuinely exercisable unmeasured ``(batch, jobs)`` points."""

        available = max(0, int(available_structures))
        measured = {
            (point.batch_size, point.concurrent_model_jobs) for point in self.evidence
        }
        jobs = self.candidate_concurrencies if concurrency_available else (1,)
        # Grow private model shells monotonically.  Exploring all batch points at
        # one concurrency avoids repeatedly constructing and retiring the same
        # providers merely because the batch candidate changed.
        return tuple(
            (batch, concurrent)
            for concurrent in jobs
            for batch in self.candidate_batch_sizes
            if batch <= self.learned_safe_batch_ceiling
            and not any(concurrent >= failed for failed in self.failed_provider_concurrency)
            and not any(
                concurrent >= failed_jobs and batch >= failed_batch
                for failed_batch, failed_jobs in self.failed_execution_boundaries
            )
            and batch * concurrent <= available
            and (batch, concurrent) not in measured
        )

    def record(self, point: StaticInferenceOperatingPointEvidence) -> None:
        self.evidence.append(point)
        if (
            not point.feasible
            and point.failure_kind == "execution-oom"
            and point.concurrent_model_jobs == 1
        ):
            self.learned_safe_batch_ceiling = min(
                self.learned_safe_batch_ceiling, max(1, point.batch_size // 2)
            )
        if not point.feasible and point.failure_kind == "execution-oom" and point.concurrent_model_jobs > 1:
            self.failed_execution_boundaries.add(
                (int(point.batch_size), int(point.concurrent_model_jobs))
            )
        if not point.feasible and point.failure_kind == "provider-pool-oom":
            self.failed_provider_concurrency.add(int(point.concurrent_model_jobs))
        self._select()

    def reclamp(
        self,
        *,
        live_ram_available_bytes: int,
        live_vram_available_bytes: int | None,
    ) -> StaticInferenceOperatingPointEvidence | None:
        self.live_ram_budget_bytes = max(
            1,
            min(
                self.initial_incremental_ram_cap_bytes,
                math.floor(int(live_ram_available_bytes) * self.ram_policy_fraction),
            ),
        )
        self.live_vram_budget_bytes = (
            None
            if live_vram_available_bytes is None
            else max(
                1,
                min(
                    int(self.initial_incremental_vram_cap_bytes or 0),
                    math.floor(
                        int(live_vram_available_bytes) * self.vram_policy_fraction
                    ),
                ),
            )
        )
        return self._select()

    def profile(self) -> StaticInferenceRuntimeProfile:
        selected = self._select()
        if selected is None:
            raise TrainingDataInputError(
                "No measured static inference operating point fits the live resource envelope."
            )
        return StaticInferenceRuntimeProfile(
            compatibility_digest=self.compatibility_digest,
            selected_batch_size=selected.batch_size,
            selected_concurrent_model_jobs=selected.concurrent_model_jobs,
            learned_safe_batch_ceiling=self.learned_safe_batch_ceiling,
            evidence=tuple(self.evidence),
        )


def _raise_if_static_inference_cancelled(phase: str) -> None:
    """Poll staged-evaluation cancellation between safe static-inference units."""

    from .inference_parallel import (
        inference_cancellation_requested,
        report_inference_worker_phase,
    )

    if inference_cancellation_requested():
        report_inference_worker_phase(f"cancelled before {phase}")
        raise InterruptedError(f"Static inference cancelled before {phase}.")


class StaticMaceInferenceExecutor:
    """Canonical deterministic batched prediction owner with bounded OOM learning."""

    def __init__(
        self,
        provider: Any,
        *,
        batch_size: int,
        graph_cache_directory: str | Path | None = None,
        maximum_oom_backoffs: int = 8,
        owns_provider: bool = False,
        runtime_authority: StaticInferenceRuntimeAuthority | None = None,
        concurrent_model_jobs: int = 1,
        device: str = "cpu",
        provider_factory: Callable[[], Any] | None = None,
    ) -> None:
        if int(batch_size) <= 0 or int(maximum_oom_backoffs) < 0:
            raise TrainingDataInputError("Static inference batch/backoff configuration is invalid.")
        self.provider = provider
        self.requested_batch_size = int(batch_size)
        self.learned_safe_batch_size = int(batch_size)
        self.graph_cache_directory = graph_cache_directory
        self.maximum_oom_backoffs = int(maximum_oom_backoffs)
        self.oom_backoff_count = 0
        self.owns_provider = bool(owns_provider)
        self.runtime_authority = runtime_authority
        self.concurrent_model_jobs = max(1, int(concurrent_model_jobs))
        self.device = str(device)
        self.provider_factory = provider_factory
        self._execution_lock = RLock()
        # Slot zero is caller-provided; every later slot is executor-owned and
        # survives calibration and production waves until explicitly retired.
        self._provider_pool: list[Any] = [provider]
        self._provider_pool_resident_ram_bytes: list[int] = [0]
        self._provider_pool_resident_vram_bytes: list[int | None] = [None]
        self._provider_pool_observed_ram_bytes: list[int] = [0]
        self._provider_pool_observed_vram_bytes: list[int | None] = [None]
        self._closed = False

    @classmethod
    def from_model_path(
        cls,
        model_path: str | Path,
        *,
        batch_size: int,
        device: str,
        default_dtype: str,
        graph_cache_directory: str | Path | None = None,
        runtime_authority: StaticInferenceRuntimeAuthority | None = None,
        concurrent_model_jobs: int = 1,
        **calculator_kwargs: Any,
    ) -> "StaticMaceInferenceExecutor":
        def provider_factory() -> Any:
            return MaceCalculatorProvider.from_model_path(
                model_path, device=device, default_dtype=default_dtype, **calculator_kwargs
            )

        provider = provider_factory()
        return cls(
            provider, batch_size=batch_size, graph_cache_directory=graph_cache_directory,
            owns_provider=True, runtime_authority=runtime_authority,
            concurrent_model_jobs=concurrent_model_jobs, device=device,
            provider_factory=provider_factory,
        )

    @staticmethod
    def _is_oom(exc: BaseException) -> bool:
        import errno

        if isinstance(exc, MemoryError):
            return True
        if isinstance(exc, OSError) and exc.errno == errno.ENOMEM:
            return True
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "out of memory", "cannot allocate memory", "cuda error: memory allocation",
                "cublas_status_alloc_failed",
            )
        )

    def _release_cuda_cache(self) -> None:
        """Release this executor's allocator cache only for a CUDA executor."""

        if not self.device.startswith("cuda"):
            return
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            return

    def _synchronize_device(self) -> None:
        """Make the executor's timing boundary include completed CUDA work."""

        if not self.device.startswith("cuda"):
            return
        try:
            import torch

            torch.cuda.synchronize(self.device)
        except Exception:
            # Providers may be CPU-backed test doubles with a CUDA-labelled
            # policy. Actual CUDA failures are still reported by prediction.
            return

    def close(self) -> None:
        if self._closed:
            return
        self._retire_private_providers(keep_jobs=1)
        if self.owns_provider and hasattr(self.provider, "close"):
            self.provider.close()
        self._closed = True

    def __enter__(self) -> "StaticMaceInferenceExecutor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @property
    def resident_provider_pool_size(self) -> int:
        return len(self._provider_pool)

    @property
    def provider_pool_resident_ram_bytes(self) -> int:
        return sum(self._provider_pool_resident_ram_bytes[1:])

    @property
    def provider_pool_resident_vram_bytes(self) -> int | None:
        values = self._provider_pool_resident_vram_bytes[1:]
        if not values:
            return 0
        if any(value is None for value in values):
            return None
        return sum(int(value) for value in values if value is not None)

    @staticmethod
    def _close_provider(provider: Any, *, release_cuda_memory: bool = True) -> None:
        if hasattr(provider, "close"):
            if isinstance(provider, MaceCalculatorProvider):
                provider.close(release_cuda_memory=release_cuda_memory)
            else:
                provider.close()

    def _retire_private_providers(
        self, *, keep_jobs: int, release_cuda_cache: bool = True
    ) -> None:
        keep = max(1, int(keep_jobs))
        shrunk = False
        while len(self._provider_pool) > keep:
            provider = self._provider_pool.pop()
            self._provider_pool_resident_ram_bytes.pop()
            self._provider_pool_resident_vram_bytes.pop()
            self._provider_pool_observed_ram_bytes.pop()
            self._provider_pool_observed_vram_bytes.pop()
            # Private MACE providers must not individually flush the process-wide
            # allocator cache.  The executor owns one release transaction after
            # every surplus owner has been dropped.
            self._close_provider(provider, release_cuda_memory=False)
            shrunk = True
        if shrunk and release_cuda_cache and self.device.startswith("cuda"):
            self._release_cuda_cache()

    def _ensure_provider_pool(
        self, jobs: int, *, admit_next_slot: Callable[[], bool] | None = None
    ) -> None:
        target = max(1, int(jobs))
        if target <= len(self._provider_pool):
            return
        if self.provider_factory is None:
            raise TrainingDataInputError(
                "Concurrent static inference requires a private-provider factory."
            )
        # Grow one slot at a time.  A construction failure can therefore close
        # only the new attempt and preserve every previously admitted provider.
        accepted = len(self._provider_pool)
        attempt_provider: Any | None = None
        try:
            while len(self._provider_pool) < target:
                _raise_if_static_inference_cancelled("private provider construction")
                if admit_next_slot is not None and not admit_next_slot():
                    raise TrainingDataInputError(
                        "Live RAM/VRAM headroom does not admit the next private provider slot."
                    )
                monitor = _StaticInferenceResourceMonitor(self.device)
                monitor.start()
                try:
                    attempt_provider = self.provider_factory()
                except BaseException:
                    monitor.finish()
                    raise
                growth_ram, growth_vram = monitor.finish()
                required_ram, required_vram = (
                    self.runtime_authority.provider_residency_estimate()
                    if self.runtime_authority is not None
                    else (max(1, int(growth_ram)), growth_vram)
                )
                required_ram = max(int(required_ram), max(1, int(growth_ram)))
                required_vram = (
                    None
                    if required_vram is None or growth_vram is None
                    else max(int(required_vram), max(1, int(growth_vram)))
                )
                self._provider_pool.append(attempt_provider)
                self._provider_pool_resident_ram_bytes.append(required_ram)
                self._provider_pool_resident_vram_bytes.append(required_vram)
                self._provider_pool_observed_ram_bytes.append(max(0, int(growth_ram)))
                self._provider_pool_observed_vram_bytes.append(
                    None if growth_vram is None else max(0, int(growth_vram))
                )
                # From here the provider is owned by the pool rollback rather
                # than this construction attempt.
                attempt_provider = None
                if self.runtime_authority is not None:
                    self.runtime_authority.observe_provider_residency(
                        ram_bytes=required_ram, vram_bytes=required_vram
                    )
        except BaseException:
            if attempt_provider is not None:
                self._close_provider(attempt_provider, release_cuda_memory=False)
            # Provider-growth failure is one executor-owned cleanup transaction:
            # exact rollback first, then one allocator release for CUDA only.
            self._retire_private_providers(
                keep_jobs=accepted, release_cuda_cache=False
            )
            self._release_cuda_cache()
            raise

    def _provider_batch(
        self, atoms_batch: Sequence[Any], geometry_identities: Sequence[str] | None
    ) -> tuple[AtomicModelPrediction, ...]:
        try:
            return tuple(self.provider.predict_batch(
                atoms_batch, geometry_identities=geometry_identities,
                graph_cache_directory=self.graph_cache_directory,
            ))
        except TypeError as exc:
            if "unexpected keyword" not in str(exc) and "geometry_identities" not in str(exc):
                raise
            return tuple(self.provider.predict_batch(atoms_batch))

    def _predict_owned(
        self,
        atoms: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
    ) -> tuple[AtomicModelPrediction, ...]:
        values = tuple(atoms)
        identities = None if geometry_identities is None else tuple(str(value) for value in geometry_identities)
        if not values:
            raise TrainingDataInputError("Static inference input is empty.")
        if identities is not None and len(identities) != len(values):
            raise TrainingDataInputError("Static inference geometry identity count mismatch.")
        result: list[AtomicModelPrediction] = []
        position = 0
        while position < len(values):
            _raise_if_static_inference_cancelled("static inference batch")
            remaining = len(values) - position
            batch_size = min(self.learned_safe_batch_size, remaining)
            if self.runtime_authority is not None:
                batch_size = min(
                    batch_size, self.runtime_authority.next_batch_size(remaining)
                )
            batch = values[position:position + batch_size]
            batch_ids = None if identities is None else identities[position:position + batch_size]
            monitor = (
                _StaticInferenceResourceMonitor(self.device)
                if self.runtime_authority is not None else None
            )
            if monitor is not None:
                monitor.start()
            started = time.perf_counter()
            try:
                predictions = self._provider_batch(batch, batch_ids)
            except RuntimeError as exc:
                peak_ram, peak_vram = (
                    monitor.finish() if monitor is not None else (0, None)
                )
                if not self._is_oom(exc) or batch_size <= 1:
                    raise
                if self.runtime_authority is not None:
                    self.runtime_authority.record(
                        StaticInferenceOperatingPointEvidence(
                            batch_size=batch_size,
                            concurrent_model_jobs=1,
                            structures_per_second=0.0,
                            peak_ram_bytes=peak_ram,
                            peak_vram_bytes=peak_vram,
                            feasible=False,
                            failure_kind="execution-oom",
                        )
                    )
                if self.oom_backoff_count >= self.maximum_oom_backoffs:
                    raise TrainingDataInputError(
                        "Static inference exhausted its bounded OOM backoff budget."
                    ) from exc
                self.oom_backoff_count += 1
                self.learned_safe_batch_size = max(1, batch_size // 2)
                self._release_cuda_cache()
                continue
            except BaseException:
                if monitor is not None:
                    monitor.finish()
                raise
            self._synchronize_device()
            elapsed = max(time.perf_counter() - started, 1.0e-12)
            peak_ram, peak_vram = (
                monitor.finish() if monitor is not None else (0, None)
            )
            if len(predictions) != len(batch):
                raise TrainingDataInputError("Static inference provider returned the wrong prediction count.")
            result.extend(predictions)
            position += batch_size
            if self.runtime_authority is not None:
                self.runtime_authority.record(
                    StaticInferenceOperatingPointEvidence(
                        batch_size=batch_size,
                        # This executor owns one private model shell and executes
                        # serially. Higher-J evidence is recorded only by the
                        # joint authority around an actual concurrent wave.
                        concurrent_model_jobs=1,
                        structures_per_second=batch_size / elapsed,
                        peak_ram_bytes=peak_ram,
                        peak_vram_bytes=peak_vram,
                        completed_structures=batch_size,
                        elapsed_seconds=elapsed,
                        observed_max_active_jobs=1,
                        provider_pool_resident_ram_bytes=0,
                        provider_pool_resident_vram_bytes=(
                            None if peak_vram is None else 0
                        ),
                        execution_peak_ram_bytes=peak_ram,
                        execution_peak_vram_bytes=peak_vram,
                    )
                )
        if self.runtime_authority is not None and self.runtime_authority.selected_point is not None:
            self.learned_safe_batch_size = min(
                self.learned_safe_batch_size,
                self.runtime_authority.selected_point.batch_size,
                self.runtime_authority.learned_safe_batch_ceiling,
            )
        return tuple(result)

    def _run_joint_wave(
        self,
        values: tuple[Any, ...],
        identities: tuple[str, ...] | None,
        *,
        batch_size: int,
        concurrent_jobs: int,
    ) -> tuple[
        tuple[AtomicModelPrediction, ...], float, int, int | None, int, int, int,
        int, int | None, int, int | None,
    ]:
        """Run one steady-state wave using stable worker-private provider slots."""

        batch, jobs = int(batch_size), int(concurrent_jobs)
        _raise_if_static_inference_cancelled("joint static-inference wave")
        if batch <= 0 or jobs <= 0 or len(values) != batch * jobs:
            raise TrainingDataInputError("Joint static inference wave dimensions are invalid.")
        if len(self._provider_pool) < jobs:
            raise TrainingDataInputError(
                "Joint static inference wave requires an already admitted provider pool."
            )
        ready = Barrier(jobs)
        active_ready = Barrier(jobs)
        active_lock = Lock()
        active = 0
        observed_peak = 0
        # The timing/resource boundary starts only after the required pool is
        # resident.  Its separately measured residency remains part of the
        # conservative profile requirement for a fresh process.
        monitor = _StaticInferenceResourceMonitor(self.device)
        monitor.start()
        started = time.perf_counter()
        providers = tuple(self._provider_pool[:jobs])

        def execute(index: int) -> tuple[int, tuple[AtomicModelPrediction, ...], int, int]:
            nonlocal active, observed_peak
            provider = providers[index]
            worker = StaticMaceInferenceExecutor(
                provider,
                batch_size=batch,
                graph_cache_directory=self.graph_cache_directory,
                maximum_oom_backoffs=self.maximum_oom_backoffs,
                owns_provider=False,
                device=self.device,
            )
            start = index * batch
            ready.wait(timeout=60.0)
            with active_lock:
                active += 1
                observed_peak = max(observed_peak, active)
            try:
                active_ready.wait(timeout=60.0)
                predicted = worker.predict(
                    values[start:start + batch],
                    geometry_identities=(
                        None if identities is None else identities[start:start + batch]
                    ),
                )
            finally:
                with active_lock:
                    active -= 1
            return index, predicted, worker.learned_safe_batch_size, worker.oom_backoff_count

        try:
            with ThreadPoolExecutor(
                max_workers=jobs, thread_name_prefix="mdstats-static-joint"
            ) as pool:
                completed = tuple(pool.map(execute, range(jobs)))
        except BaseException:
            monitor.finish()
            raise
        self._synchronize_device()
        elapsed = max(time.perf_counter() - started, 1.0e-12)
        execution_ram, execution_vram = monitor.finish()
        resident_ram = self.provider_pool_resident_ram_bytes
        resident_vram = self.provider_pool_resident_vram_bytes
        peak_ram = resident_ram + execution_ram
        peak_vram = (
            None
            if resident_vram is None or execution_vram is None
            else resident_vram + execution_vram
        )
        ordered = sorted(completed, key=lambda value: value[0])
        return (
            tuple(prediction for _, chunk, _, _ in ordered for prediction in chunk),
            elapsed,
            peak_ram,
            peak_vram,
            observed_peak,
            min(value[2] for value in ordered),
            sum(value[3] for value in ordered),
            resident_ram,
            resident_vram,
            execution_ram,
            execution_vram,
        )

    def _predict_joint_owned(
        self,
        atoms: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None,
    ) -> tuple[AtomicModelPrediction, ...]:
        authority = self.runtime_authority
        assert authority is not None
        from .inference_parallel import report_inference_worker_phase

        values = tuple(atoms)
        identities = None if geometry_identities is None else tuple(map(str, geometry_identities))
        if not values:
            raise TrainingDataInputError("Static inference input is empty.")
        if identities is not None and len(identities) != len(values):
            raise TrainingDataInputError("Static inference geometry identity count mismatch.")

        def reclamp_live() -> StaticInferenceOperatingPointEvidence | None:
            """Resolve one post-base-provider incremental coordinate snapshot."""

            try:
                from .resources import available_memory_bytes

                ram_available = available_memory_bytes()
            except Exception:
                ram_available = None
            if ram_available is None:
                # Host telemetry was required when the authority was created.
                # Retaining its last conservative cap is safer than inventing a
                # larger current value when a later probe is transiently absent.
                ram_available = max(
                    1, math.floor(authority.live_ram_budget_bytes / authority.ram_policy_fraction)
                )
            vram_available: int | None = None
            if authority.initial_incremental_vram_cap_bytes is not None:
                try:
                    from .training_parallel import query_gpu_telemetry

                    sample = query_gpu_telemetry(self.device)
                    if sample is not None:
                        vram_available = int(sample.free_bytes)
                except Exception:
                    vram_available = None
            return authority.reclamp(
                live_ram_available_bytes=int(ram_available),
                live_vram_available_bytes=vram_available,
            )

        def point_for(batch: int, jobs: int) -> StaticInferenceOperatingPointEvidence | None:
            return next(
                (
                    point
                    for point in authority.evidence
                    if point.feasible
                    and point.batch_size == int(batch)
                    and point.concurrent_model_jobs == int(jobs)
                ),
                None,
            )

        def marginal_requirement(batch: int, jobs: int) -> tuple[int, int | None]:
            """Return remaining pool growth plus the selected wave transient."""

            known = point_for(batch, jobs)
            single = point_for(batch, 1)
            current_ram = self.provider_pool_resident_ram_bytes
            current_vram = self.provider_pool_resident_vram_bytes
            if known is not None:
                target_ram = known.provider_pool_resident_ram_bytes
                target_vram = known.provider_pool_resident_vram_bytes
                execution_ram = known.execution_peak_ram_bytes
                execution_vram = known.execution_peak_vram_bytes
            else:
                estimated_ram, estimated_vram = authority.provider_residency_estimate()
                additional = max(0, int(jobs) - self.resident_provider_pool_size)
                target_ram = current_ram + additional * estimated_ram
                target_vram = (
                    None
                    if current_vram is None or estimated_vram is None
                    else current_vram + additional * estimated_vram
                )
                execution_ram = 0 if single is None else single.execution_peak_ram_bytes
                execution_vram = None if single is None else single.execution_peak_vram_bytes
            ram = max(0, int(target_ram) - current_ram) + int(execution_ram)
            vram = (
                None
                if target_vram is None or current_vram is None or execution_vram is None
                else max(0, int(target_vram) - int(current_vram)) + int(execution_vram)
            )
            return ram, vram

        def fresh_admission(batch: int, jobs: int) -> bool:
            reclamp_live()
            ram, vram = marginal_requirement(batch, jobs)
            return authority.admits_requirement(
                ram_bytes=ram, vram_bytes=vram, concurrent_model_jobs=jobs
            )

        def record_failure(batch: int, jobs: int, failure_kind: str) -> None:
            authority.record(
                StaticInferenceOperatingPointEvidence(
                    batch_size=batch,
                    concurrent_model_jobs=jobs,
                    structures_per_second=0.0,
                    peak_ram_bytes=self.provider_pool_resident_ram_bytes,
                    peak_vram_bytes=self.provider_pool_resident_vram_bytes,
                    feasible=False,
                    failure_kind=failure_kind,
                )
            )

        def prepare_wave(batch: int, jobs: int) -> str | None:
            # A smaller operating point must not inherit a larger explored
            # pool's residency. Retire first so its marginal requirement is
            # interpreted in that point's own coordinate.
            self._retire_private_providers(keep_jobs=jobs)
            if not fresh_admission(batch, jobs):
                return "live-resource"
            try:
                self._ensure_provider_pool(
                    jobs,
                    admit_next_slot=lambda: fresh_admission(batch, jobs),
                )
            except BaseException as exc:
                if isinstance(exc, TrainingDataInputError) and "next private provider slot" in str(exc):
                    return "live-resource"
                if self._is_oom(exc):
                    return "provider-pool-oom"
                raise
            # Materialization itself can consume more than the conservative
            # estimate. Re-clamp and admit the transient immediately before the
            # worker barrier is entered.
            return None if fresh_admission(batch, jobs) else "live-resource"

        reclamp_live()

        calibration_started = time.perf_counter()
        if not authority.reused_compatible_profile:
            report_inference_worker_phase("static inference calibration: start")
            for batch, jobs in authority.candidate_operating_points(
                available_structures=len(values),
                concurrency_available=self.provider_factory is not None,
            ):
                _raise_if_static_inference_cancelled("static inference calibration wave")
                if batch > authority.learned_safe_batch_ceiling:
                    continue
                count = batch * jobs
                failure = prepare_wave(batch, jobs)
                if failure is not None:
                    record_failure(batch, jobs, failure)
                    continue
                try:
                    wave = self._run_joint_wave(
                        values[:count],
                        None if identities is None else identities[:count],
                        batch_size=batch,
                        concurrent_jobs=jobs,
                    )
                except BaseException as exc:
                    if not self._is_oom(exc):
                        raise
                    record_failure(batch, jobs, "execution-oom")
                    self._release_cuda_cache()
                    continue
                (
                    _, elapsed, peak_ram, peak_vram, observed, safe_ceiling, backoffs,
                    resident_ram, resident_vram, execution_ram, execution_vram,
                ) = wave
                feasible = backoffs == 0 and safe_ceiling >= batch
                completed = count if feasible else 0
                authority.record(
                    StaticInferenceOperatingPointEvidence(
                        batch_size=batch,
                        concurrent_model_jobs=jobs,
                        structures_per_second=completed / elapsed if completed else 0.0,
                        peak_ram_bytes=peak_ram,
                        peak_vram_bytes=peak_vram,
                        feasible=feasible,
                        failure_kind=None if feasible else "execution-oom",
                        completed_structures=completed,
                        elapsed_seconds=elapsed if completed else 0.0,
                        observed_max_active_jobs=observed,
                        provider_pool_resident_ram_bytes=resident_ram,
                        provider_pool_resident_vram_bytes=resident_vram,
                        execution_peak_ram_bytes=execution_ram,
                        execution_peak_vram_bytes=execution_vram,
                    )
                )
            report_inference_worker_phase(
                "static inference calibration: complete "
                f"({time.perf_counter() - calibration_started:.3f}s)"
            )
        else:
            report_inference_worker_phase("static inference calibration: reused compatible profile (0.000s)")

        def select_available(
            excluded: set[tuple[int, int]], remaining: int
        ) -> StaticInferenceOperatingPointEvidence | None:
            candidates = [
                point
                for point in authority.evidence
                if authority._safe(point)
                and (point.batch_size, point.concurrent_model_jobs) not in excluded
                and point.batch_size * point.concurrent_model_jobs <= remaining
            ]
            if not candidates:
                return None
            peak = max(point.structures_per_second for point in candidates)
            floor = peak * (1.0 - authority.throughput_tolerance_fraction)
            return min(
                (point for point in candidates if point.structures_per_second >= floor),
                key=lambda point: (
                    point.peak_ram_bytes,
                    -1 if point.peak_vram_bytes is None else point.peak_vram_bytes,
                    point.concurrent_model_jobs,
                    point.batch_size,
                    -point.structures_per_second,
                ),
            )

        result: list[AtomicModelPrediction] = []
        position = 0
        production_started = time.perf_counter()
        report_inference_worker_phase("static inference production: start")
        while position < len(values):
            _raise_if_static_inference_cancelled("static inference production wave")
            remaining = len(values) - position
            excluded: set[tuple[int, int]] = set()
            while True:
                _raise_if_static_inference_cancelled("static inference operating-point admission")
                selected = select_available(excluded, remaining)
                if selected is None:
                    raise TrainingDataInputError(
                        "no future prediction is admissible from the measured static inference operating points."
                    )
                jobs = min(selected.concurrent_model_jobs, remaining // selected.batch_size)
                if jobs == 0:
                    saved = self.runtime_authority
                    self.runtime_authority = None
                    try:
                        result.extend(self._predict_owned(
                            values[position:],
                            geometry_identities=None if identities is None else identities[position:],
                        ))
                    finally:
                        self.runtime_authority = saved
                    position = len(values)
                    break
                failure = prepare_wave(selected.batch_size, jobs)
                if failure is not None:
                    record_failure(selected.batch_size, jobs, failure)
                    excluded.add((selected.batch_size, jobs))
                    continue
                try:
                    wave = self._run_joint_wave(
                        values[position:position + jobs * selected.batch_size],
                        None if identities is None else identities[position:position + jobs * selected.batch_size],
                        batch_size=selected.batch_size,
                        concurrent_jobs=jobs,
                    )
                except BaseException as exc:
                    if not self._is_oom(exc):
                        raise
                    record_failure(selected.batch_size, jobs, "execution-oom")
                    self._release_cuda_cache()
                    excluded.add((selected.batch_size, jobs))
                    continue
                (
                    predicted, elapsed, peak_ram, peak_vram, observed, safe_ceiling,
                    backoffs, resident_ram, resident_vram, execution_ram, execution_vram,
                ) = wave
                if observed != jobs:
                    raise TrainingDataInputError(
                        "Static inference execution did not realize selected model-job concurrency."
                    )
                if backoffs > 0 or safe_ceiling < selected.batch_size:
                    # A successful worker-local subdivision remains valid for
                    # this wave, but its causal capability evidence belongs to
                    # the requested two-dimensional operating point.  The
                    # authority keeps J=1 ceilings separate from J>1 bounds.
                    authority.record(
                        StaticInferenceOperatingPointEvidence(
                            batch_size=selected.batch_size,
                            concurrent_model_jobs=jobs,
                            structures_per_second=0.0,
                            peak_ram_bytes=peak_ram,
                            peak_vram_bytes=peak_vram,
                            feasible=False,
                            failure_kind="execution-oom",
                            completed_structures=0,
                            elapsed_seconds=0.0,
                            observed_max_active_jobs=observed,
                            provider_pool_resident_ram_bytes=resident_ram,
                            provider_pool_resident_vram_bytes=resident_vram,
                            execution_peak_ram_bytes=execution_ram,
                            execution_peak_vram_bytes=execution_vram,
                        )
                    )
                result.extend(predicted)
                position += jobs * selected.batch_size
                break
        report_inference_worker_phase(
            "static inference production: complete "
            f"({time.perf_counter() - production_started:.3f}s)"
        )
        return tuple(result)

    def predict(
        self,
        atoms: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
    ) -> tuple[AtomicModelPrediction, ...]:
        """Predict serially with one executor-owned mutable model shell."""

        if not self._execution_lock.acquire(blocking=False):
            raise TrainingDataInputError(
                "A StaticMaceInferenceExecutor/model shell cannot be shared across concurrent workers."
            )
        try:
            if self.runtime_authority is not None:
                return self._predict_joint_owned(
                    atoms, geometry_identities=geometry_identities
                )
            return self._predict_owned(atoms, geometry_identities=geometry_identities)
        finally:
            self._execution_lock.release()

    def prediction_channels(
        self,
        atoms: Sequence[Any],
        *,
        geometry_identities: Sequence[str] | None = None,
    ) -> dict[str, np.ndarray]:
        predictions = self.predict(atoms, geometry_identities=geometry_identities)
        energies = np.asarray([value.energy_ev for value in predictions], dtype=np.float64)
        forces = np.concatenate([
            np.asarray(value.forces_ev_per_angstrom, dtype=np.float64).reshape(-1)
            for value in predictions
        ])
        result = {"energy": energies, "forces": forces}
        if all(value.stress_ev_per_angstrom3 is not None for value in predictions):
            result["stress"] = np.stack([
                np.asarray(value.stress_ev_per_angstrom3, dtype=np.float64)
                for value in predictions
            ])
        return result


@dataclass(frozen=True, slots=True)
class MaceDescriptorFileRecord:
    frame_uid: str
    frame_record_digest: str
    checkpoint_identity_digest: str
    descriptor_policy_digest: str
    relative_path: str
    shape: tuple[int, int]
    dtype: str
    file_sha256: str
    array_content_digest: str
    storage_kind: str = "npy"
    shard_index: int | None = None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "frame_uid", "frame_record_digest", "checkpoint_identity_digest",
            "descriptor_policy_digest", "file_sha256", "array_content_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        path = Path(self.relative_path)
        if path.is_absolute() or ".." in path.parts or self.relative_path in {"", "."}:
            raise TrainingDataInputError("Descriptor relative_path must remain inside the cache root.")
        shape = tuple(int(v) for v in self.shape)
        if len(shape) != 2 or any(v <= 0 for v in shape):
            raise TrainingDataInputError("Descriptor shape must contain two positive dimensions.")
        dtype = np.dtype(self.dtype)
        if dtype.kind != "f":
            raise TrainingDataInputError("Descriptor dtype must be floating point.")
        storage_kind = str(self.storage_kind)
        if storage_kind not in {"npy", "npz_shard"}:
            raise TrainingDataInputError("Unsupported descriptor storage kind.")
        shard_index = None if self.shard_index is None else int(self.shard_index)
        if storage_kind == "npz_shard":
            if shard_index is None or shard_index < 0:
                raise TrainingDataInputError("Descriptor shard records require a non-negative shard index.")
        elif shard_index is not None:
            raise TrainingDataInputError("Standalone descriptor records cannot define shard_index.")
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "dtype", dtype.name)
        object.__setattr__(self, "storage_kind", storage_kind)
        object.__setattr__(self, "shard_index", shard_index)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DESCRIPTOR_FILE_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "checkpoint_identity_digest": self.checkpoint_identity_digest,
            "descriptor_policy_digest": self.descriptor_policy_digest,
            "relative_path": self.relative_path,
            "shape": list(self.shape),
            "dtype": self.dtype,
            "file_sha256": self.file_sha256,
            "array_content_digest": self.array_content_digest,
            "storage_kind": self.storage_kind,
            "shard_index": self.shard_index,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDescriptorFileRecord":
        schema = payload.get("schema")
        if schema not in {MACE_DESCRIPTOR_FILE_RECORD_SCHEMA, MACE_DESCRIPTOR_FILE_RECORD_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE descriptor-file schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            checkpoint_identity_digest=str(payload["checkpoint_identity_digest"]),
            descriptor_policy_digest=str(payload["descriptor_policy_digest"]),
            relative_path=str(payload["relative_path"]),
            shape=tuple(int(v) for v in payload["shape"]),
            dtype=str(payload["dtype"]),
            file_sha256=str(payload["file_sha256"]),
            array_content_digest=str(payload["array_content_digest"]),
            storage_kind=str(payload.get("storage_kind", "npy")),
            shard_index=None if payload.get("shard_index") is None else int(payload["shard_index"]),
        )
        supplied = payload.get("content_digest")
        if schema == MACE_DESCRIPTOR_FILE_RECORD_LEGACY_SCHEMA:
            legacy = {
                "schema": MACE_DESCRIPTOR_FILE_RECORD_LEGACY_SCHEMA,
                "frame_uid": result.frame_uid,
                "frame_record_digest": result.frame_record_digest,
                "checkpoint_identity_digest": result.checkpoint_identity_digest,
                "descriptor_policy_digest": result.descriptor_policy_digest,
                "relative_path": result.relative_path,
                "shape": list(result.shape),
                "dtype": result.dtype,
                "file_sha256": result.file_sha256,
                "array_content_digest": result.array_content_digest,
            }
            expected = digest(legacy)
        else:
            expected = result.content_digest
        if supplied not in (None, expected):
            raise TrainingDataSerializationError("MACE descriptor-file digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceDescriptorManifest:
    dataset_id: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    checkpoint_identity: ModelCheckpointIdentity
    policy: MaceDescriptorPolicy
    records: tuple[MaceDescriptorFileRecord, ...]
    excluded_frame_uids: tuple[str, ...] = ()
    signature: MaceDescriptorSignature | None = None
    serialization_schema: str = field(default=MACE_DESCRIPTOR_MANIFEST_SCHEMA, repr=False, compare=False)
    _by_frame_uid: Mapping[str, MaceDescriptorFileRecord] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_catalog_digest", "data5_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        records = tuple(self.records)
        uids = tuple(item.frame_uid for item in records)
        if any(left >= right for left, right in zip(uids, uids[1:])):
            records = tuple(sorted(records, key=lambda item: item.frame_uid))
            uids = tuple(item.frame_uid for item in records)
        if any(left == right for left, right in zip(uids, uids[1:])):
            raise TrainingDataInputError("MACE descriptor frame UIDs must be unique.")
        if any(item.checkpoint_identity_digest != self.checkpoint_identity.content_digest for item in records):
            raise TrainingDataInputError("MACE descriptor checkpoint mismatch.")
        if any(item.descriptor_policy_digest != self.policy.policy_digest for item in records):
            raise TrainingDataInputError("MACE descriptor policy mismatch.")
        if self.serialization_schema not in {
            MACE_DESCRIPTOR_MANIFEST_SCHEMA,
            MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA,
        }:
            raise TrainingDataInputError("Unsupported MACE descriptor-manifest serialization schema.")
        if self.signature is None:
            # Historical/fake-provider callers remain readable and digest-stable.
            object.__setattr__(self, "serialization_schema", MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA)
        elif self.serialization_schema == MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA:
            raise TrainingDataInputError("Legacy descriptor manifests cannot carry a descriptor signature.")
        else:
            expected_width = int(self.signature.returned_per_atom_dimension)
            if any(item.shape[1] != expected_width for item in records):
                raise TrainingDataInputError("MACE descriptor record width does not match the descriptor signature.")
            if self.signature.invariants_only != self.policy.invariants_only:
                raise TrainingDataInputError("MACE descriptor signature/policy invariants_only mismatch.")
            expected_layers = self.signature.num_layers
            observed_layers = (
                self.signature.num_interactions
                if self.policy.num_layers is None
                else int(self.policy.num_layers)
            )
            if expected_layers != observed_layers:
                raise TrainingDataInputError("MACE descriptor signature/policy layer-count mismatch.")
        excluded = tuple(sorted(set(validate_digest(v, name="excluded_frame_uid") for v in self.excluded_frame_uids)))
        if set(excluded) & {item.frame_uid for item in records}:
            raise TrainingDataInputError("Descriptor frames cannot also be excluded.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "excluded_frame_uids", excluded)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in records})

    def for_frame(self, frame_uid: str) -> MaceDescriptorFileRecord:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "checkpoint_identity": self.checkpoint_identity.to_dict(),
            "policy": self.policy.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "excluded_frame_uids": list(self.excluded_frame_uids),
        }
        if self.serialization_schema == MACE_DESCRIPTOR_MANIFEST_SCHEMA:
            payload["signature"] = self.signature.to_dict() if self.signature is not None else None
        return payload

    def _digest_payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "checkpoint_identity_digest": self.checkpoint_identity.content_digest,
            "policy_digest": self.policy.policy_digest,
            "record_digests": [item.content_digest for item in self.records],
            "excluded_frame_uids": list(self.excluded_frame_uids),
        }
        if self.serialization_schema == MACE_DESCRIPTOR_MANIFEST_SCHEMA:
            payload["signature_digest"] = self.signature.content_digest if self.signature is not None else None
        return payload

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(self._digest_payload())
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDescriptorManifest":
        schema = payload.get("schema")
        if schema not in {MACE_DESCRIPTOR_MANIFEST_SCHEMA, MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE descriptor-manifest schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            checkpoint_identity=ModelCheckpointIdentity.from_dict(payload["checkpoint_identity"]),
            policy=MaceDescriptorPolicy.from_dict(payload["policy"]),
            records=tuple(MaceDescriptorFileRecord.from_dict(item) for item in payload["records"]),
            excluded_frame_uids=tuple(str(v) for v in payload.get("excluded_frame_uids", ())),
            signature=(
                None
                if schema == MACE_DESCRIPTOR_MANIFEST_V1_SCHEMA or payload.get("signature") is None
                else MaceDescriptorSignature.from_dict(payload["signature"])
            ),
            serialization_schema=str(schema),
        )
        supplied = payload.get("content_digest")
        legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied not in (None, result.content_digest, legacy_digest):
            raise TrainingDataSerializationError("MACE descriptor-manifest digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SpeciesPredictionSummary:
    atomic_number: int
    symbol: str
    atom_count: int
    force_norm_mean_ev_per_angstrom: float
    force_norm_max_ev_per_angstrom: float
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.atomic_number <= 0 or self.atom_count <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid species prediction summary.")
        for name in ("force_norm_mean_ev_per_angstrom", "force_norm_max_ev_per_angstrom"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)

    def _payload(self) -> dict[str, Any]:
        return {
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "atom_count": self.atom_count,
            "force_norm_mean_ev_per_angstrom": self.force_norm_mean_ev_per_angstrom,
            "force_norm_max_ev_per_angstrom": self.force_norm_max_ev_per_angstrom,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesPredictionSummary":
        result = cls(
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            atom_count=int(payload["atom_count"]),
            force_norm_mean_ev_per_angstrom=float(payload["force_norm_mean_ev_per_angstrom"]),
            force_norm_max_ev_per_angstrom=float(payload["force_norm_max_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Species prediction summary digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ModelPredictionSummary:
    frame_uid: str
    frame_record_digest: str
    checkpoint_identity_digest: str
    predicted_energy_ev: float
    force_component_rms_ev_per_angstrom: float
    force_norm_mean_ev_per_angstrom: float
    force_norm_max_ev_per_angstrom: float
    predicted_stress_ev_per_angstrom3: tuple[tuple[float, float, float], ...] | None
    forces_payload_digest: str
    species_summaries: tuple[SpeciesPredictionSummary, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "checkpoint_identity_digest", "forces_payload_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "predicted_energy_ev", "force_component_rms_ev_per_angstrom",
            "force_norm_mean_ev_per_angstrom", "force_norm_max_ev_per_angstrom",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or (name != "predicted_energy_ev" and value < 0.0):
                raise TrainingDataInputError(f"{name} is invalid.")
            object.__setattr__(self, name, value)
        if self.predicted_stress_ev_per_angstrom3 is not None:
            stress = _validate_float_array(self.predicted_stress_ev_per_angstrom3, name="predicted stress", shape=(3, 3))
            object.__setattr__(self, "predicted_stress_ev_per_angstrom3", tuple(tuple(float(v) for v in row) for row in stress))
        summaries = tuple(sorted(self.species_summaries, key=lambda item: item.atomic_number))
        object.__setattr__(self, "species_summaries", summaries)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MODEL_PREDICTION_SUMMARY_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "checkpoint_identity_digest": self.checkpoint_identity_digest,
            "predicted_energy_ev": self.predicted_energy_ev,
            "force_component_rms_ev_per_angstrom": self.force_component_rms_ev_per_angstrom,
            "force_norm_mean_ev_per_angstrom": self.force_norm_mean_ev_per_angstrom,
            "force_norm_max_ev_per_angstrom": self.force_norm_max_ev_per_angstrom,
            "predicted_stress_ev_per_angstrom3": None if self.predicted_stress_ev_per_angstrom3 is None else [list(row) for row in self.predicted_stress_ev_per_angstrom3],
            "forces_payload_digest": self.forces_payload_digest,
            "species_summaries": [item.to_dict() for item in self.species_summaries],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelPredictionSummary":
        if payload.get("schema") != MODEL_PREDICTION_SUMMARY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported model-prediction summary schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            checkpoint_identity_digest=str(payload["checkpoint_identity_digest"]),
            predicted_energy_ev=float(payload["predicted_energy_ev"]),
            force_component_rms_ev_per_angstrom=float(payload["force_component_rms_ev_per_angstrom"]),
            force_norm_mean_ev_per_angstrom=float(payload["force_norm_mean_ev_per_angstrom"]),
            force_norm_max_ev_per_angstrom=float(payload["force_norm_max_ev_per_angstrom"]),
            predicted_stress_ev_per_angstrom3=None if payload.get("predicted_stress_ev_per_angstrom3") is None else tuple(tuple(float(v) for v in row) for row in payload["predicted_stress_ev_per_angstrom3"]),
            forces_payload_digest=str(payload["forces_payload_digest"]),
            species_summaries=tuple(SpeciesPredictionSummary.from_dict(item) for item in payload["species_summaries"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Model-prediction summary digest mismatch.")
        return result


def summarize_prediction(
    record: Any,
    frame_data: Any,
    local_index: int,
    prediction: AtomicModelPrediction,
    checkpoint_identity: ModelCheckpointIdentity,
) -> ModelPredictionSummary:
    numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
    forces = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
    if forces.shape != (numbers.size, 3):
        raise TrainingDataInputError("Predicted force shape does not match frame atom count.")
    norms = np.linalg.norm(forces, axis=1)
    summaries = []
    for atomic_number in sorted(set(int(v) for v in numbers)):
        selected = norms[numbers == atomic_number]
        summaries.append(
            SpeciesPredictionSummary(
                atomic_number=atomic_number,
                symbol=chemical_symbols[atomic_number],
                atom_count=int(selected.size),
                force_norm_mean_ev_per_angstrom=float(np.mean(selected)),
                force_norm_max_ev_per_angstrom=float(np.max(selected)),
            )
        )
    return ModelPredictionSummary(
        frame_uid=record.frame_uid,
        frame_record_digest=record.content_digest,
        checkpoint_identity_digest=checkpoint_identity.content_digest,
        predicted_energy_ev=prediction.energy_ev,
        force_component_rms_ev_per_angstrom=float(np.sqrt(np.mean(forces**2))),
        force_norm_mean_ev_per_angstrom=float(np.mean(norms)),
        force_norm_max_ev_per_angstrom=float(np.max(norms)),
        predicted_stress_ev_per_angstrom3=None if prediction.stress_ev_per_angstrom3 is None else tuple(tuple(float(v) for v in row) for row in prediction.stress_ev_per_angstrom3),
        forces_payload_digest=_array_content_digest(forces),
        species_summaries=tuple(summaries),
    )


def build_mace_descriptor_manifest(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    provider: AtomicModelProvider,
    output_directory: str | Path,
    *,
    frame_uids: Sequence[str],
    excluded_frame_uids: Sequence[str] = (),
    policy: MaceDescriptorPolicy | None = None,
) -> MaceDescriptorManifest:
    """Write checkpoint-bound raw atomic descriptors to deterministic .npy sidecars."""

    if data5_bundle.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("DATA5/frame lineage mismatch.")
    active = MaceDescriptorPolicy() if policy is None else policy
    descriptor_signature = None
    if hasattr(provider, "descriptor_signature"):
        native_probe = getattr(provider, "_native_batch_supported", None)
        if native_probe is None or bool(native_probe()):
            descriptor_signature = provider.descriptor_signature(active)
    root = Path(output_directory)
    descriptor_root = root / "descriptors"
    descriptor_root.mkdir(parents=True, exist_ok=True)
    index = build_frame_array_index(frame_catalog, frame_data_by_run)
    records: list[MaceDescriptorFileRecord] = []
    supported = frozenset(provider.checkpoint_identity.supported_atomic_numbers)
    atomic_numbers_by_run = {
        str(run_id): frozenset(int(value) for value in frame_data.atomic_numbers)
        for run_id, frame_data in frame_data_by_run.items()
    }
    requested = tuple(sorted(set(validate_digest(v, name="frame_uid") for v in frame_uids)))
    excluded = tuple(sorted(set(validate_digest(v, name="excluded_frame_uid") for v in excluded_frame_uids)))
    if set(requested) & set(excluded):
        raise TrainingDataInputError("Requested and excluded descriptor frames overlap.")
    for frame_uid in requested:
        try:
            record, frame_data, local_index = index[frame_uid]
        except KeyError as exc:
            raise TrainingDataInputError(f"Unknown descriptor frame UID {frame_uid}.") from exc
        if supported:
            present = atomic_numbers_by_run[str(record.run_id)]
            if not present.issubset(supported):
                raise TrainingDataInputError("Checkpoint does not declare all frame elements.")
        atoms = ase_atoms_for_frame(record, frame_data, local_index)
        descriptor = provider.get_descriptors(atoms, active)
        relative = Path("descriptors") / f"{frame_uid}.npy"
        path = root / relative
        np.save(path, descriptor, allow_pickle=False)
        records.append(
            MaceDescriptorFileRecord(
                frame_uid=frame_uid,
                frame_record_digest=record.content_digest,
                checkpoint_identity_digest=provider.checkpoint_identity.content_digest,
                descriptor_policy_digest=active.policy_digest,
                relative_path=relative.as_posix(),
                shape=descriptor.shape,
                dtype=descriptor.dtype.name,
                file_sha256=_sha256_file(path),
                array_content_digest=_array_content_digest(descriptor),
            )
        )
    return MaceDescriptorManifest(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        checkpoint_identity=provider.checkpoint_identity,
        policy=active,
        records=tuple(records),
        excluded_frame_uids=excluded,
        signature=descriptor_signature,
    )


def _descriptor_array_from_record(
    record: MaceDescriptorFileRecord, root_directory: str | Path
) -> np.ndarray:
    path = Path(root_directory) / record.relative_path
    if not path.is_file():
        raise TrainingDataSerializationError("MACE descriptor sidecar is missing.")
    if record.storage_kind == "npz_shard":
        payload = _load_descriptor_shard(
            path,
            record.file_sha256,
            ("descriptor_offsets", "descriptor_values"),
        )
        try:
            offsets = np.asarray(payload["descriptor_offsets"], dtype=np.int64)
            values = np.asarray(payload["descriptor_values"])
            index = int(record.shard_index)
            start = int(offsets[index])
            stop = int(offsets[index + 1])
            array = values[start:stop]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise TrainingDataSerializationError("MACE descriptor shard index is invalid.") from exc
    else:
        if _sha256_file(path) != record.file_sha256:
            raise TrainingDataSerializationError("MACE descriptor sidecar SHA-256 mismatch.")
        try:
            array = np.load(path, mmap_mode="r", allow_pickle=False)
        except Exception as exc:
            raise TrainingDataSerializationError("Cannot read MACE descriptor sidecar.") from exc
    if array.shape != record.shape or array.dtype.name != record.dtype:
        raise TrainingDataSerializationError("MACE descriptor sidecar shape or dtype mismatch.")
    if np.any(~np.isfinite(array)) or _array_content_digest(array) != record.array_content_digest:
        raise TrainingDataSerializationError("MACE descriptor sidecar content mismatch.")
    result = np.asarray(array)
    result.setflags(write=False)
    return result


def read_mace_descriptor_record_array(
    record: MaceDescriptorFileRecord, root_directory: str | Path
) -> np.ndarray:
    return _descriptor_array_from_record(record, root_directory)


def read_mace_descriptor_array(
    manifest: MaceDescriptorManifest,
    root_directory: str | Path,
    frame_uid: str,
) -> np.ndarray:
    return read_mace_descriptor_record_array(manifest.for_frame(frame_uid), root_directory)


def read_mace_descriptor_summary_rows(
    manifest: MaceDescriptorManifest,
    root_directory: str | Path,
    frame_uids: Sequence[str],
    species_atomic_numbers: Sequence[int],
) -> tuple[np.ndarray, np.ndarray] | None:
    """Gather persisted descriptor-summary rows shard by shard.

    Returns ``None`` when any requested record uses a legacy layout or a shard
    without summary members, allowing callers to preserve the established
    on-demand reduction fallback.
    """

    requested_uids = tuple(str(uid) for uid in frame_uids)
    if not requested_uids:
        return np.empty((0, 0), dtype=np.float64), np.empty((0, 0), dtype=np.bool_)
    try:
        records = tuple(manifest.for_frame(uid) for uid in requested_uids)
    except (AttributeError, KeyError):
        return None
    if any(record.storage_kind != "npz_shard" for record in records):
        return None
    groups: dict[tuple[str, str], list[tuple[int, MaceDescriptorFileRecord]]] = {}
    for output_index, record in enumerate(records):
        groups.setdefault(
            (record.relative_path, record.file_sha256), []
        ).append((output_index, record))
    species = tuple(int(value) for value in species_atomic_numbers)
    summary_members = (
        "summary_global_mean",
        "summary_global_std",
        "summary_species_atomic_numbers",
        "summary_species_present",
        "summary_species_mean",
    )
    values_matrix: np.ndarray | None = None
    missing_matrix: np.ndarray | None = None
    descriptor_dimension: int | None = None
    root = Path(root_directory)
    for (relative_path, expected_sha256), group in groups.items():
        try:
            payload = _load_descriptor_shard(
                root / relative_path, expected_sha256, summary_members
            )
        except TrainingDataSerializationError:
            return None
        global_mean = np.asarray(payload["summary_global_mean"])
        global_std = np.asarray(payload["summary_global_std"])
        shard_species = np.asarray(
            payload["summary_species_atomic_numbers"], dtype=np.int32
        )
        present = np.asarray(payload["summary_species_present"], dtype=np.bool_)
        species_mean = np.asarray(payload["summary_species_mean"])
        current_dimension = int(global_mean.shape[1])
        if descriptor_dimension is None:
            descriptor_dimension = current_dimension
            output_dimension = (
                2 * descriptor_dimension
                + len(species) * (descriptor_dimension + 1)
            )
            values_matrix = np.empty(
                (len(requested_uids), output_dimension), dtype=np.float64
            )
            missing_matrix = np.zeros(
                (len(requested_uids), output_dimension), dtype=np.bool_
            )
        elif descriptor_dimension != current_dimension:
            raise TrainingDataSerializationError(
                "MACE descriptor-summary dimension changed across shards."
            )
        output_indices = np.fromiter(
            (item[0] for item in group), dtype=np.int64, count=len(group)
        )
        shard_indices = np.fromiter(
            (int(item[1].shard_index) for item in group),
            dtype=np.int64,
            count=len(group),
        )
        assert values_matrix is not None and missing_matrix is not None
        d = descriptor_dimension
        values_matrix[output_indices, :d] = global_mean[shard_indices]
        values_matrix[output_indices, d : 2 * d] = global_std[shard_indices]
        by_species = {int(z): index for index, z in enumerate(shard_species)}
        cursor = 2 * d
        for atomic_number in species:
            position = by_species.get(atomic_number)
            if position is None:
                values_matrix[output_indices, cursor] = 0.0
                values_matrix[output_indices, cursor + 1 : cursor + 1 + d] = 0.0
                missing_matrix[output_indices, cursor + 1 : cursor + 1 + d] = True
            else:
                row_present = present[shard_indices, position]
                values_matrix[output_indices, cursor] = row_present.astype(
                    np.float64, copy=False
                )
                values_matrix[
                    output_indices, cursor + 1 : cursor + 1 + d
                ] = 0.0
                if np.any(row_present):
                    values_matrix[
                        output_indices[row_present],
                        cursor + 1 : cursor + 1 + d,
                    ] = species_mean[
                        shard_indices[row_present], position
                    ]
                missing_matrix[
                    output_indices, cursor + 1 : cursor + 1 + d
                ] = ~row_present[:, None]
            cursor += d + 1
    assert values_matrix is not None and missing_matrix is not None
    values_matrix.setflags(write=False)
    missing_matrix.setflags(write=False)
    return values_matrix, missing_matrix


def read_mace_descriptor_summary(
    manifest: MaceDescriptorManifest,
    root_directory: str | Path,
    frame_uid: str,
    species_atomic_numbers: Sequence[int],
) -> tuple[np.ndarray, np.ndarray] | None:
    """Read a persisted DATA6 descriptor summary when the shard provides one.

    The summary is independent of DATA7 domain membership: each descriptor shard
    stores global mean/std plus per-species means for the union of species in that
    shard. Missing species requested by a downstream domain are emitted as zero
    values with a true missing indicator, matching the legacy on-demand reduction.
    """

    if not hasattr(manifest, "for_frame"):
        return None
    record = manifest.for_frame(frame_uid)
    if record.storage_kind != "npz_shard":
        return None
    path = Path(root_directory) / record.relative_path
    summary_members = (
        "summary_global_mean",
        "summary_global_std",
        "summary_species_atomic_numbers",
        "summary_species_present",
        "summary_species_mean",
    )
    try:
        payload = _load_descriptor_shard(
            path, record.file_sha256, summary_members
        )
    except TrainingDataSerializationError:
        # Legacy or externally generated v2 shards may not contain persisted
        # summaries.  Preserve the established fallback to on-demand reduction.
        return None
    index = int(record.shard_index)
    global_mean = np.asarray(payload["summary_global_mean"])[index]
    global_std = np.asarray(payload["summary_global_std"])[index]
    shard_species = np.asarray(payload["summary_species_atomic_numbers"], dtype=np.int32)
    present = np.asarray(payload["summary_species_present"], dtype=np.bool_)[index]
    species_mean = np.asarray(payload["summary_species_mean"])[index]
    by_species = {int(z): position for position, z in enumerate(shard_species)}
    descriptor_dimension = int(global_mean.size)
    values = np.empty(
        2 * descriptor_dimension
        + len(tuple(species_atomic_numbers)) * (descriptor_dimension + 1),
        dtype=np.float64,
    )
    missing = np.zeros(values.shape, dtype=np.bool_)
    cursor = 0
    values[cursor : cursor + descriptor_dimension] = global_mean
    cursor += descriptor_dimension
    values[cursor : cursor + descriptor_dimension] = global_std
    cursor += descriptor_dimension
    for atomic_number in species_atomic_numbers:
        position = by_species.get(int(atomic_number))
        is_present = position is not None and bool(present[position])
        values[cursor] = float(is_present)
        cursor += 1
        if is_present:
            values[cursor : cursor + descriptor_dimension] = species_mean[position]
        else:
            values[cursor : cursor + descriptor_dimension] = 0.0
            missing[cursor : cursor + descriptor_dimension] = True
        cursor += descriptor_dimension
    values.setflags(write=False)
    missing.setflags(write=False)
    return values, missing
