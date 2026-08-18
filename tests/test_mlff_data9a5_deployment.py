from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys
import types

import pytest
import torch

try:
    import mdstats as _mdstats
except ModuleNotFoundError as exc:
    if exc.name != "ase":
        raise
    ROOT = Path(__file__).resolve().parents[1]
    package = types.ModuleType("mdstats")
    package.__path__ = [str(ROOT / "mdstats")]
    sys.modules["mdstats"] = package
    training = types.ModuleType("mdstats.training_data")
    training.__path__ = [str(ROOT / "mdstats" / "training_data")]
    sys.modules["mdstats.training_data"] = training
    from mdstats.training_data import mace_deployment as _mdstats


class _Toy(torch.nn.Module):
    def __init__(self, dtype: torch.dtype) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(3, 2, dtype=dtype)
        self.register_buffer("scale", torch.tensor([1.5, 0.5], dtype=dtype))
        self.register_buffer("indices", torch.arange(2, dtype=torch.int64))
        with torch.no_grad():
            self.linear.weight.copy_(
                torch.tensor([[0.25, -0.5, 0.75], [1.0, 0.125, -0.25]], dtype=dtype)
            )
            self.linear.bias.copy_(torch.tensor([0.1, -0.2], dtype=dtype))

    def forward(self, values: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"prediction": self.linear(values) * self.scale}



class _Mixed(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fp32 = torch.nn.Parameter(torch.ones(2, dtype=torch.float32))
        self.fp64 = torch.nn.Parameter(torch.ones(2, dtype=torch.float64))

def _save(path: Path, dtype: torch.dtype) -> None:
    torch.save(_Toy(dtype), path)


def _probe(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    dtype = next(model.parameters()).dtype
    values = torch.tensor([[0.2, -0.4, 0.8], [1.0, 0.5, -0.25]], dtype=dtype)
    return model(values)



def _gradient_probe(model: torch.nn.Module) -> dict[str, torch.Tensor]:
    dtype = next(model.parameters()).dtype
    values = torch.tensor([[0.2, -0.4, 0.8]], dtype=dtype, requires_grad=True)
    prediction = model(values)["prediction"]
    energy = prediction.sum()
    force = -torch.autograd.grad(energy, values, create_graph=False)[0]
    return {"energy": energy, "force": force}

def test_deployment_policy_round_trip_and_rejects_invalid_dtype() -> None:
    policy = _mdstats.MaceDeploymentExportPolicy(deployment_dtype="float32")
    assert _mdstats.MaceDeploymentExportPolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(_mdstats.TrainingDataInputError):
        _mdstats.MaceDeploymentExportPolicy(deployment_dtype="float16")



def test_inference_probe_supports_autograd_for_force_like_outputs(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    artifact = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "deployment",
        deployment_dtype="float32",
        training_dtype="float64",
        inference_probe=_gradient_probe,
    )
    assert artifact.inference_qualified
    names = {metric[0] for metric in artifact.inference_comparison.output_metrics}
    assert names == {"output.energy", "output.force"}


def test_fp64_to_fp32_export_is_exact_reloaded_and_manifested(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    source_bytes = source.read_bytes()

    artifact = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "deployment",
        deployment_dtype="float32",
        training_dtype="float64",
        target_head="target_head",
        precision_transition_digest="a" * 64,
        inference_probe=_probe,
    )

    assert artifact.passed
    assert artifact.conversion_kind == "demotion_float64_to_float32"
    assert artifact.deployment_precision.uniform_floating_dtype == "float32"
    assert artifact.state_conversion_exact
    assert artifact.inference_qualified
    assert not artifact.precision_recovery_claimed
    assert not artifact.downstream_runtime_precision_claimed
    assert not artifact.byte_determinism_claimed
    assert source.read_bytes() == source_bytes

    output = tmp_path / "deployment" / artifact.deployment_relative_path
    manifest = tmp_path / "deployment" / artifact.manifest_relative_path
    assert output.is_file()
    assert manifest.is_file()
    restored = _mdstats.MaceDeploymentArtifact.from_dict(json.loads(manifest.read_text()))
    assert restored == artifact


def test_fp32_to_fp64_is_labeled_as_promotion_without_precision_recovery(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float32)
    artifact = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "deployment",
        deployment_dtype="float64",
        training_dtype="float32",
        inference_probe=_probe,
    )
    assert artifact.conversion_kind == "promotion_float32_to_float64"
    assert artifact.deployment_precision.uniform_floating_dtype == "float64"
    assert "float32_to_float64_promotion_does_not_restore_lost_precision" in artifact.notes
    assert not artifact.precision_recovery_claimed


def test_deterministic_conversion_has_identical_semantic_state_digests(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    first = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "one",
        deployment_dtype="float32",
        training_dtype="float64",
        filename="model.model",
        inference_probe=_probe,
    )
    second = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "two",
        deployment_dtype="float32",
        training_dtype="float64",
        filename="model.model",
        inference_probe=_probe,
    )
    assert first.deployment_state_sha256 == second.deployment_state_sha256
    assert first.inference_comparison == second.inference_comparison


def test_export_requires_probe_by_default_and_rejects_mixed_source(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    with pytest.raises(_mdstats.TrainingDataInputError, match="inference probe"):
        _mdstats.export_mace_deployment_artifact(
            source,
            tmp_path / "missing_probe",
            deployment_dtype="float32",
        )

    mixed = tmp_path / "mixed.model"
    torch.save(_Mixed(), mixed)
    with pytest.raises(_mdstats.TrainingDataInputError, match="not deployable"):
        _mdstats.export_mace_deployment_artifact(
            mixed,
            tmp_path / "mixed_output",
            deployment_dtype="float32",
            inference_probe=lambda model: next(model.parameters()),
        )



def test_structural_only_policy_is_explicitly_not_inference_qualified(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    policy = _mdstats.MaceDeploymentExportPolicy(
        deployment_dtype="float32", require_inference_probe=False
    )
    artifact = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "deployment",
        deployment_dtype="float32",
        policy=policy,
    )
    assert artifact.passed
    assert artifact.inference_comparison is None
    assert not artifact.inference_qualified


def test_manifest_tamper_and_downstream_precision_overclaim_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    _save(source, torch.float64)
    artifact = _mdstats.export_mace_deployment_artifact(
        source,
        tmp_path / "deployment",
        deployment_dtype="float64",
        training_dtype="float64",
        inference_probe=_probe,
    )
    payload = artifact.to_dict()
    payload["source_training_dtype"] = "float32"
    with pytest.raises(_mdstats.TrainingDataSerializationError):
        _mdstats.MaceDeploymentArtifact.from_dict(payload)
    with pytest.raises(_mdstats.TrainingDataInputError, match="cannot claim"):
        replace(artifact, downstream_runtime_precision_claimed=True)
    with pytest.raises(_mdstats.TrainingDataInputError, match="does not match source"):
        replace(artifact, source_artifact_sha256="b" * 64)
