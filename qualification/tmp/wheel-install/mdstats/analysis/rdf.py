"""Pair radial-distribution and coordination analysis for molecular dynamics.

This module implements a transparent histogram estimator for a partial RDF,
framewise normalization for variable-cell trajectories, a direct cumulative
coordination estimator, optional Gaussian smoothing, and robust first-shell
feature detection.

The primary input is :class:`mdstats.collection.AtomisticFrameCollection`.

Core conventions
----------------
* Coordinates and cell vectors are in angstrom.
* RDF bins are spherical shells with exact shell volumes.
* For disjoint groups, every A--B pair is counted once.
* For an identical group, unordered pairs are counted once and self-pairs are
  excluded.
* Shared CSR neighbor geometry handles general-cell minimum-image vectors.
* Gaussian smoothing is never used to compute the authoritative coordination
  curve; it is only used for plotting and feature detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from ase.data import chemical_symbols
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks, peak_prominences, peak_widths

from ..collection import AtomisticFrameCollection
from ._neighbors import PairCounting, compute_safe_cutoff
from .neighbor_search import NeighborSearchOptions, _NeighborSearchExecutor
from .selection import SpeciesSelection, resolve_atom_selection


FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]


class RDFError(RuntimeError):
    """Base class for RDF-analysis errors."""


class InvalidSelectionError(RDFError):
    """Raised when atom selections are empty, inconsistent, or overlapping."""


class InvalidRDFRangeError(RDFError):
    """Raised when the requested radial range is invalid for the cell."""


class FeatureDetectionError(RDFError):
    """Raised when an RDF peak or minimum cannot be identified reliably."""


class AmbiguousFirstMinimumError(FeatureDetectionError):
    """Raised when the first-shell minimum is absent or smoothing-sensitive."""


@dataclass(slots=True)
class RDFFeature:
    """Auditable description of a detected RDF feature.

    Parameters are stored in physical units whenever applicable. ``width`` is
    in angstrom and ``stability_std`` is the standard deviation of the detected
    radius under nearby smoothing widths.
    """

    kind: str
    radius: float
    index: int
    value: float
    prominence: float | None
    width: float | None
    confidence: str
    smoothing_sigma: float
    stability_std: float | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RDFResult:
    """Numerical result of a pair-RDF and coordination calculation."""

    species_a: str
    species_b: str

    r: FloatArray
    g_r: FloatArray
    counts: IntArray
    bin_edges: FloatArray
    shell_volumes: FloatArray

    cn_r: FloatArray
    coordination_number: FloatArray

    atom_indices_a: IntArray
    atom_indices_b: IntArray
    frame_indices: IntArray

    n_frames: int
    n_bins: int
    r_max: float
    average_volume: float

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize array dtypes and verify internal shape consistency."""
        self.r = np.asarray(self.r, dtype=float).copy()
        self.g_r = np.asarray(self.g_r, dtype=float).copy()
        self.counts = np.asarray(self.counts, dtype=np.int64).copy()
        self.bin_edges = np.asarray(self.bin_edges, dtype=float).copy()
        self.shell_volumes = np.asarray(self.shell_volumes, dtype=float).copy()
        self.cn_r = np.asarray(self.cn_r, dtype=float).copy()
        self.coordination_number = np.asarray(
            self.coordination_number, dtype=float
        ).copy()
        self.atom_indices_a = np.asarray(self.atom_indices_a, dtype=np.int64).copy()
        self.atom_indices_b = np.asarray(self.atom_indices_b, dtype=np.int64).copy()
        self.frame_indices = np.asarray(self.frame_indices, dtype=np.int64).copy()

        expected = (self.n_bins,)
        for name in (
            "r",
            "g_r",
            "counts",
            "shell_volumes",
            "cn_r",
            "coordination_number",
        ):
            value = getattr(self, name)
            if value.shape != expected:
                raise ValueError(
                    f"{name} must have shape {expected}; received {value.shape}."
                )

        if self.bin_edges.shape != (self.n_bins + 1,):
            raise ValueError(
                "bin_edges must have shape (n_bins + 1,); "
                f"received {self.bin_edges.shape}."
            )
        if self.frame_indices.shape != (self.n_frames,):
            raise ValueError(
                "frame_indices length must equal n_frames; "
                f"received {self.frame_indices.size} and {self.n_frames}."
            )
        if not np.all(np.diff(self.bin_edges) > 0.0):
            raise ValueError("bin_edges must be strictly increasing.")
        if not np.all(np.isfinite(self.g_r)):
            raise ValueError("g_r contains non-finite values.")
        if not np.all(np.isfinite(self.coordination_number)):
            raise ValueError("coordination_number contains non-finite values.")
        if np.any(np.diff(self.coordination_number) < -1.0e-12):
            raise ValueError("coordination_number must be nondecreasing.")
        if self.r_max <= 0.0 or not np.isfinite(self.r_max):
            raise ValueError("r_max must be a positive finite number.")

    @property
    def bin_width(self) -> float:
        """Uniform RDF bin width in angstrom."""
        widths = np.diff(self.bin_edges)
        if not np.allclose(widths, widths[0], rtol=1.0e-12, atol=1.0e-14):
            raise RDFError("RDFResult smoothing requires a uniform radial grid.")
        return float(widths[0])

    def smoothed(self, *, sigma: float, mode: str = "nearest") -> FloatArray:
        """Return a Gaussian-smoothed copy of ``g_r``.

        Parameters
        ----------
        sigma
            Gaussian standard deviation in angstrom.
        mode
            Boundary mode accepted by ``scipy.ndimage.gaussian_filter1d``.

        Notes
        -----
        The returned curve is for visualization and feature detection. It must
        not replace the raw cumulative-pair estimator of coordination.
        """
        if not np.isfinite(sigma) or sigma <= 0.0:
            raise ValueError("sigma must be a positive finite number in angstrom.")
        sigma_bins = sigma / self.bin_width
        return np.asarray(
            gaussian_filter1d(self.g_r, sigma=sigma_bins, mode=mode),
            dtype=float,
        )

    def first_peak(
        self,
        *,
        smoothing_sigma: float = 0.05,
        search_start: float = 0.5,
        search_max: float | None = None,
        prominence: float | None = None,
        minimum_width: float = 0.03,
    ) -> RDFFeature:
        """Locate the first significant structural maximum of the RDF."""
        smooth = self.smoothed(sigma=smoothing_sigma)
        search_indices = _feature_search_indices(
            self.r, search_start=search_start, search_max=search_max
        )
        local = smooth[search_indices]
        effective_prominence = _adaptive_prominence(local, prominence)
        width_bins = _physical_width_to_bins(minimum_width, self.bin_width)

        peaks, properties = find_peaks(
            local,
            prominence=effective_prominence,
            width=width_bins,
        )
        if peaks.size == 0:
            raise FeatureDetectionError(
                "No significant RDF peak was found in the requested radial range. "
                f"Try a longer collection, a different smoothing width, or a lower "
                f"prominence threshold (current effective prominence: "
                f"{effective_prominence:.4g})."
            )

        local_index = int(peaks[0])
        index = int(search_indices[local_index])
        return RDFFeature(
            kind="peak",
            radius=float(self.r[index]),
            index=index,
            value=float(smooth[index]),
            prominence=float(properties["prominences"][0]),
            width=float(properties["widths"][0] * self.bin_width),
            confidence="high",
            smoothing_sigma=float(smoothing_sigma),
            stability_std=None,
            metadata={
                "effective_prominence": float(effective_prominence),
                "minimum_width": float(minimum_width),
                "search_start": float(search_start),
                "search_max": (
                    float(self.r_max) if search_max is None else float(search_max)
                ),
            },
        )

    def first_minimum(
        self,
        *,
        smoothing_sigma: float = 0.05,
        search_start: float = 0.5,
        search_max: float | None = None,
        peak_prominence: float | None = None,
        minimum_prominence: float | None = None,
        minimum_width: float = 0.03,
        minimum_peak_separation: float = 0.10,
        smoothing_stability_check: bool = True,
        stability_fraction: float = 0.20,
        stability_tolerance: float = 0.10,
    ) -> RDFFeature:
        """Locate a robust first-shell minimum after the first RDF peak.

        The primary rule chooses the deepest significant minimum between the
        first two significant peaks. If a second peak is unavailable, a
        prominent persistent minimum after the first peak is accepted with
        lower baseline confidence. Nearby smoothing widths are tested by
        default; a smoothing-sensitive cutoff raises
        :class:`AmbiguousFirstMinimumError`.
        """
        _validate_minimum_parameters(
            smoothing_sigma=smoothing_sigma,
            minimum_width=minimum_width,
            minimum_peak_separation=minimum_peak_separation,
            stability_fraction=stability_fraction,
            stability_tolerance=stability_tolerance,
        )

        central = self._first_minimum_once(
            smoothing_sigma=smoothing_sigma,
            search_start=search_start,
            search_max=search_max,
            peak_prominence=peak_prominence,
            minimum_prominence=minimum_prominence,
            minimum_width=minimum_width,
            minimum_peak_separation=minimum_peak_separation,
        )

        if not smoothing_stability_check:
            return central

        sigmas = np.array(
            [
                smoothing_sigma * (1.0 - stability_fraction),
                smoothing_sigma,
                smoothing_sigma * (1.0 + stability_fraction),
            ],
            dtype=float,
        )
        if np.any(sigmas <= 0.0):
            raise ValueError(
                "stability_fraction produces a non-positive smoothing width."
            )

        radii: list[float] = []
        failures: list[str] = []
        for sigma in sigmas:
            try:
                feature = self._first_minimum_once(
                    smoothing_sigma=float(sigma),
                    search_start=search_start,
                    search_max=search_max,
                    peak_prominence=peak_prominence,
                    minimum_prominence=minimum_prominence,
                    minimum_width=minimum_width,
                    minimum_peak_separation=minimum_peak_separation,
                )
                radii.append(feature.radius)
            except FeatureDetectionError as exc:
                failures.append(f"sigma={sigma:.6g}: {exc}")

        if failures or len(radii) != 3:
            details = "; ".join(failures)
            raise AmbiguousFirstMinimumError(
                "The first minimum was not reproducible over nearby smoothing "
                f"widths. {details}"
            )

        stability_std = float(np.std(np.asarray(radii), ddof=0))
        if stability_std <= 0.5 * stability_tolerance:
            stability_confidence = "high"
        elif stability_std <= stability_tolerance:
            stability_confidence = "medium"
        else:
            raise AmbiguousFirstMinimumError(
                "The detected first minimum is too sensitive to Gaussian "
                f"smoothing: radii={radii}, standard deviation="
                f"{stability_std:.4g} A, tolerance={stability_tolerance:.4g} A."
            )

        confidence = _lower_confidence(central.confidence, stability_confidence)
        metadata = dict(central.metadata)
        metadata.update(
            {
                "stability_sigmas": sigmas.tolist(),
                "stability_radii": [float(x) for x in radii],
                "stability_tolerance": float(stability_tolerance),
            }
        )
        return replace(
            central,
            confidence=confidence,
            stability_std=stability_std,
            metadata=metadata,
        )

    def _first_minimum_once(
        self,
        *,
        smoothing_sigma: float,
        search_start: float,
        search_max: float | None,
        peak_prominence: float | None,
        minimum_prominence: float | None,
        minimum_width: float,
        minimum_peak_separation: float,
    ) -> RDFFeature:
        """Single-smoothing-width implementation used by ``first_minimum``."""
        smooth = self.smoothed(sigma=smoothing_sigma)
        search_indices = _feature_search_indices(
            self.r, search_start=search_start, search_max=search_max
        )
        local = smooth[search_indices]
        effective_peak_prominence = _adaptive_prominence(local, peak_prominence)
        width_bins = _physical_width_to_bins(minimum_width, self.bin_width)

        local_peaks, peak_properties = find_peaks(
            local,
            prominence=effective_peak_prominence,
            width=width_bins,
        )
        if local_peaks.size == 0:
            raise FeatureDetectionError(
                "No significant first peak was found before searching for the "
                "first-shell minimum."
            )

        peak_indices = search_indices[local_peaks]
        first_peak_index = int(peak_indices[0])
        first_peak_value = float(smooth[first_peak_index])
        first_peak_radius = float(self.r[first_peak_index])

        minimum_start_radius = first_peak_radius + minimum_peak_separation
        minimum_start_index = int(
            np.searchsorted(self.r, minimum_start_radius, side="left")
        )
        search_end_index = int(search_indices[-1])

        second_peak_index: int | None = None
        for candidate_peak in peak_indices[1:]:
            if self.r[int(candidate_peak)] > minimum_start_radius:
                second_peak_index = int(candidate_peak)
                break

        effective_minimum_prominence = _adaptive_minimum_prominence(
            first_peak_value, minimum_prominence
        )
        inverted = -smooth
        minima, minimum_properties = find_peaks(
            inverted,
            prominence=effective_minimum_prominence,
            width=width_bins,
        )

        if second_peak_index is not None:
            lower = minimum_start_index
            upper = second_peak_index
            method = "global_significant_minimum_between_first_two_peaks"
            base_confidence = "high"
        else:
            lower = minimum_start_index
            upper = search_end_index
            method = "first_prominent_minimum_after_first_peak"
            base_confidence = "medium"

        if upper - lower < 2:
            raise AmbiguousFirstMinimumError(
                "The radial interval after the first peak is too narrow to locate "
                "a first-shell minimum."
            )

        eligible_positions = np.flatnonzero((minima > lower) & (minima < upper))
        if eligible_positions.size:
            eligible_minima = minima[eligible_positions]
            if second_peak_index is not None:
                # A shell boundary is the deepest accepted valley between peaks.
                selected_position = int(
                    eligible_positions[np.argmin(smooth[eligible_minima])]
                )
            else:
                # Without a second peak, use the first persistent accepted valley.
                selected_position = int(eligible_positions[0])
            minimum_index = int(minima[selected_position])
            prominence_value = float(
                minimum_properties["prominences"][selected_position]
            )
            width_value = float(
                minimum_properties["widths"][selected_position] * self.bin_width
            )
        else:
            # Diagnose the deepest raw valley, but accept it only if it passes
            # the same prominence and width requirements.
            interval = smooth[lower : upper + 1]
            relative = int(np.argmin(interval))
            minimum_index = lower + relative
            if minimum_index in (lower, upper):
                raise AmbiguousFirstMinimumError(
                    "The lowest RDF value after the first peak occurs at a search "
                    "boundary, so no interior shell minimum is established."
                )
            prominence_value = float(peak_prominences(inverted, [minimum_index])[0][0])
            width_value = float(
                peak_widths(inverted, [minimum_index], rel_height=0.5)[0][0]
                * self.bin_width
            )
            if prominence_value < effective_minimum_prominence:
                raise AmbiguousFirstMinimumError(
                    "The candidate first-shell minimum is not sufficiently "
                    f"prominent ({prominence_value:.4g} < "
                    f"{effective_minimum_prominence:.4g})."
                )
            if width_value < minimum_width:
                raise AmbiguousFirstMinimumError(
                    "The candidate first-shell minimum is too narrow and may be "
                    f"noise ({width_value:.4g} A < {minimum_width:.4g} A)."
                )

        minimum_radius = float(self.r[minimum_index])
        minimum_value = float(smooth[minimum_index])
        separation = minimum_radius - first_peak_radius
        contrast = first_peak_value - minimum_value
        required_contrast = max(0.05, 0.05 * abs(first_peak_value))

        if separation < minimum_peak_separation - 1.0e-12:
            raise AmbiguousFirstMinimumError(
                "The candidate minimum lies too close to the first peak: "
                f"separation={separation:.4g} A, required="
                f"{minimum_peak_separation:.4g} A."
            )
        if contrast <= required_contrast:
            raise AmbiguousFirstMinimumError(
                "The first peak-to-minimum contrast is too weak for a reliable "
                f"shell boundary ({contrast:.4g} <= {required_contrast:.4g})."
            )
        if minimum_index in (lower, upper):
            raise AmbiguousFirstMinimumError(
                "The candidate minimum lies on a search boundary."
            )

        second_peak_radius = (
            None if second_peak_index is None else float(self.r[second_peak_index])
        )
        return RDFFeature(
            kind="minimum",
            radius=minimum_radius,
            index=minimum_index,
            value=minimum_value,
            prominence=prominence_value,
            width=width_value,
            confidence=base_confidence,
            smoothing_sigma=float(smoothing_sigma),
            stability_std=None,
            metadata={
                "method": method,
                "first_peak_radius": first_peak_radius,
                "first_peak_value": first_peak_value,
                "first_peak_prominence": float(peak_properties["prominences"][0]),
                "second_peak_radius": second_peak_radius,
                "peak_to_minimum_contrast": contrast,
                "required_contrast": required_contrast,
                "effective_peak_prominence": float(effective_peak_prominence),
                "effective_minimum_prominence": float(effective_minimum_prominence),
                "minimum_width": float(minimum_width),
                "minimum_peak_separation": float(minimum_peak_separation),
                "search_start": float(search_start),
                "search_max": (
                    float(self.r_max) if search_max is None else float(search_max)
                ),
            },
        )

    def coordination_at(
        self,
        cutoff: float,
        *,
        interpolate: bool = True,
    ) -> float:
        """Return mean B neighbors around one A center within ``cutoff``."""
        if not np.isfinite(cutoff) or cutoff < 0.0 or cutoff > self.r_max:
            raise InvalidRDFRangeError(
                f"cutoff must lie in [0, {self.r_max:.8g}] A; received {cutoff}."
            )
        if cutoff == 0.0:
            return 0.0

        if interpolate:
            x = np.concatenate(([0.0], self.cn_r))
            y = np.concatenate(([0.0], self.coordination_number))
            return float(np.interp(cutoff, x, y))

        index = int(np.searchsorted(self.cn_r, cutoff, side="right") - 1)
        if index < 0:
            return 0.0
        return float(self.coordination_number[index])

    def first_shell_coordination(
        self,
        *,
        cutoff: float | None = None,
        return_feature: bool = False,
        **minimum_options: Any,
    ) -> float | tuple[float, RDFFeature]:
        """Return coordination within a manual or automatically detected shell."""
        if cutoff is None:
            feature = self.first_minimum(**minimum_options)
            cutoff_value = feature.radius
        else:
            cutoff_value = float(cutoff)
            value = float(np.interp(cutoff_value, self.r, self.g_r))
            feature = RDFFeature(
                kind="manual_cutoff",
                radius=cutoff_value,
                index=int(np.argmin(np.abs(self.r - cutoff_value))),
                value=value,
                prominence=None,
                width=None,
                confidence="high",
                smoothing_sigma=0.0,
                stability_std=None,
                metadata={"source": "user-supplied cutoff"},
            )

        coordination = self.coordination_at(cutoff_value)
        if return_feature:
            return coordination, feature
        return coordination

    def to_dataframe(self):
        """Return RDF and coordination arrays as a pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("RDFResult.to_dataframe() requires pandas.") from exc

        return pd.DataFrame(
            {
                "r": self.r,
                "g_r": self.g_r,
                "counts": self.counts,
                "shell_volume": self.shell_volumes,
                "cn_r": self.cn_r,
                "coordination_number": self.coordination_number,
            }
        )

    def save_npz(self, filename: str | Path) -> None:
        """Serialize numerical data and JSON-safe metadata to a compressed NPZ."""
        output = Path(filename)
        metadata_json = json.dumps(
            _to_json_safe(self.metadata),
            sort_keys=True,
            separators=(",", ":"),
        )
        np.savez_compressed(
            output,
            species_a=np.asarray(self.species_a),
            species_b=np.asarray(self.species_b),
            r=self.r,
            g_r=self.g_r,
            counts=self.counts,
            bin_edges=self.bin_edges,
            shell_volumes=self.shell_volumes,
            cn_r=self.cn_r,
            coordination_number=self.coordination_number,
            atom_indices_a=self.atom_indices_a,
            atom_indices_b=self.atom_indices_b,
            frame_indices=self.frame_indices,
            n_frames=np.asarray(self.n_frames),
            n_bins=np.asarray(self.n_bins),
            r_max=np.asarray(self.r_max),
            average_volume=np.asarray(self.average_volume),
            metadata_json=np.asarray(metadata_json),
        )


def _resolve_pair_selection(
    collection: AtomisticFrameCollection,
    *,
    species: SpeciesSelection,
    atom_indices: ArrayLike | None,
    selection_name: str,
) -> IntArray:
    """Resolve one RDF group and optionally validate explicit indices by species."""
    if species is None and atom_indices is None:
        raise InvalidSelectionError(
            f"{selection_name} requires a species selection or explicit atom indices."
        )

    try:
        if atom_indices is None:
            indices = resolve_atom_selection(
                collection.atomic_numbers,
                species=species,
                selection_name=selection_name,
            )
        else:
            indices = resolve_atom_selection(
                collection.atomic_numbers,
                atom_indices=atom_indices,
                selection_name=selection_name,
            )
            if species is not None:
                allowed = resolve_atom_selection(
                    collection.atomic_numbers,
                    species=species,
                    selection_name=f"{selection_name}_species",
                )
                mismatched = np.setdiff1d(indices, allowed, assume_unique=True)
                if mismatched.size:
                    raise InvalidSelectionError(
                        f"{selection_name} contains atoms outside its species "
                        f"selection: {mismatched[:10].tolist()}"
                        + (" ..." if mismatched.size > 10 else "")
                    )
    except InvalidSelectionError:
        raise
    except (TypeError, ValueError, IndexError) as exc:
        raise InvalidSelectionError(str(exc)) from exc

    # Pair statistics are invariant to user ordering. Canonical sorting makes
    # identical-set detection and serialized results deterministic.
    return np.sort(np.asarray(indices, dtype=np.int64))


def _selection_label(
    species: SpeciesSelection,
    atom_indices: ArrayLike | None,
    resolved_indices: IntArray,
) -> str:
    """Create a compact reproducible label for one RDF selection."""
    if species is None:
        return f"indices[{resolved_indices.size}]"

    if isinstance(species, str):
        return species.strip()
    if isinstance(species, (int, np.integer)) and not isinstance(
        species, (bool, np.bool_)
    ):
        number = int(species)
        return (
            chemical_symbols[number]
            if 0 < number < len(chemical_symbols)
            else str(number)
        )

    labels: list[str] = []
    for item in species:
        if isinstance(item, str):
            labels.append(item.strip())
        else:
            number = int(item)
            labels.append(
                chemical_symbols[number]
                if 0 < number < len(chemical_symbols)
                else str(number)
            )
    label = "+".join(dict.fromkeys(labels))
    if atom_indices is not None:
        return f"{label}[{resolved_indices.size}]"
    return label


def validate_pair_selections(indices_a: IntArray, indices_b: IntArray) -> str:
    """Classify selections as disjoint or identical; reject partial overlap."""
    a = np.asarray(indices_a, dtype=np.int64)
    b = np.asarray(indices_b, dtype=np.int64)
    if np.array_equal(a, b):
        if a.size < 2:
            raise InvalidSelectionError(
                "An identical same-species RDF requires at least two atoms."
            )
        return "identical"

    overlap = np.intersect1d(a, b, assume_unique=True)
    if overlap.size:
        raise InvalidSelectionError(
            "Partially overlapping atom groups are not supported. Overlapping "
            f"indices: {overlap[:10].tolist()}" + (" ..." if overlap.size > 10 else "")
        )
    return "disjoint"


def compute_safe_r_max(
    collection: AtomisticFrameCollection,
    frame_indices: IntArray,
    *,
    search_extent: int = 2,
) -> float:
    """Compatibility wrapper for the exact shared safe cutoff.

    ``search_extent`` is retained only for source compatibility and has no
    effect.  The shared implementation uses half the shortest nonzero
    periodic lattice translation over the selected frames.
    """
    if not isinstance(search_extent, int) or search_extent < 1:
        raise ValueError("search_extent must be an integer >= 1.")
    try:
        safe = compute_safe_cutoff(collection, frame_indices=frame_indices)
    except Exception as exc:
        raise InvalidRDFRangeError(str(exc)) from exc
    if not np.isfinite(safe):
        raise InvalidRDFRangeError(
            "The RDF module requires at least one periodic direction; a fully "
            "nonperiodic collection has no homogeneous periodic RDF normalization."
        )
    return float(safe)


def make_radial_grid(
    r_max: float,
    n_bins: int,
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Construct uniform bin edges, centers, and exact shell volumes."""
    if not np.isfinite(r_max) or r_max <= 0.0:
        raise InvalidRDFRangeError("r_max must be a positive finite number.")
    if not isinstance(n_bins, int) or isinstance(n_bins, bool) or n_bins < 2:
        raise ValueError("n_bins must be an integer >= 2.")

    edges = np.linspace(0.0, r_max, n_bins + 1, dtype=float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    shell_volumes = (4.0 * np.pi / 3.0) * (edges[1:] ** 3 - edges[:-1] ** 3)
    return edges, centers, shell_volumes


def normalize_frame_histogram(
    histogram: NDArray[np.integer],
    shell_volumes: NDArray[np.floating],
    volume: float,
    n_a: int,
    n_b: int,
    selection_mode: str,
) -> FloatArray:
    """Normalize one frame histogram into a partial RDF."""
    histogram = np.asarray(histogram, dtype=float)
    shell_volumes = np.asarray(shell_volumes, dtype=float)
    if histogram.shape != shell_volumes.shape:
        raise ValueError("histogram and shell_volumes must have equal shape.")
    if not np.isfinite(volume) or volume <= 0.0:
        raise ValueError("volume must be positive and finite.")

    if selection_mode == "disjoint":
        denominator = float(n_a * n_b) * shell_volumes
        return histogram * volume / denominator
    if selection_mode == "identical":
        denominator = float(n_a * (n_a - 1)) * shell_volumes
        return 2.0 * histogram * volume / denominator
    raise ValueError(f"Unknown selection_mode: {selection_mode!r}.")


def coordination_from_histogram(
    histogram: NDArray[np.integer],
    n_a: int,
    selection_mode: str,
) -> FloatArray:
    """Convert one frame histogram into cumulative coordination."""
    cumulative = np.cumsum(np.asarray(histogram, dtype=float))
    if selection_mode == "disjoint":
        return cumulative / float(n_a)
    if selection_mode == "identical":
        return 2.0 * cumulative / float(n_a)
    raise ValueError(f"Unknown selection_mode: {selection_mode!r}.")


def compute_pair_rdf(
    collection: AtomisticFrameCollection,
    species_a: SpeciesSelection = None,
    species_b: SpeciesSelection = None,
    *,
    r_max: float | None = None,
    n_bins: int = 300,
    frame_start: int | None = None,
    frame_stop: int | None = None,
    frame_step: int = 1,
    atom_indices_a: ArrayLike | None = None,
    atom_indices_b: ArrayLike | None = None,
    block_size: int = 256,
    neighbor_search_options: NeighborSearchOptions | None = None,
) -> RDFResult:
    """Compute a partial RDF and cumulative coordination curve.

    Parameters
    ----------
    collection
        :class:`~mdstats.collection.AtomisticFrameCollection` instance.
    species_a, species_b
        Center and neighbor species selections. Each may be a chemical symbol,
        atomic number, or sequence thereof. If explicit indices are supplied,
        the corresponding species selection is used as a validation filter;
        pass ``None`` to select solely by indices.
    r_max
        Maximum radius in angstrom. ``None`` uses the exact global unique
        minimum-image radius of the selected frames: one half of the shortest
        nonzero periodic lattice translation.
    n_bins
        Number of uniform radial bins.
    frame_start, frame_stop, frame_step
        Python-slice semantics for selecting frames. ``frame_step`` must be
        positive.
    atom_indices_a, atom_indices_b
        Optional explicit atom indices or Boolean masks. If a species selection
        is also supplied, every explicit index must belong to that selection.
        Groups must be disjoint or exactly identical.
    block_size
        Number of A centers processed per vectorized distance block.
    """
    _validate_primary_parameters(
        n_bins=n_bins, frame_step=frame_step, block_size=block_size
    )
    n_frames_total = _positive_integer_attribute(collection, "n_frames")
    n_atoms = _positive_integer_attribute(collection, "n_atoms")
    frame_indices = _resolve_frame_indices(
        n_frames_total,
        frame_start=frame_start,
        frame_stop=frame_stop,
        frame_step=frame_step,
    )

    indices_a = _resolve_pair_selection(
        collection,
        species=species_a,
        atom_indices=atom_indices_a,
        selection_name="group_a",
    )
    indices_b = _resolve_pair_selection(
        collection,
        species=species_b,
        atom_indices=atom_indices_b,
        selection_name="group_b",
    )
    selection_mode = validate_pair_selections(indices_a, indices_b)
    species_a_label = _selection_label(species_a, atom_indices_a, indices_a)
    species_b_label = _selection_label(species_b, atom_indices_b, indices_b)

    safe_r_max = compute_safe_r_max(collection, frame_indices)
    tolerance = max(1.0e-10, 1.0e-10 * safe_r_max)
    if r_max is None:
        # Keep the last edge infinitesimally inside the ambiguous half-cell plane.
        chosen_r_max = float(np.nextafter(safe_r_max, 0.0))
    else:
        chosen_r_max = float(r_max)
        if not np.isfinite(chosen_r_max) or chosen_r_max <= 0.0:
            raise InvalidRDFRangeError("r_max must be positive and finite.")
        if chosen_r_max > safe_r_max + tolerance:
            raise InvalidRDFRangeError(
                f"Requested r_max={chosen_r_max:.8g} A exceeds the exact global "
                f"unique minimum-image radius {safe_r_max:.8g} A, defined as "
                "half the shortest nonzero periodic lattice translation."
            )

    bin_edges, bin_centers, shell_volumes = make_radial_grid(chosen_r_max, n_bins)
    total_counts = np.zeros(n_bins, dtype=np.int64)
    g_sum = np.zeros(n_bins, dtype=float)
    coordination_sum = np.zeros(n_bins, dtype=float)
    volumes = np.empty(frame_indices.size, dtype=float)
    pbc_patterns: set[tuple[bool, bool, bool]] = set()
    neighbor_search = _NeighborSearchExecutor(
        collection,
        options=neighbor_search_options,
        selected_frame_count=int(frame_indices.size),
    )

    for output_frame_position, frame_index in enumerate(frame_indices):
        positions = np.asarray(
            collection.get_wrapped_positions(int(frame_index)), dtype=float
        )
        cell = np.asarray(collection.cells[int(frame_index)], dtype=float)
        pbc = np.asarray(collection.pbc, dtype=bool)
        _validate_frame_data(
            positions=positions,
            cell=cell,
            pbc=pbc,
            n_atoms=n_atoms,
            frame_index=int(frame_index),
        )
        volume = float(abs(np.linalg.det(cell)))
        volumes[output_frame_position] = volume
        pbc_patterns.add(tuple(bool(x) for x in pbc))

        pair_mode = (
            PairCounting.DIRECTED
            if selection_mode == "disjoint"
            else PairCounting.UNORDERED_IDENTICAL
        )
        neighbors = neighbor_search.build_neighbor_list(
            frame_index=int(frame_index),
            center_indices=indices_a,
            candidate_neighbor_indices=indices_b,
            cutoff=chosen_r_max,
            pair_counting=pair_mode,
            block_size=block_size,
        )
        if np.any(~np.isfinite(neighbors.distances)):
            raise RDFError(
                f"Non-finite pair distances were produced for frame {int(frame_index)}."
            )
        frame_histogram, _ = np.histogram(neighbors.distances, bins=bin_edges)
        frame_histogram = frame_histogram.astype(np.int64, copy=False)

        total_counts += frame_histogram
        g_sum += normalize_frame_histogram(
            frame_histogram,
            shell_volumes,
            volume,
            int(indices_a.size),
            int(indices_b.size),
            selection_mode,
        )
        coordination_sum += coordination_from_histogram(
            frame_histogram,
            int(indices_a.size),
            selection_mode,
        )

    n_selected_frames = int(frame_indices.size)
    g_r = g_sum / float(n_selected_frames)
    coordination_number = coordination_sum / float(n_selected_frames)
    cn_r = bin_edges[1:].copy()

    if selection_mode == "disjoint":
        possible_pairs_per_frame = int(indices_a.size * indices_b.size)
        normalization = "H*V/(N_A*N_B*shell_volume), averaged per frame"
    else:
        possible_pairs_per_frame = int(indices_a.size * (indices_a.size - 1) // 2)
        normalization = "2*H*V/(N_A*(N_A-1)*shell_volume), averaged per frame"

    diagnostic_warnings = _build_diagnostic_warnings(
        g_r=g_r,
        counts=total_counts,
        n_centers=int(indices_a.size),
        n_frames=n_selected_frames,
        chosen_r_max=chosen_r_max,
        safe_r_max=safe_r_max,
        pbc_patterns=pbc_patterns,
    )

    try:
        import ase
        import scipy

        software_versions = {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "ase": ase.__version__,
        }
    except Exception:  # pragma: no cover - import environment only
        software_versions = {"numpy": np.__version__}

    metadata: dict[str, Any] = {
        "selection_mode": selection_mode,
        "normalization": normalization,
        "coordination_estimator": "direct cumulative pair counts",
        "safe_r_max": float(safe_r_max),
        "safe_r_max_definition": "half_shortest_periodic_translation",
        "requested_r_max": None if r_max is None else float(r_max),
        "bin_width": float(bin_edges[1] - bin_edges[0]),
        "frame_slice": {
            "start": frame_start,
            "stop": frame_stop,
            "step": frame_step,
        },
        "n_atoms_total": int(n_atoms),
        "n_atoms_a": int(indices_a.size),
        "n_atoms_b": int(indices_b.size),
        "atomic_numbers_a": np.unique(collection.atomic_numbers[indices_a]).tolist(),
        "atomic_numbers_b": np.unique(collection.atomic_numbers[indices_b]).tolist(),
        "neighbor_backend": "periodic_neighbor_search",
        "neighbor_search": neighbor_search.diagnostics().to_dict(),
        "cutoff_inequality": "distance < r_max",
        "possible_pairs_per_frame": possible_pairs_per_frame,
        "possible_pair_observations": int(possible_pairs_per_frame * n_selected_frames),
        "observed_pairs_within_r_max": int(total_counts.sum()),
        "volume_min": float(volumes.min()),
        "volume_max": float(volumes.max()),
        "volume_mean": float(volumes.mean()),
        "pbc_patterns": [list(pattern) for pattern in sorted(pbc_patterns)],
        "warnings": diagnostic_warnings,
        "software_versions": software_versions,
    }

    return RDFResult(
        species_a=species_a_label,
        species_b=species_b_label,
        r=bin_centers,
        g_r=g_r,
        counts=total_counts,
        bin_edges=bin_edges,
        shell_volumes=shell_volumes,
        cn_r=cn_r,
        coordination_number=coordination_number,
        atom_indices_a=indices_a,
        atom_indices_b=indices_b,
        frame_indices=frame_indices,
        n_frames=n_selected_frames,
        n_bins=n_bins,
        r_max=chosen_r_max,
        average_volume=float(volumes.mean()),
        metadata=metadata,
    )


def _positive_integer_attribute(collection: AtomisticFrameCollection, name: str) -> int:
    try:
        value = getattr(collection, name)
    except AttributeError as exc:
        raise TypeError(f"collection must expose a {name!r} property.") from exc
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"collection.{name} must be an integer; received {value!r}.")
    value = int(value)
    if value <= 0:
        raise ValueError(f"collection.{name} must be positive; received {value}.")
    return value


def _resolve_frame_indices(
    n_frames: int,
    *,
    frame_start: int | None,
    frame_stop: int | None,
    frame_step: int,
) -> IntArray:
    start, stop, step = slice(frame_start, frame_stop, frame_step).indices(n_frames)
    indices = np.arange(start, stop, step, dtype=np.int64)
    if indices.size == 0:
        raise ValueError("The requested frame slice selects no frames.")
    return indices


def _coerce_integer_vector(array: NDArray[Any], *, name: str) -> IntArray:
    array = np.asarray(array)
    if array.ndim != 1:
        raise InvalidSelectionError(f"{name} must be a one-dimensional sequence.")
    if array.dtype.kind in "iu":
        return array.astype(np.int64, copy=False)
    if array.dtype.kind == "b":
        raise InvalidSelectionError(f"{name} cannot be boolean values.")
    try:
        numeric = array.astype(float)
    except (TypeError, ValueError) as exc:
        raise InvalidSelectionError(f"{name} must contain integer values.") from exc
    if np.any(~np.isfinite(numeric)) or not np.all(numeric == np.rint(numeric)):
        raise InvalidSelectionError(f"{name} must contain finite integer values.")
    return numeric.astype(np.int64)


def _validate_primary_parameters(
    *, n_bins: int, frame_step: int, block_size: int
) -> None:
    for name, value, minimum in (
        ("n_bins", n_bins, 2),
        ("frame_step", frame_step, 1),
        ("block_size", block_size, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}.")


def _validate_cell_and_pbc(cell: FloatArray, pbc: BoolArray, frame_index: int) -> None:
    if cell.shape != (3, 3):
        raise ValueError(
            f"Frame {frame_index}: cell must have shape (3, 3); received {cell.shape}."
        )
    if pbc.shape != (3,):
        raise ValueError(
            f"Frame {frame_index}: pbc must have shape (3,); received {pbc.shape}."
        )
    if np.any(~np.isfinite(cell)):
        raise ValueError(f"Frame {frame_index}: cell contains non-finite values.")
    determinant = float(np.linalg.det(cell))
    scale = max(1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3)
    if not np.isfinite(determinant) or abs(determinant) <= 1.0e-14 * scale:
        raise ValueError(f"Frame {frame_index}: cell matrix is singular.")


def _validate_frame_data(
    *,
    positions: FloatArray,
    cell: FloatArray,
    pbc: BoolArray,
    n_atoms: int,
    frame_index: int,
) -> None:
    if positions.shape != (n_atoms, 3):
        raise ValueError(
            f"Frame {frame_index}: positions must have shape ({n_atoms}, 3); "
            f"received {positions.shape}."
        )
    if np.any(~np.isfinite(positions)):
        raise ValueError(f"Frame {frame_index}: positions contain non-finite values.")
    _validate_cell_and_pbc(cell, pbc, frame_index)


def _feature_search_indices(
    r: FloatArray,
    *,
    search_start: float,
    search_max: float | None,
) -> IntArray:
    if not np.isfinite(search_start) or search_start < 0.0:
        raise ValueError("search_start must be finite and non-negative.")
    upper = float(r[-1]) if search_max is None else float(search_max)
    if not np.isfinite(upper) or upper <= search_start:
        raise ValueError("search_max must be finite and greater than search_start.")
    indices = np.flatnonzero((r >= search_start) & (r <= upper)).astype(np.int64)
    if indices.size < 5:
        raise FeatureDetectionError(
            "The requested RDF feature-search interval contains fewer than five "
            "grid points."
        )
    return indices


def _adaptive_prominence(values: FloatArray, explicit: float | None) -> float:
    if explicit is not None:
        if not np.isfinite(explicit) or explicit <= 0.0:
            raise ValueError("prominence must be positive and finite.")
        return float(explicit)
    dynamic_range = float(np.max(values) - np.min(values))
    peak_scale = float(max(np.max(values), 0.0))
    return max(0.05, 0.05 * dynamic_range, 0.02 * peak_scale)


def _adaptive_minimum_prominence(
    first_peak_value: float, explicit: float | None
) -> float:
    if explicit is not None:
        if not np.isfinite(explicit) or explicit <= 0.0:
            raise ValueError("minimum_prominence must be positive and finite.")
        return float(explicit)
    return max(0.02, 0.02 * abs(first_peak_value))


def _physical_width_to_bins(width: float, bin_width: float) -> float:
    if not np.isfinite(width) or width <= 0.0:
        raise ValueError("minimum_width must be positive and finite.")
    return max(float(width / bin_width), 1.0)


def _validate_minimum_parameters(
    *,
    smoothing_sigma: float,
    minimum_width: float,
    minimum_peak_separation: float,
    stability_fraction: float,
    stability_tolerance: float,
) -> None:
    for name, value in (
        ("smoothing_sigma", smoothing_sigma),
        ("minimum_width", minimum_width),
        ("minimum_peak_separation", minimum_peak_separation),
        ("stability_tolerance", stability_tolerance),
    ):
        if not np.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be positive and finite.")
    if (
        not np.isfinite(stability_fraction)
        or stability_fraction < 0.0
        or stability_fraction >= 1.0
    ):
        raise ValueError("stability_fraction must lie in [0, 1).")


def _lower_confidence(first: str, second: str) -> str:
    rank = {"low": 0, "medium": 1, "high": 2}
    if first not in rank or second not in rank:
        raise ValueError("Unknown confidence label.")
    return first if rank[first] <= rank[second] else second


def _build_diagnostic_warnings(
    *,
    g_r: FloatArray,
    counts: IntArray,
    n_centers: int,
    n_frames: int,
    chosen_r_max: float,
    safe_r_max: float,
    pbc_patterns: set[tuple[bool, bool, bool]],
) -> list[str]:
    messages: list[str] = []
    if n_centers < 5:
        messages.append(
            "Fewer than five center atoms were selected; RDF statistics may be noisy."
        )
    if n_frames < 10:
        messages.append(
            "Fewer than ten frames were selected; assess equilibration and sampling."
        )
    if int(counts.sum()) < 1000:
        messages.append(
            "Fewer than 1000 pair observations fall inside r_max; fine-bin RDF "
            "features may be poorly sampled."
        )
    if chosen_r_max >= 0.95 * safe_r_max:
        messages.append(
            "r_max is within 5% of the minimum-image limit; the outermost shell "
            "is sensitive to cell size and finite-system effects."
        )
    if any(pattern != (True, True, True) for pattern in pbc_patterns):
        messages.append(
            "At least one frame is not periodic in all three directions. The "
            "standard 3D spherical-shell normalization may not approach unity."
        )
    tail_size = max(5, int(np.ceil(0.1 * g_r.size)))
    tail = g_r[-tail_size:]
    tail_mean = float(np.mean(tail))
    tail_std = float(np.std(tail))
    if not (0.7 <= tail_mean <= 1.3) or tail_std > 0.3:
        messages.append(
            "The RDF tail is not flat near unity. This may indicate a crystalline "
            "or finite system, insufficient r_max, or limited sampling; do not "
            "interpret the warning alone as an error."
        )
    return messages


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


__all__ = [
    "RDFResult",
    "RDFFeature",
    "RDFError",
    "InvalidSelectionError",
    "InvalidRDFRangeError",
    "FeatureDetectionError",
    "AmbiguousFirstMinimumError",
    "validate_pair_selections",
    "compute_safe_r_max",
    "make_radial_grid",
    "normalize_frame_histogram",
    "coordination_from_histogram",
    "compute_pair_rdf",
]
