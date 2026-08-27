from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

import mdstats
from mdstats.training_data import checkpoint_capsule
from mdstats.training_data import train2_runtime
from mdstats.training_data.model_features import (
    MaceCalculatorProvider,
    MaceModelStateCompatibilityError,
    ModelCheckpointIdentity,
)


def _legacy_tensor_state_digest(values, *, schema: str) -> str:
    h = hashlib.sha256()
    h.update(schema.encode("utf-8"))
    for item in values:
        value = item.detach().cpu().contiguous()
        h.update(str(value.dtype).encode("utf-8"))
        h.update(repr(tuple(value.shape)).encode("utf-8"))
        h.update(bytes(value.numpy().tobytes()))
    return h.hexdigest()


def _legacy_model_state_sha256(state) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().cpu().contiguous()
        h.update(key.encode("utf-8")); h.update(b"\0")
        h.update(str(tensor.dtype).encode("ascii")); h.update(b"\0")
        h.update(json.dumps(tuple(int(v) for v in tensor.shape)).encode("ascii")); h.update(b"\0")
        try:
            payload = tensor.numpy().tobytes(order="C")
        except Exception:
            payload = tensor.view(torch.uint8).numpy().tobytes(order="C")
        h.update(payload); h.update(b"\xff")
    return h.hexdigest()


@pytest.mark.parametrize(
    "values",
    [
        [torch.arange(31, dtype=torch.float64).reshape(31, 1)],
        [torch.arange(37, dtype=torch.int64), torch.tensor([True, False, True])],
        [torch.linspace(-2.0, 3.0, 43, dtype=torch.float32)],
    ],
)
def test_streamed_train2_tensor_hash_is_byte_identical_to_legacy(values) -> None:
    schema = "mdstats.train2-live-parameters.v1"
    assert train2_runtime._tensor_state_digest(values, schema=schema) == _legacy_tensor_state_digest(
        values, schema=schema
    )


def test_streamed_capsule_state_hash_is_byte_identical_to_legacy() -> None:
    state = {
        "a.weight": torch.arange(24, dtype=torch.float64).reshape(6, 4),
        "b.index": torch.arange(7, dtype=torch.int64),
        "flag": torch.tensor([True, False], dtype=torch.bool),
    }
    assert checkpoint_capsule.model_state_sha256(state) == _legacy_model_state_sha256(state)


class _TinyCalculator:
    def __init__(self, model) -> None:
        self.models = [model]
        self.available_heads = ("target_head",)
        self.head = "target_head"

    def get_descriptors(self, *args, **kwargs):  # pragma: no cover - adapter requirement only
        raise NotImplementedError


def _identity(path: Path) -> ModelCheckpointIdentity:
    payload = path.read_bytes()
    return ModelCheckpointIdentity(
        model_family="MACE-test-shell",
        checkpoint_locator=str(path),
        checkpoint_sha256=hashlib.sha256(payload).hexdigest(),
        calculator_class="tests._TinyCalculator",
        model_version="test",
        supported_atomic_numbers=(1,),
        model_supported_atomic_numbers=(1,),
        requested_atomic_numbers=(1,),
        device="cpu",
        default_dtype="float64",
    )


def test_eval2_model_shell_hot_swap_requires_exact_architecture_and_state(tmp_path: Path) -> None:
    first = torch.nn.Linear(4, 3, bias=True, dtype=torch.float64)
    second = torch.nn.Linear(4, 3, bias=True, dtype=torch.float64)
    with torch.no_grad():
        second.weight.copy_(torch.arange(12, dtype=torch.float64).reshape(3, 4) / 10.0)
        second.bias.copy_(torch.tensor([0.25, -0.5, 0.75], dtype=torch.float64))
    first_path = tmp_path / "first.model"
    second_path = tmp_path / "second.model"
    torch.save(first, first_path)
    torch.save(second, second_path)

    provider = MaceCalculatorProvider(_TinyCalculator(first), _identity(first_path))
    provider._state_hot_swap_qualified = True
    probe = torch.arange(8, dtype=torch.float64).reshape(2, 4) / 7.0
    first_output = provider._calculator.models[0](probe).detach().clone()
    expected_sha = hashlib.sha256(second_path.read_bytes()).hexdigest()
    new_identity = provider.load_compatible_model_state(second_path, expected_sha256=expected_sha)
    assert new_identity.checkpoint_sha256 == expected_sha
    for key, value in second.state_dict().items():
        assert torch.equal(provider._calculator.models[0].state_dict()[key], value)
    swapped_output = provider._calculator.models[0](probe).detach()
    fresh_output = second(probe).detach()
    assert torch.equal(swapped_output, fresh_output)
    assert not torch.equal(swapped_output, first_output)

    incompatible = torch.nn.Linear(5, 3, bias=True, dtype=torch.float64)
    incompatible_path = tmp_path / "incompatible.model"
    torch.save(incompatible, incompatible_path)
    with pytest.raises(
        MaceModelStateCompatibilityError,
        match="execution-architecture identity differs",
    ):
        provider.load_compatible_model_state(incompatible_path)


def test_eval2_model_shell_is_disabled_without_explicit_qualification(tmp_path: Path) -> None:
    model = torch.nn.Linear(2, 2, dtype=torch.float64)
    path = tmp_path / "model.pt"
    torch.save(model, path)
    provider = MaceCalculatorProvider(_TinyCalculator(model), _identity(path))
    with pytest.raises(mdstats.TrainingDataInputError, match="not qualified"):
        provider.load_compatible_model_state(path)


def test_target_size_candidate_provider_session_rebuilds_incompatible_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from mdstats.training_data import campaign_execution
    from mdstats.training_data.model_features import MaceModelStateCompatibilityError

    first_path = tmp_path / "first.model"
    second_path = tmp_path / "second.model"
    first_path.write_bytes(b"first-shell")
    second_path.write_bytes(b"second-shell-incompatible")
    first_sha = hashlib.sha256(first_path.read_bytes()).hexdigest()
    second_sha = hashlib.sha256(second_path.read_bytes()).hexdigest()

    class Provider:
        def __init__(self, sha: str, *, incompatible: bool = False) -> None:
            self.checkpoint_identity = SimpleNamespace(checkpoint_sha256=sha)
            self.incompatible = incompatible
            self.closed = False
            self.heads = []

        def load_compatible_model_state(self, path, *, expected_sha256=None):
            assert expected_sha256 == second_sha
            if self.incompatible:
                raise MaceModelStateCompatibilityError("incompatible fixture shell")
            self.checkpoint_identity.checkpoint_sha256 = expected_sha256

        def set_head(self, head):
            self.heads.append(head)

        def close(self):
            self.closed = True

    first = Provider(first_sha, incompatible=True)
    rebuilt = Provider(second_sha)
    providers = iter((first, rebuilt))
    monkeypatch.setattr(
        campaign_execution,
        "_build_prepared_mace_candidate_provider",
        lambda prepared, path: next(providers),
    )
    prepared = SimpleNamespace(policy=SimpleNamespace(target_head_name="target_head"))
    session = campaign_execution.ReusableMaceCandidateProviderSession()
    assert session.acquire(prepared, first_path) is first
    assert session.acquire(prepared, second_path) is rebuilt
    assert first.closed
    assert session.rebuild_count == 2
    assert session.reuse_count == 0
    assert rebuilt.heads == ["target_head"]
    session.close()
    assert rebuilt.closed
