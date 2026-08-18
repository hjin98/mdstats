from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import pytest

from mdstats.analysis.density._pilot_common import (
    array_digest,
    array_payload_bytes,
    canonical_json,
    digest,
    freeze,
    json_value,
    readonly_array,
    replace_evidence,
)
from mdstats.analysis.density.pilot_audit import PilotAuditInputError


def test_canonical_serialization_and_digest_are_deterministic() -> None:
    left = {"b": [2, 1], "a": {"z": 3}}
    right = {"a": {"z": 3}, "b": [2, 1]}
    assert canonical_json(left) == canonical_json(right)
    assert digest(left) == digest(right)


def test_freeze_and_json_value_preserve_content_and_reject_nonfinite() -> None:
    frozen = freeze({"b": [np.int64(2), 3.0], "a": {"x": True}})
    assert isinstance(frozen, MappingProxyType)
    assert json_value(frozen) == {"a": {"x": True}, "b": [2, 3.0]}
    with pytest.raises(PilotAuditInputError, match="non-finite"):
        freeze({"bad": np.inf})


def test_array_digest_includes_shape_and_dtype() -> None:
    base = np.arange(6, dtype=np.float64)
    assert array_digest(base) != array_digest(base.reshape(2, 3))
    assert array_digest(base) != array_digest(base.astype(np.float32))


def test_readonly_array_and_unique_payload_accounting() -> None:
    array = readonly_array([[1.0, 2.0]], dtype=float, ndim=2, name="array")
    assert array.shape == (1, 2)
    assert not array.flags.writeable

    @dataclass
    class Holder:
        first: np.ndarray
        second: np.ndarray

    holder = Holder(array, array)
    assert array_payload_bytes(holder, {"again": array}) == array.nbytes


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    value: int


def test_replace_evidence_is_canonical_and_id_based() -> None:
    records = (Evidence("b", 1), Evidence("a", 1))
    result = replace_evidence(records, {"b": Evidence("b", 2), "c": Evidence("c", 3)})
    assert result == (Evidence("a", 1), Evidence("b", 2), Evidence("c", 3))
