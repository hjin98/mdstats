"""Species-resolved bond- or neighbor-angle distributions.

Neighborhoods are defined by a :class:`PairCutoffRegistry` and constructed by
the shared CSR neighbor kernel.  The second species in ``A-B-C`` is always the
central atom.  The module supports central coordination filters, including
combined-species set-union counts required for chemically mixed frameworks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal
import warnings

import numpy as np
from ase.data import chemical_symbols
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ._neighbors import CoincidentAtomsError, PairCounting
from .neighbor_search import NeighborSearchOptions, _NeighborSearchExecutor
from .cutoffs import PairCutoff, PairCutoffRegistry, PairKeyLike, coerce_cutoff_registry
from .rdf import _resolve_frame_indices
from .selection import Species, _atomic_number, resolve_atom_selection

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]
SpeciesLike = Species
AveragingMode = Literal["angle_weighted", "center_weighted", "frame_weighted"]


class BondAngleError(RuntimeError):
    """Base class for bond-angle analysis errors."""


class InvalidTripletError(BondAngleError):
    """Raised for malformed or absent triplet species."""


class MissingPairCutoffError(BondAngleError):
    """Raised when the cutoff registry lacks a required pair."""


class InvalidCoordinationConditionError(BondAngleError):
    """Raised for malformed central coordination filters."""


class NoBondAnglesError(BondAngleError):
    """Raised when no selected center produces a valid angle."""


class CoincidentNeighborError(BondAngleError):
    """Raised when a selected angle vector has zero length."""


class SparseBondAngleWarning(UserWarning):
    """Warn that few centers, angles, or frames contribute."""


@dataclass(frozen=True, slots=True)
class CoordinationCondition:
    """Inclusive coordination bounds for one or more neighbor species."""

    neighbor_species: tuple[int, ...]
    minimum: int | None = None
    maximum: int | None = None

    def __post_init__(self) -> None:
        raw = self.neighbor_species
        if isinstance(raw, (str, int, np.integer)) and not isinstance(
            raw, (bool, np.bool_)
        ):
            items = (raw,)
        else:
            try:
                items = tuple(raw)
            except TypeError as exc:
                raise InvalidCoordinationConditionError(
                    "neighbor_species must contain one or more species."
                ) from exc
        if not items:
            raise InvalidCoordinationConditionError(
                "neighbor_species must contain at least one species."
            )
        try:
            numbers = tuple(sorted({_atomic_number(item) for item in items}))
        except (TypeError, ValueError) as exc:
            raise InvalidCoordinationConditionError(str(exc)) from exc
        minimum = _optional_nonnegative_integer(self.minimum, "minimum")
        maximum = _optional_nonnegative_integer(self.maximum, "maximum")
        if minimum is None and maximum is None:
            raise InvalidCoordinationConditionError(
                "At least one coordination bound must be supplied."
            )
        if minimum is not None and maximum is not None and minimum > maximum:
            raise InvalidCoordinationConditionError("minimum cannot exceed maximum.")
        object.__setattr__(self, "neighbor_species", numbers)
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    @classmethod
    def exact(
        cls, species: SpeciesLike | Sequence[SpeciesLike], value: int
    ) -> "CoordinationCondition":
        return cls(_species_tuple(species), minimum=value, maximum=value)

    @classmethod
    def at_least(
        cls, species: SpeciesLike | Sequence[SpeciesLike], value: int
    ) -> "CoordinationCondition":
        return cls(_species_tuple(species), minimum=value)

    @classmethod
    def at_most(
        cls, species: SpeciesLike | Sequence[SpeciesLike], value: int
    ) -> "CoordinationCondition":
        return cls(_species_tuple(species), maximum=value)

    @classmethod
    def between(
        cls,
        species: SpeciesLike | Sequence[SpeciesLike],
        minimum: int,
        maximum: int,
    ) -> "CoordinationCondition":
        return cls(_species_tuple(species), minimum=minimum, maximum=maximum)

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(chemical_symbols[z] for z in self.neighbor_species)

    def accepts(self, coordination: int) -> bool:
        if self.minimum is not None and coordination < self.minimum:
            return False
        if self.maximum is not None and coordination > self.maximum:
            return False
        return True


@dataclass(slots=True)
class BondAngleDistributionResult:
    """Raw and normalized bond-angle histogram views."""

    triplet: tuple[str, str, str]
    bin_edges: FloatArray
    bin_centers: FloatArray
    counts: IntArray
    angle_weighted_probability: FloatArray
    angle_weighted_density: FloatArray
    center_weighted_density: FloatArray
    frame_weighted_density: FloatArray
    n_angles: int
    n_candidate_centers: int
    n_accepted_centers: int
    n_contributing_frames: int
    center_atom_indices: IntArray
    frame_indices: IntArray
    cutoff_registry: PairCutoffRegistry
    coordination_filters: tuple[CoordinationCondition, ...]
    averaging: AveragingMode
    per_frame_counts: NDArray[np.int64] | None = None
    per_frame_probability_density: FloatArray | None = None
    per_frame_n_angles: IntArray | None = None
    per_frame_n_accepted_centers: IntArray | None = None
    per_frame_valid: BoolArray | None = None
    raw_angles: FloatArray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.cutoff_registry, PairCutoffRegistry):
            raise TypeError("cutoff_registry must be a PairCutoffRegistry.")
        self.bin_edges = np.asarray(self.bin_edges, dtype=float).copy()
        self.bin_centers = np.asarray(self.bin_centers, dtype=float).copy()
        self.counts = np.asarray(self.counts, dtype=np.int64).copy()
        self.angle_weighted_probability = np.asarray(
            self.angle_weighted_probability, dtype=float
        ).copy()
        self.angle_weighted_density = np.asarray(
            self.angle_weighted_density, dtype=float
        ).copy()
        self.center_weighted_density = np.asarray(
            self.center_weighted_density, dtype=float
        ).copy()
        self.frame_weighted_density = np.asarray(
            self.frame_weighted_density, dtype=float
        ).copy()
        self.center_atom_indices = np.asarray(
            self.center_atom_indices, dtype=np.int64
        ).copy()
        self.frame_indices = np.asarray(self.frame_indices, dtype=np.int64).copy()
        self.coordination_filters = tuple(self.coordination_filters)
        if self.averaging not in {
            "angle_weighted",
            "center_weighted",
            "frame_weighted",
        }:
            raise ValueError("Unknown averaging mode.")
        if self.bin_edges.ndim != 1 or self.bin_edges.size < 2:
            raise ValueError("bin_edges must be a strictly increasing vector.")
        if np.any(np.diff(self.bin_edges) <= 0.0):
            raise ValueError("bin_edges must be strictly increasing.")
        n_bins = self.bin_edges.size - 1
        expected = (n_bins,)
        for name in (
            "bin_centers",
            "counts",
            "angle_weighted_probability",
            "angle_weighted_density",
            "center_weighted_density",
            "frame_weighted_density",
        ):
            if getattr(self, name).shape != expected:
                raise ValueError(f"{name} must have shape {expected}.")
        if self.n_angles <= 0 or int(self.counts.sum()) != self.n_angles:
            raise ValueError("counts must sum to positive n_angles.")
        widths = np.diff(self.bin_edges)
        if not np.isclose(self.angle_weighted_probability.sum(), 1.0):
            raise ValueError("angle_weighted_probability must sum to one.")
        if not np.isclose(np.sum(self.angle_weighted_density * widths), 1.0):
            raise ValueError("angle_weighted_density must integrate to one.")
        if not np.isclose(np.sum(self.center_weighted_density * widths), 1.0):
            raise ValueError("center_weighted_density must integrate to one.")
        if not np.isclose(np.sum(self.frame_weighted_density * widths), 1.0):
            raise ValueError("frame_weighted_density must integrate to one.")
        if self.n_accepted_centers <= 0 or self.n_contributing_frames <= 0:
            raise ValueError("At least one center and frame must contribute.")
        if self.frame_indices.ndim != 1 or self.center_atom_indices.ndim != 1:
            raise ValueError("Frame and center indices must be one-dimensional.")
        self._normalize_optional_arrays(n_bins)

    def _normalize_optional_arrays(self, n_bins: int) -> None:
        n_frames = self.frame_indices.size
        optional = (
            self.per_frame_counts,
            self.per_frame_probability_density,
            self.per_frame_n_angles,
            self.per_frame_n_accepted_centers,
            self.per_frame_valid,
        )
        if all(value is None for value in optional):
            pass
        elif any(value is None for value in optional):
            raise ValueError("All per-frame fields must be present or absent together.")
        else:
            self.per_frame_counts = np.asarray(
                self.per_frame_counts, dtype=np.int64
            ).copy()
            self.per_frame_probability_density = np.asarray(
                self.per_frame_probability_density, dtype=float
            ).copy()
            self.per_frame_n_angles = np.asarray(
                self.per_frame_n_angles, dtype=np.int64
            ).copy()
            self.per_frame_n_accepted_centers = np.asarray(
                self.per_frame_n_accepted_centers, dtype=np.int64
            ).copy()
            self.per_frame_valid = np.asarray(self.per_frame_valid, dtype=bool).copy()
            if self.per_frame_counts.shape != (n_frames, n_bins):
                raise ValueError("per_frame_counts has an invalid shape.")
            if self.per_frame_probability_density.shape != (n_frames, n_bins):
                raise ValueError("per_frame_probability_density has an invalid shape.")
            for value in (
                self.per_frame_n_angles,
                self.per_frame_n_accepted_centers,
                self.per_frame_valid,
            ):
                if value.shape != (n_frames,):
                    raise ValueError("Per-frame summary fields have invalid shape.")
        if self.raw_angles is not None:
            self.raw_angles = np.asarray(self.raw_angles, dtype=float).copy()
            if self.raw_angles.shape != (self.n_angles,):
                raise ValueError("raw_angles must have shape (n_angles,).")

    @property
    def distribution(self) -> FloatArray:
        """Probability density selected by ``averaging``."""
        if self.averaging == "angle_weighted":
            return self.angle_weighted_density
        if self.averaging == "center_weighted":
            return self.center_weighted_density
        return self.frame_weighted_density


def compute_bond_angle_distribution(
    collection: AtomisticFrameCollection,
    *,
    triplet: tuple[SpeciesLike, SpeciesLike, SpeciesLike],
    cutoffs: PairCutoffRegistry | Mapping[PairKeyLike, float | PairCutoff],
    coordination_filters: Sequence[CoordinationCondition] | None = None,
    bins: int | ArrayLike = 180,
    angle_range: tuple[float, float] = (0.0, 180.0),
    averaging: AveragingMode = "angle_weighted",
    frame_start: int | None = None,
    frame_stop: int | None = None,
    frame_step: int = 1,
    center_atom_indices: ArrayLike | None = None,
    endpoint_a_atom_indices: ArrayLike | None = None,
    endpoint_c_atom_indices: ArrayLike | None = None,
    per_frame: bool = False,
    return_angles: bool = False,
    block_size: int = 256,
    neighbor_search_options: NeighborSearchOptions | None = None,
) -> BondAngleDistributionResult:
    """Compute an ``A-B-C`` angle distribution with central coordination filters."""
    z_a, z_b, z_c = _resolve_triplet(collection, triplet)
    registry = coerce_cutoff_registry(cutoffs)
    filters = _normalize_filters(coordination_filters)
    edges = _angle_bin_edges(bins, angle_range)
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)
    if averaging not in {"angle_weighted", "center_weighted", "frame_weighted"}:
        raise ValueError(
            "averaging must be angle_weighted, center_weighted, or frame_weighted."
        )
    if isinstance(frame_step, bool) or not isinstance(frame_step, (int, np.integer)):
        raise TypeError("frame_step must be an integer.")
    if int(frame_step) <= 0:
        raise ValueError("frame_step must be positive.")
    if isinstance(block_size, bool) or not isinstance(block_size, (int, np.integer)):
        raise TypeError("block_size must be an integer.")
    if int(block_size) <= 0:
        raise ValueError("block_size must be positive.")

    frame_indices = _resolve_frame_indices(
        collection.n_frames,
        frame_start=frame_start,
        frame_stop=frame_stop,
        frame_step=int(frame_step),
    )
    center_indices = _resolve_species_indices(
        collection, z_b, center_atom_indices, "center_atom_indices"
    )
    endpoint_a = _resolve_species_indices(
        collection, z_a, endpoint_a_atom_indices, "endpoint_a_atom_indices"
    )
    endpoint_c = _resolve_species_indices(
        collection, z_c, endpoint_c_atom_indices, "endpoint_c_atom_indices"
    )
    if z_a == z_c and not np.array_equal(endpoint_a, endpoint_c):
        raise InvalidTripletError(
            "Symmetric endpoint species require identical A and C atom selections."
        )

    required_pairs = {(z_b, z_a), (z_b, z_c)}
    for condition in filters:
        required_pairs.update((z_b, z) for z in condition.neighbor_species)
    for first, second in required_pairs:
        try:
            cutoff = registry.require(first, second)
            cutoff.require_match(first, second)
        except (KeyError, ValueError) as exc:
            raise MissingPairCutoffError(str(exc)) from exc
        try:
            from ._neighbors import validate_cutoff

            validate_cutoff(cutoff, collection=collection, frame_indices=frame_indices)
        except Exception as exc:
            raise MissingPairCutoffError(str(exc)) from exc
        _warn_low_confidence_cutoff(cutoff)

    total_counts = np.zeros(edges.size - 1, dtype=np.int64)
    center_density_sum = np.zeros(edges.size - 1, dtype=float)
    frame_density_sum = np.zeros(edges.size - 1, dtype=float)
    per_frame_counts_all = np.zeros(
        (frame_indices.size, edges.size - 1), dtype=np.int64
    )
    per_frame_density_all = np.zeros_like(per_frame_counts_all, dtype=float)
    per_frame_n_angles = np.zeros(frame_indices.size, dtype=np.int64)
    per_frame_n_centers = np.zeros(frame_indices.size, dtype=np.int64)
    per_frame_valid = np.zeros(frame_indices.size, dtype=bool)
    raw_angle_chunks: list[FloatArray] = []
    n_accepted_centers = 0
    n_filter_pass_without_angles = 0
    neighbor_search = _NeighborSearchExecutor(
        collection,
        options=neighbor_search_options,
        selected_frame_count=int(frame_indices.size),
    )

    for output_frame, frame_index in enumerate(frame_indices):
        try:
            list_a = neighbor_search.build_neighbor_list(
                frame_index=int(frame_index),
                center_indices=center_indices,
                candidate_neighbor_indices=endpoint_a,
                cutoff=registry.require(z_b, z_a),
                pair_counting=PairCounting.DIRECTED,
                block_size=int(block_size),
            )
            list_c = (
                list_a
                if z_a == z_c
                else neighbor_search.build_neighbor_list(
                    frame_index=int(frame_index),
                    center_indices=center_indices,
                    candidate_neighbor_indices=endpoint_c,
                    cutoff=registry.require(z_b, z_c),
                    pair_counting=PairCounting.DIRECTED,
                    block_size=int(block_size),
                )
            )
        except CoincidentAtomsError as exc:
            raise CoincidentNeighborError(str(exc)) from exc

        filter_lists = _build_filter_neighbor_lists(
            collection,
            frame_index=int(frame_index),
            center_indices=center_indices,
            center_species=z_b,
            filters=filters,
            registry=registry,
            block_size=int(block_size),
            neighbor_search=neighbor_search,
        )
        accepted_centers = _filters_accept_mask(
            center_indices.size, filters, filter_lists
        )
        angles, angle_centers = _batched_center_angles(
            list_a,
            list_c,
            accepted_centers,
            symmetric=z_a == z_c,
        )
        if angles.size:
            in_range = (angles >= edges[0]) & (angles <= edges[-1])
            angles = angles[in_range]
            angle_centers = angle_centers[in_range]
        n_bins = edges.size - 1
        if angles.size:
            angle_bins = np.searchsorted(edges, angles, side="right") - 1
            angle_bins = np.minimum(angle_bins, n_bins - 1).astype(
                np.int64, copy=False
            )
            encoded = angle_centers * n_bins + angle_bins
            center_count_matrix = np.bincount(
                encoded,
                minlength=center_indices.size * n_bins,
            ).reshape(center_indices.size, n_bins)
        else:
            center_count_matrix = np.zeros(
                (center_indices.size, n_bins), dtype=np.int64
            )
        center_angle_counts = np.sum(center_count_matrix, axis=1, dtype=np.int64)
        contributing = center_angle_counts > 0
        frame_contributing_centers = int(np.count_nonzero(contributing))
        n_filter_pass_without_angles += int(
            np.count_nonzero(accepted_centers) - frame_contributing_centers
        )
        frame_counts = np.sum(center_count_matrix, axis=0, dtype=np.int64)
        total_counts += frame_counts
        if frame_contributing_centers:
            normalized_centers = (
                center_count_matrix[contributing].astype(np.float64)
                / center_angle_counts[contributing, None]
            )
            center_density_sum += np.sum(normalized_centers, axis=0) / widths
            n_accepted_centers += frame_contributing_centers
        if return_angles and angles.size:
            raw_angle_chunks.append(angles)

        frame_angle_count = int(frame_counts.sum())
        per_frame_counts_all[output_frame] = frame_counts
        per_frame_n_angles[output_frame] = frame_angle_count
        per_frame_n_centers[output_frame] = frame_contributing_centers
        if frame_angle_count > 0:
            density = frame_counts.astype(float) / float(frame_angle_count) / widths
            per_frame_density_all[output_frame] = density
            frame_density_sum += density
            per_frame_valid[output_frame] = True

    n_angles = int(total_counts.sum())
    n_contributing_frames = int(per_frame_valid.sum())
    if n_angles == 0 or n_accepted_centers == 0 or n_contributing_frames == 0:
        raise NoBondAnglesError(
            "No valid bond angles were found for the requested triplet and filters."
        )
    probability = total_counts.astype(float) / float(n_angles)
    angle_density = probability / widths
    center_density = center_density_sum / float(n_accepted_centers)
    frame_density = frame_density_sum / float(n_contributing_frames)
    raw_angles = (
        np.concatenate(raw_angle_chunks) if return_angles and raw_angle_chunks else None
    )

    _issue_sampling_warnings(
        n_angles=n_angles,
        n_candidate_centers=int(frame_indices.size * center_indices.size),
        n_accepted_centers=n_accepted_centers,
        n_contributing_frames=n_contributing_frames,
        n_selected_frames=int(frame_indices.size),
        n_filter_pass_without_angles=n_filter_pass_without_angles,
    )
    metadata = {
        "triplet_atomic_numbers": [z_a, z_b, z_c],
        "distance_convention": "minimum-image distance < pair cutoff",
        "neighbor_backend": "periodic_neighbor_search",
        "neighbor_search": neighbor_search.diagnostics().to_dict(),
        "frame_slice": {
            "start": frame_start,
            "stop": frame_stop,
            "step": int(frame_step),
        },
        "angle_range_degrees": [float(edges[0]), float(edges[-1])],
        "n_bins": int(edges.size - 1),
        "n_filter_pass_without_angles": int(n_filter_pass_without_angles),
        "endpoint_a_atom_indices": endpoint_a.tolist(),
        "endpoint_c_atom_indices": endpoint_c.tolist(),
    }
    return BondAngleDistributionResult(
        triplet=(chemical_symbols[z_a], chemical_symbols[z_b], chemical_symbols[z_c]),
        bin_edges=edges,
        bin_centers=centers,
        counts=total_counts,
        angle_weighted_probability=probability,
        angle_weighted_density=angle_density,
        center_weighted_density=center_density,
        frame_weighted_density=frame_density,
        n_angles=n_angles,
        n_candidate_centers=int(frame_indices.size * center_indices.size),
        n_accepted_centers=n_accepted_centers,
        n_contributing_frames=n_contributing_frames,
        center_atom_indices=center_indices,
        frame_indices=frame_indices,
        cutoff_registry=registry,
        coordination_filters=filters,
        averaging=averaging,
        per_frame_counts=per_frame_counts_all if per_frame else None,
        per_frame_probability_density=per_frame_density_all if per_frame else None,
        per_frame_n_angles=per_frame_n_angles if per_frame else None,
        per_frame_n_accepted_centers=per_frame_n_centers if per_frame else None,
        per_frame_valid=per_frame_valid if per_frame else None,
        raw_angles=raw_angles,
        metadata=metadata,
    )


def _resolve_triplet(
    collection: AtomisticFrameCollection,
    triplet: tuple[SpeciesLike, SpeciesLike, SpeciesLike],
) -> tuple[int, int, int]:
    if not isinstance(triplet, tuple) or len(triplet) != 3:
        raise InvalidTripletError("triplet must be a three-item tuple (A, B, C).")
    try:
        numbers = tuple(_atomic_number(item) for item in triplet)
    except (TypeError, ValueError) as exc:
        raise InvalidTripletError(str(exc)) from exc
    available = set(int(z) for z in np.unique(collection.atomic_numbers))
    missing = [chemical_symbols[z] for z in numbers if z not in available]
    if missing:
        raise InvalidTripletError(
            f"Triplet species are absent from the collection: {missing}."
        )
    return numbers  # type: ignore[return-value]


def _resolve_species_indices(
    collection: AtomisticFrameCollection,
    atomic_number: int,
    explicit: ArrayLike | None,
    name: str,
) -> IntArray:
    try:
        if explicit is None:
            return resolve_atom_selection(
                collection.atomic_numbers,
                species=atomic_number,
                selection_name=name,
            )
        indices = resolve_atom_selection(
            collection.atomic_numbers,
            atom_indices=explicit,
            selection_name=name,
        )
    except (TypeError, ValueError, IndexError) as exc:
        raise InvalidTripletError(str(exc)) from exc
    bad = indices[collection.atomic_numbers[indices] != atomic_number]
    if bad.size:
        raise InvalidTripletError(
            f"{name} contains atoms outside species {chemical_symbols[atomic_number]}."
        )
    return np.sort(indices)


def _normalize_filters(
    values: Sequence[CoordinationCondition] | None,
) -> tuple[CoordinationCondition, ...]:
    if values is None:
        return ()
    normalized = tuple(values)
    if any(not isinstance(value, CoordinationCondition) for value in normalized):
        raise InvalidCoordinationConditionError(
            "coordination_filters must contain CoordinationCondition objects."
        )
    return normalized


def _build_filter_neighbor_lists(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: IntArray,
    center_species: int,
    filters: tuple[CoordinationCondition, ...],
    registry: PairCutoffRegistry,
    block_size: int,
    neighbor_search: _NeighborSearchExecutor,
) -> dict[int, Any]:
    lists: dict[int, Any] = {}
    for species in sorted(
        {z for condition in filters for z in condition.neighbor_species}
    ):
        candidates = resolve_atom_selection(
            collection.atomic_numbers,
            species=species,
            selection_name="coordination_filter",
        )
        try:
            lists[species] = neighbor_search.build_neighbor_list(
                frame_index=frame_index,
                center_indices=center_indices,
                candidate_neighbor_indices=candidates,
                cutoff=registry.require(center_species, species),
                pair_counting=PairCounting.DIRECTED,
                block_size=block_size,
            )
        except CoincidentAtomsError as exc:
            raise CoincidentNeighborError(str(exc)) from exc
    return lists


def _filters_accept_mask(
    n_centers: int,
    filters: tuple[CoordinationCondition, ...],
    neighbor_lists: Mapping[int, Any],
) -> BoolArray:
    """Evaluate all coordination filters with vectorized CSR row counts."""

    accepted = np.ones(int(n_centers), dtype=bool)
    for condition in filters:
        coordination = np.zeros(int(n_centers), dtype=np.int64)
        for species in condition.neighbor_species:
            result = neighbor_lists[species]
            coordination += np.diff(result.offsets).astype(np.int64, copy=False)
        if condition.minimum is not None:
            accepted &= coordination >= condition.minimum
        if condition.maximum is not None:
            accepted &= coordination <= condition.maximum
    return accepted


def _batched_center_angles(
    list_a: Any,
    list_c: Any,
    accepted_centers: BoolArray,
    *,
    symmetric: bool,
    max_pair_rows: int = 4_000_000,
) -> tuple[FloatArray, IntArray]:
    """Generate ragged center-neighbor angle pairs in bounded array batches.

    Neighbor degrees are typically small for atomistic coordination graphs.  A
    rectangular pair template is therefore substantially cheaper than Python
    dispatch per center, while ``max_pair_rows`` bounds the temporary mask for
    unusual high-coordination inputs.
    """

    selected = np.flatnonzero(np.asarray(accepted_centers, dtype=bool)).astype(
        np.int64, copy=False
    )
    if selected.size == 0:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
    degree_a = np.diff(list_a.offsets).astype(np.int64, copy=False)[selected]
    degree_c = degree_a if symmetric else np.diff(list_c.offsets).astype(
        np.int64, copy=False
    )[selected]
    maximum_a = int(np.max(degree_a, initial=0))
    maximum_c = int(np.max(degree_c, initial=0))
    if symmetric:
        if maximum_a < 2:
            return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
        pair_a, pair_c = np.triu_indices(maximum_a, k=1)
    else:
        if maximum_a == 0 or maximum_c == 0:
            return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
        pair_a = np.repeat(np.arange(maximum_a, dtype=np.int64), maximum_c)
        pair_c = np.tile(np.arange(maximum_c, dtype=np.int64), maximum_a)
    template_size = int(pair_a.size)
    center_batch = max(1, int(max_pair_rows) // max(1, template_size))
    angle_parts: list[FloatArray] = []
    center_parts: list[IntArray] = []
    for start in range(0, selected.size, center_batch):
        stop = min(selected.size, start + center_batch)
        centers = selected[start:stop]
        valid = (
            pair_a[None, :] < degree_a[start:stop, None]
        ) & (
            pair_c[None, :] < degree_c[start:stop, None]
        )
        center_rows, template_rows = np.nonzero(valid)
        if center_rows.size == 0:
            continue
        current_centers = centers[center_rows]
        indices_a = (
            list_a.offsets[current_centers] + pair_a[template_rows]
        ).astype(np.int64, copy=False)
        indices_c = (
            (list_a.offsets if symmetric else list_c.offsets)[current_centers]
            + pair_c[template_rows]
        ).astype(np.int64, copy=False)
        angle_parts.append(
            _angles_from_vector_pairs(
                list_a.vectors[indices_a],
                (list_a.vectors if symmetric else list_c.vectors)[indices_c],
            )
        )
        center_parts.append(current_centers)
    if not angle_parts:
        return np.empty(0, dtype=float), np.empty(0, dtype=np.int64)
    return np.concatenate(angle_parts), np.concatenate(center_parts)


def _filters_accept(
    local_center: int,
    filters: tuple[CoordinationCondition, ...],
    neighbor_lists: Mapping[int, Any],
) -> bool:
    for condition in filters:
        union: set[int] = set()
        for species in condition.neighbor_species:
            result = neighbor_lists[species]
            row = result.row_slice(local_center)
            union.update(int(value) for value in result.neighbor_indices[row])
        if not condition.accepts(len(union)):
            return False
    return True


def _center_angles(
    list_a: Any, list_c: Any, local_center: int, *, symmetric: bool
) -> FloatArray:
    row_a = list_a.row_slice(local_center)
    vectors_a = list_a.vectors[row_a]
    if symmetric:
        q = vectors_a.shape[0]
        if q < 2:
            return np.empty(0, dtype=float)
        first, second = np.triu_indices(q, k=1)
        return _angles_from_vector_pairs(vectors_a[first], vectors_a[second])
    row_c = list_c.row_slice(local_center)
    vectors_c = list_c.vectors[row_c]
    if vectors_a.size == 0 or vectors_c.size == 0:
        return np.empty(0, dtype=float)
    first = np.repeat(vectors_a, vectors_c.shape[0], axis=0)
    second = np.tile(vectors_c, (vectors_a.shape[0], 1))
    return _angles_from_vector_pairs(first, second)


def _angles_from_vector_pairs(first: FloatArray, second: FloatArray) -> FloatArray:
    norm_first = np.linalg.norm(first, axis=1)
    norm_second = np.linalg.norm(second, axis=1)
    if np.any(norm_first <= 0.0) or np.any(norm_second <= 0.0):
        raise CoincidentNeighborError("A bond-angle vector has zero length.")
    cosine = np.einsum("ij,ij->i", first, second) / (norm_first * norm_second)
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


def _angle_bin_edges(
    bins: int | ArrayLike, angle_range: tuple[float, float]
) -> FloatArray:
    if not isinstance(angle_range, tuple) or len(angle_range) != 2:
        raise ValueError("angle_range must be a two-item tuple.")
    lower, upper = (float(angle_range[0]), float(angle_range[1]))
    if not np.isfinite(lower) or not np.isfinite(upper):
        raise ValueError("angle_range must be finite.")
    if lower < 0.0 or upper > 180.0 or lower >= upper:
        raise ValueError("angle_range must satisfy 0 <= lower < upper <= 180.")
    if isinstance(bins, bool):
        raise TypeError("bins must be an integer or a one-dimensional edge array.")
    if isinstance(bins, (int, np.integer)):
        if int(bins) < 1:
            raise ValueError("bins must be a positive integer.")
        return np.linspace(lower, upper, int(bins) + 1)
    edges = np.asarray(bins, dtype=float)
    if edges.ndim != 1 or edges.size < 2 or np.any(~np.isfinite(edges)):
        raise ValueError("Explicit bins must be a finite one-dimensional edge array.")
    if np.any(np.diff(edges) <= 0.0):
        raise ValueError("Explicit bin edges must be strictly increasing.")
    if edges[0] < lower - 1e-12 or edges[-1] > upper + 1e-12:
        raise ValueError("Explicit bin edges must lie inside angle_range.")
    return edges.copy()


def _optional_nonnegative_integer(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise InvalidCoordinationConditionError(f"{name} must be an integer or None.")
    value = int(value)
    if value < 0:
        raise InvalidCoordinationConditionError(f"{name} must be nonnegative.")
    return value


def _species_tuple(
    species: SpeciesLike | Sequence[SpeciesLike],
) -> tuple[SpeciesLike, ...]:
    if isinstance(species, (str, int, np.integer)) and not isinstance(
        species, (bool, np.bool_)
    ):
        return (species,)
    return tuple(species)


def _warn_low_confidence_cutoff(cutoff: Any) -> None:
    if cutoff.source != "rdf_first_minimum":
        return
    feature = cutoff.source_metadata.get("feature", {})
    if isinstance(feature, Mapping) and feature.get("confidence") == "low":
        warnings.warn(
            f"RDF-derived cutoff {cutoff.symbols} has low feature confidence.",
            SparseBondAngleWarning,
            stacklevel=3,
        )


def _issue_sampling_warnings(
    *,
    n_angles: int,
    n_candidate_centers: int,
    n_accepted_centers: int,
    n_contributing_frames: int,
    n_selected_frames: int,
    n_filter_pass_without_angles: int,
) -> None:
    messages: list[str] = []
    if n_angles < 100:
        messages.append(
            "Fewer than 100 angles contribute; the distribution may be noisy."
        )
    if n_accepted_centers < max(1, int(0.05 * n_candidate_centers)):
        messages.append("Fewer than 5% of candidate centers contribute valid angles.")
    if n_contributing_frames < n_selected_frames:
        messages.append("At least one selected frame contains no valid angle.")
    if n_filter_pass_without_angles:
        messages.append(
            "Some centers passed coordination filters but lacked enough endpoint neighbors."
        )
    for message in messages:
        warnings.warn(message, SparseBondAngleWarning, stacklevel=3)


__all__ = [
    "BondAngleError",
    "InvalidTripletError",
    "MissingPairCutoffError",
    "InvalidCoordinationConditionError",
    "NoBondAnglesError",
    "CoincidentNeighborError",
    "SparseBondAngleWarning",
    "CoordinationCondition",
    "BondAngleDistributionResult",
    "compute_bond_angle_distribution",
]
