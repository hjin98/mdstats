"""User-facing MLFF campaign orchestration.

This module intentionally keeps the public workflow small.  Scientific records remain
owned by the existing DATA2-DATA9B modules; this file coordinates them through one
configuration, one SQLite state database, and a compact results directory.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from collections import Counter, deque
from contextlib import contextmanager
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from enum import Enum
import argparse
import ast
import csv
import fcntl
import gc
import hashlib
import json
import math
import tempfile
import threading
import os
import re
import urllib.parse
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import textwrap
import time
import tomllib
import warnings
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from .progress_timing import (
    ProgressRateTracker,
    format_progress_fraction,
    format_progress_rate,
    format_progress_time,
    format_progress_timing_fields,
)
from .storage_accounting import (
    CampaignOwnershipBoundary,
    CompositeRetentionFence,
    build_campaign_storage_report,
    configured_protected_inputs,
)
from .storage_reclamation import filesystem_identity
from .campaign_target_size_retention import build_target_size_retention_fence
from .campaign_target_size_state import (
    TargetSizeCampaignStateError,
    TargetSizeLifecycle,
)

from . import _observation
from ._common import (
    TrainingDataSerializationError,
    configure_sha256_receipt_store,
    digest,
    sha256_file_cached,
    validate_digest,
)
from ._frame_access import ase_atoms_for_frame, build_frame_array_index
from .mace_compatibility import (
    format_mace_runtime_compatibility_summary,
    mace_runtime_warning_handled,
    mace_runtime_warning_scope,
)
from .resources import (
    available_memory_bytes,
    build_stage_resource_scope,
    configure_worker_thread_environment,
    detect_system_resources,
    resolve_worker_count,
    stage_resource_scope,
)
from .training_parallel import (
    AdaptiveTrainingConcurrency,
    TrainingConcurrencyPolicy,
    build_training_concurrency_plan,
    query_gpu_telemetry,
)
from .inference_parallel import (
    AdaptiveInferenceConcurrency,
    CpuTelemetryProbe,
    InferenceConcurrencyPolicy,
    InferenceLease,
    build_inference_concurrency_plan,
    inference_start_signal,
    inference_cancellation_requested,
    mark_inference_workload_started,
    report_inference_worker_phase,
)

# 0.20.100a0 changes plotting policy, 0.20.101a0 changes evaluation execution
# topology, 0.20.103a0 changes orchestration/telemetry/control-plane execution,
# 0.20.104a0 repairs source packaging, 0.20.105a0 repairs progress timing,
# 0.20.106a0 implements EVAL-MF1 nested multi-fidelity checkpoint evaluation,
# 0.20.107a0 implements EVAL-MF2 conservative survivor/reporting/default migration,
# 0.20.108a0 implements PREC1 precision profiles/schedule identity, and
# 0.20.109a0 implements the PREC2 staged-transition/restart runtime substrate, and
# 0.20.110a0 implements PREC3 profile activation/reporting/cross-stage deployment, and
# 0.20.111a0 implements STOR1 read-only storage accounting/ownership boundaries, and
# 0.20.112a0 is a warning-condensation hotfix for MACE/PyTorch evaluation/runtime noise, and
# 0.20.113a0 implements STOR2 authenticated nonselected-checkpoint compaction, and
# 0.20.114a0 implements STOR3 lifecycle-safe automatic reclamation/audit manifests, and
# 0.20.115a0 implements STOR4 manual tiered reclamation/capability plans, and
# 0.20.116a0 implements STOR5 immutable deduplication and authenticated cold archive/restore, and
# 0.20.117a0 consolidates the four storage-management CLI commands under `storage`, and
# the storage/I-O reset replaces the STOR1-STOR5 tier policy with the owner-driven
# inventory/plan/executor, cold archive v2, and owner-certified deduplication.
# None changes the frozen MLFF scientific/materialization identity, so existing
# 0.20.99a0 campaign state and prediction caches remain reusable.
MLFF_DATA9B3_VERSION = "0.20.99a0"
# Parallel scheduling does not change scientific case identity. Keep the
# historical runtime token so already-authenticated execution caches remain
# readable by storage tooling.
VERIFICATION_RUNTIME_COMPATIBILITY_VERSION = "0.20.85a0"
CAMPAIGN_CLI_SCHEMA = "mdstats.mlff-campaign-cli.v2"
_LEGACY_CAMPAIGN_CLI_SCHEMA = "mdstats.mlff-campaign-cli.v1"
FOUNDATION_CONFIG_CONTRACT_SCHEMA = "mdstats.mlff-foundation-config-contract.v2"
CAMPAIGN_STATE_SCHEMA = "mdstats.mlff-campaign-state.v2"
EXTERNAL_RECORD_POINTER_SCHEMA = "mdstats.mlff-campaign-external-record.v1"
# Current writes use generation-neutral identities.  Obsolete derived
# target-size receipts are handled only by the reject-only cutover detector;
# they are never represented by a current public constant or deserialized here.
CURRENT_PREPARE_RESTART_RECEIPT_SCHEMA = "mdstats.mlff-campaign-prepare-restart.current.v1"
CURRENT_PREPARE_CONTRACT_VERSION = "mdstats.mlff-campaign-prepare.current.v1"
EXTERNAL_RECORD_THRESHOLD_BYTES = 4 * 1024 * 1024
DEFAULT_CONFIG_NAME = "campaign.toml"
DEFAULT_MANIFEST_NAME = "campaign-manifest.json"


class CampaignCliError(RuntimeError):
    """A concise, user-actionable campaign failure."""


class StageState(str, Enum):
    NOT_STARTED = "not_started"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


#: The current public campaign operations, in lifecycle order.  Storage safety
#: checks use this sequence to detect an operation that is still running; the
#: public status/advance projection is derived from the owning current
#: authorities rather than from this static list.
PIPELINE = (
    ("doctor", "environment and input checks"),
    ("prepare", "current target-size scientific substrate; selects nothing"),
    ("target_size_selection", "paired optimizer-seed target-size screen"),
    (
        "post_selection_cross_validation",
        "post-selection cross-validation on exactly T_selected",
    ),
    (
        "post_selection_final_production",
        "fresh final production on the complete selected dataset",
    ),
)


@dataclass(frozen=True)
class CampaignPaths:
    config: Path
    config_dir: Path
    workspace: Path
    state_db: Path
    manifest: Path
    internal: Path
    data: Path
    runs: Path
    models: Path
    results: Path

    @classmethod
    def from_config(cls, config_path: str | Path, cfg: Mapping[str, Any]) -> "CampaignPaths":
        config = Path(config_path).expanduser().resolve()
        config_dir = config.parent
        workspace_value = cfg.get("campaign", {}).get("workspace", "mlff-campaign")
        workspace = _resolve_path(workspace_value, config_dir)
        manifest_value = cfg.get("data", {}).get("manifest", DEFAULT_MANIFEST_NAME)
        manifest = _resolve_path(manifest_value, workspace)
        internal = workspace / ".mdstats"
        return cls(
            config=config,
            config_dir=config_dir,
            workspace=workspace,
            state_db=internal / "campaign.sqlite3",
            manifest=manifest,
            internal=internal,
            data=workspace / "data",
            runs=workspace / "runs",
            models=workspace / "models",
            results=workspace / "results",
        )

    def ensure(self) -> None:
        for path in (self.workspace, self.internal, self.data, self.runs, self.models, self.results):
            path.mkdir(parents=True, exist_ok=True)


def _campaign_ownership_boundary(
    cfg: Mapping[str, Any],
    paths: "CampaignPaths",
    store: "CampaignStore | None" = None,
) -> CampaignOwnershipBoundary:
    """Build the deletion-authority boundary every destructive path must use.

    Beyond the configured user/reference inputs, the boundary carries the
    target-size retention fence so that promoted P3 execution evidence which the
    current generation can still legitimately adopt is never unlinked by
    cleanup, deduplication, or archival - including in the window after P3
    published a head but before the campaign store adopted it.
    """

    protected_inputs = configured_protected_inputs(
        cfg, config_dir=paths.config_dir, config_path=paths.config
    )
    from .qualification.store import build_qualification_retention_fence

    fences: list[Any] = []
    if store is not None:
        stale_hours = max(0.25, float(_cfg(cfg, "cleanup", "stale_age_hours", 6.0)))
        fences.append(
            build_target_size_retention_fence(
                store, paths.workspace, publication_window_seconds=stale_hours * 3600.0
            )
        )
    # Durable P7 release evidence and the artifacts an in-flight qualification
    # attempt still references are protected for a different reason than P3
    # execution evidence, so they contribute a second reduction rather than
    # being folded into the target-size fence's reachability model.
    qualification_fence = build_qualification_retention_fence(paths)
    if qualification_fence.is_active:
        fences.append(qualification_fence)
    fence = None
    if len(fences) == 1:
        fence = fences[0]
    elif fences:
        fence = CompositeRetentionFence(tuple(fences))
    return CampaignOwnershipBoundary(
        paths.workspace, protected_inputs=protected_inputs, retention_fence=fence
    )




@dataclass(frozen=True)
class _TrainingMethodSpec:
    mode: str
    seeds: tuple[int, ...]
    cross_validation_folds: int = 0
    fold_partition_seed: int = 104729
    seed_mode: str = "optimizer_only"

    def __post_init__(self) -> None:
        allowed = {"naive_fine_tuning", "multihead_replay"}
        if self.mode not in allowed:
            raise CampaignCliError(
                f"Unsupported training mode {self.mode!r}; choose one of {sorted(allowed)}."
            )
        seeds = tuple(int(value) for value in self.seeds)
        if not seeds or len(set(seeds)) != len(seeds) or any(value < 0 for value in seeds):
            raise CampaignCliError(
                f"[training.{self.mode}].seeds must contain unique nonnegative integers."
            )
        folds = int(self.cross_validation_folds)
        if folds == 1 or folds < 0:
            raise CampaignCliError(
                f"[training.{self.mode}].cross_validation_folds must be 0 (final-only) "
                "or at least 2."
            )
        partition_seed = int(self.fold_partition_seed)
        if partition_seed < 0:
            raise CampaignCliError(
                f"[training.{self.mode}].fold_partition_seed must be nonnegative."
            )
        seed_mode = str(self.seed_mode).strip().lower()
        if seed_mode not in {"optimizer_only", "optimizer_and_cv_partition"}:
            raise CampaignCliError(
                f"[training.{self.mode}].seed_mode must be optimizer_only or optimizer_and_cv_partition."
            )
        object.__setattr__(self, "seeds", seeds)
        object.__setattr__(self, "cross_validation_folds", folds)
        object.__setattr__(self, "fold_partition_seed", partition_seed)
        object.__setattr__(self, "seed_mode", seed_mode)








def _observational_campaign_state_active() -> bool:
    return _observation.observational()


@contextmanager
def observational_campaign_state() -> Iterable[None]:
    """Forbid this invocation from creating or writing managed campaign state.

    The capability is carried by :mod:`._observation`, so it reaches every
    nested owner helper and every worker thread this invocation spawns rather
    than only the store the command opened itself.  Nothing process-global is
    toggled: a concurrent consequential command keeps its own writable receipt
    and store behavior while this block runs.

    Receipts are a pure acceleration cache - losing one only forces a fresh byte
    hash - but the cache is itself a managed artifact this package inventories,
    so an observational command reads it without ever writing to it.
    """

    with _observation.observing():
        yield


#: Advisory lock file every campaign-state writer takes before mutating.
#:
#: It sits beside the database rather than inside it because the competing
#: writer is normally a second CLI process, which no in-process mutex can see.
CAMPAIGN_WRITER_LOCK_SUFFIX = ".writer-lock"


@dataclass
class _CampaignWriterGate:
    """The single writer gate for one campaign database, shared process-wide.

    Two properties have to hold at once and neither is optional.

    *Reentrancy belongs to a thread, not to an object.* An instance-level depth
    counter would let thread B see thread A's nonzero depth, conclude it was
    already inside, and mutate the database without ever taking the lock. The
    ``RLock`` gives reentrancy to exactly the thread that owns it and blocks
    every other one.

    *The gate is per database, not per object.* Two ``CampaignStore`` instances
    for the same file in one process are the same writer, so they share one
    entry here; the ``flock`` beneath handles the second *process*.
    """

    lock: threading.RLock = field(default_factory=threading.RLock)
    depth: int = 0
    handle: int | None = None


_CAMPAIGN_WRITER_GATES: dict[str, _CampaignWriterGate] = {}
_CAMPAIGN_WRITER_GATES_LOCK = threading.Lock()


def _campaign_writer_gate(lock_path: Path) -> _CampaignWriterGate:
    key = str(Path(os.path.abspath(os.fspath(lock_path))))
    with _CAMPAIGN_WRITER_GATES_LOCK:
        gate = _CAMPAIGN_WRITER_GATES.get(key)
        if gate is None:
            gate = _CampaignWriterGate()
            _CAMPAIGN_WRITER_GATES[key] = gate
        return gate


def _sqlite_readonly_uri(path: Path) -> str:
    """A genuinely read-only SQLite URI for one existing database file.

    Escaping matters: a campaign workspace path can contain characters that a
    URI would otherwise reinterpret, and `?` in particular would silently split
    the path from the query string and open the wrong database.
    """

    quoted = urllib.parse.quote(str(Path(path).resolve()))
    return f"file:{quoted}?mode=ro"


def _declared_relative_paths(payload: Any) -> set[str]:
    """Every ``relative_path`` a sharded-record manifest declares, at any depth."""

    found: set[str] = set()
    if isinstance(payload, Mapping):
        value = payload.get("relative_path")
        if isinstance(value, str):
            found.add(value)
        for item in payload.values():
            found |= _declared_relative_paths(item)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            found |= _declared_relative_paths(item)
    return found


class CampaignStore:
    """Single-file durable state for orchestration records and stage summaries."""

    def __init__(self, path: str | Path, *, create: bool = True):
        """Open the campaign state database.

        ``create=False`` is the observational open used by read-only storage
        paths: it will not create the directory, will not initialize a schema,
        and will not turn on write-through SHA-256 receipts. Describing a
        campaign must never be what brings its state into existence.
        """

        self.path = Path(path)
        if _observational_campaign_state_active():
            # An observational invocation cannot be made consequential by a
            # nested helper that happens to open the store for itself, on this
            # thread or on any worker it spawned.
            create = False
        self.read_only = not create
        if not create:
            if not self.path.is_file():
                raise CampaignCliError(
                    f"Campaign state database is missing: {self.path}. It is reported "
                    "as uninitialized rather than created by an observational command."
                )
            self._db_local = threading.local()
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db_local = threading.local()
        configure_sha256_receipt_store(self.path.parent / "hash-receipts.sqlite3")
        # Schema bootstrap is a real write. Leaving it outside the common
        # exclusion would let a second process construct a store and mutate the
        # database while maintenance believed every supported writer was
        # excluded, so construction joins the writer census like anything else.
        with self.writer_exclusion(), self._connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=DELETE;
                PRAGMA synchronous=NORMAL;
                PRAGMA busy_timeout=30000;
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records (
                    key TEXT PRIMARY KEY,
                    class_name TEXT NOT NULL,
                    digest TEXT,
                    payload TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stages (
                    name TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    message TEXT NOT NULL,
                    updated_utc TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    level TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS target_size_campaign_state (
                    state_revision TEXT PRIMARY KEY,
                    sequence INTEGER NOT NULL UNIQUE,
                    predecessor_revision TEXT UNIQUE,
                    transition_identity TEXT NOT NULL UNIQUE,
                    transition_kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    committed_utc TEXT NOT NULL
                );
                """
            )
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", ("schema", CAMPAIGN_STATE_SCHEMA))

    def _connect(self) -> sqlite3.Connection:
        """Return one persistent SQLite connection per calling thread.

        Campaign orchestration performs many tiny record/meta lookups. Reopening
        SQLite for every operation was measurable control-plane overhead, while
        sharing a connection across worker threads would violate sqlite3's
        thread-affinity contract. A thread-local connection gives us pooling
        without weakening that ownership rule.
        """

        db = getattr(self._db_local, "connection", None)
        if db is None:
            if self.read_only:
                # An observational open is enforced by SQLite itself, not by the
                # convention that no nested helper ever calls a write path. The
                # connection cannot create the file, a journal, a schema row, or
                # anything else, and `query_only` refuses a write even if some
                # future caller reaches one.
                db = sqlite3.connect(
                    _sqlite_readonly_uri(self.path), uri=True, timeout=30.0
                )
                db.execute("PRAGMA query_only=ON")
            else:
                db = sqlite3.connect(self.path, timeout=30.0)
            db.execute("PRAGMA busy_timeout=30000")
            self._db_local.connection = db
        return db

    @property
    def writer_lock_path(self) -> Path:
        return Path(str(self.path) + CAMPAIGN_WRITER_LOCK_SUFFIX)

    @contextmanager
    def writer_exclusion(self) -> Iterable[None]:
        """Exclude every other campaign-state writer, in this process or another.

        SQLite serializes individual statements, but an expensive maintenance
        decision needs more than that: the free-page measurement that authorizes
        a whole-file ``VACUUM`` has to still be true when the rewrite starts, and
        another process committing in between would invalidate it. A thread-only
        mutex cannot express that, because the competing writer is usually a
        second CLI invocation.

        So every product write path takes this one gate first, and maintenance
        holds it across its final predicate, its admission recheck, and the
        rewrite itself. Reentrancy is owned by the acquiring *thread*, the gate
        is shared by every store instance for the same database, and the
        ``flock`` beneath it is per open file description and therefore
        genuinely cross-process. The kernel releases it on any exit, so a crash
        can never leave writers permanently blocked.

        Lock order is single and cycle-free: a storage operation takes the
        storage-operation lease and the owner publication seams *before* it
        reaches campaign-state maintenance, and nothing holding this gate ever
        reaches back for those.
        """

        self._require_writable("take the campaign-state writer exclusion")
        lock_path = self.writer_lock_path
        gate = _campaign_writer_gate(lock_path)
        gate.lock.acquire()
        try:
            if gate.depth == 0:
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                handle = os.open(
                    lock_path,
                    os.O_CREAT | os.O_RDWR | os.O_CLOEXEC,
                    0o644,
                )
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                except BaseException:
                    os.close(handle)
                    raise
                gate.handle = handle
            gate.depth += 1
            try:
                yield
            finally:
                gate.depth -= 1
                if gate.depth == 0 and gate.handle is not None:
                    handle, gate.handle = gate.handle, None
                    try:
                        fcntl.flock(handle, fcntl.LOCK_UN)
                    finally:
                        os.close(handle)
        finally:
            gate.lock.release()

    def _require_writable(self, operation: str) -> None:
        """Refuse a mutation on an observational store before it starts.

        SQLite would refuse this too, but a clear owner error names the real
        problem - an observational command reached a write path - instead of
        surfacing a generic read-only database error from three helpers down.
        """

        if self.read_only:
            raise CampaignCliError(
                f"Refusing to {operation}: this campaign state database was opened "
                "for observation only. A read-only storage command never changes "
                "managed campaign state; run the consequential command explicitly."
            )

    @contextmanager
    def exclusive_transaction(self) -> Iterable[sqlite3.Connection]:
        """Yield one real serialized SQLite write transaction.

        Target-size campaign transitions must compare the expected predecessor
        authority and write the successor inside a single transaction.  A
        deferred transaction would let two writers both read the same
        predecessor and then race on the write, so the write lock is taken up
        front with ``BEGIN IMMEDIATE``.  The caller owns the compare/write
        logic; this method owns only transaction lifetime.
        """

        self._require_writable("open a campaign write transaction")
        db = self._connect()
        if db.in_transaction:
            raise CampaignCliError(
                "A campaign write transaction is already active on this connection; "
                "campaign CAS transitions must not nest."
            )
        with self.writer_exclusion():
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.rollback()
                raise
            db.commit()

    def close(self) -> None:
        db = getattr(self._db_local, "connection", None)
        if db is not None:
            try:
                db.close()
            finally:
                self._db_local.connection = None

    @property
    def external_record_directory(self) -> Path:
        return self.path.parent / "records"

    def certify_closed_external_record(
        self, entry: str | Path
    ) -> tuple[bool, str, tuple[str, ...]]:
        """Whether this owner certifies every descendant of one payload entry.

        ``records/`` is this store's private externalized-payload area.  This
        owner creates it, is its only writer, and delegates no part of it to any
        other component - which is what makes a closed-subtree statement here a
        truthful ownership claim rather than a containment guess.  Contrast the
        post-selection run tree, whose contents are written by a configured
        third-party trainer and therefore need an explicit recorded membership.

        The claim is still refused for anything this owner cannot have written
        (symlinks, special files), and for a sharded record the authenticated
        manifest bounds the member set exactly, so a foreign file dropped inside
        one withholds authority over the whole entry.

        Returns ``(certified, detail, nodes)`` where nodes are
        ``(posix relative path, kind)`` pairs relative to ``entry`` itself.
        """

        from .data4_sharded_store import DATA4_SHARDED_MANIFEST_SCHEMA
        from .storage.owners import (
            NODE_DIRECTORY,
            NODE_FILE,
            observed_node_kind,
        )

        root = Path(entry)
        root_kind = observed_node_kind(root)
        if root_kind == "symlink":
            return False, "a symlink is never a record payload this owner wrote", ()
        if root_kind == NODE_FILE:
            return True, "single-file external record payload", ()
        if root_kind != NODE_DIRECTORY:
            return False, f"{root} is neither a payload file nor a payload directory", ()

        observed: list[tuple[str, str]] = []
        for path in sorted(root.rglob("*")):
            kind = observed_node_kind(path)
            if kind == "symlink":
                return False, (
                    f"record payload contains a symlink this owner did not write: {path.name}"
                ), ()
            if kind not in (NODE_FILE, NODE_DIRECTORY):
                return False, (
                    f"record payload contains a special file: {path.name}"
                ), ()
            # Directories are recorded as nodes too: a recursive removal makes
            # them disappear, so an unrecorded empty directory must be covered
            # rather than swept along.
            observed.append((path.relative_to(root).as_posix(), kind))

        manifest_path = root / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                return False, f"record manifest is unreadable ({exc})", ()
            if manifest.get("schema") == DATA4_SHARDED_MANIFEST_SCHEMA:
                declared = {"manifest.json", *_declared_relative_paths(manifest)}
                extra = sorted(
                    path for path, kind in observed
                    if kind == NODE_FILE and path not in declared
                )
                if extra:
                    return False, (
                        "sharded record contains descendant(s) its manifest does not "
                        f"declare: {extra[:5]}"
                    ), ()
                return True, (
                    "sharded external record whose descendants are exactly what its "
                    "authenticated manifest declares"
                ), tuple(sorted(observed))
        return True, (
            "external record payload in this owner's exclusively written record area"
        ), tuple(sorted(observed))

    def _write_external_payload(self, key: str, payload: Mapping[str, Any]) -> tuple[str, str]:
        """Stream a large JSON record to content-addressed storage.

        The encoder writes incrementally, avoiding a second giant in-memory JSON
        string.  SQLite stores only a small, checksummed pointer.
        """

        directory = self.external_record_directory
        directory.mkdir(parents=True, exist_ok=True)
        encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        hasher = hashlib.sha256()
        byte_count = 0
        fd, temporary_name = tempfile.mkstemp(prefix="record-", suffix=".json.tmp", dir=directory)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                for text_chunk in encoder.iterencode(payload):
                    chunk = text_chunk.encode("utf-8")
                    handle.write(chunk)
                    hasher.update(chunk)
                    byte_count += len(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            sha256 = hasher.hexdigest()
            destination = directory / f"{sha256}.json"
            if destination.exists():
                temporary.unlink()
            else:
                os.replace(temporary, destination)
            pointer = {
                "schema": EXTERNAL_RECORD_POINTER_SCHEMA,
                "relative_path": str(destination.relative_to(self.path.parent)),
                "sha256": sha256,
                "size_bytes": byte_count,
                "record_key": key,
            }
            return json.dumps(pointer, sort_keys=True, separators=(",", ":")), sha256
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def _read_external_payload(self, pointer: Mapping[str, Any], *, key: str) -> dict[str, Any]:
        if pointer.get("schema") != EXTERNAL_RECORD_POINTER_SCHEMA:
            raise CampaignCliError(f"Stored campaign record pointer is invalid: {key}.")
        relative = Path(str(pointer.get("relative_path", "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise CampaignCliError(f"Stored campaign record pointer escapes the campaign workspace: {key}.")
        path = (self.path.parent / relative).resolve()
        root = self.path.parent.resolve()
        if root not in path.parents:
            raise CampaignCliError(f"Stored campaign record pointer escapes the campaign workspace: {key}.")
        if not path.is_file():
            raise CampaignCliError(f"External campaign record is missing for {key}: {path}")
        expected = str(pointer.get("sha256", ""))
        actual = _sha256(path)
        if not expected or actual != expected:
            raise CampaignCliError(f"External campaign record checksum mismatch for {key}: {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise CampaignCliError(f"External campaign record is invalid: {key}.")
        return payload

    def set_meta(self, key: str, value: Any) -> None:
        self._require_writable("write campaign metadata")
        encoded = json.dumps(value, sort_keys=True)
        with self.writer_exclusion(), self._connect() as db:
            db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, encoded))

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self._connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return default if row is None else json.loads(row[0])

    def _encode_record_for_storage(self, key: str, record: Any) -> tuple[str, str | None, str]:
        """Return ``(class_name, digest, payload_json)`` for one record."""

        # DATA4 contains hundreds of thousands of nested scientific records.
        # Persist it as checksummed JSONL shards before calling ``to_dict`` so
        # campaign state never creates a second multi-gigabyte object graph.
        from .data4_bundle import Data4FeatureBundle
        from .data4_sharded_store import write_data4_sharded_record
        from .data6_bundle import Data6FeatureBundle
        from .data6_sharded_store import write_data6_sharded_record

        if isinstance(record, Data4FeatureBundle):
            pointer = write_data4_sharded_record(
                record, self.external_record_directory, record_key=key
            )
            encoded = json.dumps(pointer, sort_keys=True, separators=(",", ":"))
            return type(record).__name__, record.content_digest, encoded
        if isinstance(record, Data6FeatureBundle):
            pointer = write_data6_sharded_record(
                record, self.external_record_directory, record_key=key
            )
            encoded = json.dumps(pointer, sort_keys=True, separators=(",", ":"))
            return type(record).__name__, record.content_digest, encoded

        payload = record.to_dict() if hasattr(record, "to_dict") else record
        if not isinstance(payload, Mapping):
            raise CampaignCliError(f"Record {key!r} is not JSON-mappable.")
        record_digest = payload.get("content_digest")
        if record_digest is None and hasattr(record, "content_digest"):
            record_digest = record.content_digest
        class_name = type(record).__name__ if hasattr(record, "to_dict") else "mapping"

        force_external = key in {"frame_catalog", "data4", "data6"}
        if force_external:
            encoded, _ = self._write_external_payload(key, payload)
        else:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            if len(encoded.encode("utf-8")) >= EXTERNAL_RECORD_THRESHOLD_BYTES:
                encoded, _ = self._write_external_payload(key, payload)
        return class_name, record_digest, encoded

    def put_record(self, key: str, record: Any) -> None:
        self._require_writable("write a campaign record")
        class_name, record_digest, encoded = self._encode_record_for_storage(key, record)
        with self.writer_exclusion(), self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO records(key,class_name,digest,payload,updated_utc) VALUES (?,?,?,?,?)",
                (key, class_name, record_digest, encoded, _utc_now()),
            )

    def put_records(self, records: Mapping[str, Any]) -> None:
        """Persist several compact orchestration records in one transaction.

        Large sharded/external payloads are fully materialized before the SQLite
        transaction begins, so filesystem work never holds the database write
        lock. This method is for naturally atomic parent-side record groups.
        """

        self._require_writable("write campaign records")
        if not records:
            return
        self._require_writable("replace campaign records")
        encoded_rows: list[tuple[str, str, str | None, str, str]] = []
        timestamp = _utc_now()
        for key, record in records.items():
            class_name, record_digest, encoded = self._encode_record_for_storage(
                str(key), record
            )
            encoded_rows.append(
                (str(key), class_name, record_digest, encoded, timestamp)
            )
        with self.writer_exclusion(), self._connect() as db:
            db.executemany(
                "INSERT OR REPLACE INTO records(key,class_name,digest,payload,updated_utc) VALUES (?,?,?,?,?)",
                encoded_rows,
            )

    def replace_records_atomically(
        self, records: Mapping[str, Any], *, delete_keys: Sequence[str] = ()
    ) -> None:
        """Atomically delete stale aliases and publish one replacement record set.

        All record serialization/externalization happens before the SQLite write
        transaction. The database transaction then performs deletions and alias
        replacement together so incompatible authority generations cannot become
        partially mixed after interruption.
        """

        encoded_rows: list[tuple[str, str, str | None, str, str]] = []
        timestamp = _utc_now()
        for key, record in records.items():
            class_name, record_digest, encoded = self._encode_record_for_storage(
                str(key), record
            )
            encoded_rows.append((str(key), class_name, record_digest, encoded, timestamp))
        delete = tuple(dict.fromkeys(str(key) for key in delete_keys if str(key)))
        with self.writer_exclusion(), self._connect() as db:
            if delete:
                db.executemany("DELETE FROM records WHERE key=?", ((key,) for key in delete))
            if encoded_rows:
                db.executemany(
                    "INSERT OR REPLACE INTO records(key,class_name,digest,payload,updated_utc) VALUES (?,?,?,?,?)",
                    encoded_rows,
                )

    def _decode_record_payload(self, key: str, encoded: str) -> dict[str, Any]:
        payload = json.loads(encoded)
        if not isinstance(payload, dict):
            raise CampaignCliError(f"Stored campaign record is invalid: {key}.")
        if payload.get("schema") == EXTERNAL_RECORD_POINTER_SCHEMA:
            return self._read_external_payload(payload, key=key)
        return payload

    def get_payload_optional(self, key: str) -> dict[str, Any] | None:
        """Fetch one optional payload with one SQL query and one JSON decode."""

        with self._connect() as db:
            row = db.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        payload = self._decode_record_payload(key, row[0])
        from .data4_sharded_store import DATA4_SHARDED_POINTER_SCHEMA
        from .data6_sharded_store import DATA6_SHARDED_POINTER_SCHEMA
        if payload.get("schema") in {
            DATA4_SHARDED_POINTER_SCHEMA,
            DATA6_SHARDED_POINTER_SCHEMA,
        }:
            raise CampaignCliError(
                f"Record {key!r} uses memory-bounded scientific shards; request it with get_record()."
            )
        return payload

    def get_payload(self, key: str) -> dict[str, Any]:
        payload = self.get_payload_optional(key)
        if payload is None:
            raise CampaignCliError(f"Required campaign record is missing: {key}. Run `status` for the next step.")
        return payload

    def _record_from_encoded_payload(self, key: str, encoded: str, cls: type[Any]) -> Any:
        payload = self._decode_record_payload(key, encoded)
        from .data4_bundle import Data4FeatureBundle
        from .data4_sharded_store import (
            DATA4_SHARDED_POINTER_SCHEMA, Data4ShardedStoreError,
            read_data4_sharded_record,
        )
        if cls is Data4FeatureBundle and isinstance(payload, Mapping) and payload.get("schema") == DATA4_SHARDED_POINTER_SCHEMA:
            try:
                return read_data4_sharded_record(
                    payload, self.path.parent,
                    progress_callback=lambda message: print(f"[DATA4 restore] {message}", flush=True),
                )
            except Data4ShardedStoreError as exc:
                raise CampaignCliError(str(exc)) from exc
        from .data6_bundle import Data6FeatureBundle
        from .data6_sharded_store import (
            DATA6_SHARDED_POINTER_SCHEMA, Data6ShardedStoreError,
            read_data6_sharded_record,
        )
        if cls is Data6FeatureBundle and isinstance(payload, Mapping) and payload.get("schema") == DATA6_SHARDED_POINTER_SCHEMA:
            try:
                return read_data6_sharded_record(
                    payload, self.path.parent,
                    progress_callback=lambda message: print(f"[DATA6 restore] {message}", flush=True),
                )
            except Data6ShardedStoreError as exc:
                raise CampaignCliError(str(exc)) from exc
        if payload.get("schema") in {
            DATA4_SHARDED_POINTER_SCHEMA,
            DATA6_SHARDED_POINTER_SCHEMA,
        }:
            raise CampaignCliError(
                f"Record {key!r} uses memory-bounded scientific shards but was requested as {cls.__name__}."
            )
        return cls.from_dict(payload)

    def get_record_optional(self, key: str, cls: type[Any]) -> Any | None:
        """Fetch one optional scientific record without a has/get double query."""

        with self._connect() as db:
            row = db.execute("SELECT payload FROM records WHERE key=?", (key,)).fetchone()
        if row is None:
            return None
        return self._record_from_encoded_payload(key, row[0], cls)

    def get_record(self, key: str, cls: type[Any]) -> Any:
        record = self.get_record_optional(key, cls)
        if record is None:
            raise CampaignCliError(f"Required campaign record is missing: {key}. Run `status` for the next step.")
        return record

    def has_record(self, key: str) -> bool:
        with self._connect() as db:
            return db.execute("SELECT 1 FROM records WHERE key=?", (key,)).fetchone() is not None

    def record_digest(self, key: str) -> str | None:
        """Return the persisted scientific digest without deserializing a record."""

        with self._connect() as db:
            row = db.execute("SELECT digest FROM records WHERE key=?", (key,)).fetchone()
        if row is None:
            raise CampaignCliError(
                f"Required campaign record is missing: {key}. Run `status` for the next step."
            )
        return None if row[0] in (None, "") else str(row[0])

    def record_keys(self, prefix: str = "") -> tuple[str, ...]:
        with self._connect() as db:
            rows = db.execute("SELECT key FROM records WHERE key LIKE ? ORDER BY key", (prefix + "%",)).fetchall()
        return tuple(row[0] for row in rows)

    def delete_records(self, prefix: str) -> None:
        """Delete compact orchestration pointers while leaving native artifacts intact."""

        self._require_writable("delete campaign records")
        with self.writer_exclusion(), self._connect() as db:
            db.execute("DELETE FROM records WHERE key LIKE ?", (prefix + "%",))

    def delete_record(self, key: str) -> None:
        self._require_writable("delete a campaign record")
        with self.writer_exclusion(), self._connect() as db:
            db.execute("DELETE FROM records WHERE key=?", (key,))

    def storage_references(self) -> tuple[Path, ...]:
        """Return external files/directories reachable from current records."""

        from .data4_sharded_store import DATA4_SHARDED_POINTER_SCHEMA
        from .data6_sharded_store import DATA6_SHARDED_POINTER_SCHEMA

        references: set[Path] = set()
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM records").fetchall()
        root = self.path.parent.resolve()
        for (encoded,) in rows:
            try:
                payload = json.loads(encoded)
            except Exception:
                continue
            if not isinstance(payload, Mapping):
                continue
            schema = payload.get("schema")
            if schema not in {
                EXTERNAL_RECORD_POINTER_SCHEMA,
                DATA4_SHARDED_POINTER_SCHEMA,
                DATA6_SHARDED_POINTER_SCHEMA,
            }:
                continue
            relative = Path(str(payload.get("relative_path", "")))
            if relative.is_absolute() or ".." in relative.parts or relative in {Path(""), Path(".")}:
                continue
            candidate = (root / relative).resolve()
            if root == candidate or root not in candidate.parents:
                continue
            references.add(candidate)
            if schema in {
                DATA4_SHARDED_POINTER_SCHEMA,
                DATA6_SHARDED_POINTER_SCHEMA,
            }:
                references.add(candidate.parent)
        return tuple(sorted(references))

    def prune_events(self, *, maximum_events: int = 10_000) -> int:
        """Bound diagnostic history to the newest ``maximum_events`` rows.

        This is the cheap half of campaign-state maintenance and is deliberately
        separate from :meth:`vacuum`. Deleting rows costs one small transaction;
        rewriting the whole database file does not, and one excess diagnostic
        event is not a reason to pay for the second.

        The delete takes the write lock up front so it serializes against any
        other campaign writer rather than assuming this process is the only one.

        The resolved policy bound is executed **exactly**. There is deliberately
        no floor here: a hidden clamp would make the plan, the policy identity,
        and the audit record all describe a retention the execution never
        applied. If the product ever needs a minimum retained diagnostic count,
        it belongs in policy resolution, before the value is hashed and planned.
        """

        self._require_writable("prune campaign diagnostic events")
        maximum_events = max(0, int(maximum_events))
        with self.exclusive_transaction() as db:
            before = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
            db.execute(
                "DELETE FROM events WHERE id NOT IN "
                "(SELECT id FROM events ORDER BY id DESC LIMIT ?)",
                (maximum_events,),
            )
            after = int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        return max(0, before - after)

    def vacuum(self) -> None:
        """Rewrite the database file to return free pages to the filesystem.

        Expensive and independently decided: the caller establishes that the
        rewrite is worth its cost and that there is room for the copy SQLite
        makes beside the original, and it does so while already holding
        :meth:`writer_exclusion` so that measurement cannot go stale before the
        rewrite starts. Entering the exclusion here as well is reentrant and
        makes a direct call safe on its own.
        """

        self._require_writable("rewrite the campaign state database")
        db = self._connect()
        if db.in_transaction:
            raise CampaignCliError(
                "Refusing to rewrite the campaign state database inside an open "
                "transaction; VACUUM owns the whole file."
            )
        with self.writer_exclusion():
            db.execute("PRAGMA optimize")
            db.execute("VACUUM")
            db.commit()

    def set_stage(self, name: str, state: StageState, message: str) -> None:
        self._require_writable("record a campaign stage")
        timestamp = _utc_now()
        with self.writer_exclusion(), self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO stages(name,state,message,updated_utc) VALUES (?,?,?,?)",
                (name, state.value, message, timestamp),
            )
            db.execute(
                "INSERT INTO events(timestamp_utc,level,stage,message) VALUES (?,?,?,?)",
                (timestamp, "info" if state is not StageState.FAILED else "error", name, message),
            )

    def stage(self, name: str) -> tuple[StageState, str]:
        with self._connect() as db:
            row = db.execute("SELECT state,message FROM stages WHERE name=?", (name,)).fetchone()
        if row is None:
            return StageState.NOT_STARTED, "not started"
        return StageState(row[0]), row[1]

    def event(self, level: str, stage: str, message: str) -> None:
        self._require_writable("record a campaign event")
        with self.writer_exclusion(), self._connect() as db:
            db.execute(
                "INSERT INTO events(timestamp_utc,level,stage,message) VALUES (?,?,?,?)",
                (_utc_now(), level, stage, message),
            )


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()




def _process_rss_mib() -> float:
    """Best-effort current resident-set size for progress diagnostics."""

    try:
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # Linux reports KiB; macOS reports bytes.
        return value / (1024.0 if sys.platform != "darwin" else 1024.0 * 1024.0)
    except Exception:
        return float("nan")


def _resolve_path(value: str | Path, base: Path) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


def _load_config(
    path: str | Path, *, ensure: bool = True
) -> tuple[dict[str, Any], CampaignPaths]:
    """Resolve configuration and campaign paths.

    ``ensure=False`` inspects a campaign without materializing its directory
    layout. Observational storage commands use it so that reporting on a
    campaign cannot be what creates its workspace.
    """

    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise CampaignCliError(f"Configuration not found: {config_path}. Run `init` first.")
    with config_path.open("rb") as handle:
        cfg = tomllib.load(handle)
    if cfg.get("schema") not in (None, _LEGACY_CAMPAIGN_CLI_SCHEMA, CAMPAIGN_CLI_SCHEMA):
        raise CampaignCliError(f"Unsupported campaign configuration schema: {cfg.get('schema')!r}.")
    _normalize_target_size_fidelity_config(cfg)
    paths = CampaignPaths.from_config(config_path, cfg)
    if ensure:
        paths.ensure()
    # TRAIN2A migration authority is configuration-level and must fail on every
    # command, not only when DATA8 is rebuilt. Historical configs without an
    # explicit policy_generation remain under their original semantics.
    _validate_train2_migration_config(cfg)
    _normalize_foundation_config_in_memory(cfg)
    _validate_canonical_foundation_head_aliases(cfg)
    return cfg, paths


def _normalize_target_size_fidelity_config(cfg: dict[str, Any]) -> None:
    """Normalize the one current target-size authoring surface before use.

    Schema-less/v1 TRAIN2 files have historical fixed semantics.  The three
    former target-size-looking keys were never active authorities, so only
    their exact historical spelling can be tolerated during this transition.
    """

    target_data = cfg.setdefault("target_data", {})
    if not isinstance(target_data, dict):
        raise CampaignCliError("[target_data] must be a TOML table.")
    size_cfg = target_data.setdefault("size_convergence", {})
    if not isinstance(size_cfg, dict):
        raise CampaignCliError("[target_data.size_convergence] must be a TOML table.")
    training = cfg.setdefault("training", {})
    if not isinstance(training, dict):
        raise CampaignCliError("[training] must be a TOML table.")

    legacy_keys = {
        "coarse_training_epochs": 3,
        "short_training_epochs": 10,
        "final_training_epochs": 30,
    }
    schema = cfg.get("schema")
    has_tuple = "fidelity_epochs" in size_cfg
    present_legacy = {key: size_cfg[key] for key in legacy_keys if key in size_cfg}
    if schema == CAMPAIGN_CLI_SCHEMA:
        if not has_tuple:
            raise CampaignCliError(
                "Campaign schema v2 requires [target_data.size_convergence].fidelity_epochs."
            )
        if present_legacy:
            raise CampaignCliError(
                "Campaign schema v2 rejects retired target-size epoch keys: "
                + ", ".join(sorted(present_legacy))
            )
        return
    if has_tuple:
        raise CampaignCliError(
            "Historical campaign schema cannot contain fidelity_epochs; set schema to "
            f"{CAMPAIGN_CLI_SCHEMA!r} and use the v2 configuration contract."
        )
    bad = {
        key: value for key, value in present_legacy.items()
        if value != legacy_keys[key]
    }
    if bad:
        raise CampaignCliError(
            "Historical target-size epoch-looking keys were not runtime authorities and "
            "cannot be reconstructed with non-historical values: "
            + ", ".join(f"{key}={value!r}" for key, value in sorted(bad.items()))
        )
    if present_legacy:
        warnings.warn(
            "Historical target-size epoch-looking keys are ignored; v1 records retain "
            "historical fixed (3, 10, 30) evidence, while a rebuilt current screen "
            "starts at (1, 3, 10). Migrate to campaign schema v2 to configure it.",
            UserWarning,
            stacklevel=3,
        )
    # Canonical in-memory resolved policy for old campaigns.  It is never
    # written back as v2 configuration.  Historical 3/10/30 screen evidence
    # stays historical; a rebuilt current screen starts from 1/3/10.
    size_cfg["fidelity_epochs"] = [1, 3, 10]


def _normalize_foundation_config_in_memory(cfg: dict[str, Any]) -> None:
    """Normalize legacy foundation settings without rewriting campaign TOML.

    MH1-CONFIG1 makes ``[foundation]`` the canonical configuration namespace.
    Historical 0.20.177a0-and-earlier MPA-0 campaign files contain only
    ``[model].foundation_name``; those are unambiguous enough to normalize to
    the singleton MPA-0/default contract in memory.  Unknown head-blind legacy
    foundations remain untouched so a later strict foundation-resolution gate
    can fail them closed rather than guessing multi-head semantics.
    """

    section = cfg.get("foundation")
    if isinstance(section, Mapping):
        family = str(section.get("family", "")).strip()
        head = str(section.get("head", "")).strip()
        if not family:
            raise CampaignCliError("[foundation].family must be non-empty when [foundation] is present.")
        if not head:
            raise CampaignCliError("[foundation].head must be non-empty when [foundation] is present.")
        try:
            from .foundation import MaceFoundationFamily

            canonical_family = MaceFoundationFamily.parse(family).value
        except Exception as exc:
            raise CampaignCliError(f"Invalid [foundation].family: {exc}") from exc
        if isinstance(section, dict):
            section["family"] = canonical_family
        return

    model = cfg.get("model", {})
    legacy_name = str(model.get("foundation_name", "")).strip() if isinstance(model, Mapping) else ""
    normalized = legacy_name.lower().replace("-", "_").replace(" ", "_")
    if "mpa_0" in normalized or "mpa0" in normalized:
        cfg["foundation"] = {
            "family": "mace_mpa_0",
            "head": "default",
            "label": legacy_name or "MACE-MPA-0",
            "legacy_normalized": True,
        }


def _foundation_config(cfg: Mapping[str, Any]) -> Mapping[str, Any]:
    section = cfg.get("foundation")
    if not isinstance(section, Mapping):
        raise CampaignCliError(
            "Campaign has no canonical [foundation] section and its legacy foundation could not be "
            "normalized safely. Add [foundation].family and [foundation].head explicitly."
        )
    return section




def _validate_canonical_foundation_head_aliases(cfg: Mapping[str, Any]) -> None:
    """Reject conflicting source-head selectors in generalized campaigns.

    Historical head-blind MPA-0 TOML retains its original evaluation/PES aliases
    until MH1-EVAL1 migration.  A campaign that already declares canonical
    ``[foundation]`` semantics, however, may not independently point those old
    selectors at a different source head.  New templates omit the aliases.
    """

    foundation = cfg.get("foundation")
    if not isinstance(foundation, Mapping) or bool(foundation.get("legacy_normalized", False)):
        return
    canonical_head = str(foundation.get("head", "")).strip()
    for section_name, key in (
        ("evaluation", "replay_baseline_head"),
        ("verification", "pes_foundation_head"),
    ):
        section = cfg.get(section_name, {})
        if not isinstance(section, Mapping):
            continue
        value = section.get(key)
        alias = "" if value is None else str(value).strip()
        if alias and alias != canonical_head:
            raise CampaignCliError(
                f"[{section_name}].{key}={alias!r} conflicts with canonical "
                f"[foundation].head={canonical_head!r}. Remove the legacy selector or make it identical."
            )


def _cfg(cfg: Mapping[str, Any], section: str, key: str, default: Any = None) -> Any:
    return cfg.get(section, {}).get(key, default)


def _foundation_configuration_contract(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Return the pre-preparation configuration identity for source foundation policy.

    This is intentionally a configuration contract, not a scientific checkpoint
    identity.  MH1-INF1 will bind the inspected model bytes/architecture.  CONFIG1
    needs only to guarantee that family, selected source head, and requested
    acceleration cannot change unnoticed between doctor runs.
    """

    foundation = _foundation_config(cfg)
    acceleration = cfg.get("acceleration", {})
    if not isinstance(acceleration, Mapping):
        raise CampaignCliError("[acceleration] must be a TOML table.")
    source_backend = str(acceleration.get("backend", "e3nn")).strip().lower()
    training_backend = str(acceleration.get("training_backend", source_backend)).strip().lower()
    if source_backend not in {"cueq", "e3nn"}:
        raise CampaignCliError("[acceleration].backend must be 'cueq' or 'e3nn'.")
    if training_backend not in {"cueq", "e3nn"}:
        raise CampaignCliError("[acceleration].training_backend must be 'cueq' or 'e3nn'.")
    payload = {
        "schema": FOUNDATION_CONFIG_CONTRACT_SCHEMA,
        "family": str(foundation.get("family", "")).strip(),
        "head": str(foundation.get("head", "")).strip(),
        "source_backend": source_backend,
        "training_backend": training_backend,
        "phase_separated": "training_backend" in acceleration,
        "only_cueq": bool(acceleration.get("only_cueq", False)),
        "require_available": bool(acceleration.get("require_available", True)),
    }
    payload["content_digest"] = digest(payload)
    return payload


def _acceleration_policy(cfg: Mapping[str, Any]) -> Any:
    """Return the explicit, protocol-frozen MACE acceleration choice."""

    import mdstats

    backend = str(_cfg(cfg, "acceleration", "backend", "e3nn")).strip().lower()
    if backend == "auto":
        raise CampaignCliError(
            "[acceleration].backend='auto' is not permitted in an active campaign. "
            "Run `init` to resolve the environment once, or choose 'cueq'/'e3nn' explicitly."
        )
    try:
        return mdstats.MaceAccelerationPolicy(
            backend=mdstats.MaceAccelerationBackend(backend),
            only_cueq=bool(_cfg(cfg, "acceleration", "only_cueq", False)),
            require_available=bool(_cfg(cfg, "acceleration", "require_available", True)),
        )
    except Exception as exc:
        raise CampaignCliError(f"Invalid [acceleration] policy: {exc}") from exc



def _training_acceleration_policy(cfg: Mapping[str, Any]) -> Any:
    """Return the protocol-frozen TRAIN2 acceleration choice.

    Revision-60 campaigns carry an explicit ``training_backend`` so source
    inference/DATA6/evaluation can remain e3nn while TRAIN2 uses pure CuEq.
    Historical campaigns without that key preserve their original unified
    backend semantics exactly.
    """

    import mdstats

    table = cfg.get("acceleration", {})
    if not isinstance(table, Mapping):
        raise CampaignCliError("[acceleration] must be a TOML table.")
    source_backend = str(table.get("backend", "e3nn")).strip().lower()
    backend = str(table.get("training_backend", source_backend)).strip().lower()
    if backend == "auto":
        raise CampaignCliError(
            "[acceleration].training_backend='auto' is not permitted in an active campaign. "
            "Choose 'cueq' or 'e3nn' explicitly."
        )
    try:
        return mdstats.MaceAccelerationPolicy(
            backend=mdstats.MaceAccelerationBackend(backend),
            only_cueq=bool(table.get("only_cueq", False)),
            require_available=bool(table.get("require_available", True)),
        )
    except Exception as exc:
        raise CampaignCliError(f"Invalid TRAIN2 [acceleration] policy: {exc}") from exc


def _phase_separated_acceleration(cfg: Mapping[str, Any]) -> bool:
    table = cfg.get("acceleration", {})
    return bool(isinstance(table, Mapping) and "training_backend" in table)


def _training_acceleration_parity_policy() -> Any:
    """Return the stable-channel TRAIN2/source CuEq/e3nn parity policy.

    Revision 86 restores the conventional FP32 ``rtol=1e-5, atol=1e-6``
    authority for energy/stress/descriptors.  Force parity is no longer
    authorized by this one-shot allclose policy; FP32 TRAIN2 force equivalence
    is governed by :func:`_training_acceleration_noise_normalized_policy`.
    """

    import mdstats

    return mdstats.MaceAccelerationParityPolicy(
        float32_rtol=1.0e-5,
        float32_atol=1.0e-6,
        float64_rtol=1.0e-10,
        float64_atol=1.0e-12,
    )


def _training_acceleration_noise_normalized_policy() -> Any:
    """Return the permanent TRAIN2 FP32 warm-up/all-pairs force parity policy."""

    import mdstats

    return mdstats.TrainingAccelerationNoiseNormalizedParityPolicy(
        repeat_count=10,
        warmup_count=1,
        stable_channel_abs_ceiling=1.0e-6,
        force_distribution_quantile=99.0,
        force_distribution_ratio_ceiling=1.25,
        force_max_self_factor=1.5,
        force_max_absolute_ceiling=1.0e-4,
        force_threshold=1.0e-5,
    )


_BINARY_PRECISION_DTYPES = {"single": "float32", "double": "float64"}
_RETIRED_PRECISION_PROFILES = {"refine", "mixed"}


def _legacy_precision_schedule_policy(cfg: Mapping[str, Any]) -> Any | None:
    """Deserialize the pre-ADAPT-PREC1 staged schedule without authorizing it.

    Historical schedule records remain readable for status/storage/reporting.  New
    production execution must use :func:`_binary_model_precision_contract`, which
    rejects staged/refine semantics and never returns this policy to DATA8/runtime.
    """

    import mdstats

    training = cfg.get("training", {})
    precision = training.get("precision")
    if precision is None:
        return None
    if not isinstance(precision, Mapping):
        raise CampaignCliError("[training.precision] must be a TOML table.")
    stage_payloads = precision.get("stage")
    if not isinstance(stage_payloads, list) or not stage_payloads:
        raise CampaignCliError(
            "[training.precision] requires one or more [[training.precision.stage]] tables."
        )
    try:
        stages = tuple(
            mdstats.PrecisionStage(
                dtype=str(item["dtype"]),
                fraction=float(item["fraction"]),
                learning_rate_scale=float(item.get("learning_rate_scale", 1.0)),
            )
            for item in stage_payloads
        )
        profile = str(_cfg(cfg, "campaign", "precision_profile", "custom")).strip() or "custom"
        policy = mdstats.PrecisionSchedulePolicy(
            requested_profile=profile,
            stages=stages,
            minimum_final_stage_epochs=int(precision.get("minimum_final_stage_epochs", 0)),
            minimum_final_stage_gradient_updates=int(
                precision.get("minimum_final_stage_gradient_updates", 0)
            ),
            preserve_optimizer_state=bool(precision.get("preserve_optimizer_state", True)),
            preserve_scheduler_state=bool(precision.get("preserve_scheduler_state", True)),
            preserve_ema_state=bool(precision.get("preserve_ema_state", True)),
            model_dtype=str(_cfg(cfg, "model", "dtype", training.get("dtype", "float32"))),
            critical_operation_dtype=str(
                precision.get("critical_operation_dtype", "float64")
            ),
            evaluation_dtype=str(_cfg(cfg, "evaluation", "dtype", training.get("dtype", "float32"))),
            verification_dtype=str(_cfg(cfg, "verification", "dtype", training.get("dtype", "float32"))),
            export_dtype=str(cfg.get("export", {}).get("dtype", training.get("dtype", "float32"))),
        )
    except Exception as exc:
        raise CampaignCliError(f"Invalid historical staged precision configuration: {exc}") from exc
    training_dtype = str(training.get("dtype", stages[0].dtype))
    if training_dtype != stages[0].dtype:
        raise CampaignCliError(
            "[training].dtype must equal the first historical [[training.precision.stage]].dtype."
        )
    mode = str(precision.get("mode", policy.mode))
    if mode != policy.mode:
        raise CampaignCliError(
            f"[training.precision].mode={mode!r} disagrees with the historical stage count; "
            f"expected {policy.mode!r}."
        )
    return policy


def _binary_model_precision_contract(
    cfg: Mapping[str, Any],
    *,
    allow_historical_refine: bool = False,
) -> dict[str, Any]:
    """Resolve the ADAPT-PREC1 learned-model dtype and validate all inference surfaces.

    The precision mode controls only learned-model arithmetic.  mdstats-owned critical
    reductions/statistics/MD bookkeeping remain FP64 and are not a user-selectable mode.
    """

    campaign = cfg.get("campaign", {})
    training = cfg.get("training", {})
    model = cfg.get("model", {})
    requested = campaign.get("precision_profile")
    requested_text = "" if requested is None else str(requested).strip().lower()

    historical = _legacy_precision_schedule_policy(cfg)
    if requested_text in _RETIRED_PRECISION_PROFILES or (
        historical is not None and len(historical.stages) > 1
    ):
        if allow_historical_refine:
            if historical is None:
                raise CampaignCliError(
                    "Historical staged precision evidence is incomplete: the configuration names "
                    f"{requested_text!r} but contains no explicit schedule."
                )
            return {
                "requested_profile": historical.requested_profile,
                "model_dtype": historical.model_dtype,
                "historical_schedule": historical,
                "historical_read_only": True,
            }
        raise CampaignCliError(
            "The staged `refine`/`mixed` precision mode is retired for production campaigns. "
            "Choose `single` (FP32 learned model) or `double` (FP64 learned model). "
            "Historical staged evidence remains readable through status/storage/reporting, "
            "but cannot be resumed or silently reinterpreted under the binary precision contract."
        )

    # Pre-PREC/one-stage configurations are scientifically equivalent when every
    # learned-model inference surface already agrees on one dtype.  Infer the binary
    # label only when the profile is absent/legacy; explicit unknown profile names fail.
    if requested_text in _BINARY_PRECISION_DTYPES:
        profile = requested_text
        expected_dtype = _BINARY_PRECISION_DTYPES[profile]
        source = "explicit"
    elif requested_text in {"", "legacy", "legacy_custom", "custom"}:
        inferred_dtype = str(training.get("dtype", model.get("dtype", "float32")))
        if inferred_dtype not in {"float32", "float64"}:
            raise CampaignCliError(f"Unsupported learned-model dtype {inferred_dtype!r}.")
        profile = "single" if inferred_dtype == "float32" else "double"
        expected_dtype = inferred_dtype
        source = "legacy_inferred"
    else:
        raise CampaignCliError(
            f"Unsupported precision profile {requested_text!r}. New campaigns support only "
            "`single` and `double`."
        )

    observed = {
        "[model].dtype": str(model.get("dtype", expected_dtype)),
        "[training].dtype": str(training.get("dtype", expected_dtype)),
        "[evaluation].dtype": str(cfg.get("evaluation", {}).get("dtype", expected_dtype)),
        "[verification].dtype": str(cfg.get("verification", {}).get("dtype", expected_dtype)),
        "[export].dtype": str(cfg.get("export", {}).get("dtype", expected_dtype)),
    }
    mismatches = [f"{name}={value!r}" for name, value in observed.items() if value != expected_dtype]
    if mismatches:
        raise CampaignCliError(
            f"Precision profile `{profile}` requires learned-model dtype {expected_dtype} for "
            "training and every model-inference/export surface; mismatches: " + ", ".join(mismatches)
        )

    # Old single/double TOMLs may still contain a one-stage [training.precision]
    # table. Validate it, but deliberately do not return it to DATA8/runtime; this
    # makes staged transition machinery unreachable from the binary production path.
    if historical is not None:
        if len(historical.stages) != 1:
            raise CampaignCliError("Binary precision cannot carry a staged training schedule.")
        stage = historical.stages[0]
        if stage.dtype != expected_dtype or abs(stage.fraction - 1.0) > 1.0e-12:
            raise CampaignCliError(
                "Historical one-stage precision metadata disagrees with the binary model dtype."
            )
        if abs(stage.learning_rate_scale - 1.0) > 1.0e-12:
            raise CampaignCliError(
                "Binary precision does not support a precision-stage learning-rate scale."
            )

    return {
        "requested_profile": profile,
        "model_dtype": expected_dtype,
        "source": source,
        "historical_schedule": historical,
        "historical_read_only": False,
    }










def _optimizer_policy(
    cfg: Mapping[str, Any],
    *,
    seed: int,
    num_workers: int,
    paths: CampaignPaths | None = None,
    planned_epochs: int | None = None,
) -> Any:
    """Build one protocol-frozen optimizer policy under binary model precision."""

    import mdstats

    contract = _binary_model_precision_contract(cfg)
    model_dtype = str(contract["model_dtype"])
    realization = None if paths is None else _stored_training_acceleration_realization(
        cfg, paths, require_qualified=True
    )
    training_acceleration = _training_acceleration_policy(cfg)
    return mdstats.MaceOptimizerPolicy(
        learning_rate=float(_cfg(cfg, "training", "learning_rate", 1.0e-4)),
        batch_size=int(_cfg(cfg, "training", "batch_size", 2)),
        valid_batch_size=int(_cfg(cfg, "training", "valid_batch_size", 2)),
        num_workers=num_workers,
        max_num_epochs=(
            int(_cfg(cfg, "training", "max_num_epochs", 30))
            if planned_epochs is None else int(planned_epochs)
        ),
        eval_interval=int(_cfg(cfg, "training", "eval_interval", 1)),
        default_dtype=model_dtype,
        device=str(_cfg(cfg, "training", "device", "cuda")),
        seed=seed,
        critical_precision_policy=mdstats.MaceCriticalPrecisionPolicy(),
        acceleration_policy=training_acceleration,
        acceleration_realization_digest=(None if realization is None else realization.content_digest),
        resolved_acceleration_kernel_mode=(None if realization is None else realization.training_kernel_mode),
        precision_schedule_policy=None,
    )


#: Configured training-policy families that name the retired pre-V7 target-size
#: generation.  They are recognised only so an obsolete campaign configuration
#: can be rejected with actionable reset guidance; no retired policy, schedule,
#: or derived target-size record is ever read forward from them.
RETIRED_TRAINING_POLICY_GENERATIONS = frozenset(
    {"adaptive", "adaptive_stop", "adaptive_stop_v3", "legacy"}
)

#: The only training-policy family the current runtime implements.
CURRENT_TRAINING_POLICY_GENERATION = "train2"


def _training_policy_generation(cfg: Mapping[str, Any]) -> str:
    """Return the current training-policy family, rejecting retired generations.

    The current architecture has exactly one training-policy family.  The
    retired ``adaptive_stop_v3`` generation owned the retired
    FEAS1/MVIDX1/MVSEL2/REPAIR2/MVQUAL2 target-size topology, and there is no
    runtime that can serve both: a workspace configured for it is rejected here,
    before any campaign record is opened, so retired derived target-size state is
    never deserialized, reused, or reinterpreted as current authority.
    """

    value = str(
        _cfg(cfg, "training", "policy_generation", "")
    ).strip().lower()
    if value == CURRENT_TRAINING_POLICY_GENERATION:
        return CURRENT_TRAINING_POLICY_GENERATION
    if not value:
        raise CampaignCliError(
            "[training].policy_generation is missing. A configuration without an "
            "explicit policy generation is a retired pre-V7 campaign: the current "
            "target-size architecture is not a migration of it. Set "
            '[training].policy_generation = "train2" and run `prepare`, which '
            "performs the one-time destructive target-size cutover and rebuilds "
            "current authority from the source inputs."
        )
    if value in RETIRED_TRAINING_POLICY_GENERATIONS:
        raise CampaignCliError(
            f"[training].policy_generation = {value!r} names the retired pre-V7 "
            "target-size generation. Its selector, role-domain, coverage-selection, "
            "and selected-size records are never migrated or read forward. Set "
            '[training].policy_generation = "train2" and run `prepare` to perform '
            "the one-time destructive target-size cutover, which quarantines the "
            "retired records and reprepares current authority from the source "
            "inputs."
        )
    raise CampaignCliError(
        '[training].policy_generation must be "train2".'
    )


def _explicit_config_key(cfg: Mapping[str, Any], section: str, key: str) -> bool:
    table = cfg.get(section, {})
    return isinstance(table, Mapping) and key in table


def _validate_train2_migration_config(cfg: Mapping[str, Any]) -> None:
    """Fail closed when TRAIN2 is mixed with historical adaptive controls."""

    if _training_policy_generation(cfg) != "train2":
        return
    legacy = (
        ("training", "target_stop_fraction"),
        ("training", "replay_stop_multiplier"),
        ("training", "minimum_epochs_before_adaptive_stop"),
        ("training", "replay_degradation_budget_mev_per_a"),
        ("evaluation", "target_score_weight"),
        ("evaluation", "replay_score_weight"),
        ("acceptance", "maximum_replay_degradation_fraction"),
    )
    conflicts = [f"[{section}].{key}" for section, key in legacy if _explicit_config_key(cfg, section, key)]
    if conflicts:
        raise CampaignCliError(
            "TRAIN2 configuration cannot silently reinterpret historical adaptive-stop/"
            "replay-weighted controls. Remove or deliberately migrate: " + ", ".join(conflicts)
        )






def _precision_template(profile: str) -> dict[str, str]:
    """Resolve one ADAPT-PREC1 init profile into TOML-visible model dtypes."""

    normalized = str(profile).strip().lower()
    if normalized not in _BINARY_PRECISION_DTYPES:
        if normalized in _RETIRED_PRECISION_PROFILES:
            raise CampaignCliError(
                "The staged `refine`/`mixed` precision mode is retired. "
                "Choose `single` or `double`."
            )
        raise CampaignCliError(
            f"Unsupported precision profile {profile!r}; choose `single` or `double`."
        )
    dtype = _BINARY_PRECISION_DTYPES[normalized]
    return {
        "profile": normalized,
        "model_dtype": dtype,
        "training_dtype": dtype,
        "critical_dtype": "float64",
        "evaluation_dtype": dtype,
        "verification_dtype": dtype,
        "export_dtype": dtype,
    }


def _path_cfg(cfg: Mapping[str, Any], paths: CampaignPaths, key: str, *, required: bool = True) -> Path | None:
    value = _cfg(cfg, "paths", key)
    if value in (None, ""):
        if required:
            raise CampaignCliError(f"Missing [paths].{key} in {paths.config}.")
        return None
    return _resolve_path(value, paths.config_dir)


def _true_label_replay_root(
    cfg: Mapping[str, Any], paths: CampaignPaths
) -> Path | None:
    return _path_cfg(cfg, paths, "replay_true_labels", required=False)


def _resolve_true_label_replay_inputs(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    *,
    require_train: bool,
) -> Any | None:
    import mdstats

    single = mdstats.single_source_replay_config_from_campaign(cfg, base_directory=paths.config_dir)
    if single is not None:
        context = _single_source_replay_context(cfg, paths)
        assert context is not None
        resolution = context["true_resolution"]
        if require_train and resolution.train_artifact is None:
            # Pseudo-label training intentionally has no true-label train transport
            # unless a caller explicitly requests it.  Build it lazily from the
            # exact same source/split authority when required.
            true_views = mdstats.materialize_replay_true_label_views(
                context["source"], context["true_cache"], context["split"],
                paths.internal / "replay-unified" / "views",
                roles=(mdstats.ReplaySplitRole.TRAIN, mdstats.ReplaySplitRole.MONITOR),
            )
            train_view = true_views[mdstats.ReplaySplitRole.TRAIN]
            monitor_view = true_views[mdstats.ReplaySplitRole.MONITOR]
            train_artifact = _inspect_unified_replay_artifact(
                Path(train_view.path), label_mode=mdstats.ReplayLabelMode.TRUE_DFT
            )
            monitor_artifact = _inspect_unified_replay_artifact(
                Path(monitor_view.path), label_mode=mdstats.ReplayLabelMode.TRUE_DFT
            )
            return mdstats.TrueLabelReplayResolution(
                root_directory=str(paths.internal / "replay-unified" / "views"),
                train_path=train_view.path, monitor_path=monitor_view.path,
                train_artifact=train_artifact, monitor_artifact=monitor_artifact,
                source_path=str(context["source"].path), materialized=True,
            )
        return resolution

    root = _true_label_replay_root(cfg, paths)
    if root is None:
        return None
    replay_train = _path_cfg(cfg, paths, "replay_train", required=require_train)
    replay_monitor = _path_cfg(cfg, paths, "replay_monitor")
    assert replay_monitor is not None
    try:
        return mdstats.resolve_true_label_replay_directory(
            root,
            replay_train_path=replay_train,
            replay_monitor_path=replay_monitor,
            output_directory=paths.internal / "true-label-replay",
            require_train=require_train,
        )
    except Exception as exc:
        raise CampaignCliError(f"Could not resolve [paths].replay_true_labels: {exc}") from exc


def _doctor_sample_atoms(cfg: Mapping[str, Any], paths: CampaignPaths) -> Any | None:
    """Load one real campaign geometry for an accelerator model smoke."""

    try:
        import numpy as np
        from ase.io import iread, read
    except Exception:
        return None
    replay = _path_cfg(cfg, paths, "replay_set", required=False)
    if replay is None:
        replay = _path_cfg(cfg, paths, "replay_train", required=False)
    if replay is not None and replay.is_file():
        try:
            # Replay corpora can include isolated atoms or molecular cells.  Use
            # the first fully periodic, finite-volume configuration so the same
            # smoke also verifies the stress path required by this campaign.
            for index, atoms in enumerate(iread(replay, index=":", format="extxyz")):
                if bool(np.all(atoms.pbc)) and float(abs(atoms.get_volume())) > 1.0e-12:
                    return atoms
                if index >= 255:
                    break
        except Exception:
            pass
    root = _path_cfg(cfg, paths, "training_root", required=False)
    if root is not None and root.is_dir():
        pattern = str(_cfg(cfg, "data", "discovery_pattern", "**/*.xml"))
        for candidate in sorted(root.glob(pattern)):
            try:
                return read(candidate, index=0, format="vasp-xml")
            except Exception:
                continue
    return None


def _sha256(path: str | Path) -> str:
    return sha256_file_cached(path)


def _stage_config_key(name: str) -> str:
    return f"stage_config_sha256:{name}"


def _stage_config_digest(paths: CampaignPaths, name: str) -> str:
    """Return the scoped completion identity for one lifecycle stage.

    Preparation uses its explicit semantic projection.  Downstream current
    owners bind their own persisted protocol identities, so the CLI uses the
    conservative full-TOML hash for those stage records.  If a legacy input has
    no parseable TOML, the full hash is the fallback.
    """

    if name != "prepare":
        return _sha256(paths.config)
    try:
        cfg, _ = _load_config(paths.config)
    except Exception:
        return _sha256(paths.config)
    return _preparation_config_digest(cfg)


def _mark_stage(
    store: CampaignStore,
    paths: CampaignPaths,
    name: str,
    state: StageState,
    message: str,
) -> None:
    """Persist a stage transition and bind completion to its scoped identity."""

    store.set_stage(name, state, message)
    store.set_meta(
        _stage_config_key(name),
        _stage_config_digest(paths, name) if state is StageState.COMPLETE else None,
    )


def _effective_stage(
    store: CampaignStore,
    paths: CampaignPaths,
    name: str,
) -> tuple[StageState, str]:
    state, message = store.stage(name)
    if state is StageState.COMPLETE:
        recorded = store.get_meta(_stage_config_key(name))
        current = _stage_config_digest(paths, name)
        if recorded != current:
            return (
                StageState.WAITING,
                "campaign.toml changed after this stage completed; rerun the stage before continuing",
            )
    return state, message




def _require_stage_complete(
    store: CampaignStore,
    paths: CampaignPaths,
    name: str,
) -> None:
    state, message = _effective_stage(store, paths, name)
    if state is not StageState.COMPLETE:
        raise CampaignCliError(
            f"Stage `{name}` is not complete for the current campaign.toml ({message}). "
            f"Run `{name}` first, or use `status` for the next safe command."
        )


def _ensure_local_wrappers(paths: CampaignPaths) -> dict[str, Path]:
    """Create source-checkout shims with the exact qualified executable names."""
    wrapper_dir = paths.internal / "bin"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    targets = {
        "mdstats-mace-train": "train_main",
        "mdstats-mace-eval": "eval_main",
        "mdstats-mace-select-head": "select_head_main",
    }
    result: dict[str, Path] = {}
    for name, function in targets.items():
        target = wrapper_dir / name
        source_root = Path(__file__).resolve().parents[2]
        body = (
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.path.insert(0, {str(source_root)!r})\n"
            "from mdstats.training_data.critical_precision_cli import " + function + "\n"
            f"raise SystemExit({function}())\n"
        )
        if not target.is_file() or target.read_text(encoding="utf-8") != body:
            target.write_text(body, encoding="utf-8")
            target.chmod(0o755)
        result[name] = target
    return result









def _current_lifecycle_is_complete(
    cfg: Mapping[str, Any], paths: CampaignPaths, store: "CampaignStore"
) -> bool:
    """Return whether every current public lifecycle step is complete.

    Consequential storage tiers are authorized by the current lifecycle owners -
    the target-size campaign revision and the post-selection CV/final-production
    authorities - rather than by a retired deployment protocol-freeze record.
    """

    try:
        lifecycle = _current_public_lifecycle(cfg, paths, store)
    except Exception:
        return False
    return all(step.state is StageState.COMPLETE for step in lifecycle)


















def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _update_benchmark(paths: CampaignPaths, stage: str, payload: Mapping[str, Any]) -> None:
    target = paths.results / "campaign-benchmark.json"
    current: dict[str, Any] = {}
    if target.is_file():
        current = json.loads(target.read_text(encoding="utf-8"))
    current.update({"schema": "mdstats.mlff-campaign-benchmark.v1", "updated_utc": _utc_now()})
    stages = current.setdefault("stages", {})
    stages[stage] = dict(payload)
    _atomic_json(target, current)


def _print_header(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}", flush=True)


def _ok(message: str) -> None:
    print(f"[PASS] {message}", flush=True)


def _warn(message: str) -> None:
    print(f"[WARN] {message}", flush=True)


def _fail(message: str) -> None:
    print(f"[FAIL] {message}", flush=True)


def _print_metric_summary(prefix: str, label: str, stats: Mapping[str, float]) -> None:
    print(
        f"{prefix} {label}: min={stats['min']:.3e}, median={stats['median']:.3e}, "
        f"p90={stats['p90']:.3e}, p99={stats.get('p99', stats['max']):.3e}, max={stats['max']:.3e}",
        flush=True,
    )


def _print_count_summary(prefix: str, label: str, values: Sequence[int], component_count: int) -> None:
    counts = np.asarray(values, dtype=np.float64)
    print(
        f"{prefix} {label}: min={int(np.min(counts))}, median={float(np.median(counts)):.1f}, "
        f"p90={float(np.percentile(counts, 90.0)):.1f}, p99={float(np.percentile(counts, 99.0)):.1f}, "
        f"max={int(np.max(counts))} of {component_count}",
        flush=True,
    )


def _print_training_repeatability_diagnostic(record: Any, *, prefix: str = "[DIAG]", title: str = "TRAIN2 FP32 repeatability (non-authorizing)") -> None:
    """Print warm-up/all-pairs or historical baseline repeatability statistics."""

    print(
        f"{prefix} {title}: repeats={record.repeat_count}, warmups={getattr(record, 'warmup_count', 0)}, "
        f"mode={getattr(record, 'comparison_mode', 'baseline')}, structures={record.structure_count}, "
        f"atoms={record.atom_count}, force_threshold={record.force_threshold:.1e}", flush=True,
    )
    print(
        f"{prefix} determinism: torch_deterministic_algorithms={record.torch_deterministic_algorithms}, "
        f"debug_mode={record.torch_deterministic_debug_mode}, cudnn_deterministic={record.cudnn_deterministic}, "
        f"CUBLAS_WORKSPACE_CONFIG={record.cublas_workspace_config or '<unset>'}", flush=True,
    )
    print(
        f"{prefix} comparison counts: e3nn-self={record.self_pair_count}, "
        f"CuEq-self={record.self_pair_count}, cross={record.cross_pair_count}", flush=True,
    )

    # Historical v1 records used one paired cross comparison per run and are
    # still printed run-by-run.  DIAG3 all-pairs records contain 100 cross
    # comparisons for N=10, so emit distribution summaries instead of noise.
    if getattr(record, "comparison_mode", "baseline") == "baseline":
        for index in range(record.cross_pair_count):
            print(
                f"{prefix} cross {index + 1:02d}/{record.cross_pair_count:02d}: "
                f"Emax={record.cross_energy_max_abs[index]:.3e}, Fmax={record.cross_force_max_abs[index]:.3e}, "
                f"Frmse={record.cross_force_rmse[index]:.3e}, Fp99={record.cross_force_p99_abs[index]:.3e}, "
                f"Fp99.9={record.cross_force_p999_abs[index]:.3e}, "
                f"F>{record.force_threshold:.1e}={record.cross_force_above_threshold_count[index]}/"
                f"{record.cross_force_component_count}, Smax={record.cross_stress_max_abs[index]:.3e}, "
                f"Dmax={record.cross_descriptor_max_abs[index]:.3e}, "
                f"selection_identical={record.cross_selection_identical[index]}", flush=True,
            )

    summaries = record.summaries
    for label, key in (
        ("e3nn-self Fmax", "e3nn_self_force_max_abs"),
        ("e3nn-self Frmse", "e3nn_self_force_rmse"),
        ("CuEq-self Fmax", "cueq_self_force_max_abs"),
        ("CuEq-self Frmse", "cueq_self_force_rmse"),
    ):
        _print_metric_summary(prefix, label, summaries[key])
    if record.self_detail_available:
        for label, key in (
            ("e3nn-self Fp99", "e3nn_self_force_p99_abs"),
            ("e3nn-self Fp99.9", "e3nn_self_force_p999_abs"),
            ("CuEq-self Fp99", "cueq_self_force_p99_abs"),
            ("CuEq-self Fp99.9", "cueq_self_force_p999_abs"),
        ):
            _print_metric_summary(prefix, label, summaries[key])
        _print_count_summary(prefix, f"e3nn-self F>{record.force_threshold:.1e}",
            record.e3nn_self_force_above_threshold_count, record.cross_force_component_count)
        _print_count_summary(prefix, f"CuEq-self F>{record.force_threshold:.1e}",
            record.cueq_self_force_above_threshold_count, record.cross_force_component_count)
    if getattr(record, "self_channel_detail_available", False):
        for label, key in (
            ("e3nn-self Emax", "e3nn_self_energy_max_abs"),
            ("e3nn-self Smax", "e3nn_self_stress_max_abs"),
            ("e3nn-self Dmax", "e3nn_self_descriptor_max_abs"),
            ("CuEq-self Emax", "cueq_self_energy_max_abs"),
            ("CuEq-self Smax", "cueq_self_stress_max_abs"),
            ("CuEq-self Dmax", "cueq_self_descriptor_max_abs"),
        ):
            _print_metric_summary(prefix, label, summaries[key])
        print(
            f"{prefix} self selection_identical: e3nn={sum(record.e3nn_self_selection_identical)}/"
            f"{record.self_pair_count}, CuEq={sum(record.cueq_self_selection_identical)}/{record.self_pair_count}",
            flush=True,
        )
    for label, key in (
        ("cross Fmax", "cross_force_max_abs"), ("cross Frmse", "cross_force_rmse"),
        ("cross Fp99", "cross_force_p99_abs"), ("cross Fp99.9", "cross_force_p999_abs"),
        ("cross Emax", "cross_energy_max_abs"), ("cross Smax", "cross_stress_max_abs"),
        ("cross Dmax", "cross_descriptor_max_abs"),
    ):
        _print_metric_summary(prefix, label, summaries[key])
    _print_count_summary(prefix, f"cross F>{record.force_threshold:.1e}",
        record.cross_force_above_threshold_count, record.cross_force_component_count)
    print(
        f"{prefix} cross selection_identical={sum(record.cross_selection_identical)}/{record.cross_pair_count}",
        flush=True,
    )




def _file_size_mib(path: Path) -> float:
    try:
        return path.stat().st_size / (1024.0 * 1024.0)
    except OSError:
        return 0.0



class _ProgressReporter:
    """Compact elapsed/rate/ETA reporter for long campaign stages.

    Immediate cache/restart completions are treated as baseline work rather
    than throughput samples.  This avoids predicting an hours-long remaining
    run from a millisecond burst of already-complete items.
    """

    def __init__(self, label: str, total: int, *, minimum_interval_seconds: float = 15.0):
        self.label = str(label)
        self.total = max(0, int(total))
        self.started = time.monotonic()
        self.last_printed = self.started
        self.minimum_interval_seconds = float(minimum_interval_seconds)
        self._rate_tracker = ProgressRateTracker(
            completed=0,
            started_at=self.started,
            minimum_recent_window_seconds=1.0,
        )
        self._startup_baseline_seconds = 1.0

    @staticmethod
    def _duration(seconds: float) -> str:
        return format_progress_time(seconds)

    def item_start(self, index: int, name: str, detail: str = "") -> None:
        suffix = f"; detail={detail}" if detail else ""
        elapsed = max(0.0, time.monotonic() - self.started)
        completed = max(0, min(self.total, int(index) - 1))
        print(
            f"[{self.label} {index:>3}/{self.total}] {name}; status=start; "
            f"progress={format_progress_fraction(completed, self.total)}; "
            f"elapsed={format_progress_time(elapsed)}; eta=--:--:--{suffix}",
            flush=True,
        )

    def item_done(
        self,
        index: int,
        name: str,
        detail: str = "",
        *,
        force: bool = True,
        completed_count: int | None = None,
    ) -> None:
        now = time.monotonic()
        completed = (
            int(index) if completed_count is None else int(completed_count)
        )
        completed = max(0, min(self.total, completed))
        if not force and completed < self.total and now - self.last_printed < self.minimum_interval_seconds:
            return
        elapsed = now - self.started
        # Completed/recovered work reported immediately after reporter creation
        # is not a sample of current execution speed.  Move the rate baseline
        # past that startup burst.
        if elapsed <= self._startup_baseline_seconds and completed < self.total:
            self._rate_tracker.reset(completed=completed, now=now)
        timing = self._rate_tracker.snapshot(
            completed=completed, total=self.total, now=now
        )
        suffix = f"; detail={detail}" if detail else ""
        print(
            f"[{self.label} {index:>3}/{self.total}] {name}; status=complete; "
            f"progress={format_progress_fraction(completed, self.total)}; "
            f"elapsed={format_progress_time(elapsed)}; "
            f"eta={format_progress_time(timing.eta_seconds)}{suffix}",
            flush=True,
        )
        self.last_printed = now


def _manifest_inference_policy(cfg: Mapping[str, Any]) -> Any:
    import mdstats

    return mdstats.ManifestInferencePolicy(
        fixed_cell_relative_tolerance=float(
            _cfg(cfg, "manifest_inference", "fixed_cell_relative_tolerance", 1.0e-7)
        ),
        reference_cell_relative_tolerance=float(
            _cfg(cfg, "manifest_inference", "reference_cell_relative_tolerance", 1.0e-7)
        ),
        strain_matrix_absolute_tolerance=float(
            _cfg(cfg, "manifest_inference", "strain_matrix_absolute_tolerance", 5.0e-5)
        ),
        strain_volume_ratio_tolerance=float(
            _cfg(cfg, "manifest_inference", "strain_volume_ratio_tolerance", 5.0e-5)
        ),
        maximum_rotation_radians=float(
            _cfg(cfg, "manifest_inference", "maximum_rotation_radians", 1.0e-4)
        ),
        conventional_axis_orthogonality_tolerance=float(
            _cfg(cfg, "manifest_inference", "conventional_axis_orthogonality_tolerance", 5.0e-6)
        ),
        temperature_equality_tolerance_kelvin=float(
            _cfg(cfg, "manifest_inference", "temperature_equality_tolerance_kelvin", 1.0e-6)
        ),
        filename_values_at_or_above_one_are_percent=bool(
            _cfg(cfg, "manifest_inference", "filename_values_at_or_above_one_are_percent", True)
        ),
    )


def _print_manifest_inference(result: Any) -> None:
    _print_header("Manifest inference")
    print(f"XML metadata resolved: {result.resolved_xml_metadata_runs}")
    print(f"Fixed-cell runs:       {result.fixed_cell_runs}")
    print(f"Strain candidates:     {result.strain_candidate_runs}")
    print(f"Verified strains:      {result.verified_strain_runs}")
    print(f"Rejected strains:      {result.rejected_strain_runs}")
    print(f"Ambiguous strains:     {result.ambiguous_strain_runs}")
    for warning in result.warnings:
        _warn(warning)


def _ensure_manifest(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    *,
    approve: bool,
    refresh_inferences: bool = False,
) -> Any:
    import mdstats

    training_root = _path_cfg(cfg, paths, "training_root")
    assert training_root is not None
    store = CampaignStore(paths.state_db)
    if not paths.manifest.is_file():
        pattern = str(_cfg(cfg, "data", "discovery_pattern", "**/*.xml"))
        discovered = mdstats.discover_vasp_manifest(
            training_root,
            dataset_id=str(_cfg(cfg, "data", "dataset_id", "mlff-dataset")),
            system_profile=str(_cfg(cfg, "campaign", "profile", "lta")),
            pattern=pattern,
        )
        inference = mdstats.infer_training_manifest_metadata(
            discovered,
            base_directory=training_root,
            policy=_manifest_inference_policy(cfg),
        )
        manifest = inference.manifest
        _atomic_json(paths.manifest, manifest.to_dict())
        _print_manifest_inference(inference)
        unresolved = inference.rejected_strain_runs + inference.ambiguous_strain_runs
        if unresolved:
            review_note = f" {unresolved} strain relationship(s) require inspection."
        elif inference.strain_candidate_runs:
            review_note = " All strain relationships passed geometry verification."
        else:
            review_note = " No filename strain candidates were present."
        raise CampaignCliError(
            f"Discovered {len(manifest.runs)} VASP runs, inferred reviewable metadata, and wrote {paths.manifest}."
            + review_note
            + " Review reference groups, independent replicas/realizations, and the populated inference evidence; "
            + "then rerun `prepare --approve-manifest`."
        )

    manifest = mdstats.TrainingDataManifest.load(paths.manifest)
    approved_digest = store.get_meta("approved_manifest_digest")
    if refresh_inferences:
        if approved_digest == manifest.content_digest:
            raise CampaignCliError(
                "The current manifest is already approved. Use --rebuild-catalog only after intentionally "
                "invalidating the campaign, or remove approval by starting a new workspace."
            )
        inference = mdstats.infer_training_manifest_metadata(
            manifest,
            base_directory=training_root,
            policy=_manifest_inference_policy(cfg),
        )
        manifest = inference.manifest
        _atomic_json(paths.manifest, manifest.to_dict())
        store.set_meta("approved_manifest_digest", None)
        _print_manifest_inference(inference)
        raise CampaignCliError(
            f"Refreshed XML and strain inferences in {paths.manifest}. Review the populated manifest, "
            "then rerun `prepare --approve-manifest`."
        )

    if approve:
        store.set_meta("approved_manifest_digest", manifest.content_digest)
        approved_digest = manifest.content_digest
    if approved_digest != manifest.content_digest:
        raise CampaignCliError(
            f"Manifest {paths.manifest} is not approved, or changed after approval. "
            "Review it and rerun `prepare --approve-manifest`."
        )
    return manifest


def _lta_contracts(cfg: Mapping[str, Any]) -> Any:
    import mdstats

    framework_numbers = tuple(int(v) for v in _cfg(cfg, "profile", "framework_atomic_numbers", (8, 13, 14)))
    mobile_numbers = tuple(int(v) for v in _cfg(cfg, "profile", "mobile_atomic_numbers", (3, 11, 19)))
    profile = mdstats.build_single_phase_material_profile(
        profile_id=str(_cfg(cfg, "profile", "profile_id", "dry-lta-alkali")),
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        geometry=mdstats.MaterialGeometryKind.BULK,
        chemistry_modifiers=(
            mdstats.ChemistryModifier.IONIC.value,
            mdstats.ChemistryModifier.COVALENT_NETWORK.value,
        ),
        extensions=(
            mdstats.StructuralExtension.POROUS_NETWORK.value,
            mdstats.StructuralExtension.ZEOLITE.value,
            mdstats.StructuralExtension.LTA.value,
        ),
        phase_id="lta_framework_and_guests",
    )
    groups = mdstats.AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=("lta_framework_and_guests",),
        groups=(
            mdstats.AtomGroupDefinition(
                group_id="all_atoms",
                label="All atoms",
                selector=mdstats.AtomGroupSelector(kind=mdstats.AtomGroupSelectorKind.ALL_ATOMS),
                phase_ids=("lta_framework_and_guests",),
            ),
            mdstats.AtomGroupDefinition(
                group_id="framework",
                label="LTA framework",
                selector=mdstats.AtomGroupSelector(
                    kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
                    atomic_numbers=framework_numbers,
                ),
                phase_ids=("lta_framework_and_guests",),
                roles=("training_focus", "validation_focus"),
            ),
            mdstats.AtomGroupDefinition(
                group_id="mobile_ions",
                label="Li/Na/K mobile ions",
                selector=mdstats.AtomGroupSelector(
                    kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
                    atomic_numbers=mobile_numbers,
                ),
                phase_ids=("lta_framework_and_guests",),
                roles=("mlff_focus", "training_focus", "validation_focus"),
            ),
        ),
        catalog_id="dry_lta_groups",
    )
    return mdstats.build_material_profile_contracts(profile, atom_groups=groups)


def _material_profile_contracts(cfg: Mapping[str, Any]) -> Any:
    profile = str(_cfg(cfg, "campaign", "profile", "lta")).lower()
    if profile != "lta":
        raise CampaignCliError(
            "The first campaign CLI profile is `lta`. Generic material profiles remain available through the Python API."
        )
    return _lta_contracts(cfg)













































_HISTORICAL_FIXED_CANDIDATE_AUTHORITY_KEY = "target_size_historical_candidate_authority"










_TRAIN2_INVALIDATION_RECORD_PREFIXES = (
    "execution:",
    "train2_runtime:",
    "adaptive_stop:",
    "lightweight_rank:",
    "checkpoint_catalog:",
    "checkpoint_retention:",
    "evaluation:",
    "checkpoint_shortlist:",
    "selection:",
    "interim_member:",
    "committee_member:",
    "mlcv_run_selection:",
    "mlcv_physical_attempt:",
)

_TRAIN2_INVALIDATION_RECORD_KEYS = (
    "training_campaign",
    "interim_evaluation",
    "available_model_verification_set",
    "mlcv_lifecycle_authority",
    "mlcv_campaign_cv",
    "mlcv_final_selection",
    "mlcv_final_committee",
    "mlcv_verification_policy",
    "mlcv_verification",
    "mlcv_locked_test_evaluation",
    "mlcv_locked_test",
    "mlcv_production_model",
    "mlcv_protocol_freeze",
    "mlcv_migration",
)














def _load_or_rebuild_frame_data(
    cfg: Mapping[str, Any], paths: CampaignPaths, sources: Any
) -> dict[str, Any]:
    """Restore normalized arrays only when a scientific phase actually needs them."""

    import mdstats

    cache_start = time.monotonic()
    try:
        frame_data = mdstats.load_frame_data_cache(
            sources, paths.internal / "frame-cache"
        )
        _ok(
            f"normalized frame cache restored on demand; "
            f"elapsed={format_progress_time(time.monotonic() - cache_start)}"
        )
        return dict(frame_data)
    except Exception as exc:
        training_root = _path_cfg(cfg, paths, "training_root")
        assert training_root is not None
        _warn(
            f"frame cache unavailable ({exc}); rebuilding it with one source read per run"
        )
        frame_data, _ = mdstats.load_vasp_frame_data_by_run(
            sources, base_directory=training_root
        )
        mdstats.write_frame_data_cache(
            sources, frame_data, paths.internal / "frame-cache"
        )
        _ok(
            f"normalized frame cache rebuilt on demand; "
            f"elapsed={format_progress_time(time.monotonic() - cache_start)}"
        )
        return dict(frame_data)


def _resolved_foundation_potential_identity(cfg: Mapping[str, Any], paths: CampaignPaths) -> Any:
    """Inspect and resolve the canonical scientific foundation before inference."""

    import mdstats

    model_path = _path_cfg(cfg, paths, "foundation_model")
    assert model_path is not None
    foundation = _foundation_config(cfg)
    numbers = tuple(
        int(v)
        for v in _cfg(cfg, "profile", "all_atomic_numbers", (3, 8, 11, 13, 14, 19))
    )
    try:
        return mdstats.MaceFoundationSpec(
            family=str(foundation.get("family", "")),
            requested_head=str(foundation.get("head", "")).strip() or None,
            requested_atomic_numbers=numbers,
        ).resolve_file(model_path)
    except Exception as exc:
        raise CampaignCliError(f"Foundation checkpoint/head resolution failed: {exc}") from exc



def _stored_acceleration_realization(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    *,
    require_qualified: bool = False,
) -> Any | None:
    """Load and validate the doctor-frozen acceleration implementation."""

    import mdstats

    store = CampaignStore(paths.state_db)
    record = store.get_record_optional("acceleration_realization", mdstats.AccelerationRealizationRecord)
    if record is None:
        if require_qualified:
            raise CampaignCliError(
                "Acceleration realization is missing. Run `doctor` under the intended runtime before preparation."
            )
        return None
    policy = _acceleration_policy(cfg)
    device = str(_cfg(cfg, "model", "device", _cfg(cfg, "training", "device", "cuda")))
    dtype = str(_cfg(cfg, "model", "dtype", _cfg(cfg, "training", "dtype", "float32")))
    if record.requested_backend != policy.backend.value:
        raise CampaignCliError("Stored acceleration realization belongs to a different requested backend.")
    if record.device != device or record.dtype != dtype:
        raise CampaignCliError("Stored acceleration realization belongs to a different device/dtype runtime.")
    if require_qualified and not record.qualified:
        raise CampaignCliError(
            f"Requested acceleration backend is not qualified: {record.failure_reason or 'unknown qualification failure'}"
        )
    return record



def _stored_training_acceleration_realization(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    *,
    require_qualified: bool = False,
) -> Any | None:
    """Load the doctor-frozen TRAIN2 realization without changing source authority."""

    import mdstats

    if not _phase_separated_acceleration(cfg):
        return _stored_acceleration_realization(cfg, paths, require_qualified=require_qualified)
    store = CampaignStore(paths.state_db)
    record = store.get_record_optional(
        "training_acceleration_realization", mdstats.TrainingAccelerationRealizationRecord
    )
    if record is None:
        if require_qualified:
            raise CampaignCliError(
                "TRAIN2 acceleration realization is missing. Run `doctor` under the intended runtime before preparation."
            )
        return None
    policy = _training_acceleration_policy(cfg)
    device = str(_cfg(cfg, "training", "device", "cuda"))
    dtype = str(_cfg(cfg, "training", "dtype", "float32"))
    if record.requested_backend != policy.backend.value:
        raise CampaignCliError("Stored TRAIN2 acceleration realization belongs to a different requested backend.")
    if record.device != device or record.dtype != dtype:
        raise CampaignCliError("Stored TRAIN2 acceleration realization belongs to a different device/dtype runtime.")
    checkpoint = Path(record.training_checkpoint_reference)
    if not checkpoint.is_file() or _sha256(checkpoint) != record.training_checkpoint_sha256:
        raise CampaignCliError("Stored TRAIN2 acceleration realization checkpoint bytes changed after doctor.")
    if require_qualified and not record.qualified:
        raise CampaignCliError(
            f"Requested TRAIN2 acceleration backend is not qualified: {record.failure_reason or 'unknown qualification failure'}"
        )
    return record






def _doctor_acceleration_corpus(sample_atoms: Any) -> tuple[Any, ...]:
    """Small deterministic local corpus for E/F/stress/descriptor backend qualification."""

    import numpy as np

    base = sample_atoms.copy()
    variants = [base]
    if len(base):
        displaced = base.copy()
        positions = np.asarray(displaced.get_positions(), dtype=np.float64).copy()
        index = np.arange(positions.shape[0], dtype=np.float64)[:, None]
        axis = np.arange(3, dtype=np.float64)[None, :]
        positions += 0.015 * np.sin(0.73 * (index + 1.0) * (axis + 1.0))
        displaced.set_positions(positions)
        variants.append(displaced)
    if bool(np.all(base.get_pbc())) and abs(float(np.linalg.det(np.asarray(base.cell.array)))) > 1.0e-8:
        strained = base.copy()
        cell = np.asarray(strained.cell.array, dtype=np.float64).copy()
        cell = np.diag([1.01, 0.99, 1.005]) @ cell
        strained.set_cell(cell, scale_atoms=True)
        variants.append(strained)
    return tuple(variants)

def _selected_head_qualification_matches(potential: Any, qualification: Any) -> bool:
    extraction = qualification.extraction
    derived = Path(extraction.derived_checkpoint_reference)
    return bool(
        qualification.training_qualified
        and extraction.source_potential_digest == potential.canonical_content_digest
        and extraction.source_checkpoint_sha256 == potential.sha256
        and extraction.source_head == potential.foundation_head
        and derived.is_file()
        and _sha256(derived) == extraction.derived_checkpoint_sha256
    )


def _qualify_selected_head_training_foundation(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    store: CampaignStore,
    potential: Any,
    structures: Sequence[Any],
) -> Any | None:
    """Create/reuse EXTRACT1 evidence for a genuinely multi-head foundation."""

    import mdstats

    if len(tuple(potential.available_heads)) <= 1:
        return None
    existing = store.get_record_optional(
        "selected_head_qualification", mdstats.MaceSelectedHeadQualificationRecord
    )
    if existing is not None and _selected_head_qualification_matches(potential, existing):
        return existing
    model_path = _path_cfg(cfg, paths, "foundation_model")
    assert model_path is not None
    output_dir = paths.internal / "foundation-selected-head"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{potential.family.value}-{potential.foundation_head}.model"
    extraction, _evidence = mdstats.extract_mace_selected_foundation_head(
        model_path,
        output,
        source_identity=potential,
    )
    qualification = mdstats.qualify_mace_selected_foundation_head(
        model_path,
        extraction,
        tuple(structures),
        device="cpu",
    )
    if not _selected_head_qualification_matches(potential, qualification):
        raise CampaignCliError("Selected-head training foundation failed EXTRACT1 lineage validation.")
    store.put_record("selected_head_qualification", qualification)
    return qualification




def _foundation_inference_identity(
    cfg: Mapping[str, Any],
    potential: Any,
    *,
    adapter_version: str,
    resolved_kernel_mode: str | None = None,
) -> Any:
    """Build the execution identity for the currently requested foundation path.

    ACCEL1 will replace ``cueq_unresolved`` with a qualified pure/hybrid kernel
    realization.  INF1 still binds the requested backend, dtype, MACE version,
    and adapter so DATA6 cannot cross-reuse e3nn/CuEq evidence.
    """

    import mdstats
    from importlib import metadata as importlib_metadata

    acceleration = _acceleration_policy(cfg)
    dtype = str(_cfg(cfg, "model", "dtype", _cfg(cfg, "training", "dtype", "float32")))
    try:
        mace_version = importlib_metadata.version("mace-torch")
    except Exception:
        try:
            import mace
            mace_version = str(getattr(mace, "__version__", "unknown"))
        except Exception:
            mace_version = "unknown"
    kernel_mode = (
        str(resolved_kernel_mode)
        if resolved_kernel_mode is not None
        else ("e3nn" if acceleration.backend.value == "e3nn" else "cueq_unresolved")
    )
    return mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype=dtype,
        backend=acceleration.backend.value,
        resolved_kernel_mode=kernel_mode,
        mace_version=str(mace_version),
        adapter_version=str(adapter_version),
    )
















_UNIFIED_REPLAY_CONTEXT_CACHE: dict[str, dict[str, Any]] = {}


def _unified_replay_artifact_receipt_path(path: Path) -> Path:
    return path.with_name(path.name + ".mdstats-artifact.json")


def _load_or_inspect_single_replay_source(path: Path, replay_root: Path) -> Any:
    """Reuse an authenticated single-source inspection across command restarts.

    Parsing 12k ExtXYZ frames is unnecessary when the external replay bytes have
    not changed.  Bind the persisted ReplaySourceArtifact to the current source
    SHA-256 and locator; a mutation or relocation falls back to a fresh streaming
    inspection and atomically replaces the receipt.
    """

    import mdstats

    source = path.expanduser().resolve()
    replay_root.mkdir(parents=True, exist_ok=True)
    receipt = replay_root / "replay-source-artifact.json"
    expected_sha = _sha256(source)
    if receipt.is_file():
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            artifact = mdstats.ReplaySourceArtifact.from_dict(payload["artifact"])
            if (
                payload.get("schema") == "mdstats.replay-source-artifact-receipt.v1"
                and artifact.sha256 == expected_sha
            ):
                if Path(artifact.path).resolve() == source:
                    return artifact
                # Relocation with identical bytes is not a scientific change.
                # Rebind only the locator and preserve every authenticated
                # geometry/label identity without reparsing the ExtXYZ corpus.
                relocated = mdstats.ReplaySourceArtifact(
                    path=str(source),
                    sha256=artifact.sha256,
                    configuration_count=artifact.configuration_count,
                    atomic_numbers=artifact.atomic_numbers,
                    geometry_identities=artifact.geometry_identities,
                    source_label_identities=artifact.source_label_identities,
                    source_energy_present_count=artifact.source_energy_present_count,
                    source_forces_present_count=artifact.source_forces_present_count,
                    source_stress_present_count=artifact.source_stress_present_count,
                )
                _atomic_json(receipt, {
                    "schema": "mdstats.replay-source-artifact-receipt.v1",
                    "artifact": relocated.to_dict(),
                })
                return relocated
        except Exception:
            pass
    artifact = mdstats.inspect_replay_source_extxyz(source)
    _atomic_json(
        receipt,
        {
            "schema": "mdstats.replay-source-artifact-receipt.v1",
            "artifact": artifact.to_dict(),
        },
    )
    return artifact


def _inspect_unified_replay_artifact(
    path: Path,
    *,
    label_mode: Any,
    foundation_label_generator_identity_digest: str | None = None,
) -> Any:
    """Return a cached historical ReplayFileArtifact for one internal transport view.

    REPLAY-UNIFY1D keeps downstream TRAIN2/DATA8 contracts stable while moving
    external authority to one replay source.  The old artifact is therefore a
    disposable transport description, cached next to the generated ExtXYZ so
    repeated prepare/evaluate calls do not rescan 12k replay frames.
    """

    import mdstats

    source = path.expanduser().resolve()
    receipt = _unified_replay_artifact_receipt_path(source)
    expected_sha = _sha256(source)
    if receipt.is_file():
        try:
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            artifact = mdstats.ReplayFileArtifact.from_dict(payload["artifact"])
            if (
                payload.get("schema") == "mdstats.replay-unified-transport-artifact-receipt.v1"
                and artifact.sha256 == expected_sha
                and Path(artifact.path).resolve() == source
                and artifact.label_mode is label_mode
                and artifact.foundation_label_generator_identity_digest
                == foundation_label_generator_identity_digest
            ):
                return artifact
        except Exception:
            pass
    artifact = mdstats.inspect_replay_extxyz(
        source,
        label_mode=label_mode,
        foundation_label_generator_identity_digest=foundation_label_generator_identity_digest,
    )
    _atomic_json(
        receipt,
        {
            "schema": "mdstats.replay-unified-transport-artifact-receipt.v1",
            "artifact": artifact.to_dict(),
        },
    )
    return artifact


def _single_source_replay_context(cfg: Mapping[str, Any], paths: CampaignPaths) -> dict[str, Any] | None:
    """Prepare/cache the single-source replay authority and internal transport views.

    The single selected ExtXYZ is the only external replay authority.  All train,
    monitor, true-label, and pseudo-label files below ``.mdstats/replay-unified``
    are reconstructable internal materializations.
    """

    import mdstats

    try:
        single = mdstats.single_source_replay_config_from_campaign(
            cfg, base_directory=paths.config_dir
        )
    except Exception as exc:
        raise CampaignCliError(f"Invalid single-source replay configuration: {exc}") from exc
    if single is None:
        return None
    source_path = Path(single.replay_set_path).expanduser().resolve()
    if not source_path.is_file():
        raise CampaignCliError(f"[paths].replay_set is missing or not a file: {source_path}")
    stat = source_path.stat()
    cache_key = hashlib.sha256(json.dumps({
        "config": single.content_digest,
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "model": str(_cfg(cfg, "paths", "foundation_model", "")),
        "dtype": str(_cfg(cfg, "model", "dtype", "")),
        "backend": str(_cfg(cfg, "acceleration", "backend", "")),
        "max_force": _cfg(cfg, "replay", "maximum_force_ev_per_angstrom", 20.0),
        "max_force_rms": _cfg(cfg, "replay", "force_component_rms_ev_per_angstrom", 5.0),
        "max_stress": _cfg(cfg, "replay", "maximum_abs_stress_ev_per_angstrom3", 0.5),
        "require_stress": bool(_cfg(cfg, "replay", "require_stress", False)),
    }, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    cached = _UNIFIED_REPLAY_CONTEXT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    replay_root = paths.internal / "replay-unified"
    view_root = replay_root / "views"
    replay_root.mkdir(parents=True, exist_ok=True)
    source = _load_or_inspect_single_replay_source(source_path, replay_root)
    source_index = mdstats.build_replay_source_index(source, replay_root / "source-index")
    true_cache = mdstats.build_replay_true_label_cache(source)

    replay_weight = float(_cfg(cfg, "training", "replay_head_weight", 1.0))
    target_weight = float(_cfg(cfg, "training", "target_head_weight", 5.0))
    retention = mdstats.ReplayRetentionPolicy(
        maximum_degradation_fraction=float(
            _cfg(cfg, "acceptance", "maximum_replay_degradation_fraction", 0.20)
        )
    )
    records: dict[str, Any] = {
        "replay_single_source_config": single,
        "replay_source": source,
        "replay_true_label_cache": true_cache,
    }

    if single.label_mode is mdstats.ReplayLabelMode.TRUE_DFT:
        split = mdstats.build_replay_split_manifest(
            source,
            qualification_authority_digest=true_cache.content_digest,
            split_ratio=single.split_ratio,
            split_seed=single.split_seed,
        )
        views = mdstats.materialize_replay_true_label_views(
            source, true_cache, split, view_root, source_index=source_index
        )
        train_view = views[mdstats.ReplaySplitRole.TRAIN]
        monitor_view = views[mdstats.ReplaySplitRole.MONITOR]
        train_artifact = _inspect_unified_replay_artifact(
            Path(train_view.path), label_mode=mdstats.ReplayLabelMode.TRUE_DFT
        )
        monitor_artifact = _inspect_unified_replay_artifact(
            Path(monitor_view.path), label_mode=mdstats.ReplayLabelMode.TRUE_DFT
        )
        plan = mdstats.ReplayPreparationPlan(
            mode=mdstats.ReplayMode.EXTERNAL_TRUE_LABEL,
            train_artifact=train_artifact,
            monitor_artifact=monitor_artifact,
            source_replay_path=str(source_path),
            seed=single.split_seed,
            head_weight=replay_weight,
            target_weight=target_weight,
            retention_policy=retention,
        )
        true_resolution = mdstats.TrueLabelReplayResolution(
            root_directory=str(view_root),
            train_path=train_view.path,
            monitor_path=monitor_view.path,
            train_artifact=train_artifact,
            monitor_artifact=monitor_artifact,
            source_path=str(source_path),
            materialized=True,
        )
        records.update({
            "replay_split_manifest": split,
            "replay_true_train_view": train_view,
            "replay_true_monitor_view": monitor_view,
        })
    else:
        potential = _resolved_foundation_potential_identity(cfg, paths)
        realization = _stored_acceleration_realization(cfg, paths, require_qualified=True)
        if realization is None:
            raise CampaignCliError(
                "Canonical single-source pseudo-label replay requires a doctor-frozen acceleration realization."
            )
        inference = _foundation_inference_identity(
            cfg, potential, adapter_version=mdstats.MACE_ADAPTER_VERSION,
            resolved_kernel_mode=realization.resolved_kernel_mode,
        )
        if realization.foundation_inference_identity_digest != inference.content_digest:
            raise CampaignCliError(
                "Single-source replay prediction identity disagrees with the doctor-frozen acceleration realization."
            )
        prediction_policy = mdstats.ReplayFoundationPredictionPolicy(
            foundation_potential=potential,
            foundation_inference=inference,
            device=str(_cfg(cfg, "model", "device", "cuda")),
        )
        prediction_cache = mdstats.build_replay_foundation_prediction_cache(
            source,
            prediction_policy,
            replay_root / "foundation-predictions",
            batch_size=int(_cfg(cfg, "replay", "prediction_batch_size", 32)),
            shard_size=int(_cfg(cfg, "replay", "prediction_shard_size", 256)),
            graph_cache_directory=replay_root / "graph-cache",
            source_index=source_index,
        )
        qualification_policy = mdstats.ReplayPseudolabelQualificationPolicy(
            maximum_force_ev_per_angstrom=_optional_float(
                _cfg(cfg, "replay", "maximum_force_ev_per_angstrom", 20.0)
            ),
            force_component_rms_ev_per_angstrom=_optional_float(
                _cfg(cfg, "replay", "force_component_rms_ev_per_angstrom", 5.0)
            ),
            maximum_abs_stress_ev_per_angstrom3=_optional_float(
                _cfg(cfg, "replay", "maximum_abs_stress_ev_per_angstrom3", 0.5)
            ),
            require_stress=bool(_cfg(cfg, "replay", "require_stress", False)),
        )
        qualification = mdstats.build_replay_pseudolabel_qualification(
            prediction_cache, qualification_policy
        )
        split = mdstats.build_replay_split_manifest(
            source,
            eligible_geometry_identities=qualification.eligible_geometry_identities,
            qualification_authority_digest=qualification.content_digest,
            split_ratio=single.split_ratio,
            split_seed=single.split_seed,
        )
        pseudo_views = mdstats.materialize_replay_pseudolabel_views(
            source, prediction_cache, qualification, split, view_root, source_index=source_index
        )
        true_views = mdstats.materialize_replay_true_label_views(
            source,
            true_cache,
            split,
            view_root,
            roles=(mdstats.ReplaySplitRole.MONITOR,),
            source_index=source_index,
        )
        train_view = pseudo_views[mdstats.ReplaySplitRole.TRAIN]
        monitor_view = pseudo_views[mdstats.ReplaySplitRole.MONITOR]
        true_monitor_view = true_views[mdstats.ReplaySplitRole.MONITOR]
        train_artifact = _inspect_unified_replay_artifact(
            Path(train_view.path),
            label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
            foundation_label_generator_identity_digest=inference.content_digest,
        )
        monitor_artifact = _inspect_unified_replay_artifact(
            Path(monitor_view.path),
            label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
            foundation_label_generator_identity_digest=inference.content_digest,
        )
        true_monitor_artifact = _inspect_unified_replay_artifact(
            Path(true_monitor_view.path), label_mode=mdstats.ReplayLabelMode.TRUE_DFT
        )
        plan = mdstats.ReplayPreparationPlan(
            mode=mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL,
            train_artifact=train_artifact,
            monitor_artifact=monitor_artifact,
            source_replay_path=str(source_path),
            seed=single.split_seed,
            head_weight=replay_weight,
            target_weight=target_weight,
            retention_policy=retention,
        )
        true_resolution = mdstats.TrueLabelReplayResolution(
            root_directory=str(view_root),
            train_path=None,
            monitor_path=true_monitor_view.path,
            train_artifact=None,
            monitor_artifact=true_monitor_artifact,
            source_path=str(source_path),
            materialized=True,
        )
        records.update({
            "replay_foundation_prediction_policy": prediction_policy,
            "replay_foundation_prediction_cache": prediction_cache,
            "replay_pseudolabel_qualification": qualification,
            "replay_split_manifest": split,
            "replay_pseudolabel_train_view": train_view,
            "replay_pseudolabel_monitor_view": monitor_view,
            "replay_true_monitor_view": true_monitor_view,
        })

    context = {
        "config": single,
        "source": source,
        "source_index": source_index,
        "true_cache": true_cache,
        "split": split,
        "plan": plan,
        "true_resolution": true_resolution,
        "records": records,
    }
    _UNIFIED_REPLAY_CONTEXT_CACHE[cache_key] = context
    return context


def _persist_single_source_replay_authority(
    store: CampaignStore, cfg: Mapping[str, Any], paths: CampaignPaths
) -> None:
    context = _single_source_replay_context(cfg, paths)
    if context is None:
        return
    store.put_records(context["records"])

def _training_modes(cfg: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(item.mode for item in _training_method_specs(cfg))


def _requires_replay(cfg: Mapping[str, Any]) -> bool:
    return "multihead_replay" in _training_modes(cfg)


def _build_replay_plan(cfg: Mapping[str, Any], paths: CampaignPaths) -> Any:
    """Build the exact replay plan declared by the campaign configuration.

    Production pseudo-label replay is checkpoint-bound.  The raw checkpoint
    byte hash is used because it remains meaningful outside mdstats and can be
    independently reproduced with ``sha256sum``.
    """

    import mdstats

    target_weight = float(_cfg(cfg, "training", "target_head_weight", 5.0))
    replay_weight = float(_cfg(cfg, "training", "replay_head_weight", 1.0))
    if not _requires_replay(cfg):
        return mdstats.ReplayPreparationPlan(
            mode=mdstats.ReplayMode.NONE,
            head_weight=replay_weight,
            target_weight=target_weight,
        )

    single = mdstats.single_source_replay_config_from_campaign(cfg, base_directory=paths.config_dir)
    if single is not None:
        context = _single_source_replay_context(cfg, paths)
        assert context is not None
        return context["plan"]

    try:
        mode = mdstats.ReplayMode(str(_cfg(cfg, "replay", "mode", "external_pseudolabel")))
    except ValueError as exc:
        allowed = ", ".join(
            v.value for v in (
                mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL,
                mdstats.ReplayMode.EXTERNAL_TRUE_LABEL,
                mdstats.ReplayMode.PRESELECTED,
            )
        )
        raise CampaignCliError(f"Unsupported [replay].mode; choose one of: {allowed}.") from exc
    if mode not in {
        mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL,
        mdstats.ReplayMode.EXTERNAL_TRUE_LABEL,
        mdstats.ReplayMode.PRESELECTED,
    }:
        raise CampaignCliError(
            "The campaign CLI requires fixed local replay files for production; "
            "use external_pseudolabel, external_true_label, or preselected."
        )
    train_path = _path_cfg(cfg, paths, "replay_train")
    monitor_path = _path_cfg(cfg, paths, "replay_monitor")
    assert train_path is not None and monitor_path is not None
    if mode is mdstats.ReplayMode.EXTERNAL_TRUE_LABEL:
        true_resolution = _resolve_true_label_replay_inputs(
            cfg, paths, require_train=True
        )
        if true_resolution is not None:
            assert true_resolution.train_path is not None
            train_path = Path(true_resolution.train_path)
            monitor_path = Path(true_resolution.monitor_path)
    foundation_digest = None
    foundation_generator_digest = None
    if mode is mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL:
        foundation_model = _path_cfg(cfg, paths, "foundation_model")
        assert foundation_model is not None
        foundation_cfg = cfg.get("foundation")
        if isinstance(foundation_cfg, Mapping) and not bool(foundation_cfg.get("legacy_normalized", False)):
            potential = _resolved_foundation_potential_identity(cfg, paths)
            realization = _stored_acceleration_realization(cfg, paths, require_qualified=True)
            if realization is None:
                raise CampaignCliError(
                    "Canonical pseudo-labeled replay requires doctor-frozen acceleration realization before replay qualification."
                )
            inference = _foundation_inference_identity(
                cfg, potential, adapter_version=mdstats.MACE_ADAPTER_VERSION,
                resolved_kernel_mode=realization.resolved_kernel_mode,
            )
            if realization.foundation_inference_identity_digest != inference.content_digest:
                raise CampaignCliError("Replay label-generator identity disagrees with the doctor-frozen acceleration realization.")
            foundation_generator_digest = inference.content_digest
        else:
            # Controlled legacy compatibility: pre-MH1 pseudo-label replay only
            # carried the raw checkpoint SHA.  New canonical campaigns never use
            # this head-blind path.
            foundation_digest = _sha256(foundation_model)
    return mdstats.build_local_replay_plan(
        train_path,
        monitor_path,
        mode=mode,
        seed=int(_cfg(cfg, "replay", "seed", 42)),
        head_weight=replay_weight,
        target_weight=target_weight,
        retention_policy=mdstats.ReplayRetentionPolicy(
            maximum_degradation_fraction=float(
                _cfg(cfg, "acceptance", "maximum_replay_degradation_fraction", 0.20)
            )
        ),
        foundation_checkpoint_digest=foundation_digest,
        foundation_label_generator_identity_digest=foundation_generator_digest,
    )


def _qualify_replay(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
) -> tuple[Any, dict[str, Any], list[str], list[str]]:
    """Return the replay plan and fail-closed production qualification."""

    import mdstats

    plan = _build_replay_plan(cfg, paths)
    failures: list[str] = []
    warnings: list[str] = []
    if plan.mode is mdstats.ReplayMode.NONE:
        return plan, {
            "required": False,
            "mode": plan.mode.value,
            "qualified": True,
            "train_count": 0,
            "monitor_count": 0,
            "digest": plan.content_digest,
        }, failures, warnings

    train = plan.train_artifact
    monitor = plan.monitor_artifact
    assert train is not None and monitor is not None
    minimum_train = int(_cfg(cfg, "replay", "minimum_train_configurations", 100))
    minimum_monitor = int(_cfg(cfg, "replay", "minimum_monitor_configurations", 20))
    allow_small = bool(_cfg(cfg, "replay", "allow_small_corpus", False))
    if train.configuration_count < minimum_train:
        message = (
            f"replay-training corpus has {train.configuration_count} configurations; "
            f"production policy requires at least {minimum_train}"
        )
        (warnings if allow_small else failures).append(message)
    if monitor.configuration_count < minimum_monitor:
        message = (
            f"replay-monitor corpus has {monitor.configuration_count} configurations; "
            f"production policy requires at least {minimum_monitor}"
        )
        (warnings if allow_small else failures).append(message)

    required_numbers = set(int(v) for v in _cfg(cfg, "profile", "all_atomic_numbers", ()))
    observed_numbers = set(train.atomic_numbers) | set(monitor.atomic_numbers)
    missing_numbers = tuple(sorted(required_numbers - observed_numbers))
    if missing_numbers and bool(_cfg(cfg, "replay", "require_target_elements", True)):
        failures.append(
            "replay corpus does not cover target atomic numbers: "
            + ", ".join(str(v) for v in missing_numbers)
        )
    if plan.mode is mdstats.ReplayMode.PRESELECTED and not bool(
        _cfg(cfg, "replay", "allow_unspecified_label_provenance", False)
    ):
        failures.append(
            "[replay].mode=preselected has unspecified label provenance; declare "
            "external_pseudolabel or external_true_label, or explicitly allow it for exploratory work"
        )
    context = _single_source_replay_context(cfg, paths)
    summary = {
        "required": True,
        "mode": plan.mode.value,
        "interface": "single_source" if context is not None else "legacy_split_files",
        "qualified": not failures,
        "train_count": train.configuration_count,
        "monitor_count": monitor.configuration_count,
        "minimum_train_configurations": minimum_train,
        "minimum_monitor_configurations": minimum_monitor,
        "allow_small_corpus": allow_small,
        "atomic_numbers": sorted(observed_numbers),
        "missing_target_atomic_numbers": list(missing_numbers),
        "train_sha256": train.sha256,
        "monitor_sha256": monitor.sha256,
        "label_mode": train.label_mode.value,
        "foundation_label_generator_identity_digest": train.foundation_label_generator_identity_digest,
        "legacy_foundation_checkpoint_digest": train.foundation_checkpoint_digest,
        "digest": plan.content_digest,
        "failures": failures,
        "warnings": warnings,
    }
    if context is not None:
        summary.update({
            "replay_set": context["config"].replay_set_path,
            "replay_source_sha256": context["source"].sha256,
            "replay_source_digest": context["source"].content_digest,
            "split_ratio": list(context["config"].split_ratio),
            "split_seed": context["config"].split_seed,
            "split_manifest_digest": context["split"].content_digest,
            "qualified_configuration_count": context["split"].train_count + context["split"].monitor_count,
        })
        qualification = context["records"].get("replay_pseudolabel_qualification")
        if qualification is not None:
            summary["pseudolabel_rejected_count"] = qualification.rejected_count
            summary["prediction_cache_digest"] = context["records"]["replay_foundation_prediction_cache"].content_digest
    return plan, summary, failures, warnings


def command_init(args: argparse.Namespace) -> int:
    target = Path(args.config).expanduser().resolve()
    if target.exists() and not args.force:
        raise CampaignCliError(f"Refusing to overwrite {target}; use --force only when intentional.")
    target.parent.mkdir(parents=True, exist_ok=True)
    workspace = args.workspace or "mlff-campaign"
    try:
        import torch
        detected_device = "cuda" if bool(torch.cuda.is_available()) else "cpu"
    except ModuleNotFoundError:
        detected_device = "cpu"
    foundation_family = str(args.foundation_family)
    foundation_head = None if args.foundation_head in (None, "") else str(args.foundation_head)
    default_foundation_path = (
        "/path/to/mace-mh-1.model"
        if foundation_family == "mace_mh_1"
        else "/path/to/mace-mpa-0-medium.model"
    )
    text = _config_template(
        workspace=workspace,
        training_root=args.training_root or "/path/to/LTA_training",
        foundation_model=args.foundation_model or default_foundation_path,
        replay_set=(
            args.replay_set
            if args.replay_set not in (None, "")
            else None
            if any(getattr(args, name, None) not in (None, "") for name in ("replay_train", "replay_monitor", "replay_true_labels"))
            else "/path/to/replay_fps_12000.extxyz"
        ),
        replay_train=getattr(args, "replay_train", None),
        replay_monitor=getattr(args, "replay_monitor", None),
        replay_true_labels=getattr(args, "replay_true_labels", None),
        foundation_family=foundation_family,
        foundation_head=foundation_head,
        acceleration_backend=str(args.backend),
        training_acceleration_backend=str(args.training_backend),
        default_device=detected_device,
        precision_profile=str(args.precision),
    )
    target.write_text(text, encoding="utf-8")
    cfg, paths = _load_config(target)
    store = CampaignStore(paths.state_db)
    store.set_meta("configuration", str(target))
    store.set_meta("campaign_id", _cfg(cfg, "campaign", "id", "lta-mh1-omat-pbe-finetune"))
    _print_header("Campaign initialized")
    print(f"Configuration: {target}")
    print(f"Workspace:     {paths.workspace}")
    print(f"Device:        {detected_device} (auto-detected and frozen in campaign.toml)")
    foundation = _foundation_config(cfg)
    print(f"Foundation:    {foundation['family']} / {foundation['head']}")
    print(f"Source accel:  {args.backend} (source/DATA6/evaluation; frozen in campaign.toml)")
    print(f"TRAIN2 accel:  {args.training_backend} (training-only; frozen in campaign.toml)")
    print(f"Precision:     {args.precision} (learned-model dtype frozen in campaign.toml; scientific analysis remains FP64)")
    print("\nEdit the three input paths, then run:")
    print(f"  python tools/mdstats-mlff-campaign.py --config {target} doctor")
    return 0


def _runtime_freeze_backend_failure(
    acceleration: Any,
    runtime_freeze: Any | None,
) -> str | None:
    """Return a fail-closed accelerator freeze error without mutating policy."""

    if runtime_freeze is None or not bool(getattr(acceleration, "enable_cueq", False)):
        return None
    if runtime_freeze.passed_for_backend("cueq"):
        return None
    reasons = "; ".join(runtime_freeze.backend_failure_reasons("cueq"))
    return (
        "cuEquivariance campaign dependency freeze is incomplete; "
        "no backend fallback was applied: "
        f"{reasons or 'CuEq/OEq capability did not qualify'}"
    )


def command_doctor(args: argparse.Namespace) -> int:
    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _mark_stage(store, paths, "doctor", StageState.RUNNING, "checking environment and campaign inputs")
    _print_header("MLFF campaign doctor")
    failures: list[str] = []
    warnings: list[str] = []

    try:
        foundation_contract = _foundation_configuration_contract(cfg)
        store.set_meta("foundation_configuration_contract", foundation_contract)
        _ok(
            "foundation config: "
            f"{foundation_contract['family']} / {foundation_contract['head']} / "
            f"source={foundation_contract['source_backend']}; TRAIN2={foundation_contract['training_backend']}; "
            f"digest={foundation_contract['content_digest'][:12]}..."
        )
    except Exception as exc:
        failures.append(f"foundation configuration is invalid: {exc}")
        _fail(failures[-1])

    try:
        precision_contract = _binary_model_precision_contract(cfg)
        _ok(
            "precision: "
            f"profile={precision_contract['requested_profile']}; "
            f"learned-model dtype={precision_contract['model_dtype']}; "
            "mdstats scientific arithmetic=float64"
        )
    except Exception as exc:
        failures.append(f"model precision contract is invalid: {exc}")
        _fail(failures[-1])

    checks = [
        ("training_root", True, "dir"),
        ("foundation_model", True, "file"),
    ]
    if _requires_replay(cfg):
        try:
            import mdstats
            single_replay = mdstats.single_source_replay_config_from_campaign(
                cfg, base_directory=paths.config_dir
            )
        except Exception as exc:
            single_replay = None
            failures.append(f"replay configuration is invalid: {exc}")
            _fail(failures[-1])
        if single_replay is not None:
            checks.append(("replay_set", True, "file"))
        else:
            checks.extend((("replay_train", True, "file"), ("replay_monitor", True, "file")))
            if "replay_true_labels" in cfg.get("paths", {}):
                checks.append(("replay_true_labels", True, "dir"))
    for key, required, kind in checks:
        path = _path_cfg(cfg, paths, key, required=required)
        exists = path is not None and (path.is_dir() if kind == "dir" else path.is_file())
        if exists:
            _ok(f"{key}: {path}")
        else:
            failures.append(f"{key} is missing or not a {kind}: {path}")
            _fail(failures[-1])

    if _requires_replay(cfg):
        try:
            import mdstats
            single_replay = mdstats.single_source_replay_config_from_campaign(
                cfg, base_directory=paths.config_dir
            )
            if single_replay is not None:
                source = mdstats.inspect_replay_source_extxyz(single_replay.replay_set_path)
                true_cache = mdstats.build_replay_true_label_cache(source)
                _ok(
                    "single replay source: "
                    f"{source.configuration_count} configurations; "
                    f"complete true labels={true_cache.complete_true_label_count}; "
                    f"split={single_replay.split_ratio[0]}:{single_replay.split_ratio[1]}"
                )
                if true_cache.complete_true_label_count != source.configuration_count:
                    failures.append(
                        "single replay source lacks complete true energy/force labels for one or more configurations; "
                        "independent replay retention would not be reproducible"
                    )
                    _fail(failures[-1])
            elif _true_label_replay_root(cfg, paths) is not None:
                configured_mode = str(_cfg(cfg, "replay", "mode", "external_pseudolabel"))
                resolution = _resolve_true_label_replay_inputs(
                    cfg, paths, require_train=(configured_mode == "external_true_label")
                )
                assert resolution is not None
                _ok(
                    "true-label replay evaluation: "
                    f"{resolution.monitor_artifact.configuration_count} monitor configurations; "
                    f"source={resolution.source_path or resolution.monitor_path}"
                )
            else:
                warnings.append(
                    "legacy configuration has no [paths].replay_true_labels; pseudo-label replay remains diagnostic only"
                )
                _warn(warnings[-1])
        except Exception as exc:
            failures.append(str(exc))
            _fail(failures[-1])

    versions: dict[str, str | None] = {}
    for import_name in ("mdstats", "ase", "mace", "torch", "e3nn"):
        try:
            module = __import__(import_name)
            version = getattr(module, "__version__", None)
            versions[import_name] = None if version is None else str(version)
            _ok(f"import {import_name}" + (f" {version}" if version else ""))
        except Exception as exc:
            failures.append(f"cannot import {import_name}: {exc}")
            _fail(failures[-1])

    expected_mace = str(_cfg(cfg, "runtime", "mace_version", "0.3.16"))
    observed_mace = versions.get("mace")
    if observed_mace is not None and observed_mace != expected_mace:
        failures.append(f"MACE version mismatch: expected {expected_mace}, observed {observed_mace}")
        _fail(failures[-1])
    elif observed_mace is not None:
        _ok(f"MACE compatibility lock: {observed_mace}")

    runtime_freeze = None
    runtime_freeze_summary: dict[str, Any] = {}
    try:
        import mdstats

        runtime_freeze = mdstats.probe_mace_runtime_freeze()
        runtime_freeze_summary = runtime_freeze.to_dict()
        store.put_record("mace_runtime_freeze", runtime_freeze)
        if runtime_freeze.core_runtime_passed:
            source_mode = "exact" if runtime_freeze.source_lock_passed else "semantic"
            _ok(
                "MACE runtime source/dependency compatibility: "
                f"mace={runtime_freeze.mace_version}; e3nn={runtime_freeze.e3nn_version}; "
                f"source_mode={source_mode}"
            )
            if not runtime_freeze.source_lock_passed:
                mismatched = [
                    item.relative_path for item in runtime_freeze.source_evidence if not item.matched
                ]
                warnings.append(
                    "MACE 0.3.16 source bytes differ from the locked reference, but required semantic "
                    "compatibility probes passed; continuing under semantic source qualification. "
                    f"Differing/missing files: {', '.join(mismatched) or 'unknown'}."
                )
                _warn(warnings[-1])
        else:
            reasons = "; ".join(runtime_freeze.backend_failure_reasons("e3nn"))
            failures.append(f"MACE runtime freeze failed: {reasons or 'core runtime did not qualify'}")
            _fail(failures[-1])
        cueq_state = "available" if runtime_freeze.cueq_stack_available else "unavailable"
        oeq_state = "available" if runtime_freeze.oeq_available else "unavailable"
        _ok(f"accelerator capabilities: CuEq={cueq_state}; OpenEquivariance={oeq_state}")
    except Exception as exc:
        failures.append(f"MACE runtime-freeze probe failed: {exc}")
        _fail(failures[-1])

    disk = shutil.disk_usage(paths.workspace)
    free_disk_gib = disk.free / (1024 ** 3)
    minimum_free_disk_gib = float(_cfg(cfg, "execution", "minimum_free_disk_gib", 20.0))
    if free_disk_gib < minimum_free_disk_gib:
        failures.append(
            f"workspace has {free_disk_gib:.1f} GiB free; {minimum_free_disk_gib:.1f} GiB is required by policy"
        )
        _fail(failures[-1])
    else:
        _ok(f"workspace free disk: {free_disk_gib:.1f} GiB")

    wrappers = {}
    local_wrappers = _ensure_local_wrappers(paths)
    for executable in ("mdstats-mace-train", "mdstats-mace-eval", "mdstats-mace-select-head"):
        resolved = shutil.which(executable) or str(local_wrappers[executable])
        wrappers[executable] = resolved
        if Path(resolved).is_file():
            _ok(f"{executable}: {resolved}")
        else:
            failures.append(f"required wrapper is unavailable: {executable}")
            _fail(failures[-1])

    cuda: dict[str, Any] = {"requested": str(_cfg(cfg, "training", "device", "cuda")) == "cuda"}
    try:
        import torch
        cuda.update(
            {
                "available": bool(torch.cuda.is_available()),
                "device_count": int(torch.cuda.device_count()),
                "torch_version": str(torch.__version__),
                "cuda_version": torch.version.cuda,
            }
        )
        if torch.cuda.is_available():
            cuda["device_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            cuda["memory_gib"] = props.total_memory / (1024 ** 3)
            _ok(f"CUDA device: {cuda['device_name']} ({cuda['memory_gib']:.1f} GiB)")
        elif cuda["requested"]:
            failures.append("training.device=cuda but torch.cuda.is_available() is false")
            _fail(failures[-1])
        else:
            _warn("CUDA is unavailable; CPU-only smoke work is still possible.")
    except Exception as exc:
        failures.append(f"PyTorch CUDA probe failed: {exc}")
        _fail(failures[-1])

    acceleration_summary: dict[str, Any] = {}
    training_acceleration_summary: dict[str, Any] = {}
    acceleration_qualified_this_doctor = False
    try:
        import mdstats

        acceleration = _acceleration_policy(cfg)
        runtime_backend_failure = _runtime_freeze_backend_failure(acceleration, runtime_freeze)
        if runtime_backend_failure is not None:
            failures.append(runtime_backend_failure)
            _fail(failures[-1])
        if acceleration.only_cueq:
            failures.append(
                "[acceleration].only_cueq=true is not production-qualified by mdstats; "
                "use backend='cueq' with only_cueq=false so checkpoints are exported in portable e3nn form"
            )
            _fail(failures[-1])
        model_path = _path_cfg(cfg, paths, "foundation_model", required=False)
        if model_path is None:
            raise CampaignCliError("Acceleration qualification requires [paths].foundation_model.")
        sample_atoms = _doctor_sample_atoms(cfg, paths)
        if sample_atoms is None:
            raise CampaignCliError(
                "Acceleration qualification requires at least one readable target/replay structure."
            )
        corpus = _doctor_acceleration_corpus(sample_atoms)
        device = str(_cfg(cfg, "training", "device", "cuda"))
        dtype = str(_cfg(cfg, "training", "dtype", "float32"))
        potential = _resolved_foundation_potential_identity(cfg, paths)
        resolved_head = potential.foundation_head
        selected_head_qualification = _qualify_selected_head_training_foundation(
            cfg, paths, store, potential, corpus
        )
        if selected_head_qualification is not None:
            acceleration_summary["selected_head_training_foundation"] = selected_head_qualification.to_dict()
            _ok(
                "selected-head training foundation qualified: "
                f"{resolved_head}; derived_sha={selected_head_qualification.extraction.derived_checkpoint_sha256[:16]}"
            )
        probe = mdstats.probe_mace_acceleration(
            device=device,
            model_path=model_path,
            sample_atoms=sample_atoms,
            default_dtype=dtype,
            head=resolved_head,
            run_model_smoke=False,
        )
        parity_record = None
        training_parity_record = None
        if acceleration.backend is mdstats.MaceAccelerationBackend.E3NN:
            realization, inference = mdstats.qualify_e3nn_realization(
                model_path=model_path,
                head=resolved_head,
                structures=corpus,
                device=device,
                dtype=dtype,
                foundation_potential_digest=potential.canonical_content_digest,
                adapter_version=mdstats.MACE_ADAPTER_VERSION,
            )
        else:
            training_foundation_path = model_path
            if selected_head_qualification is not None:
                training_foundation_path = Path(
                    selected_head_qualification.extraction.derived_checkpoint_reference
                )
            realization, inference, parity_record, training_parity_record = mdstats.qualify_cueq_realization(
                model_path=model_path,
                head=resolved_head,
                structures=corpus,
                device=device,
                dtype=dtype,
                foundation_potential_digest=potential.canonical_content_digest,
                adapter_version=mdstats.MACE_ADAPTER_VERSION,
                probe=probe,
                prefer_hybrid=(str(potential.model_family) == "mace_mh_1"),
                training_model_path=training_foundation_path,
                training_head=resolved_head,
            )
        acceleration_summary = {
            "policy": acceleration.to_dict(),
            "probe": probe.to_dict(),
            "realization": realization.to_dict(),
            "parity": None if parity_record is None else parity_record.to_dict(),
            "training_parity": None if training_parity_record is None else training_parity_record.to_dict(),
        }
        store.put_record("acceleration_policy", acceleration)
        store.put_record("acceleration_probe", probe)
        store.put_record("acceleration_realization", realization)
        if parity_record is not None:
            store.put_record("acceleration_parity", parity_record)
        if training_parity_record is not None:
            store.put_record("acceleration_training_parity", training_parity_record)
        if realization.foundation_inference_identity_digest != inference.content_digest:
            raise CampaignCliError("Acceleration realization/inference identity mismatch.")
        if realization.qualified:
            acceleration_qualified_this_doctor = True
            provider_for_calibration = mdstats.MaceCalculatorProvider.from_model_path(
                model_path,
                device=device,
                default_dtype=dtype,
                model_family=potential.model_family,
                supported_atomic_numbers=potential.model_atomic_numbers,
                requested_atomic_numbers=tuple(
                    int(v)
                    for v in _cfg(
                        cfg,
                        "profile",
                        "all_atomic_numbers",
                        (3, 8, 11, 13, 14, 19),
                    )
                ),
                foundation_potential_identity=potential,
                foundation_inference_identity=inference,
                **realization.calculator_kwargs(),
            )
            resources = _performance_resources(cfg)
            maximum_batch = max(
                1, int(_cfg(cfg, "model", "maximum_inference_batch_size", 16))
            )
            stress_count = max(1, int(_cfg(cfg, "model", "batch_calibration_stress_structures", 8)))
            if len(corpus) <= stress_count:
                calibration_corpus = corpus
            else:
                indices = np.linspace(0, len(corpus) - 1, num=stress_count, dtype=np.int64)
                calibration_corpus = tuple(corpus[int(index)] for index in indices)
            batch_calibration = provider_for_calibration.calibrate_batch_capacity(
                calibration_corpus,
                mdstats.MaceDescriptorPolicy(),
                maximum_batch_size=maximum_batch,
                device_budget_bytes=resources.gpu.budget_bytes,
                workload_mode=mdstats.MaceBatchWorkloadMode.COMBINED_EVALUATE,
                max_device_fraction=float(_cfg(cfg, "model", "vram_max_device_fraction", 0.80)),
                reserve_bytes=int(float(_cfg(cfg, "model", "vram_reserve_gib", 4.0)) * 1024**3),
                throughput_tolerance_fraction=float(_cfg(cfg, "model", "batch_throughput_tolerance_fraction", 0.05)),
                stress_sample_count=min(stress_count, len(calibration_corpus)),
            )
            store.put_record("model_sweep_batch_calibration", batch_calibration)
            acceleration_summary["data6_batch_calibration"] = batch_calibration.to_dict()
            _ok(
                f"acceleration backend: {acceleration.backend.value}; "
                f"inference kernel={realization.resolved_kernel_mode}; "
                f"training kernel={realization.training_kernel_mode}; corpus={len(corpus)} structures"
            )
            _ok(
                "DATA6 descriptor capacity: "
                f"signature={batch_calibration.descriptor_signature_digest[:12]}, "
                f"recommended_batch={batch_calibration.recommended_batch_size}, "
                f"descriptor_bytes/structure={batch_calibration.descriptor_bytes_per_structure}"
            )
            if acceleration.enable_cueq:
                versions_text = ", ".join(
                    f"{name}={version or 'unknown'}" for name, version in realization.cueq_versions
                )
                _ok(f"cuEquivariance stack: {versions_text}")
                if realization.oeq_version is not None:
                    _ok(f"OpenEquivariance: {realization.oeq_version}")
                if parity_record is not None:
                    _ok(
                        "CuEq/e3nn parity passed: "
                        f"E/atom max={parity_record.energy_max_abs:.3e}, "
                        f"Fmax={parity_record.force_max_abs:.3e}, "
                        f"Smax={parity_record.stress_max_abs:.3e}, "
                        f"Dmax={parity_record.descriptor_max_abs:.3e}; "
                        f"selection_identical={parity_record.selection_identical}"
                    )
        elif acceleration.require_available:
            failures.append(
                f"requested acceleration backend {acceleration.backend.value!r} is not qualified: "
                f"{realization.failure_reason or 'unknown failure'}"
            )
            _fail(failures[-1])
        else:
            warnings.append(
                f"requested acceleration backend {acceleration.backend.value!r} is not qualified; "
                "the campaign remains non-authorizing until the configuration is changed explicitly"
            )
            _warn(warnings[-1])

        # Revision 60 phase separation: source/DATA6/evaluation keep the
        # realization above while TRAIN2 may freeze a different backend against
        # the exact selected-head checkpoint that MACE will fine-tune.
        if _phase_separated_acceleration(cfg):
            training_acceleration = _training_acceleration_policy(cfg)
            runtime_training_failure = _runtime_freeze_backend_failure(
                training_acceleration, runtime_freeze
            )
            if runtime_training_failure is not None:
                failures.append("TRAIN2 " + runtime_training_failure)
                _fail(failures[-1])
            if training_acceleration.only_cueq:
                failures.append(
                    "[acceleration].only_cueq=true is not production-qualified by mdstats; "
                    "keep only_cueq=false so CuEq training checkpoints are converted back to portable e3nn form"
                )
                _fail(failures[-1])
            training_foundation_path = model_path
            selected_digest = None
            if selected_head_qualification is not None:
                training_foundation_path = Path(
                    selected_head_qualification.extraction.derived_checkpoint_reference
                )
                selected_digest = selected_head_qualification.content_digest
            # CUEQ-REPEAT1-PARITY1: stable E/S/D channels retain the tight
            # FP32 1e-5/1e-6 policy.  TRAIN2 forces use one discarded warm-up,
            # ten post-warm-up outputs/backend, and 45/45/100 all-pairs
            # self/cross statistics normalized against the measured self-noise.
            training_parity_policy = _training_acceleration_parity_policy()
            training_noise_policy = _training_acceleration_noise_normalized_policy()
            training_realization, phase_training_parity = (
                mdstats.qualify_training_acceleration_realization(
                    backend=training_acceleration.backend,
                    training_model_path=training_foundation_path,
                    training_head=resolved_head,
                    structures=corpus,
                    device=device,
                    dtype=dtype,
                    selected_head_qualification_digest=selected_digest,
                    probe=probe,
                    parity_policy=training_parity_policy,
                    noise_normalized_policy=training_noise_policy,
                )
            )
            phase_training_repeatability = None
            phase_training_deterministic_control = None
            if isinstance(phase_training_parity, mdstats.TrainingAccelerationNoiseNormalizedParityRecord):
                phase_training_repeatability = phase_training_parity.repeatability
                store.put_record("training_acceleration_repeatability_diagnostic", phase_training_repeatability)
                store.put_record("training_acceleration_noise_normalized_parity", phase_training_parity)
                # Rev. 86 removes deterministic-control execution from routine doctor.
                # Drop stale DIAG2/3 control evidence so it cannot masquerade as current authority.
                store.delete_record("training_acceleration_deterministic_control_diagnostic")
                _print_training_repeatability_diagnostic(
                    phase_training_repeatability,
                    title="TRAIN2 FP32 warm-up/all-pairs parity evidence (authorizing)",
                )
                ratios = (
                    phase_training_parity.force_rmse_ratio,
                    phase_training_parity.force_p99_ratio,
                    phase_training_parity.force_p999_ratio,
                )
                ratio_text = ", ".join("inf" if value is None else f"{value:.3f}" for value in ratios)
                print(
                    "[PARITY] TRAIN2 FP32 noise-normalized: "
                    f"ratios(Frmse,Fp99,Fp99.9)=({ratio_text}); "
                    f"Fmax={phase_training_parity.force_max_cross:.3e}/"
                    f"{phase_training_parity.force_max_limit:.3e}; "
                    f"selection_identical={phase_training_parity.selection_identical}; "
                    f"passed={phase_training_parity.passed}",
                    flush=True,
                )
            training_acceleration_summary = {
                "policy": training_acceleration.to_dict(),
                "parity_policy": training_parity_policy.to_dict(),
                "noise_normalized_parity_policy": training_noise_policy.to_dict(),
                "realization": training_realization.to_dict(),
                "parity": None if phase_training_parity is None else phase_training_parity.to_dict(),
                "repeatability_diagnostic": (
                    None if phase_training_repeatability is None else phase_training_repeatability.to_dict()
                ),
                "deterministic_control_diagnostic": (
                    None if phase_training_deterministic_control is None else phase_training_deterministic_control.to_dict()
                ),
            }
            store.put_record("training_acceleration_policy", training_acceleration)
            store.put_record("training_acceleration_parity_policy", training_parity_policy)
            store.put_record("training_acceleration_noise_normalized_parity_policy", training_noise_policy)
            store.put_record("training_acceleration_realization", training_realization)
            if phase_training_parity is not None:
                store.put_record("training_acceleration_parity", phase_training_parity)
            if training_realization.qualified:
                _ok(
                    f"TRAIN2 acceleration backend: {training_acceleration.backend.value}; "
                    f"kernel={training_realization.training_kernel_mode}; "
                    f"checkpoint={training_realization.training_checkpoint_sha256[:16]}"
                )
            elif training_acceleration.require_available:
                failures.append(
                    f"requested TRAIN2 acceleration backend {training_acceleration.backend.value!r} is not qualified: "
                    f"{training_realization.failure_reason or 'unknown failure'}"
                )
                _fail(failures[-1])
            else:
                warnings.append(
                    f"requested TRAIN2 acceleration backend {training_acceleration.backend.value!r} is not qualified; "
                    "training remains non-authorizing until the configuration is changed explicitly"
                )
                _warn(warnings[-1])
    except Exception as exc:
        failures.append(f"acceleration qualification failed: {exc}")
        _fail(failures[-1])

    resource_snapshot = _performance_resources(cfg)
    _ok(f"resource budget: {resource_snapshot.summary()}")

    replay_summary: dict[str, Any] = {}
    try:
        import mdstats
        _single_replay_cfg = mdstats.single_source_replay_config_from_campaign(
            cfg, base_directory=paths.config_dir
        )
    except Exception:
        _single_replay_cfg = None
    replay_mode = (
        "external_pseudolabel"
        if _single_replay_cfg is not None
        and _single_replay_cfg.label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        else "external_true_label"
        if _single_replay_cfg is not None
        else str(_cfg(cfg, "replay", "mode", "external_pseudolabel")).strip().lower()
    )
    foundation_section = cfg.get("foundation")
    canonical_foundation = bool(
        isinstance(foundation_section, Mapping)
        and not bool(foundation_section.get("legacy_normalized", False))
    )
    replay_waits_for_acceleration = bool(
        canonical_foundation
        and _requires_replay(cfg)
        and replay_mode == "external_pseudolabel"
        and not acceleration_qualified_this_doctor
    )
    if replay_waits_for_acceleration:
        replay_summary = {
            "required": True,
            "mode": replay_mode,
            "qualified": False,
            "deferred": True,
            "reason": "acceleration realization is not yet qualified",
        }
        warnings.append(
            "replay qualification deferred because canonical pseudolabel provenance depends on the "
            "doctor-frozen acceleration realization; fix the acceleration failure and rerun doctor"
        )
        _warn(warnings[-1])
    elif (
        _single_replay_cfg is not None
        and _single_replay_cfg.label_mode is mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    ):
        # Doctor validates the single source and the exact inference runtime but
        # does not spend a full replay-wide model pass. Preparation owns the
        # expensive prediction cache and all derived transport materialization.
        replay_summary = {
            "required": True,
            "mode": replay_mode,
            "qualified": False,
            "deferred": True,
            "reason": "single-source foundation predictions are materialized during prepare",
            "source": _single_replay_cfg.replay_set_path,
            "split_ratio": list(_single_replay_cfg.split_ratio),
            "split_seed": _single_replay_cfg.split_seed,
        }
        _ok(
            "single-source replay interface validated; foundation pseudo-label generation "
            "and deterministic split are deferred to prepare"
        )
    elif not failures or all("replay_" not in item for item in failures):
        try:
            replay_plan, replay_summary, replay_failures, replay_warnings = _qualify_replay(cfg, paths)
            store.put_record("replay_plan_doctor", replay_plan)
            store.put_record("replay_qualification", replay_summary)
            _persist_single_source_replay_authority(store, cfg, paths)
            failures.extend(replay_failures)
            warnings.extend(replay_warnings)
            if replay_summary["required"]:
                _ok(
                    "replay train/monitor are numerically valid and disjoint "
                    f"({replay_summary['train_count']} / {replay_summary['monitor_count']} configurations; "
                    f"{replay_summary['label_mode']})"
                )
            else:
                _ok("replay is not required by the selected training modes")
            for message in replay_failures:
                _fail(message)
            for message in replay_warnings:
                _warn(message)
        except Exception as exc:
            failures.append(f"replay qualification failed: {exc}")
            _fail(failures[-1])

    payload = {
        "timestamp_utc": _utc_now(),
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "versions": versions,
        "expected_mace_version": expected_mace,
        "workspace_free_disk_gib": free_disk_gib,
        "minimum_free_disk_gib": minimum_free_disk_gib,
        "wrappers": wrappers,
        "cuda": cuda,
        "acceleration": acceleration_summary,
        "training_acceleration": training_acceleration_summary,
        "mace_runtime_freeze": runtime_freeze_summary,
        "replay": replay_summary,
        "resources": {
            "cpu_threads_available": resource_snapshot.cpu_threads_available,
            "cpu_threads_budget": resource_snapshot.cpu_threads_budget,
            "cpu_fraction": resource_snapshot.cpu_fraction,
            "ram_available_bytes": resource_snapshot.ram_available_bytes,
            "ram_budget_bytes": resource_snapshot.ram_budget_bytes,
            "ram_fraction": resource_snapshot.ram_fraction,
            "gpu_memory_fraction": resource_snapshot.gpu_memory_fraction,
            "gpu_available": resource_snapshot.gpu.available,
            "gpu_device_name": resource_snapshot.gpu.device_name,
            "gpu_free_bytes": resource_snapshot.gpu.free_bytes,
            "gpu_budget_bytes": resource_snapshot.gpu.budget_bytes,
        },
    }
    store.put_record("doctor", payload)
    _update_benchmark(paths, "doctor", payload)
    if failures:
        _mark_stage(store, paths, "doctor", StageState.FAILED, f"{len(failures)} blocking checks failed")
        print("\nFix every [FAIL] item before continuing.")
        return 1
    _mark_stage(store, paths, "doctor", StageState.COMPLETE, "environment and inputs passed")
    if not bool(getattr(args, "embedded", False)):
        print("\nDoctor passed. Next: run `prepare`; review the automatically populated manifest, then rerun with `--approve-manifest`.")
    return 0


def _performance_resources(cfg: Mapping[str, Any]):
    """Resolve the campaign-wide 90%-CPU/GPU and 80%-RAM budget."""

    device = str(_cfg(cfg, "model", "device", _cfg(cfg, "training", "device", "cuda")))
    try:
        return detect_system_resources(
            cpu_fraction=float(_cfg(cfg, "performance", "cpu_fraction", 0.9)),
            ram_fraction=float(_cfg(cfg, "performance", "ram_fraction", 0.8)),
            gpu_memory_fraction=float(_cfg(cfg, "performance", "gpu_memory_fraction", 0.9)),
            device=device,
        )
    except ValueError as exc:
        raise CampaignCliError(str(exc)) from exc


def _source_worker_memory_estimate(payloads: Sequence[Mapping[str, Any]]) -> int:
    """Conservative peak-RSS estimate for one isolated XML worker."""

    estimates: list[int] = []
    for payload in payloads:
        run = payload.get("run", {})
        locator = run.get("vasprun") or run.get("source_locator")
        base = Path(str(payload.get("base_directory", ".")))
        path = Path(str(locator)) if locator is not None else Path()
        if not path.is_absolute():
            path = base / path
        try:
            file_bytes = path.stat().st_size
        except OSError:
            file_bytes = 0
        # XML text, parser nodes, normalized arrays, ASE objects, and quality
        # records coexist briefly.  The 384 MiB floor matches the production
        # LTA profile while the size term scales for unusually large sources.
        estimates.append(max(384 * 1024**2, int(file_bytes * 3.0) + 256 * 1024**2))
    return max(estimates, default=512 * 1024**2)


def _resolve_source_worker_count(
    cfg: Mapping[str, Any], payloads: Sequence[Mapping[str, Any]]
) -> tuple[int, Any, int]:
    requested = int(_cfg(cfg, "performance", "source_workers", 0))
    resources = _performance_resources(cfg)
    estimate = _source_worker_memory_estimate(payloads)
    try:
        workers = resolve_worker_count(
            task_count=len(payloads),
            resources=resources,
            requested=requested,
            estimated_bytes_per_worker=estimate,
        )
    except ValueError as exc:
        raise CampaignCliError(str(exc)) from exc
    return workers, resources, estimate


def _resolve_feature_worker_count(
    cfg: Mapping[str, Any],
    *,
    run_count: int,
    estimated_bytes_per_worker: int,
    reserved_bytes: int = 0,
    startup_sensitive: bool = False,
) -> tuple[int, Any]:
    """Resolve process-level run concurrency within CPU and RAM budgets.

    One-shot process workers are intentionally used for the object-heavy MLFF
    stages so native-library state and RSS are released after every trajectory.
    For startup-sensitive stages, automatic mode stays serial on very small CPU
    allocations where interpreter startup costs exceed useful parallel work.
    Explicit positive worker counts still request parallel execution, subject to
    the hard resource bounds.
    """

    requested = int(_cfg(cfg, "performance", "feature_workers", 0))
    resources = _performance_resources(cfg)
    try:
        workers = resolve_worker_count(
            task_count=run_count,
            resources=resources,
            requested=requested,
            estimated_bytes_per_worker=estimated_bytes_per_worker,
            reserved_bytes=max(0, int(reserved_bytes)),
        )
    except ValueError as exc:
        raise CampaignCliError(str(exc)) from exc
    if requested == 0 and startup_sensitive and resources.cpu_threads_budget < 4:
        workers = 1
    return workers, resources


def _estimated_lta_state_count(
    cfg: Mapping[str, Any], frame_data_by_run: Mapping[str, Any]
) -> int:
    mobile_numbers = set(int(v) for v in _cfg(
        cfg, "profile", "mobile_atomic_numbers", (3, 11, 19)
    ))
    return sum(
        int(data.n_frames)
        * sum(int(value) in mobile_numbers for value in data.atomic_numbers)
        for data in frame_data_by_run.values()
    )


def _resolve_lta_worker_count(
    cfg: Mapping[str, Any], *, frame_data_by_run: Mapping[str, Any]
) -> tuple[int, int, Any, int]:
    """Resolve compact LTA-column workers under the 80% RAM envelope.

    Workers return compact NumPy columns rather than hundreds of thousands of
    Python records.  This makes trajectory-level process parallelism economical;
    the parent-side immutable catalog is included as reserved memory so worker
    concurrency cannot consume the space needed to materialize the final result.
    """

    requested = int(_cfg(cfg, "performance", "lta_workers", 0))
    if requested < 0:
        raise CampaignCliError(
            "performance.lta_workers must be zero (auto) or positive."
        )
    resources = _performance_resources(cfg)
    estimated_states = _estimated_lta_state_count(cfg, frame_data_by_run)
    total_frames = sum(int(data.n_frames) for data in frame_data_by_run.values())
    # Empirical upper bound for the retained immutable Python catalog plus its
    # per-frame index. Current available RAM already excludes arrays and objects
    # resident before this stage, so this reserve covers only new output growth.
    reserved_bytes = estimated_states * 2300 + total_frames * 4096
    estimate_per_worker = max(512 * 1024**2, reserved_bytes // max(1, len(frame_data_by_run)))
    try:
        workers = resolve_worker_count(
            task_count=len(frame_data_by_run),
            resources=resources,
            requested=requested,
            estimated_bytes_per_worker=estimate_per_worker,
            reserved_bytes=reserved_bytes,
        )
    except ValueError as exc:
        raise CampaignCliError(str(exc)) from exc
    return workers, estimated_states, resources, reserved_bytes






def _source_worker_file_stem(run_id: str) -> str:
    return hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]


def _run_source_ingestion_workers(
    payloads: Sequence[Mapping[str, Any]],
    *,
    paths: CampaignPaths,
    worker_count: int,
    progress_interval_seconds: float,
    timeout_seconds: float | None,
) -> list[dict[str, Any]]:
    """Run one fresh interpreter per source with bounded parallelism."""

    worker_root = paths.internal / "source-ingestion"
    if worker_root.exists():
        shutil.rmtree(worker_root)
    requests = worker_root / "requests"
    results = worker_root / "results"
    logs = worker_root / "logs"
    for directory in (requests, results, logs):
        directory.mkdir(parents=True, exist_ok=True)

    pending: deque[dict[str, Any]] = deque()
    for payload in payloads:
        run_id = str(payload["run"]["run_id"])
        stem = _source_worker_file_stem(run_id)
        request_path = requests / f"{stem}.json"
        result_path = results / f"{stem}.json"
        stdout_path = logs / f"{stem}.stdout.log"
        stderr_path = logs / f"{stem}.stderr.log"
        _atomic_json(request_path, payload)
        pending.append(
            {
                "run_id": run_id,
                "request": request_path,
                "result": result_path,
                "stdout": stdout_path,
                "stderr": stderr_path,
            }
        )

    active: dict[subprocess.Popen[Any], dict[str, Any]] = {}
    completed_results: list[dict[str, Any]] = []
    progress = _ProgressReporter("DATA2", len(pending))
    completed_count = 0

    def launch(item: dict[str, Any]) -> None:
        command = (
            sys.executable, "-m", "mdstats.training_data.source_worker",
            "--request", str(item["request"]),
            "--result", str(item["result"]),
        )
        stdout_handle = item["stdout"].open("wb")
        stderr_handle = item["stderr"].open("wb")
        source_root = Path(__file__).resolve().parents[2]
        worker_env = configure_worker_thread_environment(dict(os.environ), threads=1)
        existing_pythonpath = worker_env.get("PYTHONPATH", "")
        worker_env["PYTHONPATH"] = os.pathsep.join(
            [str(source_root)] + ([existing_pythonpath] if existing_pythonpath else [])
        )
        try:
            process = subprocess.Popen(
                command,
                cwd=source_root,
                env=worker_env,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=(os.name == "posix"),
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
        item["started"] = time.monotonic()
        item["last_heartbeat"] = item["started"]
        item["command"] = command
        active[process] = item
        print(
            f"[DATA2 START] {item['run_id']} — worker pid={process.pid}",
            flush=True,
        )

    try:
        while pending or active:
            while pending and len(active) < worker_count:
                launch(pending.popleft())
            finished: list[subprocess.Popen[Any]] = []
            now = time.monotonic()
            for process, item in list(active.items()):
                return_code = process.poll()
                elapsed = now - float(item["started"])
                if return_code is None:
                    if timeout_seconds is not None and elapsed >= timeout_seconds:
                        _terminate_process(process, grace_seconds=10.0)
                        raise CampaignCliError(
                            f"DATA2 source worker timed out for {item['run_id']!r} after "
                            f"{_ProgressReporter._duration(elapsed)}. Logs: {item['stderr']}"
                        )
                    if now - float(item["last_heartbeat"]) >= progress_interval_seconds:
                        print(
                            f"[DATA2 {item['run_id']}] status=running; phase=parsing; "
                            f"elapsed={format_progress_time(elapsed)}; eta=--:--:--; "
                            f"stdout={_file_size_mib(item['stdout']):.1f} MiB; "
                            f"stderr={_file_size_mib(item['stderr']):.1f} MiB",
                            flush=True,
                        )
                        item["last_heartbeat"] = now
                    continue
                finished.append(process)
                if return_code != 0:
                    stderr_tail = item["stderr"].read_text(
                        encoding="utf-8", errors="replace"
                    )[-4000:]
                    raise CampaignCliError(
                        f"DATA2 source worker failed for {item['run_id']!r} "
                        f"with exit code {return_code}:\n{stderr_tail}"
                    )
                if not item["result"].is_file():
                    raise CampaignCliError(
                        f"DATA2 source worker produced no result for {item['run_id']!r}."
                    )
                result = json.loads(item["result"].read_text(encoding="utf-8"))
                completed_results.append(result)
                completed_count += 1
                source_payload = result["source"]
                timing = result["timings"]
                source_seconds = sum(
                    float(timing[name])
                    for name in ("controls_seconds", "frames_seconds", "assessment_seconds")
                )
                warning_lines = [
                    line for line in item["stderr"].read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    if line.strip()
                ]
                detail = (
                    f"frames={source_payload['frame_count']}, "
                    f"quality={source_payload['quality_outcome']}, "
                    f"production={source_payload['production_status']}, "
                    f"worker_elapsed={format_progress_time(source_seconds)}"
                )
                if warning_lines:
                    detail += f", warning-log={item['stderr'].name}"
                progress.item_done(completed_count, str(item["run_id"]), detail)
            for process in finished:
                active.pop(process, None)
            if active and not finished:
                time.sleep(0.2)
    except Exception:
        for process in active:
            _terminate_process(process, grace_seconds=5.0)
        raise
    return completed_results


def _prepare_catalog(
    cfg: Mapping[str, Any],
    paths: CampaignPaths,
    store: CampaignStore,
    *,
    approve_manifest: bool,
    refresh_inferences: bool = False,
) -> dict[str, Any]:
    """Build DATA2-DATA5 with one VASP frame decode per source."""

    import mdstats

    manifest = _ensure_manifest(
        cfg, paths, approve=approve_manifest, refresh_inferences=refresh_inferences
    )
    training_root = _path_cfg(cfg, paths, "training_root")
    assert training_root is not None
    start = time.monotonic()
    source_policy = mdstats.SourceAuditPolicy(
        trajectory_assessment_mode=mdstats.SourceTrajectoryAssessmentMode.FULL_REQUIRED,
        fail_on_unresolved_label_domain=True,
    )

    _print_header("DATA2 source ingestion and quality assessment")
    cache_root = paths.internal / "frame-cache"
    if cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    source_by_run: dict[str, Any] = {}
    targets: dict[str, Any] = {}
    cache_records: list[dict[str, Any]] = []
    source_timings: list[dict[str, Any]] = []
    worker_payloads = [
        {
            "run": run.to_dict(),
            "source_policy": source_policy.to_dict(),
            "base_directory": str(training_root),
            "cache_directory": str(cache_root),
        }
        for run in manifest.runs
    ]
    worker_count, resources, source_worker_bytes = _resolve_source_worker_count(cfg, worker_payloads)
    print(f"Resource plan: {resources.summary()}", flush=True)
    print(
        f"Parsing {len(manifest.runs)} sources with {worker_count} isolated worker(s); "
        f"estimated peak per worker={source_worker_bytes / (1024**3):.2f} GiB. "
        "Each worker decodes one XML, assesses quality, writes normalized arrays, then exits.",
        flush=True,
    )
    worker_results = _run_source_ingestion_workers(
        worker_payloads,
        paths=paths,
        worker_count=worker_count,
        progress_interval_seconds=float(
            _cfg(cfg, "performance", "progress_interval_seconds", 30.0)
        ),
        timeout_seconds=_optional_positive_float(
            _cfg(cfg, "performance", "source_timeout_seconds")
        ),
    )
    for result in worker_results:
        run_id = str(result["run_id"])
        source = mdstats.TrainingDataSource.from_dict(result["source"])
        target_payload = result["temperature_target"]
        source_by_run[run_id] = source
        targets[run_id] = mdstats.TemperatureTargetEvidence(
            target_start_kelvin=target_payload["target_start_kelvin"],
            target_end_kelvin=target_payload["target_end_kelvin"],
            evidence=str(target_payload["evidence"]),
        )
        cache_records.append(dict(result["cache_record"]))
        timing = dict(result["timings"])
        wall_seconds = sum(
            float(timing[name])
            for name in ("controls_seconds", "frames_seconds", "assessment_seconds")
        )
        source_timings.append(
            {
                "run_id": run_id,
                "wall_seconds": wall_seconds,
                "controls_seconds": float(timing["controls_seconds"]),
                "frames_seconds": float(timing["frames_seconds"]),
                "assessment_seconds": float(timing["assessment_seconds"]),
                "frame_count": source.frame_count,
            }
        )

    sources = mdstats.build_training_data_source_catalog_from_sources(
        manifest, source_by_run, source_policy=source_policy
    )
    cache_finalize_start = time.monotonic()
    mdstats.finalize_frame_data_cache(
        sources, cache_records, cache_root, verify_entry_hashes=False
    )
    cache_finalize_seconds = time.monotonic() - cache_finalize_start
    cache_load_start = time.monotonic()
    frame_data = mdstats.load_frame_data_cache(
        sources, cache_root, verify_hashes=False
    )
    cache_load_seconds = time.monotonic() - cache_load_start
    _ok(
        f"DATA2 complete: {len(sources.sources)} audited sources; normalized arrays restored "
        f"in {format_progress_time(cache_load_seconds)}"
    )
    del worker_results, worker_payloads, source_by_run, cache_records
    gc.collect()

    role_budget = mdstats.PartitionRoleBudgetPolicy(
        purge_units_between_roles=int(_cfg(cfg, "partition", "purge_units_between_roles", 1)),
    )
    partition_policy = mdstats.PartitionPolicy(
        role_budget=role_budget,
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=int(_cfg(cfg, "partition", "minimum_block_frames", 32))
        ),
    )

    stage_start = time.monotonic()
    _print_header("DATA3 frame identity, eligibility, and strain")
    total_retained_frames = sum(v.n_frames for v in frame_data.values())
    print(
        f"Building immutable records for {total_retained_frames} retained frames...",
        flush=True,
    )
    data3_reserved_bytes = int(total_retained_frames) * 8192
    data3_workers, feature_resources = _resolve_feature_worker_count(
        cfg,
        run_count=len(frame_data),
        estimated_bytes_per_worker=384 * 1024**2,
        reserved_bytes=data3_reserved_bytes,
        startup_sensitive=True,
    )
    print(
        f"DATA3 resource plan: {data3_workers} isolated run worker(s); "
        f"reserved output={data3_reserved_bytes / 1024**3:.2f} GiB; "
        f"{feature_resources.summary()}",
        flush=True,
    )
    if data3_workers == 1 and feature_resources.cpu_threads_budget < 4:
        print(
            "DATA3 automatic mode selected serial execution because fewer than "
            "four CPU threads are budgeted and one-shot process startup would "
            "dominate this stage.",
            flush=True,
        )
    frames = mdstats.build_training_frame_catalog(
        sources, frame_data, temperature_targets_by_run=targets,
        parallel_workers=data3_workers,
        progress_callback=lambda message: print(f"[DATA3] {message}", flush=True),
    )
    data3_seconds = time.monotonic() - stage_start
    _ok(f"DATA3 complete: {len(frames.frames)} frames; elapsed={format_progress_time(data3_seconds)}")

    stage_start = time.monotonic()
    _print_header("DATA4 full-resolution features and event evidence")
    print("Computing raw, LTA partition, and event features without temporal thinning...", flush=True)
    data4_progress = _ProgressReporter(
        "DATA4", 3 * len(frame_data),
        minimum_interval_seconds=float(_cfg(cfg, "performance", "progress_interval_seconds", 15.0)),
    )
    data4_progress_count = 0

    def report_data4(message: str) -> None:
        nonlocal data4_progress_count
        data4_progress_count += 1
        data4_progress.item_done(
            data4_progress_count, message,
            detail=f"rss={_process_rss_mib():.0f} MiB",
            force=True,
        )

    raw_reserved_bytes = int(total_retained_frames) * 6144
    raw_workers, _ = _resolve_feature_worker_count(
        cfg,
        run_count=len(frame_data),
        estimated_bytes_per_worker=384 * 1024**2,
        reserved_bytes=raw_reserved_bytes,
        startup_sensitive=True,
    )
    lta_workers, estimated_lta_states, lta_resources, lta_reserved_bytes = (
        _resolve_lta_worker_count(cfg, frame_data_by_run=frame_data)
    )
    print(
        f"DATA4 raw-feature workers={raw_workers}; "
        f"LTA compact-column workers={lta_workers}; "
        f"estimated LTA states={estimated_lta_states:,}; "
        f"reserved LTA output={lta_reserved_bytes / 1024**3:.2f} GiB",
        flush=True,
    )
    if (
        lta_resources.ram_budget_bytes is not None
        and lta_reserved_bytes >= lta_resources.ram_budget_bytes
    ):
        print(
            "[WARN] Estimated persistent LTA catalog alone approaches or exceeds "
            "the configured 80% available-RAM budget. Worker concurrency was "
            "reduced to one; consider more RAM or a smaller campaign partition.",
            flush=True,
        )

    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        material_profile_contracts=_material_profile_contracts(cfg),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(),
        event_policy=mdstats.EventDetectionPolicy(pre_frames=2, post_frames=2),
        partition_role_budget=role_budget,
        progress_callback=report_data4,
        parallel_workers=raw_workers,
        lta_parallel_workers=lta_workers,
    )
    data4_seconds = time.monotonic() - stage_start
    _ok(f"DATA4 complete; elapsed={format_progress_time(data4_seconds)}")

    stage_start = time.monotonic()
    _print_header("DATA5 leakage-safe partition construction")
    data5 = mdstats.build_data5_partition_bundle(
        sources, frames, data4, partition_policy=partition_policy
    )
    data5_seconds = time.monotonic() - stage_start
    _ok(f"DATA5 complete; elapsed={format_progress_time(data5_seconds)}")

    cache_seconds = cache_finalize_seconds + cache_load_seconds
    cache_bytes = sum(path.stat().st_size for path in cache_root.glob("*.npz"))
    _ok(
        f"normalized frame cache: {cache_bytes / (1024 ** 3):.2f} GiB; "
        f"manifest finalization + restore={format_progress_time(cache_seconds)}"
    )

    _print_header("Persisting checksum-verified campaign state")

    def persist_record(key: str, value: Any) -> None:
        persisted_start = time.monotonic()
        print(f"[state] writing {key}...", flush=True)
        store.put_record(key, value)
        _ok(f"[state] {key} persisted; elapsed={format_progress_time(time.monotonic() - persisted_start)}")

    persist_record("manifest", manifest)
    persist_record("source_catalog", sources)
    persist_record("frame_catalog", frames)
    persist_record("data4", data4)
    persist_record("data5", data5)
    persist_record(
        "normalization_manifest",
        {
            "schema": "mdstats.mlff-campaign-normalization.v1",
            "manifest_digest": manifest.content_digest,
            "source_catalog_digest": sources.content_digest,
            "frame_catalog_digest": frames.content_digest,
            "policy": "native_vasp_labels_and_canonical_mdstats_units",
        },
    )
    persist_record(
        "reference_manifest",
        {
            "schema": "mdstats.mlff-campaign-reference.v1",
            "reference_groups": sorted({v.reference_group for v in sources.sources if v.reference_group is not None}),
            "reference_runs": sorted({v.reference_run_id for v in sources.sources if v.reference_run_id is not None}),
        },
    )
    elapsed = time.monotonic() - start
    eligible = sum(v.state.value == "eligible" for v in frames.eligibility.decisions)
    summary = {
        "wall_seconds": elapsed,
        "source_count": len(sources.sources),
        "source_worker_count": worker_count,
        "frame_count": len(frames.frames),
        "eligible_frame_count": eligible,
        "data3_seconds": data3_seconds,
        "data4_seconds": data4_seconds,
        "data5_seconds": data5_seconds,
        "frame_cache_seconds": cache_seconds,
        "frame_cache_bytes": cache_bytes,
        "source_timings": source_timings,
        "leakage_audit_passed": data5.leakage_audit.passed,
    }
    _update_benchmark(paths, "prepare_catalog", summary)
    if not data5.leakage_audit.passed:
        raise CampaignCliError(
            "DATA5 leakage audit failed. Inspect the manifest independence and reference declarations."
        )
    _ok(f"catalogued {len(sources.sources)} runs and {len(frames.frames)} frames; elapsed={format_progress_time(elapsed)}")
    _ok("DATA5 leakage audit passed")
    return frame_data





def _training_method_specs(cfg: Mapping[str, Any]) -> tuple[_TrainingMethodSpec, ...]:
    """Resolve the explicit per-method stochastic training matrix.

    New campaign files use nested method tables.  Legacy ``modes``/``seeds``
    remain readable so existing campaigns can resume without editing their
    frozen TOML; they inherit the legacy shared fold count and partition seed.
    """

    training = cfg.get("training", {})
    if not isinstance(training, Mapping):
        raise CampaignCliError("[training] must be a TOML table.")
    nested_present = any(
        isinstance(training.get(mode), Mapping)
        for mode in ("naive_fine_tuning", "multihead_replay")
    )
    result: list[_TrainingMethodSpec] = []
    if nested_present:
        for mode in ("naive_fine_tuning", "multihead_replay"):
            payload = training.get(mode)
            if payload is None:
                continue
            if not isinstance(payload, Mapping):
                raise CampaignCliError(f"[training.{mode}] must be a TOML table.")
            if not bool(payload.get("enabled", True)):
                continue
            result.append(
                _TrainingMethodSpec(
                    mode=mode,
                    seeds=tuple(int(value) for value in payload.get("seeds", (1, 2))),
                    cross_validation_folds=int(
                        payload.get("cross_validation_folds", 0)
                    ),
                    fold_partition_seed=int(
                        payload.get("fold_partition_seed", 104729)
                    ),
                    seed_mode=str(payload.get("seed_mode", "optimizer_only")),
                )
            )
    else:
        modes = tuple(
            str(value)
            for value in training.get("modes", ("multihead_replay",))
        )
        seeds = tuple(int(value) for value in training.get("seeds", (1, 2)))
        result.extend(
            _TrainingMethodSpec(
                mode=mode,
                seeds=seeds,
                cross_validation_folds=0,
                fold_partition_seed=104729,
                seed_mode="optimizer_only",
            )
            for mode in modes
        )
    if not result:
        raise CampaignCliError(
            "At least one of [training.naive_fine_tuning] or "
            "[training.multihead_replay] must be enabled."
        )
    return tuple(result)


SEED_EXTENSION_SCHEMA = "mdstats.mlff-campaign-seed-extension.v1"
SEED_EXTENSION_ARCHIVE_SCHEMA = "mdstats.mlff-campaign-seed-extension-archive.v1"
































_PREPARATION_CONFIG_PROJECTION_FIELDS: dict[str, tuple[str, ...]] = {
    # These are the configuration authorities that can change DATA2-DATA8
    # scientific inputs, identities, or required preparation topology.  Keep
    # this list positive and explicit: a new downstream section must not become
    # an upstream invalidation merely because it was added to campaign.toml.
    "campaign": ("profile", "precision_profile"),
    "foundation": ("family", "head", "legacy_normalized"),
    "paths": (
        "training_root",
        "foundation_model",
        "replay_set",
        "replay_train",
        "replay_monitor",
        "replay_true_labels",
    ),
    "data": ("dataset_id", "manifest", "discovery_pattern"),
    "manifest_inference": (
        "fixed_cell_relative_tolerance",
        "reference_cell_relative_tolerance",
        "strain_matrix_absolute_tolerance",
        "strain_volume_ratio_tolerance",
        "maximum_rotation_radians",
        "conventional_axis_orthogonality_tolerance",
        "temperature_equality_tolerance_kelvin",
        "filename_values_at_or_above_one_are_percent",
    ),
    "profile": (
        "profile_id",
        "framework_atomic_numbers",
        "mobile_atomic_numbers",
        "all_atomic_numbers",
    ),
    "partition": (
        "minimum_block_frames",
        "purge_units_between_roles",
    ),
    "random": (
        "feature_projection_seed",
        "online_monitor_seed",
    ),
    # DATA6 values depend on the resolved foundation device/dtype.  Sweep
    # batching, capacity calibration, journals, and shard layout are execution
    # realizations: their compatibility belongs to the sweep/materialization
    # records that own them, never to preparation scientific identity.
    "model": ("device", "dtype"),
    # ``backend`` controls the source foundation inference used to create DATA6
    # evidence.  The remaining acceleration settings are either TRAIN2-only
    # (``training_backend``) or execution availability/conversion controls
    # (``only_cueq`` and ``require_available``); they cannot change the
    # authoritative DATA2-DATA8 scientific products after the source backend
    # has been resolved.  Their compatibility is owned by the runtime
    # realization that consumes them, not by completed-prepare reuse.
    "acceleration": ("backend",),
    "selection": ("sizes",),
    "objective": ("energy_weight", "forces_weight", "stress_weight"),
    "acceptance": ("maximum_replay_degradation_fraction",),
    "runtime": ("mace_version",),
    # Replay source qualification and split/materialization policy affect
    # DATA8 inputs.  Historical split-file aliases are intentionally included.
    "replay": (
        "mode",
        "label_mode",
        "seed",
        "split_ratio",
        "split_seed",
        "maximum_force_ev_per_angstrom",
        "force_component_rms_ev_per_angstrom",
        "maximum_abs_stress_ev_per_angstrom3",
        "require_stress",
        "prediction_batch_size",
        "prediction_shard_size",
        "minimum_train_configurations",
        "minimum_monitor_configurations",
        "require_target_elements",
        "allow_small_corpus",
        "allow_unspecified_label_provenance",
    ),
}

_PREPARATION_TRAINING_FIELDS = (
    # Policy generation, method topology, and fixed monitor inputs affect the
    # required DATA8 population/materialization.  LR, horizon, checkpoint, and
    # stopping authorities are deliberately downstream TRAIN2 identities.
    "policy_generation",
    "modes",
    "seeds",
    "online_target_monitor_configurations",
    "online_replay_monitor_configurations",
    "training_diagnostic_monitor_configurations",
)

_PREPARATION_TRAINING_METHOD_FIELDS = (
    "enabled",
    "seeds",
)

def _json_copy(value: Any) -> Any:
    """Copy one TOML value into the deterministic digest representation."""

    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _preparation_config_projection(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Return the positive configuration projection owned by preparation.

    This function is intentionally the sole preparation-config ownership
    authority.  It selects known preparation inputs instead of hashing the
    campaign wholesale and trying to remember every downstream field to omit.
    """

    projection: dict[str, Any] = {}
    for section, fields in _PREPARATION_CONFIG_PROJECTION_FIELDS.items():
        table = cfg.get(section)
        if not isinstance(table, Mapping):
            continue
        values = {
            key: _json_copy(table[key])
            for key in fields
            if key in table
        }
        if values:
            projection[section] = values

    # Historical campaigns may carry device/dtype only under [training].
    # Preparation resolves those values as DATA6 foundation-inference inputs
    # when [model] does not override them, so preserve the resolved identity
    # without making a training-only edit to an explicit [model] value an
    # upstream invalidation.
    model = cfg.get("model")
    if not isinstance(model, Mapping) or "device" not in model:
        projection.setdefault("model", {})["device"] = _json_copy(
            _cfg(cfg, "training", "device", "cuda")
        )
    if not isinstance(model, Mapping) or "dtype" not in model:
        projection.setdefault("model", {})["dtype"] = _json_copy(
            _cfg(cfg, "training", "dtype", "float32")
        )

    training = cfg.get("training")
    if isinstance(training, Mapping):
        values = {
            key: _json_copy(training[key])
            for key in _PREPARATION_TRAINING_FIELDS
            if key in training
        }
        for method_name in ("naive_fine_tuning", "multihead_replay"):
            method = training.get(method_name)
            if not isinstance(method, Mapping):
                continue
            method_values = {
                key: _json_copy(method[key])
                for key in _PREPARATION_TRAINING_METHOD_FIELDS
                if key in method
            }
            if method_values:
                values[method_name] = method_values
        if values:
            projection["training"] = values
    return projection


def _preparation_config_digest(cfg: Mapping[str, Any]) -> str:
    """Fingerprint the explicit preparation-owned configuration projection.

    A fidelity tuple and target-size ranking tolerances govern downstream
    screening; they do not change the lower-level preparation inputs.  Keep the
    full TOML hash as provenance, but use this dependency-scoped identity for
    preparation reuse.
    """

    return digest({
        "schema": "mdstats.mlff-prepare-semantic-config.v2",
        "config": _preparation_config_projection(cfg),
    })


def command_prepare(args: argparse.Namespace) -> int:
    """Prepare the current target-size scientific substrate.

    This reaches the accepted P1/P2 owners and the one common preparation, and it
    cannot select a target size.  Resolving the training-policy generation first
    is the reject-only obsolete-generation gate: a retired pre-V7 configuration is
    refused here, before any campaign record is opened, so retired derived
    target-size state is never deserialized or reinterpreted as current authority.
    """

    cfg, _paths = _load_config(args.config)
    _training_policy_generation(cfg)
    from .campaign_target_size_runtime import execute_current_prepare

    return execute_current_prepare(args)




_DATA8_VARIANT_RE = re.compile(
    r"^(naive_fine_tuning|multihead_replay)-n(?P<size>[0-9]+)-seed(?P<seed>-?[0-9]+)$"
)
















_DATA8_PREDECESSOR_AUTHORITY_BRIDGE_SCHEMA = (
    "mdstats.target-size-data8-authority-bridge.fixed-predecessor.v1"
)










def _terminate_process(process: subprocess.Popen[Any], *, grace_seconds: float) -> None:
    """Terminate a subprocess and its descendants without leaving GPU workers."""
    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - Windows fallback
        process.terminate()
    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - Windows fallback
        process.kill()
    process.wait()






































































































def command_select_target_size(args: argparse.Namespace) -> int:
    """Run or resume the complete current configurable-fidelity target-size screen.

    This is the sole current screening entrypoint. It reaches the accepted
    P1/P2/P3 owners directly; no retired selector, role-domain, coverage,
    complement, or pre-target CV authority participates.
    """

    cfg, _paths = _load_config(args.config)
    if _training_policy_generation(cfg) != "train2":
        raise CampaignCliError(
            "`select-target-size` is available only for TRAIN2 campaigns. Historical "
            "campaigns retain their existing train/evaluate lifecycle."
        )
    from .campaign_target_size_runtime import execute_current_select_target_size

    return execute_current_select_target_size(
        args,
        trainer=getattr(args, "_external_boundary_trainer", None),
        inference_evaluator=getattr(args, "_external_inference_evaluator", None),
    )


def command_cross_validate(args: argparse.Namespace) -> int:
    """Run or resume the current post-selection cross-validation.

    The command exists only for TRAIN2 campaigns; historical campaigns keep
    their original train/evaluate lifecycle and never gain a post-selection CV
    owner retroactively.
    """

    cfg, _paths = _load_config(args.config)
    if _training_policy_generation(cfg) != "train2":
        raise CampaignCliError(
            "`cross-validate` is available only for TRAIN2 campaigns. Historical "
            "campaigns retain their existing train/evaluate lifecycle."
        )
    from .campaign_post_selection_runtime import execute_current_cross_validate

    return execute_current_cross_validate(args)


def command_train_production(args: argparse.Namespace) -> int:
    """Train the fresh final production run(s) on the full selected dataset."""

    cfg, _paths = _load_config(args.config)
    if _training_policy_generation(cfg) != "train2":
        raise CampaignCliError(
            "`train-production` is available only for TRAIN2 campaigns. Historical "
            "campaigns retain their existing train/evaluate lifecycle."
        )
    from .campaign_post_selection_runtime import execute_current_train_production

    return execute_current_train_production(args)


def _require_train2_qualification(cfg: Mapping[str, Any]) -> None:
    if _training_policy_generation(cfg) != "train2":
        raise CampaignCliError(
            "`qualification` is available only for TRAIN2 campaigns. Historical "
            "campaigns retain their existing train/evaluate lifecycle."
        )


def command_qualification_run(args: argparse.Namespace) -> int:
    """Run or resume nonlocked post-production qualification."""

    cfg, _paths = _load_config(args.config)
    _require_train2_qualification(cfg)
    from .qualification import execute_qualification_run

    return execute_qualification_run(args)


def command_qualification_status(args: argparse.Namespace) -> int:
    """Report post-production qualification state without mutating anything."""

    cfg, _paths = _load_config(args.config)
    _require_train2_qualification(cfg)
    from .qualification import execute_qualification_status

    return execute_qualification_status(args)


def command_qualification_activate_locked(args: argparse.Namespace) -> int:
    """Explicitly open the one-shot locked interpolation test."""

    cfg, _paths = _load_config(args.config)
    _require_train2_qualification(cfg)
    from .qualification import execute_qualification_activate_locked

    return execute_qualification_activate_locked(args)














































































































_VERIFICATION_WORKER_LOCAL = threading.local()

















def _atomic_copy_file(source: Path, destination: Path) -> None:
    """Publish one verified immutable model by same-directory atomic replace."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source, temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


































































def _storage_command_context(
    config: Path, *, consequential: bool
) -> tuple[Any, Any, "CampaignStore", Any]:
    """Resolve the one owner/boundary context every storage command shares.

    ``consequential`` decides whether this invocation may create anything. An
    observational command resolves paths without materializing them and opens
    the state database read-only; only an explicitly authorized apply is allowed
    to bring campaign state into existence.
    """

    cfg, paths = _load_config(config, ensure=consequential)
    boundary = _campaign_ownership_boundary(cfg, paths)
    state_authorized, state_detail = boundary.destructive_authorization(paths.state_db)
    if not state_authorized:
        raise CampaignCliError(
            "Refusing the storage operation because campaign state is outside the "
            f"campaign ownership boundary: {state_detail}: {paths.state_db}"
        )
    store = CampaignStore(paths.state_db, create=consequential)
    # Rebuild the boundary with the store so the P3 publication-window fence and
    # the P7 durable-evidence fence both reduce deletion authority.
    boundary = _campaign_ownership_boundary(cfg, paths, store)
    return cfg, paths, store, boundary


def _storage_dispatch(args: argparse.Namespace, handler: str, printer: str) -> int:
    from .storage import commands as storage_commands
    from .storage.admission import StorageAdmissionError
    from .storage.archive import StorageArchiveError
    from .storage.control_plane import StorageControlPlaneError
    from .storage.commands import StorageDisabledError
    from .storage.dedup import StorageDedupError
    from .storage.executor import StorageAuthorizationError
    from .storage.inventory import OwnerGraphError
    from .storage.lease import StorageLeaseUnavailableError
    from .storage.plan import StoragePlanStaleError
    from .storage.policy import StoragePolicyError

    consequential = storage_commands.invocation_apply(args)
    if not consequential:
        with observational_campaign_state():
            return _storage_dispatch_locked(args, handler, printer)
    return _storage_dispatch_locked(args, handler, printer)


def _storage_dispatch_locked(
    args: argparse.Namespace, handler: str, printer: str
) -> int:
    from .storage import commands as storage_commands
    from .storage.admission import StorageAdmissionError
    from .storage.archive import StorageArchiveError
    from .storage.control_plane import StorageControlPlaneError
    from .storage.commands import StorageDisabledError
    from .storage.dedup import StorageDedupError
    from .storage.executor import StorageAuthorizationError
    from .storage.inventory import OwnerGraphError
    from .storage.lease import StorageLeaseUnavailableError
    from .storage.plan import StoragePlanStaleError
    from .storage.policy import StoragePolicyError

    consequential = storage_commands.invocation_apply(args)
    cfg, paths, store, boundary = _storage_command_context(
        args.config, consequential=consequential
    )
    try:
        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        try:
            payload = getattr(storage_commands, handler)(context, args)
        except (
            StorageAdmissionError,
            StorageArchiveError,
            StorageControlPlaneError,
            StorageDedupError,
            StorageDisabledError,
            StorageAuthorizationError,
            StorageLeaseUnavailableError,
            StoragePlanStaleError,
            StoragePolicyError,
            OwnerGraphError,
        ) as exc:
            raise CampaignCliError(str(exc)) from exc
        getattr(storage_commands, printer)(payload)
        print(
            "  storage operations never grant scientific authority and never change "
            "a scientific decision",
            flush=True,
        )
        return 0
    finally:
        store.close()


def command_storage(args: argparse.Namespace) -> int:
    """Read-only owner-driven storage report, or an explicit deep audit."""

    return _storage_dispatch(args, "storage_report", "print_storage_report")


def _reject_conflicting_authorization(args: argparse.Namespace) -> None:
    """`--dry-run` and `--apply` are opposite answers to the same question."""

    if bool(getattr(args, "apply", False)) and bool(getattr(args, "dry_run", False)):
        raise CampaignCliError("Choose either --dry-run or --apply, not both.")


def command_cleanup(args: argparse.Namespace) -> int:
    """Plan and, when authorized, apply owner-driven safe/cache cleanup."""

    _reject_conflicting_authorization(args)
    return _storage_dispatch(args, "storage_cleanup", "print_cleanup")


def command_storage_archive(args: argparse.Namespace) -> int:
    """Create, list, verify, restore, or resume a cold archive representation."""

    _reject_conflicting_authorization(args)
    return _storage_dispatch(args, "storage_archive", "print_archive")


def command_storage_deduplicate(args: argparse.Namespace) -> int:
    """Plan and, when authorized, apply owner-certified immutable dedup."""

    _reject_conflicting_authorization(args)
    return _storage_dispatch(args, "storage_deduplicate", "print_dedup")


@dataclass(frozen=True)
class _PublicLifecycleStep:
    semantic_id: str
    command: str
    label: str
    description: str
    state: StageState
    message: str
    terminal: bool = False


def _current_public_lifecycle(
    cfg: Mapping[str, Any], paths: CampaignPaths, store: CampaignStore
) -> tuple[_PublicLifecycleStep, ...]:
    """Project the current target-size/post-selection authorities into the CLI lifecycle.

    Every state shown here is read from the owning current authority - the
    campaign-store target-size revision for the substrate and the screen, and the
    post-selection owners for cross-validation and fresh final production.  No
    retired selector, role-domain, coverage, materialization, or study record
    participates, and no stage marker is trusted in place of the authority it
    claims to describe.
    """

    from .campaign_post_selection import load_current_selected_training_context
    from .campaign_post_selection_runtime import (
        build_post_selection_context,
        resolve_current_cv_acceptance,
        resolve_current_cv_plan,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )
    from .campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
        load_target_size_campaign_revision,
    )

    steps: list[_PublicLifecycleStep] = []
    doctor_state, doctor_message = _effective_stage(store, paths, "doctor")
    steps.append(_PublicLifecycleStep(
        "doctor", "doctor", "doctor", "environment and input checks",
        doctor_state, doctor_message,
    ))

    revision = load_target_size_campaign_revision(store)
    state = None if revision is None else revision.state
    if state is None or state.regime is TargetSizeRegime.LEGACY:
        prepare_state = StageState.NOT_STARTED
        prepare_message = (
            "the current target-size substrate has not been bound; `prepare` performs "
            "the one-time destructive cutover"
        )
    elif state.regime is TargetSizeRegime.TRANSITIONING:
        prepare_state = StageState.WAITING
        prepare_message = (
            f"a destructive cutover for canonical generation {state.generation} is "
            "interrupted; rerun `prepare` to resume it"
        )
    else:
        prepare_state = StageState.COMPLETE
        prepare_message = (
            f"current substrate bound at canonical generation {state.generation}; "
            f"experiment={_short_digest(state.experiment_definition_digest)}"
        )
    steps.append(_PublicLifecycleStep(
        "current_prepare", "prepare", "prepare",
        "current target-size scientific substrate; selects nothing",
        prepare_state, prepare_message,
    ))

    terminal = None if state is None else state.terminal
    screen_terminal = False
    if prepare_state is not StageState.COMPLETE:
        screen_state = StageState.NOT_STARTED
        screen_message = "the current substrate must be bound first"
    elif state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED and terminal is not None:
        screen_state = StageState.COMPLETE
        screen_message = (
            f"selected target size frozen at N={terminal.selected_target_size}; "
            f"T_selected={_short_digest(terminal.selected_membership_digest)}"
        )
    elif state.lifecycle is TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE:
        screen_state = StageState.COMPLETE
        screen_terminal = True
        reasons = ", ".join(terminal.terminal_reason_codes) if terminal is not None else ""
        screen_message = (
            "the paired-seed screen reached a typed scientific terminal outcome"
            + (f": {reasons}" if reasons else "")
        )
    elif state.lifecycle is TargetSizeLifecycle.SCREEN_ACTIVE:
        screen_state = StageState.RUNNING
        screen_message = (
            f"screen attempt {state.attempt} is open at canonical generation "
            f"{state.generation}"
        )
    else:
        screen_state = StageState.NOT_STARTED
        screen_message = "no candidate has been screened for this generation"
    steps.append(_PublicLifecycleStep(
        "target_size_selection", "select-target-size", "select-target-size",
        "paired optimizer-seed target-size screen; the only command that decides N",
        screen_state, screen_message, terminal=screen_terminal,
    ))

    selected_frozen = screen_state is StageState.COMPLETE and not screen_terminal
    context = None
    if selected_frozen:
        try:
            load_current_selected_training_context(cfg, paths, store)
            context = build_post_selection_context(cfg, paths, store, trainer=None)
        except Exception as exc:  # noqa: BLE001 - reported, never silently ignored
            selected_frozen = False
            post_selection_blocker = str(exc)
        else:
            post_selection_blocker = None
    else:
        post_selection_blocker = None

    if not selected_frozen:
        cv_state = StageState.NOT_STARTED
        cv_message = (
            post_selection_blocker
            if post_selection_blocker is not None
            else "no target size is frozen yet"
        )
        acceptance = None
    else:
        try:
            plan = resolve_current_cv_plan(context)
            acceptance = resolve_current_cv_acceptance(context)
        except Exception as exc:  # noqa: BLE001
            cv_state, cv_message, acceptance = StageState.WAITING, str(exc), None
        else:
            if acceptance is not None and acceptance.accepted:
                cv_state = StageState.COMPLETE
                cv_message = (
                    "the frozen method passed every required fold of every required "
                    f"CV seed (K={plan.fold_count})"
                )
            elif acceptance is not None:
                cv_state = StageState.FAILED
                cv_message = "cross-validation rejected the frozen training method"
            else:
                cv_state = StageState.NOT_STARTED
                cv_message = (
                    "the exact selected dataset has not been cross-validated"
                    if plan is None
                    else f"CV plan is current (K={plan.fold_count}); no acceptance exists yet"
                )
    steps.append(_PublicLifecycleStep(
        "post_selection_cv", "cross-validate", "cross-validate",
        "post-selection cross-validation of the frozen method on exactly T_selected",
        cv_state, cv_message,
    ))

    if cv_state is not StageState.COMPLETE:
        production_state = StageState.NOT_STARTED
        production_message = "the frozen method is not cross-validation accepted"
    else:
        try:
            final_plan = resolve_current_final_production_plan(context)
            final_completion = resolve_current_final_production_completion(context)
        except Exception as exc:  # noqa: BLE001
            production_state, production_message = StageState.WAITING, str(exc)
        else:
            if final_plan is None:
                production_state = StageState.NOT_STARTED
                production_message = "no fresh final production run has been published"
            elif final_completion is None:
                production_state = StageState.WAITING
                production_message = (
                    "fresh final production plan is published on the full exact "
                    f"T_selected ({_short_digest(final_plan.content_digest)}); "
                    "required final production run(s) are incomplete"
                )
            else:
                production_state = StageState.COMPLETE
                production_message = (
                    "fresh production is published on the full exact T_selected under "
                    f"the accepted method ({_short_digest(final_plan.content_digest)})"
                )
    steps.append(_PublicLifecycleStep(
        "final_production", "train-production", "train-production",
        "fresh final production on the complete selected dataset",
        production_state, production_message,
    ))
    return tuple(steps)


def _short_digest(value: Any) -> str:
    text = "" if value is None else str(value)
    return f"{text[:12]}..." if text else "unbound"


def _next_public_operation(
    cfg: Mapping[str, Any], paths: CampaignPaths, store: CampaignStore
) -> str | None:
    lifecycle = _current_public_lifecycle(cfg, paths, store)
    if any(step.terminal for step in lifecycle):
        return None
    for step in lifecycle:
        if step.state is not StageState.COMPLETE:
            return step.command
    return None


def command_status(args: argparse.Namespace) -> int:
    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _print_header(f"Campaign status: {_cfg(cfg, 'campaign', 'id', 'mlff-campaign')}")
    lifecycle = _current_public_lifecycle(cfg, paths, store)
    for step in lifecycle:
        symbol = (
            "STOP" if step.terminal else {
                StageState.COMPLETE: "PASS",
                StageState.FAILED: "FAIL",
                StageState.WAITING: "WAIT",
                StageState.RUNNING: "RUN ",
                StageState.NOT_STARTED: "----",
            }[step.state]
        )
        print(f"[{symbol}] {step.label:<24} {step.description}")
        print(f"       {step.message}")
    next_command = _next_public_operation(cfg, paths, store)
    print(f"\nWorkspace: {paths.workspace}")
    print(f"State DB:  {paths.state_db}")
    print(f"Results:   {paths.results}")
    terminal_step = next((step for step in lifecycle if step.terminal), None)
    if next_command:
        print(f"\nNext command: python tools/mdstats-mlff-campaign.py --config {paths.config} {next_command}")
    elif terminal_step is not None:
        print("\nThe target-size screen stopped scientifically; no production next command exists.")
    else:
        print("\nAll bounded campaign stages are complete.")
    return 0


def command_advance(args: argparse.Namespace) -> int:
    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    lifecycle = _current_public_lifecycle(cfg, paths, store)
    name = _next_public_operation(cfg, paths, store)
    if name is None:
        terminal_step = next((step for step in lifecycle if step.terminal), None)
        if terminal_step is not None:
            print(
                "Campaign has no next production command: "
                f"{terminal_step.message}.",
                flush=True,
            )
            return 0
        print("Campaign is already complete.")
        return 0
    if name == "doctor":
        return command_doctor(args)
    if name == "prepare":
        return command_prepare(argparse.Namespace(config=args.config, approve_manifest=False, continue_after_approval=False, refresh_inferences=False, rebuild_catalog=False, max_new_frames=None))
    if name == "select-target-size":
        select_args = argparse.Namespace(config=args.config)
        # This private, in-process attribute is deliberately propagated only
        # through public lifecycle routing.  It lets the bounded integration
        # harness retain the real ``advance -> select-target-size`` ownership
        # while replacing only the external numerical MACE child.  It is not a
        # parser option, configuration field, or persisted campaign property.
        for attribute in (
            "_external_child_wrapper",
            "_external_boundary_trainer",
            "_external_inference_evaluator",
        ):
            if hasattr(args, attribute):
                setattr(select_args, attribute, getattr(args, attribute))
        return command_select_target_size(select_args)
    if name in {"cross-validate", "train-production"}:
        forwarded = argparse.Namespace(config=args.config)
        for attribute in (
            "_external_post_selection_trainer",
            "_external_inference_evaluator",
        ):
            if hasattr(args, attribute):
                setattr(forwarded, attribute, getattr(args, attribute))
        if name == "cross-validate":
            return command_cross_validate(forwarded)
        return command_train_production(forwarded)
    raise CampaignCliError(f"Unsupported derived next operation: {name}")




def command_guide(args: argparse.Namespace) -> int:
    print(GUIDE_TEXT)
    return 0




def _optional_float(value: Any) -> float | None:
    return None if value in (None, "", "none", "None") else float(value)


def _optional_positive_float(value: Any) -> float | None:
    parsed = _optional_float(value)
    return None if parsed is None or parsed <= 0.0 else parsed


def _config_template(
    *,
    workspace: str,
    training_root: str,
    foundation_model: str,
    replay_set: str | None = None,
    replay_train: str | None = None,
    replay_monitor: str | None = None,
    replay_true_labels: str | None = None,
    foundation_family: str = "mace_mh_1",
    foundation_head: str | None = None,
    foundation_label: str | None = None,
    acceleration_backend: str = "e3nn",
    training_acceleration_backend: str = "cueq",
    default_device: str = "cpu",
    precision_profile: str = "single",
) -> str:
    precision = _precision_template(precision_profile)
    family = str(foundation_family).strip().lower()
    if family not in {"mace_mh_1", "mace_mpa_0"}:
        raise CampaignCliError(
            "_config_template foundation_family must be mace_mh_1 or mace_mpa_0 for a generated campaign."
        )
    resolved_head = str(foundation_head or ("omat_pbe" if family == "mace_mh_1" else "default")).strip()
    if not resolved_head:
        raise CampaignCliError("Generated campaign foundation head must be non-empty.")
    label = str(foundation_label or ("MACE-MH-1" if family == "mace_mh_1" else "MPA-0-medium")).strip()
    campaign_id = (
        "lta-mh1-omat-pbe-finetune"
        if family == "mace_mh_1" and resolved_head == "omat_pbe"
        else "lta-mpa0-finetune"
        if family == "mace_mpa_0" and resolved_head == "default"
        else f"lta-{family.removeprefix('mace_').replace('_', '')}-{resolved_head.replace('_', '-')}-finetune"
    )
    if replay_set not in (None, ""):
        if any(value not in (None, "") for value in (replay_train, replay_monitor, replay_true_labels)):
            raise CampaignCliError("_config_template cannot mix replay_set with legacy split replay paths.")
        replay_paths_block = (
            '# Single selected replay corpus, e.g. replay_fps_12000.extxyz produced by the\n'
            '# replay_select_*.sh random+FPS workflow. mdstats owns qualification, the\n'
            '# deterministic train/monitor split, pseudo-label generation, true-label views,\n'
            '# and all reconstructable internal transport files.\n'
            f'replay_set = "{replay_set}"'
        )
        replay_contract_block = (
            '# REPLAY-UNIFY1: one external replay source. Foundation pseudo labels and source\n'
            '# true labels are separate internal namespaces over the same frozen split.\n'
            'label_mode = "foundation_pseudolabel"\n'
            'split_ratio = "5:1"\n'
            'split_seed = 42\n'
            '# Foundation-pseudolabel qualification defaults inherited from the standalone\n'
            '# replay preparation workflow. Threshold-only edits reuse cached predictions.\n'
            'maximum_force_ev_per_angstrom = 20.0\n'
            'force_component_rms_ev_per_angstrom = 5.0\n'
            'maximum_abs_stress_ev_per_angstrom3 = 0.5\n'
            'require_stress = false\n'
            'prediction_batch_size = 32\n'
            'prediction_shard_size = 256'
        )
    else:
        # Internal compatibility factory used by historical tests/migrations.
        # New user-facing `init` never selects this branch.
        replay_train = replay_train or "/path/to/replay_train.extxyz"
        replay_monitor = replay_monitor or "/path/to/replay_monitor.extxyz"
        replay_true_labels = replay_true_labels or "/path/to/LTA_replay_true_labels"
        replay_paths_block = (
            f'replay_train = "{replay_train}"\n'
            f'replay_monitor = "{replay_monitor}"\n'
            '# Independent true labels for replay retention and downstream analysis.\n'
            f'replay_true_labels = "{replay_true_labels}"'
        )
        replay_contract_block = (
            '# Split-file replay interface retained for existing campaign inputs.\n'
            'mode = "external_pseudolabel"\n'
            'seed = 42'
        )
    return f'''schema = "{CAMPAIGN_CLI_SCHEMA}"

[campaign]
id = "{campaign_id}"
profile = "lta"
precision_profile = "{precision['profile']}"
workspace = "{workspace}"

[foundation]
# Canonical scientific source potential. The checkpoint itself is inspected in
# later gates; filename/model labels are never authoritative for family or head.
family = "{family}"
head = "{resolved_head}"
label = "{label}"

[paths]
training_root = "{training_root}"
foundation_model = "{foundation_model}"
{replay_paths_block}

[data]
dataset_id = "lta-dry-alkali-v1"
manifest = "{DEFAULT_MANIFEST_NAME}"
discovery_pattern = "**/*.xml"

[manifest_inference]
# Filename strain hints are candidates only. They are promoted after fixed-cell
# XML controls and the exact LTA cell deformation pass these tolerances.
fixed_cell_relative_tolerance = 1.0e-7
reference_cell_relative_tolerance = 1.0e-7
strain_matrix_absolute_tolerance = 5.0e-5
strain_volume_ratio_tolerance = 5.0e-5
maximum_rotation_radians = 1.0e-4
conventional_axis_orthogonality_tolerance = 5.0e-6
temperature_equality_tolerance_kelvin = 1.0e-6
# hydro+5 / ortho-2 / shear+2 mean +5%, -2%, and +2%; decimal
# forms such as hydro+0.05 retain their fractional interpretation.
filename_values_at_or_above_one_are_percent = true

[profile]
profile_id = "dry-lta-alkali"
framework_atomic_numbers = [8, 13, 14]
mobile_atomic_numbers = [3, 11, 19]
all_atomic_numbers = [3, 8, 11, 13, 14, 19]

[partition]
minimum_block_frames = 32
purge_units_between_roles = 1

[random]
# Randomized PCA/range-finder seed used only when a DATA7 feature block is too
# large for exact SVD. Exact-SVD paths are deterministic and ignore this seed.
feature_projection_seed = 271828
# ADAPT-MON1 deterministic random-start for balanced systematic online monitors.
online_monitor_seed = 161803

[model]
# Compatibility/display label only. Scientific foundation identity is carried by
# [foundation].family + [foundation].head and the inspected checkpoint identity.
foundation_name = "{label}"
device = "{default_device}"
dtype = "{precision['model_dtype']}"
# Completed frames append one recovery record immediately. This value controls
# durable journal flushes, not full-history JSON rewrites. Use 1 for maximum
# durability or a larger value for lower filesystem synchronization overhead.
checkpoint_interval = 128
# Persist descriptors/predictions in immutable multi-frame shards. Larger values
# reduce inode and open/stat pressure; an abrupt interruption may recompute at
# most one incomplete shard.
artifact_shard_size = 128
# Set a small positive value for a bounded first pass; 0 means finish the sweep.
max_new_frames = 0
# 0 chooses a VRAM-bounded automatic batch. CUDA OOM halves the batch and retries.
inference_batch_size = 0
maximum_inference_batch_size = 16
estimated_inference_memory_mib_per_frame = 512.0
# VRAM1 execution policy. Calibration uses the actual combined DATA6 workload,
# stress-oriented frames, a fractional occupancy ceiling, and an absolute reserve.
batch_calibration_stress_structures = 8
vram_max_device_fraction = 0.80
vram_reserve_gib = 4.0
batch_throughput_tolerance_fraction = 0.05
# PERF-P4 overlaps bounded artifact persistence with the next inference batch.
# Queue depth is intentionally small so host-memory pressure remains explicit.
pipeline_enabled = true
persistence_queue_depth = 1

[acceleration]
# Source inference and DATA6 use the selected source backend. Production
# training may use its explicitly configured backend while preserving portable
# checkpoint identity.
backend = "{acceleration_backend}"
# TRAIN2 backend: cueq is the generated default; set e3nn for a reference run.
training_backend = "{training_acceleration_backend}"
# Keep false so trained checkpoints remain portable e3nn artifacts.
only_cueq = false
# Fail instead of silently falling back if either requested backend is unavailable.
require_available = true

[selection]
# Optional non-target learning-curve labels. Target-size candidates are
# configured below by the explicit power range.
sizes = [512]
# 0 auto-selects an economical outer thread count (up to 90% of available
# CPUs, capped where these vectorized per-frame kernels stop scaling).
structural_workers = 0

[target_data.size_convergence]
# Candidate target sizes are powers from target_size_power_min through
# target_size_power_max. The configured range is the scientific ladder; it is
# not a hidden fixed-size universe.
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
coarse_practical_equivalence_mev_per_a = 1.0
practical_equivalence_mev_per_a = 1.0
# The ordered screen seed list comes only from the sole enabled training method.

[objective]
energy_weight = 1.0
forces_weight = 10.0
stress_weight = 1.0

[training]
# TRAIN2A policy generation. Absence of this key in a historical campaign means
# the immutable AdaptiveTrainingStopPolicy lifecycle that created that campaign;
# it is never silently migrated. New campaigns use orthogonal TRAIN2/EVAL2
# budget/LR/admissibility/selection authorities.
policy_generation = "train2"
# New campaigns default to multi-head replay fine-tuning only. Historical
# modes/seeds configurations remain readable for restart compatibility; use the
# explicit per-method tables below for new campaigns.
device = "{default_device}"
dtype = "{precision['training_dtype']}"
learning_rate = 1.0e-4
batch_size = 2
valid_batch_size = 2
# 0 chooses a CPU/RAM-bounded DataLoader worker count.
num_workers = 0
estimated_loader_memory_mib_per_worker = 256.0
max_num_epochs = 30
eval_interval = 1
# ADAPT-MON1 fixed common online monitors. These are model-selection evidence only
# and never supply gradients. Target frames are condition/trajectory/time balanced;
# replay frames are selected from independent true-label replay evidence.
online_target_monitor_configurations = 256
online_replay_monitor_configurations = 512
training_diagnostic_monitor_configurations = 256
# TRAIN2B executes this frozen schedule once per optimizer update. Validation
# never mutates the LR authority. The exact default is
# 5% warm-up, 75% target adaptation, and 20% low-LR refinement.
train2_warmup_end_fraction = 0.05
train2_adaptation_end_fraction = 0.80
train2_initial_lr_multiplier = 0.10
train2_refinement_start_lr_multiplier = 0.10
train2_final_lr_multiplier = 0.01
target_head_weight = 5.0
replay_head_weight = 1.0

# ADAPT-PREC1: model precision is binary and controls learned-model arithmetic only.
# mdstats-owned scientific reductions/statistics and persistent MD bookkeeping remain FP64.
# There is intentionally no [training.precision] staged/refine schedule.

[training.naive_fine_tuning]
# Naive/native single-head fine-tuning is retained as an explicit comparison or
# ablation option, but is disabled in newly initialized campaigns. Enable it
# deliberately if a target-only baseline is scientifically useful.
enabled = false
seeds = [1, 2]

[training.multihead_replay]
# Production default: two optimizer seeds for target-size screening.
# The post-selection fold plan is configured under [post_selection.cv].
enabled = true
seeds = [1, 2]

[post_selection.cv]
# Post-selection cross-validation of the frozen training method, run by
# the cross-validate command after the select-target-size command has frozen N
# and T_selected. Its universe is exactly T_selected.
# K >= 2 is required: there is no current zero-fold production bypass.
fold_count = 5
partition_seed = 104729
# Required CV seeds/variants. Every fold of every seed must pass.
seeds = [0]
# The cross-validation training budget. It is deliberately its own value:
# [training].max_num_epochs is the production horizon, and editing that must not
# invalidate accepted cross-validation evidence.
max_num_epochs = 30
# One split-exclusion component per fold is reserved as that fold's own
# checkpoint monitor; the held-out outer fold never controls checkpoint choice.
checkpoint_monitor_components_per_fold = 1
purge_components_between_roles = 0
# The target-only outer-fold acceptance predicate. Replay evidence gates
# admissibility but contributes no acceptance or ranking credit.
acceptance_metric = "target_force_rmse_ev_per_angstrom"
acceptance_maximum = 0.030

[post_selection.production]
# Fresh final training on the full exact T_selected, run by `train-production`
# after cross-validation accepts the method. Its epoch horizon is
# [training].max_num_epochs and is independent of target-size screening n3.
seeds = [1]
committee_policy = "all_qualified_final_seeds"

[qualification]
# V7-native post-production qualification of the exact frozen final-production
# publication. Every threshold below is frozen before any product outcome is
# observed; downstream evidence rejects or blocks the exact published product
# and never selects a different target size, seed, checkpoint, or member.
required_components = ["deployment_parity", "physical_pes", "relaxation", "dynamics", "calibration"]
optional_components = []

[qualification.reference]
# External first-principles reference evidence for the frozen physical plan.
# `qualification run` publishes an exact request bundle here; a missing bundle
# is reported as waiting_for_reference, never as a pass.
protocol = "external-reference-protocol-unset"

[qualification.deployment_parity]
probe_configurations = 4
energy_atol_ev_per_atom = 1.0e-4
force_atol_ev_per_angstrom = 1.0e-3
force_rtol = 1.0e-3
# The supported LAMMPS/ML-IAP runtime is required for a real deployment claim.
# When it is absent, qualification reports unavailable/blocking rather than pass.
require_deployed_runtime = true
# Stress applicability is NOT a switch. It is resolved before execution from the
# accepted training objective, the reference labels, the authenticated model,
# periodicity, and the runtime. Set stress_required to insist that an applicable
# channel is qualified; a declared-inapplicable reason is recorded for audit but
# cannot suppress a stress channel the product actually has. Tensor ordering and
# the pressure/stress sign belong to each source adapter and are not configurable.
stress_required = false
# stress_declared_inapplicable_reason = "why this product has no stress channel"
stress_atol_ev_per_angstrom3 = 1.0e-4
stress_rtol = 1.0e-3

[qualification.physical]
base_count = 4
displaced_atoms_per_base = 2
# Symmetric amplitudes are mandatory: every mode needs a matched +/- reference pair.
displacement_amplitudes_angstrom = [-0.05, -0.02, 0.02, 0.05]
strain_magnitudes = []
require_all_modes = true
require_restoring_sign = true
force_component_rmse_maximum_ev_per_angstrom = 0.20
energy_curvature_minimum_ev_per_angstrom2 = 0.0
stiffness_relative_tolerance = 0.50
resolution_floor_ev = 1.0e-6

[qualification.relaxation]
maximum_steps = 50
force_convergence_ev_per_angstrom = 0.05
rms_displacement_maximum_angstrom = 0.30
maximum_displacement_maximum_angstrom = 0.60
bond_rmse_maximum_angstrom = 0.10
bond_maximum_error_angstrom = 0.25
angle_rmse_maximum_degrees = 8.0
angle_maximum_error_degrees = 20.0
bond_cutoff_scale = 1.20
require_all_bases = true

[qualification.dynamics]
temperatures_kelvin = [300.0]
velocity_seeds = [20260831]
timestep_femtoseconds = 0.5
warmup_steps = 200
propagation_steps = 200
sample_interval_steps = 50
thermostat_damping_femtoseconds = 50.0
nvt_temperature_tolerance_kelvin = 150.0
nve_energy_drift_maximum_ev_per_atom_per_picosecond = 0.01
minimum_pair_distance_angstrom = 0.80
maximum_force_ev_per_angstrom = 100.0
base_count = 1
require_all_cases = true

[qualification.calibration]
# auto resolves to not_applicable for a single-model publication with no
# accepted uncertainty estimator; uncertainty is never invented from a point
# prediction.
method = "auto"
coverage_target = 0.68
coverage_tolerance = 0.15
minimum_frames = 2

[qualification.locked]
# The one-shot locked interpolation test. It is opened only by an explicit
# `qualification activate-locked --confirm` and never by `advance`.
enabled = true
force_component_rmse_maximum_ev_per_angstrom = 0.10
energy_rmse_maximum_ev_per_atom = 0.02
minimum_frames = 1

[runtime]
# DATA8 is source-locked to this MACE interface. Change only after requalification.
mace_version = "0.3.16"

[performance]
# Auto parallelism targets 90% of CPU threads and GPU/VRAM capacity. RAM remains
# capped at 80% so the OS and unrelated programs retain baseline headroom.
cpu_fraction = 0.90
ram_fraction = 0.80
gpu_memory_fraction = 0.90
# 0 selects the automatic resource-bounded count. Explicit positive values are
# remain caps inside the runtime CPU-fraction and RAM budgets.
source_workers = 0
feature_workers = 0
# LTA workers return compact NumPy columns; the automatic count is bounded by
# CPU threads plus RAM reserved for the final immutable catalog.
lta_workers = 0
# 0 disables the per-source hard timeout.
source_timeout_seconds = 0
# Heartbeat interval for source ingestion and other long preparation stages.
progress_interval_seconds = 30.0

[execution]
max_attempts = 2
minimum_free_disk_gib = 20.0
# 0 or omitted means no wall-clock timeout for a production run.
timeout_seconds = 0
terminate_grace_seconds = 30.0
# Heartbeat interval for external subprocesses.
progress_interval_seconds = 60.0
# Visible production-training updates. Cancellation is still polled silently
# every second so Ctrl-C and disk-reserve stops remain responsive.
training_progress_interval_seconds = 10.0
# 0 enables adaptive CUDA concurrency. CUDA always starts with one job.
# Additional jobs are admitted one at a time only after every active job has
# reached sustained optimizer/epoch work for the full averaging window. The
# projected mean aggregate VRAM and GPU utilization must both remain below
# their admission ceilings. Natural telemetry fluctuation is averaged rather
# than treated as a reason to wait indefinitely. A positive value is only a
# maximum cap; it does not bypass adaptive admission.
parallel_training_jobs = 0
minimum_parallel_training_jobs = 1
maximum_parallel_training_jobs = 4
training_gpu_memory_fraction = 0.90
training_gpu_utilization_fraction = 0.90
estimated_training_vram_mib_per_job = 6144.0
estimated_training_ram_mib_per_job = 8192.0
parallel_training_epoch_stabilization_seconds = 60.0
parallel_training_epoch_activity_timeout_seconds = 120.0
parallel_training_epoch_stability_samples = 12
# Legacy tolerance fields remain accepted for old campaign files but no longer
# gate scheduler promotion; the fixed-duration average above is authoritative.
parallel_training_stability_relative_tolerance = 0.10
parallel_training_utilization_stability_absolute_tolerance = 8.0
parallel_training_memory_growth_margin = 1.05
parallel_training_utilization_growth_margin = 1.05
parallel_training_monitor_interval_seconds = 10.0
# Staged evaluation uses a one-time single-job CUDA calibration. CUDA
# starts with exactly one job and samples GPU utilization plus incremental VRAM.
# OPT-EVAL4 evaluation calibrates only the accelerator stage (checkpoint/model
# materialization, serialized CuEq/OEq/FX conversion, and inference) because
# monitor/cache preparation now runs in separate CPU workers. Samples below the
# 1% activity floor are discarded independently for GPU utilization and VRAM.
# The highest 5% of retained samples
# are discarded as transient peaks, then the next-highest 10% are averaged
# independently for GPU utilization and incremental VRAM (approximately the
# 85th--95th percentile band). The resulting estimate is fixed for the remaining
# queue: live GPU-utilization spikes do not reduce concurrency. A hard live VRAM
# guard remains because exceeding the memory ceiling can cause OOM. mdstats then
# jumps directly to the largest projected concurrency below the 90% GPU/VRAM
# ceilings. CPU jobs retain a 20-second workload window and a
# projected 90% host-utilization ceiling. The 80% RAM bound above is always
# applied. Zero means automatic resource-bounded concurrency; a positive value is
# a hard maximum, and maximum_parallel_inference_jobs=0 adds no extra cap beyond
# CPU/RAM/VRAM/utility admission.
parallel_inference_jobs = 0
maximum_parallel_inference_jobs = 0
inference_cpu_utilization_fraction = 0.90
inference_gpu_memory_fraction = 0.90
inference_gpu_utilization_fraction = 0.90
inference_estimated_vram_mib_per_job = 4096.0
inference_estimated_ram_mib_per_job = 4096.0
parallel_inference_calibration_window_seconds = 120.0
inference_minimum_calibration_seconds = 20.0
inference_calibration_stability_relative_tolerance = 0.10
parallel_inference_cpu_calibration_window_seconds = 20.0
inference_gpu_minimum_activity_fraction = 0.01
inference_gpu_calibration_peak_trim_fraction = 0.05
inference_gpu_calibration_band_fraction = 0.10
# The exact shared 0.20.91a0 generated peak-trim value 0.10 migrates to
# the new 0.05 default; explicit phase-specific/custom values remain authoritative.
# Legacy 0.20.90a0 key inference_gpu_calibration_upper_tail_fraction remains
# accepted as an alias for inference_gpu_calibration_band_fraction.
parallel_inference_stability_samples = 3
inference_memory_growth_margin = 1.05
inference_utilization_growth_margin = 1.05
parallel_inference_monitor_interval_seconds = 2.0
# After CUDA calibration, the fixed per-job GPU-utilization estimate is authoritative.
# Only the hard live-VRAM safety guard still needs telemetry, so poll it less often
# instead of spawning/reading telemetry every scheduler tick. A concurrency change
# forces an immediate sample regardless of this interval.
parallel_inference_post_calibration_monitor_interval_seconds = 30.0
# Optional phase-specific overrides use the same suffixes, for example:
# parallel_evaluation_jobs or evaluation_estimated_vram_mib_per_job.
# OPT-EVAL4 evaluation additionally has bounded CPU preparation/finalization
# stages around accelerator inference. Zero means auto (currently up to two CPU
# stage workers); the prepared buffer is also bounded so parsed monitors and
# pending prediction arrays cannot grow without limit.
parallel_evaluation_prepare_jobs = 0
parallel_evaluation_finalize_jobs = 0
evaluation_pipeline_buffer_jobs = 0
evaluation_pipeline_buffer_mib = 0
# Zero uses the phase RAM estimate; shared model/cache residency is charged once.
evaluation_prepare_working_memory_mib = 0
evaluation_inference_working_memory_mib = 0
evaluation_finalize_working_memory_mib = 0
evaluation_shared_runtime_residency_mib = 0
# Stop admitting new jobs after the first failed run; already-active jobs finish.
stop_scheduling_after_failure = true

[cleanup]
# Storage is operator-driven: storage cleanup --tier safe|cache. It plans first and
# mutates only with --apply on the invocation you run; a persisted apply/action key
# under [storage] is rejected rather than obeyed. Setting enabled = false withholds
# every consequential storage mutation while leaving reporting and planning
# available. Optional [storage] policy keys tune codecs, bounds, and reserves only;
# they never widen deletion or archive authority.
enabled = true
# Publication window. Evidence younger than this is retained so storage can never
# race a reference that has not landed yet.
stale_age_hours = 6.0
# Bound on retained diagnostic campaign-store events; scientific records and the
# SHA-256 receipt cache have separate retention. Exceeding this bound authorizes
# pruning only: rewriting the state database is a separate, independently
# benefit-gated storage action.
maximum_event_records = 10000

[replay]
{replay_contract_block}
minimum_train_configurations = 100
minimum_monitor_configurations = 20
require_target_elements = true
allow_small_corpus = false
allow_unspecified_label_provenance = false

[acceptance]
# TRAIN2A target qualification boundary plus foundation-relative TRUE_DFT replay
# retention budget. Replay is a hard admissibility constraint only; extra replay
# margin earns zero checkpoint or seed ranking credit.
maximum_target_force_rmse_ev_per_angstrom = 0.030
allowed_replay_degradation_mev_per_a = 30.0
# Other safety thresholds remain independent hard/diagnostic gates.
maximum_energy_mae_ev_per_atom = 0.005
maximum_focus_force_rmse_ev_per_angstrom = 0.10
maximum_stress_rmse_ev_per_angstrom3 = 0.02
maximum_worst_condition_force_rmse_ev_per_angstrom = 0.15
[evaluation]
# TRAIN2A/EVAL2 selection authority is target-only after hard admissibility.
# No replay score weight or replay tie-break exists in the new schema.
primary_target_metric = "target_force_rmse_ev_per_angstrom"
refinement_reserved_candidates = 2
bootstrap_replicates = 2000
bootstrap_confidence = 0.95
bootstrap_min_independent_blocks = 10
device = "{default_device}"
dtype = "{precision['evaluation_dtype']}"
# TRAIN2A/EVAL2 authority: target-ranked shortlist with reserved refinement candidates;
# replay remains a hard TRUE_DFT retention gate with zero ranking/tie-break credit.
# Historical MLCV configs retain checkpoint_strategy="mlcv_nested_cv" and older
# adaptive configs retain their original checkpoint_strategy values.
checkpoint_strategy = "train2_target_first"
finalist_count = 5
finalist_rescue_batch_size = 5
# EVAL2 v1 may purchase at most this many additional target-ranked candidates
# after the initial 3+2 shortlist if no checkpoint passes hard admissibility.
eval2_candidate_rescue_cap = 5
# Permit checkpoint evaluation after any run completes. Incomplete campaigns are
# labeled interim and cannot create a production protocol freeze.
allow_partial_campaign = true
# Runtime inference choices are execution evidence, not scientific policy.
# A historical file with no inference_batch_policy keeps its positive batch_size
# as an exact fixed runtime choice. New fixed mode uses fixed_inference_batch_size
# (bounded by maximum_inference_batch_size); auto starts bounded and may adapt.
inference_batch_policy = "auto"
maximum_inference_batch_size = 32
# Immutable monitor and foundation-baseline results are reused across checkpoints.
cache_monitor_datasets = true
cache_replay_baseline = true
[export]
# Exported learned-model dtype must match [campaign].precision_profile.
dtype = "{precision['export_dtype']}"
'''


GUIDE_TEXT = """\
MLFF campaign commands
======================

The current campaign lifecycle has one scientific path:

init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production

1. init                Write an annotated campaign.toml.
2. doctor              Check paths, source inputs, MACE, replay, and the requested backend.
3. prepare             Build the neutral source/statistical substrate and common target-size preparation.
4. select-target-size  Run the paired-seed target-size screen and freeze N_selected.
5. cross-validate      Validate the frozen training method on exactly T_selected.
6. train-production    Train fresh final model(s) on the complete T_selected.

Post-production qualification is a separate, downstream family:

qualification status | qualification run | qualification activate-locked

The orthogonal storage command reports and manages reconstructible campaign
artifacts. Its report modes and every --dry-run are observational: they change
nothing, not even a cache, and they never create a campaign. Only --apply on the
invocation you are running authorizes a mutation; configuration cannot carry that
authority. status and advance project the training lifecycle only; advance never
runs qualification and never opens locked evidence. A target-size scientific
failure is terminal evidence; it does not authorize a production command.

Preparation and target-size selection
--------------------------------------
prepare is restartable and source-neutral. It authenticates the manifest,
DATA2-DATA5 authorities, the canonical P_train/M3 split, pi_train/pi_eval, and
one common preparation shared by every configured candidate size. It does not
choose a size, train a candidate, rank a checkpoint, or materialize a
per-size production dataset. The cutover rejects obsolete derived target-size
records and quarantines them rather than migrating them; they are never
translated.

select-target-size is the sole target-size owner. Candidate sizes are powers
from target_size_power_min through target_size_power_max, bounded by the
available population. evaluation_size_powers defines the direct nested M1,
M2, M3 populations and fidelity_epochs defines the controlled screen horizon.
Candidates are exact prefixes of pi_train, use the ordered seeds from the sole
enabled training method, and continue only through the accepted n1/n2/n3
funnel. The reducer freezes one N_selected and its exact T_selected membership,
or records a typed scientific failure. Replay and held-out CV evidence cannot
choose the size.

Post-selection owners
----------------------
cross-validate runs only after a selected target is current. It constructs the
configured K-fold plan under post_selection.cv, with K at least two, uses
target-only checkpoint and acceptance metrics, and requires every configured
fold/seed to pass. Its universe is exactly T_selected; it cannot change N.

train-production starts fresh from the canonical initialization, uses the
method accepted by cross-validation, and trains the complete T_selected under
training.max_num_epochs. Screening and CV checkpoints are not production
parents. Changing the production horizon invalidates only production
descendants; the selected target and accepted CV evidence remain current.

Post-production qualification
-----------------------------
Qualification consumes the frozen final-production publication; it never
creates, reorders, or shrinks it, and it owns no target-size, cross-validation,
production, checkpoint, seed, or member decision. Every threshold under
[qualification] is frozen before any product outcome is observed.

qualification run executes or resumes the nonlocked components for the exact
frozen publication: deployment parity through the real supported ML-IAP/LAMMPS
runtime, local PES response against matched external references, fixed-cell
relaxation topology and geometry fidelity, finite-temperature dynamics
stability, and uncertainty calibration on the reserved calibration role. A
required external reference that has not been supplied yields
waiting_for_reference together with an exact request bundle on disk; it is never
converted into a pass. A component failure rejects that exact publication.

qualification activate-locked is the only path that opens the reserved
LOCKED_INTERPOLATION_TEST cohort. It requires --confirm, requires every
mandatory nonlocked component to have already passed, and is refused a second
time for the same publication and cohort. A locked failure rejects the exact
published product; it cannot select another member, loosen a threshold, or make
the revealed cohort a fresh locked test again.

qualification status reports publication, executable, environment,
specification, component, activation, and verdict state without mutating
anything.

Configuration and reproducibility
---------------------------------
The generated configuration exposes the target-size power range, direct
evaluation powers, screen fidelity epochs, and the post-selection CV policy.
Optimizer seeds are authored only by the sole enabled training method. The
current CV authority is post_selection.cv; pre-target fold controls are not
generated. The learned model uses the binary single (FP32) or double (FP64)
precision selected at init, while mdstats scientific reductions and persistent
MD bookkeeping remain FP64.

Every durable scientific record binds its source, protocol, parent authorities,
and content digests. Reopening a workspace re-derives current selection and
currentness before reuse. Scientific input changes invalidate the affected
descendants; provenance-only changes do not change arithmetic; CV-only edits do
not invalidate selection; production-only edits do not invalidate selection or
CV. Missing, corrupt, stale, or incompatible derived artifacts fail closed and
are rebuilt by their owning stage.

Storage operations
------------------
Storage semantics come from the real P1-P7 owners, never from a pathname, a
report label, a stage name, or a process id. Every consequential action plans
first, shows what it would do, and mutates only when you authorize it:

storage report                          owner-driven read-only inventory
storage report --deep                   exact recursive physical audit
storage cleanup --tier safe --dry-run   inspect zero-loss cleanup
storage cleanup --tier cache --dry-run  inspect owner-certified cache eviction
storage cleanup --tier safe|cache --apply   apply the shown plan
storage archive create --dry-run        show cold-replaceable historical bulk
storage archive create --apply          archive it and reclaim its hot bytes
storage archive list|verify|restore     catalog, authenticate, bring bytes back
storage deduplicate --dry-run|--apply   owner-certified immutable dedup

safe loses no scientific, restart, qualification, locked, or acceleration-cache
capability. cache adds only eviction an owner certifies as exactly
reconstructible, so it costs recomputation and nothing else. archive is a
reversible representation change for historical bulk: restored evidence stays
historical and is never promoted to current. The retired recompute and compact
loss tiers are not current product authority.

External inputs, current scientific records, restart checkpoints, and the logs
needed for diagnosis are never deletion candidates. Anything an owner cannot
positively classify is retained.

The P6 implementation ends at current functional/restart closure. Downstream
accelerator and long-production qualification is separate evidence and is not
claimed by this guide.
"""


class _Formatter(argparse.RawDescriptionHelpFormatter):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdstats-mlff-campaign",
        formatter_class=_Formatter,
        description=(
            "Run an auditable MACE fine-tuning campaign from VASP data to a current "
            "selected target and fresh production model.\n\n"
"Current lifecycle: init -> doctor -> prepare -> select-target-size -> "
            "cross-validate -> train-production, then the separate post-production "
            "`qualification` family"
        ),
        epilog="Run `... guide` for the short scientific workflow and `... status` for the next safe action.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG_NAME, help="campaign TOML file (default: campaign.toml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="write an annotated campaign configuration", formatter_class=_Formatter)
    p.add_argument("--workspace")
    p.add_argument("--training-root")
    p.add_argument("--foundation-model")
    p.add_argument(
        "--foundation-family",
        choices=("mace_mh_1", "mace_mpa_0"),
        default="mace_mh_1",
        help="generated campaign foundation family (default: mace_mh_1)",
    )
    p.add_argument(
        "--foundation-head",
        help="selected foundation head (default: omat_pbe for MH-1, default for MPA-0)",
    )
    p.add_argument(
        "--backend",
        choices=("cueq", "e3nn"),
        default="e3nn",
        help="source/DATA6/evaluation backend (default: e3nn)",
    )
    p.add_argument(
        "--training-backend",
        choices=("cueq", "e3nn"),
        default="cueq",
        help="TRAIN2 backend (default: cueq; pure CuEq training with portable e3nn checkpoints)",
    )
    p.add_argument(
        "--replay-set",
        help="single selected replay ExtXYZ; mdstats derives train/monitor internally",
    )
    # Deprecated init-only flags remain parseable for historical automation but
    # are intentionally hidden from help. New configs use --replay-set.
    p.add_argument("--replay-train", help=argparse.SUPPRESS)
    p.add_argument("--replay-monitor", help=argparse.SUPPRESS)
    p.add_argument("--replay-true-labels", help=argparse.SUPPRESS)
    p.add_argument(
        "--precision",
        choices=("single", "double"),
        default="single",
        help="learned-model precision: single=FP32 or double=FP64 (default: single)",
    )
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=command_init)

    p = sub.add_parser("doctor", help="check inputs, MACE, replay, wrappers, CUDA, and the frozen acceleration backend")
    p.set_defaults(func=command_doctor)

    p = sub.add_parser(
        "prepare",
        help=(
            "rebuild the current target-size scientific substrate: source and frame "
            "authority, the neutral statistical base, the target-size experiment "
            "definition, and the one common preparation. It does not select a target "
            "size, train a candidate, or rank anything; safely resumable"
        ),
    )
    p.add_argument("--approve-manifest", action="store_true", help="approve the reviewed manifest and return; then run plain prepare")
    p.add_argument(
        "--continue-after-approval",
        action="store_true",
        help="approve and continue the current preparation pipeline in this invocation",
    )
    p.add_argument(
        "--refresh-inferences",
        action="store_true",
        help="re-read XML metadata and re-run filename/cell strain inference before approval",
    )
    p.add_argument("--rebuild-catalog", action="store_true", help="rebuild DATA2-DATA5 after an intentional manifest change")
    p.add_argument("--max-new-frames", type=int, help="bound new foundation-inference frames for this invocation")
    p.set_defaults(func=command_prepare)

    p = sub.add_parser(
        "select-target-size",
        help=(
            "run/resume the complete configurable-fidelity paired-seed target-size "
            "screen; this is the only command that trains candidates and decides N"
        ),
    )
    p.set_defaults(func=command_select_target_size)

    p = sub.add_parser(
        "cross-validate",
        help=(
            "run/resume the complete selected-only post-selection cross-validation "
            "of the frozen training method; this is the only command that decides "
            "whether the method is accepted for production"
        ),
    )
    p.set_defaults(func=command_cross_validate)

    p = sub.add_parser(
        "train-production",
        help=(
            "train the fresh final production run(s) on the full selected dataset "
            "under the cross-validation-accepted method and the configured "
            "[training].max_num_epochs horizon"
        ),
    )
    p.set_defaults(func=command_train_production)

    p = sub.add_parser(
        "storage",
        help="inspect and manage owner-driven MLFF campaign storage",
        description=(
            "Owner-driven storage management. Semantic eligibility always comes "
            "from the real P1-P7 owners, never from a pathname or a report label. "
            "Use `report`, `cleanup`, `archive`, or `deduplicate`; bare `storage` "
            "is a shorthand for `storage report`."
        ),
    )
    p.add_argument(
        "--top", type=int, default=20,
        help="with bare `storage`, number of largest artifacts retained in the report",
    )
    storage_sub = p.add_subparsers(
        dest="storage_command", metavar="{report,cleanup,archive,deduplicate}"
    )
    p.set_defaults(func=command_storage, storage_command="report", deep=False)

    sp = storage_sub.add_parser(
        "report",
        help="read-only owner-driven inventory; --deep for exact physical accounting",
    )
    sp.add_argument(
        "--top", type=int, default=20,
        help="number of largest artifacts to retain in the JSON report",
    )
    sp.add_argument(
        "--deep", action="store_true",
        help=(
            "run the explicit deep physical audit: exact recursive accounting, "
            "symlink and ownership inspection. Still read-only."
        ),
    )
    sp.set_defaults(func=command_storage, storage_command="report")

    sp = storage_sub.add_parser(
        "cleanup",
        help="owner-driven safe/cache cleanup under a mandatory plan-then-authorize flow",
    )
    sp.add_argument(
        "--tier", choices=("safe", "cache"), default="safe",
        help=(
            "safe: zero scientific/restart/qualification/locked and acceleration-cache "
            "capability loss. cache: safe plus owner-certified exactly reconstructible "
            "cache eviction, which costs only recomputation."
        ),
    )
    sp.add_argument(
        "--dry-run", action="store_true",
        help="print and write the plan without modifying anything",
    )
    sp.add_argument(
        "--apply", action="store_true",
        help="authorize the plan; it is revalidated against fresh owner state first",
    )
    sp.set_defaults(func=command_cleanup, storage_command="cleanup")

    sp = storage_sub.add_parser(
        "archive",
        help="reversible authenticated cold representation of historical bulk",
    )
    archive_sub = sp.add_subparsers(
        dest="archive_command", metavar="{create,list,verify,restore,reclaim}"
    )
    sp.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="list")

    ap = archive_sub.add_parser(
        "create", help="archive owner-declared cold-replaceable historical bulk"
    )
    ap.add_argument(
        "--root", action="append", default=None,
        help=(
            "workspace-relative root to archive; may be repeated. Omitting it archives "
            "every owner-declared cold-replaceable artifact."
        ),
    )
    ap.add_argument(
        "--keep-hot", action="store_true",
        help="create and catalog the archive without reclaiming any hot byte",
    )
    ap.add_argument("--dry-run", action="store_true", help="show eligibility and stop")
    ap.add_argument("--apply", action="store_true", help="authorize archive creation")
    ap.add_argument(
        "--archive-codec", default=None, choices=("gzip", "none"),
        help="archive codec; the default is resolved from [storage]",
    )
    ap.add_argument("--archive-compression-level", type=int, default=None)
    ap.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="create")

    ap = archive_sub.add_parser("list", help="list the identity-keyed archive catalog")
    ap.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="list")

    ap = archive_sub.add_parser("verify", help="authenticate one cataloged archive")
    ap.add_argument("archive_identity")
    ap.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="verify")

    ap = archive_sub.add_parser(
        "restore", help="restore one cataloged archive; restored evidence stays historical"
    )
    ap.add_argument("archive_identity")
    ap.add_argument("--dry-run", action="store_true", help="authenticate only")
    ap.add_argument("--apply", action="store_true", help="authorize installation")
    ap.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="restore")

    ap = archive_sub.add_parser(
        "reclaim", help="resume interrupted hot reclamation for an authenticated archive"
    )
    ap.add_argument("archive_identity")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.set_defaults(func=command_storage_archive, storage_command="archive", archive_command="reclaim")

    sp = storage_sub.add_parser(
        "deduplicate",
        help="owner-certified immutable deduplication; representation change only",
    )
    sp.add_argument("--dry-run", action="store_true", help="plan without relinking")
    sp.add_argument("--apply", action="store_true", help="authorize inode replacement")
    sp.set_defaults(func=command_storage_deduplicate, storage_command="deduplicate")

    p = sub.add_parser(
        "qualification",
        help="post-production qualification of the frozen final publication",
        description=(
            "V7-native post-production qualification. `run` executes or resumes the "
            "nonlocked components against the exact frozen final-production "
            "publication and may stop in waiting_for_reference. `status` is "
            "observational. `activate-locked` is the only path that opens the "
            "reserved one-shot locked interpolation test; it is never automatic."
        ),
        formatter_class=_Formatter,
    )
    qualification_sub = p.add_subparsers(
        dest="qualification_command", metavar="{status,run,activate-locked}"
    )
    p.set_defaults(func=command_qualification_status, qualification_command="status")

    sp = qualification_sub.add_parser(
        "status", help="observational qualification/currentness report; mutates nothing"
    )
    sp.set_defaults(func=command_qualification_status, qualification_command="status")

    sp = qualification_sub.add_parser(
        "run",
        help=(
            "execute/resume nonlocked deployment, physical, relaxation, dynamics, and "
            "calibration qualification for the exact frozen publication"
        ),
    )
    sp.add_argument(
        "--case-workers",
        dest="case_workers",
        type=int,
        default=1,
        help=(
            "bounded concurrency for independent qualification cases; scheduling only, "
            "with no effect on evidence identity or the terminal verdict (default: 1)"
        ),
    )
    sp.set_defaults(func=command_qualification_run, qualification_command="run")

    sp = qualification_sub.add_parser(
        "activate-locked",
        help=(
            "irreversibly open the reserved one-shot locked interpolation test for the "
            "exact frozen publication"
        ),
    )
    sp.add_argument(
        "--confirm",
        action="store_true",
        help="acknowledge that activation permanently reveals the reserved locked cohort",
    )
    sp.set_defaults(
        func=command_qualification_activate_locked, qualification_command="activate-locked"
    )

    p = sub.add_parser("status", help="show stage state, paths, and the next safe command")
    p.set_defaults(func=command_status)

    p = sub.add_parser("advance", help="run the next incomplete stage; never skips a gate")
    p.set_defaults(func=command_advance)

    p = sub.add_parser("guide", help="print the short scientific user guide")
    p.set_defaults(func=command_guide)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = str(getattr(args, "command", None) or getattr(getattr(args, "func", None), "__name__", "command"))
    campaign_warning_capture = None
    try:
        # WARNING-DOMAIN1: one outer warning domain owns the complete campaign
        # command.  All operation-local MACE scopes nest into this capture, so
        # setup/recovery/provider warnings cannot leak between local scopes.
        # The outer domain also intercepts MACE/PyTorch WARNING logging records.
        with mace_runtime_warning_scope(
            f"campaign {command} command",
            emit_consolidated_warning=False,
            campaign_wide=True,
        ) as campaign_warning_capture:
            return int(args.func(args))
    except (CampaignCliError, TargetSizeCampaignStateError) as exc:
        try:
            if command in {name for name, _ in PIPELINE}:
                _, paths = _load_config(args.config)
                _mark_stage(CampaignStore(paths.state_db), paths, command, StageState.FAILED, str(exc))
        except Exception:
            pass
        print(f"mdstats-mlff-campaign: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("mdstats-mlff-campaign: interrupted; completed records remain resumable", file=sys.stderr)
        return 130
    finally:
        if campaign_warning_capture is not None:
            try:
                record = campaign_warning_capture.record
            except RuntimeError:
                record = None
            if record is not None and record.upstream_warning_groups:
                _warn(format_mace_runtime_compatibility_summary(record))


__all__ = [
    "MLFF_DATA9B3_VERSION",
    "CAMPAIGN_CLI_SCHEMA",
    "CURRENT_PREPARE_RESTART_RECEIPT_SCHEMA",
    "CURRENT_PREPARE_CONTRACT_VERSION",
    "CampaignCliError",
    "CampaignPaths",
    "CampaignStore",
    "StageState",
    "build_parser",
    "main",
]
