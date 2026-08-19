"""Canonical generalized MACE foundation identities and checkpoint inspection.

MH1-ID1 introduces a shared foundation-model boundary for both MACE-MPA-0 and
MACE-MH-1.  Scientific identity is no longer inferred from filenames and a
multi-head checkpoint is never allowed to fall through MACE's permissive head
fallback logic.

Historical serialized foundation records remain readable without invalidating
parent-artifact digests: legacy records preserve their source schema when
round-tripped, while ``canonical_content_digest`` exposes the v3 scientific
identity used by new lineage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
import warnings

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)

FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA = "mdstats.foundation-checkpoint-identity.v3"
FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA = "mdstats.foundation-checkpoint-identity.v2"
FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA = "mdstats.foundation-checkpoint-identity.v1"
MACE_FOUNDATION_INSPECTION_SCHEMA = "mdstats.mace-foundation-inspection.v1"
FOUNDATION_INFERENCE_IDENTITY_SCHEMA = "mdstats.foundation-inference-identity.v1"


class MaceFoundationFamily(str, Enum):
    MPA_0 = "mace_mpa_0"
    MH_1 = "mace_mh_1"
    CUSTOM = "mace_custom"

    @classmethod
    def parse(cls, value: "MaceFoundationFamily | str") -> "MaceFoundationFamily":
        if isinstance(value, cls):
            return value
        text = str(value).strip()
        normalized = text.lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "mace_mpa_0": cls.MPA_0,
            "mace_mpa0": cls.MPA_0,
            "mpa_0": cls.MPA_0,
            "mpa0": cls.MPA_0,
            "mpa_0_medium": cls.MPA_0,
            "mace_mpa_0_medium": cls.MPA_0,
            "mace_mh_1": cls.MH_1,
            "mace_mh1": cls.MH_1,
            "mh_1": cls.MH_1,
            "mh1": cls.MH_1,
            "mace_custom": cls.CUSTOM,
            "custom": cls.CUSTOM,
            "mace": cls.CUSTOM,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise TrainingDataInputError(
                f"Unsupported MACE foundation family {value!r}; expected one of "
                "mace_mpa_0, mace_mh_1, or mace_custom."
            ) from exc


def _as_int_tuple(value: Any) -> tuple[int, ...]:
    if value is None:
        return ()
    if hasattr(value, "detach"):
        value = value.detach().cpu().tolist()
    elif hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (int, float)):
        value = [value]
    result = tuple(int(v) for v in value)
    if any(v <= 0 for v in result) or len(set(result)) != len(result):
        raise TrainingDataInputError("Foundation atomic-number table is invalid.")
    return result


def _scalar_float(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def _scalar_int(value: Any) -> int | None:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "item"):
        value = value.item()
    return int(value)


def _string_attr(obj: Any, name: str) -> str | None:
    if not hasattr(obj, name):
        return None
    value = getattr(obj, name)
    if value is None:
        return None
    return str(value)


def _linear_signature(obj: Any, name: str) -> tuple[str | None, str | None] | None:
    if not hasattr(obj, name):
        return None
    linear = getattr(obj, name)
    return (
        None if getattr(linear, "irreps_in", None) is None else str(linear.irreps_in),
        None if getattr(linear, "irreps_out", None) is None else str(linear.irreps_out),
    )


def _module_signature(module: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "class": type(module).__name__,
        "module": type(module).__module__,
    }
    for name in (
        "node_feats_irreps",
        "node_attrs_irreps",
        "edge_attrs_irreps",
        "edge_feats_irreps",
        "hidden_irreps",
        "target_irreps",
        "irreps_out",
    ):
        value = _string_attr(module, name)
        if value is not None:
            payload[name] = value
    for name in ("linear", "linear_up", "linear_down"):
        value = _linear_signature(module, name)
        if value is not None:
            payload[name] = list(value)
    return payload


def _model_dtype(model: Any) -> str | None:
    try:
        for parameter in model.parameters():
            if getattr(parameter, "is_floating_point", lambda: False)():
                text = str(parameter.dtype)
                return text.removeprefix("torch.")
    except Exception:
        pass
    return None


def _atomic_energies_shape(model: Any) -> tuple[int, ...]:
    block = getattr(model, "atomic_energies_fn", None)
    energies = None if block is None else getattr(block, "atomic_energies", None)
    if energies is None:
        return ()
    return tuple(int(v) for v in energies.shape)


def _state_shape_digest(model: Any) -> str:
    shapes: list[tuple[str, tuple[int, ...], str]] = []
    for key, tensor in model.state_dict().items():
        shapes.append((str(key), tuple(int(v) for v in tensor.shape), str(tensor.dtype)))
    return digest(shapes)


@dataclass(frozen=True, slots=True)
class MaceFoundationInspection:
    reference: str
    sha256: str
    model_class: str
    model_module: str
    available_heads: tuple[str, ...]
    atomic_numbers: tuple[int, ...]
    r_max_angstrom: float | None
    num_interactions: int | None
    model_dtype: str | None
    atomic_energies_shape: tuple[int, ...]
    interaction_signatures: tuple[Mapping[str, Any], ...]
    product_signatures: tuple[Mapping[str, Any], ...]
    readout_signatures: tuple[Mapping[str, Any], ...]
    edge_irreps: str | None = None
    use_agnostic_product: bool | None = None
    use_last_readout_only: bool | None = None
    state_shape_digest: str = ""

    def __post_init__(self) -> None:
        if not self.reference.strip() or not self.model_class.strip() or not self.model_module.strip():
            raise TrainingDataInputError("Foundation inspection identifiers must be non-empty.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        heads = tuple(str(v).strip() for v in self.available_heads)
        if not heads or any(not v for v in heads) or len(set(heads)) != len(heads):
            raise TrainingDataInputError("Foundation checkpoint must expose unique non-empty heads.")
        object.__setattr__(self, "available_heads", heads)
        object.__setattr__(self, "atomic_numbers", _as_int_tuple(self.atomic_numbers))
        if not self.atomic_numbers:
            raise TrainingDataInputError("Foundation checkpoint exposes no supported atomic numbers.")
        object.__setattr__(self, "atomic_energies_shape", tuple(int(v) for v in self.atomic_energies_shape))
        object.__setattr__(self, "interaction_signatures", tuple(dict(v) for v in self.interaction_signatures))
        object.__setattr__(self, "product_signatures", tuple(dict(v) for v in self.product_signatures))
        object.__setattr__(self, "readout_signatures", tuple(dict(v) for v in self.readout_signatures))
        object.__setattr__(self, "state_shape_digest", validate_digest(self.state_shape_digest, name="state_shape_digest"))
        if self.num_interactions is not None and self.num_interactions <= 0:
            raise TrainingDataInputError("Foundation interaction count must be positive.")
        if self.r_max_angstrom is not None and self.r_max_angstrom <= 0.0:
            raise TrainingDataInputError("Foundation cutoff radius must be positive.")

    def _architecture_payload(self) -> dict[str, Any]:
        return {
            "model_class": self.model_class,
            "model_module": self.model_module,
            "available_heads": list(self.available_heads),
            "atomic_numbers": list(self.atomic_numbers),
            "r_max_angstrom": self.r_max_angstrom,
            "num_interactions": self.num_interactions,
            "model_dtype": self.model_dtype,
            "atomic_energies_shape": list(self.atomic_energies_shape),
            "interaction_signatures": [dict(v) for v in self.interaction_signatures],
            "product_signatures": [dict(v) for v in self.product_signatures],
            "readout_signatures": [dict(v) for v in self.readout_signatures],
            "edge_irreps": self.edge_irreps,
            "use_agnostic_product": self.use_agnostic_product,
            "use_last_readout_only": self.use_last_readout_only,
            "state_shape_digest": self.state_shape_digest,
        }

    @property
    def architecture_signature(self) -> str:
        return digest(self._architecture_payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_FOUNDATION_INSPECTION_SCHEMA,
            "sha256": self.sha256,
            **self._architecture_payload(),
            "architecture_signature": self.architecture_signature,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "reference": self.reference, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceFoundationInspection":
        if payload.get("schema") != MACE_FOUNDATION_INSPECTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE foundation-inspection schema.")
        result = cls(
            reference=str(payload["reference"]),
            sha256=str(payload["sha256"]),
            model_class=str(payload["model_class"]),
            model_module=str(payload["model_module"]),
            available_heads=tuple(str(v) for v in payload["available_heads"]),
            atomic_numbers=tuple(int(v) for v in payload["atomic_numbers"]),
            r_max_angstrom=None if payload.get("r_max_angstrom") is None else float(payload["r_max_angstrom"]),
            num_interactions=None if payload.get("num_interactions") is None else int(payload["num_interactions"]),
            model_dtype=None if payload.get("model_dtype") is None else str(payload["model_dtype"]),
            atomic_energies_shape=tuple(int(v) for v in payload.get("atomic_energies_shape", ())),
            interaction_signatures=tuple(dict(v) for v in payload.get("interaction_signatures", ())),
            product_signatures=tuple(dict(v) for v in payload.get("product_signatures", ())),
            readout_signatures=tuple(dict(v) for v in payload.get("readout_signatures", ())),
            edge_irreps=None if payload.get("edge_irreps") is None else str(payload["edge_irreps"]),
            use_agnostic_product=None if payload.get("use_agnostic_product") is None else bool(payload["use_agnostic_product"]),
            use_last_readout_only=None if payload.get("use_last_readout_only") is None else bool(payload["use_last_readout_only"]),
            state_shape_digest=str(payload["state_shape_digest"]),
        )
        if payload.get("architecture_signature") not in (None, result.architecture_signature):
            raise TrainingDataSerializationError("MACE foundation architecture-signature mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE foundation-inspection digest mismatch.")
        return result


def inspect_mace_foundation(path: str | Path) -> MaceFoundationInspection:
    """Inspect a serialized MACE checkpoint directly on CPU.

    This operation deliberately does not construct ``MACECalculator`` and does
    not select a head.  It therefore runs before any calculator fallback could
    silently change scientific identity.
    """

    source = Path(path)
    if not source.is_file():
        raise TrainingDataInputError(f"Foundation checkpoint does not exist: {source!s}.")
    sha256 = sha256_file_cached(source)
    try:
        import torch
        # Importing mace registers the classes needed by the torch pickle.
        import mace  # noqa: F401
    except Exception as exc:
        raise TrainingDataInputError(
            "MACE checkpoint inspection requires torch and mace-torch in the active environment."
        ) from exc

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            model = torch.load(str(source), map_location="cpu", weights_only=False)
    except Exception as exc:
        raise TrainingDataInputError(f"Failed to load MACE foundation checkpoint {source!s}: {exc}") from exc

    heads_raw = getattr(model, "heads", None)
    if heads_raw is None:
        heads = ("default",)
    else:
        heads = tuple(str(v) for v in heads_raw)
        if not heads:
            heads = ("default",)
    atomic_numbers = _as_int_tuple(getattr(model, "atomic_numbers", ()))
    if not atomic_numbers:
        raise TrainingDataInputError("Loaded MACE checkpoint does not expose an atomic-number table.")

    interactions = tuple(_module_signature(v) for v in getattr(model, "interactions", ()))
    products = tuple(_module_signature(v) for v in getattr(model, "products", ()))
    readouts = tuple(_module_signature(v) for v in getattr(model, "readouts", ()))
    if not interactions:
        raise TrainingDataInputError("Loaded object does not look like a supported MACE model: no interactions found.")

    return MaceFoundationInspection(
        reference=str(source.resolve()),
        sha256=sha256,
        model_class=type(model).__name__,
        model_module=type(model).__module__,
        available_heads=heads,
        atomic_numbers=atomic_numbers,
        r_max_angstrom=_scalar_float(getattr(model, "r_max", None)),
        num_interactions=_scalar_int(getattr(model, "num_interactions", None)),
        model_dtype=_model_dtype(model),
        atomic_energies_shape=_atomic_energies_shape(model),
        interaction_signatures=interactions,
        product_signatures=products,
        readout_signatures=readouts,
        edge_irreps=_string_attr(model, "edge_irreps"),
        use_agnostic_product=None if not hasattr(model, "use_agnostic_product") else bool(model.use_agnostic_product),
        use_last_readout_only=None if not hasattr(model, "use_last_readout_only") else bool(model.use_last_readout_only),
        state_shape_digest=_state_shape_digest(model),
    )


def _validate_family_against_inspection(
    family: MaceFoundationFamily,
    inspection: MaceFoundationInspection,
) -> None:
    if family is MaceFoundationFamily.CUSTOM:
        return
    interaction_classes = tuple(str(v.get("class", "")) for v in inspection.interaction_signatures)
    if family is MaceFoundationFamily.MPA_0:
        valid = (
            inspection.available_heads == ("default",)
            and any("Density" in name for name in interaction_classes)
            and inspection.use_agnostic_product is not True
        )
        if not valid:
            raise TrainingDataInputError(
                "Configured family mace_mpa_0 is incompatible with the inspected checkpoint "
                f"(heads={inspection.available_heads}, interactions={interaction_classes})."
            )
        return
    if family is MaceFoundationFamily.MH_1:
        valid = (
            len(inspection.available_heads) > 1
            and "omat_pbe" in inspection.available_heads
            and inspection.use_agnostic_product is True
            and inspection.edge_irreps is not None
            and all("NonLinear" in name for name in interaction_classes)
        )
        if not valid:
            raise TrainingDataInputError(
                "Configured family mace_mh_1 is incompatible with the inspected checkpoint "
                f"(heads={inspection.available_heads}, interactions={interaction_classes})."
            )
        return
    raise AssertionError(f"Unhandled foundation family {family!r}")


def _resolve_head(requested_head: str | None, inspection: MaceFoundationInspection) -> str:
    heads = inspection.available_heads
    requested = None if requested_head is None else str(requested_head).strip()
    if requested == "":
        requested = None
    if len(heads) == 1:
        only = heads[0]
        if requested is None:
            return only
        if requested != only:
            raise TrainingDataInputError(
                f"Requested foundation head {requested!r} is unavailable; checkpoint exposes only {only!r}."
            )
        return only
    if requested is None:
        raise TrainingDataInputError(
            "Multi-head MACE foundation requires an explicit foundation head before calculator construction; "
            f"available heads are {heads}."
        )
    if requested not in heads:
        raise TrainingDataInputError(
            f"Requested foundation head {requested!r} is unavailable; available heads are {heads}."
        )
    return requested


@dataclass(frozen=True, slots=True)
class MaceFoundationSpec:
    family: MaceFoundationFamily | str
    requested_head: str | None = None
    requested_atomic_numbers: tuple[int, ...] = ()
    correction_stack: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "family", MaceFoundationFamily.parse(self.family))
        head = None if self.requested_head is None else str(self.requested_head).strip()
        object.__setattr__(self, "requested_head", None if head == "" else head)
        numbers = _as_int_tuple(self.requested_atomic_numbers)
        object.__setattr__(self, "requested_atomic_numbers", numbers)
        corrections = tuple(str(v).strip() for v in self.correction_stack)
        if any(not v for v in corrections) or len(set(corrections)) != len(corrections):
            raise TrainingDataInputError("Foundation correction stack must contain unique non-empty identifiers.")
        object.__setattr__(self, "correction_stack", corrections)

    def resolve(self, inspection: MaceFoundationInspection) -> "FoundationPotentialIdentity":
        _validate_family_against_inspection(self.family, inspection)
        head = _resolve_head(self.requested_head, inspection)
        missing = tuple(sorted(set(self.requested_atomic_numbers) - set(inspection.atomic_numbers)))
        if missing:
            raise TrainingDataInputError(
                "Requested species are not supported by the foundation checkpoint: "
                f"missing atomic numbers {missing}."
            )
        return FoundationPotentialIdentity(
            reference=inspection.reference,
            sha256=inspection.sha256,
            foundation_head=head,
            model_family=self.family.value,
            architecture_signature=inspection.architecture_signature,
            model_atomic_numbers=inspection.atomic_numbers,
            available_heads=inspection.available_heads,
            correction_stack=self.correction_stack,
            inspection_state="inspected",
        )

    def resolve_file(self, path: str | Path) -> "FoundationPotentialIdentity":
        return self.resolve(inspect_mace_foundation(path))


@dataclass(frozen=True, slots=True)
class FoundationPotentialIdentity:
    """Scientific identity of a selected MACE foundation potential/head.

    ``serialization_schema`` is an internal compatibility knob.  New objects use
    v3.  Objects deserialized from v1/v2 preserve that source schema so parent
    artifact digests remain valid; use ``canonical_content_digest`` for new
    lineage and ``canonicalized()`` when writing a new artifact.
    """

    reference: str
    sha256: str
    foundation_head: str = "default"
    model_family: str = MaceFoundationFamily.MPA_0.value
    architecture_signature: str | None = None
    model_atomic_numbers: tuple[int, ...] = ()
    available_heads: tuple[str, ...] = ()
    correction_stack: tuple[str, ...] = ()
    inspection_state: str = "uninspected"
    serialization_schema: str = field(default=FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.reference.strip() or not self.foundation_head.strip() or not str(self.model_family).strip():
            raise TrainingDataInputError("Foundation checkpoint identifiers must be non-empty.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA:
            object.__setattr__(self, "model_family", MaceFoundationFamily.parse(self.model_family).value)
        elif self.serialization_schema not in {
            FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA,
            FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA,
        }:
            raise TrainingDataInputError("Unsupported internal foundation serialization schema.")
        if self.architecture_signature is not None:
            object.__setattr__(
                self,
                "architecture_signature",
                validate_digest(self.architecture_signature, name="architecture_signature"),
            )
        object.__setattr__(self, "model_atomic_numbers", _as_int_tuple(self.model_atomic_numbers))
        heads = tuple(str(v).strip() for v in self.available_heads)
        if any(not v for v in heads) or len(set(heads)) != len(heads):
            raise TrainingDataInputError("Foundation available-head list is invalid.")
        if heads and self.foundation_head not in heads:
            raise TrainingDataInputError("Selected foundation head is absent from the recorded available-head list.")
        object.__setattr__(self, "available_heads", heads)
        corrections = tuple(str(v).strip() for v in self.correction_stack)
        if any(not v for v in corrections) or len(set(corrections)) != len(corrections):
            raise TrainingDataInputError("Foundation correction stack is invalid.")
        object.__setattr__(self, "correction_stack", corrections)
        if self.inspection_state not in {"inspected", "uninspected", "legacy_singleton_authenticated"}:
            raise TrainingDataInputError("Unsupported foundation inspection state.")

    @property
    def family(self) -> MaceFoundationFamily:
        return MaceFoundationFamily.parse(self.model_family)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        foundation_head: str = "default",
        model_family: str = "MACE-MPA-0",
    ) -> "FoundationPotentialIdentity":
        """Historical lightweight byte identity.

        This method intentionally preserves the pre-MH1 no-import behavior for
        existing callers and unit fixtures.  New generalized foundation paths
        should use ``MaceFoundationSpec.resolve_file`` so family/head/species are
        authenticated against the actual checkpoint.
        """

        source = Path(path)
        if not source.is_file():
            raise TrainingDataInputError(f"Foundation checkpoint does not exist: {source!s}.")
        return cls(
            reference=str(source.resolve()),
            sha256=sha256_file_cached(source),
            foundation_head=foundation_head,
            model_family=MaceFoundationFamily.parse(model_family).value,
            inspection_state="uninspected",
        )

    @classmethod
    def from_inspection(
        cls,
        inspection: MaceFoundationInspection,
        *,
        family: MaceFoundationFamily | str,
        requested_head: str | None = None,
        requested_atomic_numbers: Sequence[int] = (),
        correction_stack: Sequence[str] = (),
    ) -> "FoundationPotentialIdentity":
        return MaceFoundationSpec(
            family=family,
            requested_head=requested_head,
            requested_atomic_numbers=tuple(int(v) for v in requested_atomic_numbers),
            correction_stack=tuple(str(v) for v in correction_stack),
        ).resolve(inspection)

    def _canonical_identity_payload(self) -> dict[str, Any]:
        return {
            "schema": FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA,
            "sha256": self.sha256,
            "foundation_head": self.foundation_head,
            "model_family": self.family.value,
            "architecture_signature": self.architecture_signature,
            "model_atomic_numbers": list(self.model_atomic_numbers),
            "available_heads": list(self.available_heads),
            "correction_stack": list(self.correction_stack),
        }

    @property
    def canonical_content_digest(self) -> str:
        return digest(self._canonical_identity_payload())

    def _identity_payload(self) -> dict[str, Any]:
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA:
            return {
                "schema": FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA,
                "sha256": self.sha256,
                "foundation_head": self.foundation_head,
                "model_family": self.model_family,
            }
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA:
            return {
                "schema": FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA,
                "sha256": self.sha256,
                "model_family": self.model_family,
            }
        return self._canonical_identity_payload()

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        payload = {**self._identity_payload(), "reference": self.reference, "content_digest": self.content_digest}
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA:
            payload["inspection_state"] = self.inspection_state
        return payload

    def canonicalized(self, inspection: MaceFoundationInspection | None = None) -> "FoundationPotentialIdentity":
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA and self.inspection_state == "inspected":
            return self
        if inspection is None:
            inspection = inspect_mace_foundation(self.reference)
        if inspection.sha256 != self.sha256:
            raise TrainingDataSerializationError("Foundation checkpoint bytes changed while canonicalizing legacy identity.")
        requested_head: str | None = self.foundation_head
        if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA:
            if len(inspection.available_heads) != 1:
                raise TrainingDataSerializationError(
                    "Head-blind legacy foundation identity is ambiguous for a multi-head checkpoint."
                )
            requested_head = inspection.available_heads[0]
        identity = MaceFoundationSpec(
            family=self.family,
            requested_head=requested_head,
            correction_stack=self.correction_stack,
        ).resolve(inspection)
        state = "legacy_singleton_authenticated" if self.serialization_schema == FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA else "inspected"
        return FoundationPotentialIdentity(
            reference=identity.reference,
            sha256=identity.sha256,
            foundation_head=identity.foundation_head,
            model_family=identity.model_family,
            architecture_signature=identity.architecture_signature,
            model_atomic_numbers=identity.model_atomic_numbers,
            available_heads=identity.available_heads,
            correction_stack=identity.correction_stack,
            inspection_state=state,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationPotentialIdentity":
        schema = str(payload.get("schema", ""))
        if schema == FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA:
            result = cls(
                reference=str(payload["reference"]),
                sha256=str(payload["sha256"]),
                foundation_head=str(payload["foundation_head"]),
                model_family=str(payload["model_family"]),
                architecture_signature=None if payload.get("architecture_signature") is None else str(payload["architecture_signature"]),
                model_atomic_numbers=tuple(int(v) for v in payload.get("model_atomic_numbers", ())),
                available_heads=tuple(str(v) for v in payload.get("available_heads", ())),
                correction_stack=tuple(str(v) for v in payload.get("correction_stack", ())),
                inspection_state=str(payload.get("inspection_state", "uninspected")),
                serialization_schema=schema,
            )
        elif schema == FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA:
            result = cls(
                reference=str(payload["reference"]),
                sha256=str(payload["sha256"]),
                foundation_head=str(payload["foundation_head"]),
                model_family=str(payload["model_family"]),
                inspection_state="uninspected",
                serialization_schema=schema,
            )
        elif schema == FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA:
            # A head-blind identity is accepted only if the exact referenced
            # checkpoint still exists, matches the authenticated SHA, and is
            # demonstrably singleton.
            source = Path(str(payload["reference"]))
            if not source.is_file():
                raise TrainingDataSerializationError(
                    "Head-blind legacy foundation identity requires the original checkpoint for authentication."
                )
            expected_sha = validate_digest(str(payload["sha256"]), name="sha256")
            if sha256_file_cached(source) != expected_sha:
                raise TrainingDataSerializationError("Head-blind legacy foundation checkpoint SHA mismatch.")
            inspection = inspect_mace_foundation(source)
            if len(inspection.available_heads) != 1:
                raise TrainingDataSerializationError(
                    "Head-blind legacy foundation identity is ambiguous for a multi-head checkpoint."
                )
            family_raw = str(payload.get("model_family", MaceFoundationFamily.CUSTOM.value))
            family = MaceFoundationFamily.parse(family_raw)
            _validate_family_against_inspection(family, inspection)
            result = cls(
                reference=str(payload["reference"]),
                sha256=expected_sha,
                foundation_head=inspection.available_heads[0],
                model_family=family_raw,
                architecture_signature=inspection.architecture_signature,
                model_atomic_numbers=inspection.atomic_numbers,
                available_heads=inspection.available_heads,
                inspection_state="legacy_singleton_authenticated",
                serialization_schema=schema,
            )
        else:
            raise TrainingDataSerializationError("Unsupported foundation-checkpoint schema.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Foundation-checkpoint digest mismatch.")
        return result


# Backward-compatible public name used throughout the existing DATA8 branch.
FoundationCheckpointIdentity = FoundationPotentialIdentity


def foundation_identity_matches_lineage(
    identity: FoundationPotentialIdentity,
    *,
    foundation_identity_digest: str | None = None,
    legacy_checkpoint_digest: str | None = None,
) -> bool:
    """Return whether lineage belongs to ``identity`` without guessing multi-head legacy state.

    New artifacts bind ``canonical_content_digest``.  A legacy raw checkpoint SHA
    is accepted only for a demonstrably singleton checkpoint, which keeps old
    MPA-0 evidence usable while refusing ambiguous head-blind MH-1 lineage.
    """

    if foundation_identity_digest is not None:
        return validate_digest(foundation_identity_digest, name="foundation_identity_digest") == identity.canonical_content_digest
    if legacy_checkpoint_digest is None:
        return False
    legacy = validate_digest(legacy_checkpoint_digest, name="legacy_checkpoint_digest")
    if legacy != identity.sha256:
        return False
    # Preserve exact historical semantics for pre-ID1 records.  ID1 also
    # retained a deliberately lightweight ``from_file`` constructor so legacy
    # and synthetic workflows can identify bytes without importing MACE.  Such
    # v3 records are explicitly *uninspected* and carry no head/architecture
    # evidence; accepting their matching raw SHA preserves those historical
    # workflows without weakening the fail-closed rule for inspected multi-head
    # foundations.
    if identity.serialization_schema in {FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA, FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA}:
        return True
    if (
        identity.inspection_state == "uninspected"
        and not identity.available_heads
        and identity.architecture_signature is None
    ):
        return True
    heads = tuple(str(v) for v in identity.available_heads)
    return len(heads) == 1


@dataclass(frozen=True, slots=True)
class FoundationInferenceIdentity:
    """Execution identity layered on a scientific foundation potential.

    Gate MH1-ID1 only establishes this schema.  Accelerator realization and
    DATA6 cache integration are deliberately deferred to later gates.
    """

    foundation_potential_digest: str
    default_dtype: str
    backend: str
    resolved_kernel_mode: str
    mace_version: str
    adapter_version: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "foundation_potential_digest",
            validate_digest(self.foundation_potential_digest, name="foundation_potential_digest"),
        )
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Foundation inference dtype must be float32 or float64.")
        if self.backend not in {"e3nn", "cueq"}:
            raise TrainingDataInputError("Foundation inference backend must be e3nn or cueq.")
        for name in ("resolved_kernel_mode", "mace_version", "adapter_version"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"Foundation inference {name} must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FOUNDATION_INFERENCE_IDENTITY_SCHEMA,
            "foundation_potential_digest": self.foundation_potential_digest,
            "default_dtype": self.default_dtype,
            "backend": self.backend,
            "resolved_kernel_mode": self.resolved_kernel_mode,
            "mace_version": self.mace_version,
            "adapter_version": self.adapter_version,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationInferenceIdentity":
        if payload.get("schema") != FOUNDATION_INFERENCE_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported foundation-inference identity schema.")
        result = cls(
            foundation_potential_digest=str(payload["foundation_potential_digest"]),
            default_dtype=str(payload["default_dtype"]),
            backend=str(payload["backend"]),
            resolved_kernel_mode=str(payload["resolved_kernel_mode"]),
            mace_version=str(payload["mace_version"]),
            adapter_version=str(payload["adapter_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Foundation-inference identity digest mismatch.")
        return result


__all__ = [
    "FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA",
    "FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA",
    "FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA",
    "MACE_FOUNDATION_INSPECTION_SCHEMA",
    "FOUNDATION_INFERENCE_IDENTITY_SCHEMA",
    "MaceFoundationFamily",
    "MaceFoundationSpec",
    "MaceFoundationInspection",
    "FoundationPotentialIdentity",
    "FoundationCheckpointIdentity",
    "FoundationInferenceIdentity",
    "inspect_mace_foundation",
    "foundation_identity_matches_lineage",
]
