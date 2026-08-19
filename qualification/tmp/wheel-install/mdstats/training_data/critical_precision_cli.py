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
