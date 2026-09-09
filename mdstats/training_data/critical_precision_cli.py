"""User-facing MACE CLI wrappers with the mdstats critical-FP64 patch enabled.

MACE/PyTorch can leave non-daemon worker or thread-pool state alive after a
successful CLI return.  These functions are executable entry points, not an
in-process API: after the MACE command finishes successfully, they flush logging
and streams and use ``os._exit(0)`` so a completed production job cannot hang at
interpreter shutdown.  Exceptions and nonzero ``SystemExit`` values remain
ordinary failures.
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from typing import Any

import numpy as np

from .critical_precision import (
    CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE,
    MaceCriticalPrecisionPolicy,
    activate_mace_critical_precision_policy,
)
from .mace_compatibility import mace_runtime_warning_handled, mace_runtime_warning_scope




def _arm_linux_parent_death_signal() -> None:
    """Ask Linux to terminate this process if its supervising parent disappears.

    Production training has two supervision layers: the campaign parent launches
    the mdstats precision wrapper, and the wrapper launches the real MACE Python
    child.  A parent-death signal closes the narrow gap where a supervisor is
    killed before it has a chance to forward an ordinary termination signal.
    This is best-effort and intentionally a no-op outside Linux.
    """

    if not sys.platform.startswith("linux"):
        return
    parent_pid = os.getppid()
    try:
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        # Linux prctl(PR_SET_PDEATHSIG, SIGTERM).
        result = int(libc.prctl(1, int(signal.SIGTERM), 0, 0, 0))
        if result != 0:
            return
    except Exception:
        return
    # The parent can disappear between getppid() and prctl().  Close that race.
    if os.getppid() != parent_pid:
        os.kill(os.getpid(), signal.SIGTERM)


def _force_kill_child(process: subprocess.Popen[bytes]) -> None:
    """Immediately kill a nested MACE process group, best effort."""

    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
    else:  # pragma: no cover - Windows fallback
        process.kill()


@contextmanager
def _forward_termination_signals(process: subprocess.Popen[bytes]):
    """Forward wrapper termination to the detached MACE process group.

    The MACE child intentionally owns a separate session so the wrapper can
    validate and terminate a completed-but-lingering PyTorch process.  Without
    forwarding, however, terminating the wrapper would orphan that detached
    CUDA process.  The first signal performs an orderly group shutdown; a
    repeated signal escalates immediately.
    """

    if threading.current_thread() is not threading.main_thread():
        yield
        return
    supported = [
        candidate
        for candidate in (
            getattr(signal, "SIGINT", None),
            getattr(signal, "SIGTERM", None),
            getattr(signal, "SIGHUP", None),
            getattr(signal, "SIGQUIT", None),
        )
        if candidate is not None
    ]
    previous: dict[int, Any] = {}
    forwarding = False

    def _handler(signum: int, frame: Any) -> None:
        del frame
        nonlocal forwarding
        if forwarding:
            _force_kill_child(process)
            os._exit(128 + int(signum))
        forwarding = True
        try:
            _terminate_child(process, grace_seconds=5.0)
        finally:
            raise SystemExit(128 + int(signum))

    for candidate in supported:
        previous[int(candidate)] = signal.getsignal(candidate)
        signal.signal(candidate, _handler)
    try:
        yield
    finally:
        for candidate, handler in previous.items():
            signal.signal(candidate, handler)


def _clean_success_exit() -> None:
    logging.shutdown()
    try:
        sys.stdout.flush()
    finally:
        sys.stderr.flush()
    os._exit(0)



def _mace_execution_authority() -> dict[str, Any] | None:
    from .mace_compatibility import mace_execution_authority_from_environment

    return mace_execution_authority_from_environment()


def _qualify_mace_execution_source(authority: dict[str, Any]) -> dict[str, Any]:
    """Qualify the installed MACE source before applying the narrow repair."""

    import mace
    from importlib import metadata

    from .mace_compatibility import (
        MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
        mace_execution_authority_to_environment,
        probe_mace_source_tree,
    )

    source_root = Path(mace.__file__).resolve().parent.parent
    try:
        installed_version = metadata.version("mace-torch")
    except metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            "The qualified MACE execution repair requires the installed "
            "mace-torch distribution."
        ) from exc
    if installed_version != "0.3.16":
        raise RuntimeError(
            "The qualified MACE execution repair is locked to mace-torch==0.3.16; "
            f"observed {installed_version!r}."
        )
    try:
        probe = probe_mace_source_tree(source_root)
    except Exception as exc:
        raise RuntimeError(
            "The installed MACE source could not be qualified for the mdstats "
            f"execution repair: {type(exc).__name__}: {exc}"
        ) from exc
    if not probe.current_execution_compatible:
        raise RuntimeError(
            "The installed MACE source does not match the qualified 0.3.16 "
            "execution semantics; refusing to patch or run it."
        )
    qualified = dict(authority)
    qualified["source_probe_digest"] = probe.content_digest
    os.environ[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = (
        mace_execution_authority_to_environment(qualified)
    )
    return _mace_execution_authority() or qualified


def _validate_mace_execution_arguments(
    args: Any,
    *,
    stage: str = "resolved",
) -> dict[str, Any]:
    """Check parser and post-mutation MACE arguments against launch authority."""

    authority = _mace_execution_authority()
    if authority is None:
        raise RuntimeError(
            "The qualified execution argument check ran without launch authority."
        )
    if str(getattr(args, "loss", "")) != authority["loss_family"]:
        raise RuntimeError(
            f"MACE {stage} loss family differs from authenticated mdstats "
            f"request: {getattr(args, 'loss', None)!r}."
        )
    if bool(getattr(args, "multiheads_finetuning", False)) != bool(
        authority["multiheads_finetuning"]
    ):
        raise RuntimeError(f"MACE {stage} multihead mode differs from authority.")
    if int(getattr(args, "batch_size", -1)) != int(authority["batch_size"]):
        raise RuntimeError(f"MACE {stage} batch size differs from authority.")
    if not np.isclose(
        float(getattr(args, "lr", float("nan"))),
        float(authority["learning_rate"]),
        rtol=0.0,
        atol=0.0,
    ):
        raise RuntimeError(f"MACE {stage} learning rate differs from authority.")
    if bool(getattr(args, "ema", False)) != bool(authority["ema"]):
        raise RuntimeError(f"MACE {stage} EMA flag differs from authority.")
    if bool(getattr(args, "compute_avg_num_neighbors", False)):
        raise RuntimeError(
            f"MACE {stage} retained forbidden local average-neighbor recomputation."
        )
    if authority["ema"] and not np.isclose(
        float(getattr(args, "ema_decay", float("nan"))),
        float(authority["ema_decay"]),
        rtol=0.0,
        atol=0.0,
    ):
        raise RuntimeError(f"MACE {stage} EMA decay differs from authority.")
    if authority["multiheads_finetuning"]:
        if getattr(args, "force_mh_ft_lr", None) is not True:
            raise RuntimeError(
                f"MACE {stage} did not retain force_mh_ft_lr=True."
            )
        if float(getattr(args, "real_pt_data_ratio_threshold", float("nan"))) != 0.0:
            raise RuntimeError(
                f"MACE {stage} did not retain real_pt_data_ratio_threshold=0.0."
            )
    if authority["role"] == "target_size" and bool(
        getattr(args, "distributed", False)
    ):
        raise RuntimeError(
            "Target-size complete-batch execution cannot use a distributed sampler."
        )
    return authority


def _mace_collection_uids(collection: Any, *, head_name: str) -> tuple[str, ...]:
    values: list[str] = []
    for item in collection:
        uid = getattr(item, "frame_uid", None)
        info = getattr(item, "info", None)
        if info is None and isinstance(item, dict):
            info = item.get("info", item)
        if uid in (None, ""):
            uid = info.get("frame_uid") if isinstance(info, dict) else None
        if uid in (None, ""):
            raise RuntimeError(
                f"MACE {head_name} training collection lost exported frame_uid metadata."
            )
        values.append(str(uid))
    if not values or len(set(values)) != len(values):
        raise RuntimeError(
            f"MACE {head_name} training collection is empty or duplicates frame UIDs."
        )
    return tuple(values)


def _annotate_mace_collections_with_exported_uids(*, head_configs: Any) -> None:
    """Carry exporter frame identity through MACE's Configuration dataclass.

    MACE 0.3.16 intentionally reduces ASE ``Atoms.info`` to its fixed
    ``Configuration`` fields and therefore does not preserve arbitrary
    membership metadata.  The wrapper re-associates the authenticated target
    ``frame_uid`` or replay ``replay_geometry_identity`` sequence with the
    corresponding collection immediately after MACE's own dataset loader
    returns.  A length/order/identity-domain mismatch fails closed; no token is
    inferred from a position or regenerated locally.
    """

    from .mace_compatibility import (
        _mace_execution_membership_values,
        mace_frame_uid_set_digest,
    )
    from .replay import (
        canonical_replay_geometry_identity,
        historical_replay_geometry_identity,
    )

    authority = _mace_execution_authority()
    if authority is None:
        raise RuntimeError(
            "MACE execution membership annotation ran without launch authority."
        )
    target_name = str(authority["target_head_name"])
    replay_name = str(authority["replay_head_name"])
    multihead = bool(authority["multiheads_finetuning"])

    for head_config in head_configs:
        head_name = str(getattr(head_config, "head_name", ""))
        if head_name == target_name:
            role = "target"
        elif multihead and head_name == replay_name:
            role = "replay"
        else:
            raise RuntimeError(
                f"MACE execution cannot classify training head {head_name!r} "
                "against the authenticated authority."
            )
        train_files = getattr(head_config, "train_file", None)
        collections = getattr(head_config, "collections", None)
        train_collection = None if collections is None else getattr(collections, "train", None)
        if not train_files or train_collection is None:
            raise RuntimeError(
                "MACE execution cannot authenticate frame membership without a "
                "materialized ASE training collection."
            )
        if isinstance(train_files, (str, os.PathLike)):
            train_files = [train_files]
        collection_values = list(train_collection)
        try:
            if role == "target":
                # Target frame_uid is retained by the existing exporter-facing
                # metadata adapter. Unlike replay geometry, it cannot be
                # reconstructed from a MACE Configuration, so keep the exact
                # target-file metadata check at this boundary.
                exported_uids = _mace_execution_membership_values(
                    train_files,
                    role=role,
                    head_name=head_name,
                )
            else:
                expected_replay_digest = authority.get(
                    "replay_frame_uid_set_digest"
                )
                if expected_replay_digest is None:
                    # Compatibility for older manually-authenticated launch
                    # fixtures that predate replay geometry authority.
                    exported_uids = _mace_execution_membership_values(
                        train_files,
                        role=role,
                        head_name=head_name,
                    )
                else:
                    # ReplayFileArtifact owns the authenticated geometry
                    # sequence. The actual loaded MACE Configuration is the
                    # child-side proof of what MACE will train, so derive the
                    # existing identity directly from these objects rather
                    # than reparsing replay ExtXYZ bytes or accepting a
                    # count-only match. Persisted v3/v4 replay artifacts use
                    # the historical wrapped-fractional identity; new
                    # single-source authorities use the raw canonical one.
                    canonical_geometry = tuple(
                        canonical_replay_geometry_identity(item)
                        for item in collection_values
                    )
                    if (
                        mace_frame_uid_set_digest(canonical_geometry)
                        == expected_replay_digest
                    ):
                        exported_uids = canonical_geometry
                    else:
                        # Only persisted legacy artifacts need the historical
                        # wrapped-fractional schema. Keep that compatibility
                        # calculation lazy so a valid canonical non-periodic
                        # geometry (whose cell may be absent/singular) is not
                        # rejected merely because it has no legacy identity.
                        historical_geometry = tuple(
                            historical_replay_geometry_identity(item)
                            for item in collection_values
                        )
                        if (
                            mace_frame_uid_set_digest(historical_geometry)
                            == expected_replay_digest
                        ):
                            exported_uids = historical_geometry
                        else:
                            # Older manually-authenticated/legacy launch
                            # fixtures may intentionally authenticate replay
                            # through their exported frame_uid metadata. Keep
                            # that compatibility route only after the loaded
                            # geometry domains have both failed; current
                            # single-source P5 never reaches this file scan.
                            metadata_uids = _mace_execution_membership_values(
                                train_files,
                                role=role,
                                head_name=head_name,
                            )
                            if (
                                mace_frame_uid_set_digest(metadata_uids)
                                == expected_replay_digest
                            ):
                                exported_uids = metadata_uids
                            else:
                                raise RuntimeError(
                                    "MACE changed replay geometry membership, order, or "
                                    "identity domain after authenticated launch."
                                )
        except Exception as exc:
            raise RuntimeError(
                f"MACE {head_name} training membership could not be authenticated."
            ) from exc
        if len(collection_values) != len(exported_uids):
            raise RuntimeError(
                "MACE dataset loading changed the authenticated training collection "
                "length; refusing to guess frame membership."
            )
        if len(set(exported_uids)) != len(exported_uids):
            raise RuntimeError(
                "MACE exported training files contain duplicate frame UIDs."
            )
        for item, uid in zip(collection_values, exported_uids):
            item.frame_uid = uid


def _validate_mace_execution_loader(
    *,
    args: Any,
    loss_fn: Any,
    train_loader: Any,
    train_set: Any,
    head_configs: Any,
    train_sampler: Any,
) -> dict[str, Any]:
    """Validate actual MACE collections/loaders and publish resolved evidence."""

    from .mace_compatibility import (
        MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
        mace_execution_authority_to_environment,
        mace_frame_uid_set_digest,
        record_mace_execution_evidence,
    )

    authority = _validate_mace_execution_arguments(args, stage="post-mutation")
    loss_class = (
        f"{type(loss_fn).__module__}.{type(loss_fn).__qualname__}"
    )
    if loss_class != "mace.modules.loss.WeightedEnergyForcesStressLoss":
        raise RuntimeError(
            "MACE resolved an unsupported loss implementation for the authenticated "
            f"stress method: {loss_class}."
        )
    target_name = str(authority["target_head_name"])
    replay_name = str(authority["replay_head_name"])
    by_head = {str(config.head_name): config for config in head_configs}
    target_config = by_head.get(target_name)
    if target_config is None:
        raise RuntimeError(f"MACE target head {target_name!r} is absent from loaded data.")
    target_uids = _mace_collection_uids(
        target_config.collections.train, head_name=target_name
    )
    target_count = len(target_uids)
    replay_uids: tuple[str, ...] = ()
    if authority["multiheads_finetuning"]:
        replay_config = by_head.get(replay_name)
        if replay_config is None:
            raise RuntimeError(f"MACE replay head {replay_name!r} is absent from loaded data.")
        replay_uids = _mace_collection_uids(
            replay_config.collections.train, head_name=replay_name
        )
        replay_count = len(replay_uids)
    else:
        replay_count = 0
    if target_count != int(authority["target_train_count"]):
        raise RuntimeError(
            "MACE resolved target exposure count differs from authenticated materialization."
        )
    if replay_count != int(authority["replay_train_count"]):
        raise RuntimeError(
            "MACE resolved replay exposure count differs from authenticated materialization."
        )
    if len(train_set) != target_count + replay_count:
        raise RuntimeError(
            "MACE combined training dataset count differs from head exposure counts."
        )
    target_uid_digest = mace_frame_uid_set_digest(target_uids)
    expected_target_uid_digest = authority.get("target_frame_uid_set_digest")
    if expected_target_uid_digest is not None and target_uid_digest != expected_target_uid_digest:
        raise RuntimeError("MACE changed target frame membership before training.")
    replay_uid_digest = None if not replay_uids else mace_frame_uid_set_digest(replay_uids)
    expected_replay_uid_digest = authority.get("replay_frame_uid_set_digest")
    if expected_replay_uid_digest is not None and replay_uid_digest != expected_replay_uid_digest:
        raise RuntimeError("MACE changed replay frame membership before training.")

    target_batches: int | None = None
    target_drop_last: bool | None = None
    if authority["role"] == "target_size":
        if train_sampler is not None:
            raise RuntimeError(
                "Target-size complete-batch execution received a sampler."
            )
        target_drop_last = bool(getattr(train_loader, "drop_last", True))
        if target_drop_last is not False:
            raise RuntimeError(
                "Target-size qualified execution retained drop_last=True."
            )
        target_batches = int(len(train_loader))
        if target_batches != int(authority["target_updates_per_epoch"]):
            raise RuntimeError(
                "Target-size realized batch count differs from ceil(N/B) authority."
            )
        head_loader = getattr(target_config, "train_loader", None)
        if head_loader is None or bool(getattr(head_loader, "drop_last", True)):
            raise RuntimeError(
                "Target-size per-head loader retained drop_last=True."
            )
        if int(len(head_loader)) != target_batches:
            raise RuntimeError(
                "Target-size per-head and combined loaders disagree on batch count."
            )

    evidence = {
        "role": authority["role"],
        "loss_family": str(args.loss),
        "loss_class": loss_class,
        "learning_rate": float(args.lr),
        "ema": bool(args.ema),
        "ema_decay": None if not bool(args.ema) else float(args.ema_decay),
        "multiheads_finetuning": bool(args.multiheads_finetuning),
        "force_mh_ft_lr": (
            None if not bool(args.multiheads_finetuning) else bool(args.force_mh_ft_lr)
        ),
        "real_pt_data_ratio_threshold": (
            None
            if not bool(args.multiheads_finetuning)
            else float(args.real_pt_data_ratio_threshold)
        ),
        "target_train_count": target_count,
        "replay_train_count": replay_count,
        "target_duplication_factor": 1,
        "target_batch_size": int(args.batch_size),
        "target_updates_per_epoch": target_batches,
        "target_drop_last": target_drop_last,
        "distributed": bool(args.distributed),
        "target_frame_uid_set_digest": target_uid_digest,
        "replay_frame_uid_set_digest": replay_uid_digest,
        "combined_train_count": int(len(train_set)),
    }
    resolved = record_mace_execution_evidence(authority, evidence)
    os.environ[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = (
        mace_execution_authority_to_environment(resolved)
    )
    return evidence


def _install_mace_execution_semantics_patch(authority: dict[str, Any]) -> None:
    """Install the one source-qualified MACE execution-semantics repair.

    MACE 0.3.16 unconditionally selects ``UniversalLoss`` for multi-head
    fine-tuning and constructs all training loaders with ``drop_last`` tied to
    the historical LBFGS flag.  The authenticated mdstats launch authority is
    the only thing that enables this patch.  The exact source markers are
    checked before rewriting so a future MACE source cannot silently receive a
    stale transformation.
    """

    import inspect
    import re
    import textwrap

    import mace.cli.run_train as run_train_module

    if getattr(run_train_module, "_mdstats_execution_semantics_patched", False):
        if getattr(run_train_module, "_mdstats_execution_semantics_role", None) == authority[
            "role"
        ]:
            return
        original_patched = getattr(run_train_module, "_mdstats_original_run", None)
        if original_patched is None:
            raise RuntimeError(
                "MACE execution-semantics patch state is inconsistent; refusing "
                "to switch launch roles in-process."
            )
        run_train_module.run = original_patched
        delattr(run_train_module, "_mdstats_execution_semantics_patched")
        if hasattr(run_train_module, "_mdstats_execution_semantics_role"):
            delattr(run_train_module, "_mdstats_execution_semantics_role")
    original = getattr(run_train_module, "_mdstats_original_run", run_train_module.run)
    source = textwrap.dedent(inspect.getsource(original))

    parser_marker = "    args, input_log_messages = tools.check_args(args)\n"
    forced_loss_marker = '        args.loss = "universal"\n'
    collection_marker = "        head_configs.append(head_config)\n\n    if all(\n"
    loss_marker = "    loss_fn = get_loss_fn(args, dipole_only, args.compute_dipole)\n"
    drop_last_pattern = r"drop_last\s*=\s*\(\s*not\s+args\.lbfgs\s*\)"
    combined_drop_last_pattern = (
        r"drop_last\s*=\s*\(\s*train_sampler\s+is\s+None\s+and\s+not\s+args\.lbfgs\s*\)"
    )
    if (
        source.count(parser_marker) != 1
        or source.count(forced_loss_marker) != 1
        or source.count(collection_marker) != 1
        or source.count(loss_marker) != 1
    ):
        raise RuntimeError(
            "The qualified MACE argument/loss source contract changed; mdstats "
            "refuses to patch an unverified execution path."
        )
    if authority["role"] == "target_size":
        if len(re.findall(drop_last_pattern, source)) != 2:
            raise RuntimeError(
                "The qualified MACE target-loader drop_last source contract changed; "
                "mdstats refuses to patch an unverified execution path."
            )
        if len(re.findall(combined_drop_last_pattern, source)) != 1:
            raise RuntimeError(
                "The qualified MACE combined-loader source contract changed; mdstats "
                "refuses to patch an unverified execution path."
            )

    source = source.replace(
        parser_marker,
        parser_marker
        + "    from mdstats.training_data.critical_precision_cli import _validate_mace_execution_arguments\n"
        + "    _validate_mace_execution_arguments(args, stage='parser')\n",
        1,
    )
    # The native MACE call to get_loss_fn remains the owner of loss
    # construction.  Only its forced UniversalLoss selector is removed.
    source = source.replace(
        forced_loss_marker,
        "        # mdstats: retain the authenticated native executable loss.\n"
        "        args.loss = 'stress'\n",
        1,
    )
    source = source.replace(
        collection_marker,
        "        head_configs.append(head_config)\n\n"
        "    from mdstats.training_data.critical_precision_cli import _annotate_mace_collections_with_exported_uids\n"
        "    _annotate_mace_collections_with_exported_uids(head_configs=head_configs)\n\n"
        "    if all(\n",
        1,
    )
    if authority["role"] == "target_size":
        source = re.sub(drop_last_pattern, "drop_last=False", source)
        source = re.sub(combined_drop_last_pattern, "drop_last=False", source)
    source = source.replace(
        loss_marker,
        loss_marker
        + "    from mdstats.training_data.critical_precision_cli import _validate_mace_execution_loader\n"
        + "    _mdstats_mace_execution_evidence = _validate_mace_execution_loader(\n"
        + "        args=args, loss_fn=loss_fn, train_loader=train_loader,\n"
        + "        train_set=train_set, head_configs=head_configs,\n"
        + "        train_sampler=train_sampler,\n"
        + "    )\n",
        1,
    )

    namespace: dict[str, Any] = {}
    globals_copy = dict(original.__globals__)
    exec(compile(source, "<mdstats-mace-execution-semantics>", "exec"), globals_copy, namespace)
    patched = namespace.get("run")
    if patched is None:
        raise RuntimeError("Failed to install the qualified MACE execution-semantics patch.")
    patched.__name__ = original.__name__
    patched.__qualname__ = original.__qualname__
    patched.__doc__ = original.__doc__
    run_train_module._mdstats_original_run = original
    run_train_module._mdstats_execution_semantics_patched = True
    run_train_module._mdstats_execution_semantics_role = authority["role"]
    run_train_module.run = patched


def _install_mace_restart_epoch_patch() -> None:
    """Install the qualified MACE epoch/restart and PREC2 stage hooks.

    MACE 0.3.16 restarts at the checkpointed epoch rather than the following
    epoch.  mdstats already corrected that behavior.  PREC2 extends the same
    source-qualified loop patch with an in-process precision-stage boundary and
    a latest-only exact-continuation companion written after each durable epoch.
    """

    import inspect
    import textwrap
    import mace.tools as mace_tools

    from .precision_runtime import (
        configure_precision_runtime_from_argv,
        install_mace_precision_runtime_patches,
    )

    from .adaptive_stop import adaptive_stop_policy_from_environment
    from .train2_runtime import runtime_plan_from_environment
    from .mlcv_monitors import MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE

    execution_authority = _mace_execution_authority()
    if execution_authority is not None:
        execution_authority = _qualify_mace_execution_source(execution_authority)
        _install_mace_execution_semantics_patch(execution_authority)

    plan = configure_precision_runtime_from_argv(sys.argv)
    staged = bool(plan is not None and plan.staged)
    restarting = "--restart_latest" in sys.argv[1:]
    adaptive_stop = adaptive_stop_policy_from_environment() is not None
    train2 = runtime_plan_from_environment() is not None
    if train2 and adaptive_stop:
        raise RuntimeError('TRAIN2 and historical adaptive-stop runtime authorities cannot be active together.')
    if train2 and staged:
        raise RuntimeError(
            'TRAIN2B v1 requires one fixed FP32 or FP64 precision stage; the retired staged refine/mixed precision runtime cannot be combined with TRAIN2.'
        )
    mlcv_training_diagnostic = bool(
        os.environ.get(MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE)
    )
    if not restarting and not staged and not adaptive_stop and not train2 and not mlcv_training_diagnostic:
        return

    # Batch casting, EMA restoration, and staged checkpoint selection must be
    # installed before run_train imports the corresponding MACE symbols.
    if staged:
        install_mace_precision_runtime_patches()

    original = mace_tools.train
    source = textwrap.dedent(inspect.getsource(original))
    epoch_line = "    epoch = start_epoch\n"
    scheduler_line = "        if epoch > start_epoch:\n"
    train_marker = "        # Train\n"
    persistence_marker = (
        "                        keep_last = False or save_all_checkpoints\n"
        "        if distributed:\n"
        "            torch.distributed.barrier()\n"
    )
    baseline_marker = (
        "    valid_loss = valid_loss_head  # consider only the last head for the checkpoint\n"
    )
    validation_start_marker = (
        "    # log validation loss before _any_ training\n"
        "    for valid_loader_name, valid_loader in valid_loaders.items():\n"
    )
    epoch_increment_marker = "        epoch += 1\n"
    exit_now_marker = "    exit_now = torch.zeros(1, device=device) if distributed else None\n"
    if source.count(epoch_line) != 1 or source.count(scheduler_line) != 2:
        raise RuntimeError(
            "The qualified MACE restart-loop source contract changed; mdstats "
            "refuses an unverified restart/staged transition."
        )
    if (staged or train2) and (source.count(train_marker) != 1 or source.count(persistence_marker) != 1):
        raise RuntimeError(
            "The qualified MACE PREC2 training-loop source contract changed; mdstats "
            "refuses an unverified precision-stage transition."
        )
    if (adaptive_stop or train2 or mlcv_training_diagnostic) and source.count(validation_start_marker) != 1:
        raise RuntimeError(
            "The qualified MACE validation-loop source contract changed; mdstats "
            "refuses an unverified MLCV monitor patch."
        )
    if (adaptive_stop or train2) and (
        source.count(exit_now_marker) != 1
        or source.count(epoch_increment_marker) != 1
    ):
        raise RuntimeError(
            'The qualified MACE TRAIN2/ADAPT training-loop source contract changed; mdstats refuses an unverified runtime patch.'
        )
    if adaptive_stop and (
        source.count(baseline_marker) != 1
    ):
        raise RuntimeError(
            "The qualified MACE ADAPT-STOP1 training-loop source contract changed; mdstats "
            "refuses an unverified adaptive-stop patch."
        )

    if restarting:
        source = source.replace(
            epoch_line,
            "    checkpoint_start_epoch = start_epoch\n"
            "    expected_restart_epoch = int(__import__('os').environ['MDSTATS_MACE_RESTART_EPOCH'])\n"
            "    if checkpoint_start_epoch != expected_restart_epoch:\n"
            "        raise RuntimeError(f'MACE loaded restart epoch {checkpoint_start_epoch}, expected {expected_restart_epoch}')\n"
            "    epoch = start_epoch + 1\n",
            1,
        ).replace(
            scheduler_line,
            "        if epoch > checkpoint_start_epoch:\n",
        )

    if staged:
        source = source.replace(
            train_marker,
            "        # mdstats PREC2: transition after this epoch's scheduler step and before training.\n"
            "        from mdstats.training_data.precision_runtime import apply_precision_stage_boundary\n"
            "        apply_precision_stage_boundary(\n"
            "            model=model, optimizer=optimizer, lr_scheduler=lr_scheduler, ema=ema,\n"
            "            loss_fn=loss_fn, epoch=epoch, distributed_model=distributed_model, swa=swa,\n"
            "        )\n"
            "\n"
            + train_marker,
            1,
        )
        source = source.replace(
            persistence_marker,
            "                        keep_last = False or save_all_checkpoints\n"
            "        from mdstats.training_data.precision_runtime import persist_precision_runtime_companion\n"
            "        persist_precision_runtime_companion(\n"
            "            model=model, optimizer=optimizer, lr_scheduler=lr_scheduler, ema=ema,\n"
            "            checkpoint_handler=checkpoint_handler, epoch=epoch, rank=rank,\n"
            "        )\n"
            "        if distributed:\n"
            "            torch.distributed.barrier()\n",
            1,
        )

    if train2:
        source = source.replace(
            exit_now_marker,
            exit_now_marker
            + "    from mdstats.training_data.train2_runtime import activate_train2_runtime\n"
            + "    _mdstats_train2_active = activate_train2_runtime(\n"
            + "        model=model, optimizer=optimizer, lr_scheduler=lr_scheduler, ema=ema,\n"
            + "        train_loader=train_loader, current_epoch=epoch, max_num_epochs=max_num_epochs,\n"
            + "        checkpoint_handler=checkpoint_handler, logger_path=logger.path, swa=swa, rank=rank,\n"
            + "    )\n"
            + "    if _mdstats_train2_active:\n"
            + "        patience = max_num_epochs + 1\n",
            1,
        )
        source = source.replace(
            persistence_marker,
            "                        keep_last = False or save_all_checkpoints\n"
            "        from mdstats.training_data.train2_runtime import persist_train2_runtime_epoch\n"
            "        persist_train2_runtime_epoch(epoch=epoch)\n"
            "        if distributed:\n"
            "            torch.distributed.barrier()\n",
            1,
        )
        source = source.replace(
            epoch_increment_marker,
            "        from mdstats.training_data.train2_runtime import train2_runtime_should_pause_after_epoch\n"
            "        if train2_runtime_should_pause_after_epoch(epoch):\n"
            "            logging.info(f'mdstats TRAIN2B paused after durable epoch {epoch}')\n"
            "            break\n"
            + epoch_increment_marker,
            1,
        )

    if train2:
        source = source.replace(
            validation_start_marker,
            "    # mdstats TRAIN2B: prepend the authenticated TRUE_DFT replay monitor as diagnostics only.\n"
            "    from mdstats.training_data.train2_runtime import prepare_train2_true_replay_validation_loader\n"
            "    valid_loaders = prepare_train2_true_replay_validation_loader(model, valid_loaders)\n"
            + validation_start_marker,
            1,
        )

    if mlcv_training_diagnostic:
        source = source.replace(
            validation_start_marker,
            "    # mdstats MLCV-MON1: prepend the selection-inert target-training diagnostic\n"
            "    # so MACE's historical last-loader checkpoint/patience scalar remains target-driven.\n"
            "    from mdstats.training_data.mlcv_monitors import prepare_training_diagnostic_validation_loader\n"
            "    valid_loaders = prepare_training_diagnostic_validation_loader(model, valid_loaders)\n"
            + validation_start_marker,
            1,
        )

    if adaptive_stop:
        source = source.replace(
            validation_start_marker,
            "    # mdstats ADAPT-STOP1: one-head/naive runs receive the fixed true-replay monitor\n"
            "    # as an auxiliary validation loader. Replay is inserted before target so MACE's\n"
            "    # historical last-loader checkpoint/patience scalar remains target-driven.\n"
            "    from mdstats.training_data.adaptive_stop import prepare_auxiliary_replay_validation_loader, prepare_foundation_full_replay_validation_loader\n"
            "    valid_loaders = prepare_auxiliary_replay_validation_loader(model, valid_loaders)\n"
            "    valid_loaders = prepare_foundation_full_replay_validation_loader(model, valid_loaders)\n"
            + validation_start_marker,
            1,
        )
        source = source.replace(
            baseline_marker,
            baseline_marker
            + "    from mdstats.training_data.adaptive_stop import validate_adaptive_stop_foundation_baseline, remove_foundation_full_replay_validation_loader\n"
            + "    validate_adaptive_stop_foundation_baseline(logger.path)\n"
            + "    valid_loaders = remove_foundation_full_replay_validation_loader(valid_loaders)\n",
            1,
        )
        source = source.replace(
            exit_now_marker,
            exit_now_marker
            + "    from mdstats.training_data.adaptive_stop import adaptive_training_stop_already_terminal\n"
            + "    if adaptive_training_stop_already_terminal(logger.path):\n"
            + "        logging.info('mdstats ADAPT-STOP1 found terminal restart evidence; skipping further epochs')\n"
            + "        epoch = max_num_epochs\n",
            1,
        )
        source = source.replace(
            epoch_increment_marker,
            "        from mdstats.training_data.adaptive_stop import adaptive_training_stop_requested\n"
            "        _mdstats_adaptive_stop = False\n"
            "        if rank == 0:\n"
            "            _mdstats_adaptive_stop = adaptive_training_stop_requested(logger.path, epoch)\n"
            "        if distributed:\n"
            "            _mdstats_stop_tensor = torch.tensor([1 if _mdstats_adaptive_stop else 0], device=device)\n"
            "            torch.distributed.broadcast(_mdstats_stop_tensor, src=0)\n"
            "            _mdstats_adaptive_stop = bool(_mdstats_stop_tensor.item())\n"
            "        if _mdstats_adaptive_stop:\n"
            "            logging.info(f'mdstats ADAPT-STOP1 terminated training after durable epoch {epoch}')\n"
            "            break\n"
            + epoch_increment_marker,
            1,
        )

    namespace: dict[str, Any] = {}
    globals_copy = dict(original.__globals__)
    exec(compile(source, "<mdstats-mace-precision-train>", "exec"), globals_copy, namespace)
    patched = namespace.get("train")
    if patched is None:
        raise RuntimeError("Failed to install the qualified MACE training-loop patch.")
    patched.__name__ = original.__name__
    patched.__qualname__ = original.__qualname__
    patched.__doc__ = original.__doc__
    mace_tools.train = patched


CRITICAL_PRECISION_POLICY_ENV = CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE


def _critical_precision_policy_from_environment() -> MaceCriticalPrecisionPolicy:
    """Restore the protocol-bound critical policy for one wrapper process.

    Missing environment state is intentionally interpreted as the historical
    critical-FP64 policy so old direct wrapper invocations remain compatible.
    """

    raw = os.environ.get(CRITICAL_PRECISION_POLICY_ENV)
    if raw in (None, ""):
        return MaceCriticalPrecisionPolicy()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("policy payload must be a JSON object")
        return MaceCriticalPrecisionPolicy.from_dict(payload)
    except Exception as exc:
        raise RuntimeError(
            f"Invalid {CRITICAL_PRECISION_POLICY_ENV} wrapper policy: {exc}"
        ) from exc


def _dispatch(module: str) -> None:
    activate_mace_critical_precision_policy(_critical_precision_policy_from_environment())
    if module == "train":
        _install_mace_restart_epoch_patch()
        from mace.cli.run_train import main
    elif module == "eval":
        from mace.cli.eval_configs import main
    elif module == "select-head":
        from mace.cli.select_head import main
    else:  # pragma: no cover - internal contract
        raise RuntimeError(f"Unknown MACE command: {module}")
    try:
        with mace_runtime_warning_scope(f"MACE {module} command-line execution"):
            result = main()
    except SystemExit as exc:
        code = exc.code
        if code in (None, 0):
            _clean_success_exit()
        raise
    if result not in (None, 0):
        raise SystemExit(result)
    _clean_success_exit()


def _argument_value(name: str) -> str | None:
    """Return one ordinary ``--name value`` or ``--name=value`` argument."""

    for index, token in enumerate(sys.argv[1:]):
        if token == name:
            position = index + 2
            return None if position >= len(sys.argv) else sys.argv[position]
        prefix = name + "="
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _configuration_count(path: Path) -> int:
    from ase.io import read

    configurations = read(path, index=":", format="extxyz")
    return len(configurations) if isinstance(configurations, list) else 1


def _valid_eval_output(path: Path, *, expected_count: int, require_stress: bool) -> bool:
    """Validate a completed MACE evaluation file without trusting process exit."""

    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        from ase.io import read

        configurations = read(path, index=":", format="extxyz")
        if not isinstance(configurations, list):
            configurations = [configurations]
        if len(configurations) != expected_count:
            return False
        for atoms in configurations:
            energy = atoms.info.get("MACE_energy")
            forces = atoms.arrays.get("MACE_forces")
            stress = atoms.info.get("MACE_stress")
            if energy is None or not np.all(np.isfinite(np.asarray(energy, dtype=float))):
                return False
            if forces is None or not np.all(np.isfinite(np.asarray(forces, dtype=float))):
                return False
            if require_stress and (
                stress is None or not np.all(np.isfinite(np.asarray(stress, dtype=float)))
            ):
                return False
    except Exception:
        return False
    return True


def _terminate_child(process: subprocess.Popen[bytes], *, grace_seconds: float = 5.0) -> None:
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


def _child_code(module: str) -> str:
    source_root = Path(__file__).resolve().parents[2]
    imports = {
        "train": "from mace.cli.run_train import main",
        "eval": "from mace.cli.eval_configs import main",
        "select-head": "from mace.cli.select_head import main",
    }
    return "\n".join(
        (
            "import os, signal, sys",
            "if sys.platform.startswith('linux'):",
            "    import ctypes",
            "    _mdstats_parent_pid = os.getppid()",
            "    _mdstats_libc = ctypes.CDLL(None, use_errno=True)",
            "    _mdstats_libc.prctl(1, int(signal.SIGTERM), 0, 0, 0)",
            "    if os.getppid() != _mdstats_parent_pid:",
            "        os.kill(os.getpid(), signal.SIGTERM)",
            f"sys.path.insert(0, {str(source_root)!r})",
            "from mdstats.training_data.critical_precision import activate_mace_critical_precision_policy",
            "from mdstats.training_data.critical_precision_cli import _critical_precision_policy_from_environment",
            "from mdstats.training_data.critical_precision_cli import _install_mace_restart_epoch_patch",
            "from mdstats.training_data.mace_compatibility import mace_runtime_warning_scope",
            "activate_mace_critical_precision_policy(_critical_precision_policy_from_environment())",
            "_install_mace_restart_epoch_patch()" if module == "train" else "pass",
            imports[module],
            f"with mace_runtime_warning_scope({('MACE ' + module + ' child execution')!r}):",
            "    main()",
        )
    )


@mace_runtime_warning_handled("MACE checkpoint validation")
def _valid_mace_model(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    try:
        import torch

        model = torch.load(path, map_location="cpu", weights_only=False)
        return hasattr(model, "atomic_numbers") and hasattr(model, "parameters")
    except Exception:
        return False


def _run_child_until_artifact(
    module: str,
    *,
    artifact: Path,
    validator: Any,
    stable_seconds: float = 1.0,
    require_artifact_change: bool = False,
) -> None:
    """Run one MACE CLI and fail-safe on a complete stable artifact."""

    _arm_linux_parent_death_signal()
    # Snapshot a pre-existing artifact before the child can mutate it.  This
    # matters for TRAIN2 Stage-C continuation, where a valid Stage-B model file
    # already exists and must not be mistaken for newly completed work.
    initial_signature: tuple[int, int] | None = None
    if artifact.is_file():
        stat = artifact.stat()
        initial_signature = (int(stat.st_size), int(stat.st_mtime_ns))
    process = subprocess.Popen(
        [sys.executable, "-c", _child_code(module), *sys.argv[1:]],
        env=dict(os.environ),
        start_new_session=(os.name == "posix"),
    )
    stable_signature: tuple[int, int] | None = None
    stable_since: float | None = None
    try:
        with _forward_termination_signals(process):
            while True:
                return_code = process.poll()
                if return_code is not None:
                    if return_code == 0 and validator(artifact):
                        _clean_success_exit()
                    raise SystemExit(return_code if return_code != 0 else 3)
                if artifact.is_file():
                    stat = artifact.stat()
                    signature = (int(stat.st_size), int(stat.st_mtime_ns))
                    if require_artifact_change and initial_signature is not None and signature == initial_signature:
                        stable_signature = signature
                        stable_since = None
                    elif signature != stable_signature:
                        stable_signature = signature
                        stable_since = time.monotonic()
                    elif stable_since is not None and time.monotonic() - stable_since >= stable_seconds:
                        if validator(artifact):
                            _terminate_child(process)
                            _clean_success_exit()
                time.sleep(0.2)
    finally:
        # Covers exceptions and non-interactive termination paths.  Normal
        # successful completion uses os._exit only after _terminate_child().
        if process.poll() is None:
            _terminate_child(process)


def _eval_with_completion_watch() -> None:
    """Run MACE evaluation and accept a complete output even if MACE lingers.

    MACE 0.3.16 can finish writing the requested extended-XYZ file while a
    PyTorch runtime thread keeps the interpreter alive indefinitely.  The
    wrapper therefore runs MACE in a separate process, independently validates
    the exact expected output count and finite prediction fields, then
    terminates the lingering child process group and exits successfully.
    """

    configs_value = _argument_value("--configs")
    output_value = _argument_value("--output")
    if configs_value is None or output_value is None:
        # Preserve ordinary MACE argument errors for unsupported invocation.
        _dispatch("eval")
        return
    configs = Path(configs_value).expanduser().resolve()
    output = Path(output_value).expanduser().resolve()
    expected_count = _configuration_count(configs)
    require_stress = "--compute_stress" in sys.argv[1:]
    _run_child_until_artifact(
        "eval",
        artifact=output,
        validator=lambda path: _valid_eval_output(
            path, expected_count=expected_count, require_stress=require_stress
        ),
    )


def _select_head_with_completion_watch() -> None:
    output_value = _argument_value("--output_file")
    if output_value is None:
        _dispatch("select-head")
        return
    _run_child_until_artifact(
        "select-head",
        artifact=Path(output_value).expanduser().resolve(),
        validator=_valid_mace_model,
    )


def _train_output_paths() -> tuple[Path, Path]:
    config_value = _argument_value("--config")
    config: dict[str, object] = {}
    if config_value is not None:
        try:
            import yaml

            loaded = yaml.safe_load(Path(config_value).read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config = loaded
        except Exception:
            config = {}
    name = _argument_value("--name") or str(config.get("name", "MACE_model"))
    model_dir_value = _argument_value("--model_dir") or str(config.get("model_dir", "./"))
    checkpoint_dir_value = _argument_value("--checkpoints_dir") or str(
        config.get("checkpoints_dir", "./checkpoints")
    )
    model_dir = Path(model_dir_value).expanduser()
    checkpoint_dir = Path(checkpoint_dir_value).expanduser()
    if not model_dir.is_absolute():
        model_dir = Path.cwd() / model_dir
    if not checkpoint_dir.is_absolute():
        checkpoint_dir = Path.cwd() / checkpoint_dir
    return (model_dir.resolve() / f"{name}.model", checkpoint_dir.resolve())


def _train_with_completion_watch() -> None:
    model_path, checkpoint_dir = _train_output_paths()

    def valid(path: Path) -> bool:
        if not _valid_mace_model(path):
            return False
        return checkpoint_dir.is_dir() and any(
            item.is_file() for pattern in ("*.pt", "*.model") for item in checkpoint_dir.rglob(pattern)
        )

    _run_child_until_artifact(
        "train",
        artifact=model_path,
        validator=valid,
        stable_seconds=2.0,
        require_artifact_change=("--restart_latest" in sys.argv[1:]),
    )


def train_main() -> None:
    _train_with_completion_watch()


def eval_main() -> None:
    _eval_with_completion_watch()


def select_head_main() -> None:
    _select_head_with_completion_watch()


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"train", "eval", "select-head"}:
        raise SystemExit(
            "usage: python -m mdstats.training_data.critical_precision_cli "
            "{train|eval|select-head} [MACE arguments...]"
        )
    command = sys.argv.pop(1)
    _dispatch(command)


if __name__ == "__main__":
    main()
