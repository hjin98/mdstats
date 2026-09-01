"""Storage, scratch, and inode admission as a first-class resource decision.

Bytes, inodes, metadata operations, and I/O bandwidth are real resources: an
archive that runs the filesystem out of space part-way through is a recovery
problem, not merely a slow operation.  Admission therefore bounds the peak -
not just the final - footprint of a storage operation before anything
destructive happens.

Storage pressure never changes science.  Nothing here can alter target
membership, precision, epochs, seed or qualification population, timestep,
acceptance thresholds, or a locked policy: an admission failure refuses the
storage operation and leaves the campaign exactly as it was.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .policy import StoragePolicy, storage_reserve_bytes

STORAGE_ADMISSION_SCHEMA = "mdstats.mlff-storage-admission.v1"


class StorageAdmissionError(RuntimeError):
    """A storage operation was refused before it could mutate anything."""


@dataclass(frozen=True, slots=True)
class AdmissionObservation:
    """The dynamic measurement one plan was admitted against.

    This is an execution observation, not policy.  It is recorded on the plan
    so a later apply can revalidate the *resource* question without touching
    any scientific identity, and so a changed disk causes admission
    revalidation rather than scientific invalidation.
    """

    location: str
    total_bytes: int
    free_bytes: int
    free_inodes: int
    reserve_bytes: int
    required_peak_bytes: int
    required_inodes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_ADMISSION_SCHEMA,
            "location": self.location,
            "total_bytes": int(self.total_bytes),
            "free_bytes": int(self.free_bytes),
            "free_inodes": int(self.free_inodes),
            "reserve_bytes": int(self.reserve_bytes),
            "required_peak_bytes": int(self.required_peak_bytes),
            "required_inodes": int(self.required_inodes),
        }

    @property
    def admitted(self) -> bool:
        headroom = int(self.free_bytes) - int(self.reserve_bytes)
        return headroom >= int(self.required_peak_bytes)


def observe_filesystem(location: str | os.PathLike[str]) -> tuple[int, int, int]:
    """Return ``(total_bytes, free_bytes, free_inodes)`` for one location.

    ``free_inodes`` is ``-1`` where the platform does not report an inode count;
    callers treat that as "unknown" rather than as "unlimited".
    """

    path = Path(location)
    usage = shutil.disk_usage(path)
    free_inodes = -1
    statvfs = getattr(os, "statvfs", None)
    if statvfs is not None:
        try:
            stats = statvfs(os.fspath(path))
            free_inodes = int(stats.f_favail)
        except OSError:
            free_inodes = -1
    return int(usage.total), int(usage.free), free_inodes


def admit_storage_operation(
    location: str | os.PathLike[str],
    policy: StoragePolicy,
    *,
    required_peak_bytes: int,
    required_inodes: int = 0,
) -> AdmissionObservation:
    """Admit or refuse one storage operation against real free resources.

    ``required_peak_bytes`` is the operation's *peak* temporary amplification -
    an archive's staged blob before its hot bytes are reclaimed, a restore's
    staging tree, a dedup temporary link - not its net effect.
    """

    total, free, free_inodes = observe_filesystem(location)
    observation = AdmissionObservation(
        location=str(Path(location)),
        total_bytes=total,
        free_bytes=free,
        free_inodes=free_inodes,
        reserve_bytes=storage_reserve_bytes(policy, total),
        required_peak_bytes=max(0, int(required_peak_bytes)),
        required_inodes=max(0, int(required_inodes)),
    )
    if not observation.admitted:
        raise StorageAdmissionError(
            f"Refusing the storage operation at {observation.location}: it needs a peak "
            f"{observation.required_peak_bytes} bytes but only "
            f"{observation.free_bytes - observation.reserve_bytes} bytes are available "
            f"above the {observation.reserve_bytes}-byte safety reserve. Nothing was "
            "modified."
        )
    if (
        observation.free_inodes >= 0
        and observation.required_inodes > 0
        and observation.free_inodes - int(policy.minimum_free_inodes)
        < observation.required_inodes
    ):
        raise StorageAdmissionError(
            f"Refusing the storage operation at {observation.location}: it needs "
            f"{observation.required_inodes} inodes but only "
            f"{observation.free_inodes} are free against a minimum headroom of "
            f"{policy.minimum_free_inodes}. Nothing was modified."
        )
    return observation


def revalidate_admission(
    observation: AdmissionObservation, policy: StoragePolicy
) -> AdmissionObservation:
    """Re-observe free resources immediately before mutation.

    A plan whose admission no longer holds is refused as a *resource* failure.
    The campaign's scientific identities are untouched by that refusal.
    """

    return admit_storage_operation(
        observation.location,
        policy,
        required_peak_bytes=observation.required_peak_bytes,
        required_inodes=observation.required_inodes,
    )


__all__ = [
    "STORAGE_ADMISSION_SCHEMA",
    "AdmissionObservation",
    "StorageAdmissionError",
    "admit_storage_operation",
    "observe_filesystem",
    "revalidate_admission",
]
