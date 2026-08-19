"""Stage-11E3 local mean-force and harmonic/manifold refinement.

The implementation follows average-force and force-matching ideas from Darve and
Pohorille (2001) and Noid et al. (2008).  The source-bound support, periodic
chart, evidence-status, and density/force comparison contracts are mdstats
constructions.  Spatial attractors are never deleted because force evidence is
missing or inadmissible.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..site_samples import FrameworkAlignedIonSampleCatalog
from .attractors import AttractorGeometry, DensityAttractorCatalog, LocalChartKind
from .species import AnalysisGeometryMetric, PeriodicSpeciesDensityEstimate

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int64]

LOCAL_MEAN_FORCE_OPTIONS_SCHEMA = "mdstats.local-mean-force-options.v1"
LOCAL_MEAN_FORCE_RESOURCES_SCHEMA = "mdstats.local-mean-force-resources.v1"
MATCHED_MEAN_FORCE_FIELD_SCHEMA = "mdstats.matched-mean-force-field.v1"
LOCAL_FORCE_REFINEMENT_SCHEMA = "mdstats.local-force-refinement.v1"
FORCE_REFINEMENT_CATALOG_SCHEMA = "mdstats.force-refinement-catalog.v1"
FORCE_REFINEMENT_STAGE = "11E3"
BOLTZMANN_EV_PER_K = 8.617333262145e-5


class ForceRefinementError(ValueError):
    """Base Stage-11E3 error."""


class ForceRefinementInputError(ForceRefinementError):
    """Raised when E0b, E1, and E2 inputs are not source-compatible."""


class ForceRefinementResourceError(ForceRefinementError):
    """Raised before a configured Stage-11E3 resource limit is exceeded."""


class ForceRefinementSerializationError(ForceRefinementError):
    """Raised when serialized Stage-11E3 data are malformed or tampered with."""


class ForceEvidenceStatus(str, Enum):
    RESOLVED = "resolved"
    FORCE_UNAVAILABLE = "force_unavailable"
    PMF_PROVENANCE_REJECTED = "pmf_provenance_rejected"
    INSUFFICIENT_LOCAL_SUPPORT = "insufficient_local_support"
    CHART_UNRESOLVED = "chart_unresolved"
    RANK_DEFICIENT = "rank_deficient"
    ILL_CONDITIONED = "ill_conditioned"
    CENTER_OUTSIDE_CHART = "center_outside_chart"


class CurvatureClass(str, Enum):
    STABLE_POINT = "stable_point"
    SADDLE_OR_UNSTABLE = "saddle_or_unstable"
    SOFT_MANIFOLD = "soft_manifold"
    FLAT_OR_UNRESOLVED = "flat_or_unresolved"
    NOT_EVALUATED = "not_evaluated"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii")); h.update(str(arr.shape).encode("ascii")); h.update(arr.tobytes())
    return h.hexdigest()


def _sha(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ForceRefinementInputError(f"{name} must be a SHA-256 string.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True)
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise ForceRefinementInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise ForceRefinementInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        x = float(value)
        if not np.isfinite(x): raise ForceRefinementInputError("Metadata contains non-finite values.")
        return x
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, np.ndarray):
        arr = np.array(value, copy=True); arr.setflags(write=False); return arr
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)): return tuple(_freeze(v) for v in value)
    raise ForceRefinementInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping): return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, np.ndarray): return value.tolist()
    if isinstance(value, tuple): return [_json_value(v) for v in value]
    if isinstance(value, np.generic): return _json_value(value.item())
    if value is None or isinstance(value, (str, bool, int, float)): return value
    raise ForceRefinementInputError(f"Cannot serialize {type(value).__name__}.")


def _positive(value: Any, name: str) -> float:
    x = float(value)
    if not np.isfinite(x) or x <= 0.0: raise ForceRefinementInputError(f"{name} must be finite and positive.")
    return x


def _nonnegative(value: Any, name: str) -> float:
    x = float(value)
    if not np.isfinite(x) or x < 0.0: raise ForceRefinementInputError(f"{name} must be finite and nonnegative.")
    return x


@dataclass(frozen=True, slots=True)
class LocalMeanForceOptions:
    minimum_effective_samples: float = 4.0
    minimum_fit_samples: int = 12
    maximum_condition_number: float = 1.0e10
    minimum_stiffness: float = 1.0e-8
    soft_direction_ratio: float = 0.15
    chart_radius_factor: float = 1.25
    uncertainty_blocks: int = 4
    query_batch_size: int = 256
    sample_batch_size: int = 128
    boltzmann_constant: float = BOLTZMANN_EV_PER_K
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        neff = _positive(self.minimum_effective_samples, "minimum_effective_samples")
        nfit = int(self.minimum_fit_samples)
        if nfit < 9: raise ForceRefinementInputError("minimum_fit_samples must be at least 9.")
        cond = _positive(self.maximum_condition_number, "maximum_condition_number")
        stiffness = _nonnegative(self.minimum_stiffness, "minimum_stiffness")
        ratio = _nonnegative(self.soft_direction_ratio, "soft_direction_ratio")
        if ratio >= 1.0: raise ForceRefinementInputError("soft_direction_ratio must be smaller than one.")
        radius = _positive(self.chart_radius_factor, "chart_radius_factor")
        blocks = int(self.uncertainty_blocks)
        if blocks < 0: raise ForceRefinementInputError("uncertainty_blocks must be nonnegative.")
        qb, sb = int(self.query_batch_size), int(self.sample_batch_size)
        if qb <= 0 or sb <= 0: raise ForceRefinementInputError("batch sizes must be positive.")
        kb = _positive(self.boltzmann_constant, "boltzmann_constant")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": LOCAL_MEAN_FORCE_OPTIONS_SCHEMA, "minimum_effective_samples": neff,
                   "minimum_fit_samples": nfit, "maximum_condition_number": cond,
                   "minimum_stiffness": stiffness, "soft_direction_ratio": ratio,
                   "chart_radius_factor": radius, "uncertainty_blocks": blocks,
                   "query_batch_size": qb, "sample_batch_size": sb, "boltzmann_constant": kb,
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise ForceRefinementInputError("Options signature is inconsistent.")
        for name, value in (("minimum_effective_samples", neff), ("minimum_fit_samples", nfit),
                            ("maximum_condition_number", cond), ("minimum_stiffness", stiffness),
                            ("soft_direction_ratio", ratio), ("chart_radius_factor", radius),
                            ("uncertainty_blocks", blocks), ("query_batch_size", qb),
                            ("sample_batch_size", sb), ("boltzmann_constant", kb),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": LOCAL_MEAN_FORCE_OPTIONS_SCHEMA, "minimum_effective_samples": self.minimum_effective_samples,
                "minimum_fit_samples": self.minimum_fit_samples, "maximum_condition_number": self.maximum_condition_number,
                "minimum_stiffness": self.minimum_stiffness, "soft_direction_ratio": self.soft_direction_ratio,
                "chart_radius_factor": self.chart_radius_factor, "uncertainty_blocks": self.uncertainty_blocks,
                "query_batch_size": self.query_batch_size, "sample_batch_size": self.sample_batch_size,
                "boltzmann_constant": self.boltzmann_constant, "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "LocalMeanForceOptions":
        if p.get("schema") != LOCAL_MEAN_FORCE_OPTIONS_SCHEMA: raise ForceRefinementSerializationError("Unsupported options schema.")
        return cls(**{k: p[k] for k in ("minimum_effective_samples", "minimum_fit_samples", "maximum_condition_number",
                                        "minimum_stiffness", "soft_direction_ratio", "chart_radius_factor",
                                        "uncertainty_blocks", "query_batch_size", "sample_batch_size", "boltzmann_constant")},
                   metadata=p.get("metadata", {}), signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class LocalMeanForceResourcePolicy:
    max_grid_nodes: int = 2_000_000
    max_force_samples: int = 2_000_000
    max_kernel_terms: int = 500_000_000
    max_workspace_bytes: int = 512 * 1024**2
    max_output_bytes: int = 512 * 1024**2
    max_attractors: int = 100_000
    signature: str = ""

    def __post_init__(self) -> None:
        vals = {name: int(getattr(self, name)) for name in ("max_grid_nodes", "max_force_samples", "max_kernel_terms",
                                                             "max_workspace_bytes", "max_output_bytes", "max_attractors")}
        if any(v <= 0 for v in vals.values()): raise ForceRefinementInputError("Resource limits must be positive.")
        expected = _digest({"schema": LOCAL_MEAN_FORCE_RESOURCES_SCHEMA, **vals})
        if self.signature and self.signature != expected: raise ForceRefinementInputError("Resource signature is inconsistent.")
        for k, v in vals.items(): object.__setattr__(self, k, v)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": LOCAL_MEAN_FORCE_RESOURCES_SCHEMA, **{k: getattr(self, k) for k in ("max_grid_nodes", "max_force_samples",
                "max_kernel_terms", "max_workspace_bytes", "max_output_bytes", "max_attractors")}, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "LocalMeanForceResourcePolicy":
        if p.get("schema") != LOCAL_MEAN_FORCE_RESOURCES_SCHEMA: raise ForceRefinementSerializationError("Unsupported resources schema.")
        return cls(**{k: int(p[k]) for k in ("max_grid_nodes", "max_force_samples", "max_kernel_terms", "max_workspace_bytes",
                                             "max_output_bytes", "max_attractors")}, signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class MatchedMeanForceField:
    grid_shape: tuple[int, int, int]
    conditional_force_covector: FloatArray
    force_covariance: FloatArray
    local_effective_sample_size: FloatArray
    support_mask: BoolArray
    standard_error_covector: FloatArray | None
    sample_count: int
    represented_ion_time: float
    density_estimate_signature: str
    sample_catalog_signature: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        shape = tuple(int(v) for v in self.grid_shape)
        if len(shape) != 3 or min(shape) <= 0: raise ForceRefinementInputError("grid_shape must have three positive entries.")
        force = _readonly(self.conditional_force_covector, dtype=np.float64, ndim=4, name="conditional_force_covector", shape=shape + (3,))
        cov = _readonly(self.force_covariance, dtype=np.float64, ndim=5, name="force_covariance", shape=shape + (3, 3))
        neff = _readonly(self.local_effective_sample_size, dtype=np.float64, ndim=3, name="local_effective_sample_size", shape=shape)
        support = _readonly(self.support_mask, dtype=np.bool_, ndim=3, name="support_mask", shape=shape)
        se = None if self.standard_error_covector is None else _readonly(self.standard_error_covector, dtype=np.float64, ndim=4,
                                                                           name="standard_error_covector", shape=shape + (3,))
        count = int(self.sample_count)
        if count < 0: raise ForceRefinementInputError("sample_count must be nonnegative.")
        ion_time = _nonnegative(self.represented_ion_time, "represented_ion_time")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": MATCHED_MEAN_FORCE_FIELD_SCHEMA, "grid_shape": list(shape), "force": _array_digest(force),
                   "covariance": _array_digest(cov), "neff": _array_digest(neff), "support": _array_digest(support),
                   "stderr": None if se is None else _array_digest(se), "sample_count": count, "represented_ion_time": ion_time,
                   "density_estimate_signature": _sha(self.density_estimate_signature, "density_estimate_signature"),
                   "sample_catalog_signature": _sha(self.sample_catalog_signature, "sample_catalog_signature"),
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise ForceRefinementInputError("Mean-force-field signature is inconsistent.")
        for name, value in (("grid_shape", shape), ("conditional_force_covector", force), ("force_covariance", cov),
                            ("local_effective_sample_size", neff), ("support_mask", support), ("standard_error_covector", se),
                            ("sample_count", count), ("represented_ion_time", ion_time), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self, *, include_values: bool = True) -> dict[str, Any]:
        p = {"schema": MATCHED_MEAN_FORCE_FIELD_SCHEMA, "grid_shape": list(self.grid_shape), "sample_count": self.sample_count,
             "represented_ion_time": self.represented_ion_time, "density_estimate_signature": self.density_estimate_signature,
             "sample_catalog_signature": self.sample_catalog_signature, "metadata": _json_value(self.metadata), "signature": self.signature}
        if include_values:
            p.update(conditional_force_covector=self.conditional_force_covector.tolist(), force_covariance=self.force_covariance.tolist(),
                     local_effective_sample_size=self.local_effective_sample_size.tolist(), support_mask=self.support_mask.tolist(),
                     standard_error_covector=None if self.standard_error_covector is None else self.standard_error_covector.tolist())
        return p

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "MatchedMeanForceField":
        if p.get("schema") != MATCHED_MEAN_FORCE_FIELD_SCHEMA: raise ForceRefinementSerializationError("Unsupported mean-force-field schema.")
        required = ("conditional_force_covector", "force_covariance", "local_effective_sample_size", "support_mask")
        if any(k not in p for k in required): raise ForceRefinementSerializationError("Mean-force-field replay requires values.")
        return cls(grid_shape=tuple(p["grid_shape"]), conditional_force_covector=np.asarray(p["conditional_force_covector"]),
                   force_covariance=np.asarray(p["force_covariance"]), local_effective_sample_size=np.asarray(p["local_effective_sample_size"]),
                   support_mask=np.asarray(p["support_mask"]), standard_error_covector=None if p.get("standard_error_covector") is None else np.asarray(p["standard_error_covector"]),
                   sample_count=int(p["sample_count"]), represented_ion_time=float(p["represented_ion_time"]),
                   density_estimate_signature=str(p["density_estimate_signature"]), sample_catalog_signature=str(p["sample_catalog_signature"]),
                   metadata=p.get("metadata", {}), signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class LocalForceRefinement:
    attractor_id: int
    geometry: AttractorGeometry
    evidence_status: ForceEvidenceStatus
    curvature_class: CurvatureClass
    sample_indices: IntArray
    density_anchor_fractional: FloatArray
    force_center_fractional: FloatArray | None
    intercept_orthonormal: FloatArray | None
    stiffness_orthonormal: FloatArray | None
    stiffness_eigenvalues: FloatArray | None
    stiffness_eigenvectors: FloatArray | None
    residual_covariance: FloatArray | None
    parameter_standard_error: FloatArray | None
    fit_rank: int
    fit_condition_number: float | None
    center_within_chart: bool | None
    residence_covariance_orthonormal: FloatArray | None
    harmonic_covariance_orthonormal: FloatArray | None
    covariance_relative_error: float | None
    density_force_residual_norm: float | None
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        aid = int(self.attractor_id)
        if aid < 0: raise ForceRefinementInputError("attractor_id must be nonnegative.")
        geom, status, curvature = AttractorGeometry(self.geometry), ForceEvidenceStatus(self.evidence_status), CurvatureClass(self.curvature_class)
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        anchor = _readonly(self.density_anchor_fractional, dtype=np.float64, ndim=1, name="density_anchor_fractional", shape=(3,))
        def vec(v: Any, name: str): return None if v is None else _readonly(v, dtype=np.float64, ndim=1, name=name, shape=(3,))
        def mat(v: Any, name: str): return None if v is None else _readonly(v, dtype=np.float64, ndim=2, name=name, shape=(3,3))
        center, intercept = vec(self.force_center_fractional, "force_center_fractional"), vec(self.intercept_orthonormal, "intercept_orthonormal")
        stiff, eigvec, resid = mat(self.stiffness_orthonormal, "stiffness_orthonormal"), mat(self.stiffness_eigenvectors, "stiffness_eigenvectors"), mat(self.residual_covariance, "residual_covariance")
        eigval = vec(self.stiffness_eigenvalues, "stiffness_eigenvalues")
        pstd = None if self.parameter_standard_error is None else _readonly(self.parameter_standard_error, dtype=np.float64, ndim=1, name="parameter_standard_error", shape=(9,))
        rcov, hcov = mat(self.residence_covariance_orthonormal, "residence_covariance_orthonormal"), mat(self.harmonic_covariance_orthonormal, "harmonic_covariance_orthonormal")
        rank = int(self.fit_rank)
        if rank < 0: raise ForceRefinementInputError("fit_rank must be nonnegative.")
        cond = None if self.fit_condition_number is None else _nonnegative(self.fit_condition_number, "fit_condition_number")
        crel = None if self.covariance_relative_error is None else _nonnegative(self.covariance_relative_error, "covariance_relative_error")
        dres = None if self.density_force_residual_norm is None else _nonnegative(self.density_force_residual_norm, "density_force_residual_norm")
        payload = {"schema": LOCAL_FORCE_REFINEMENT_SCHEMA, "attractor_id": aid, "geometry": geom.value, "status": status.value,
                   "curvature": curvature.value, "samples": _array_digest(samples), "anchor": _array_digest(anchor),
                   "center": None if center is None else _array_digest(center), "intercept": None if intercept is None else _array_digest(intercept),
                   "stiffness": None if stiff is None else _array_digest(stiff), "eigval": None if eigval is None else _array_digest(eigval),
                   "eigvec": None if eigvec is None else _array_digest(eigvec), "residual": None if resid is None else _array_digest(resid),
                   "pstd": None if pstd is None else _array_digest(pstd), "rank": rank, "condition": cond,
                   "center_within_chart": self.center_within_chart, "residence_covariance": None if rcov is None else _array_digest(rcov),
                   "harmonic_covariance": None if hcov is None else _array_digest(hcov), "covariance_relative_error": crel,
                   "density_force_residual_norm": dres, "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise ForceRefinementInputError("Local refinement signature is inconsistent.")
        for name, value in (("attractor_id", aid), ("geometry", geom), ("evidence_status", status), ("curvature_class", curvature),
                            ("sample_indices", samples), ("density_anchor_fractional", anchor), ("force_center_fractional", center),
                            ("intercept_orthonormal", intercept), ("stiffness_orthonormal", stiff), ("stiffness_eigenvalues", eigval),
                            ("stiffness_eigenvectors", eigvec), ("residual_covariance", resid), ("parameter_standard_error", pstd),
                            ("fit_rank", rank), ("fit_condition_number", cond), ("residence_covariance_orthonormal", rcov),
                            ("harmonic_covariance_orthonormal", hcov), ("covariance_relative_error", crel),
                            ("density_force_residual_norm", dres), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        conv = lambda v: None if v is None else v.tolist()
        return {"schema": LOCAL_FORCE_REFINEMENT_SCHEMA, "attractor_id": self.attractor_id, "geometry": self.geometry.value,
                "evidence_status": self.evidence_status.value, "curvature_class": self.curvature_class.value,
                "sample_indices": self.sample_indices.tolist(), "density_anchor_fractional": self.density_anchor_fractional.tolist(),
                "force_center_fractional": conv(self.force_center_fractional), "intercept_orthonormal": conv(self.intercept_orthonormal),
                "stiffness_orthonormal": conv(self.stiffness_orthonormal), "stiffness_eigenvalues": conv(self.stiffness_eigenvalues),
                "stiffness_eigenvectors": conv(self.stiffness_eigenvectors), "residual_covariance": conv(self.residual_covariance),
                "parameter_standard_error": conv(self.parameter_standard_error), "fit_rank": self.fit_rank,
                "fit_condition_number": self.fit_condition_number, "center_within_chart": self.center_within_chart,
                "residence_covariance_orthonormal": conv(self.residence_covariance_orthonormal),
                "harmonic_covariance_orthonormal": conv(self.harmonic_covariance_orthonormal),
                "covariance_relative_error": self.covariance_relative_error, "density_force_residual_norm": self.density_force_residual_norm,
                "diagnostic": self.diagnostic, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "LocalForceRefinement":
        if p.get("schema") != LOCAL_FORCE_REFINEMENT_SCHEMA: raise ForceRefinementSerializationError("Unsupported local refinement schema.")
        arr = lambda k: None if p.get(k) is None else np.asarray(p[k], dtype=float)
        return cls(attractor_id=int(p["attractor_id"]), geometry=AttractorGeometry(p["geometry"]),
                   evidence_status=ForceEvidenceStatus(p["evidence_status"]), curvature_class=CurvatureClass(p["curvature_class"]),
                   sample_indices=np.asarray(p["sample_indices"], dtype=np.int64), density_anchor_fractional=np.asarray(p["density_anchor_fractional"]),
                   force_center_fractional=arr("force_center_fractional"), intercept_orthonormal=arr("intercept_orthonormal"),
                   stiffness_orthonormal=arr("stiffness_orthonormal"), stiffness_eigenvalues=arr("stiffness_eigenvalues"),
                   stiffness_eigenvectors=arr("stiffness_eigenvectors"), residual_covariance=arr("residual_covariance"),
                   parameter_standard_error=arr("parameter_standard_error"), fit_rank=int(p["fit_rank"]),
                   fit_condition_number=p.get("fit_condition_number"), center_within_chart=p.get("center_within_chart"),
                   residence_covariance_orthonormal=arr("residence_covariance_orthonormal"), harmonic_covariance_orthonormal=arr("harmonic_covariance_orthonormal"),
                   covariance_relative_error=p.get("covariance_relative_error"), density_force_residual_norm=p.get("density_force_residual_norm"),
                   diagnostic=p.get("diagnostic"), signature=str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ForceRefinementCatalog:
    sample_catalog_signature: str
    density_estimate_signature: str
    attractor_catalog_signature: str
    options: LocalMeanForceOptions
    resources: LocalMeanForceResourcePolicy
    mean_force_field: MatchedMeanForceField | None
    refinements: tuple[LocalForceRefinement, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sample = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        density = _sha(self.density_estimate_signature, "density_estimate_signature")
        attractor = _sha(self.attractor_catalog_signature, "attractor_catalog_signature")
        refs = tuple(self.refinements)
        if tuple(r.attractor_id for r in refs) != tuple(range(len(refs))):
            raise ForceRefinementInputError("Refinement ids must be contiguous and preserve every attractor.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": FORCE_REFINEMENT_CATALOG_SCHEMA, "sample": sample, "density": density, "attractor": attractor,
                   "options": self.options.signature, "resources": self.resources.signature,
                   "field": None if self.mean_force_field is None else self.mean_force_field.signature,
                   "refinements": [r.signature for r in refs], "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise ForceRefinementInputError("Force-refinement-catalog signature is inconsistent.")
        object.__setattr__(self, "sample_catalog_signature", sample); object.__setattr__(self, "density_estimate_signature", density)
        object.__setattr__(self, "attractor_catalog_signature", attractor); object.__setattr__(self, "refinements", refs)
        object.__setattr__(self, "metadata", metadata); object.__setattr__(self, "signature", expected)

    def to_dict(self, *, include_field_values: bool = True) -> dict[str, Any]:
        return {"schema": FORCE_REFINEMENT_CATALOG_SCHEMA, "sample_catalog_signature": self.sample_catalog_signature,
                "density_estimate_signature": self.density_estimate_signature, "attractor_catalog_signature": self.attractor_catalog_signature,
                "options": self.options.to_dict(), "resources": self.resources.to_dict(),
                "mean_force_field": None if self.mean_force_field is None else self.mean_force_field.to_dict(include_values=include_field_values),
                "refinements": [r.to_dict() for r in self.refinements], "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ForceRefinementCatalog":
        if p.get("schema") != FORCE_REFINEMENT_CATALOG_SCHEMA: raise ForceRefinementSerializationError("Unsupported force-refinement-catalog schema.")
        return cls(sample_catalog_signature=str(p["sample_catalog_signature"]), density_estimate_signature=str(p["density_estimate_signature"]),
                   attractor_catalog_signature=str(p["attractor_catalog_signature"]), options=LocalMeanForceOptions.from_dict(p["options"]),
                   resources=LocalMeanForceResourcePolicy.from_dict(p["resources"]),
                   mean_force_field=None if p.get("mean_force_field") is None else MatchedMeanForceField.from_dict(p["mean_force_field"]),
                   refinements=tuple(LocalForceRefinement.from_dict(v) for v in p["refinements"]), metadata=p.get("metadata", {}),
                   signature=str(p.get("signature", "")))


def _logical_grid(shape: tuple[int, int, int]) -> np.ndarray:
    axes = [np.arange(n, dtype=float) / n for n in shape]
    return np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)


def _matched_field(catalog: FrameworkAlignedIonSampleCatalog, estimate: PeriodicSpeciesDensityEstimate,
                   options: LocalMeanForceOptions, resources: LocalMeanForceResourcePolicy) -> MatchedMeanForceField | None:
    indices = catalog.sample_indices_for("pmf_force")
    if catalog.transformed_forces is None or indices.size == 0:
        return None
    shape = estimate.realization.grid_shape; nodes = int(np.prod(shape)); samples = int(indices.size)
    images = estimate.image_truncation.image_shifts(); terms = nodes * samples * len(images)
    if nodes > resources.max_grid_nodes: raise ForceRefinementResourceError(f"grid nodes {nodes}>{resources.max_grid_nodes}")
    if samples > resources.max_force_samples: raise ForceRefinementResourceError(f"force samples {samples}>{resources.max_force_samples}")
    if terms > resources.max_kernel_terms: raise ForceRefinementResourceError(f"kernel terms {terms}>{resources.max_kernel_terms}")
    workspace = options.query_batch_size * min(samples, options.sample_batch_size) * 3 * 8 * 6
    if workspace > resources.max_workspace_bytes: raise ForceRefinementResourceError("Matched-force workspace exceeds max_workspace_bytes.")
    output = nodes * (3 + 9 + 1 + 1 + (3 if options.uncertainty_blocks >= 2 else 0)) * 8
    if output > resources.max_output_bytes: raise ForceRefinementResourceError("Matched-force output exceeds max_output_bytes.")
    q = _logical_grid(shape); s = np.mod(catalog.registered_wrapped_fractional[indices], 1.0)
    w = np.asarray(catalog.represented_time_weights[indices], float)
    # Registered forces are Cartesian covectors; q is fractional, x=qH, hence F_q=F_x H^T.
    fq = np.asarray(catalog.transformed_forces[indices] @ estimate.domain.cell.T, float)
    precision, normalizer = estimate.kernel_covariance.precision, estimate.kernel_covariance.normalizer
    den = np.zeros(nodes); den2 = np.zeros(nodes); num = np.zeros((nodes,3)); second = np.zeros((nodes,3,3))
    for qa in range(0, nodes, options.query_batch_size):
        qb = min(qa + options.query_batch_size, nodes); qq = q[qa:qb]
        for sa in range(0, samples, options.sample_batch_size):
            sb = min(sa + options.sample_batch_size, samples); ss=s[sa:sb]; ww=w[sa:sb]; ff=fq[sa:sb]
            for shift in images:
                d = qq[:,None,:]-ss[None,:,:]+shift[None,None,:]
                pd = np.einsum("bsi,ij->bsj", d, precision, optimize=True)
                k = normalizer*np.exp(-0.5*np.einsum("bsi,bsi->bs", d,pd,optimize=True))
                kw = k*ww[None,:]
                den[qa:qb] += kw.sum(1); den2[qa:qb] += (kw*kw).sum(1)
                num[qa:qb] += np.einsum("bs,sj->bj", kw,ff,optimize=True)
                second[qa:qb] += np.einsum("bs,si,sj->bij", kw,ff,ff,optimize=True)
    neff=np.zeros(nodes); good2=den2>0; neff[good2]=den[good2]**2/den2[good2]
    support = (den>0) & (neff>=options.minimum_effective_samples) & estimate.realization.support_mask_dense().reshape(-1)
    mean=np.zeros((nodes,3)); cov=np.zeros((nodes,3,3)); mean[support]=num[support]/den[support,None]
    cov[support]=second[support]/den[support,None,None]-np.einsum("bi,bj->bij",mean[support],mean[support])
    cov[support]=0.5*(cov[support]+np.swapaxes(cov[support],1,2))
    stderr=None
    if options.uncertainty_blocks>=2:
        frame_ids=catalog.frame_ids[indices]; unique=np.unique(frame_ids); blocks=np.array_split(unique, min(options.uncertainty_blocks,len(unique)))
        reps=[]
        for block in blocks:
            mask=np.isin(frame_ids,block)
            if not np.any(mask): continue
            bd=np.zeros(nodes); bn=np.zeros((nodes,3))
            for qa in range(0,nodes,options.query_batch_size):
                qb=min(qa+options.query_batch_size,nodes); qq=q[qa:qb]
                ss=s[mask]; ww=w[mask]; ff=fq[mask]
                for sa in range(0,len(ss),options.sample_batch_size):
                    sb=min(sa+options.sample_batch_size,len(ss))
                    for shift in images:
                        d=qq[:,None,:]-ss[None,sa:sb,:]+shift[None,None,:]
                        pd=np.einsum("bsi,ij->bsj",d,precision,optimize=True)
                        kw=normalizer*np.exp(-0.5*np.einsum("bsi,bsi->bs",d,pd,optimize=True))*ww[None,sa:sb]
                        bd[qa:qb]+=kw.sum(1); bn[qa:qb]+=np.einsum("bs,sj->bj",kw,ff[sa:sb],optimize=True)
            bm=np.zeros_like(bn); ok=bd>0; bm[ok]=bn[ok]/bd[ok,None]; reps.append(bm)
        if len(reps)>=2:
            stderr=np.std(np.stack(reps),axis=0,ddof=1)/np.sqrt(len(reps)); stderr[~support]=0.0
    return MatchedMeanForceField(shape,mean.reshape(shape+(3,)),cov.reshape(shape+(3,3)),neff.reshape(shape),support.reshape(shape),
                                 None if stderr is None else stderr.reshape(shape+(3,)),samples,float(w.sum()),estimate.signature,catalog.signature,
                                 metadata={"stage":FORCE_REFINEMENT_STAGE,"kernel":"matched_stage11e1_periodized_gaussian",
                                           "force_coordinate_measure":"fractional_covector","support_intersects_stage11e1":True})


def _design(delta: np.ndarray) -> np.ndarray:
    n=len(delta); X=np.zeros((3*n,9))
    for a,(x,y,z) in enumerate(delta):
        r=3*a
        X[r,0]=1; X[r,3]=-x; X[r,6]=-y; X[r,7]=-z
        X[r+1,1]=1; X[r+1,4]=-y; X[r+1,6]=-x; X[r+1,8]=-z
        X[r+2,2]=1; X[r+2,5]=-z; X[r+2,7]=-x; X[r+2,8]=-y
    return X


def _unpack(beta: np.ndarray) -> tuple[np.ndarray,np.ndarray]:
    b=beta[:3]; K=np.array([[beta[3],beta[6],beta[7]],[beta[6],beta[4],beta[8]],[beta[7],beta[8],beta[5]]],float)
    return b,K


def _owner_for_samples(frac: np.ndarray, owner: np.ndarray) -> np.ndarray:
    shape=np.asarray(owner.shape); idx=np.mod(np.rint(np.mod(frac,1.0)*shape).astype(int),shape)
    return owner[idx[:,0],idx[:,1],idx[:,2]]


def _periodic_delta(points: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    d=np.asarray(points)-np.asarray(anchor); return d-np.rint(d)


def _empty_refinement(aid:int, geom:AttractorGeometry, anchor:np.ndarray, status:ForceEvidenceStatus, diagnostic:str) -> LocalForceRefinement:
    return LocalForceRefinement(aid,geom,status,CurvatureClass.NOT_EVALUATED,np.empty(0,dtype=np.int64),anchor,None,None,None,None,None,None,None,0,None,None,None,None,None,None,diagnostic)


def prepare_force_refinement_catalog(
    catalog: FrameworkAlignedIonSampleCatalog,
    density_estimate: PeriodicSpeciesDensityEstimate,
    attractor_catalog: DensityAttractorCatalog,
    *,
    options: LocalMeanForceOptions | None = None,
    resources: LocalMeanForceResourcePolicy | None = None,
) -> ForceRefinementCatalog:
    """Prepare matched mean forces and local E2-attractor force refinements."""
    options=LocalMeanForceOptions() if options is None else options
    resources=LocalMeanForceResourcePolicy() if resources is None else resources
    if density_estimate.catalog_signature!=catalog.signature: raise ForceRefinementInputError("Density estimate is bound to another sample catalog.")
    if attractor_catalog.density_estimate_signature!=density_estimate.signature: raise ForceRefinementInputError("Attractor catalog is bound to another density estimate.")
    if len(attractor_catalog.attractors)>resources.max_attractors: raise ForceRefinementResourceError("Attractor count exceeds max_attractors.")
    field=_matched_field(catalog,density_estimate,options,resources)
    pmf_indices=catalog.sample_indices_for("pmf_force")
    if catalog.transformed_forces is None:
        refs=tuple(_empty_refinement(a.attractor_id,a.geometry,a.anchor_fractional,ForceEvidenceStatus.FORCE_UNAVAILABLE,"transformed forces unavailable") for a in attractor_catalog.attractors)
    elif pmf_indices.size==0:
        refs=tuple(_empty_refinement(a.attractor_id,a.geometry,a.anchor_fractional,ForceEvidenceStatus.PMF_PROVENANCE_REJECTED,"no PMF-admissible joint samples") for a in attractor_catalog.attractors)
    else:
        frac=catalog.registered_wrapped_fractional[pmf_indices]; forces_x=catalog.transformed_forces[pmf_indices]
        forces_q=forces_x@density_estimate.domain.cell.T
        metric=density_estimate.analysis_metric; L=metric.orthonormal_factor; invL=np.linalg.inv(L)
        force_y=metric.covectors_in_orthonormal_chart(forces_q)
        weights=catalog.represented_time_weights[pmf_indices]
        owners=_owner_for_samples(frac,attractor_catalog.cell_complex.basin_owner)
        position_indices=catalog.sample_indices_for("position"); pos_frac=catalog.registered_wrapped_fractional[position_indices]
        pos_owners=_owner_for_samples(pos_frac,attractor_catalog.cell_complex.basin_owner)
        temperature=catalog.pmf_temperature.temperature_kelvin
        kbt=None if temperature is None else options.boltzmann_constant*temperature
        score=density_estimate.realization.density_score_covector_dense().reshape(-1,3)
        refs_list=[]
        for a in attractor_catalog.attractors:
            if a.local_chart.kind is LocalChartKind.MANIFOLD_UNRESOLVED:
                refs_list.append(_empty_refinement(a.attractor_id,a.geometry,a.anchor_fractional,ForceEvidenceStatus.CHART_UNRESOLVED,"local chart unresolved")); continue
            local=np.flatnonzero(owners==a.attractor_id)
            if local.size:
                dq=_periodic_delta(frac[local],a.anchor_fractional)
                # The nearest periodic lift is unique away from the half-cell cut.
                # The E3 fit chart is the union of the E2 chart and these certified
                # residence lifts; this avoids a zero-radius one-node E2 chart.
                keep=np.all(np.abs(dq)<(0.5-1.0e-12),axis=1)
                local=local[keep]; dq=dq[keep]; dy=dq@L
                fit_radius=max(a.local_chart.validity_radius*options.chart_radius_factor,
                               float(np.max(np.linalg.norm(dy,axis=1))) if len(dy) else 0.0)
            else:
                dy=np.empty((0,3)); fit_radius=0.0
            selected=pmf_indices[local]
            if len(local)<options.minimum_fit_samples:
                refs_list.append(LocalForceRefinement(a.attractor_id,a.geometry,ForceEvidenceStatus.INSUFFICIENT_LOCAL_SUPPORT,
                    CurvatureClass.NOT_EVALUATED,selected,a.anchor_fractional,None,None,None,None,None,None,None,0,None,None,None,None,None,None,
                    f"local PMF-force samples {len(local)}<{options.minimum_fit_samples}")); continue
            X=_design(dy); yy=force_y[local].reshape(-1); sw=np.repeat(np.sqrt(weights[local]/np.mean(weights[local])),3)
            Xw=X*sw[:,None]; yw=yy*sw
            beta,_,rank,svals=np.linalg.lstsq(Xw,yw,rcond=None); cond=float(np.inf if svals[-1]<=0 else svals[0]/svals[-1])
            if rank<9:
                refs_list.append(LocalForceRefinement(a.attractor_id,a.geometry,ForceEvidenceStatus.RANK_DEFICIENT,CurvatureClass.NOT_EVALUATED,
                    selected,a.anchor_fractional,None,None,None,None,None,None,None,int(rank),cond,None,None,None,None,None,None,"symmetric harmonic design rank deficient")); continue
            if cond>options.maximum_condition_number:
                refs_list.append(LocalForceRefinement(a.attractor_id,a.geometry,ForceEvidenceStatus.ILL_CONDITIONED,CurvatureClass.NOT_EVALUATED,
                    selected,a.anchor_fractional,None,None,None,None,None,None,None,int(rank),cond,None,None,None,None,None,None,"symmetric harmonic fit ill conditioned")); continue
            b,K=_unpack(beta); eigval,eigvec=np.linalg.eigh(K)
            predicted=X@beta; residual=(yy-predicted).reshape(-1,3); rw=weights[local]/weights[local].sum()
            rcov=np.einsum("n,ni,nj->ij",rw,residual,residual); dof=max(3*len(local)-9,1)
            sigma2=float(np.sum((yw-Xw@beta)**2)/dof); pcov=sigma2*np.linalg.pinv(Xw.T@Xw); pstd=np.sqrt(np.maximum(np.diag(pcov),0.0))
            maxabs=max(float(np.max(np.abs(eigval))),options.minimum_stiffness)
            if np.any(eigval < -options.minimum_stiffness): curvature=CurvatureClass.SADDLE_OR_UNSTABLE
            elif a.geometry is AttractorGeometry.RIDGE_OR_MANIFOLD and np.count_nonzero(eigval>options.minimum_stiffness)>=2 and abs(float(eigval[0]))<=options.soft_direction_ratio*maxabs:
                curvature=CurvatureClass.SOFT_MANIFOLD
            elif np.all(eigval>options.minimum_stiffness): curvature=CurvatureClass.STABLE_POINT
            else: curvature=CurvatureClass.FLAT_OR_UNRESOLVED
            center=None; inside=None; status=ForceEvidenceStatus.RESOLVED
            if a.geometry is AttractorGeometry.ISOLATED_MODE and np.min(np.abs(eigval))>options.minimum_stiffness:
                center_y=b@np.linalg.inv(K); center_q=center_y@invL
                center=np.mod(a.anchor_fractional+center_q,1.0); inside=bool(np.linalg.norm(center_y)<=max(fit_radius, np.finfo(float).eps))
                if not inside: status=ForceEvidenceStatus.CENTER_OUTSIDE_CHART
            pos_local=np.flatnonzero(pos_owners==a.attractor_id); residence=None
            if len(pos_local)>=2:
                py=_periodic_delta(pos_frac[pos_local],a.anchor_fractional)@L
                pw=catalog.represented_time_weights[position_indices[pos_local]]; pw=pw/pw.sum(); pm=np.sum(py*pw[:,None],axis=0)
                residence=np.einsum("n,ni,nj->ij",pw,py-pm,py-pm)
            harmonic=None; cov_err=None
            if kbt is not None and np.min(eigval)>options.minimum_stiffness:
                harmonic=kbt*np.linalg.inv(K)
                if residence is not None:
                    cov_err=float(np.linalg.norm(residence-harmonic)/max(np.linalg.norm(harmonic),np.finfo(float).tiny))
            density_res=None
            if field is not None and kbt is not None:
                node=a.representative_node_index; mf=field.conditional_force_covector.reshape(-1,3)[node]
                if field.support_mask.reshape(-1)[node]: density_res=float(np.linalg.norm(mf-kbt*score[node]))
            refs_list.append(LocalForceRefinement(a.attractor_id,a.geometry,status,curvature,selected,a.anchor_fractional,center,b,K,eigval,eigvec,rcov,pstd,
                                                  int(rank),cond,inside,residence,harmonic,cov_err,density_res,None))
        refs=tuple(refs_list)
    return ForceRefinementCatalog(catalog.signature,density_estimate.signature,attractor_catalog.signature,options,resources,field,refs,
                                  metadata={"stage":FORCE_REFINEMENT_STAGE,"spatial_attractors_preserved":True,
                                            "force_matching_reference":"Noid et al. 2008 DOI 10.1063/1.2938860",
                                            "average_force_reference":"Darve and Pohorille 2001 DOI 10.1063/1.1410978",
                                            "global_pmf_reconstruction_performed":False})


__all__ = [
    "BOLTZMANN_EV_PER_K", "FORCE_REFINEMENT_CATALOG_SCHEMA", "FORCE_REFINEMENT_STAGE",
    "LOCAL_FORCE_REFINEMENT_SCHEMA", "LOCAL_MEAN_FORCE_OPTIONS_SCHEMA", "LOCAL_MEAN_FORCE_RESOURCES_SCHEMA",
    "MATCHED_MEAN_FORCE_FIELD_SCHEMA", "CurvatureClass", "ForceEvidenceStatus", "ForceRefinementCatalog",
    "ForceRefinementError", "ForceRefinementInputError", "ForceRefinementResourceError", "ForceRefinementSerializationError",
    "LocalForceRefinement", "LocalMeanForceOptions", "LocalMeanForceResourcePolicy", "MatchedMeanForceField",
    "prepare_force_refinement_catalog",
]
