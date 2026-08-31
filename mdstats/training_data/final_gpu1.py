"""FINAL-GPU1 release-handoff evidence and qualification reducer.

This module does not launch GPU work itself.  It defines the immutable final-
release matrix, content-addressed evidence records, and the fail-closed reducer
used by the external FINAL-GPU1 harness.  Accelerator execution remains an
explicit workstation action; absent evidence is never converted into success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .accelerator_runtime_freeze import CueqDep1RuntimeRecord
from .perf_cert1 import PerfCert1QualificationRecord

FINAL_GPU1_POLICY_SCHEMA = "mdstats.final-gpu1-policy.target-size-v5.v4"
FINAL_GPU1_EVIDENCE_SCHEMA = "mdstats.final-gpu1-evidence.v1"
FINAL_GPU1_QUALIFICATION_SCHEMA = "mdstats.final-gpu1-qualification.target-size-v5.v4"
FINAL_GPU1_VERSION = "mdstats.final-gpu1.release-handoff.target-size-v5.2026-08.v4"

ACCEPT_MUST_PASS = "must_pass"
ACCEPT_MEASURE_ONLY = "measure_only"
ACCEPT_OPTIONAL = "optional"
_ALLOWED_ACCEPTANCE = {ACCEPT_MUST_PASS, ACCEPT_MEASURE_ONLY, ACCEPT_OPTIONAL}
_ALLOWED_DISPOSITIONS = {"pass", "fail", "pending", "superseded", "not_applicable"}

FINAL_GPU1_REQUIRED_PASS_GATES = (
    "CUEQ_DEP1_RUNTIME_FREEZE",
    "E3NN_BASELINE_COMPLETE_CAMPAIGN",
    "SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION",
    "PERF_P2R_WHOLE_FUNNEL_GPU_PERFORMANCE",
    "VRAM1_PERF_P4_ACCELERATOR_MEMORY_THROUGHPUT",
    "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION",
    "REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION",
    "PERF_CERT1_END_TO_END_CERTIFICATION",
)

FINAL_GPU1_MEASURE_ONLY_GATES = (
    "PREC3_REAL_CUEQ_ACTIVATION",
    "MH1_ACCEL1_CUEQ_NUMERICAL_PARITY",
    "MH1_DATA6_1_CUEQ_DESCRIPTOR_SELECTION_PARITY",
    "MH1_TRAIN1_CUEQ_TRAINING_REALIZATION",
    "MH1_CERT1_GENERATED_DEFAULT_CUEQ_MATRIX",
    "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE",
)

FINAL_GPU1_OPTIONAL_GATES = (
    "CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL",
    "MH1_DEPLOY1_MLIAP_EXPORT_AND_LAMMPS_RUN0",
)

# Evidence from these gates is meaningful only relative to one exact CuEq
# runtime freeze.  Optional PHASE2 may be absent entirely, but if it is
# registered its runtime identity must match the release-authorizing freeze.
FINAL_GPU1_RUNTIME_BOUND_GATES = (
    "CUEQ_DEP1_RUNTIME_FREEZE",
    "PREC3_REAL_CUEQ_ACTIVATION",
    "MH1_ACCEL1_CUEQ_NUMERICAL_PARITY",
    "MH1_DATA6_1_CUEQ_DESCRIPTOR_SELECTION_PARITY",
    "MH1_TRAIN1_CUEQ_TRAINING_REALIZATION",
    "MH1_CERT1_GENERATED_DEFAULT_CUEQ_MATRIX",
    "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION",
    "CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL",
    "REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION",
    "PERF_CERT1_END_TO_END_CERTIFICATION",
)

FINAL_GPU1_LOCKED_FOUNDATION_SHA256 = {
    "mace_mh_1": "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde",
    "mace_mpa_0": "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638",
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class FinalGpu1Policy:
    """Immutable FINAL-GPU1 acceptance matrix.

    ``must_pass`` gates block release on a negative or missing result.
    ``measure_only`` gates must produce content-addressed evidence, but a negative
    optimization result is admissible when the corresponding optimization remains
    disabled or has been superseded by the phase-separated authority.
    ``optional`` gates never block the core final release.
    """

    required_pass_gates: tuple[str, ...] = FINAL_GPU1_REQUIRED_PASS_GATES
    measure_only_gates: tuple[str, ...] = FINAL_GPU1_MEASURE_ONLY_GATES
    optional_gates: tuple[str, ...] = FINAL_GPU1_OPTIONAL_GATES
    runtime_bound_gates: tuple[str, ...] = FINAL_GPU1_RUNTIME_BOUND_GATES
    require_single_cueq_runtime: bool = True
    require_release_artifact_binding: bool = True
    generated_default_change_authorized: bool = False
    authority_version: str = FINAL_GPU1_VERSION

    def __post_init__(self) -> None:
        groups = tuple(tuple(str(v).strip() for v in group) for group in (
            self.required_pass_gates, self.measure_only_gates, self.optional_gates
        ))
        if any(not value for group in groups for value in group):
            raise TrainingDataInputError("FINAL-GPU1 gate IDs must be non-empty.")
        flattened = [value for group in groups for value in group]
        if len(flattened) != len(set(flattened)):
            raise TrainingDataInputError("FINAL-GPU1 gate IDs must be unique across acceptance classes.")
        if self.generated_default_change_authorized:
            raise TrainingDataInputError(
                "FINAL-GPU1 cannot directly authorize a generated-default change; a later policy revision is required."
            )
        if self.authority_version != FINAL_GPU1_VERSION:
            raise TrainingDataInputError("Unsupported stale FINAL-GPU1 authority version; rebuild for the current target-size generation.")
        if groups[0] != FINAL_GPU1_REQUIRED_PASS_GATES:
            raise TrainingDataInputError("FINAL-GPU1 v4 required-pass matrix changed.")
        object.__setattr__(self, "required_pass_gates", groups[0])
        object.__setattr__(self, "measure_only_gates", groups[1])
        object.__setattr__(self, "optional_gates", groups[2])
        runtime_bound = tuple(str(v).strip() for v in self.runtime_bound_gates)
        if any(not value for value in runtime_bound):
            raise TrainingDataInputError("FINAL-GPU1 runtime-bound gate IDs must be non-empty.")
        if len(runtime_bound) != len(set(runtime_bound)):
            raise TrainingDataInputError("FINAL-GPU1 runtime-bound gate IDs must be unique.")
        unknown_runtime = sorted(set(runtime_bound) - set(flattened))
        if unknown_runtime:
            raise TrainingDataInputError(
                "FINAL-GPU1 runtime-bound gates must belong to the acceptance matrix: "
                + ", ".join(unknown_runtime)
            )
        object.__setattr__(self, "runtime_bound_gates", runtime_bound)

    def acceptance_for(self, gate_id: str) -> str:
        gate = str(gate_id)
        if gate in self.required_pass_gates:
            return ACCEPT_MUST_PASS
        if gate in self.measure_only_gates:
            return ACCEPT_MEASURE_ONLY
        if gate in self.optional_gates:
            return ACCEPT_OPTIONAL
        raise TrainingDataInputError(f"Unknown FINAL-GPU1 gate {gate!r}.")

    @property
    def all_gates(self) -> tuple[str, ...]:
        return self.required_pass_gates + self.measure_only_gates + self.optional_gates

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_GPU1_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "required_pass_gates": list(self.required_pass_gates),
            "measure_only_gates": list(self.measure_only_gates),
            "optional_gates": list(self.optional_gates),
            "runtime_bound_gates": list(self.runtime_bound_gates),
            "require_single_cueq_runtime": self.require_single_cueq_runtime,
            "require_release_artifact_binding": self.require_release_artifact_binding,
            "generated_default_change_authorized": self.generated_default_change_authorized,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalGpu1Policy":
        if payload.get("schema") != FINAL_GPU1_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported stale FINAL-GPU1 policy schema; rebuild for the current target-size generation.")
        if str(payload.get("authority_version")) != FINAL_GPU1_VERSION:
            raise TrainingDataSerializationError("FINAL-GPU1 policy schema/version mismatch.")
        result = cls(
            required_pass_gates=tuple(str(v) for v in payload["required_pass_gates"]),
            measure_only_gates=tuple(str(v) for v in payload["measure_only_gates"]),
            optional_gates=tuple(str(v) for v in payload["optional_gates"]),
            runtime_bound_gates=tuple(str(v) for v in payload.get("runtime_bound_gates", FINAL_GPU1_RUNTIME_BOUND_GATES)),
            require_single_cueq_runtime=bool(payload.get("require_single_cueq_runtime", True)),
            require_release_artifact_binding=bool(payload.get("require_release_artifact_binding", True)),
            generated_default_change_authorized=bool(payload.get("generated_default_change_authorized", False)),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("FINAL-GPU1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FinalGpu1EvidenceRecord:
    """Content-addressed evidence registration for one matrix item."""

    gate_id: str
    acceptance: str
    disposition: str
    release_artifact_sha256: str
    evidence_sha256: str | None = None
    evidence_schema: str | None = None
    evidence_content_digest: str | None = None
    cueq_dep1_runtime_digest: str | None = None
    evidence_relative_path: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        gate = str(self.gate_id).strip()
        acceptance = str(self.acceptance).strip()
        disposition = str(self.disposition).strip()
        if not gate:
            raise TrainingDataInputError("FINAL-GPU1 evidence gate_id is required.")
        if acceptance not in _ALLOWED_ACCEPTANCE:
            raise TrainingDataInputError("Invalid FINAL-GPU1 acceptance class.")
        if disposition not in _ALLOWED_DISPOSITIONS:
            raise TrainingDataInputError("Invalid FINAL-GPU1 evidence disposition.")
        object.__setattr__(self, "gate_id", gate)
        object.__setattr__(self, "acceptance", acceptance)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "release_artifact_sha256", validate_digest(self.release_artifact_sha256, name="release_artifact_sha256"))
        for name in ("evidence_sha256", "evidence_content_digest", "cueq_dep1_runtime_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if disposition in {"pass", "fail", "superseded"} and self.evidence_sha256 is None:
            raise TrainingDataInputError(
                f"FINAL-GPU1 {disposition} evidence requires a content-addressed evidence file."
            )
        if disposition == "pass" and self.evidence_schema is None:
            raise TrainingDataInputError("Passing FINAL-GPU1 evidence requires an evidence schema.")
        if acceptance == ACCEPT_MUST_PASS and disposition in {"superseded", "not_applicable"}:
            raise TrainingDataInputError("Release-blocking FINAL-GPU1 gates cannot be superseded or not-applicable.")

    @property
    def evidence_present(self) -> bool:
        return self.evidence_sha256 is not None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_GPU1_EVIDENCE_SCHEMA,
            "gate_id": self.gate_id,
            "acceptance": self.acceptance,
            "disposition": self.disposition,
            "release_artifact_sha256": self.release_artifact_sha256,
            "evidence_sha256": self.evidence_sha256,
            "evidence_schema": self.evidence_schema,
            "evidence_content_digest": self.evidence_content_digest,
            "cueq_dep1_runtime_digest": self.cueq_dep1_runtime_digest,
            "evidence_relative_path": self.evidence_relative_path,
            "note": self.note,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalGpu1EvidenceRecord":
        if payload.get("schema") != FINAL_GPU1_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported FINAL-GPU1 evidence schema.")
        result = cls(
            gate_id=str(payload["gate_id"]),
            acceptance=str(payload["acceptance"]),
            disposition=str(payload["disposition"]),
            release_artifact_sha256=str(payload["release_artifact_sha256"]),
            evidence_sha256=None if payload.get("evidence_sha256") is None else str(payload["evidence_sha256"]),
            evidence_schema=None if payload.get("evidence_schema") is None else str(payload["evidence_schema"]),
            evidence_content_digest=None if payload.get("evidence_content_digest") is None else str(payload["evidence_content_digest"]),
            cueq_dep1_runtime_digest=None if payload.get("cueq_dep1_runtime_digest") is None else str(payload["cueq_dep1_runtime_digest"]),
            evidence_relative_path=None if payload.get("evidence_relative_path") is None else str(payload["evidence_relative_path"]),
            note=None if payload.get("note") is None else str(payload["note"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("FINAL-GPU1 evidence digest mismatch.")
        return result

    @classmethod
    def from_json_file(
        cls,
        *,
        gate_id: str,
        acceptance: str,
        disposition: str,
        release_artifact_sha256: str,
        evidence_path: Path,
        cueq_dep1_runtime_digest: str | None = None,
        evidence_relative_path: str | None = None,
        note: str | None = None,
    ) -> "FinalGpu1EvidenceRecord":
        path = Path(evidence_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise TrainingDataInputError("FINAL-GPU1 JSON evidence must contain an object.")
        content = payload.get("content_digest")
        return cls(
            gate_id=gate_id,
            acceptance=acceptance,
            disposition=disposition,
            release_artifact_sha256=release_artifact_sha256,
            evidence_sha256=_sha256_file(path),
            evidence_schema=None if payload.get("schema") is None else str(payload.get("schema")),
            evidence_content_digest=None if content is None else str(content),
            cueq_dep1_runtime_digest=cueq_dep1_runtime_digest,
            evidence_relative_path=evidence_relative_path,
            note=note,
        )


@dataclass(frozen=True, slots=True)
class FinalGpu1QualificationRecord:
    """Final release reducer for one complete GPU qualification handoff."""

    policy: FinalGpu1Policy
    release_artifact_sha256: str
    foundation_model_sha256: tuple[tuple[str, str], ...]
    cueq_dep1_runtime: CueqDep1RuntimeRecord
    perf_cert1: PerfCert1QualificationRecord | None = None
    evidence: tuple[FinalGpu1EvidenceRecord, ...] = ()
    handoff_integrity_failures: tuple[str, ...] = ()
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        release_digest = validate_digest(self.release_artifact_sha256, name="release_artifact_sha256")
        object.__setattr__(self, "release_artifact_sha256", release_digest)
        foundations = tuple((str(k), validate_digest(v, name=f"foundation_model_sha256:{k}")) for k, v in self.foundation_model_sha256)
        if len({key for key, _ in foundations}) != len(foundations):
            raise TrainingDataInputError("FINAL-GPU1 foundation model keys must be unique.")
        object.__setattr__(self, "foundation_model_sha256", foundations)
        evidence = tuple(self.evidence)
        if len({item.gate_id for item in evidence}) != len(evidence):
            raise TrainingDataInputError("FINAL-GPU1 evidence may contain at most one record per gate.")
        for item in evidence:
            expected = self.policy.acceptance_for(item.gate_id)
            if item.acceptance != expected:
                raise TrainingDataInputError(f"FINAL-GPU1 evidence acceptance mismatch for {item.gate_id}.")
        object.__setattr__(self, "evidence", evidence)
        integrity_failures = tuple(str(v).strip() for v in self.handoff_integrity_failures if str(v).strip())
        object.__setattr__(self, "handoff_integrity_failures", integrity_failures)

        reasons: list[str] = [f"handoff_integrity:{value}" for value in integrity_failures]
        foundation_map = dict(foundations)
        for key, expected in FINAL_GPU1_LOCKED_FOUNDATION_SHA256.items():
            if foundation_map.get(key) != expected:
                reasons.append(f"locked_foundation_model_identity:{key}")
        if not self.cueq_dep1_runtime.passed:
            reasons.append("CUEQ_DEP1_RUNTIME_FREEZE")
        runtime_digest = self.cueq_dep1_runtime.content_digest
        by_gate = {item.gate_id: item for item in evidence}
        for gate in self.policy.required_pass_gates:
            item = by_gate.get(gate)
            if item is None:
                reasons.append(f"missing_required_evidence:{gate}")
                continue
            if item.disposition != "pass":
                reasons.append(f"required_gate_not_passed:{gate}")
        for gate in self.policy.measure_only_gates:
            item = by_gate.get(gate)
            if item is None:
                reasons.append(f"missing_measurement_evidence:{gate}")
            elif item.disposition == "pending":
                reasons.append(f"measurement_pending:{gate}")
            elif not item.evidence_present:
                reasons.append(f"measurement_evidence_not_content_addressed:{gate}")
        if self.policy.require_release_artifact_binding:
            for item in evidence:
                if item.release_artifact_sha256 != release_digest:
                    reasons.append(f"release_artifact_identity:{item.gate_id}")
        if self.policy.require_single_cueq_runtime:
            for gate in self.policy.runtime_bound_gates:
                item = by_gate.get(gate)
                if item is not None and item.disposition != "pending" and item.cueq_dep1_runtime_digest is None:
                    reasons.append(f"cueq_runtime_binding_missing:{gate}")
            for item in evidence:
                if item.cueq_dep1_runtime_digest is not None and item.cueq_dep1_runtime_digest != runtime_digest:
                    reasons.append(f"cueq_runtime_identity:{item.gate_id}")
        runtime_gate = by_gate.get("CUEQ_DEP1_RUNTIME_FREEZE")
        if runtime_gate is not None and runtime_gate.evidence_content_digest != runtime_digest:
            reasons.append("CUEQ_DEP1_evidence_identity")
        perf_gate = by_gate.get("PERF_CERT1_END_TO_END_CERTIFICATION")
        if self.perf_cert1 is None:
            reasons.append("PERF_CERT1_qualification_record_missing")
        else:
            if not self.perf_cert1.passed:
                reasons.append("PERF_CERT1_END_TO_END_CERTIFICATION")
            if self.perf_cert1.upstream.cueq_dep1_runtime_digest != runtime_digest:
                reasons.append("PERF_CERT1_cueq_runtime_identity")
            phase1_gate = by_gate.get("CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION")
            if phase1_gate is not None and phase1_gate.evidence_content_digest != self.perf_cert1.upstream.cueq_phase1_qualification_digest:
                reasons.append("CUEQ_PHASE1_evidence_identity")
            phase2_gate = by_gate.get("CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL")
            if phase2_gate is not None and phase2_gate.evidence_content_digest != self.perf_cert1.upstream.cueq_phase2_qualification_digest:
                reasons.append("CUEQ_PHASE2_evidence_identity")
            if perf_gate is not None and perf_gate.evidence_content_digest != self.perf_cert1.content_digest:
                reasons.append("PERF_CERT1_evidence_identity")

        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def generated_default_change_authorized(self) -> bool:
        return False

    @property
    def generated_default_policy_revision_required(self) -> bool:
        return bool(
            self.passed
            and self.perf_cert1 is not None
            and self.perf_cert1.generated_default_policy_revision_required
        )

    @property
    def recommended_profile_id(self) -> str | None:
        return None if self.perf_cert1 is None else self.perf_cert1.recommended_profile_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_GPU1_QUALIFICATION_SCHEMA,
            "authority_version": self.policy.authority_version,
            "policy": self.policy.to_dict(),
            "release_artifact_sha256": self.release_artifact_sha256,
            "foundation_model_sha256": {k: v for k, v in self.foundation_model_sha256},
            "cueq_dep1_runtime": self.cueq_dep1_runtime.to_dict(),
            "perf_cert1": None if self.perf_cert1 is None else self.perf_cert1.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "handoff_integrity_failures": list(self.handoff_integrity_failures),
            "blocking_reasons": list(self.blocking_reasons),
            "passed": self.passed,
            "authorization": {
                "recommended_profile_id": self.recommended_profile_id,
                "generated_default_change_authorized": self.generated_default_change_authorized,
                "generated_default_policy_revision_required": self.generated_default_policy_revision_required,
            },
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalGpu1QualificationRecord":
        if payload.get("schema") != FINAL_GPU1_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported stale FINAL-GPU1 qualification schema; rebuild for the current target-size generation.")
        if payload.get("authority_version") != FINAL_GPU1_VERSION:
            raise TrainingDataSerializationError("Unsupported FINAL-GPU1 qualification authority version.")
        foundations = payload.get("foundation_model_sha256", {})
        result = cls(
            policy=FinalGpu1Policy.from_dict(payload["policy"]),
            release_artifact_sha256=str(payload["release_artifact_sha256"]),
            foundation_model_sha256=tuple((str(k), str(v)) for k, v in sorted(foundations.items())),
            cueq_dep1_runtime=CueqDep1RuntimeRecord.from_dict(payload["cueq_dep1_runtime"]),
            perf_cert1=None if payload.get("perf_cert1") is None else PerfCert1QualificationRecord.from_dict(payload["perf_cert1"]),
            evidence=tuple(FinalGpu1EvidenceRecord.from_dict(v) for v in payload.get("evidence", ())),
            handoff_integrity_failures=tuple(str(v) for v in payload.get("handoff_integrity_failures", ())),
        )
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("FINAL-GPU1 qualification blockers mismatch.")
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("FINAL-GPU1 qualification pass state mismatch.")
        if payload.get("authorization", {}) not in ({}, result._payload()["authorization"]):
            raise TrainingDataSerializationError("FINAL-GPU1 qualification authorization mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("FINAL-GPU1 qualification digest mismatch.")
        return result


def build_final_gpu1_qualification(
    *,
    release_artifact_sha256: str,
    foundation_model_sha256: Mapping[str, str],
    cueq_dep1_runtime: CueqDep1RuntimeRecord,
    perf_cert1: PerfCert1QualificationRecord | None,
    evidence: Sequence[FinalGpu1EvidenceRecord] = (),
    policy: FinalGpu1Policy | None = None,
    handoff_integrity_failures: Sequence[str] = (),
) -> FinalGpu1QualificationRecord:
    return FinalGpu1QualificationRecord(
        policy=policy or FinalGpu1Policy(),
        release_artifact_sha256=release_artifact_sha256,
        foundation_model_sha256=tuple(sorted((str(k), str(v)) for k, v in foundation_model_sha256.items())),
        cueq_dep1_runtime=cueq_dep1_runtime,
        perf_cert1=perf_cert1,
        evidence=tuple(evidence),
        handoff_integrity_failures=tuple(str(v) for v in handoff_integrity_failures),
    )
