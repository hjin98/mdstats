"""Immutable prepared target-size generations.

``prepare`` is the only command that constructs the expensive P1 -> P2 ->
P3-common scientific substrate.  Before this module existed the campaign store
persisted only the *identities* of that substrate, so every downstream command
rebuilt the whole graph from live sources -- restoring DATA4, re-authenticating
VASP inputs, and reconstructing the canonical frame authority -- merely to prove
that nothing had changed.  That made currentness cost O(dataset) and made a
downstream command silently depend on live input bytes it does not own.

The repaired ownership is:

.. code-block:: text

    prepare      -> build the substrate -> publish immutable components
                 -> CAS-bind the prepared manifest onto the campaign generation
    downstream   -> load the exact bound manifest -> authenticate its components

Publication is content-addressed.  A component whose bytes are unchanged is
written once and shared by every generation that binds it, which is what keeps
repeated ``prepare`` from duplicating the dataset and what makes a shared
component survive the retirement of an older generation that also referenced it.
Nothing published here is ever overwritten or deleted in place, so constructing
a future generation cannot damage a dependency of the current one.

This is not a second currentness authority.  ``CampaignStore`` remains the sole
owner of which generation is current; a prepared manifest is inert content that
becomes meaningful only because a committed campaign state names its digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from ._common import (
    TrainingDataError,
    TrainingDataInputError,
    TrainingDataSerializationError,
    sha256_file_cached,
)

PREPARED_GENERATION_SCHEMA = "mdstats.mlff-prepared-generation.v1"
PREPARED_OBJECT_DIRECTORY = "objects"
PREPARED_MANIFEST_DIRECTORY = "generations"

#: Ordered prepared components.  The order is a construction order: every entry
#: may depend only on the entries before it.
PREPARED_COMPONENT_NAMES = (
    "manifest",
    "source_catalog",
    "frame_catalog",
    "source_authority",
    "frame_authority",
    "feature_evidence",
    "neutral_base",
    "split_exclusion",
    "aggregate",
    "common",
)


class PreparedGenerationError(TrainingDataError):
    """The prepared substrate bound to a campaign generation is unusable."""


class PreparedGenerationMissingError(PreparedGenerationError):
    """No prepared substrate is bound, or its published objects are absent."""


class PreparedGenerationConfigurationError(PreparedGenerationError):
    """Preparation-owned configuration changed after this generation was built."""


def prepared_generation_root(paths: Any) -> Path:
    """Campaign-owned root for immutable prepared-generation content."""

    return Path(paths.internal) / "prepared"


def _object_path(root: Path, digest_value: str) -> Path:
    return root / PREPARED_OBJECT_DIRECTORY / f"{digest_value}.json"


def _manifest_path(root: Path, digest_value: str) -> Path:
    return root / PREPARED_MANIFEST_DIRECTORY / f"{digest_value}.json"


def _encode(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _publish_bytes(path: Path, encoded: bytes) -> None:
    """Write immutable content exactly once; an existing identity is reused."""

    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _component_types() -> dict[str, Any]:
    import mdstats
    from .neutral_substrate import (
        CanonicalFrameAuthority,
        NeutralFeatureEvidence,
        NeutralSplitExclusionEvidence,
        NeutralStatisticalBase,
        SourceAuthority,
    )
    from .target_size_execution import TargetSizeCommonPreparation
    from .target_size_experiment import TargetSizeStatisticalAggregate

    return {
        "manifest": mdstats.TrainingDataManifest,
        "source_catalog": mdstats.TrainingDataSourceCatalog,
        "frame_catalog": mdstats.TrainingFrameCatalog,
        "source_authority": SourceAuthority,
        "frame_authority": CanonicalFrameAuthority,
        "feature_evidence": NeutralFeatureEvidence,
        "neutral_base": NeutralStatisticalBase,
        "split_exclusion": NeutralSplitExclusionEvidence,
        "aggregate": TargetSizeStatisticalAggregate,
        "common": TargetSizeCommonPreparation,
    }


def preparation_configuration_identity(cfg: Mapping[str, Any]) -> dict[str, str]:
    """Digest the configuration domain that owns preparation science.

    This is a pure projection of the campaign configuration through the two
    accepted policy owners.  It reads no data and touches no filesystem, so a
    downstream command can prove that the substrate it is about to consume was
    prepared under the configuration currently in force without reconstructing
    anything.  Configuration outside these owners -- cross-validation, final
    production, qualification, and execution scheduling -- deliberately has no
    influence here, because it cannot change prepared P1/P2 science.
    """

    from .campaign_target_size_runtime import resolve_neutral_partition_policy
    from .target_size_experiment import resolve_target_size_policy_from_config

    return {
        "neutral_partition_policy_digest": resolve_neutral_partition_policy(
            cfg
        ).policy_digest,
        "target_size_policy_digest": resolve_target_size_policy_from_config(
            cfg
        ).content_digest,
    }


@dataclass(frozen=True, slots=True)
class PreparedGenerationManifest:
    """Compact immutable membership of one prepared scientific generation."""

    component_digests: Mapping[str, str]
    frame_records: tuple[Mapping[str, Any], ...]
    scientific_identity: Mapping[str, str]
    common_preparation_digest: str
    preparation_configuration: Mapping[str, str]

    def changed_preparation_configuration(
        self, cfg: Mapping[str, Any]
    ) -> tuple[str, ...]:
        """Preparation-owned configuration fields that no longer agree."""

        observed = preparation_configuration_identity(cfg)
        return tuple(
            sorted(
                name
                for name, value in observed.items()
                if self.preparation_configuration.get(name) != value
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PREPARED_GENERATION_SCHEMA,
            "components": {
                name: self.component_digests[name] for name in PREPARED_COMPONENT_NAMES
            },
            "frame_members": [
                {
                    "run_id": str(record["run_id"]),
                    "relative_path": str(record["relative_path"]),
                    "sha256": str(record["sha256"]),
                    "storage_kind": str(record.get("storage_kind", "npz")),
                    "source_identity_signature": record["source_identity_signature"],
                    "source_control_bundle_signature": record[
                        "source_control_bundle_signature"
                    ],
                    "frame_count": int(record["frame_count"]),
                    "atom_count": int(record["atom_count"]),
                }
                for record in sorted(
                    self.frame_records, key=lambda item: str(item["run_id"])
                )
            ],
            "scientific_identity": dict(self.scientific_identity),
            "common_preparation_digest": self.common_preparation_digest,
            "preparation_configuration": dict(self.preparation_configuration),
        }

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(_encode(self._payload())).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return self._payload()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PreparedGenerationManifest:
        if payload.get("schema") != PREPARED_GENERATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported prepared-generation manifest schema."
            )
        components = payload.get("components")
        if not isinstance(components, Mapping) or set(components) != set(
            PREPARED_COMPONENT_NAMES
        ):
            raise TrainingDataSerializationError(
                "Prepared-generation manifest does not declare every component."
            )
        return cls(
            component_digests={
                name: str(components[name]) for name in PREPARED_COMPONENT_NAMES
            },
            frame_records=tuple(
                dict(record) for record in payload.get("frame_members", ())
            ),
            scientific_identity={
                str(key): str(value)
                for key, value in dict(payload.get("scientific_identity", {})).items()
            },
            common_preparation_digest=str(payload["common_preparation_digest"]),
            preparation_configuration={
                str(key): str(value)
                for key, value in dict(
                    payload.get("preparation_configuration", {})
                ).items()
            },
        )


def publish_prepared_generation(
    paths: Any,
    *,
    components: Mapping[str, Any],
    frame_records: Any,
    scientific_identity: Mapping[str, str],
    preparation_configuration: Mapping[str, str],
) -> PreparedGenerationManifest:
    """Publish one immutable prepared generation and return its manifest.

    Publication is complete before the caller may CAS-bind the manifest digest
    onto the campaign generation, so an interruption at any point leaves only
    unreachable content rather than a half-adopted generation.
    """

    missing = [name for name in PREPARED_COMPONENT_NAMES if name not in components]
    if missing:
        raise PreparedGenerationError(
            "A prepared generation must publish every component; missing: "
            + ", ".join(missing)
        )
    root = prepared_generation_root(paths)
    digests: dict[str, str] = {}
    for name in PREPARED_COMPONENT_NAMES:
        encoded = _encode(components[name].to_dict())
        digest_value = hashlib.sha256(encoded).hexdigest()
        _publish_bytes(_object_path(root, digest_value), encoded)
        digests[name] = digest_value
    manifest = PreparedGenerationManifest(
        component_digests=digests,
        frame_records=tuple(dict(record) for record in frame_records),
        scientific_identity=dict(scientific_identity),
        common_preparation_digest=components["common"].content_digest,
        preparation_configuration=dict(preparation_configuration),
    )
    _publish_bytes(
        _manifest_path(root, manifest.content_digest), _encode(manifest.to_dict())
    )
    return manifest


def read_prepared_generation_manifest(
    paths: Any, manifest_digest: str
) -> PreparedGenerationManifest:
    """Read and authenticate one published prepared-generation manifest."""

    path = _manifest_path(prepared_generation_root(paths), manifest_digest)
    if not path.is_file():
        raise PreparedGenerationMissingError(
            "The prepared scientific substrate bound to this campaign generation is "
            f"missing ({path}). Run `prepare` to build a fresh generation; downstream "
            "commands never reconstruct it from live sources."
        )
    if sha256_file_cached(path) != manifest_digest:
        raise PreparedGenerationError(
            "The published prepared-generation manifest does not match the digest "
            "bound by the campaign store. This is durable-state corruption, not a "
            "reason to rebuild the substrate implicitly."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreparedGenerationError(
            "The published prepared-generation manifest is unreadable."
        ) from exc
    return PreparedGenerationManifest.from_dict(payload)


def _read_component(root: Path, name: str, digest_value: str) -> Mapping[str, Any]:
    path = _object_path(root, digest_value)
    if not path.is_file():
        raise PreparedGenerationMissingError(
            f"Prepared component {name!r} is missing from this campaign generation "
            f"({path}). Run `prepare` to build a fresh generation."
        )
    if sha256_file_cached(path) != digest_value:
        raise PreparedGenerationError(
            f"Prepared component {name!r} does not match its published identity."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreparedGenerationError(
            f"Prepared component {name!r} is unreadable."
        ) from exc


def load_prepared_generation_components(
    paths: Any, manifest: PreparedGenerationManifest
) -> dict[str, Any]:
    """Materialize every prepared component through its accepted owner type."""

    root = prepared_generation_root(paths)
    types = _component_types()
    loaded: dict[str, Any] = {}
    for name in PREPARED_COMPONENT_NAMES:
        payload = _read_component(root, name, manifest.component_digests[name])
        try:
            if name == "aggregate":
                loaded[name] = types[name].from_dict(
                    payload,
                    frame_authority=loaded["frame_authority"],
                    neutral_base=loaded["neutral_base"],
                )
            else:
                loaded[name] = types[name].from_dict(payload)
        except TrainingDataError as exc:
            raise PreparedGenerationError(
                f"Prepared component {name!r} failed its owner validation: {exc}"
            ) from exc
    return loaded


def load_prepared_frame_data(
    paths: Any, manifest: PreparedGenerationManifest, source_catalog: Any
) -> dict[str, Any]:
    """Load exactly the immutable normalized members this generation bound."""

    from .frame_cache import load_frame_data_cache_records

    try:
        return load_frame_data_cache_records(
            source_catalog,
            manifest.frame_records,
            Path(paths.internal) / "frame-cache",
        )
    except (TrainingDataInputError, TrainingDataSerializationError) as exc:
        raise PreparedGenerationError(
            "The normalized frame members bound to this campaign generation are "
            f"missing or corrupt: {exc}. Run `prepare` to build a fresh generation; "
            "a downstream command never rebuilds them from live sources."
        ) from exc


def prepared_generation_protected_paths(paths: Any, manifest_digests: Any) -> set[Path]:
    """Every published path the named prepared generations still require.

    Storage owners derive reclaimability from this reachability view rather than
    from generation-local pathnames, so an immutable component or normalized
    frame member shared by two generations survives the retirement of either.
    """

    root = prepared_generation_root(paths)
    cache_root = Path(paths.internal) / "frame-cache"
    protected: set[Path] = set()
    for manifest_digest in manifest_digests:
        if not manifest_digest:
            continue
        manifest_path = _manifest_path(root, manifest_digest)
        if not manifest_path.is_file():
            continue
        protected.add(manifest_path)
        try:
            manifest = PreparedGenerationManifest.from_dict(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except Exception:
            continue
        for digest_value in manifest.component_digests.values():
            protected.add(_object_path(root, digest_value))
        for record in manifest.frame_records:
            member = cache_root / str(record["relative_path"])
            protected.add(member)
            if str(record.get("storage_kind")) == "npy_directory":
                protected.add(member.parent)
    return protected


__all__ = [
    "PREPARED_COMPONENT_NAMES",
    "PREPARED_GENERATION_SCHEMA",
    "PREPARED_MANIFEST_DIRECTORY",
    "PREPARED_OBJECT_DIRECTORY",
    "PreparedGenerationConfigurationError",
    "PreparedGenerationError",
    "PreparedGenerationManifest",
    "PreparedGenerationMissingError",
    "load_prepared_frame_data",
    "load_prepared_generation_components",
    "prepared_generation_protected_paths",
    "prepared_generation_root",
    "preparation_configuration_identity",
    "publish_prepared_generation",
    "read_prepared_generation_manifest",
]
