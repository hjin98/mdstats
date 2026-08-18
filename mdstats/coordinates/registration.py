"""Stage-C0A2 affine registration and registered coordinate products."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence

import numpy as np

from ..collection import AtomisticFrameCollection
from .contracts import (
    ForceAdmissibilityContract,
    GeometricForceTransformStatus,
    PMFForceAdmissibilityStatus,
    ReferenceCellDefinition,
)
from .metric_geometry import (
    AnalysisGeometryMetric,
    ClosestImageAmbiguityError,
    ClosestImageOptions,
    RegistrationFitMetric,
    closest_periodic_image,
)
from .periodic_gauge import (
    SourceCoordinateContract,
    build_periodic_lattice_gauge,
    prepare_source_coordinate_contract,
)

FRAME_REGISTRATION_POLICY_SCHEMA = "mdstats.frame-registration-policy.v1"
REFERENCE_TRANSLATION_GAUGE_SCHEMA = "mdstats.reference-translation-gauge.v1"
TRANSLATION_BRANCH_LIFT_SCHEMA = "mdstats.translation-branch-lift.v1"
FRAME_REGISTRATION_RESULT_SCHEMA = "mdstats.frame-registration-result.v1"
FRAME_REGISTRATION_DIGEST_ALGORITHM = "sha256-canonical-json-and-array-bytes-v1"


class FrameRegistrationError(ValueError):
    """Base exception for Stage-C0A2 registration."""


class RegistrationPolicyError(FrameRegistrationError):
    """Raised when a requested registration policy is incomplete or inconsistent."""


class ReferenceTranslationError(FrameRegistrationError):
    """Raised when one uniform periodic reference translation cannot be certified."""


class TranslationBranchAmbiguityError(FrameRegistrationError):
    """Raised when a continuous translation branch cannot be chosen uniquely."""


class RegistrationValidationError(FrameRegistrationError):
    """Raised when affine, round-trip, fixed-domain, or work validation fails."""


class RegistrationSpatialPolicy(str, Enum):
    PHYSICAL = "physical"
    TRANSLATION_REGISTERED = "translation_registered"
    REFERENCE_MATERIAL = "reference_material"


class TranslationMode(str, Enum):
    NONE = "none"
    MATCHED_REFERENCE = "matched_reference"


class ReferenceWeighting(str, Enum):
    CENTER_OF_GEOMETRY = "center_of_geometry"
    CENTER_OF_MASS = "center_of_mass"
    EXPLICIT = "explicit"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _readonly_array(
    value: object,
    *,
    dtype: np.dtype | type,
    shape_suffix: tuple[int, ...],
    name: str,
) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True)
    if array.ndim < len(shape_suffix) or tuple(array.shape[-len(shape_suffix) :]) != shape_suffix:
        raise RegistrationValidationError(
            f"{name} must end with shape {shape_suffix}; received {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and not np.all(np.isfinite(array)):
        raise RegistrationValidationError(f"{name} contains non-finite values.")
    array.setflags(write=False)
    return array


def _enum(enum_type: type[Enum], value: object, *, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise RegistrationPolicyError(f"{name} must be one of: {allowed}.") from exc


def _indices_tuple(value: Sequence[int] | np.ndarray, *, name: str) -> tuple[int, ...]:
    result = tuple(int(item) for item in value)
    if not result:
        raise RegistrationPolicyError(f"{name} must not be empty.")
    if len(set(result)) != len(result) or min(result) < 0:
        raise RegistrationPolicyError(
            f"{name} must contain unique nonnegative atom indices."
        )
    return result


@dataclass(frozen=True, slots=True)
class ReferenceTranslationOptions:
    convergence_tolerance: float = 1.0e-11
    candidate_deduplication_tolerance: float = 1.0e-9
    competing_minimum_tolerance: float = 1.0e-9
    maximum_residual: float | None = 1.0
    maximum_iterations: int = 64

    def __post_init__(self) -> None:
        for name in (
            "convergence_tolerance",
            "candidate_deduplication_tolerance",
            "competing_minimum_tolerance",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise RegistrationPolicyError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if self.maximum_residual is not None:
            residual = float(self.maximum_residual)
            if not np.isfinite(residual) or residual <= 0.0:
                raise RegistrationPolicyError(
                    "maximum_residual must be positive or None."
                )
            object.__setattr__(self, "maximum_residual", residual)
        if isinstance(self.maximum_iterations, bool) or int(self.maximum_iterations) < 1:
            raise RegistrationPolicyError("maximum_iterations must be positive.")
        object.__setattr__(self, "maximum_iterations", int(self.maximum_iterations))

    def to_dict(self) -> dict[str, Any]:
        return {
            "convergence_tolerance": self.convergence_tolerance,
            "candidate_deduplication_tolerance": self.candidate_deduplication_tolerance,
            "competing_minimum_tolerance": self.competing_minimum_tolerance,
            "maximum_residual": self.maximum_residual,
            "maximum_iterations": self.maximum_iterations,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceTranslationOptions":
        return cls(
            convergence_tolerance=float(payload["convergence_tolerance"]),
            candidate_deduplication_tolerance=float(
                payload["candidate_deduplication_tolerance"]
            ),
            competing_minimum_tolerance=float(payload["competing_minimum_tolerance"]),
            maximum_residual=(
                None
                if payload.get("maximum_residual") is None
                else float(payload["maximum_residual"])
            ),
            maximum_iterations=int(payload["maximum_iterations"]),
        )


@dataclass(frozen=True, slots=True)
class FrameRegistrationPolicy:
    spatial_policy: RegistrationSpatialPolicy = RegistrationSpatialPolicy.PHYSICAL
    translation_mode: TranslationMode = TranslationMode.NONE
    reference_atom_indices: tuple[int, ...] = ()
    reference_frame_index: int = 0
    reference_weighting: ReferenceWeighting = ReferenceWeighting.CENTER_OF_GEOMETRY
    explicit_reference_weights: tuple[float, ...] | None = None
    force_target_atom_indices: tuple[int, ...] | None = None
    segment_reset_frame_indices: tuple[int, ...] = ()
    require_fixed_registered_cell: bool = False
    fixed_cell_relative_tolerance: float = 1.0e-10
    round_trip_tolerance: float = 1.0e-10
    translation_options: ReferenceTranslationOptions = ReferenceTranslationOptions()
    closest_image_options: ClosestImageOptions = ClosestImageOptions()
    signature: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "spatial_policy",
            _enum(RegistrationSpatialPolicy, self.spatial_policy, name="spatial_policy"),
        )
        object.__setattr__(
            self,
            "translation_mode",
            _enum(TranslationMode, self.translation_mode, name="translation_mode"),
        )
        object.__setattr__(
            self,
            "reference_weighting",
            _enum(
                ReferenceWeighting,
                self.reference_weighting,
                name="reference_weighting",
            ),
        )
        reference_indices = tuple(int(item) for item in self.reference_atom_indices)
        if self.translation_mode is TranslationMode.MATCHED_REFERENCE:
            reference_indices = _indices_tuple(
                reference_indices, name="reference_atom_indices"
            )
        elif reference_indices:
            raise RegistrationPolicyError(
                "reference_atom_indices require translation_mode='matched_reference'."
            )
        if self.reference_frame_index < 0:
            raise RegistrationPolicyError("reference_frame_index must be nonnegative.")
        explicit_weights = self.explicit_reference_weights
        if self.reference_weighting is ReferenceWeighting.EXPLICIT:
            if explicit_weights is None:
                raise RegistrationPolicyError(
                    "Explicit reference weighting requires explicit_reference_weights."
                )
            explicit_weights = tuple(float(item) for item in explicit_weights)
            if len(explicit_weights) != len(reference_indices):
                raise RegistrationPolicyError(
                    "explicit_reference_weights must match reference_atom_indices."
                )
            if not all(np.isfinite(item) and item > 0.0 for item in explicit_weights):
                raise RegistrationPolicyError(
                    "explicit_reference_weights must be finite and positive."
                )
        elif explicit_weights is not None:
            raise RegistrationPolicyError(
                "explicit_reference_weights are only valid for explicit weighting."
            )
        target_indices = self.force_target_atom_indices
        if target_indices is not None:
            target_indices = _indices_tuple(target_indices, name="force_target_atom_indices")
        reset_indices = tuple(sorted(set(int(item) for item in self.segment_reset_frame_indices)))
        if any(item < 0 for item in reset_indices):
            raise RegistrationPolicyError(
                "segment_reset_frame_indices must be nonnegative."
            )
        for name in ("fixed_cell_relative_tolerance", "round_trip_tolerance"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise RegistrationPolicyError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if not isinstance(self.translation_options, ReferenceTranslationOptions):
            raise RegistrationPolicyError(
                "translation_options must be ReferenceTranslationOptions."
            )
        if not isinstance(self.closest_image_options, ClosestImageOptions):
            raise RegistrationPolicyError("closest_image_options must be ClosestImageOptions.")
        payload = {
            "schema": FRAME_REGISTRATION_POLICY_SCHEMA,
            "spatial_policy": self.spatial_policy.value,
            "translation_mode": self.translation_mode.value,
            "reference_atom_indices": list(reference_indices),
            "reference_frame_index": int(self.reference_frame_index),
            "reference_weighting": self.reference_weighting.value,
            "explicit_reference_weights": (
                None if explicit_weights is None else list(explicit_weights)
            ),
            "force_target_atom_indices": (
                None if target_indices is None else list(target_indices)
            ),
            "segment_reset_frame_indices": list(reset_indices),
            "require_fixed_registered_cell": bool(self.require_fixed_registered_cell),
            "fixed_cell_relative_tolerance": self.fixed_cell_relative_tolerance,
            "round_trip_tolerance": self.round_trip_tolerance,
            "translation_options": self.translation_options.to_dict(),
            "closest_image_options": self.closest_image_options.to_dict(),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise RegistrationPolicyError("Frame-registration policy signature is inconsistent.")
        object.__setattr__(self, "reference_atom_indices", reference_indices)
        object.__setattr__(self, "reference_frame_index", int(self.reference_frame_index))
        object.__setattr__(self, "explicit_reference_weights", explicit_weights)
        object.__setattr__(self, "force_target_atom_indices", target_indices)
        object.__setattr__(self, "segment_reset_frame_indices", reset_indices)
        object.__setattr__(
            self, "require_fixed_registered_cell", bool(self.require_fixed_registered_cell)
        )
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FRAME_REGISTRATION_POLICY_SCHEMA,
            "spatial_policy": self.spatial_policy.value,
            "translation_mode": self.translation_mode.value,
            "reference_atom_indices": list(self.reference_atom_indices),
            "reference_frame_index": self.reference_frame_index,
            "reference_weighting": self.reference_weighting.value,
            "explicit_reference_weights": (
                None
                if self.explicit_reference_weights is None
                else list(self.explicit_reference_weights)
            ),
            "force_target_atom_indices": (
                None
                if self.force_target_atom_indices is None
                else list(self.force_target_atom_indices)
            ),
            "segment_reset_frame_indices": list(self.segment_reset_frame_indices),
            "require_fixed_registered_cell": self.require_fixed_registered_cell,
            "fixed_cell_relative_tolerance": self.fixed_cell_relative_tolerance,
            "round_trip_tolerance": self.round_trip_tolerance,
            "translation_options": self.translation_options.to_dict(),
            "closest_image_options": self.closest_image_options.to_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRegistrationPolicy":
        if payload.get("schema") != FRAME_REGISTRATION_POLICY_SCHEMA:
            raise RegistrationPolicyError("Unsupported frame-registration policy schema.")
        return cls(
            spatial_policy=payload["spatial_policy"],
            translation_mode=payload["translation_mode"],
            reference_atom_indices=tuple(payload.get("reference_atom_indices", ())),
            reference_frame_index=int(payload.get("reference_frame_index", 0)),
            reference_weighting=payload.get(
                "reference_weighting", "center_of_geometry"
            ),
            explicit_reference_weights=(
                None
                if payload.get("explicit_reference_weights") is None
                else tuple(float(item) for item in payload["explicit_reference_weights"])
            ),
            force_target_atom_indices=(
                None
                if payload.get("force_target_atom_indices") is None
                else tuple(int(item) for item in payload["force_target_atom_indices"])
            ),
            segment_reset_frame_indices=tuple(
                int(item) for item in payload.get("segment_reset_frame_indices", ())
            ),
            require_fixed_registered_cell=bool(
                payload.get("require_fixed_registered_cell", False)
            ),
            fixed_cell_relative_tolerance=float(
                payload.get("fixed_cell_relative_tolerance", 1.0e-10)
            ),
            round_trip_tolerance=float(payload.get("round_trip_tolerance", 1.0e-10)),
            translation_options=ReferenceTranslationOptions.from_dict(
                payload["translation_options"]
            ),
            closest_image_options=ClosestImageOptions.from_dict(
                payload["closest_image_options"]
            ),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class ReferenceTranslationFrame:
    frame_index: int
    torus_translation: tuple[float, float, float]
    residual_rms: float
    residual_maximum: float
    competing_minimum_separation: float | None
    ambiguous: bool
    converged: bool
    candidate_minima: int
    closest_image_calls: int
    solver_method: str = "exhaustive_multiseed"
    uniqueness_radius_margin: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "torus_translation": list(self.torus_translation),
            "residual_rms": self.residual_rms,
            "residual_maximum": self.residual_maximum,
            "competing_minimum_separation": self.competing_minimum_separation,
            "ambiguous": self.ambiguous,
            "converged": self.converged,
            "candidate_minima": self.candidate_minima,
            "closest_image_calls": self.closest_image_calls,
            "solver_method": self.solver_method,
            "uniqueness_radius_margin": self.uniqueness_radius_margin,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceTranslationFrame":
        return cls(
            frame_index=int(payload["frame_index"]),
            torus_translation=tuple(float(item) for item in payload["torus_translation"]),
            residual_rms=float(payload["residual_rms"]),
            residual_maximum=float(payload["residual_maximum"]),
            competing_minimum_separation=(
                None
                if payload.get("competing_minimum_separation") is None
                else float(payload["competing_minimum_separation"])
            ),
            ambiguous=bool(payload["ambiguous"]),
            converged=bool(payload["converged"]),
            candidate_minima=int(payload["candidate_minima"]),
            closest_image_calls=int(payload["closest_image_calls"]),
            solver_method=str(payload.get("solver_method", "exhaustive_multiseed")),
            uniqueness_radius_margin=(
                None
                if payload.get("uniqueness_radius_margin") is None
                else float(payload["uniqueness_radius_margin"])
            ),
        )


@dataclass(frozen=True, slots=True)
class ReferenceTranslationGauge:
    reference_atom_indices: tuple[int, ...]
    normalized_weights: tuple[float, ...]
    reference_frame_index: int
    weighting: ReferenceWeighting
    registered_origin_convention: str
    fit_metric_digest: str
    frames: tuple[ReferenceTranslationFrame, ...]
    options: ReferenceTranslationOptions
    signature: str = ""

    def __post_init__(self) -> None:
        if len(self.reference_atom_indices) != len(self.normalized_weights):
            raise ReferenceTranslationError("Reference indices and weights disagree.")
        if not np.isclose(sum(self.normalized_weights), 1.0, rtol=0.0, atol=1.0e-12):
            raise ReferenceTranslationError("Reference weights must sum to one.")
        if not self.frames:
            raise ReferenceTranslationError("Reference translation gauge has no frames.")
        if any(frame.frame_index != index for index, frame in enumerate(self.frames)):
            raise ReferenceTranslationError("Reference translation frames are not contiguous.")
        payload = self._payload(include_signature=False)
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise ReferenceTranslationError("Reference-translation signature is inconsistent.")
        object.__setattr__(self, "weighting", ReferenceWeighting(self.weighting))
        object.__setattr__(self, "signature", expected)

    @property
    def torus_translations(self) -> np.ndarray:
        return np.asarray(
            [frame.torus_translation for frame in self.frames], dtype=np.float64
        )

    def _payload(self, *, include_signature: bool) -> dict[str, Any]:
        payload = {
            "schema": REFERENCE_TRANSLATION_GAUGE_SCHEMA,
            "reference_atom_indices": list(self.reference_atom_indices),
            "normalized_weights": list(self.normalized_weights),
            "reference_frame_index": self.reference_frame_index,
            "weighting": self.weighting.value,
            "registered_origin_convention": self.registered_origin_convention,
            "fit_metric_digest": self.fit_metric_digest,
            "frames": [frame.to_dict() for frame in self.frames],
            "options": self.options.to_dict(),
        }
        if include_signature:
            payload["signature"] = self.signature
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(include_signature=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceTranslationGauge":
        if payload.get("schema") != REFERENCE_TRANSLATION_GAUGE_SCHEMA:
            raise ReferenceTranslationError("Unsupported reference-translation schema.")
        return cls(
            reference_atom_indices=tuple(
                int(item) for item in payload["reference_atom_indices"]
            ),
            normalized_weights=tuple(float(item) for item in payload["normalized_weights"]),
            reference_frame_index=int(payload["reference_frame_index"]),
            weighting=ReferenceWeighting(payload["weighting"]),
            registered_origin_convention=str(payload["registered_origin_convention"]),
            fit_metric_digest=str(payload["fit_metric_digest"]),
            frames=tuple(
                ReferenceTranslationFrame.from_dict(item) for item in payload["frames"]
            ),
            options=ReferenceTranslationOptions.from_dict(payload["options"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class TranslationBranchLift:
    torus_translations: np.ndarray
    lifted_translations: np.ndarray
    lattice_branches: np.ndarray
    continuity_residuals: np.ndarray
    competing_branch_separations: np.ndarray
    segment_start_mask: np.ndarray
    temporal_continuity_available: bool
    fit_metric_digest: str
    signature: str = ""

    def __post_init__(self) -> None:
        torus = _readonly_array(
            self.torus_translations,
            dtype=np.float64,
            shape_suffix=(3,),
            name="torus_translations",
        )
        lifted = _readonly_array(
            self.lifted_translations,
            dtype=np.float64,
            shape_suffix=(3,),
            name="lifted_translations",
        )
        branches = _readonly_array(
            self.lattice_branches,
            dtype=np.int64,
            shape_suffix=(3,),
            name="lattice_branches",
        )
        residuals = np.array(self.continuity_residuals, dtype=np.float64, copy=True)
        separations = np.array(
            self.competing_branch_separations, dtype=np.float64, copy=True
        )
        starts = np.array(self.segment_start_mask, dtype=np.bool_, copy=True)
        n_frames = torus.shape[0]
        if lifted.shape != torus.shape or branches.shape != torus.shape:
            raise TranslationBranchAmbiguityError("Translation lift array shapes disagree.")
        if residuals.shape != (n_frames,) or separations.shape != (n_frames,):
            raise TranslationBranchAmbiguityError("Translation diagnostics shapes disagree.")
        if starts.shape != (n_frames,) or not starts[0]:
            raise TranslationBranchAmbiguityError(
                "segment_start_mask must mark the first frame."
            )
        residuals.setflags(write=False)
        separations.setflags(write=False)
        starts.setflags(write=False)
        payload = {
            "schema": TRANSLATION_BRANCH_LIFT_SCHEMA,
            "torus_digest": _array_digest(torus),
            "lifted_digest": _array_digest(lifted),
            "branches_digest": _array_digest(branches),
            "residuals_digest": _array_digest(residuals),
            "separations_digest": _array_digest(separations),
            "segment_starts_digest": _array_digest(starts),
            "temporal_continuity_available": bool(self.temporal_continuity_available),
            "fit_metric_digest": self.fit_metric_digest,
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TranslationBranchAmbiguityError("Translation-lift signature is inconsistent.")
        object.__setattr__(self, "torus_translations", torus)
        object.__setattr__(self, "lifted_translations", lifted)
        object.__setattr__(self, "lattice_branches", branches)
        object.__setattr__(self, "continuity_residuals", residuals)
        object.__setattr__(self, "competing_branch_separations", separations)
        object.__setattr__(self, "segment_start_mask", starts)
        object.__setattr__(
            self,
            "temporal_continuity_available",
            bool(self.temporal_continuity_available),
        )
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRANSLATION_BRANCH_LIFT_SCHEMA,
            "torus_translations": self.torus_translations.tolist(),
            "lifted_translations": self.lifted_translations.tolist(),
            "lattice_branches": self.lattice_branches.tolist(),
            "continuity_residuals": self.continuity_residuals.tolist(),
            "competing_branch_separations": self.competing_branch_separations.tolist(),
            "segment_start_mask": self.segment_start_mask.tolist(),
            "temporal_continuity_available": self.temporal_continuity_available,
            "fit_metric_digest": self.fit_metric_digest,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TranslationBranchLift":
        if payload.get("schema") != TRANSLATION_BRANCH_LIFT_SCHEMA:
            raise TranslationBranchAmbiguityError("Unsupported translation-branch schema.")
        return cls(
            torus_translations=np.asarray(payload["torus_translations"], dtype=np.float64),
            lifted_translations=np.asarray(payload["lifted_translations"], dtype=np.float64),
            lattice_branches=np.asarray(payload["lattice_branches"], dtype=np.int64),
            continuity_residuals=np.asarray(
                payload["continuity_residuals"], dtype=np.float64
            ),
            competing_branch_separations=np.asarray(
                payload["competing_branch_separations"], dtype=np.float64
            ),
            segment_start_mask=np.asarray(payload["segment_start_mask"], dtype=np.bool_),
            temporal_continuity_available=bool(
                payload["temporal_continuity_available"]
            ),
            fit_metric_digest=str(payload["fit_metric_digest"]),
            signature=str(payload.get("signature", "")),
        )


def _normalized_reference_weights(
    collection: AtomisticFrameCollection,
    policy: FrameRegistrationPolicy,
) -> np.ndarray:
    indices = np.asarray(policy.reference_atom_indices, dtype=np.int64)
    if policy.reference_weighting is ReferenceWeighting.CENTER_OF_GEOMETRY:
        weights = np.ones(indices.size, dtype=np.float64)
    elif policy.reference_weighting is ReferenceWeighting.CENTER_OF_MASS:
        weights = np.asarray(collection.masses[indices], dtype=np.float64)
    else:
        assert policy.explicit_reference_weights is not None
        weights = np.asarray(policy.explicit_reference_weights, dtype=np.float64)
    if not np.all(np.isfinite(weights) & (weights > 0.0)):
        raise RegistrationPolicyError("Resolved reference weights must be positive.")
    return weights / np.sum(weights)


def _fit_single_translation(
    residuals: np.ndarray,
    *,
    weights: np.ndarray,
    cell: np.ndarray,
    metric: RegistrationFitMetric,
    translation_options: ReferenceTranslationOptions,
    closest_options: ClosestImageOptions,
    frame_index: int,
) -> ReferenceTranslationFrame:
    # Exact fast path for the common trajectory-registration regime.  Let
    # sigma_min be the smallest singular value of the metric-transformed
    # lattice.  Every nonzero lattice vector then has metric norm at least
    # sigma_min.  If all weighted-mean residuals lie in the open ball of radius
    # sigma_min / 4, they occupy one geodesically convex torus chart and the
    # ordinary weighted Euclidean mean is the unique intrinsic translation.
    # This avoids the O(N_reference^2) multiseed search without changing the
    # accepted scientific solution.  Borderline cases retain the exhaustive
    # certified solver below.
    metric_array = metric.as_array()
    factor = np.linalg.cholesky(metric_array)
    sigma_min = float(np.linalg.svd(cell @ factor, compute_uv=False)[-1])
    weighted_mean = np.sum(weights[:, None] * residuals, axis=0)
    centered = residuals - weighted_mean
    centered_sq = np.einsum("ni,ij,nj->n", centered, metric_array, centered)
    centered_distances = np.sqrt(np.maximum(centered_sq, 0.0))
    maximum = float(np.max(centered_distances))
    rms = float(np.sqrt(np.sum(weights * centered_distances**2)))
    convexity_radius = 0.25 * sigma_min
    if maximum < convexity_radius:
        canonical = closest_periodic_image(
            weighted_mean,
            cell=cell,
            metric=metric,
            options=closest_options,
        )
        if canonical.ambiguous:
            raise ReferenceTranslationError(
                f"Reference translation is ambiguous at frame {frame_index}."
            )
        if translation_options.maximum_residual is not None:
            if maximum > translation_options.maximum_residual:
                raise ReferenceTranslationError(
                    "One uniform reference translation is inadequate at frame "
                    f"{frame_index}: maximum residual {maximum:.6g} exceeds "
                    f"{translation_options.maximum_residual:.6g}."
                )
        return ReferenceTranslationFrame(
            frame_index=frame_index,
            torus_translation=tuple(float(item) for item in canonical.vector),
            residual_rms=rms,
            residual_maximum=maximum,
            competing_minimum_separation=None,
            ambiguous=False,
            converged=True,
            candidate_minima=1,
            closest_image_calls=1,
            solver_method="certified_local_convexity",
            uniqueness_radius_margin=float(convexity_radius - maximum),
        )

    seeds = [np.asarray(value, dtype=np.float64) for value in residuals]
    seeds.append(weighted_mean)
    minima: list[dict[str, Any]] = []
    closest_calls = 0

    for seed in seeds:
        tau = seed.copy()
        converged = False
        local_ambiguous = False
        for _ in range(translation_options.maximum_iterations):
            lifted = np.empty_like(residuals)
            for index, residual in enumerate(residuals):
                image = closest_periodic_image(
                    residual - tau,
                    cell=cell,
                    metric=metric,
                    options=closest_options,
                )
                closest_calls += 1
                local_ambiguous = local_ambiguous or image.ambiguous
                lifted[index] = tau + np.asarray(image.vector, dtype=np.float64)
            updated = np.sum(weights[:, None] * lifted, axis=0)
            step = closest_periodic_image(
                updated - tau,
                cell=cell,
                metric=metric,
                options=closest_options,
            )
            closest_calls += 1
            local_ambiguous = local_ambiguous or step.ambiguous
            tau = updated
            if step.distance <= translation_options.convergence_tolerance:
                converged = True
                break
        canonical = closest_periodic_image(
            tau,
            cell=cell,
            metric=metric,
            options=closest_options,
        )
        closest_calls += 1
        local_ambiguous = local_ambiguous or canonical.ambiguous
        tau_canonical = np.asarray(canonical.vector, dtype=np.float64)
        vectors = np.empty_like(residuals)
        distances = np.empty(residuals.shape[0], dtype=np.float64)
        for index, residual in enumerate(residuals):
            image = closest_periodic_image(
                residual - tau_canonical,
                cell=cell,
                metric=metric,
                options=closest_options,
            )
            closest_calls += 1
            local_ambiguous = local_ambiguous or image.ambiguous
            vectors[index] = np.asarray(image.vector, dtype=np.float64)
            distances[index] = image.distance
        rms = float(np.sqrt(np.sum(weights * distances**2)))
        maximum = float(np.max(distances))
        duplicate = False
        for existing in minima:
            comparison = closest_periodic_image(
                tau_canonical - existing["tau"],
                cell=cell,
                metric=metric,
                options=closest_options,
            )
            closest_calls += 1
            if comparison.distance <= translation_options.candidate_deduplication_tolerance:
                duplicate = True
                if rms < existing["rms"]:
                    existing.update(
                        tau=tau_canonical,
                        rms=rms,
                        maximum=maximum,
                        ambiguous=local_ambiguous,
                        converged=converged,
                    )
                break
        if not duplicate:
            minima.append(
                {
                    "tau": tau_canonical,
                    "rms": rms,
                    "maximum": maximum,
                    "ambiguous": local_ambiguous,
                    "converged": converged,
                }
            )

    minima.sort(key=lambda item: (item["rms"], tuple(float(x) for x in item["tau"])))
    selected = minima[0]
    separation = None if len(minima) == 1 else float(minima[1]["rms"] - selected["rms"])
    ambiguous = bool(selected["ambiguous"])
    if separation is not None and separation <= translation_options.competing_minimum_tolerance:
        ambiguous = True
    if not selected["converged"]:
        raise ReferenceTranslationError(
            f"Reference-translation solver did not converge at frame {frame_index}."
        )
    if translation_options.maximum_residual is not None:
        if selected["maximum"] > translation_options.maximum_residual:
            raise ReferenceTranslationError(
                "One uniform reference translation is inadequate at frame "
                f"{frame_index}: maximum residual {selected['maximum']:.6g} exceeds "
                f"{translation_options.maximum_residual:.6g}."
            )
    if ambiguous:
        raise ReferenceTranslationError(
            f"Reference translation is ambiguous at frame {frame_index}."
        )
    return ReferenceTranslationFrame(
        frame_index=frame_index,
        torus_translation=tuple(float(item) for item in selected["tau"]),
        residual_rms=float(selected["rms"]),
        residual_maximum=float(selected["maximum"]),
        competing_minimum_separation=separation,
        ambiguous=False,
        converged=True,
        candidate_minima=len(minima),
        closest_image_calls=closest_calls,
        solver_method="exhaustive_multiseed",
        uniqueness_radius_margin=None,
    )


def _build_reference_translation_gauge(
    collection: AtomisticFrameCollection,
    *,
    policy: FrameRegistrationPolicy,
    pretranslation_positions: np.ndarray,
    registered_cells: np.ndarray,
    fit_metric: RegistrationFitMetric,
) -> ReferenceTranslationGauge:
    if not all(bool(value) for value in collection.pbc):
        raise RegistrationPolicyError(
            "Matched periodic reference translation currently requires full periodicity."
        )
    if policy.reference_frame_index >= collection.n_frames:
        raise RegistrationPolicyError("reference_frame_index is outside the collection.")
    indices = np.asarray(policy.reference_atom_indices, dtype=np.int64)
    if np.any(indices >= collection.n_atoms):
        raise RegistrationPolicyError("reference_atom_indices are outside the collection.")
    weights = _normalized_reference_weights(collection, policy)
    reference_cell = registered_cells[policy.reference_frame_index]
    reference_fractional = (
        pretranslation_positions[policy.reference_frame_index, indices]
        @ np.linalg.inv(reference_cell)
    )
    frames: list[ReferenceTranslationFrame] = []
    for frame_index in range(collection.n_frames):
        reference_coordinates = reference_fractional @ registered_cells[frame_index]
        residuals = (
            pretranslation_positions[frame_index, indices] - reference_coordinates
        )
        frames.append(
            _fit_single_translation(
                residuals,
                weights=weights,
                cell=registered_cells[frame_index],
                metric=fit_metric,
                translation_options=policy.translation_options,
                closest_options=policy.closest_image_options,
                frame_index=frame_index,
            )
        )
    return ReferenceTranslationGauge(
        reference_atom_indices=policy.reference_atom_indices,
        normalized_weights=tuple(float(item) for item in weights),
        reference_frame_index=policy.reference_frame_index,
        weighting=policy.reference_weighting,
        registered_origin_convention=(
            f"matched_reference_source_frame_{policy.reference_frame_index}"
        ),
        fit_metric_digest=fit_metric.digest,
        frames=tuple(frames),
        options=policy.translation_options,
    )


def _build_translation_branch_lift(
    collection: AtomisticFrameCollection,
    *,
    torus_translations: np.ndarray,
    registered_cells: np.ndarray,
    fit_metric: RegistrationFitMetric,
    policy: FrameRegistrationPolicy,
) -> TranslationBranchLift:
    n_frames = collection.n_frames
    lifted = np.array(torus_translations, copy=True)
    branches = np.zeros((n_frames, 3), dtype=np.int64)
    continuity = np.zeros(n_frames, dtype=np.float64)
    separation = np.zeros(n_frames, dtype=np.float64)
    starts = np.zeros(n_frames, dtype=np.bool_)
    starts[0] = True
    for index in policy.segment_reset_frame_indices:
        if index >= n_frames:
            raise RegistrationPolicyError(
                "segment_reset_frame_indices contains an out-of-range frame."
            )
        starts[index] = True

    if collection.is_trajectory:
        for frame_index in range(1, n_frames):
            if starts[frame_index]:
                continue
            image = closest_periodic_image(
                torus_translations[frame_index] - lifted[frame_index - 1],
                cell=registered_cells[frame_index],
                metric=fit_metric,
                options=policy.closest_image_options,
            )
            if image.ambiguous:
                raise TranslationBranchAmbiguityError(
                    f"Translation branch lift is ambiguous at frame {frame_index}."
                )
            lifted[frame_index] = (
                lifted[frame_index - 1] + np.asarray(image.vector, dtype=np.float64)
            )
            fractional_branch = (
                lifted[frame_index] - torus_translations[frame_index]
            ) @ np.linalg.inv(registered_cells[frame_index])
            rounded = np.rint(fractional_branch).astype(np.int64)
            if not np.allclose(
                fractional_branch,
                rounded,
                rtol=0.0,
                atol=policy.round_trip_tolerance,
            ):
                raise TranslationBranchAmbiguityError(
                    "Translation branch is not an integer lattice vector at frame "
                    f"{frame_index}."
                )
            branches[frame_index] = rounded
            continuity[frame_index] = image.distance
            separation[frame_index] = (
                0.0
                if image.branch_separation is None
                else image.branch_separation
            )
        temporal_available = True
    else:
        starts[:] = True
        temporal_available = False

    return TranslationBranchLift(
        torus_translations=torus_translations,
        lifted_translations=lifted,
        lattice_branches=branches,
        continuity_residuals=continuity,
        competing_branch_separations=separation,
        segment_start_mask=starts,
        temporal_continuity_available=temporal_available,
        fit_metric_digest=fit_metric.digest,
    )


def _registered_force_contract(
    source: ForceAdmissibilityContract,
    *,
    collection: AtomisticFrameCollection,
    policy: FrameRegistrationPolicy,
) -> ForceAdmissibilityContract:
    if collection.forces is None or not source.geometric_force_available:
        geometric = GeometricForceTransformStatus.GENERALIZED_FORCE_UNAVAILABLE
        reasons = tuple(source.reasons) + ("No transformable source force field is available.",)
    elif policy.translation_mode is TranslationMode.NONE:
        geometric = GeometricForceTransformStatus.EXACT_EXTERNAL_AFFINE_COVECTOR
        reasons = tuple(source.reasons)
    elif (
        policy.force_target_atom_indices is not None
        and set(policy.force_target_atom_indices).isdisjoint(policy.reference_atom_indices)
    ):
        geometric = (
            GeometricForceTransformStatus.EXACT_TRANSLATION_RELATIVE_TO_DISJOINT_REFERENCE_GROUP
        )
        reasons = tuple(source.reasons) + (
            "Target and fitted reference atom sets are explicitly disjoint.",
        )
    else:
        geometric = GeometricForceTransformStatus.DIAGNOSTIC_STRUCTURE_FITTED_PROJECTION
        reasons = tuple(source.reasons) + (
            "Matched translation is structure-fitted and no disjoint force target was certified.",
        )
    pmf_status = source.pmf_status
    if policy.translation_mode is TranslationMode.MATCHED_REFERENCE:
        pmf_status = PMFForceAdmissibilityStatus.PMF_FORCE_INADMISSIBLE_STRUCTURE_FITTED_MAP
    return ForceAdmissibilityContract(
        geometric_status=geometric,
        pmf_status=pmf_status,
        source_provenance=source.source_provenance,
        reasons=reasons,
    )


@dataclass(frozen=True, slots=True)
class FrameRegistrationResult:
    source_contract_signature: str
    policy: FrameRegistrationPolicy
    fit_metric: RegistrationFitMetric
    analysis_metric: AnalysisGeometryMetric
    affine_matrices: np.ndarray
    affine_translations: np.ndarray
    registered_cells: np.ndarray
    registered_unwrapped_cartesian: np.ndarray
    registered_wrapped_fractional: np.ndarray
    registered_image_shifts: np.ndarray
    transformed_forces: np.ndarray | None
    force_admissibility: ForceAdmissibilityContract
    reference_translation_gauge: ReferenceTranslationGauge | None
    translation_branch_lift: TranslationBranchLift | None
    maximum_cell_identity_error: float
    maximum_position_round_trip_error: float
    maximum_force_work_error: float | None
    signature: str = ""

    def __post_init__(self) -> None:
        matrices = _readonly_array(
            self.affine_matrices,
            dtype=np.float64,
            shape_suffix=(3, 3),
            name="affine_matrices",
        )
        translations = _readonly_array(
            self.affine_translations,
            dtype=np.float64,
            shape_suffix=(3,),
            name="affine_translations",
        )
        cells = _readonly_array(
            self.registered_cells,
            dtype=np.float64,
            shape_suffix=(3, 3),
            name="registered_cells",
        )
        positions = _readonly_array(
            self.registered_unwrapped_cartesian,
            dtype=np.float64,
            shape_suffix=(3,),
            name="registered_unwrapped_cartesian",
        )
        wrapped = _readonly_array(
            self.registered_wrapped_fractional,
            dtype=np.float64,
            shape_suffix=(3,),
            name="registered_wrapped_fractional",
        )
        shifts = _readonly_array(
            self.registered_image_shifts,
            dtype=np.int64,
            shape_suffix=(3,),
            name="registered_image_shifts",
        )
        n_frames = matrices.shape[0]
        if translations.shape != (n_frames, 3) or cells.shape != (n_frames, 3, 3):
            raise RegistrationValidationError("Framewise affine product shapes disagree.")
        if positions.shape[0] != n_frames or wrapped.shape != positions.shape or shifts.shape != positions.shape:
            raise RegistrationValidationError("Registered coordinate product shapes disagree.")
        forces = None
        if self.transformed_forces is not None:
            forces = _readonly_array(
                self.transformed_forces,
                dtype=np.float64,
                shape_suffix=(3,),
                name="transformed_forces",
            )
            if forces.shape != positions.shape:
                raise RegistrationValidationError("Transformed force shape is inconsistent.")
        payload = {
            "schema": FRAME_REGISTRATION_RESULT_SCHEMA,
            "digest_algorithm": FRAME_REGISTRATION_DIGEST_ALGORITHM,
            "source_contract_signature": self.source_contract_signature,
            "policy_signature": self.policy.signature,
            "fit_metric_digest": self.fit_metric.digest,
            "analysis_metric_digest": self.analysis_metric.digest,
            "affine_matrices_digest": _array_digest(matrices),
            "affine_translations_digest": _array_digest(translations),
            "registered_cells_digest": _array_digest(cells),
            "registered_positions_digest": _array_digest(positions),
            "registered_wrapped_fractional_digest": _array_digest(wrapped),
            "registered_image_shifts_digest": _array_digest(shifts),
            "transformed_forces_digest": None if forces is None else _array_digest(forces),
            "force_admissibility": self.force_admissibility.to_dict(),
            "reference_translation_signature": (
                None
                if self.reference_translation_gauge is None
                else self.reference_translation_gauge.signature
            ),
            "translation_branch_signature": (
                None
                if self.translation_branch_lift is None
                else self.translation_branch_lift.signature
            ),
            "maximum_cell_identity_error": float(self.maximum_cell_identity_error),
            "maximum_position_round_trip_error": float(
                self.maximum_position_round_trip_error
            ),
            "maximum_force_work_error": (
                None
                if self.maximum_force_work_error is None
                else float(self.maximum_force_work_error)
            ),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise RegistrationValidationError("Frame-registration signature is inconsistent.")
        object.__setattr__(self, "affine_matrices", matrices)
        object.__setattr__(self, "affine_translations", translations)
        object.__setattr__(self, "registered_cells", cells)
        object.__setattr__(self, "registered_unwrapped_cartesian", positions)
        object.__setattr__(self, "registered_wrapped_fractional", wrapped)
        object.__setattr__(self, "registered_image_shifts", shifts)
        object.__setattr__(self, "transformed_forces", forces)
        object.__setattr__(self, "signature", expected)

    def transform_positions(self, positions: object, *, frame_index: int) -> np.ndarray:
        values = np.asarray(positions, dtype=np.float64)
        return values @ self.affine_matrices[frame_index] + self.affine_translations[frame_index]

    def inverse_transform_positions(self, positions: object, *, frame_index: int) -> np.ndarray:
        values = np.asarray(positions, dtype=np.float64)
        return (values - self.affine_translations[frame_index]) @ np.linalg.inv(
            self.affine_matrices[frame_index]
        )

    def transform_displacements(self, displacements: object, *, frame_index: int) -> np.ndarray:
        return np.asarray(displacements, dtype=np.float64) @ self.affine_matrices[frame_index]

    def inverse_transform_displacements(
        self, displacements: object, *, frame_index: int
    ) -> np.ndarray:
        return np.asarray(displacements, dtype=np.float64) @ np.linalg.inv(
            self.affine_matrices[frame_index]
        )

    def transform_force_covectors(self, forces: object, *, frame_index: int) -> np.ndarray:
        values = np.asarray(forces, dtype=np.float64)
        return values @ np.linalg.inv(self.affine_matrices[frame_index]).T

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FRAME_REGISTRATION_RESULT_SCHEMA,
            "source_contract_signature": self.source_contract_signature,
            "policy": self.policy.to_dict(),
            "fit_metric": self.fit_metric.to_dict(),
            "analysis_metric": self.analysis_metric.to_dict(),
            "affine_matrices": self.affine_matrices.tolist(),
            "affine_translations": self.affine_translations.tolist(),
            "registered_cells": self.registered_cells.tolist(),
            "registered_unwrapped_cartesian": self.registered_unwrapped_cartesian.tolist(),
            "registered_wrapped_fractional": self.registered_wrapped_fractional.tolist(),
            "registered_image_shifts": self.registered_image_shifts.tolist(),
            "transformed_forces": (
                None if self.transformed_forces is None else self.transformed_forces.tolist()
            ),
            "force_admissibility": self.force_admissibility.to_dict(),
            "reference_translation_gauge": (
                None
                if self.reference_translation_gauge is None
                else self.reference_translation_gauge.to_dict()
            ),
            "translation_branch_lift": (
                None
                if self.translation_branch_lift is None
                else self.translation_branch_lift.to_dict()
            ),
            "maximum_cell_identity_error": self.maximum_cell_identity_error,
            "maximum_position_round_trip_error": self.maximum_position_round_trip_error,
            "maximum_force_work_error": self.maximum_force_work_error,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRegistrationResult":
        if payload.get("schema") != FRAME_REGISTRATION_RESULT_SCHEMA:
            raise RegistrationValidationError("Unsupported frame-registration result schema.")
        gauge_payload = payload.get("reference_translation_gauge")
        branch_payload = payload.get("translation_branch_lift")
        return cls(
            source_contract_signature=str(payload["source_contract_signature"]),
            policy=FrameRegistrationPolicy.from_dict(payload["policy"]),
            fit_metric=RegistrationFitMetric.from_dict(payload["fit_metric"]),
            analysis_metric=AnalysisGeometryMetric.from_dict(payload["analysis_metric"]),
            affine_matrices=np.asarray(payload["affine_matrices"], dtype=np.float64),
            affine_translations=np.asarray(payload["affine_translations"], dtype=np.float64),
            registered_cells=np.asarray(payload["registered_cells"], dtype=np.float64),
            registered_unwrapped_cartesian=np.asarray(
                payload["registered_unwrapped_cartesian"], dtype=np.float64
            ),
            registered_wrapped_fractional=np.asarray(
                payload["registered_wrapped_fractional"], dtype=np.float64
            ),
            registered_image_shifts=np.asarray(
                payload["registered_image_shifts"], dtype=np.int64
            ),
            transformed_forces=(
                None
                if payload.get("transformed_forces") is None
                else np.asarray(payload["transformed_forces"], dtype=np.float64)
            ),
            force_admissibility=ForceAdmissibilityContract.from_dict(
                payload["force_admissibility"]
            ),
            reference_translation_gauge=(
                None
                if gauge_payload is None
                else ReferenceTranslationGauge.from_dict(gauge_payload)
            ),
            translation_branch_lift=(
                None
                if branch_payload is None
                else TranslationBranchLift.from_dict(branch_payload)
            ),
            maximum_cell_identity_error=float(payload["maximum_cell_identity_error"]),
            maximum_position_round_trip_error=float(
                payload["maximum_position_round_trip_error"]
            ),
            maximum_force_work_error=(
                None
                if payload.get("maximum_force_work_error") is None
                else float(payload["maximum_force_work_error"])
            ),
            signature=str(payload.get("signature", "")),
        )


def _resolve_source_contract(
    collection: AtomisticFrameCollection,
    *,
    source_contract: SourceCoordinateContract | None,
    reference_cell: ReferenceCellDefinition | None,
    reference_frame_index: int | None,
) -> SourceCoordinateContract:
    if source_contract is None:
        return prepare_source_coordinate_contract(
            collection,
            reference_cell=reference_cell,
            reference_frame_index=reference_frame_index,
        )
    if reference_cell is not None or reference_frame_index is not None:
        raise RegistrationPolicyError(
            "Reference-cell arguments are not allowed with an existing source_contract."
        )
    rebound = build_periodic_lattice_gauge(
        collection, options=source_contract.lattice_gauge.options
    )
    if rebound.source_digest != source_contract.source_digest:
        raise RegistrationPolicyError(
            "The source-coordinate contract is not bound to this collection."
        )
    return source_contract


def prepare_frame_registration(
    collection: AtomisticFrameCollection,
    *,
    policy: FrameRegistrationPolicy | None = None,
    source_contract: SourceCoordinateContract | None = None,
    reference_cell: ReferenceCellDefinition | None = None,
    reference_frame_index: int | None = None,
    fit_metric: RegistrationFitMetric | None = None,
    analysis_metric: AnalysisGeometryMetric | None = None,
) -> FrameRegistrationResult:
    """Construct and validate one Stage-C0A2 registered view."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    active_policy = policy or FrameRegistrationPolicy()
    source = _resolve_source_contract(
        collection,
        source_contract=source_contract,
        reference_cell=reference_cell,
        reference_frame_index=reference_frame_index,
    )
    active_fit_metric = fit_metric or RegistrationFitMetric.euclidean(
        units="angstrom^-2",
        coordinate_frame="registered_cartesian",
    )
    active_analysis_metric = analysis_metric or AnalysisGeometryMetric.euclidean(
        units="angstrom^-2",
        coordinate_frame="registered_cartesian",
    )

    if active_policy.reference_frame_index >= collection.n_frames:
        raise RegistrationPolicyError("reference_frame_index is outside the collection.")
    for index_set, name in (
        (active_policy.reference_atom_indices, "reference_atom_indices"),
        (active_policy.force_target_atom_indices or (), "force_target_atom_indices"),
    ):
        if index_set and max(index_set) >= collection.n_atoms:
            raise RegistrationPolicyError(f"{name} are outside the collection.")

    gauged_cells = np.stack(
        [source.lattice_gauge.gauged_cell(index) for index in range(collection.n_frames)]
    )
    affine = np.repeat(np.eye(3)[None, :, :], collection.n_frames, axis=0)
    if active_policy.spatial_policy is RegistrationSpatialPolicy.REFERENCE_MATERIAL:
        if source.reference_cell is None:
            raise RegistrationPolicyError(
                "reference_material registration requires a C0A1 reference cell."
            )
        if not all(bool(value) for value in collection.pbc):
            raise RegistrationPolicyError(
                "reference_material registration currently requires full periodicity."
            )
        reference_matrix = np.asarray(source.reference_cell.matrix, dtype=np.float64)
        for frame_index in range(collection.n_frames):
            affine[frame_index] = np.linalg.inv(gauged_cells[frame_index]) @ reference_matrix
    registered_cells = np.einsum(
        "tij,tjk->tik", gauged_cells, affine, optimize=True
    )
    source_positions = collection.get_positions()
    pretranslation = np.einsum(
        "tni,tij->tnj", source_positions, affine, optimize=True
    )

    translation_gauge = None
    branch_lift = None
    translations = np.zeros((collection.n_frames, 3), dtype=np.float64)
    if active_policy.translation_mode is TranslationMode.MATCHED_REFERENCE:
        translation_gauge = _build_reference_translation_gauge(
            collection,
            policy=active_policy,
            pretranslation_positions=pretranslation,
            registered_cells=registered_cells,
            fit_metric=active_fit_metric,
        )
        branch_lift = _build_translation_branch_lift(
            collection,
            torus_translations=translation_gauge.torus_translations,
            registered_cells=registered_cells,
            fit_metric=active_fit_metric,
            policy=active_policy,
        )
        translations = -np.asarray(branch_lift.lifted_translations, dtype=np.float64)
    registered_positions = pretranslation + translations[:, None, :]

    if active_policy.require_fixed_registered_cell:
        scale = max(float(np.linalg.norm(registered_cells[0])), np.finfo(float).tiny)
        changes = np.linalg.norm(registered_cells - registered_cells[0], axis=(1, 2)) / scale
        if np.any(changes > active_policy.fixed_cell_relative_tolerance):
            frame = int(np.flatnonzero(changes > active_policy.fixed_cell_relative_tolerance)[0])
            raise RegistrationValidationError(
                "Registered fixed-domain requirement fails at frame "
                f"{frame}: relative cell change {changes[frame]:.6g}."
            )

    fractional = np.einsum(
        "tni,tij->tnj",
        registered_positions,
        np.linalg.inv(registered_cells),
        optimize=True,
    )
    wrapped = np.array(fractional, copy=True)
    image_shifts = np.zeros_like(fractional, dtype=np.int64)
    for axis, periodic in enumerate(collection.pbc):
        if periodic:
            shifts_axis = np.floor(wrapped[..., axis]).astype(np.int64)
            image_shifts[..., axis] = shifts_axis
            wrapped[..., axis] -= shifts_axis
    reconstructed = np.einsum(
        "tni,tij->tnj",
        wrapped + image_shifts,
        registered_cells,
        optimize=True,
    )
    position_round_trip_error = float(
        np.max(np.linalg.norm(reconstructed - registered_positions, axis=-1))
    )
    if position_round_trip_error > active_policy.round_trip_tolerance:
        raise RegistrationValidationError(
            "Registered wrapped/image reconstruction failed: maximum error "
            f"{position_round_trip_error:.6g}."
        )

    cell_expected = np.einsum("tij,tjk->tik", gauged_cells, affine, optimize=True)
    cell_identity_error = float(
        np.max(np.linalg.norm(cell_expected - registered_cells, axis=(1, 2)))
    )
    if cell_identity_error > active_policy.round_trip_tolerance:
        raise RegistrationValidationError(
            f"Registered-cell identity G=HM failed with error {cell_identity_error:.6g}."
        )

    inverse_affine = np.linalg.inv(affine)
    inverse_positions = np.einsum(
        "tni,tij->tnj",
        registered_positions - translations[:, None, :],
        inverse_affine,
        optimize=True,
    )
    inverse_error = float(np.max(np.linalg.norm(inverse_positions - source_positions, axis=-1)))
    position_round_trip_error = max(position_round_trip_error, inverse_error)
    if position_round_trip_error > active_policy.round_trip_tolerance:
        raise RegistrationValidationError(
            "Affine position round trip failed: maximum error "
            f"{position_round_trip_error:.6g}."
        )

    transformed_forces = None
    force_work_error = None
    if collection.forces is not None and source.semantics.force_transformable:
        covector_maps = np.transpose(inverse_affine, (0, 2, 1))
        transformed_forces = np.einsum(
            "tni,tij->tnj", collection.forces, covector_maps, optimize=True
        )
        probe = np.array([0.731, -0.413, 0.257], dtype=np.float64)
        source_work = np.einsum("tni,i->tn", collection.forces, probe)
        transformed_probe = np.einsum("i,tij->tj", probe, affine, optimize=True)
        registered_work = np.einsum(
            "tni,ti->tn", transformed_forces, transformed_probe, optimize=True
        )
        force_work_error = float(np.max(np.abs(source_work - registered_work)))
        if force_work_error > 10.0 * active_policy.round_trip_tolerance:
            raise RegistrationValidationError(
                f"Force-work invariance failed with error {force_work_error:.6g}."
            )

    force_contract = _registered_force_contract(
        source.force_admissibility,
        collection=collection,
        policy=active_policy,
    )
    return FrameRegistrationResult(
        source_contract_signature=source.signature,
        policy=active_policy,
        fit_metric=active_fit_metric,
        analysis_metric=active_analysis_metric,
        affine_matrices=affine,
        affine_translations=translations,
        registered_cells=registered_cells,
        registered_unwrapped_cartesian=registered_positions,
        registered_wrapped_fractional=wrapped,
        registered_image_shifts=image_shifts,
        transformed_forces=transformed_forces,
        force_admissibility=force_contract,
        reference_translation_gauge=translation_gauge,
        translation_branch_lift=branch_lift,
        maximum_cell_identity_error=cell_identity_error,
        maximum_position_round_trip_error=position_round_trip_error,
        maximum_force_work_error=force_work_error,
    )
