"""Dataset manifests and deterministic VASP source discovery for MLFF-DATA2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    read_mapping_file,
)

TRAINING_DATA_RUN_SPEC_SCHEMA = "mdstats.training-data-run-spec.v2"
TRAINING_DATA_RUN_SPEC_LEGACY_SCHEMA = "mdstats.training-data-run-spec.v1"
TRAINING_DATA_MANIFEST_SCHEMA = "mdstats.training-data-manifest.v1"
TRAINING_DATA_MANIFEST_VERSION = "mdstats.mlff-data2.manifest.2026-08.v2"


def _pairs(value: Mapping[str, Any] | None) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (str(key), json_value(item))
        for key, item in sorted((value or {}).items(), key=lambda pair: str(pair[0]))
    )


def _mapping(value: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return {key: json_value(item) for key, item in value}


@dataclass(frozen=True, slots=True)
class TrainingDataRunSpec:
    """One source locator plus reviewed assertions and non-operational inference evidence."""

    run_id: str
    vasprun: str
    companion_files: tuple[tuple[str, str], ...] = ()
    reference_group: str | None = None
    replica_id: str | None = None
    reference_run_id: str | None = None
    assertions: tuple[tuple[str, Any], ...] = ()
    inference: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.vasprun.strip():
            raise TrainingDataInputError("run_id and vasprun must be non-empty.")
        companions = tuple(
            sorted((str(role), str(path)) for role, path in self.companion_files)
        )
        if len({role for role, _ in companions}) != len(companions):
            raise TrainingDataInputError("Companion-file roles must be unique.")
        object.__setattr__(self, "companion_files", companions)
        object.__setattr__(
            self,
            "assertions",
            tuple(sorted((str(key), json_value(value)) for key, value in self.assertions)),
        )
        object.__setattr__(
            self,
            "inference",
            tuple(sorted((str(key), json_value(value)) for key, value in self.inference)),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DATA_RUN_SPEC_SCHEMA,
            "run_id": self.run_id,
            "vasprun": self.vasprun,
            "companion_files": dict(self.companion_files),
            "reference_group": self.reference_group,
            "replica_id": self.replica_id,
            "reference_run_id": self.reference_run_id,
            "assertions": _mapping(self.assertions),
            "inference": _mapping(self.inference),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDataRunSpec":
        schema = payload.get("schema")
        if schema not in (None, TRAINING_DATA_RUN_SPEC_SCHEMA, TRAINING_DATA_RUN_SPEC_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported training-data run schema.")
        companions = payload.get("companion_files", {})
        assertions = payload.get("assertions", {})
        inference = payload.get("inference", {})
        if not isinstance(companions, Mapping) or not isinstance(assertions, Mapping) or not isinstance(inference, Mapping):
            raise TrainingDataSerializationError(
                "companion_files, assertions, and inference must be mappings."
            )
        result = cls(
            run_id=str(payload["run_id"]),
            vasprun=str(payload["vasprun"]),
            companion_files=tuple(
                (str(role), str(path)) for role, path in companions.items()
            ),
            reference_group=(
                None if payload.get("reference_group") is None else str(payload["reference_group"])
            ),
            replica_id=(
                None if payload.get("replica_id") is None else str(payload["replica_id"])
            ),
            reference_run_id=(
                None
                if payload.get("reference_run_id") is None
                else str(payload["reference_run_id"])
            ),
            assertions=_pairs(assertions),
            inference=_pairs(inference),
        )
        provided_digest = payload.get("content_digest")
        accepted_digests = {None, result.content_digest}
        if schema == TRAINING_DATA_RUN_SPEC_LEGACY_SCHEMA:
            legacy_payload = {
                "schema": TRAINING_DATA_RUN_SPEC_LEGACY_SCHEMA,
                "run_id": result.run_id,
                "vasprun": result.vasprun,
                "companion_files": dict(result.companion_files),
                "reference_group": result.reference_group,
                "replica_id": result.replica_id,
                "reference_run_id": result.reference_run_id,
                "assertions": _mapping(result.assertions),
            }
            accepted_digests.add(digest(legacy_payload))
        if provided_digest not in accepted_digests:
            raise TrainingDataSerializationError("Training-data run digest mismatch.")
        return result

    def resolve(self, base_directory: str | Path) -> tuple[Path, dict[str, Path]]:
        base = Path(base_directory)
        primary = Path(self.vasprun)
        if not primary.is_absolute():
            primary = base / primary
        companions: dict[str, Path] = {}
        for role, locator in self.companion_files:
            path = Path(locator)
            companions[role] = path if path.is_absolute() else base / path
        return primary, companions


@dataclass(frozen=True, slots=True)
class TrainingDataManifest:
    dataset_id: str
    system_profile: str
    runs: tuple[TrainingDataRunSpec, ...]
    manifest_version: str = TRAINING_DATA_MANIFEST_VERSION
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.system_profile.strip():
            raise TrainingDataInputError("dataset_id and system_profile are required.")
        if not self.runs:
            raise TrainingDataInputError("A training-data manifest requires at least one run.")
        runs = tuple(sorted(self.runs, key=lambda item: item.run_id))
        if len({run.run_id for run in runs}) != len(runs):
            raise TrainingDataInputError("Manifest run_id values must be unique.")
        known = {run.run_id for run in runs}
        missing = sorted(
            run.reference_run_id
            for run in runs
            if run.reference_run_id is not None and run.reference_run_id not in known
        )
        if missing:
            raise TrainingDataInputError(
                "Unknown reference_run_id values: " + ", ".join(missing)
            )
        object.__setattr__(self, "runs", runs)
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DATA_MANIFEST_SCHEMA,
            "manifest_version": self.manifest_version,
            "dataset_id": self.dataset_id,
            "system_profile": self.system_profile,
            "runs": [run.to_dict() for run in self.runs],
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDataManifest":
        if payload.get("schema") not in (None, TRAINING_DATA_MANIFEST_SCHEMA):
            raise TrainingDataSerializationError("Unsupported training-data manifest schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            system_profile=str(payload.get("system_profile", "generic")),
            runs=tuple(TrainingDataRunSpec.from_dict(item) for item in payload.get("runs", ())),
            manifest_version=str(
                payload.get("manifest_version", TRAINING_DATA_MANIFEST_VERSION)
            ),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        provided_digest = payload.get("content_digest")
        legacy_payload_digest = digest(
            {str(key): value for key, value in payload.items() if key != "content_digest"}
        )
        if provided_digest not in (None, result.content_digest, legacy_payload_digest):
            raise TrainingDataSerializationError("Training-data manifest digest mismatch.")
        return result

    @classmethod
    def load(cls, path: str | Path) -> "TrainingDataManifest":
        return cls.from_dict(read_mapping_file(path))


def _run_id(relative_parent: Path) -> str:
    raw = "run" if str(relative_parent) in {"", "."} else relative_parent.as_posix()
    result = re.sub(r"[^A-Za-z0-9_.-]+", "__", raw).strip("._-")
    return result or "run"


def discover_vasp_manifest(
    root: str | Path,
    *,
    dataset_id: str,
    system_profile: str = "generic",
    pattern: str = "**/vasprun.xml",
) -> TrainingDataManifest:
    """Discover VASP XML files without inferring scientific labels from paths."""

    base = Path(root)
    if not base.is_dir():
        raise TrainingDataInputError(f"Discovery root is not a directory: {base!s}.")
    paths = tuple(sorted(path for path in base.glob(pattern) if path.is_file()))
    if not paths:
        raise TrainingDataInputError(
            f"No VASP XML files matched {pattern!r} below {base!s}."
        )
    used: dict[str, int] = {}
    runs: list[TrainingDataRunSpec] = []
    for path in paths:
        relative = path.relative_to(base)
        # Production archives are often delivered as flat, descriptively named
        # XML files rather than one ``vasprun.xml`` per run directory.  Preserve
        # those filename identities instead of collapsing every root-level file
        # to ``run``, while retaining the established directory-derived identity
        # for the canonical nested layout.
        if str(relative.parent) in {"", "."}:
            candidate = (
                "run"
                if relative.name.lower() == "vasprun.xml"
                else _run_id(Path(relative.stem))
            )
        else:
            candidate = _run_id(relative.parent)
        occurrence = used.get(candidate, 0)
        used[candidate] = occurrence + 1
        run_id = candidate if occurrence == 0 else f"{candidate}__{occurrence + 1}"
        runs.append(TrainingDataRunSpec(run_id=run_id, vasprun=relative.as_posix()))
    return TrainingDataManifest(
        dataset_id=dataset_id,
        system_profile=system_profile,
        runs=tuple(runs),
        notes=(
            "Generated by deterministic source discovery; automatic metadata inference has not yet been applied.",
        ),
    )
