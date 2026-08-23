"""Receipt-aware forward-only MVIDX1 restore for MVSEL2/REPAIR2.

The canonical native-store reader remains the authority for receipt misses. This
module only accelerates the already-authenticated cache-hit case: when the exact
compound native-store validation receipt matches the manifest plus every sidecar
file identity, product-scale forward family arrays are reopened with metadata
validation and trusted-native construction instead of rescanning their values.
A final identity check closes the mmap-open race.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ._common import digest
from . import target_coverage_sparse_index_store as _store
from .target_coverage_sparse_index import TargetCoverageHardObligation
from .target_coverage_sparse_forward_view import (
    TargetCoverageSparseForwardDomainView,
    TargetCoverageSparseForwardFamilyView,
    TargetCoverageSparseForwardIndexView,
)


def _authenticated_manifest(
    pointer: Mapping[str, Any],
    state_root: str | Path,
) -> tuple[Path, Mapping[str, Any]]:
    """Authenticate the native pointer/manifest without opening sidecar arrays."""

    if pointer.get("schema") != _store.TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "Unsupported TARGET-DATA2C-MVIDX1 native pointer schema."
        )
    if pointer.get("persistence_version") != _store.TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "Unsupported TARGET-DATA2C-MVIDX1 persistence version."
        )
    relative = Path(str(pointer.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "Invalid TARGET-DATA2C-MVIDX1 manifest path."
        )
    root = Path(state_root).resolve()
    manifest_path = (root / relative).resolve()
    if root not in manifest_path.parents or not manifest_path.is_file():
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "Missing TARGET-DATA2C-MVIDX1 native manifest."
        )
    expected_sha = str(pointer.get("sha256", ""))
    if not expected_sha or _store._sha256_file(manifest_path) != expected_sha:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 manifest checksum mismatch."
        )
    pointer_payload = {key: value for key, value in pointer.items() if key != "pointer_digest"}
    if pointer.get("pointer_digest") not in (None, digest(pointer_payload)):
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 pointer digest mismatch."
        )
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if (
        not isinstance(manifest, Mapping)
        or manifest.get("schema") != _store.TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA
        or manifest.get("persistence_version")
        != _store.TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION
    ):
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "Invalid TARGET-DATA2C-MVIDX1 native manifest."
        )
    expected_manifest_digest = digest(
        {key: value for key, value in manifest.items() if key != "manifest_digest"}
    )
    if manifest.get("manifest_digest") != expected_manifest_digest:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 native manifest digest mismatch."
        )
    if pointer.get("content_digest") != manifest.get("index_content_digest"):
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 pointer/manifest content digest mismatch."
        )
    return manifest_path, manifest


def _forward_family_from_receipt(
    *,
    family_payload: Mapping[str, Any],
    arrays: Mapping[str, Any],
    candidate_offsets: Any,
    candidate_witnesses: Any,
) -> TargetCoverageSparseForwardFamilyView:
    """Construct a family view whose large rows were validated by the receipt.

    This mirrors the trusted-native constructor used by the full sparse index.
    The compact CSR offsets are still checked structurally; only the O(E)
    witness range/sortedness passes are skipped because the compound receipt can
    exist only after the exact sidecars were fully validated.
    """

    from ._common import validate_digest
    from .target_coverage_sparse_index import _canonical_array, _validate_offsets

    family_id = str(family_payload["family_id"])
    if not family_id.strip():
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 forward family ID is empty."
        )
    family_digest = validate_digest(str(family_payload["family_digest"]), name="family_digest")
    mvidx1_family_digest = validate_digest(
        str(family_payload["content_digest"]), name="mvidx1_family_digest"
    )
    candidate_count = int(family_payload["candidate_count"])
    witness_count = int(family_payload["witness_count"])
    if candidate_count < 1 or witness_count < 1:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 forward family cardinality is invalid."
        )
    offsets = _canonical_array(
        candidate_offsets,
        dtype="<u8",
        ndim=1,
        name="forward candidate_offsets",
    )
    witnesses = _canonical_array(
        candidate_witnesses,
        dtype="<u4",
        ndim=1,
        name="forward candidate_witnesses",
    )
    _validate_offsets(
        offsets,
        item_count=candidate_count,
        edge_count=len(witnesses),
        name="forward candidate",
    )
    family = object.__new__(TargetCoverageSparseForwardFamilyView)
    object.__setattr__(family, "family_id", family_id)
    object.__setattr__(family, "family_digest", family_digest)
    object.__setattr__(family, "mvidx1_family_digest", mvidx1_family_digest)
    object.__setattr__(family, "candidate_count", candidate_count)
    object.__setattr__(family, "witness_count", witness_count)
    object.__setattr__(family, "candidate_offsets", offsets)
    object.__setattr__(family, "candidate_witnesses", witnesses)
    object.__setattr__(
        family,
        "_array_references",
        {
            name: dict(arrays[name]["array_reference"])
            for name in ("candidate_offsets", "candidate_witnesses")
        },
    )
    return family


def read_target_coverage_sparse_index_forward_view_native_record_receipt_aware(
    pointer: Mapping[str, Any],
    state_root: str | Path,
    *,
    mmap_threshold_bytes: int = 8 * 1024 * 1024,
) -> TargetCoverageSparseForwardIndexView:
    """Restore the forward MVIDX1 view with an exact compound-receipt fast path.

    Receipt misses delegate byte-for-byte behavior to the canonical forward
    reader. Receipt hits reuse the same restore identity accepted by the full
    native reader and skip the redundant O(E) value-hash/range/sortedness passes
    over family ``candidate_offsets``/``candidate_witnesses`` arrays. Array
    metadata, compact CSR offsets, manifest lineage, per-file checksums,
    immutable mmap flags, edge counts, and final sidecar identity are still
    checked.
    """

    manifest_path, manifest = _authenticated_manifest(pointer, state_root)
    data_root = manifest_path.parent
    restore_identity, _ = _store._restore_identity(data_root, manifest)
    expected_index_digest = str(manifest.get("index_content_digest", ""))
    receipt_hit = (
        _store.read_validation_receipt(
            _store._MVIDX_VALIDATION_RECEIPT_NAMESPACE,
            restore_identity,
        )
        == expected_index_digest
    )
    if not receipt_hit:
        return _store.read_target_coverage_sparse_index_forward_view_native_record(
            pointer,
            state_root,
            mmap_threshold_bytes=mmap_threshold_bytes,
        )

    packed_payload = manifest.get("packed_family_arrays")
    if not isinstance(packed_payload, Mapping):
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 native v2 manifest is missing packed family arrays."
        )
    packed_roots: dict[str, Any] = {}
    for name in ("candidate_offsets", "candidate_witnesses"):
        descriptor = packed_payload.get(name)
        if not isinstance(descriptor, Mapping):
            raise _store.TargetCoverageSparseIndexNativeStoreError(
                f"TARGET-DATA2C-MVIDX1 packed {name} descriptor is missing."
            )
        packed_roots[name] = _store._read_packed_npy(
            data_root, descriptor, label=f"packed family {name}"
        )

    packed_cursors = {name: 0 for name in packed_roots}
    try:
        domains: list[TargetCoverageSparseForwardDomainView] = []
        for domain_payload in manifest.get("domains", ()):
            families: list[TargetCoverageSparseForwardFamilyView] = []
            for family_payload in domain_payload.get("families", ()):
                slices = family_payload.get("array_slices")
                if not isinstance(slices, Mapping):
                    raise _store.TargetCoverageSparseIndexNativeStoreError(
                        "TARGET-DATA2C-MVIDX1 family packed-slice manifest is missing."
                    )
                family_arrays: dict[str, Any] = {}
                for name in ("candidate_offsets", "candidate_witnesses"):
                    descriptor = slices.get(name)
                    if not isinstance(descriptor, Mapping):
                        raise _store.TargetCoverageSparseIndexNativeStoreError(
                            f"TARGET-DATA2C-MVIDX1 family {name} packed slice is missing."
                        )
                    if int(descriptor.get("start", -1)) != packed_cursors[name]:
                        raise _store.TargetCoverageSparseIndexNativeStoreError(
                            f"TARGET-DATA2C-MVIDX1 packed {name} slices are not canonical."
                        )
                    family_arrays[name] = _store._packed_slice(
                        packed_roots[name],
                        descriptor,
                        label=name,
                        validate_array_reference=False,
                    )
                    packed_cursors[name] = int(descriptor["stop"])
                family = _forward_family_from_receipt(
                    family_payload=family_payload,
                    arrays=slices,
                    candidate_offsets=family_arrays["candidate_offsets"],
                    candidate_witnesses=family_arrays["candidate_witnesses"],
                )
                if int(family_payload.get("edge_count", family.edge_count)) != family.edge_count:
                    raise _store.TargetCoverageSparseIndexNativeStoreError(
                        "TARGET-DATA2C-MVIDX1 forward family edge count mismatch."
                    )
                families.append(family)

            arrays = domain_payload.get("arrays")
            if not isinstance(arrays, Mapping):
                raise _store.TargetCoverageSparseIndexNativeStoreError(
                    "TARGET-DATA2C-MVIDX1 domain array manifest is missing."
                )
            domains.append(
                TargetCoverageSparseForwardDomainView(
                    label_domain_id=str(domain_payload["label_domain_id"]),
                    frame_domain_digest=str(domain_payload["frame_domain_digest"]),
                    mvidx1_domain_digest=str(domain_payload["content_digest"]),
                    candidate_count=int(domain_payload["candidate_count"]),
                    families=tuple(families),
                    obligations=tuple(
                        TargetCoverageHardObligation.from_dict(item)
                        for item in domain_payload["obligations"]
                    ),
                    candidate_obligation_offsets=_store._read_npy(
                        data_root,
                        arrays["candidate_obligation_offsets"],
                        label="candidate_obligation_offsets",
                        mmap_threshold_bytes=mmap_threshold_bytes,
                    ),
                    candidate_obligations=_store._read_npy(
                        data_root,
                        arrays["candidate_obligations"],
                        label="candidate_obligations",
                        mmap_threshold_bytes=mmap_threshold_bytes,
                    ),
                    correlation_unit_ids=tuple(
                        str(item) for item in domain_payload["correlation_unit_ids"]
                    ),
                    candidate_correlation_unit_codes=_store._read_npy(
                        data_root,
                        arrays["candidate_correlation_unit_codes"],
                        label="candidate_correlation_unit_codes",
                        mmap_threshold_bytes=mmap_threshold_bytes,
                    ),
                )
            )
        for name, root_array in packed_roots.items():
            if packed_cursors[name] != int(root_array.size):
                raise _store.TargetCoverageSparseIndexNativeStoreError(
                    f"TARGET-DATA2C-MVIDX1 packed {name} contains unreferenced trailing data."
                )
    except Exception:
        for array in packed_roots.values():
            _store._close_memmap(array)
        raise

    result = TargetCoverageSparseForwardIndexView(
        dataset_id=str(manifest["dataset_id"]),
        mvidx1_content_digest=str(manifest["index_content_digest"]),
        target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
        target_data_role_freeze_digest=str(manifest["target_data_role_freeze_digest"]),
        target_coverage_feasibility_digest=str(manifest["target_coverage_feasibility_digest"]),
        domains=tuple(domains),
    )
    final_identity, _ = _store._restore_identity(data_root, manifest)
    if final_identity != restore_identity:
        raise _store.TargetCoverageSparseIndexNativeStoreError(
            "TARGET-DATA2C-MVIDX1 sidecar identity changed during forward restore."
        )
    return result


def install_forward_receipt_runtime(hardening_module: Any) -> None:
    """Install the cache-hit-only forward reader into the existing runtime seam."""

    hardening_module.read_target_coverage_sparse_index_forward_view_native_record = (
        read_target_coverage_sparse_index_forward_view_native_record_receipt_aware
    )
