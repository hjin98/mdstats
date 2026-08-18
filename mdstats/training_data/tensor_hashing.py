"""Zero-copy tensor-byte hashing helpers for MLFF persistence paths.

The scientific digest contracts in TRAIN2 and STOR2 are defined over tensor
metadata plus the exact contiguous CPU byte representation.  Hashing therefore
must not depend on torch serialization bytes.  These helpers expose that byte
representation through the Python buffer protocol so large tensors do not
require an additional ``numpy().tobytes()`` allocation solely for hashing.
"""

from __future__ import annotations

from typing import Any

from ._common import TrainingDataInputError

DEFAULT_TENSOR_HASH_CHUNK_BYTES = 8 * 1024 * 1024


def contiguous_cpu_tensor(tensor: Any) -> Any:
    """Return the detached contiguous CPU tensor used by digest contracts."""

    if not hasattr(tensor, "detach") or not hasattr(tensor, "shape"):
        raise TrainingDataInputError("Tensor hashing requires a torch-like tensor value.")
    try:
        return tensor.detach().cpu().contiguous()
    except Exception as exc:
        raise TrainingDataInputError("Could not obtain a contiguous CPU tensor for hashing.") from exc


def tensor_byte_view(tensor: Any) -> tuple[Any, memoryview]:
    """Return ``(owner, byte_view)`` without materializing a second byte copy.

    ``owner`` keeps the NumPy export alive for the lifetime of the memoryview.
    The fallback handles torch dtypes such as bfloat16 that NumPy cannot expose
    directly by viewing the same tensor storage as uint8 first.
    """

    value = contiguous_cpu_tensor(tensor)
    try:
        owner = value.numpy()
    except Exception:
        try:
            owner = value.view(dtype=getattr(__import__("torch"), "uint8")).numpy()
        except Exception as exc:
            raise TrainingDataInputError(
                "Could not expose tensor storage through the Python buffer protocol."
            ) from exc
    try:
        return owner, memoryview(owner).cast("B")
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError("Tensor byte view is not contiguous.") from exc


def update_hasher_with_tensor_bytes(
    hasher: Any,
    tensor: Any,
    *,
    chunk_bytes: int = DEFAULT_TENSOR_HASH_CHUNK_BYTES,
) -> None:
    """Stream exact contiguous tensor bytes into a hashlib-compatible hasher."""

    size = int(chunk_bytes)
    if size <= 0:
        raise TrainingDataInputError("Tensor hash chunk size must be positive.")
    owner, view = tensor_byte_view(tensor)
    del owner  # memoryview owns a reference to its exporter
    for start in range(0, len(view), size):
        hasher.update(view[start : start + size])


def tensor_bytes_copy(tensor: Any) -> bytes:
    """Materialize tensor bytes only where a byte object is intrinsically needed."""

    owner, view = tensor_byte_view(tensor)
    del owner
    return bytes(view)


__all__ = [
    "DEFAULT_TENSOR_HASH_CHUNK_BYTES",
    "contiguous_cpu_tensor",
    "tensor_byte_view",
    "tensor_bytes_copy",
    "update_hasher_with_tensor_bytes",
]
