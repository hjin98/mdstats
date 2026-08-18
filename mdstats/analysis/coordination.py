"""Integer coordination-state distributions using shared neighbor geometry."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ._neighbors import (
    PairCounting,
    compute_safe_cutoff,
    validate_cutoff,
)
from .cutoffs import PairCutoff, PairCutoffRegistry
from .neighbor_search import NeighborSearchOptions, _NeighborSearchExecutor
from .rdf import (
    InvalidSelectionError,
    RDFResult,
    _positive_integer_attribute,
    _resolve_frame_indices,
    _resolve_pair_selection,
    _selection_label,
    _to_json_safe,
)
from .selection import SpeciesSelection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]


class CoordinationError(RuntimeError):
    """Base class for coordination-distribution errors."""


class InvalidCoordinationSelectionError(CoordinationError):
    """Raised when center and neighbor selections are invalid."""


class InvalidCoordinationCutoffError(CoordinationError):
    """Raised when the coordination cutoff is invalid for the collection."""


class IncompatibleRDFError(CoordinationError):
    """Raised when an RDF result is incompatible with the requested analysis."""


class CoordinationFrameMismatchWarning(UserWarning):
    """Warn that the RDF cutoff and coordination analysis use different frames."""


@dataclass(slots=True)
class CoordinationResult:
    """Integer coordination distribution and its authoritative raw matrix."""

    species_a: str
    species_b: str
    pair_cutoff: PairCutoff

    coordination_values: Int32Array
    counts: IntArray
    probabilities: FloatArray

    per_atom_per_frame: Int32Array
    per_frame_mean: FloatArray
    per_frame_std: FloatArray
    per_atom_mean: FloatArray
    per_atom_std: FloatArray

    atom_indices_a: IntArray
    atom_indices_b: IntArray
    frame_indices: IntArray

    mean: float
    std: float
    variance: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.pair_cutoff, PairCutoff):
            raise TypeError("pair_cutoff must be a PairCutoff.")
        self.coordination_values = np.asarray(
            self.coordination_values, dtype=np.int32
        ).copy()
        self.counts = np.asarray(self.counts, dtype=np.int64).copy()
        self.probabilities = np.asarray(self.probabilities, dtype=float).copy()
        self.per_atom_per_frame = np.asarray(
            self.per_atom_per_frame, dtype=np.int32
        ).copy()
        self.per_frame_mean = np.asarray(self.per_frame_mean, dtype=float).copy()
        self.per_frame_std = np.asarray(self.per_frame_std, dtype=float).copy()
        self.per_atom_mean = np.asarray(self.per_atom_mean, dtype=float).copy()
        self.per_atom_std = np.asarray(self.per_atom_std, dtype=float).copy()
        self.atom_indices_a = np.asarray(self.atom_indices_a, dtype=np.int64).copy()
        self.atom_indices_b = np.asarray(self.atom_indices_b, dtype=np.int64).copy()
        self.frame_indices = np.asarray(self.frame_indices, dtype=np.int64).copy()

        if self.per_atom_per_frame.ndim != 2:
            raise ValueError("per_atom_per_frame must be two-dimensional.")
        n_frames, n_centers = self.per_atom_per_frame.shape
        if n_frames <= 0 or n_centers <= 0:
            raise ValueError("per_atom_per_frame must contain frames and centers.")
        if np.any(self.per_atom_per_frame < 0):
            raise ValueError("Coordination counts cannot be negative.")
        if self.atom_indices_a.shape != (n_centers,):
            raise ValueError("atom_indices_a must match coordination columns.")
        if self.frame_indices.shape != (n_frames,):
            raise ValueError("frame_indices must match coordination rows.")
        if self.atom_indices_b.ndim != 1 or self.atom_indices_b.size == 0:
            raise ValueError("atom_indices_b must be a nonempty vector.")
        for name, value, shape in (
            ("per_frame_mean", self.per_frame_mean, (n_frames,)),
            ("per_frame_std", self.per_frame_std, (n_frames,)),
            ("per_atom_mean", self.per_atom_mean, (n_centers,)),
            ("per_atom_std", self.per_atom_std, (n_centers,)),
        ):
            if value.shape != shape:
                raise ValueError(f"{name} must have shape {shape}.")

        expected_values = np.arange(self.coordination_values.size, dtype=np.int32)
        if not np.array_equal(self.coordination_values, expected_values):
            raise ValueError("coordination_values must be [0, 1, ..., n_max].")
        if self.counts.shape != expected_values.shape:
            raise ValueError("counts must match coordination_values.")
        if self.probabilities.shape != expected_values.shape:
            raise ValueError("probabilities must match coordination_values.")
        n_observations = n_frames * n_centers
        if int(self.counts.sum()) != n_observations:
            raise ValueError("counts must sum to all atom-frame observations.")
        expected_probabilities = self.counts.astype(float) / float(n_observations)
        if not np.allclose(self.probabilities, expected_probabilities):
            raise ValueError("probabilities are inconsistent with counts.")

        expected_frame_mean = self.per_atom_per_frame.mean(axis=1)
        expected_frame_std = self.per_atom_per_frame.std(axis=1, ddof=0)
        expected_atom_mean = self.per_atom_per_frame.mean(axis=0)
        expected_atom_std = self.per_atom_per_frame.std(axis=0, ddof=0)
        for name, actual, expected in (
            ("per_frame_mean", self.per_frame_mean, expected_frame_mean),
            ("per_frame_std", self.per_frame_std, expected_frame_std),
            ("per_atom_mean", self.per_atom_mean, expected_atom_mean),
            ("per_atom_std", self.per_atom_std, expected_atom_std),
        ):
            if not np.allclose(actual, expected):
                raise ValueError(f"{name} is inconsistent with raw coordination data.")

        flat = self.per_atom_per_frame.astype(float, copy=False).ravel()
        if not np.isclose(self.mean, float(flat.mean())):
            raise ValueError("mean is inconsistent with raw coordination data.")
        if not np.isclose(self.variance, float(flat.var(ddof=0))):
            raise ValueError("variance is inconsistent with raw coordination data.")
        if not np.isclose(self.std, float(flat.std(ddof=0))):
            raise ValueError("std is inconsistent with raw coordination data.")

    @property
    def cutoff(self) -> float:
        """Numeric cutoff radius in angstrom."""
        return self.pair_cutoff.radius

    @property
    def cutoff_source(self) -> str:
        """Cutoff provenance category."""
        return self.pair_cutoff.source

    @property
    def cutoff_feature(self):
        """RDF minimum feature, when the cutoff is RDF-derived."""
        feature = self.pair_cutoff.source_metadata.get("feature")
        if feature is None:
            return None
        from .rdf import RDFFeature

        return RDFFeature(**dict(feature))

    @property
    def n_frames(self) -> int:
        return int(self.per_atom_per_frame.shape[0])

    @property
    def n_atoms_a(self) -> int:
        return int(self.per_atom_per_frame.shape[1])

    @property
    def n_atoms_b(self) -> int:
        return int(self.atom_indices_b.size)

    @property
    def n_observations(self) -> int:
        return int(self.per_atom_per_frame.size)

    def probability_at(self, coordination: int) -> float:
        if isinstance(coordination, (bool, np.bool_)) or not isinstance(
            coordination, (int, np.integer)
        ):
            raise TypeError("coordination must be a nonnegative integer.")
        coordination = int(coordination)
        if coordination < 0:
            raise ValueError("coordination must be nonnegative.")
        if coordination >= self.probabilities.size:
            return 0.0
        return float(self.probabilities[coordination])

    @property
    def most_probable_coordination(self) -> int:
        return int(self.coordination_values[int(np.argmax(self.probabilities))])

    def to_dataframe(self):
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "CoordinationResult.to_dataframe() requires pandas."
            ) from exc
        return pd.DataFrame(
            {
                "coordination": self.coordination_values,
                "count": self.counts,
                "probability": self.probabilities,
            }
        )

    def save_npz(self, filename: str | Path) -> None:
        metadata_json = json.dumps(
            _to_json_safe(self.metadata), sort_keys=True, separators=(",", ":")
        )
        cutoff_json = json.dumps(self.pair_cutoff.to_dict(), sort_keys=True)
        np.savez_compressed(
            Path(filename),
            species_a=np.asarray(self.species_a),
            species_b=np.asarray(self.species_b),
            pair_cutoff_json=np.asarray(cutoff_json),
            coordination_values=self.coordination_values,
            counts=self.counts,
            probabilities=self.probabilities,
            per_atom_per_frame=self.per_atom_per_frame,
            per_frame_mean=self.per_frame_mean,
            per_frame_std=self.per_frame_std,
            per_atom_mean=self.per_atom_mean,
            per_atom_std=self.per_atom_std,
            atom_indices_a=self.atom_indices_a,
            atom_indices_b=self.atom_indices_b,
            frame_indices=self.frame_indices,
            mean=np.asarray(self.mean),
            std=np.asarray(self.std),
            variance=np.asarray(self.variance),
            metadata_json=np.asarray(metadata_json),
        )

    @classmethod
    def load_npz(cls, filename: str | Path) -> "CoordinationResult":
        with np.load(Path(filename), allow_pickle=False) as archive:
            return cls(
                species_a=str(archive["species_a"].item()),
                species_b=str(archive["species_b"].item()),
                pair_cutoff=PairCutoff.from_dict(
                    json.loads(str(archive["pair_cutoff_json"].item()))
                ),
                coordination_values=archive["coordination_values"],
                counts=archive["counts"],
                probabilities=archive["probabilities"],
                per_atom_per_frame=archive["per_atom_per_frame"],
                per_frame_mean=archive["per_frame_mean"],
                per_frame_std=archive["per_frame_std"],
                per_atom_mean=archive["per_atom_mean"],
                per_atom_std=archive["per_atom_std"],
                atom_indices_a=archive["atom_indices_a"],
                atom_indices_b=archive["atom_indices_b"],
                frame_indices=archive["frame_indices"],
                mean=float(archive["mean"].item()),
                std=float(archive["std"].item()),
                variance=float(archive["variance"].item()),
                metadata=json.loads(str(archive["metadata_json"].item())),
            )


def compute_coordination_distribution(
    collection: AtomisticFrameCollection,
    species_a: SpeciesSelection = None,
    species_b: SpeciesSelection = None,
    *,
    cutoff: float | PairCutoff | None = None,
    cutoff_registry: PairCutoffRegistry | None = None,
    rdf_result: RDFResult | None = None,
    atom_indices_a: ArrayLike | None = None,
    atom_indices_b: ArrayLike | None = None,
    frame_start: int | None = None,
    frame_stop: int | None = None,
    frame_step: int = 1,
    minimum_options: Mapping[str, Any] | None = None,
    block_size: int = 256,
    neighbor_search_options: NeighborSearchOptions | None = None,
) -> CoordinationResult:
    """Compute integer coordination states using the shared CSR neighbor kernel."""
    if isinstance(frame_step, bool) or not isinstance(frame_step, (int, np.integer)):
        raise TypeError("frame_step must be an integer.")
    if int(frame_step) <= 0:
        raise ValueError("frame_step must be positive.")
    if isinstance(block_size, bool) or not isinstance(block_size, (int, np.integer)):
        raise TypeError("block_size must be an integer.")
    if int(block_size) <= 0:
        raise ValueError("block_size must be positive.")

    n_frames_total = _positive_integer_attribute(collection, "n_frames")
    frame_indices = _resolve_frame_indices(
        n_frames_total,
        frame_start=frame_start,
        frame_stop=frame_stop,
        frame_step=int(frame_step),
    )
    indices_a = _resolve_coordination_selection(
        collection,
        species=species_a,
        atom_indices=atom_indices_a,
        selection_name="group_a",
    )
    indices_b = _resolve_coordination_selection(
        collection,
        species=species_b,
        atom_indices=atom_indices_b,
        selection_name="group_b",
    )
    selection_mode = _classify_selections(indices_a, indices_b)
    species_a_label = _selection_label(species_a, atom_indices_a, indices_a)
    species_b_label = _selection_label(species_b, atom_indices_b, indices_b)
    atomic_number_a = _unique_atomic_number(collection, indices_a, "group_a")
    atomic_number_b = _unique_atomic_number(collection, indices_b, "group_b")

    pair_cutoff, rdf_metadata = _resolve_pair_cutoff(
        collection,
        atomic_number_a=atomic_number_a,
        atomic_number_b=atomic_number_b,
        indices_a=indices_a,
        indices_b=indices_b,
        frame_indices=frame_indices,
        cutoff=cutoff,
        cutoff_registry=cutoff_registry,
        rdf_result=rdf_result,
        minimum_options=minimum_options,
    )
    try:
        validate_cutoff(
            pair_cutoff,
            collection=collection,
            frame_indices=frame_indices,
        )
    except Exception as exc:
        raise InvalidCoordinationCutoffError(str(exc)) from exc

    matrix = np.empty((frame_indices.size, indices_a.size), dtype=np.int32)
    neighbor_search = _NeighborSearchExecutor(
        collection,
        options=neighbor_search_options,
        selected_frame_count=int(frame_indices.size),
    )
    for output_position, frame_index in enumerate(frame_indices):
        neighbors = neighbor_search.build_neighbor_list(
            frame_index=int(frame_index),
            center_indices=indices_a,
            candidate_neighbor_indices=indices_b,
            cutoff=pair_cutoff,
            pair_counting=PairCounting.DIRECTED,
            block_size=int(block_size),
        )
        matrix[output_position] = neighbors.coordination_counts.astype(
            np.int32, copy=False
        )

    flat = matrix.ravel()
    counts = np.bincount(flat.astype(np.int64, copy=False)).astype(np.int64)
    values = np.arange(counts.size, dtype=np.int32)
    probabilities = counts.astype(float) / float(flat.size)
    per_frame_mean = matrix.mean(axis=1, dtype=float)
    per_frame_std = matrix.std(axis=1, ddof=0, dtype=float)
    per_atom_mean = matrix.mean(axis=0, dtype=float)
    per_atom_std = matrix.std(axis=0, ddof=0, dtype=float)
    mean = float(flat.mean())
    variance = float(flat.var(ddof=0))
    std = float(np.sqrt(variance))
    safe_cutoff = compute_safe_cutoff(collection, frame_indices=frame_indices)

    metadata: dict[str, Any] = {
        "selection_mode": selection_mode,
        "distance_convention": "minimum-image distance < cutoff",
        "neighbor_backend": "periodic_neighbor_search",
        "neighbor_search": neighbor_search.diagnostics().to_dict(),
        "safe_cutoff": float(safe_cutoff),
        "safe_cutoff_definition": "half_shortest_periodic_translation",
        "frame_slice": {
            "start": frame_start,
            "stop": frame_stop,
            "step": int(frame_step),
        },
        "n_atoms_total": int(collection.n_atoms),
        "n_atoms_a": int(indices_a.size),
        "n_atoms_b": int(indices_b.size),
        "n_frames": int(frame_indices.size),
        "n_observations": int(flat.size),
        **rdf_metadata,
    }
    return CoordinationResult(
        species_a=species_a_label,
        species_b=species_b_label,
        pair_cutoff=pair_cutoff,
        coordination_values=values,
        counts=counts,
        probabilities=probabilities,
        per_atom_per_frame=matrix,
        per_frame_mean=per_frame_mean,
        per_frame_std=per_frame_std,
        per_atom_mean=per_atom_mean,
        per_atom_std=per_atom_std,
        atom_indices_a=indices_a,
        atom_indices_b=indices_b,
        frame_indices=frame_indices,
        mean=mean,
        std=std,
        variance=variance,
        metadata=metadata,
    )


def _resolve_coordination_selection(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection,
    atom_indices: ArrayLike | None,
    selection_name: str,
) -> IntArray:
    try:
        return _resolve_pair_selection(
            collection,
            species=species,
            atom_indices=atom_indices,
            selection_name=selection_name,
        )
    except (InvalidSelectionError, TypeError, ValueError, IndexError) as exc:
        raise InvalidCoordinationSelectionError(str(exc)) from exc


def _classify_selections(indices_a: IntArray, indices_b: IntArray) -> str:
    if np.array_equal(indices_a, indices_b):
        return "identical"
    overlap = np.intersect1d(indices_a, indices_b, assume_unique=True)
    if overlap.size:
        raise InvalidCoordinationSelectionError(
            "Partially overlapping atom groups are not supported."
        )
    return "disjoint"


def _unique_atomic_number(
    collection: AtomisticFrameCollection, indices: IntArray, name: str
) -> int:
    values = np.unique(collection.atomic_numbers[indices])
    if values.size != 1:
        raise InvalidCoordinationCutoffError(
            f"{name} contains multiple species. One PairCutoff describes one "
            "species pair; compute separate coordination distributions."
        )
    return int(values[0])


def _resolve_pair_cutoff(
    collection: AtomisticFrameCollection,
    *,
    atomic_number_a: int,
    atomic_number_b: int,
    indices_a: IntArray,
    indices_b: IntArray,
    frame_indices: IntArray,
    cutoff: float | PairCutoff | None,
    cutoff_registry: PairCutoffRegistry | None,
    rdf_result: RDFResult | None,
    minimum_options: Mapping[str, Any] | None,
) -> tuple[PairCutoff, dict[str, Any]]:
    active = sum(value is not None for value in (cutoff, cutoff_registry, rdf_result))
    if active != 1:
        raise InvalidCoordinationCutoffError(
            "Exactly one cutoff source is required: cutoff, cutoff_registry, or "
            "rdf_result."
        )
    if minimum_options and rdf_result is None:
        raise InvalidCoordinationCutoffError(
            "minimum_options is only valid with rdf_result."
        )

    metadata: dict[str, Any] = {}
    if rdf_result is not None:
        if not isinstance(rdf_result, RDFResult):
            raise TypeError("rdf_result must be an RDFResult.")
        metadata = _validate_rdf_compatibility(
            rdf_result,
            indices_a=indices_a,
            indices_b=indices_b,
            frame_indices=frame_indices,
            n_atoms_total=collection.n_atoms,
        )
        try:
            resolved = PairCutoff.from_rdf_minimum(
                rdf_result, minimum_options=minimum_options
            )
        except Exception as exc:
            raise InvalidCoordinationCutoffError(str(exc)) from exc
    elif cutoff_registry is not None:
        if not isinstance(cutoff_registry, PairCutoffRegistry):
            raise TypeError("cutoff_registry must be a PairCutoffRegistry.")
        try:
            resolved = cutoff_registry.require(atomic_number_a, atomic_number_b)
        except KeyError as exc:
            raise InvalidCoordinationCutoffError(str(exc)) from exc
    elif isinstance(cutoff, PairCutoff):
        resolved = cutoff
    else:
        resolved = PairCutoff.manual(
            atomic_number_a, atomic_number_b, radius=float(cutoff)
        )

    try:
        resolved.require_match(atomic_number_a, atomic_number_b)
    except ValueError as exc:
        raise InvalidCoordinationCutoffError(str(exc)) from exc
    return resolved, metadata


def _validate_rdf_compatibility(
    rdf_result: RDFResult,
    *,
    indices_a: IntArray,
    indices_b: IntArray,
    frame_indices: IntArray,
    n_atoms_total: int,
) -> dict[str, Any]:
    direct = np.array_equal(rdf_result.atom_indices_a, indices_a) and np.array_equal(
        rdf_result.atom_indices_b, indices_b
    )
    swapped = np.array_equal(rdf_result.atom_indices_a, indices_b) and np.array_equal(
        rdf_result.atom_indices_b, indices_a
    )
    if not (direct or swapped):
        raise IncompatibleRDFError(
            "rdf_result center-atom and neighbor-atom selections do not match the coordination pair."
        )
    rdf_n_atoms = rdf_result.metadata.get("n_atoms_total")
    if rdf_n_atoms is not None and int(rdf_n_atoms) != n_atoms_total:
        raise IncompatibleRDFError(
            "rdf_result was computed for a collection with a different atom count."
        )

    relation = "identical"
    if not np.array_equal(rdf_result.frame_indices, frame_indices):
        rdf_frames = set(int(x) for x in rdf_result.frame_indices)
        current_frames = set(int(x) for x in frame_indices)
        if current_frames.issubset(rdf_frames):
            relation = "coordination_subset_of_rdf"
        elif rdf_frames.issubset(current_frames):
            relation = "rdf_subset_of_coordination"
        else:
            relation = "different_frame_sets"
        warnings.warn(
            "The RDF cutoff was estimated from a different frame selection than "
            "the coordination distribution.",
            CoordinationFrameMismatchWarning,
            stacklevel=3,
        )
    return {
        "rdf_species_a": rdf_result.species_a,
        "rdf_species_b": rdf_result.species_b,
        "rdf_frame_relation": relation,
        "rdf_pair_orientation": "direct" if direct else "swapped",
        "rdf_r_max": float(rdf_result.r_max),
    }


__all__ = [
    "CoordinationError",
    "InvalidCoordinationSelectionError",
    "InvalidCoordinationCutoffError",
    "IncompatibleRDFError",
    "CoordinationFrameMismatchWarning",
    "CoordinationResult",
    "compute_coordination_distribution",
]
