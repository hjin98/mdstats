"""Stage-11D semantic registry for certified natural tilings.

The generic semantic identity of a tile is its canonical natural-tile face
signature.  The generic identity of a ring interface is the ring order together
with the unordered pair of adjacent tile signatures.  Conventional framework
names are applied only through an explicit, source-auditable profile.

The natural-tiling and zeolite semantic conventions follow V. A. Blatov et al.,
Acta Crystallographica A 63, 418-425 (2007), doi:10.1107/S0108767307038287,
and N. A. Anurova et al., Journal of Physical Chemistry C 114, 10160-10170
(2010), doi:10.1021/jp1030027.  The profile machinery, generic machine labels,
and the rule that expected multiplicities validate rather than determine a
classification are mdstats constructions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from numbers import Integral
import re
from typing import Any, Mapping, Sequence

from .tiling_geometry import TileSideRef, TilingGeometryCatalog

CANONICAL_FRAMEWORK_SEMANTICS_SCHEMA = "mdstats.framework-semantics.v1"
FRAMEWORK_SEMANTICS_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class FrameworkSemanticsError(ValueError):
    """Base exception for Stage-11D semantic classification."""


class FrameworkSemanticsInputError(FrameworkSemanticsError):
    """Raised when source objects, profiles, or limits violate the contract."""


class FrameworkSemanticsInvariantError(FrameworkSemanticsError):
    """Raised when an explicit framework profile fails independent validation."""


class FrameworkSemanticsResourceError(FrameworkSemanticsError):
    """Raised transactionally before declared finite-work limits are exceeded."""


class FrameworkSemanticsSerializationError(FrameworkSemanticsError):
    """Raised when deterministic source replay disagrees with serialized data."""


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


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise FrameworkSemanticsInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise FrameworkSemanticsInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise FrameworkSemanticsInputError(f"{name} must be positive.")
    return result


_MACHINE_LABEL = re.compile(r"^[a-z0-9][a-z0-9_.:^\-]*$")


def _machine_label(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not _MACHINE_LABEL.fullmatch(value):
        raise FrameworkSemanticsInputError(
            f"{name} must be a lowercase machine label containing only a-z, 0-9, _, ., :, ^, or -."
        )
    return value


def _display_label(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FrameworkSemanticsInputError(f"{name} must be a nonempty string.")
    return value.strip()


@dataclass(frozen=True, order=True, slots=True)
class TileFaceSignature:
    """Canonical multiset of natural-tile face orders."""

    counts: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        counts = tuple((int(order), int(count)) for order, count in self.counts)
        if not counts:
            raise FrameworkSemanticsInputError("A tile face signature cannot be empty.")
        if counts != tuple(sorted(counts)) or len({order for order, _ in counts}) != len(counts):
            raise FrameworkSemanticsInputError("Tile face-signature orders must be sorted and unique.")
        if any(order <= 0 or count <= 0 for order, count in counts):
            raise FrameworkSemanticsInputError("Tile face-signature orders and counts must be positive.")
        object.__setattr__(self, "counts", counts)

    @property
    def face_count(self) -> int:
        return sum(count for _order, count in self.counts)

    @property
    def symbol(self) -> str:
        return ".".join(f"{order}^{count}" for order, count in self.counts)

    @property
    def bracketed_symbol(self) -> str:
        return f"[{self.symbol}]"

    def to_dict(self) -> dict[str, Any]:
        return {"counts": [[order, count] for order, count in self.counts], "symbol": self.symbol}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TileFaceSignature":
        try:
            signature = cls(tuple((int(value[0]), int(value[1])) for value in payload["counts"]))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid tile-face signature payload.") from exc
        if payload.get("symbol") != signature.symbol:
            raise FrameworkSemanticsSerializationError("Tile-face signature symbol is inconsistent.")
        return signature


@dataclass(frozen=True, order=True, slots=True)
class RingInterfaceSignature:
    """Generic ring identity: order plus unordered adjacent tile signatures."""

    ring_size: int
    tile_signatures: tuple[TileFaceSignature, TileFaceSignature]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        signatures = tuple(self.tile_signatures)
        if len(signatures) != 2 or not all(isinstance(value, TileFaceSignature) for value in signatures):
            raise FrameworkSemanticsInputError("tile_signatures must contain two TileFaceSignature records.")
        signatures = tuple(sorted(signatures))
        object.__setattr__(self, "tile_signatures", signatures)

    @property
    def symbol(self) -> str:
        first, second = self.tile_signatures
        return f"{self.ring_size}r:{first.symbol}--{second.symbol}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ring_size": self.ring_size,
            "tile_signatures": [value.to_dict() for value in self.tile_signatures],
            "symbol": self.symbol,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingInterfaceSignature":
        try:
            result = cls(
                int(payload["ring_size"]),
                tuple(TileFaceSignature.from_dict(value) for value in payload["tile_signatures"]),  # type: ignore[arg-type]
            )
        except FrameworkSemanticsError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid ring-interface signature payload.") from exc
        if payload.get("symbol") != result.symbol:
            raise FrameworkSemanticsSerializationError("Ring-interface signature symbol is inconsistent.")
        return result


@dataclass(frozen=True, slots=True)
class TileSemanticRule:
    signature: TileFaceSignature
    semantic_label: str
    display_label: str
    role: str
    expected_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.signature, TileFaceSignature):
            raise FrameworkSemanticsInputError("signature must be TileFaceSignature.")
        object.__setattr__(self, "semantic_label", _machine_label(self.semantic_label, name="semantic_label"))
        object.__setattr__(self, "display_label", _display_label(self.display_label, name="display_label"))
        object.__setattr__(self, "role", _machine_label(self.role, name="role"))
        if self.expected_count is not None:
            object.__setattr__(self, "expected_count", _positive(self.expected_count, name="expected_count"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.to_dict(),
            "semantic_label": self.semantic_label,
            "display_label": self.display_label,
            "role": self.role,
            "expected_count": self.expected_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TileSemanticRule":
        try:
            return cls(
                TileFaceSignature.from_dict(payload["signature"]),
                str(payload["semantic_label"]),
                str(payload["display_label"]),
                str(payload["role"]),
                None if payload.get("expected_count") is None else int(payload["expected_count"]),
            )
        except FrameworkSemanticsError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid tile semantic rule payload.") from exc


@dataclass(frozen=True, slots=True)
class RingInterfaceRule:
    ring_size: int
    adjacent_tile_labels: tuple[str, str]
    family_label: str
    display_label: str
    role: str
    expected_count: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        labels = tuple(_machine_label(value, name="adjacent_tile_label") for value in self.adjacent_tile_labels)
        if len(labels) != 2:
            raise FrameworkSemanticsInputError("adjacent_tile_labels must contain two labels.")
        labels = tuple(sorted(labels))
        object.__setattr__(self, "adjacent_tile_labels", labels)
        object.__setattr__(self, "family_label", _machine_label(self.family_label, name="family_label"))
        object.__setattr__(self, "display_label", _display_label(self.display_label, name="display_label"))
        object.__setattr__(self, "role", _machine_label(self.role, name="role"))
        if self.expected_count is not None:
            object.__setattr__(self, "expected_count", _positive(self.expected_count, name="expected_count"))

    @property
    def key(self) -> tuple[int, tuple[str, str]]:
        return self.ring_size, self.adjacent_tile_labels

    def to_dict(self) -> dict[str, Any]:
        return {
            "ring_size": self.ring_size,
            "adjacent_tile_labels": list(self.adjacent_tile_labels),
            "family_label": self.family_label,
            "display_label": self.display_label,
            "role": self.role,
            "expected_count": self.expected_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingInterfaceRule":
        try:
            return cls(
                int(payload["ring_size"]),
                tuple(str(value) for value in payload["adjacent_tile_labels"]),  # type: ignore[arg-type]
                str(payload["family_label"]),
                str(payload["display_label"]),
                str(payload["role"]),
                None if payload.get("expected_count") is None else int(payload["expected_count"]),
            )
        except FrameworkSemanticsError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid ring-interface rule payload.") from exc


@dataclass(frozen=True, slots=True)
class FrameworkSemanticProfile:
    """Explicit conventional-name profile layered on generic signatures."""

    profile_id: str
    display_name: str
    tile_rules: tuple[TileSemanticRule, ...]
    interface_rules: tuple[RingInterfaceRule, ...]
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _machine_label(self.profile_id, name="profile_id"))
        object.__setattr__(self, "display_name", _display_label(self.display_name, name="display_name"))
        tile_rules = tuple(self.tile_rules)
        interface_rules = tuple(self.interface_rules)
        if not tile_rules:
            raise FrameworkSemanticsInputError("A conventional profile requires at least one tile rule.")
        if len({value.signature for value in tile_rules}) != len(tile_rules):
            raise FrameworkSemanticsInputError("Tile rules must have unique signatures.")
        if len({value.semantic_label for value in tile_rules}) != len(tile_rules):
            raise FrameworkSemanticsInputError("Tile rules must have unique semantic labels.")
        if len({value.key for value in interface_rules}) != len(interface_rules):
            raise FrameworkSemanticsInputError("Interface rules must have unique ring/adjacency keys.")
        known_labels = {value.semantic_label for value in tile_rules}
        if any(label not in known_labels for rule in interface_rules for label in rule.adjacent_tile_labels):
            raise FrameworkSemanticsInputError("Interface rules may reference only tile labels in the profile.")
        if len({value.family_label for value in interface_rules}) != len(interface_rules):
            raise FrameworkSemanticsInputError("Interface family labels must be unique.")
        references = tuple(_display_label(value, name="reference") for value in self.references)
        object.__setattr__(self, "tile_rules", tuple(sorted(tile_rules, key=lambda value: value.signature)))
        object.__setattr__(self, "interface_rules", tuple(sorted(interface_rules, key=lambda value: value.key)))
        object.__setattr__(self, "references", references)

    def tile_rule_for(self, signature: TileFaceSignature) -> TileSemanticRule | None:
        return next((value for value in self.tile_rules if value.signature == signature), None)

    def interface_rule_for(self, ring_size: int, labels: Sequence[str]) -> RingInterfaceRule | None:
        key = int(ring_size), tuple(sorted(str(value) for value in labels))
        return next((value for value in self.interface_rules if value.key == key), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "tile_rules": [value.to_dict() for value in self.tile_rules],
            "interface_rules": [value.to_dict() for value in self.interface_rules],
            "references": list(self.references),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkSemanticProfile":
        try:
            return cls(
                str(payload["profile_id"]),
                str(payload["display_name"]),
                tuple(TileSemanticRule.from_dict(value) for value in payload["tile_rules"]),
                tuple(RingInterfaceRule.from_dict(value) for value in payload["interface_rules"]),
                tuple(str(value) for value in payload.get("references", ())),
            )
        except FrameworkSemanticsError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid semantic-profile payload.") from exc


LTA_FRAMEWORK_PROFILE = FrameworkSemanticProfile(
    profile_id="lta",
    display_name="LTA natural-tile semantics",
    tile_rules=(
        TileSemanticRule(TileFaceSignature(((4, 6),)), "d4r", "D4R", "structural_unit", 6),
        TileSemanticRule(TileFaceSignature(((4, 6), (6, 8))), "beta", "beta cage", "cage", 2),
        TileSemanticRule(TileFaceSignature(((4, 12), (6, 8), (8, 6))), "alpha", "alpha cage", "cage", 2),
    ),
    interface_rules=(
        RingInterfaceRule(4, ("alpha", "d4r"), "d4r_alpha_4r", "D4R--alpha 4R", "exposed_4r", 24),
        RingInterfaceRule(4, ("beta", "d4r"), "d4r_beta_4r", "D4R--beta 4R", "internal_4r", 12),
        RingInterfaceRule(6, ("alpha", "beta"), "alpha_beta_6r", "alpha--beta 6R", "cage_interface", 16),
        RingInterfaceRule(8, ("alpha", "alpha"), "alpha_alpha_8r", "alpha--alpha 8R", "window", 6),
    ),
    references=(
        "Blatov et al. (2007), doi:10.1107/S0108767307038287",
        "Anurova et al. (2010), doi:10.1021/jp1030027",
    ),
)


@dataclass(frozen=True, slots=True)
class FrameworkSemanticsResources:
    max_tiles: int = 100_000
    max_windows: int = 1_000_000
    max_profile_rules: int = 10_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class SemanticTile:
    tile_index: int
    source_label: str
    face_signature: TileFaceSignature
    generic_label: str
    semantic_label: str | None
    display_label: str
    role: str
    side_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_index", _nonnegative(self.tile_index, name="tile_index"))
        if not isinstance(self.source_label, str):
            raise FrameworkSemanticsInputError("source_label must be a string.")
        if not isinstance(self.face_signature, TileFaceSignature):
            raise FrameworkSemanticsInputError("face_signature must be TileFaceSignature.")
        object.__setattr__(self, "generic_label", _machine_label(self.generic_label, name="generic_label"))
        if self.semantic_label is not None:
            object.__setattr__(self, "semantic_label", _machine_label(self.semantic_label, name="semantic_label"))
        object.__setattr__(self, "display_label", _display_label(self.display_label, name="display_label"))
        object.__setattr__(self, "role", _machine_label(self.role, name="role"))
        sides = tuple(int(value) for value in self.side_indices)
        if sides != tuple(sorted(set(sides))) or len(sides) != self.face_signature.face_count:
            raise FrameworkSemanticsInputError("side_indices must be sorted, unique, and match the face signature.")
        object.__setattr__(self, "side_indices", sides)

    @property
    def effective_label(self) -> str:
        return self.semantic_label or self.generic_label

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "source_label": self.source_label,
            "face_signature": self.face_signature.to_dict(),
            "generic_label": self.generic_label,
            "semantic_label": self.semantic_label,
            "display_label": self.display_label,
            "role": self.role,
            "side_indices": list(self.side_indices),
        }


@dataclass(frozen=True, slots=True)
class SemanticRingInterface:
    window_index: int
    face_index: int
    face_digest: str
    ring_size: int
    side_a: TileSideRef
    side_b: TileSideRef
    side_a_tile_label: str
    side_b_tile_label: str
    generic_signature: RingInterfaceSignature
    generic_label: str
    family_label: str | None
    display_label: str
    role: str
    relative_tile_translation: tuple[int, int, int]
    self_adjacent: bool

    def __post_init__(self) -> None:
        for name in ("window_index", "face_index"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        _sha(self.face_digest, name="face_digest")
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        if not isinstance(self.side_a, TileSideRef) or not isinstance(self.side_b, TileSideRef):
            raise FrameworkSemanticsInputError("side_a and side_b must be TileSideRef records.")
        object.__setattr__(self, "side_a_tile_label", _machine_label(self.side_a_tile_label, name="side_a_tile_label"))
        object.__setattr__(self, "side_b_tile_label", _machine_label(self.side_b_tile_label, name="side_b_tile_label"))
        if not isinstance(self.generic_signature, RingInterfaceSignature):
            raise FrameworkSemanticsInputError("generic_signature must be RingInterfaceSignature.")
        if self.generic_signature.ring_size != self.ring_size:
            raise FrameworkSemanticsInputError("generic_signature ring size is inconsistent.")
        object.__setattr__(self, "generic_label", _machine_label(self.generic_label, name="generic_label"))
        if self.family_label is not None:
            object.__setattr__(self, "family_label", _machine_label(self.family_label, name="family_label"))
        object.__setattr__(self, "display_label", _display_label(self.display_label, name="display_label"))
        object.__setattr__(self, "role", _machine_label(self.role, name="role"))
        shift = tuple(int(value) for value in self.relative_tile_translation)
        if len(shift) != 3:
            raise FrameworkSemanticsInputError("relative_tile_translation must contain three integers.")
        object.__setattr__(self, "relative_tile_translation", shift)
        object.__setattr__(self, "self_adjacent", bool(self.self_adjacent))

    @property
    def effective_label(self) -> str:
        return self.family_label or self.generic_label

    @property
    def unordered_tile_labels(self) -> tuple[str, str]:
        return tuple(sorted((self.side_a_tile_label, self.side_b_tile_label)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "face_digest": self.face_digest,
            "ring_size": self.ring_size,
            "side_a": self.side_a.to_dict(),
            "side_b": self.side_b.to_dict(),
            "side_a_tile_label": self.side_a_tile_label,
            "side_b_tile_label": self.side_b_tile_label,
            "generic_signature": self.generic_signature.to_dict(),
            "generic_label": self.generic_label,
            "family_label": self.family_label,
            "display_label": self.display_label,
            "role": self.role,
            "relative_tile_translation": list(self.relative_tile_translation),
            "self_adjacent": self.self_adjacent,
        }


@dataclass(frozen=True, slots=True)
class FrameworkProfileValidation:
    tile_counts: tuple[tuple[str, int], ...]
    expected_tile_counts: tuple[tuple[str, int], ...]
    interface_counts: tuple[tuple[str, int], ...]
    expected_interface_counts: tuple[tuple[str, int], ...]
    matched: bool

    def __post_init__(self) -> None:
        for name in ("tile_counts", "expected_tile_counts", "interface_counts", "expected_interface_counts"):
            values = tuple((str(label), int(count)) for label, count in getattr(self, name))
            if values != tuple(sorted(values)) or any(count < 0 for _label, count in values):
                raise FrameworkSemanticsInputError(f"{name} must be sorted and nonnegative.")
            object.__setattr__(self, name, values)
        observed_tiles = dict(self.tile_counts)
        observed_interfaces = dict(self.interface_counts)
        expected = (
            all(observed_tiles.get(label, 0) == count for label, count in self.expected_tile_counts)
            and all(observed_interfaces.get(label, 0) == count for label, count in self.expected_interface_counts)
        )
        if bool(self.matched) is not expected:
            raise FrameworkSemanticsInputError("matched is inconsistent with observed and expected counts.")
        object.__setattr__(self, "matched", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_counts": [list(value) for value in self.tile_counts],
            "expected_tile_counts": [list(value) for value in self.expected_tile_counts],
            "interface_counts": [list(value) for value in self.interface_counts],
            "expected_interface_counts": [list(value) for value in self.expected_interface_counts],
            "matched": self.matched,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FrameworkSemanticCatalog:
    tiling_geometry_digest: str
    profile: FrameworkSemanticProfile | None
    tiles: tuple[SemanticTile, ...]
    interfaces: tuple[SemanticRingInterface, ...]
    validation: FrameworkProfileValidation | None
    canonical_schema_version: str = CANONICAL_FRAMEWORK_SEMANTICS_SCHEMA
    digest_algorithm: str = FRAMEWORK_SEMANTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _sha(self.tiling_geometry_digest, name="tiling_geometry_digest")
        if self.profile is not None and not isinstance(self.profile, FrameworkSemanticProfile):
            raise FrameworkSemanticsInputError("profile must be FrameworkSemanticProfile or None.")
        tiles = tuple(self.tiles)
        interfaces = tuple(self.interfaces)
        if tuple(value.tile_index for value in tiles) != tuple(range(len(tiles))):
            raise FrameworkSemanticsInputError("Semantic tile IDs must be dense and ordered.")
        if tuple(value.window_index for value in interfaces) != tuple(range(len(interfaces))):
            raise FrameworkSemanticsInputError("Semantic interface IDs must be dense and ordered.")
        if (self.profile is None) != (self.validation is None):
            raise FrameworkSemanticsInputError("Profile validation must be present exactly when a profile is applied.")
        if self.validation is not None and not self.validation.matched:
            raise FrameworkSemanticsInputError("Stored conventional profile validation must be matched.")
        if self.canonical_schema_version != CANONICAL_FRAMEWORK_SEMANTICS_SCHEMA:
            raise FrameworkSemanticsInputError("Unsupported framework-semantics schema.")
        if self.digest_algorithm != FRAMEWORK_SEMANTICS_DIGEST_ALGORITHM:
            raise FrameworkSemanticsInputError("Unsupported framework-semantics digest algorithm.")
        object.__setattr__(self, "tiles", tiles)
        object.__setattr__(self, "interfaces", interfaces)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FrameworkSemanticsInputError("Stored framework-semantics digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrameworkSemanticCatalog) and self.digest == other.digest

    @property
    def profile_id(self) -> str:
        return "generic" if self.profile is None else self.profile.profile_id

    def tile_for_index(self, tile_index: int) -> SemanticTile:
        index = _nonnegative(tile_index, name="tile_index")
        if index >= len(self.tiles):
            raise FrameworkSemanticsInputError("tile_index is outside this catalog.")
        return self.tiles[index]

    def interface_for_window(self, window_index: int) -> SemanticRingInterface:
        index = _nonnegative(window_index, name="window_index")
        if index >= len(self.interfaces):
            raise FrameworkSemanticsInputError("window_index is outside this catalog.")
        return self.interfaces[index]

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "tiling_geometry_digest": self.tiling_geometry_digest,
            "profile": None if self.profile is None else self.profile.to_dict(),
            "tiles": [value.to_dict() for value in self.tiles],
            "interfaces": [value.to_dict() for value in self.interfaces],
            "validation": None if self.validation is None else self.validation.to_dict(),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        geometry: TilingGeometryCatalog,
        resources: FrameworkSemanticsResources | None = None,
    ) -> "FrameworkSemanticCatalog":
        try:
            profile_payload = payload.get("profile")
            profile = None if profile_payload is None else FrameworkSemanticProfile.from_dict(profile_payload)
        except FrameworkSemanticsError:
            raise
        except (TypeError, ValueError) as exc:
            raise FrameworkSemanticsSerializationError("Invalid profile in semantic catalog payload.") from exc
        rebuilt = build_framework_semantic_catalog(geometry, profile=profile, resources=resources)
        if rebuilt.to_dict() != dict(payload):
            raise FrameworkSemanticsSerializationError(
                "Serialized framework semantics are not canonical for the supplied sources."
            )
        return rebuilt


def _tile_face_signature(geometry: TilingGeometryCatalog, tile_index: int) -> TileFaceSignature:
    tile = geometry.tiles[tile_index]
    face_by_side = {face.side_index: face for face in geometry.tile_faces}
    try:
        counts = Counter(face_by_side[index].ring_size for index in tile.side_indices)
    except KeyError as exc:
        raise FrameworkSemanticsInvariantError("A tile side is missing from the geometry catalog.") from exc
    return TileFaceSignature(tuple(sorted(counts.items())))


def _validation(
    profile: FrameworkSemanticProfile,
    tiles: Sequence[SemanticTile],
    interfaces: Sequence[SemanticRingInterface],
) -> FrameworkProfileValidation:
    tile_counts = Counter(value.semantic_label for value in tiles)
    interface_counts = Counter(value.family_label for value in interfaces)
    if None in tile_counts or None in interface_counts:
        raise FrameworkSemanticsInvariantError("A conventional profile produced an unclassified object.")
    observed_tiles = tuple(sorted((str(label), int(count)) for label, count in tile_counts.items()))
    expected_tiles = tuple(
        sorted(
            (rule.semantic_label, int(rule.expected_count))
            for rule in profile.tile_rules
            if rule.expected_count is not None
        )
    )
    observed_interfaces = tuple(sorted((str(label), int(count)) for label, count in interface_counts.items()))
    expected_interfaces = tuple(
        sorted(
            (rule.family_label, int(rule.expected_count))
            for rule in profile.interface_rules
            if rule.expected_count is not None
        )
    )
    matched = observed_tiles == expected_tiles and observed_interfaces == expected_interfaces
    return FrameworkProfileValidation(
        observed_tiles,
        expected_tiles,
        observed_interfaces,
        expected_interfaces,
        matched,
    )


def build_framework_semantic_catalog(
    geometry: TilingGeometryCatalog,
    *,
    profile: FrameworkSemanticProfile | None = None,
    resources: FrameworkSemanticsResources | None = None,
) -> FrameworkSemanticCatalog:
    """Build generic and optional conventional semantics for one tiling geometry.

    Classification is local and signature-driven.  Expected profile counts are
    evaluated only after all tiles and interfaces have been independently
    classified; they validate the result and never select or repair labels.
    """

    if not isinstance(geometry, TilingGeometryCatalog):
        raise FrameworkSemanticsInputError("geometry must be TilingGeometryCatalog.")
    if profile is not None and not isinstance(profile, FrameworkSemanticProfile):
        raise FrameworkSemanticsInputError("profile must be FrameworkSemanticProfile or None.")
    active = resources or FrameworkSemanticsResources()
    if not isinstance(active, FrameworkSemanticsResources):
        raise FrameworkSemanticsInputError("resources must be FrameworkSemanticsResources.")
    if len(geometry.tiles) > active.max_tiles:
        raise FrameworkSemanticsResourceError("Tile count exceeds max_tiles.")
    if len(geometry.windows) > active.max_windows:
        raise FrameworkSemanticsResourceError("Window count exceeds max_windows.")
    if profile is not None and len(profile.tile_rules) + len(profile.interface_rules) > active.max_profile_rules:
        raise FrameworkSemanticsResourceError("Profile rule count exceeds max_profile_rules.")

    semantic_tiles: list[SemanticTile] = []
    for tile in geometry.tiles:
        signature = _tile_face_signature(geometry, tile.tile_index)
        generic_label = f"tile:{signature.symbol}"
        if profile is None:
            semantic_label = None
            display_label = signature.bracketed_symbol
            role = "generic_region"
        else:
            rule = profile.tile_rule_for(signature)
            if rule is None:
                raise FrameworkSemanticsInvariantError(
                    f"Profile {profile.profile_id!r} has no tile rule for {signature.bracketed_symbol}."
                )
            semantic_label = rule.semantic_label
            display_label = rule.display_label
            role = rule.role
        semantic_tiles.append(
            SemanticTile(
                tile.tile_index,
                tile.label,
                signature,
                generic_label,
                semantic_label,
                display_label,
                role,
                tile.side_indices,
            )
        )

    tile_by_index = {value.tile_index: value for value in semantic_tiles}
    interfaces: list[SemanticRingInterface] = []
    for window in geometry.windows:
        first = tile_by_index[window.side_a.tile_index]
        second = tile_by_index[window.side_b.tile_index]
        generic_signature = RingInterfaceSignature(
            window.ring_size,
            (first.face_signature, second.face_signature),
        )
        generic_label = f"interface:{generic_signature.symbol}"
        first_label = first.effective_label
        second_label = second.effective_label
        if profile is None:
            family_label = None
            display_label = generic_signature.symbol
            role = "generic_interface"
        else:
            rule = profile.interface_rule_for(window.ring_size, (first_label, second_label))
            if rule is None:
                raise FrameworkSemanticsInvariantError(
                    f"Profile {profile.profile_id!r} has no interface rule for ring {window.ring_size} "
                    f"between {first_label!r} and {second_label!r}."
                )
            family_label = rule.family_label
            display_label = rule.display_label
            role = rule.role
        interfaces.append(
            SemanticRingInterface(
                window.window_index,
                window.face_index,
                window.face_digest,
                window.ring_size,
                window.side_a,
                window.side_b,
                first_label,
                second_label,
                generic_signature,
                generic_label,
                family_label,
                display_label,
                role,
                window.relative_tile_translation,
                window.self_adjacent,
            )
        )

    validation = None
    if profile is not None:
        validation = _validation(profile, semantic_tiles, interfaces)
        if not validation.matched:
            raise FrameworkSemanticsInvariantError(
                f"Profile {profile.profile_id!r} classifications failed multiplicity validation: "
                f"tiles {validation.tile_counts} != {validation.expected_tile_counts}; "
                f"interfaces {validation.interface_counts} != {validation.expected_interface_counts}."
            )

    return FrameworkSemanticCatalog(
        geometry.digest,
        profile,
        tuple(semantic_tiles),
        tuple(interfaces),
        validation,
    )


__all__ = [
    "CANONICAL_FRAMEWORK_SEMANTICS_SCHEMA",
    "FRAMEWORK_SEMANTICS_DIGEST_ALGORITHM",
    "FrameworkProfileValidation",
    "FrameworkSemanticCatalog",
    "FrameworkSemanticProfile",
    "FrameworkSemanticsError",
    "FrameworkSemanticsInputError",
    "FrameworkSemanticsInvariantError",
    "FrameworkSemanticsResourceError",
    "FrameworkSemanticsResources",
    "FrameworkSemanticsSerializationError",
    "LTA_FRAMEWORK_PROFILE",
    "RingInterfaceRule",
    "RingInterfaceSignature",
    "SemanticRingInterface",
    "SemanticTile",
    "TileFaceSignature",
    "TileSemanticRule",
    "build_framework_semantic_catalog",
]
