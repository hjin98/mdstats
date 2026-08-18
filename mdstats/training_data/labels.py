"""Decomposed electronic-structure identities and label domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)

THEORY_IDENTITY_SCHEMA = "mdstats.training-theory-identity.v1"
ENERGY_REFERENCE_IDENTITY_SCHEMA = "mdstats.training-energy-reference-identity.v1"
DERIVATIVE_CONVENTION_SCHEMA = "mdstats.training-derivative-convention.v1"
NUMERICAL_QUALITY_PROFILE_SCHEMA = "mdstats.training-numerical-quality-profile.v1"
SOFTWARE_PROVENANCE_SCHEMA = "mdstats.training-software-provenance.v1"
ELECTRONIC_STRUCTURE_FINGERPRINT_SCHEMA = "mdstats.electronic-structure-fingerprint.v1"
LABEL_COMPATIBILITY_POLICY_SCHEMA = "mdstats.label-compatibility-policy.v1"
LABEL_COMPATIBILITY_DECISION_SCHEMA = "mdstats.label-compatibility-decision.v1"
LABEL_DOMAIN_SCHEMA = "mdstats.label-domain.v1"
LABEL_DOMAIN_CATALOG_SCHEMA = "mdstats.label-domain-catalog.v1"
LABEL_COMPATIBILITY_POLICY_VERSION = "mdstats.mlff-data2.label-compatibility.2026-07.v1"


def _items(value: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> tuple[tuple[str, Any], ...]:
    source = value.items() if isinstance(value, Mapping) else value
    return tuple(
        sorted((str(key), json_value(item)) for key, item in source)
    )


def _dict(value: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return {key: json_value(item) for key, item in value}


@dataclass(frozen=True, slots=True)
class TheoryIdentity:
    xc_settings: tuple[tuple[str, Any], ...]
    dft_u_settings: tuple[tuple[str, Any], ...]
    paw_datasets: tuple[tuple[str, str], ...]
    spin_settings: tuple[tuple[str, Any], ...]
    dispersion_settings: tuple[tuple[str, Any], ...]
    hybrid_settings: tuple[tuple[str, Any], ...]
    resolution_status: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "xc_settings", "dft_u_settings", "spin_settings",
            "dispersion_settings", "hybrid_settings",
        ):
            object.__setattr__(self, name, _items(getattr(self, name)))
        object.__setattr__(
            self, "paw_datasets",
            tuple(sorted((str(symbol), str(label)) for symbol, label in self.paw_datasets)),
        )
        if self.resolution_status not in {"resolved", "partial", "unresolved"}:
            raise TrainingDataInputError("Unsupported theory resolution status.")
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": THEORY_IDENTITY_SCHEMA,
            "xc_settings": _dict(self.xc_settings),
            "dft_u_settings": _dict(self.dft_u_settings),
            "paw_datasets": dict(self.paw_datasets),
            "spin_settings": _dict(self.spin_settings),
            "dispersion_settings": _dict(self.dispersion_settings),
            "hybrid_settings": _dict(self.hybrid_settings),
            "resolution_status": self.resolution_status,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TheoryIdentity":
        if payload.get("schema") != THEORY_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported theory-identity schema.")
        result = cls(
            xc_settings=_items(payload.get("xc_settings", {})),
            dft_u_settings=_items(payload.get("dft_u_settings", {})),
            paw_datasets=tuple(
                (str(key), str(value))
                for key, value in payload.get("paw_datasets", {}).items()
            ),
            spin_settings=_items(payload.get("spin_settings", {})),
            dispersion_settings=_items(payload.get("dispersion_settings", {})),
            hybrid_settings=_items(payload.get("hybrid_settings", {})),
            resolution_status=str(payload["resolution_status"]),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Theory-identity digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class EnergyReferenceIdentity:
    source_name: str
    semantic_role: str
    units: str
    normalization: str
    smearing_settings: tuple[tuple[str, Any], ...]
    entropy_convention: str
    resolution_status: str = "resolved"

    def __post_init__(self) -> None:
        object.__setattr__(self, "smearing_settings", _items(self.smearing_settings))
        if self.resolution_status not in {"resolved", "partial", "unresolved"}:
            raise TrainingDataInputError("Unsupported energy-reference resolution status.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ENERGY_REFERENCE_IDENTITY_SCHEMA,
            "source_name": self.source_name,
            "semantic_role": self.semantic_role,
            "units": self.units,
            "normalization": self.normalization,
            "smearing_settings": _dict(self.smearing_settings),
            "entropy_convention": self.entropy_convention,
            "resolution_status": self.resolution_status,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EnergyReferenceIdentity":
        if payload.get("schema") != ENERGY_REFERENCE_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported energy-reference schema.")
        result = cls(
            source_name=str(payload["source_name"]),
            semantic_role=str(payload["semantic_role"]),
            units=str(payload["units"]),
            normalization=str(payload["normalization"]),
            smearing_settings=_items(payload.get("smearing_settings", {})),
            entropy_convention=str(payload["entropy_convention"]),
            resolution_status=str(payload.get("resolution_status", "resolved")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Energy-reference digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class DerivativeConvention:
    force_units: str = "eV/angstrom"
    force_sign: str = "negative_energy_gradient"
    stress_label_kind: str = "cauchy_stress"
    stress_units: str = "eV/angstrom^3"
    stress_sign: str = "tensile_positive"
    stress_representation: str = "symmetric_3x3_cartesian"
    shear_convention: str = "tensor_shear_no_engineering_factor"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DERIVATIVE_CONVENTION_SCHEMA,
            "force_units": self.force_units,
            "force_sign": self.force_sign,
            "stress_label_kind": self.stress_label_kind,
            "stress_units": self.stress_units,
            "stress_sign": self.stress_sign,
            "stress_representation": self.stress_representation,
            "shear_convention": self.shear_convention,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DerivativeConvention":
        if payload.get("schema") != DERIVATIVE_CONVENTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported derivative-convention schema.")
        result = cls(**{key: str(payload[key]) for key in (
            "force_units", "force_sign", "stress_label_kind", "stress_units",
            "stress_sign", "stress_representation", "shear_convention",
        )})
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Derivative-convention digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class NumericalQualityProfile:
    settings: tuple[tuple[str, Any], ...]
    kpoint_count: int | None
    kpoint_payload_sha256: str | None
    scf_limit_fraction: float | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "settings", _items(self.settings))
        if self.kpoint_count is not None and self.kpoint_count < 0:
            raise TrainingDataInputError("kpoint_count must be nonnegative.")
        if self.kpoint_payload_sha256 is not None:
            object.__setattr__(
                self, "kpoint_payload_sha256",
                validate_digest(self.kpoint_payload_sha256, name="kpoint_payload_sha256"),
            )
        if self.scf_limit_fraction is not None and not 0 <= self.scf_limit_fraction <= 1:
            raise TrainingDataInputError("scf_limit_fraction must lie in [0, 1].")
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NUMERICAL_QUALITY_PROFILE_SCHEMA,
            "settings": _dict(self.settings),
            "kpoint_count": self.kpoint_count,
            "kpoint_payload_sha256": self.kpoint_payload_sha256,
            "scf_limit_fraction": self.scf_limit_fraction,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NumericalQualityProfile":
        if payload.get("schema") != NUMERICAL_QUALITY_PROFILE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported numerical-quality schema.")
        result = cls(
            settings=_items(payload.get("settings", {})),
            kpoint_count=(None if payload.get("kpoint_count") is None else int(payload["kpoint_count"])),
            kpoint_payload_sha256=(None if payload.get("kpoint_payload_sha256") is None else str(payload["kpoint_payload_sha256"])),
            scf_limit_fraction=(None if payload.get("scf_limit_fraction") is None else float(payload["scf_limit_fraction"])),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Numerical-quality digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SoftwareProvenance:
    source_program: str
    source_program_version: str | None
    source_program_subversion: str | None
    control_semantics_version: str
    parser_package: str
    parser_version: str

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOFTWARE_PROVENANCE_SCHEMA,
            "source_program": self.source_program,
            "source_program_version": self.source_program_version,
            "source_program_subversion": self.source_program_subversion,
            "control_semantics_version": self.control_semantics_version,
            "parser_package": self.parser_package,
            "parser_version": self.parser_version,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SoftwareProvenance":
        if payload.get("schema") != SOFTWARE_PROVENANCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported software-provenance schema.")
        result = cls(
            source_program=str(payload["source_program"]),
            source_program_version=None if payload.get("source_program_version") is None else str(payload["source_program_version"]),
            source_program_subversion=None if payload.get("source_program_subversion") is None else str(payload["source_program_subversion"]),
            control_semantics_version=str(payload["control_semantics_version"]),
            parser_package=str(payload["parser_package"]),
            parser_version=str(payload["parser_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Software-provenance digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ElectronicStructureFingerprint:
    theory: TheoryIdentity
    energy_reference: EnergyReferenceIdentity
    derivative_convention: DerivativeConvention
    numerical_quality: NumericalQualityProfile
    software_provenance: SoftwareProvenance

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ELECTRONIC_STRUCTURE_FINGERPRINT_SCHEMA,
            "theory": self.theory.to_dict(),
            "energy_reference": self.energy_reference.to_dict(),
            "derivative_convention": self.derivative_convention.to_dict(),
            "numerical_quality": self.numerical_quality.to_dict(),
            "software_provenance": self.software_provenance.to_dict(),
        }

    @property
    def core_label_digest(self) -> str:
        return digest({
            "theory": self.theory.content_digest,
            "energy_reference": self.energy_reference.content_digest,
            "derivative_convention": self.derivative_convention.content_digest,
        })

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "core_label_digest": self.core_label_digest, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ElectronicStructureFingerprint":
        if payload.get("schema") != ELECTRONIC_STRUCTURE_FINGERPRINT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported fingerprint schema.")
        result = cls(
            theory=TheoryIdentity.from_dict(payload["theory"]),
            energy_reference=EnergyReferenceIdentity.from_dict(payload["energy_reference"]),
            derivative_convention=DerivativeConvention.from_dict(payload["derivative_convention"]),
            numerical_quality=NumericalQualityProfile.from_dict(payload["numerical_quality"]),
            software_provenance=SoftwareProvenance.from_dict(payload["software_provenance"]),
        )
        if payload.get("core_label_digest") not in (None, result.core_label_digest):
            raise TrainingDataSerializationError("Core label digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Fingerprint digest mismatch.")
        return result


class LabelCompatibilityOutcome(str, Enum):
    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_QUALITY_FLAG = "compatible_with_quality_flag"
    SEPARATE_LABEL_DOMAIN = "separate_label_domain"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class LabelCompatibilityPolicy:
    require_resolved_theory: bool = True
    require_resolved_energy_reference: bool = True
    numerical_differences_are_quality_flags: bool = True
    software_differences_are_quality_flags: bool = True
    policy_version: str = LABEL_COMPATIBILITY_POLICY_VERSION

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LABEL_COMPATIBILITY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "require_resolved_theory": self.require_resolved_theory,
            "require_resolved_energy_reference": self.require_resolved_energy_reference,
            "numerical_differences_are_quality_flags": self.numerical_differences_are_quality_flags,
            "software_differences_are_quality_flags": self.software_differences_are_quality_flags,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LabelCompatibilityPolicy":
        if payload.get("schema") != LABEL_COMPATIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported label-compatibility policy schema.")
        result = cls(
            require_resolved_theory=bool(payload["require_resolved_theory"]),
            require_resolved_energy_reference=bool(payload["require_resolved_energy_reference"]),
            numerical_differences_are_quality_flags=bool(payload["numerical_differences_are_quality_flags"]),
            software_differences_are_quality_flags=bool(payload["software_differences_are_quality_flags"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Label-compatibility policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LabelCompatibilityDecision:
    left_fingerprint_digest: str
    right_fingerprint_digest: str
    policy_digest: str
    outcome: LabelCompatibilityOutcome
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("left_fingerprint_digest", "right_fingerprint_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "outcome", LabelCompatibilityOutcome(self.outcome))
        object.__setattr__(self, "reasons", tuple(str(item) for item in self.reasons))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LABEL_COMPATIBILITY_DECISION_SCHEMA,
            "left_fingerprint_digest": self.left_fingerprint_digest,
            "right_fingerprint_digest": self.right_fingerprint_digest,
            "policy_digest": self.policy_digest,
            "outcome": self.outcome.value,
            "reasons": list(self.reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LabelCompatibilityDecision":
        if payload.get("schema") != LABEL_COMPATIBILITY_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported label-compatibility-decision schema.")
        result = cls(
            left_fingerprint_digest=str(payload["left_fingerprint_digest"]),
            right_fingerprint_digest=str(payload["right_fingerprint_digest"]),
            policy_digest=str(payload["policy_digest"]),
            outcome=LabelCompatibilityOutcome(payload["outcome"]),
            reasons=tuple(str(item) for item in payload.get("reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Label-compatibility-decision digest mismatch.")
        return result


def _theory_base_payload(theory: TheoryIdentity) -> dict[str, Any]:
    return {
        "xc_settings": _dict(theory.xc_settings),
        "dft_u_settings": _dict(theory.dft_u_settings),
        "spin_settings": _dict(theory.spin_settings),
        "dispersion_settings": _dict(theory.dispersion_settings),
        "hybrid_settings": _dict(theory.hybrid_settings),
    }


def _theory_identities_compatible(left: TheoryIdentity, right: TheoryIdentity) -> bool:
    if _theory_base_payload(left) != _theory_base_payload(right):
        return False
    left_paw = dict(left.paw_datasets)
    right_paw = dict(right.paw_datasets)
    return all(left_paw[element] == right_paw[element] for element in left_paw.keys() & right_paw.keys())


def _aggregate_domain_core(members: Sequence[tuple[str, ElectronicStructureFingerprint]]) -> str:
    first = members[0][1]
    paw: dict[str, str] = {}
    for _, fingerprint in members:
        for element, label in fingerprint.theory.paw_datasets:
            previous = paw.get(element)
            if previous is not None and previous != label:
                raise TrainingDataInputError(
                    f"Conflicting PAW dataset for {element!r} inside one label domain."
                )
            paw[element] = label
    return digest({
        "theory_base": _theory_base_payload(first.theory),
        "paw_datasets": paw,
        "energy_reference": first.energy_reference.content_digest,
        "derivative_convention": first.derivative_convention.content_digest,
    })


def compare_label_fingerprints(
    left: ElectronicStructureFingerprint,
    right: ElectronicStructureFingerprint,
    *,
    policy: LabelCompatibilityPolicy | None = None,
) -> LabelCompatibilityDecision:
    active = LabelCompatibilityPolicy() if policy is None else policy
    reasons: list[str] = []
    unresolved = (
        active.require_resolved_theory
        and (left.theory.resolution_status != "resolved" or right.theory.resolution_status != "resolved")
    ) or (
        active.require_resolved_energy_reference
        and (
            left.energy_reference.resolution_status != "resolved"
            or right.energy_reference.resolution_status != "resolved"
        )
    )
    if unresolved:
        outcome = LabelCompatibilityOutcome.UNRESOLVED
        reasons.append("Required theory or energy-reference identity is unresolved.")
    elif not _theory_identities_compatible(left.theory, right.theory):
        outcome = LabelCompatibilityOutcome.SEPARATE_LABEL_DOMAIN
        reasons.append("Theory identity differs or overlapping PAW datasets conflict.")
    elif left.energy_reference.content_digest != right.energy_reference.content_digest:
        outcome = LabelCompatibilityOutcome.SEPARATE_LABEL_DOMAIN
        reasons.append("Energy-reference identity differs.")
    elif left.derivative_convention.content_digest != right.derivative_convention.content_digest:
        outcome = LabelCompatibilityOutcome.SEPARATE_LABEL_DOMAIN
        reasons.append("Derivative convention differs.")
    else:
        quality_difference = left.numerical_quality.content_digest != right.numerical_quality.content_digest
        software_difference = left.software_provenance.content_digest != right.software_provenance.content_digest
        if quality_difference and active.numerical_differences_are_quality_flags:
            reasons.append("Numerical-quality profile differs.")
        elif quality_difference:
            outcome = LabelCompatibilityOutcome.SEPARATE_LABEL_DOMAIN
            reasons.append("Numerical-quality profile differs under a strict policy.")
            return LabelCompatibilityDecision(left.content_digest, right.content_digest, active.policy_digest, outcome, tuple(reasons))
        if software_difference and active.software_differences_are_quality_flags:
            reasons.append("Software provenance differs.")
        elif software_difference:
            outcome = LabelCompatibilityOutcome.SEPARATE_LABEL_DOMAIN
            reasons.append("Software provenance differs under a strict policy.")
            return LabelCompatibilityDecision(left.content_digest, right.content_digest, active.policy_digest, outcome, tuple(reasons))
        outcome = (
            LabelCompatibilityOutcome.COMPATIBLE_WITH_QUALITY_FLAG
            if reasons else LabelCompatibilityOutcome.COMPATIBLE
        )
    return LabelCompatibilityDecision(
        left_fingerprint_digest=left.content_digest,
        right_fingerprint_digest=right.content_digest,
        policy_digest=active.policy_digest,
        outcome=outcome,
        reasons=tuple(reasons),
    )


@dataclass(frozen=True, slots=True)
class LabelDomain:
    domain_id: str
    core_label_digest: str
    source_ids: tuple[str, ...]
    fingerprint_digests: tuple[str, ...]
    numerical_quality_digests: tuple[str, ...]
    software_provenance_digests: tuple[str, ...]
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_digest(self.core_label_digest, name="core_label_digest")
        if not self.domain_id or not self.source_ids:
            raise TrainingDataInputError("Label domain requires an id and sources.")
        object.__setattr__(self, "source_ids", tuple(sorted(str(item) for item in self.source_ids)))
        object.__setattr__(self, "fingerprint_digests", tuple(sorted(validate_digest(item, name="fingerprint_digest") for item in self.fingerprint_digests)))
        object.__setattr__(self, "numerical_quality_digests", tuple(sorted(validate_digest(item, name="numerical_quality_digest") for item in self.numerical_quality_digests)))
        object.__setattr__(self, "software_provenance_digests", tuple(sorted(validate_digest(item, name="software_provenance_digest") for item in self.software_provenance_digests)))
        object.__setattr__(self, "quality_flags", tuple(sorted(str(item) for item in self.quality_flags)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LABEL_DOMAIN_SCHEMA,
            "domain_id": self.domain_id,
            "core_label_digest": self.core_label_digest,
            "source_ids": list(self.source_ids),
            "fingerprint_digests": list(self.fingerprint_digests),
            "numerical_quality_digests": list(self.numerical_quality_digests),
            "software_provenance_digests": list(self.software_provenance_digests),
            "quality_flags": list(self.quality_flags),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LabelDomain":
        if payload.get("schema") != LABEL_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported label-domain schema.")
        result = cls(
            domain_id=str(payload["domain_id"]),
            core_label_digest=str(payload["core_label_digest"]),
            source_ids=tuple(str(item) for item in payload.get("source_ids", ())),
            fingerprint_digests=tuple(str(item) for item in payload.get("fingerprint_digests", ())),
            numerical_quality_digests=tuple(str(item) for item in payload.get("numerical_quality_digests", ())),
            software_provenance_digests=tuple(str(item) for item in payload.get("software_provenance_digests", ())),
            quality_flags=tuple(str(item) for item in payload.get("quality_flags", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Label-domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LabelDomainCatalog:
    policy_digest: str
    domains: tuple[LabelDomain, ...]
    source_domain_assignments: tuple[tuple[str, str], ...]
    unresolved_source_ids: tuple[str, ...] = ()
    _domain_by_source: dict[str, str] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        validate_digest(self.policy_digest, name="policy_digest")
        object.__setattr__(self, "domains", tuple(sorted(self.domains, key=lambda item: item.domain_id)))
        assignments = tuple(sorted((str(a), str(b)) for a, b in self.source_domain_assignments))
        object.__setattr__(self, "source_domain_assignments", assignments)
        object.__setattr__(self, "unresolved_source_ids", tuple(sorted(str(item) for item in self.unresolved_source_ids)))
        object.__setattr__(self, "_domain_by_source", dict(assignments))

    def domain_for_source(self, source_id: str) -> str | None:
        return self._domain_by_source.get(source_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LABEL_DOMAIN_CATALOG_SCHEMA,
            "policy_digest": self.policy_digest,
            "domains": [item.to_dict() for item in self.domains],
            "source_domain_assignments": dict(self.source_domain_assignments),
            "unresolved_source_ids": list(self.unresolved_source_ids),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LabelDomainCatalog":
        if payload.get("schema") != LABEL_DOMAIN_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported label-domain-catalog schema.")
        assignments = payload.get("source_domain_assignments", {})
        if not isinstance(assignments, Mapping):
            raise TrainingDataSerializationError("source_domain_assignments must be a mapping.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            domains=tuple(LabelDomain.from_dict(item) for item in payload.get("domains", ())),
            source_domain_assignments=tuple((str(key), str(value)) for key, value in assignments.items()),
            unresolved_source_ids=tuple(str(item) for item in payload.get("unresolved_source_ids", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Label-domain-catalog digest mismatch.")
        return result


def build_label_domain_catalog(
    source_fingerprints: Mapping[str, ElectronicStructureFingerprint],
    *,
    policy: LabelCompatibilityPolicy | None = None,
) -> LabelDomainCatalog:
    """Build deterministic compatibility domains without all-pairs comparisons.

    The former first-fit implementation compared a new fingerprint with every
    member of every existing group, which is O(S**2) in source count.  Domain
    compatibility depends on a small immutable base key plus the aggregate PAW
    labels already present in a group.  Bucket by the immutable key and use
    bit-set indexes for PAW conflicts, preserving the original earliest
    compatible-group rule while reducing Python work to approximately O(S*P),
    where P is the number of PAW-labelled elements per source.
    """

    active = LabelCompatibilityPolicy() if policy is None else policy
    groups: list[list[tuple[str, ElectronicStructureFingerprint]]] = []
    group_paw: list[dict[str, str]] = []
    unresolved: list[str] = []

    # Global group-index bit masks are convenient here: a candidate's
    # incompatible groups are the union of groups that define one of its PAW
    # elements with a different label.  The least-significant compatible bit
    # is exactly the earliest compatible group used by the historical
    # deterministic first-fit algorithm.
    bucket_masks: dict[tuple[Any, ...], int] = {}
    groups_defining_element: dict[tuple[tuple[Any, ...], str], int] = {}
    groups_with_element_label: dict[tuple[tuple[Any, ...], str, str], int] = {}

    def base_key(fingerprint: ElectronicStructureFingerprint) -> tuple[Any, ...]:
        return (
            digest(_theory_base_payload(fingerprint.theory)),
            fingerprint.energy_reference.content_digest,
            fingerprint.derivative_convention.content_digest,
            (
                fingerprint.numerical_quality.content_digest
                if not active.numerical_differences_are_quality_flags
                else None
            ),
            (
                fingerprint.software_provenance.content_digest
                if not active.software_differences_are_quality_flags
                else None
            ),
        )

    for source_id, fingerprint in sorted(source_fingerprints.items()):
        is_unresolved = (
            active.require_resolved_theory
            and fingerprint.theory.resolution_status != "resolved"
        ) or (
            active.require_resolved_energy_reference
            and fingerprint.energy_reference.resolution_status != "resolved"
        )
        if is_unresolved:
            unresolved.append(source_id)
            continue

        key = base_key(fingerprint)
        paw = dict(fingerprint.theory.paw_datasets)
        forbidden = 0
        for element, label in paw.items():
            defining = groups_defining_element.get((key, element), 0)
            matching = groups_with_element_label.get((key, element, label), 0)
            forbidden |= defining & ~matching
        compatible = bucket_masks.get(key, 0) & ~forbidden
        if compatible:
            lowest_bit = compatible & -compatible
            group_index = lowest_bit.bit_length() - 1
            groups[group_index].append((source_id, fingerprint))
        else:
            group_index = len(groups)
            groups.append([(source_id, fingerprint)])
            group_paw.append({})
            bit = 1 << group_index
            bucket_masks[key] = bucket_masks.get(key, 0) | bit

        bit = 1 << group_index
        aggregate = group_paw[group_index]
        for element, label in paw.items():
            previous = aggregate.get(element)
            if previous is not None and previous != label:
                # This should be impossible because the conflict mask excludes
                # the group.  Keep a fail-closed invariant in case the index is
                # changed in the future.
                raise TrainingDataInputError(
                    f"Conflicting PAW dataset for {element!r} inside one label domain."
                )
            if previous is None:
                aggregate[element] = label
                defining_key = (key, element)
                matching_key = (key, element, label)
                groups_defining_element[defining_key] = (
                    groups_defining_element.get(defining_key, 0) | bit
                )
                groups_with_element_label[matching_key] = (
                    groups_with_element_label.get(matching_key, 0) | bit
                )

    domains: list[LabelDomain] = []
    assignments: list[tuple[str, str]] = []
    for members in groups:
        core_digest = _aggregate_domain_core(members)
        domain_id = f"label-domain-{core_digest[:16]}"
        numerical = {item.numerical_quality.content_digest for _, item in members}
        software = {item.software_provenance.content_digest for _, item in members}
        flags: list[str] = []
        if len(numerical) > 1:
            flags.append("numerical_quality_variants")
        if len(software) > 1:
            flags.append("software_provenance_variants")
        source_ids = tuple(source_id for source_id, _ in members)
        domains.append(LabelDomain(
            domain_id=domain_id,
            core_label_digest=core_digest,
            source_ids=source_ids,
            fingerprint_digests=tuple(item.content_digest for _, item in members),
            numerical_quality_digests=tuple(numerical),
            software_provenance_digests=tuple(software),
            quality_flags=tuple(flags),
        ))
        assignments.extend((source_id, domain_id) for source_id in source_ids)
    return LabelDomainCatalog(
        policy_digest=active.policy_digest,
        domains=tuple(domains),
        source_domain_assignments=tuple(assignments),
        unresolved_source_ids=tuple(unresolved),
    )

