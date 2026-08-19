"""Training-domain-local atomic reference-energy fitting for MLFF-DATA7/DATA9A.

Two distinct fitting modes are supported:

``from_scratch_total_energy``
    Decompose the target DFT total energies directly. This is retained for
    models trained from scratch and for backwards-compatible diagnostics.

``foundation_residual``
    Fit elemental corrections to ``E_DFT - E_foundation`` and add those
    corrections to the foundation checkpoint's elemental references. This is
    the required production mode for foundation-model fine-tuning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, MutableMapping

import numpy as np
from ase.data import chemical_symbols

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from ._frame_access import build_frame_array_index
from .feature_metric import FeatureFitDomain, build_feature_fit_domains

ATOMIC_REFERENCE_FIT_POLICY_SCHEMA = "mdstats.atomic-reference-fit-policy.v2"
ATOMIC_REFERENCE_FIT_RECORD_SCHEMA = "mdstats.atomic-reference-fit-record.v3"
ATOMIC_REFERENCE_FIT_RECORD_V2_SCHEMA = "mdstats.atomic-reference-fit-record.v2"
ATOMIC_REFERENCE_FIT_POLICY_VERSION = "mdstats.mlff-data9a.atomic-reference-fit.2026-07.v2"


class AtomicReferenceFitMode(str, Enum):
    FROM_SCRATCH_TOTAL_ENERGY = "from_scratch_total_energy"
    FOUNDATION_RESIDUAL = "foundation_residual"


@dataclass(frozen=True, slots=True)
class AtomicReferenceFitPolicy:
    fit_mode: AtomicReferenceFitMode = AtomicReferenceFitMode.FROM_SCRATCH_TOTAL_ENERGY
    ridge_lambda: float = 0.0
    allow_rank_deficient_fixed_domain: bool = True
    prior_by_atomic_number: tuple[tuple[int, float], ...] = ()
    relative_singular_value_tolerance: float = 1.0e-12
    policy_version: str = ATOMIC_REFERENCE_FIT_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "fit_mode", AtomicReferenceFitMode(self.fit_mode))
        ridge = float(self.ridge_lambda)
        tolerance = float(self.relative_singular_value_tolerance)
        if not np.isfinite(ridge) or ridge < 0.0 or not np.isfinite(tolerance) or tolerance <= 0.0:
            raise TrainingDataInputError("Atomic-reference fit tolerances are invalid.")
        prior = tuple(sorted((int(z), float(v)) for z, v in self.prior_by_atomic_number))
        if len({z for z, _ in prior}) != len(prior) or any(z <= 0 or not np.isfinite(v) for z, v in prior):
            raise TrainingDataInputError("Atomic-reference prior is invalid.")
        object.__setattr__(self, "ridge_lambda", ridge)
        object.__setattr__(self, "relative_singular_value_tolerance", tolerance)
        object.__setattr__(self, "prior_by_atomic_number", prior)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_REFERENCE_FIT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "fit_mode": self.fit_mode.value,
            "ridge_lambda": self.ridge_lambda,
            "allow_rank_deficient_fixed_domain": self.allow_rank_deficient_fixed_domain,
            "prior_by_atomic_number": {str(z): value for z, value in self.prior_by_atomic_number},
            "relative_singular_value_tolerance": self.relative_singular_value_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicReferenceFitPolicy":
        schema = payload.get("schema")
        if schema not in {ATOMIC_REFERENCE_FIT_POLICY_SCHEMA, "mdstats.atomic-reference-fit-policy.v1"}:
            raise TrainingDataSerializationError("Unsupported atomic-reference fit-policy schema.")
        result = cls(
            fit_mode=AtomicReferenceFitMode(payload.get("fit_mode", AtomicReferenceFitMode.FROM_SCRATCH_TOTAL_ENERGY.value)),
            ridge_lambda=float(payload["ridge_lambda"]),
            allow_rank_deficient_fixed_domain=bool(payload["allow_rank_deficient_fixed_domain"]),
            prior_by_atomic_number=tuple((int(k), float(v)) for k, v in payload.get("prior_by_atomic_number", {}).items()),
            relative_singular_value_tolerance=float(payload["relative_singular_value_tolerance"]),
            policy_version=str(payload.get("policy_version", ATOMIC_REFERENCE_FIT_POLICY_VERSION)),
        )
        if schema == ATOMIC_REFERENCE_FIT_POLICY_SCHEMA and payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Atomic-reference fit-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomicReferenceFitRecord:
    domain: FeatureFitDomain
    policy: AtomicReferenceFitPolicy
    frame_catalog_digest: str
    element_order: tuple[int, ...]
    element_symbols: tuple[str, ...]
    count_matrix: tuple[tuple[int, ...], ...]
    target_energies_ev: tuple[float, ...]
    fitted_targets_ev: tuple[float, ...]
    foundation_prediction_energies_ev: tuple[float, ...] | None
    foundation_reference_energies_ev: tuple[tuple[int, float], ...]
    correction_energies_ev: tuple[tuple[int, float], ...]
    reference_energies_ev: tuple[tuple[int, float], ...]
    foundation_checkpoint_digest: str | None
    rank: int
    singular_values: tuple[float, ...]
    null_space_dimension: int
    residual_rmse_ev: float
    residual_mae_ev: float
    maximum_absolute_residual_ev: float
    rank_deficient: bool
    transfer_warnings: tuple[str, ...]
    foundation_identity_digest: str | None = None
    serialization_schema: str = ATOMIC_REFERENCE_FIT_RECORD_SCHEMA
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        if self.foundation_checkpoint_digest is not None:
            object.__setattr__(self, "foundation_checkpoint_digest", validate_digest(self.foundation_checkpoint_digest, name="foundation_checkpoint_digest"))
        if self.foundation_identity_digest is not None:
            object.__setattr__(self, "foundation_identity_digest", validate_digest(self.foundation_identity_digest, name="foundation_identity_digest"))
        if self.serialization_schema not in {ATOMIC_REFERENCE_FIT_RECORD_SCHEMA, ATOMIC_REFERENCE_FIT_RECORD_V2_SCHEMA}:
            raise TrainingDataInputError("Unsupported atomic-reference fit serialization schema.")
        elements = tuple(int(v) for v in self.element_order)
        symbols = tuple(str(v) for v in self.element_symbols)
        matrix = tuple(tuple(int(v) for v in row) for row in self.count_matrix)
        target = tuple(float(v) for v in self.target_energies_ev)
        fitted_targets = tuple(float(v) for v in self.fitted_targets_ev)
        predictions = None if self.foundation_prediction_energies_ev is None else tuple(float(v) for v in self.foundation_prediction_energies_ev)
        foundation_refs = tuple(sorted((int(z), float(v)) for z, v in self.foundation_reference_energies_ev))
        corrections = tuple(sorted((int(z), float(v)) for z, v in self.correction_energies_ev))
        refs = tuple(sorted((int(z), float(v)) for z, v in self.reference_energies_ev))
        if not elements or len(elements) != len(symbols) or len(matrix) != len(self.domain.frame_uids):
            raise TrainingDataInputError("Atomic-reference fit arrays are inconsistent.")
        if len(target) != len(matrix) or len(fitted_targets) != len(matrix):
            raise TrainingDataInputError("Atomic-reference target arrays are inconsistent.")
        if predictions is not None and len(predictions) != len(matrix):
            raise TrainingDataInputError("Foundation predictions do not match the fit domain.")
        if any(len(row) != len(elements) for row in matrix) or any(v < 0 for row in matrix for v in row):
            raise TrainingDataInputError("Atomic-reference count matrix is invalid.")
        if tuple(z for z, _ in corrections) != elements or tuple(z for z, _ in refs) != elements:
            raise TrainingDataInputError("Atomic-reference mapping does not match element order.")
        if self.policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
            lineage = self.foundation_identity_digest or self.foundation_checkpoint_digest
            if predictions is None or tuple(z for z, _ in foundation_refs) != elements or lineage is None:
                raise TrainingDataInputError("Foundation-residual fits require predictions, foundation E0s, and foundation identity.")
            if self.serialization_schema == ATOMIC_REFERENCE_FIT_RECORD_SCHEMA and self.foundation_identity_digest is None:
                raise TrainingDataInputError("Atomic-reference fit v3 requires head-qualified foundation identity.")
        elif predictions is not None or foundation_refs or self.foundation_checkpoint_digest is not None or self.foundation_identity_digest is not None:
            raise TrainingDataInputError("From-scratch E0 fits cannot carry foundation-model state.")
        numeric = [*target, *fitted_targets, *(v for _, v in corrections), *(v for _, v in refs), *self.singular_values]
        if predictions is not None:
            numeric.extend(predictions)
        numeric.extend(v for _, v in foundation_refs)
        if any(not np.isfinite(v) for v in numeric):
            raise TrainingDataInputError("Atomic-reference fit contains non-finite values.")
        if self.rank < 0 or self.rank > len(elements) or self.null_space_dimension != len(elements) - self.rank:
            raise TrainingDataInputError("Atomic-reference fit rank is inconsistent.")
        for name in ("residual_rmse_ev", "residual_mae_ev", "maximum_absolute_residual_ev"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "element_order", elements)
        object.__setattr__(self, "element_symbols", symbols)
        object.__setattr__(self, "count_matrix", matrix)
        object.__setattr__(self, "target_energies_ev", target)
        object.__setattr__(self, "fitted_targets_ev", fitted_targets)
        object.__setattr__(self, "foundation_prediction_energies_ev", predictions)
        object.__setattr__(self, "foundation_reference_energies_ev", foundation_refs)
        object.__setattr__(self, "correction_energies_ev", corrections)
        object.__setattr__(self, "reference_energies_ev", refs)
        object.__setattr__(self, "singular_values", tuple(float(v) for v in self.singular_values))
        object.__setattr__(self, "transfer_warnings", tuple(str(v) for v in self.transfer_warnings))

    @property
    def total_energies_ev(self) -> tuple[float, ...]:
        """Backward-compatible alias for the target DFT energies."""
        return self.target_energies_ev

    @property
    def explicit_mapping(self) -> dict[int, float]:
        return dict(self.reference_energies_ev)

    @property
    def correction_mapping(self) -> dict[int, float]:
        return dict(self.correction_energies_ev)

    @property
    def is_foundation_residual_fit(self) -> bool:
        return self.policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL

    @property
    def foundation_lineage_digest(self) -> str | None:
        return self.foundation_identity_digest or self.foundation_checkpoint_digest

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "domain": self.domain.to_dict(),
            "policy": self.policy.to_dict(),
            "frame_catalog_digest": self.frame_catalog_digest,
            "element_order": list(self.element_order),
            "element_symbols": list(self.element_symbols),
            "count_matrix": [list(row) for row in self.count_matrix],
            "target_energies_ev": list(self.target_energies_ev),
            "fitted_targets_ev": list(self.fitted_targets_ev),
            "foundation_prediction_energies_ev": None if self.foundation_prediction_energies_ev is None else list(self.foundation_prediction_energies_ev),
            "foundation_reference_energies_ev": {str(z): value for z, value in self.foundation_reference_energies_ev},
            "correction_energies_ev": {str(z): value for z, value in self.correction_energies_ev},
            "reference_energies_ev": {str(z): value for z, value in self.reference_energies_ev},
            "rank": self.rank,
            "singular_values": list(self.singular_values),
            "null_space_dimension": self.null_space_dimension,
            "residual_rmse_ev": self.residual_rmse_ev,
            "residual_mae_ev": self.residual_mae_ev,
            "maximum_absolute_residual_ev": self.maximum_absolute_residual_ev,
            "rank_deficient": self.rank_deficient,
            "transfer_warnings": list(self.transfer_warnings),
        }
        if self.serialization_schema == ATOMIC_REFERENCE_FIT_RECORD_SCHEMA:
            payload["foundation_identity_digest"] = self.foundation_identity_digest
        else:
            payload["foundation_checkpoint_digest"] = self.foundation_checkpoint_digest
        return payload

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
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicReferenceFitRecord":
        schema = payload.get("schema")
        if schema == "mdstats.atomic-reference-fit-record.v1":
            # Replay legacy DATA7 records as explicit from-scratch fits.
            target = tuple(float(v) for v in payload["total_energies_ev"])
            mapping = tuple((int(k), float(v)) for k, v in payload["reference_energies_ev"].items())
            result = cls(
                domain=FeatureFitDomain.from_dict(payload["domain"]),
                policy=AtomicReferenceFitPolicy.from_dict(payload["policy"]),
                frame_catalog_digest=str(payload["frame_catalog_digest"]),
                element_order=tuple(int(v) for v in payload["element_order"]),
                element_symbols=tuple(str(v) for v in payload["element_symbols"]),
                count_matrix=tuple(tuple(int(v) for v in row) for row in payload["count_matrix"]),
                target_energies_ev=target,
                fitted_targets_ev=target,
                foundation_prediction_energies_ev=None,
                foundation_reference_energies_ev=(),
                correction_energies_ev=mapping,
                reference_energies_ev=mapping,
                foundation_checkpoint_digest=None,
                foundation_identity_digest=None,
                serialization_schema=ATOMIC_REFERENCE_FIT_RECORD_V2_SCHEMA,
                rank=int(payload["rank"]),
                singular_values=tuple(float(v) for v in payload["singular_values"]),
                null_space_dimension=int(payload["null_space_dimension"]),
                residual_rmse_ev=float(payload["residual_rmse_ev"]),
                residual_mae_ev=float(payload["residual_mae_ev"]),
                maximum_absolute_residual_ev=float(payload["maximum_absolute_residual_ev"]),
                rank_deficient=bool(payload["rank_deficient"]),
                transfer_warnings=tuple(str(v) for v in payload.get("transfer_warnings", ())),
            )
            return result
        if schema not in {ATOMIC_REFERENCE_FIT_RECORD_SCHEMA, ATOMIC_REFERENCE_FIT_RECORD_V2_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported atomic-reference-fit schema.")
        result = cls(
            domain=FeatureFitDomain.from_dict(payload["domain"]),
            policy=AtomicReferenceFitPolicy.from_dict(payload["policy"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            element_order=tuple(int(v) for v in payload["element_order"]),
            element_symbols=tuple(str(v) for v in payload["element_symbols"]),
            count_matrix=tuple(tuple(int(v) for v in row) for row in payload["count_matrix"]),
            target_energies_ev=tuple(float(v) for v in payload["target_energies_ev"]),
            fitted_targets_ev=tuple(float(v) for v in payload["fitted_targets_ev"]),
            foundation_prediction_energies_ev=None if payload.get("foundation_prediction_energies_ev") is None else tuple(float(v) for v in payload["foundation_prediction_energies_ev"]),
            foundation_reference_energies_ev=tuple((int(k), float(v)) for k, v in payload.get("foundation_reference_energies_ev", {}).items()),
            correction_energies_ev=tuple((int(k), float(v)) for k, v in payload["correction_energies_ev"].items()),
            reference_energies_ev=tuple((int(k), float(v)) for k, v in payload["reference_energies_ev"].items()),
            foundation_checkpoint_digest=None if payload.get("foundation_checkpoint_digest") is None else str(payload["foundation_checkpoint_digest"]),
            foundation_identity_digest=None if payload.get("foundation_identity_digest") is None else str(payload["foundation_identity_digest"]),
            serialization_schema=str(schema),
            rank=int(payload["rank"]),
            singular_values=tuple(float(v) for v in payload["singular_values"]),
            null_space_dimension=int(payload["null_space_dimension"]),
            residual_rmse_ev=float(payload["residual_rmse_ev"]),
            residual_mae_ev=float(payload["residual_mae_ev"]),
            maximum_absolute_residual_ev=float(payload["maximum_absolute_residual_ev"]),
            rank_deficient=bool(payload["rank_deficient"]),
            transfer_warnings=tuple(str(v) for v in payload.get("transfer_warnings", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Atomic-reference-fit digest mismatch.")
        return result


def fit_atomic_reference_energies(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    domain: FeatureFitDomain,
    *,
    policy: AtomicReferenceFitPolicy | None = None,
    foundation_prediction_energy_by_frame: Mapping[str, float] | None = None,
    foundation_reference_energies: Mapping[int, float] | None = None,
    foundation_checkpoint_digest: str | None = None,
    foundation_identity_digest: str | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    composition_count_cache: MutableMapping[str, Mapping[int, int]] | None = None,
    canonical_domain_digests: set[str] | frozenset[str] | None = None,
) -> AtomicReferenceFitRecord:
    canonical = (
        {item.content_digest for item in build_feature_fit_domains(data5_bundle)}
        if canonical_domain_digests is None
        else canonical_domain_digests
    )
    if domain.content_digest not in canonical:
        raise TrainingDataInputError("Atomic-reference fitting requires a canonical DATA5 training domain.")
    active = AtomicReferenceFitPolicy() if policy is None else policy
    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    counts_by_run = composition_count_cache if composition_count_cache is not None else {}
    run_ids = tuple({str(index[uid][0].run_id) for uid in domain.frame_uids})
    element_set: set[int] = set()
    for run_id in run_ids:
        counts = counts_by_run.get(run_id)
        if counts is None:
            data = frame_data_by_run[run_id]
            numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
            unique, multiplicities = np.unique(numbers, return_counts=True)
            counts = {
                int(z): int(count)
                for z, count in zip(unique, multiplicities, strict=True)
            }
            counts_by_run[run_id] = counts
        element_set.update(int(z) for z in counts)
    elements = tuple(sorted(element_set))
    element_position = {z: position for position, z in enumerate(elements)}
    frame_count = len(domain.frame_uids)
    A = np.zeros((frame_count, len(elements)), dtype=np.float64)
    target = np.empty(frame_count, dtype=np.float64)
    for row, uid in enumerate(domain.frame_uids):
        frame_record, data, local = index[uid]
        counts = counts_by_run[str(frame_record.run_id)]
        for z, count in counts.items():
            A[row, element_position[int(z)]] = int(count)
        if data.energies_ev is None:
            raise TrainingDataInputError("Atomic-reference fitting requires total energies on every frame.")
        value = float(data.energies_ev[local])
        if not np.isfinite(value):
            raise TrainingDataInputError("Atomic-reference fitting encountered a non-finite target energy.")
        target[row] = value
    predictions: np.ndarray | None = None
    foundation_refs: dict[int, float] = {}
    if active.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        if foundation_prediction_energy_by_frame is None or foundation_reference_energies is None or (foundation_identity_digest is None and foundation_checkpoint_digest is None):
            raise TrainingDataInputError(
                "Foundation-residual E0 fitting requires per-frame foundation predictions, foundation E0s, and foundation identity."
            )
        missing_predictions = [uid for uid in domain.frame_uids if uid not in foundation_prediction_energy_by_frame]
        if missing_predictions:
            raise TrainingDataInputError(f"Missing foundation predictions for {len(missing_predictions)} fit-domain frames.")
        predictions = np.asarray([float(foundation_prediction_energy_by_frame[uid]) for uid in domain.frame_uids], dtype=np.float64)
        if not np.all(np.isfinite(predictions)):
            raise TrainingDataInputError("Foundation predictions contain non-finite values.")
        foundation_refs = {int(z): float(v) for z, v in foundation_reference_energies.items()}
        missing_refs = sorted(set(elements) - set(foundation_refs))
        if missing_refs or any(not np.isfinite(foundation_refs[z]) for z in elements):
            raise TrainingDataInputError(f"Foundation E0 mapping is missing or invalid for atomic numbers: {missing_refs}.")
        fit_target = target - predictions
        checkpoint_digest = None if foundation_checkpoint_digest is None else validate_digest(foundation_checkpoint_digest, name="foundation_checkpoint_digest")
        identity_digest = None if foundation_identity_digest is None else validate_digest(foundation_identity_digest, name="foundation_identity_digest")
    else:
        if foundation_prediction_energy_by_frame is not None or foundation_reference_energies is not None or foundation_checkpoint_digest is not None or foundation_identity_digest is not None:
            raise TrainingDataInputError("Foundation data were supplied to a from-scratch atomic-reference fit.")
        fit_target = target
        checkpoint_digest = None
        identity_digest = None
    singular_values = np.linalg.svd(A, compute_uv=False)
    threshold = active.relative_singular_value_tolerance * (singular_values[0] if singular_values.size else 1.0)
    rank = int(np.count_nonzero(singular_values > threshold))
    rank_deficient = rank < len(elements)
    if rank_deficient and not active.allow_rank_deficient_fixed_domain:
        raise TrainingDataInputError("Atomic-reference count matrix is rank deficient under the active policy.")
    prior_map = dict(active.prior_by_atomic_number)
    prior = np.asarray([prior_map.get(z, 0.0) for z in elements], dtype=np.float64)
    if active.ridge_lambda > 0.0:
        augmented_A = np.vstack((A, np.sqrt(active.ridge_lambda) * np.eye(len(elements))))
        augmented_y = np.concatenate((fit_target, np.sqrt(active.ridge_lambda) * prior))
        fitted, *_ = np.linalg.lstsq(augmented_A, augmented_y, rcond=active.relative_singular_value_tolerance)
    else:
        fitted, *_ = np.linalg.lstsq(A, fit_target, rcond=active.relative_singular_value_tolerance)
    residual = A @ fitted - fit_target
    correction_map = {z: float(value) for z, value in zip(elements, fitted, strict=True)}
    if active.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        final_map = {z: foundation_refs[z] + correction_map[z] for z in elements}
    else:
        final_map = dict(correction_map)
    warnings: list[str] = []
    if rank_deficient:
        warnings.extend(
            (
                "elemental_reference_mapping_is_minimum_norm_and_nonunique",
                "do_not_transfer_absolute_energy_offsets_outside_the_fitted_composition_manifold",
            )
        )
    if active.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        warnings.append("foundation_residual_corrections_are_checkpoint_bound")
    return AtomicReferenceFitRecord(
        domain=domain,
        policy=active,
        frame_catalog_digest=frame_catalog.content_digest,
        element_order=elements,
        element_symbols=tuple(chemical_symbols[z] for z in elements),
        count_matrix=tuple(tuple(int(v) for v in row) for row in A),
        target_energies_ev=tuple(float(v) for v in target),
        fitted_targets_ev=tuple(float(v) for v in fit_target),
        foundation_prediction_energies_ev=None if predictions is None else tuple(float(v) for v in predictions),
        foundation_reference_energies_ev=tuple((z, foundation_refs[z]) for z in elements) if foundation_refs else (),
        correction_energies_ev=tuple((z, correction_map[z]) for z in elements),
        reference_energies_ev=tuple((z, final_map[z]) for z in elements),
        foundation_checkpoint_digest=checkpoint_digest,
        foundation_identity_digest=identity_digest,
        serialization_schema=(ATOMIC_REFERENCE_FIT_RECORD_SCHEMA if identity_digest is not None else ATOMIC_REFERENCE_FIT_RECORD_V2_SCHEMA),
        rank=rank,
        singular_values=tuple(float(v) for v in singular_values),
        null_space_dimension=len(elements) - rank,
        residual_rmse_ev=float(np.sqrt(np.mean(residual**2))),
        residual_mae_ev=float(np.mean(np.abs(residual))),
        maximum_absolute_residual_ev=float(np.max(np.abs(residual))),
        rank_deficient=rank_deficient,
        transfer_warnings=tuple(warnings),
    )


def fit_foundation_residual_atomic_references(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    domain: FeatureFitDomain,
    *,
    foundation_prediction_energy_by_frame: Mapping[str, float],
    foundation_reference_energies: Mapping[int, float],
    foundation_checkpoint_digest: str | None = None,
    foundation_identity_digest: str | None = None,
    policy: AtomicReferenceFitPolicy | None = None,
) -> AtomicReferenceFitRecord:
    active = policy or AtomicReferenceFitPolicy(fit_mode=AtomicReferenceFitMode.FOUNDATION_RESIDUAL)
    if active.fit_mode is not AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        raise TrainingDataInputError("The convenience foundation fit requires FOUNDATION_RESIDUAL mode.")
    return fit_atomic_reference_energies(
        frame_catalog,
        frame_data_by_run,
        data5_bundle,
        domain,
        policy=active,
        foundation_prediction_energy_by_frame=foundation_prediction_energy_by_frame,
        foundation_reference_energies=foundation_reference_energies,
        foundation_checkpoint_digest=foundation_checkpoint_digest,
        foundation_identity_digest=foundation_identity_digest,
    )
