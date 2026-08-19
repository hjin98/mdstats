"""Explicit named-energy selection for MLFF training labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from mdstats.io.source_controls import FrameEnergyCatalog

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

VASP_ENERGY_LABEL_POLICY_SCHEMA = "mdstats.vasp-energy-label-policy.v1"
SELECTED_ENERGY_CHANNEL_SCHEMA = "mdstats.selected-energy-channel.v1"
VASP_ENERGY_LABEL_POLICY_VERSION = "mdstats.mlff-data2.vasp-energy.2026-07.v1"


@dataclass(frozen=True, slots=True)
class VaspEnergyLabelPolicy:
    channel: str = "e_fr_energy"
    require_complete: bool = True
    derivative_consistency: str = "electronic_free_energy"
    output_key: str = "REF_energy"
    normalization: str = "total_per_cell"
    policy_version: str = VASP_ENERGY_LABEL_POLICY_VERSION

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.channel,
                self.derivative_consistency,
                self.output_key,
                self.normalization,
                self.policy_version,
            )
        ):
            raise TrainingDataInputError("Energy-label policy fields must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": VASP_ENERGY_LABEL_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "channel": self.channel,
            "require_complete": self.require_complete,
            "derivative_consistency": self.derivative_consistency,
            "output_key": self.output_key,
            "normalization": self.normalization,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VaspEnergyLabelPolicy":
        if payload.get("schema") != VASP_ENERGY_LABEL_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported VASP energy policy schema.")
        result = cls(
            channel=str(payload["channel"]),
            require_complete=bool(payload["require_complete"]),
            derivative_consistency=str(payload["derivative_consistency"]),
            output_key=str(payload["output_key"]),
            normalization=str(payload["normalization"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("VASP energy policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SelectedEnergyChannel:
    source_control_bundle_signature: str
    energy_catalog_signature: str
    policy_digest: str
    source_name: str
    semantic_role: str
    units: str
    source_path: str
    frame_count: int
    present_count: int
    completeness_fraction: float
    output_key: str
    normalization: str
    values_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "source_control_bundle_signature",
            "energy_catalog_signature",
            "policy_digest",
            "values_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.frame_count < 0 or not 0 <= self.present_count <= self.frame_count:
            raise TrainingDataInputError("Energy-channel counts are inconsistent.")
        if not 0.0 <= float(self.completeness_fraction) <= 1.0:
            raise TrainingDataInputError("Energy completeness must lie in [0, 1].")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SELECTED_ENERGY_CHANNEL_SCHEMA,
            "source_control_bundle_signature": self.source_control_bundle_signature,
            "energy_catalog_signature": self.energy_catalog_signature,
            "policy_digest": self.policy_digest,
            "source_name": self.source_name,
            "semantic_role": self.semantic_role,
            "units": self.units,
            "source_path": self.source_path,
            "frame_count": self.frame_count,
            "present_count": self.present_count,
            "completeness_fraction": self.completeness_fraction,
            "output_key": self.output_key,
            "normalization": self.normalization,
            "values_sha256": self.values_sha256,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectedEnergyChannel":
        if payload.get("schema") != SELECTED_ENERGY_CHANNEL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-energy schema.")
        result = cls(
            source_control_bundle_signature=str(payload["source_control_bundle_signature"]),
            energy_catalog_signature=str(payload["energy_catalog_signature"]),
            policy_digest=str(payload["policy_digest"]),
            source_name=str(payload["source_name"]),
            semantic_role=str(payload["semantic_role"]),
            units=str(payload["units"]),
            source_path=str(payload["source_path"]),
            frame_count=int(payload["frame_count"]),
            present_count=int(payload["present_count"]),
            completeness_fraction=float(payload["completeness_fraction"]),
            output_key=str(payload["output_key"]),
            normalization=str(payload["normalization"]),
            values_sha256=str(payload["values_sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Selected-energy digest mismatch.")
        return result


def select_vasp_energy_channel(
    energy_catalog: FrameEnergyCatalog,
    *,
    source_control_bundle_signature: str,
    policy: VaspEnergyLabelPolicy | None = None,
) -> SelectedEnergyChannel:
    active = VaspEnergyLabelPolicy() if policy is None else policy
    channel = energy_catalog.channel(active.channel)
    if channel is None:
        raise TrainingDataInputError(
            f"Required VASP energy channel {active.channel!r} is absent."
        )
    if active.require_complete and not channel.complete:
        raise TrainingDataInputError(
            f"VASP energy channel {active.channel!r} is incomplete: "
            f"{channel.present_count}/{channel.frame_count} frames."
        )
    if channel.semantic_role != active.derivative_consistency:
        raise TrainingDataInputError(
            "Selected energy semantic role is inconsistent with the declared "
            f"derivative surface: {channel.semantic_role!r} != "
            f"{active.derivative_consistency!r}."
        )
    return SelectedEnergyChannel(
        source_control_bundle_signature=source_control_bundle_signature,
        energy_catalog_signature=energy_catalog.signature,
        policy_digest=active.policy_digest,
        source_name=channel.source_name,
        semantic_role=channel.semantic_role,
        units=channel.units,
        source_path=channel.source_path,
        frame_count=channel.frame_count,
        present_count=channel.present_count,
        completeness_fraction=channel.completeness_fraction,
        output_key=active.output_key,
        normalization=active.normalization,
        values_sha256=channel.values_sha256,
    )
