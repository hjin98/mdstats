"""Cross-system qualification evidence for the general MLFF preparation path.

The module does not calculate physical descriptors.  It audits already-built
DATA4-DATA7 products and proves that generic profiles remain independent of the
optional LTA implementation while the LTA profile travels through the same
provider envelopes and generic selection machinery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    canonical_json,
    digest,
    validate_digest,
)
from .material_profiles import MaterialGeometryKind, MaterialPhaseKind, StructuralExtension

IMPORT_ISOLATION_EVIDENCE_SCHEMA = "mdstats.import-isolation-evidence.v1"
CROSS_SYSTEM_QUALIFICATION_POLICY_SCHEMA = "mdstats.cross-system-qualification-policy.v1"
CROSS_SYSTEM_QUALIFICATION_CASE_SCHEMA = "mdstats.cross-system-qualification-case.v1"
CROSS_SYSTEM_QUALIFICATION_SUITE_SCHEMA = "mdstats.cross-system-qualification-suite.v1"
MLFF_DATA9A7E_PARSER_VERSION = "0.20.51a0"
CROSS_SYSTEM_QUALIFICATION_VERSION = "mdstats.mlff-data9a7e.cross-system.2026-07.v1"


@dataclass(frozen=True, slots=True)
class ImportIsolationEvidence:
    probe_id: str
    clean_interpreter: bool
    modules_before: tuple[str, ...]
    modules_after_generic_import: tuple[str, ...]
    forbidden_module_prefixes: tuple[str, ...]
    probe_script_digest: str
    passed: bool

    def __post_init__(self) -> None:
        if not str(self.probe_id).strip():
            raise TrainingDataInputError("probe_id must be nonempty.")
        object.__setattr__(self, "probe_script_digest", validate_digest(self.probe_script_digest, name="probe_script_digest"))
        for name in ("modules_before", "modules_after_generic_import", "forbidden_module_prefixes"):
            object.__setattr__(self, name, tuple(sorted(set(str(v) for v in getattr(self, name)))))
        forbidden = tuple(
            module for module in self.modules_after_generic_import
            if any(module == prefix or module.startswith(prefix + ".") for prefix in self.forbidden_module_prefixes)
        )
        expected = self.clean_interpreter and not self.modules_before and not forbidden
        if self.passed != expected:
            raise TrainingDataInputError("Import-isolation passed flag disagrees with the probe evidence.")

    @property
    def forbidden_modules(self) -> tuple[str, ...]:
        return tuple(
            module for module in self.modules_after_generic_import
            if any(module == prefix or module.startswith(prefix + ".") for prefix in self.forbidden_module_prefixes)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": IMPORT_ISOLATION_EVIDENCE_SCHEMA,
            "parser_version": MLFF_DATA9A7E_PARSER_VERSION,
            "probe_id": self.probe_id,
            "clean_interpreter": self.clean_interpreter,
            "modules_before": list(self.modules_before),
            "modules_after_generic_import": list(self.modules_after_generic_import),
            "forbidden_module_prefixes": list(self.forbidden_module_prefixes),
            "probe_script_digest": self.probe_script_digest,
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ImportIsolationEvidence":
        if payload.get("schema") != IMPORT_ISOLATION_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported import-isolation evidence schema.")
        result = cls(
            probe_id=str(payload["probe_id"]),
            clean_interpreter=bool(payload["clean_interpreter"]),
            modules_before=tuple(str(v) for v in payload["modules_before"]),
            modules_after_generic_import=tuple(str(v) for v in payload["modules_after_generic_import"]),
            forbidden_module_prefixes=tuple(str(v) for v in payload["forbidden_module_prefixes"]),
            probe_script_digest=str(payload["probe_script_digest"]),
            passed=bool(payload["passed"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Import-isolation evidence digest mismatch.")
        return result


class CrossSystemCaseKind(str, Enum):
    GENERIC_CRYSTAL = "generic_crystal"
    AMORPHOUS_SOLID = "amorphous_solid"
    LIQUID = "liquid"
    MULTIPHASE_INTERFACE = "multiphase_interface"
    LTA_EXTENSION = "lta_extension"


_EXPECTED_PHASES: dict[CrossSystemCaseKind, frozenset[str]] = {
    CrossSystemCaseKind.GENERIC_CRYSTAL: frozenset({MaterialPhaseKind.CRYSTALLINE_SOLID.value}),
    CrossSystemCaseKind.AMORPHOUS_SOLID: frozenset({MaterialPhaseKind.AMORPHOUS_SOLID.value}),
    CrossSystemCaseKind.LIQUID: frozenset({MaterialPhaseKind.LIQUID.value}),
}


@dataclass(frozen=True, slots=True)
class CrossSystemQualificationPolicy:
    required_case_kinds: tuple[CrossSystemCaseKind, ...] = tuple(CrossSystemCaseKind)
    forbidden_generic_module_prefixes: tuple[str, ...] = (
        "mdstats.training_data.lta_profile",
        "mdstats.training_data.lta_selection",
    )
    forbidden_generic_serialized_keys: tuple[str, ...] = (
        "lta_partition_features",
        "lta_selection_features",
    )
    require_data7_selection: bool = True
    require_clean_import_evidence: bool = True
    policy_version: str = CROSS_SYSTEM_QUALIFICATION_VERSION

    def __post_init__(self) -> None:
        cases = tuple(CrossSystemCaseKind(value) for value in self.required_case_kinds)
        if not cases or len(set(cases)) != len(cases):
            raise TrainingDataInputError("Cross-system required case kinds must be nonempty and unique.")
        object.__setattr__(self, "required_case_kinds", tuple(sorted(cases, key=lambda item: item.value)))
        for name in ("forbidden_generic_module_prefixes", "forbidden_generic_serialized_keys"):
            values = tuple(str(value).strip() for value in getattr(self, name))
            if any(not value for value in values) or len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} must contain unique nonempty strings.")
            object.__setattr__(self, name, tuple(sorted(values)))
        if not str(self.policy_version).strip():
            raise TrainingDataInputError("policy_version must be nonempty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CROSS_SYSTEM_QUALIFICATION_POLICY_SCHEMA,
            "parser_version": MLFF_DATA9A7E_PARSER_VERSION,
            "policy_version": self.policy_version,
            "required_case_kinds": [item.value for item in self.required_case_kinds],
            "forbidden_generic_module_prefixes": list(self.forbidden_generic_module_prefixes),
            "forbidden_generic_serialized_keys": list(self.forbidden_generic_serialized_keys),
            "require_data7_selection": self.require_data7_selection,
            "require_clean_import_evidence": self.require_clean_import_evidence,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossSystemQualificationPolicy":
        if payload.get("schema") != CROSS_SYSTEM_QUALIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported cross-system qualification-policy schema.")
        result = cls(
            required_case_kinds=tuple(CrossSystemCaseKind(str(value)) for value in payload["required_case_kinds"]),
            forbidden_generic_module_prefixes=tuple(str(value) for value in payload["forbidden_generic_module_prefixes"]),
            forbidden_generic_serialized_keys=tuple(str(value) for value in payload["forbidden_generic_serialized_keys"]),
            require_data7_selection=bool(payload.get("require_data7_selection", True)),
            require_clean_import_evidence=bool(payload.get("require_clean_import_evidence", True)),
            policy_version=str(payload.get("policy_version", CROSS_SYSTEM_QUALIFICATION_VERSION)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Cross-system qualification-policy digest mismatch.")
        return result


def _find_serialized_key_paths(value: Any, forbidden_keys: frozenset[str], path: str = "$") -> tuple[str, ...]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in forbidden_keys:
                findings.append(child_path)
            findings.extend(_find_serialized_key_paths(child, forbidden_keys, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            findings.extend(_find_serialized_key_paths(child, forbidden_keys, f"{path}[{index}]"))
    return tuple(findings)


def _extension_ids(data4_bundle: Any, data6_bundle: Any) -> tuple[str, ...]:
    values = {
        str(item.extension_id)
        for item in tuple(getattr(data4_bundle, "profile_partition_features", ()))
        + tuple(getattr(data6_bundle, "profile_selection_features", ()))
    }
    return tuple(sorted(values))


def _expected_profile_passes(kind: CrossSystemCaseKind, contracts: Any, extension_ids: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
    profile = contracts.profile
    phases = frozenset(str(item.phase_kind.value) for item in profile.phases)
    warnings: list[str] = []
    expected = _EXPECTED_PHASES.get(kind)
    if expected is not None and phases != expected:
        warnings.append(f"expected_phase_kinds:{','.join(sorted(expected))}")
    if kind is CrossSystemCaseKind.MULTIPHASE_INTERFACE:
        if profile.geometry is not MaterialGeometryKind.INTERFACE:
            warnings.append("expected_interface_geometry")
        if len(profile.phases) < 2:
            warnings.append("expected_multiple_phases")
    if kind is CrossSystemCaseKind.LTA_EXTENSION:
        required = {
            StructuralExtension.POROUS_NETWORK.value,
            StructuralExtension.ZEOLITE.value,
            StructuralExtension.LTA.value,
        }
        if not required.issubset(set(profile.extensions)):
            warnings.append("missing_lta_extension_chain")
        if "lta" not in extension_ids:
            warnings.append("missing_lta_feature_catalog")
    elif "lta" in extension_ids:
        warnings.append("generic_case_contains_lta_extension")
    return (not warnings, tuple(warnings))


@dataclass(frozen=True, slots=True)
class CrossSystemQualificationCaseRecord:
    case_id: str
    case_kind: CrossSystemCaseKind
    policy_digest: str
    material_profile_contracts_digest: str
    material_profile_digest: str
    phase_kinds: tuple[str, ...]
    geometry: str
    data4_bundle_digest: str
    data5_bundle_digest: str
    data6_bundle_digest: str
    data7_bundle_digest: str
    phase_geometry_plan_digest: str
    enabled_feature_families: tuple[str, ...]
    enabled_event_types: tuple[str, ...]
    profile_extension_ids: tuple[str, ...]
    selected_frame_count: int
    import_isolation_evidence_digest: str
    import_isolation_verified: bool
    forbidden_imported_modules: tuple[str, ...]
    forbidden_serialized_paths: tuple[str, ...]
    profile_contract_passed: bool
    data_lineage_passed: bool
    selection_materialized: bool
    passed: bool
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.case_id).strip():
            raise TrainingDataInputError("case_id must be nonempty.")
        object.__setattr__(self, "case_kind", CrossSystemCaseKind(self.case_kind))
        for name in (
            "policy_digest", "material_profile_contracts_digest", "material_profile_digest",
            "data4_bundle_digest", "data5_bundle_digest", "data6_bundle_digest",
            "data7_bundle_digest", "phase_geometry_plan_digest", "import_isolation_evidence_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.selected_frame_count < 0:
            raise TrainingDataInputError("selected_frame_count must be nonnegative.")
        for name in (
            "phase_kinds", "enabled_feature_families", "enabled_event_types",
            "profile_extension_ids", "forbidden_imported_modules", "forbidden_serialized_paths", "warnings",
        ):
            object.__setattr__(self, name, tuple(sorted(set(str(value) for value in getattr(self, name)))))
        expected_pass = (
            self.profile_contract_passed
            and self.data_lineage_passed
            and self.selection_materialized
            and self.import_isolation_verified
            and not self.forbidden_imported_modules
            and not self.forbidden_serialized_paths
        )
        if self.passed != expected_pass:
            raise TrainingDataInputError("Cross-system case passed flag disagrees with its evidence.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CROSS_SYSTEM_QUALIFICATION_CASE_SCHEMA,
            "parser_version": MLFF_DATA9A7E_PARSER_VERSION,
            "case_id": self.case_id,
            "case_kind": self.case_kind.value,
            "policy_digest": self.policy_digest,
            "material_profile_contracts_digest": self.material_profile_contracts_digest,
            "material_profile_digest": self.material_profile_digest,
            "phase_kinds": list(self.phase_kinds),
            "geometry": self.geometry,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "data7_bundle_digest": self.data7_bundle_digest,
            "phase_geometry_plan_digest": self.phase_geometry_plan_digest,
            "enabled_feature_families": list(self.enabled_feature_families),
            "enabled_event_types": list(self.enabled_event_types),
            "profile_extension_ids": list(self.profile_extension_ids),
            "selected_frame_count": self.selected_frame_count,
            "import_isolation_evidence_digest": self.import_isolation_evidence_digest,
            "import_isolation_verified": self.import_isolation_verified,
            "forbidden_imported_modules": list(self.forbidden_imported_modules),
            "forbidden_serialized_paths": list(self.forbidden_serialized_paths),
            "profile_contract_passed": self.profile_contract_passed,
            "data_lineage_passed": self.data_lineage_passed,
            "selection_materialized": self.selection_materialized,
            "passed": self.passed,
            "warnings": list(self.warnings),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossSystemQualificationCaseRecord":
        if payload.get("schema") != CROSS_SYSTEM_QUALIFICATION_CASE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported cross-system qualification-case schema.")
        result = cls(
            case_id=str(payload["case_id"]),
            case_kind=CrossSystemCaseKind(str(payload["case_kind"])),
            policy_digest=str(payload["policy_digest"]),
            material_profile_contracts_digest=str(payload["material_profile_contracts_digest"]),
            material_profile_digest=str(payload["material_profile_digest"]),
            phase_kinds=tuple(str(value) for value in payload["phase_kinds"]),
            geometry=str(payload["geometry"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            data6_bundle_digest=str(payload["data6_bundle_digest"]),
            data7_bundle_digest=str(payload["data7_bundle_digest"]),
            phase_geometry_plan_digest=str(payload["phase_geometry_plan_digest"]),
            enabled_feature_families=tuple(str(value) for value in payload["enabled_feature_families"]),
            enabled_event_types=tuple(str(value) for value in payload["enabled_event_types"]),
            profile_extension_ids=tuple(str(value) for value in payload["profile_extension_ids"]),
            selected_frame_count=int(payload["selected_frame_count"]),
            import_isolation_evidence_digest=str(payload["import_isolation_evidence_digest"]),
            import_isolation_verified=bool(payload["import_isolation_verified"]),
            forbidden_imported_modules=tuple(str(value) for value in payload["forbidden_imported_modules"]),
            forbidden_serialized_paths=tuple(str(value) for value in payload["forbidden_serialized_paths"]),
            profile_contract_passed=bool(payload["profile_contract_passed"]),
            data_lineage_passed=bool(payload["data_lineage_passed"]),
            selection_materialized=bool(payload["selection_materialized"]),
            passed=bool(payload["passed"]),
            warnings=tuple(str(value) for value in payload.get("warnings", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Cross-system qualification-case digest mismatch.")
        return result


def qualify_cross_system_case(
    case_id: str,
    case_kind: CrossSystemCaseKind,
    data4_bundle: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    data7_bundle: Any,
    *,
    policy: CrossSystemQualificationPolicy | None = None,
    import_isolation_evidence: ImportIsolationEvidence,
) -> CrossSystemQualificationCaseRecord:
    """Audit one bounded DATA4-DATA7 profile workflow.

    ``import_isolation_evidence`` must come from a clean-interpreter probe.
    """

    active = CrossSystemQualificationPolicy() if policy is None else policy
    kind = CrossSystemCaseKind(case_kind)
    contracts = getattr(data4_bundle, "material_profile_contracts", None)
    if contracts is None:
        raise TrainingDataInputError("Cross-system qualification requires explicit material-profile contracts.")
    plan = getattr(data6_bundle, "phase_geometry_profile_plan", None)
    if plan is None:
        raise TrainingDataInputError("Cross-system qualification requires a DATA6 phase/geometry plan.")

    data_lineage_passed = (
        data5_bundle.data4_bundle_digest == data4_bundle.content_digest
        and data6_bundle.data4_bundle_digest == data4_bundle.content_digest
        and data6_bundle.data5_bundle_digest == data5_bundle.content_digest
        and data7_bundle.data4_bundle_digest == data4_bundle.content_digest
        and data7_bundle.data5_bundle_digest == data5_bundle.content_digest
        and data7_bundle.data6_bundle_digest == data6_bundle.content_digest
        and plan.material_profile_contracts_digest == contracts.content_digest
    )
    extension_ids = _extension_ids(data4_bundle, data6_bundle)
    profile_contract_passed, profile_warnings = _expected_profile_passes(kind, contracts, extension_ids)

    if tuple(import_isolation_evidence.forbidden_module_prefixes) != tuple(active.forbidden_generic_module_prefixes):
        raise TrainingDataInputError("Import-isolation evidence uses a different forbidden-module policy.")
    forbidden_imports = import_isolation_evidence.forbidden_modules if kind is not CrossSystemCaseKind.LTA_EXTENSION else ()

    serialized_payloads = (data4_bundle.to_dict(), data6_bundle.to_dict(), data7_bundle.to_dict())
    keys = frozenset(active.forbidden_generic_serialized_keys)
    forbidden_paths = tuple(sorted({
        path for payload in serialized_payloads for path in _find_serialized_key_paths(payload, keys)
    }))

    selected_count = len(data7_bundle.selection_plan.master_order)
    selection_materialized = selected_count > 0 if active.require_data7_selection else True
    clean_import_passed = import_isolation_evidence.passed if active.require_clean_import_evidence else True
    warnings = list(profile_warnings)
    if not data_lineage_passed:
        warnings.append("data4_data7_lineage_mismatch")
    if not selection_materialized:
        warnings.append("data7_selection_not_materialized")
    if not clean_import_passed:
        warnings.append("clean_import_evidence_missing")
    if forbidden_imports:
        warnings.append("generic_path_imported_lta_modules")
    if forbidden_paths:
        warnings.append("generic_path_serialized_legacy_lta_fields")
    passed = (
        profile_contract_passed and data_lineage_passed and selection_materialized
        and clean_import_passed and not forbidden_imports and not forbidden_paths
    )
    return CrossSystemQualificationCaseRecord(
        case_id=case_id,
        case_kind=kind,
        policy_digest=active.content_digest,
        material_profile_contracts_digest=contracts.content_digest,
        material_profile_digest=contracts.profile.content_digest,
        phase_kinds=tuple(str(value) for value in plan.phase_kinds),
        geometry=plan.geometry.value,
        data4_bundle_digest=data4_bundle.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest,
        data7_bundle_digest=data7_bundle.content_digest,
        phase_geometry_plan_digest=plan.content_digest,
        enabled_feature_families=tuple(str(value) for value in plan.feature_families),
        enabled_event_types=tuple(str(value) for value in plan.event_types),
        profile_extension_ids=extension_ids,
        selected_frame_count=selected_count,
        import_isolation_evidence_digest=import_isolation_evidence.content_digest,
        import_isolation_verified=clean_import_passed,
        forbidden_imported_modules=forbidden_imports,
        forbidden_serialized_paths=forbidden_paths,
        profile_contract_passed=profile_contract_passed,
        data_lineage_passed=data_lineage_passed,
        selection_materialized=selection_materialized,
        passed=passed,
        warnings=tuple(warnings),
    )


@dataclass(frozen=True, slots=True)
class CrossSystemQualificationSuiteRecord:
    suite_id: str
    policy: CrossSystemQualificationPolicy
    cases: tuple[CrossSystemQualificationCaseRecord, ...]
    passed: bool
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.suite_id).strip():
            raise TrainingDataInputError("suite_id must be nonempty.")
        if not isinstance(self.policy, CrossSystemQualificationPolicy):
            raise TrainingDataInputError("policy has the wrong type.")
        cases = tuple(sorted(self.cases, key=lambda item: item.case_kind.value))
        kinds = tuple(item.case_kind for item in cases)
        if len(set(kinds)) != len(kinds):
            raise TrainingDataInputError("Cross-system suites require at most one record per case kind.")
        missing = set(self.policy.required_case_kinds) - set(kinds)
        if missing:
            raise TrainingDataInputError(
                "Cross-system suite is missing required cases: " + ", ".join(sorted(item.value for item in missing))
            )
        if any(item.policy_digest != self.policy.content_digest for item in cases):
            raise TrainingDataInputError("Cross-system cases do not share the suite policy.")
        object.__setattr__(self, "cases", cases)
        expected = all(item.passed for item in cases)
        if self.passed != expected:
            raise TrainingDataInputError("Cross-system suite passed flag disagrees with case evidence.")
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CROSS_SYSTEM_QUALIFICATION_SUITE_SCHEMA,
            "parser_version": MLFF_DATA9A7E_PARSER_VERSION,
            "suite_id": self.suite_id,
            "policy": self.policy.to_dict(),
            "cases": [item.to_dict() for item in self.cases],
            "passed": self.passed,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(canonical_json(self.to_dict()) + "\n", encoding="utf-8")
        return destination

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossSystemQualificationSuiteRecord":
        if payload.get("schema") != CROSS_SYSTEM_QUALIFICATION_SUITE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported cross-system qualification-suite schema.")
        result = cls(
            suite_id=str(payload["suite_id"]),
            policy=CrossSystemQualificationPolicy.from_dict(payload["policy"]),
            cases=tuple(CrossSystemQualificationCaseRecord.from_dict(item) for item in payload["cases"]),
            passed=bool(payload["passed"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Cross-system qualification-suite digest mismatch.")
        return result

    @classmethod
    def read_json(cls, path: str | Path) -> "CrossSystemQualificationSuiteRecord":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def build_cross_system_qualification_suite(
    suite_id: str,
    cases: Iterable[CrossSystemQualificationCaseRecord],
    *,
    policy: CrossSystemQualificationPolicy | None = None,
    notes: Iterable[str] = (),
) -> CrossSystemQualificationSuiteRecord:
    active = CrossSystemQualificationPolicy() if policy is None else policy
    records = tuple(cases)
    return CrossSystemQualificationSuiteRecord(
        suite_id=suite_id,
        policy=active,
        cases=records,
        passed=all(item.passed for item in records),
        notes=tuple(str(value) for value in notes),
    )
