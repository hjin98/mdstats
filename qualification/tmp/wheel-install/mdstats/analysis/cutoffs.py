"""Reusable pair-cutoff definitions for structural analyses.

The public objects in this module provide one auditable neighborhood definition
for RDF-derived coordination, bond-angle analysis, and future local-environment
statistics.  Pair keys are unordered and stored as canonical atomic-number
pairs.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from ase.data import chemical_symbols

from .selection import Species, _atomic_number

if TYPE_CHECKING:  # pragma: no cover
    from ..collection import AtomisticFrameCollection
    from .rdf import RDFResult

CutoffSource = Literal["manual", "rdf_first_minimum"]
PairKeyLike = tuple[Species, Species]


def canonical_pair(species_a: Species, species_b: Species) -> tuple[int, int]:
    """Return a validated unordered atomic-number pair."""
    a = _atomic_number(species_a)
    b = _atomic_number(species_b)
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True, slots=True)
class PairCutoff:
    """A fixed radial neighborhood cutoff with provenance.

    Parameters
    ----------
    atomic_numbers
        Canonical unordered atomic-number pair.
    radius
        Strict cutoff radius in angstrom. A neighbor satisfies ``r < radius``.
    source
        ``"manual"`` or ``"rdf_first_minimum"``.
    source_metadata
        JSON-oriented provenance describing how the cutoff was selected.
    """

    atomic_numbers: tuple[int, int]
    radius: float
    source: CutoffSource = "manual"
    source_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.atomic_numbers, tuple) or len(self.atomic_numbers) != 2:
            raise TypeError("atomic_numbers must be a two-item tuple.")
        canonical = canonical_pair(*self.atomic_numbers)
        radius = float(self.radius)
        if not np.isfinite(radius) or radius <= 0.0:
            raise ValueError("PairCutoff.radius must be positive and finite.")
        if self.source not in {"manual", "rdf_first_minimum"}:
            raise ValueError(
                "PairCutoff.source must be 'manual' or 'rdf_first_minimum'."
            )
        if not isinstance(self.source_metadata, Mapping):
            raise TypeError("source_metadata must be a mapping.")
        object.__setattr__(self, "atomic_numbers", canonical)
        object.__setattr__(self, "radius", radius)
        frozen_metadata = _deep_freeze(_deep_copy_json_mapping(self.source_metadata))
        object.__setattr__(self, "source_metadata", frozen_metadata)

    @classmethod
    def manual(
        cls,
        species_a: Species,
        species_b: Species,
        *,
        radius: float,
        source_metadata: Mapping[str, Any] | None = None,
    ) -> "PairCutoff":
        """Construct a manually selected pair cutoff."""
        return cls(
            atomic_numbers=canonical_pair(species_a, species_b),
            radius=radius,
            source="manual",
            source_metadata={} if source_metadata is None else source_metadata,
        )

    @classmethod
    def from_rdf_minimum(
        cls,
        rdf_result: "RDFResult",
        *,
        minimum_options: Mapping[str, Any] | None = None,
    ) -> "PairCutoff":
        """Construct a cutoff from an auditable RDF first-shell minimum."""
        options = dict(minimum_options or {})
        feature = rdf_result.first_minimum(**options)
        pair = _pair_from_rdf_result(rdf_result)
        metadata = {
            "feature": _json_safe(asdict(feature)),
            "minimum_options": _json_safe(options),
            "rdf_species_a": rdf_result.species_a,
            "rdf_species_b": rdf_result.species_b,
            "rdf_atom_indices_a": rdf_result.atom_indices_a.tolist(),
            "rdf_atom_indices_b": rdf_result.atom_indices_b.tolist(),
            "rdf_frame_indices": rdf_result.frame_indices.tolist(),
            "rdf_r_max": float(rdf_result.r_max),
            "rdf_metadata": _json_safe(rdf_result.metadata),
        }
        return cls(
            atomic_numbers=pair,
            radius=float(feature.radius),
            source="rdf_first_minimum",
            source_metadata=metadata,
        )

    @property
    def symbols(self) -> tuple[str, str]:
        """Canonical chemical-symbol pair."""
        return tuple(chemical_symbols[z] for z in self.atomic_numbers)  # type: ignore[return-value]

    def matches(self, species_a: Species, species_b: Species) -> bool:
        """Return whether this cutoff belongs to the requested unordered pair."""
        return self.atomic_numbers == canonical_pair(species_a, species_b)

    def require_match(self, species_a: Species, species_b: Species) -> None:
        """Raise when the requested pair is incompatible with this cutoff."""
        requested = canonical_pair(species_a, species_b)
        if requested != self.atomic_numbers:
            requested_symbols = tuple(chemical_symbols[z] for z in requested)
            raise ValueError(
                "PairCutoff belongs to "
                f"{self.symbols}, not requested pair {requested_symbols}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe serialization payload."""
        return {
            "atomic_numbers": list(self.atomic_numbers),
            "radius": self.radius,
            "source": self.source,
            "source_metadata": _json_safe(self.source_metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PairCutoff":
        """Restore a cutoff from :meth:`to_dict` output."""
        numbers = tuple(int(x) for x in payload["atomic_numbers"])
        if len(numbers) != 2:
            raise ValueError("Serialized PairCutoff atomic_numbers must have length 2.")
        return cls(
            atomic_numbers=(numbers[0], numbers[1]),
            radius=float(payload["radius"]),
            source=str(payload["source"]),  # type: ignore[arg-type]
            source_metadata=dict(payload.get("source_metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class PairCutoffRegistry:
    """Canonical mapping from unordered species pairs to fixed cutoffs."""

    cutoffs: Mapping[tuple[int, int], PairCutoff]

    def __post_init__(self) -> None:
        if not isinstance(self.cutoffs, Mapping):
            raise TypeError("cutoffs must be a mapping.")
        normalized: dict[tuple[int, int], PairCutoff] = {}
        for key, cutoff in self.cutoffs.items():
            if not isinstance(cutoff, PairCutoff):
                raise TypeError("Every registry value must be a PairCutoff.")
            if not isinstance(key, tuple) or len(key) != 2:
                raise TypeError("Every registry key must be a two-item species pair.")
            canonical = canonical_pair(*key)
            if cutoff.atomic_numbers != canonical:
                raise ValueError(
                    f"Registry key {canonical} is inconsistent with cutoff "
                    f"pair {cutoff.atomic_numbers}."
                )
            existing = normalized.get(canonical)
            if existing is not None and existing != cutoff:
                raise ValueError(
                    f"Conflicting cutoffs were supplied for pair {canonical}."
                )
            normalized[canonical] = cutoff
        object.__setattr__(self, "cutoffs", MappingProxyType(normalized))

    @classmethod
    def from_cutoffs(cls, cutoffs: Iterable[PairCutoff]) -> "PairCutoffRegistry":
        """Construct a registry from an iterable of cutoff objects."""
        mapping: dict[tuple[int, int], PairCutoff] = {}
        for cutoff in cutoffs:
            if not isinstance(cutoff, PairCutoff):
                raise TypeError("from_cutoffs expects PairCutoff objects.")
            existing = mapping.get(cutoff.atomic_numbers)
            if existing is not None and existing != cutoff:
                raise ValueError(
                    f"Conflicting cutoffs for pair {cutoff.atomic_numbers}."
                )
            mapping[cutoff.atomic_numbers] = cutoff
        return cls(mapping)

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[PairKeyLike, float | PairCutoff],
    ) -> "PairCutoffRegistry":
        """Construct a registry from species-pair keys and floats/cutoffs."""
        cutoffs: dict[tuple[int, int], PairCutoff] = {}
        for key, value in mapping.items():
            if not isinstance(key, tuple) or len(key) != 2:
                raise TypeError("Cutoff mapping keys must be two-item species pairs.")
            canonical = canonical_pair(*key)
            cutoff = (
                value
                if isinstance(value, PairCutoff)
                else PairCutoff.manual(key[0], key[1], radius=float(value))
            )
            if cutoff.atomic_numbers != canonical:
                raise ValueError(
                    f"Cutoff pair {cutoff.atomic_numbers} does not match key {canonical}."
                )
            existing = cutoffs.get(canonical)
            if existing is not None and existing != cutoff:
                raise ValueError(
                    f"Conflicting cutoffs were supplied for pair {canonical}."
                )
            cutoffs[canonical] = cutoff
        return cls(cutoffs)

    def contains(self, species_a: Species, species_b: Species) -> bool:
        """Return whether the registry contains the unordered pair."""
        return canonical_pair(species_a, species_b) in self.cutoffs

    def get(
        self,
        species_a: Species,
        species_b: Species,
        default: PairCutoff | None = None,
    ) -> PairCutoff | None:
        """Return the cutoff for a pair, or ``default`` when absent."""
        return self.cutoffs.get(canonical_pair(species_a, species_b), default)

    def require(self, species_a: Species, species_b: Species) -> PairCutoff:
        """Return a required cutoff or raise a descriptive ``KeyError``."""
        pair = canonical_pair(species_a, species_b)
        try:
            return self.cutoffs[pair]
        except KeyError as exc:
            symbols = tuple(chemical_symbols[z] for z in pair)
            raise KeyError(f"No pair cutoff is registered for {symbols}.") from exc

    def validate_for_collection(
        self,
        collection: "AtomisticFrameCollection",
        *,
        frame_indices: Any,
    ) -> None:
        """Validate every registered radius against selected frame geometry."""
        from ._neighbors import validate_cutoff

        for cutoff in self.cutoffs.values():
            validate_cutoff(
                cutoff,
                collection=collection,
                frame_indices=frame_indices,
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe registry payload."""
        return {
            f"{pair[0]}-{pair[1]}": cutoff.to_dict()
            for pair, cutoff in sorted(self.cutoffs.items())
        }


def coerce_cutoff_registry(
    value: PairCutoffRegistry | Mapping[PairKeyLike, float | PairCutoff],
) -> PairCutoffRegistry:
    """Normalize a public registry argument."""
    if isinstance(value, PairCutoffRegistry):
        return value
    if isinstance(value, Mapping):
        return PairCutoffRegistry.from_mapping(value)
    raise TypeError("cutoffs must be a PairCutoffRegistry or pair-cutoff mapping.")


def _pair_from_rdf_result(rdf_result: "RDFResult") -> tuple[int, int]:
    metadata = rdf_result.metadata
    values_a = metadata.get("atomic_numbers_a")
    values_b = metadata.get("atomic_numbers_b")
    if values_a is not None and values_b is not None:
        a_unique = np.unique(np.asarray(values_a, dtype=np.int32))
        b_unique = np.unique(np.asarray(values_b, dtype=np.int32))
        if a_unique.size == 1 and b_unique.size == 1:
            return canonical_pair(int(a_unique[0]), int(b_unique[0]))

    try:
        return canonical_pair(rdf_result.species_a, rdf_result.species_b)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "RDFResult does not identify one unique species in each pair group; "
            "an RDF-derived PairCutoff requires a single-species pair."
        ) from exc


def _deep_freeze(value: Any) -> Any:
    """Recursively freeze JSON-oriented provenance containers."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_copy_json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a defensive JSON-oriented copy suitable for read-only wrapping."""
    copied = _json_safe(value)
    if not isinstance(copied, dict):
        raise TypeError("Expected mapping provenance after JSON-safe conversion.")
    return copied


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
