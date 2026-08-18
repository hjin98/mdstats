"""Authenticated bundled-array persistence for MVSTATE-REUSE1 selector state.

The state cache contains many small/medium arrays per target rung.  Persisting
one fsync'd ``.npy`` file per array makes the reconstructible cache more
expensive than the compute it saves.  MVSTATE-REUSE1 therefore stores all
arrays in one uncompressed NPZ bundle, authenticated by a whole-file SHA-256
plus per-array value identities in the manifest.  The cache remains execution
state; worker/storage choices never enter scientific digests.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

import numpy as np

from ._common import canonical_json, digest, sha256_file_cached
from .target_coverage import _coverage_array_reference, _validate_array_reference
from .target_multi_view_selection_state import (
    TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION,
    TargetMultiViewSelectionFamilyStateCheckpoint,
    TargetMultiViewSelectionStateCheckpoint,
    TargetMultiViewSelectionDomainStateCache,
    TargetMultiViewSelectionStateCache,
)

TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA = "mdstats.target-multi-view-selection-state-native-manifest.v1"
TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA = "mdstats.mlff-campaign-target-multi-view-selection-state-native-pointer.v1"


class TargetMultiViewSelectionStateNativeStoreError(RuntimeError):
    """Persisted MVSTATE-REUSE1 arrays are missing, stale, or inconsistent."""


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _bundle_descriptor(path: Path) -> dict[str, Any]:
    return {"relative_path": path.name, "sha256": _sha256_file(path), "size_bytes": int(path.stat().st_size)}


def _safe_bundle(root: Path, descriptor: Mapping[str, Any]) -> Path:
    relative = Path(str(descriptor.get("relative_path", "")))
    if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
        raise TargetMultiViewSelectionStateNativeStoreError("Invalid MVSTATE-REUSE1 bundle path.")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents or not path.is_file():
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 array bundle is missing.")
    if path.stat().st_size != int(descriptor.get("size_bytes", -1)):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 array bundle size mismatch.")
    if _sha256_file(path) != str(descriptor.get("sha256", "")):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 array bundle checksum mismatch.")
    return path


def _array_descriptor(key: str, array: np.ndarray) -> dict[str, Any]:
    return {"bundle_key": key, "array_reference": _coverage_array_reference(np.ascontiguousarray(array))}


def _read_array(bundle: Any, descriptor: Mapping[str, Any], *, label: str) -> np.ndarray:
    key = str(descriptor.get("bundle_key", ""))
    if not key or key not in bundle.files:
        raise TargetMultiViewSelectionStateNativeStoreError(f"Missing MVSTATE-REUSE1 {label} array.")
    try:
        value = np.asarray(bundle[key])
        reference = descriptor.get("array_reference")
        if not isinstance(reference, Mapping):
            raise TargetMultiViewSelectionStateNativeStoreError(f"Missing MVSTATE-REUSE1 {label} array identity.")
        _validate_array_reference(reference, value, name=label)
    except Exception as exc:
        if isinstance(exc, TargetMultiViewSelectionStateNativeStoreError):
            raise
        raise TargetMultiViewSelectionStateNativeStoreError(f"Cannot restore MVSTATE-REUSE1 {label} array.") from exc
    value = np.ascontiguousarray(value)
    value.setflags(write=False)
    return value


def _validate_existing_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    path = _safe_bundle(root, manifest.get("array_bundle", {}))
    try:
        with np.load(path, allow_pickle=False) as bundle:
            for domain in manifest.get("domains", ()):
                for checkpoint in domain.get("checkpoints", ()):
                    for name, desc in checkpoint.get("arrays", {}).items():
                        _read_array(bundle, desc, label=f"checkpoint {checkpoint.get('target_size')} {name}")
                    for family in checkpoint.get("families", ()):
                        for name, desc in family.get("arrays", {}).items():
                            _read_array(bundle, desc, label=f"family {family.get('family_id')} {name}")
    except (OSError, ValueError) as exc:
        raise TargetMultiViewSelectionStateNativeStoreError("Cannot open MVSTATE-REUSE1 array bundle.") from exc


def write_target_multi_view_selection_state_native_record(
    cache: TargetMultiViewSelectionStateCache,
    records_root: str | Path,
    *,
    record_key: str = "target_multi_view_selection_state_cache",
) -> dict[str, Any]:
    root = Path(records_root); root.mkdir(parents=True, exist_ok=True)
    destination = root / f"target-multi-view-selection-state-{cache.content_digest}"
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
            supplied = existing.get("manifest_digest")
            expected = digest({k:v for k,v in existing.items() if k != "manifest_digest"})
            if (
                existing.get("schema") == TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA
                and existing.get("content_digest") == cache.content_digest
                and existing.get("record_key") == record_key
                and supplied == expected
            ):
                _validate_existing_manifest(destination, existing)
                pointer = {
                    "schema": TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA,
                    "persistence_version": TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION,
                    "relative_path": str(manifest_path.relative_to(root.parent)),
                    "sha256": _sha256_file(manifest_path),
                    "content_digest": cache.content_digest,
                    "record_key": record_key,
                }
                return {**pointer, "pointer_digest": digest(pointer)}
        except Exception:
            pass
        shutil.rmtree(destination, ignore_errors=True)

    temporary = Path(tempfile.mkdtemp(prefix="target-multi-view-selection-state-write-", dir=root))
    try:
        arrays: dict[str, np.ndarray] = {}
        domains=[]
        for di, domain in enumerate(cache.domains):
            cps=[]
            for ci, cp in enumerate(domain.checkpoints):
                prefix=f"d{di:03d}_c{ci:03d}_n{cp.target_size:05d}"
                cp_arrays={}
                for name, array in (
                    ("available", cp.available),
                    ("total_coverage_gain", cp.total_coverage_gain),
                    ("total_representative_gain", cp.total_representative_gain),
                    ("hard_gain", cp.hard_gain),
                    ("obligation_counts", cp.obligation_counts),
                    ("required_obligation_mask", cp.required_obligation_mask),
                    ("unit_counts", cp.unit_counts),
                ):
                    key=f"{prefix}_{name}"; arrays[key]=np.ascontiguousarray(array); cp_arrays[name]=_array_descriptor(key,array)
                fams=[]
                for fi, fam in enumerate(cp.families):
                    fp=f"{prefix}_f{fi:03d}"
                    fam_arrays={}
                    for name, array in (
                        ("covered", fam.covered),
                        ("multiplicity", fam.multiplicity),
                        ("coverage_gain", fam.coverage_gain),
                        ("representative_gain", fam.representative_gain),
                    ):
                        key=f"{fp}_{name}"; arrays[key]=np.ascontiguousarray(array); fam_arrays[name]=_array_descriptor(key,array)
                    fams.append({"family_id":fam.family_id,"coverage_mass":fam.coverage_mass,"content_digest":fam.content_digest,"arrays":fam_arrays})
                cps.append({
                    "target_size":cp.target_size,"selected_prefix_digest":cp.selected_prefix_digest,
                    "representative_utility":cp.representative_utility,
                    "unsatisfied_required_obligation_count":cp.unsatisfied_required_obligation_count,
                    "content_digest":cp.content_digest,"arrays":cp_arrays,"families":fams,
                })
            domains.append({
                "label_domain_id":domain.label_domain_id,"reference_domain_digest":domain.reference_domain_digest,
                "sparse_domain_digest":domain.sparse_domain_digest,"selection_domain_digest":domain.selection_domain_digest,
                "candidate_count":domain.candidate_count,"content_digest":domain.content_digest,"checkpoints":cps,
            })

        bundle_path=temporary/"arrays.npz"
        np.savez(bundle_path, **arrays)
        with bundle_path.open("rb") as handle:
            os.fsync(handle.fileno())
        manifest={
            "schema":TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA,
            "persistence_version":cache.persistence_version,"record_key":record_key,"content_digest":cache.content_digest,
            "dataset_id":cache.dataset_id,"target_coverage_reference_digest":cache.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest":cache.target_coverage_sparse_index_digest,
            "target_multi_view_selection_digest":cache.target_multi_view_selection_digest,
            "selector_policy_digest":cache.selector_policy_digest,"sparse_kernel_schema":cache.sparse_kernel_schema,
            "authority_version":cache.authority_version,"array_bundle":_bundle_descriptor(bundle_path),"domains":domains,
        }
        manifest["manifest_digest"]=digest(manifest)
        mp=temporary/"manifest.json"; mp.write_text(canonical_json(manifest)+"\n",encoding="utf-8")
        with mp.open("rb") as handle: os.fsync(handle.fileno())
        os.replace(temporary,destination)
        manifest_path=destination/"manifest.json"
        pointer={
            "schema":TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA,
            "persistence_version":TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION,
            "relative_path":str(manifest_path.relative_to(root.parent)),"sha256":_sha256_file(manifest_path),
            "content_digest":cache.content_digest,"record_key":record_key,
        }
        return {**pointer,"pointer_digest":digest(pointer)}
    except Exception:
        shutil.rmtree(temporary,ignore_errors=True); raise


def read_target_multi_view_selection_state_native_record(
    pointer: Mapping[str, Any],
    campaign_root: str | Path,
    *,
    mmap_threshold_bytes: int = 8 * 1024 * 1024,  # retained for API symmetry; NPZ is bundled/non-mmap
) -> TargetMultiViewSelectionStateCache:
    del mmap_threshold_bytes
    if pointer.get("schema") != TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA:
        raise TargetMultiViewSelectionStateNativeStoreError("Unsupported MVSTATE-REUSE1 native pointer schema.")
    if pointer.get("pointer_digest") != digest({k:v for k,v in pointer.items() if k != "pointer_digest"}):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 native pointer digest mismatch.")
    root=Path(campaign_root).resolve(); rel=Path(str(pointer.get("relative_path","")))
    if rel.is_absolute() or ".." in rel.parts:
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 native pointer escapes campaign root.")
    manifest_path=(root/rel).resolve()
    if root not in manifest_path.parents or not manifest_path.is_file():
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 native manifest is missing.")
    if _sha256_file(manifest_path) != str(pointer.get("sha256","")):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 native manifest checksum mismatch.")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA:
        raise TargetMultiViewSelectionStateNativeStoreError("Unsupported MVSTATE-REUSE1 native manifest schema.")
    if manifest.get("persistence_version") != TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION:
        raise TargetMultiViewSelectionStateNativeStoreError("Unsupported MVSTATE-REUSE1 native persistence version.")
    if manifest.get("manifest_digest") != digest({k:v for k,v in manifest.items() if k != "manifest_digest"}):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 native manifest digest mismatch.")
    bundle_path=_safe_bundle(manifest_path.parent,manifest.get("array_bundle",{}))
    domains=[]
    try:
        with np.load(bundle_path,allow_pickle=False) as bundle:
            for drow in manifest.get("domains",()):
                cps=[]
                for crow in drow.get("checkpoints",()):
                    fams=[]
                    for frow in crow.get("families",()):
                        a=frow["arrays"]
                        fam=TargetMultiViewSelectionFamilyStateCheckpoint(
                            family_id=str(frow["family_id"]),coverage_mass=float(frow["coverage_mass"]),
                            covered=_read_array(bundle,a["covered"],label="covered"),
                            multiplicity=_read_array(bundle,a["multiplicity"],label="multiplicity"),
                            coverage_gain=_read_array(bundle,a["coverage_gain"],label="coverage_gain"),
                            representative_gain=_read_array(bundle,a["representative_gain"],label="representative_gain"),
                        )
                        if fam.content_digest != frow.get("content_digest"):
                            raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 family content digest mismatch.")
                        fams.append(fam)
                    a=crow["arrays"]
                    cp=TargetMultiViewSelectionStateCheckpoint(
                        target_size=int(crow["target_size"]),selected_prefix_digest=str(crow["selected_prefix_digest"]),
                        representative_utility=float(crow["representative_utility"]),
                        available=_read_array(bundle,a["available"],label="available"),families=tuple(fams),
                        total_coverage_gain=_read_array(bundle,a["total_coverage_gain"],label="total_coverage_gain"),
                        total_representative_gain=_read_array(bundle,a["total_representative_gain"],label="total_representative_gain"),
                        hard_gain=_read_array(bundle,a["hard_gain"],label="hard_gain"),
                        obligation_counts=_read_array(bundle,a["obligation_counts"],label="obligation_counts"),
                        required_obligation_mask=_read_array(bundle,a["required_obligation_mask"],label="required_obligation_mask"),
                        unsatisfied_required_obligation_count=int(crow["unsatisfied_required_obligation_count"]),
                        unit_counts=_read_array(bundle,a["unit_counts"],label="unit_counts"),
                    )
                    if cp.content_digest != crow.get("content_digest"):
                        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 checkpoint content digest mismatch.")
                    cps.append(cp)
                domain=TargetMultiViewSelectionDomainStateCache(
                    label_domain_id=str(drow["label_domain_id"]),reference_domain_digest=str(drow["reference_domain_digest"]),
                    sparse_domain_digest=str(drow["sparse_domain_digest"]),selection_domain_digest=str(drow["selection_domain_digest"]),
                    candidate_count=int(drow["candidate_count"]),checkpoints=tuple(cps),
                )
                if domain.content_digest != drow.get("content_digest"):
                    raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 domain content digest mismatch.")
                domains.append(domain)
    except (OSError,ValueError,KeyError,TargetMultiViewSelectionStateNativeStoreError) as exc:
        if isinstance(exc,TargetMultiViewSelectionStateNativeStoreError): raise
        raise TargetMultiViewSelectionStateNativeStoreError("Cannot restore MVSTATE-REUSE1 array bundle.") from exc
    cache=TargetMultiViewSelectionStateCache(
        dataset_id=str(manifest["dataset_id"]),target_coverage_reference_digest=str(manifest["target_coverage_reference_digest"]),
        target_coverage_sparse_index_digest=str(manifest["target_coverage_sparse_index_digest"]),
        target_multi_view_selection_digest=str(manifest["target_multi_view_selection_digest"]),
        selector_policy_digest=str(manifest["selector_policy_digest"]),domains=tuple(domains),
        sparse_kernel_schema=str(manifest["sparse_kernel_schema"]),authority_version=str(manifest["authority_version"]),
        persistence_version=str(manifest["persistence_version"]),
    )
    if cache.content_digest != manifest.get("content_digest") or cache.content_digest != pointer.get("content_digest"):
        raise TargetMultiViewSelectionStateNativeStoreError("MVSTATE-REUSE1 cache content digest mismatch.")
    return cache


__all__=[
    "TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA","TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA",
    "TargetMultiViewSelectionStateNativeStoreError","write_target_multi_view_selection_state_native_record",
    "read_target_multi_view_selection_state_native_record",
]
