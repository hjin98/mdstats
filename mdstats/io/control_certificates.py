"""Source-general Stage 11E-ENS1 control and provenance certificates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

from .source_controls import SourceControlError, SourceControlSerializationError

SIMULATION_CONTROL_COMPONENT_SCHEMA = "mdstats.simulation-control-component.v1"
SIMULATION_CONTROL_DECISION_SCHEMA = "mdstats.simulation-control-decision.v1"
SIMULATION_CONTROL_CERTIFICATE_SCHEMA = "mdstats.simulation-control-certificate.v1"
ENSEMBLE_INFERENCE_POLICY_VERSION = "mdstats.ensemble-inference-policy.v1"
CONTROL_CERTIFICATE_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class InferenceStatus(str, Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICTING = "conflicting"
    NOT_APPLICABLE = "not_applicable"


class EnsembleKind(str, Enum):
    NVE = "NVE"
    NVT = "NVT"
    NPT = "NpT"
    NPH = "NpH"
    TEMPERATURE_RAMP = "temperature_ramp"
    CONSTANT_VELOCITY_PATH = "constant_velocity_path"
    MULTI_THERMOSTAT = "multi_thermostat"
    NON_EQUILIBRIUM_DRIVEN = "non_equilibrium_driven"
    UNKNOWN = "unknown"


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


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list)):
        return [_json_value(v) for v in value]
    raise SourceControlError(f"Unsupported certificate value {type(value).__name__}.")


def _tuple_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuple_value(v) for v in value)
    if isinstance(value, dict):
        return tuple((str(k), _tuple_value(v)) for k, v in sorted(value.items()))
    return value


@dataclass(frozen=True, slots=True)
class SimulationControlComponent:
    """One resolved, unresolved, conflicting, or inapplicable ENS1 component."""

    status: InferenceStatus
    kind: str
    active: bool | None
    parameters: tuple[tuple[str, Any], ...] = ()
    evidence: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", InferenceStatus(self.status))
        if not self.kind:
            raise SourceControlError("Control component kind must be non-empty.")
        object.__setattr__(
            self,
            "parameters",
            tuple(
                sorted(
                    (str(name), _tuple_value(_json_value(value)))
                    for name, value in self.parameters
                )
            ),
        )
        object.__setattr__(self, "evidence", tuple(str(v) for v in self.evidence))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def parameter(self, name: str, default: Any = None) -> Any:
        return dict(self.parameters).get(name, default)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SIMULATION_CONTROL_COMPONENT_SCHEMA,
            "status": self.status.value,
            "kind": self.kind,
            "active": self.active,
            "parameters": {name: _json_value(value) for name, value in self.parameters},
            "evidence": list(self.evidence),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SimulationControlComponent":
        if payload.get("schema") not in (None, SIMULATION_CONTROL_COMPONENT_SCHEMA):
            raise SourceControlSerializationError(
                "Unsupported simulation-control-component schema."
            )
        return cls(
            status=InferenceStatus(payload["status"]),
            kind=str(payload["kind"]),
            active=None if payload.get("active") is None else bool(payload["active"]),
            parameters=tuple(
                (str(name), _tuple_value(value))
                for name, value in payload.get("parameters", {}).items()
            ),
            evidence=tuple(str(v) for v in payload.get("evidence", ())),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )


@dataclass(frozen=True, slots=True)
class SimulationControlDecision:
    rule_id: str
    outcome: str
    evidence: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id or not self.outcome:
            raise SourceControlError("Decision rule_id and outcome must be non-empty.")
        object.__setattr__(self, "evidence", tuple(str(v) for v in self.evidence))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SIMULATION_CONTROL_DECISION_SCHEMA,
            "rule_id": self.rule_id,
            "outcome": self.outcome,
            "evidence": list(self.evidence),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SimulationControlDecision":
        return cls(
            rule_id=str(payload["rule_id"]),
            outcome=str(payload["outcome"]),
            evidence=tuple(str(v) for v in payload.get("evidence", ())),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )


@dataclass(frozen=True, slots=True)
class SimulationControlCertificate:
    """Signed ENS1 interpretation of one immutable ENS0 source bundle."""

    source_identity_signature: str
    source_control_bundle_signature: str
    run_controls_signature: str
    policy_version: str
    dynamics_status: InferenceStatus
    dynamics_mode: str
    ensemble_status: InferenceStatus
    ensemble: EnsembleKind
    propagator: SimulationControlComponent
    thermostat: SimulationControlComponent
    barostat: SimulationControlComponent
    cell_control: SimulationControlComponent
    bias: SimulationControlComponent
    constraints: SimulationControlComponent
    force_provenance: SimulationControlComponent
    initial_velocity_provenance: SimulationControlComponent
    continuation_provenance: SimulationControlComponent
    decisions: tuple[SimulationControlDecision, ...]
    unresolved_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature",
            "source_control_bundle_signature",
            "run_controls_signature",
        ):
            if len(getattr(self, name)) != 64:
                raise SourceControlError(f"{name} must be a SHA-256 digest.")
        if not self.policy_version or not self.dynamics_mode:
            raise SourceControlError("Policy version and dynamics mode must be non-empty.")
        object.__setattr__(self, "dynamics_status", InferenceStatus(self.dynamics_status))
        object.__setattr__(self, "ensemble_status", InferenceStatus(self.ensemble_status))
        object.__setattr__(self, "ensemble", EnsembleKind(self.ensemble))
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(
            self, "unresolved_reasons", tuple(str(v) for v in self.unresolved_reasons)
        )
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))

    @property
    def ensemble_dependent_methods_permitted(self) -> bool:
        return (
            self.dynamics_status is InferenceStatus.RESOLVED
            and self.ensemble_status is InferenceStatus.RESOLVED
            and self.ensemble is not EnsembleKind.UNKNOWN
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SIMULATION_CONTROL_CERTIFICATE_SCHEMA,
            "digest_algorithm": CONTROL_CERTIFICATE_DIGEST_ALGORITHM,
            "source_identity_signature": self.source_identity_signature,
            "source_control_bundle_signature": self.source_control_bundle_signature,
            "run_controls_signature": self.run_controls_signature,
            "policy_version": self.policy_version,
            "dynamics_status": self.dynamics_status.value,
            "dynamics_mode": self.dynamics_mode,
            "ensemble_status": self.ensemble_status.value,
            "ensemble": self.ensemble.value,
            "propagator": self.propagator.to_dict(),
            "thermostat": self.thermostat.to_dict(),
            "barostat": self.barostat.to_dict(),
            "cell_control": self.cell_control.to_dict(),
            "bias": self.bias.to_dict(),
            "constraints": self.constraints.to_dict(),
            "force_provenance": self.force_provenance.to_dict(),
            "initial_velocity_provenance": self.initial_velocity_provenance.to_dict(),
            "continuation_provenance": self.continuation_provenance.to_dict(),
            "decisions": [item.to_dict() for item in self.decisions],
            "unresolved_reasons": list(self.unresolved_reasons),
            "warnings": list(self.warnings),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SimulationControlCertificate":
        if payload.get("schema") != SIMULATION_CONTROL_CERTIFICATE_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported simulation-control-certificate schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            source_control_bundle_signature=str(payload["source_control_bundle_signature"]),
            run_controls_signature=str(payload["run_controls_signature"]),
            policy_version=str(payload["policy_version"]),
            dynamics_status=InferenceStatus(payload["dynamics_status"]),
            dynamics_mode=str(payload["dynamics_mode"]),
            ensemble_status=InferenceStatus(payload["ensemble_status"]),
            ensemble=EnsembleKind(payload["ensemble"]),
            propagator=SimulationControlComponent.from_dict(payload["propagator"]),
            thermostat=SimulationControlComponent.from_dict(payload["thermostat"]),
            barostat=SimulationControlComponent.from_dict(payload["barostat"]),
            cell_control=SimulationControlComponent.from_dict(payload["cell_control"]),
            bias=SimulationControlComponent.from_dict(payload["bias"]),
            constraints=SimulationControlComponent.from_dict(payload["constraints"]),
            force_provenance=SimulationControlComponent.from_dict(payload["force_provenance"]),
            initial_velocity_provenance=SimulationControlComponent.from_dict(
                payload["initial_velocity_provenance"]
            ),
            continuation_provenance=SimulationControlComponent.from_dict(
                payload["continuation_provenance"]
            ),
            decisions=tuple(
                SimulationControlDecision.from_dict(item)
                for item in payload.get("decisions", ())
            ),
            unresolved_reasons=tuple(str(v) for v in payload.get("unresolved_reasons", ())),
            warnings=tuple(str(v) for v in payload.get("warnings", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Simulation control certificate signature mismatch."
            )
        return result


__all__ = [
    "CONTROL_CERTIFICATE_DIGEST_ALGORITHM",
    "ENSEMBLE_INFERENCE_POLICY_VERSION",
    "SIMULATION_CONTROL_CERTIFICATE_SCHEMA",
    "SIMULATION_CONTROL_COMPONENT_SCHEMA",
    "SIMULATION_CONTROL_DECISION_SCHEMA",
    "EnsembleKind",
    "InferenceStatus",
    "SimulationControlCertificate",
    "SimulationControlComponent",
    "SimulationControlDecision",
]
