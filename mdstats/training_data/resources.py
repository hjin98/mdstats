"""Resource-aware parallel execution planning for MLFF campaigns.

The planner is deliberately conservative: it targets a configurable fraction of
CPU threads and currently available RAM/VRAM, then reduces concurrency whenever
per-task memory estimates would exceed those budgets.  It respects Linux CPU
 affinity and cgroup limits when available.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import math
import os
from pathlib import Path
from typing import Any

_GIB = 1024 ** 3


def _read_int(path: str | Path) -> int | None:
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text or text == "max":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _host_available_memory_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    try:
        return int(os.sysconf("SC_AVPHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, ValueError):
        return None


def _cgroup_available_memory_bytes() -> int | None:
    # cgroup v2
    limit = _read_int("/sys/fs/cgroup/memory.max")
    current = _read_int("/sys/fs/cgroup/memory.current")
    if limit is not None and current is not None and limit > current:
        return limit - current
    # cgroup v1
    limit = _read_int("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    current = _read_int("/sys/fs/cgroup/memory/memory.usage_in_bytes")
    if limit is not None and current is not None and limit > current:
        # Ignore the common effectively-unlimited sentinel.
        if limit < (1 << 60):
            return limit - current
    return None


def available_memory_bytes() -> int | None:
    values = [value for value in (_host_available_memory_bytes(), _cgroup_available_memory_bytes()) if value is not None]
    return None if not values else min(values)


def _cgroup_cpu_quota_threads() -> int | None:
    try:
        text = Path("/sys/fs/cgroup/cpu.max").read_text(encoding="utf-8").strip()
        quota_text, period_text = text.split()[:2]
        if quota_text != "max":
            quota = int(quota_text)
            period = int(period_text)
            if quota > 0 and period > 0:
                return max(1, math.ceil(quota / period))
    except (OSError, ValueError, IndexError):
        pass
    quota = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period = _read_int("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota is not None and period is not None and quota > 0 and period > 0:
        return max(1, math.ceil(quota / period))
    return None


def available_cpu_threads() -> int:
    candidates: list[int] = []
    count = os.cpu_count()
    if count:
        candidates.append(int(count))
    try:
        candidates.append(len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    quota = _cgroup_cpu_quota_threads()
    if quota is not None:
        candidates.append(quota)
    return max(1, min(candidates) if candidates else 1)


def _fraction(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not (0.0 < result <= 1.0):
        raise ValueError(f"{name} must be in (0, 1].")
    return result


@dataclass(frozen=True, slots=True)
class GpuResourceSnapshot:
    available: bool
    device_count: int
    selected_device: int | None
    device_name: str | None
    free_bytes: int | None
    total_bytes: int | None
    budget_bytes: int | None
    reason: str


@dataclass(frozen=True, slots=True)
class SystemResourceSnapshot:
    cpu_threads_available: int
    cpu_fraction: float
    cpu_threads_budget: int
    ram_available_bytes: int | None
    ram_fraction: float
    ram_budget_bytes: int | None
    gpu_memory_fraction: float
    gpu: GpuResourceSnapshot

    def summary(self) -> str:
        ram = "unknown" if self.ram_available_bytes is None else f"{self.ram_available_bytes / _GIB:.1f} GiB available / {self.ram_budget_bytes / _GIB:.1f} GiB budget"
        if (
            self.gpu.available
            and self.gpu.free_bytes is not None
            and self.gpu.budget_bytes is not None
        ):
            gpu = (
                f"{self.gpu.device_name or 'CUDA device'}; "
                f"{self.gpu.free_bytes / _GIB:.1f} GiB free / "
                f"{self.gpu.budget_bytes / _GIB:.1f} GiB budget"
            )
        else:
            gpu = self.gpu.reason
        return (
            f"CPU {self.cpu_threads_budget}/{self.cpu_threads_available} threads; "
            f"RAM {ram}; GPU {gpu}"
        )



@dataclass(frozen=True, slots=True)
class StageResourceScope:
    """Execution-only nested-parallelism budget for one pipeline stage.

    The scope is deliberately excluded from scientific records.  It prevents
    independently reasonable worker settings from multiplying into CPU
    oversubscription when Python/process, structural, native-tree, BLAS, explicit
    OpenMP, or PyTorch layers are nested.
    """

    stage_name: str
    cpu_threads_available: int
    cpu_threads_budget: int
    python_workers: int = 1
    structural_workers: int = 1
    tree_workers: int = 1
    blas_threads: int = 1
    native_openmp_threads: int = 1
    pytorch_cpu_workers: int = 1
    gpu_jobs: int = 0
    ram_budget_bytes: int | None = None

    def __post_init__(self) -> None:
        if not str(self.stage_name).strip():
            raise ValueError("stage_name must be non-empty")
        for name in (
            "cpu_threads_available", "cpu_threads_budget", "python_workers",
            "structural_workers", "tree_workers", "blas_threads",
            "native_openmp_threads", "pytorch_cpu_workers",
        ):
            if int(getattr(self, name)) <= 0:
                raise ValueError(f"{name} must be positive")
        if int(self.gpu_jobs) < 0:
            raise ValueError("gpu_jobs must be nonnegative")
        if self.ram_budget_bytes is not None and int(self.ram_budget_bytes) <= 0:
            raise ValueError("ram_budget_bytes must be positive when supplied")
        if self.cpu_threads_budget > self.cpu_threads_available:
            raise ValueError("cpu_threads_budget cannot exceed cpu_threads_available")
        if self.estimated_nested_cpu_threads > self.cpu_threads_budget:
            raise ValueError(
                f"stage {self.stage_name!r} requests approximately "
                f"{self.estimated_nested_cpu_threads} nested CPU threads but "
                f"the stage budget is {self.cpu_threads_budget}"
            )

    @property
    def estimated_nested_cpu_threads(self) -> int:
        inner = max(
            int(self.structural_workers) * int(self.blas_threads),
            int(self.tree_workers),
            int(self.native_openmp_threads),
            int(self.pytorch_cpu_workers),
            1,
        )
        return int(self.python_workers) * inner

    def summary(self) -> str:
        return (
            f"{self.stage_name}: cpu={self.estimated_nested_cpu_threads}/"
            f"{self.cpu_threads_budget} budget; python={self.python_workers}; "
            f"structure={self.structural_workers}; tree={self.tree_workers}; "
            f"blas={self.blas_threads}; openmp={self.native_openmp_threads}; "
            f"torch={self.pytorch_cpu_workers}; "
            f"gpu_jobs={self.gpu_jobs}; "
            f"ram_budget={'unbounded' if self.ram_budget_bytes is None else int(self.ram_budget_bytes)}"
        )


def build_stage_resource_scope(
    resources: SystemResourceSnapshot,
    *,
    stage_name: str,
    python_workers: int = 1,
    structural_workers: int = 1,
    tree_workers: int = 1,
    blas_threads: int = 1,
    native_openmp_threads: int = 1,
    pytorch_cpu_workers: int = 1,
    gpu_jobs: int = 0,
    ram_budget_bytes: int | None = None,
) -> StageResourceScope:
    """Build and validate one execution-only stage resource scope."""

    return StageResourceScope(
        stage_name=str(stage_name),
        cpu_threads_available=int(resources.cpu_threads_available),
        cpu_threads_budget=int(resources.cpu_threads_budget),
        python_workers=int(python_workers),
        structural_workers=int(structural_workers),
        tree_workers=int(tree_workers),
        blas_threads=int(blas_threads),
        native_openmp_threads=int(native_openmp_threads),
        pytorch_cpu_workers=int(pytorch_cpu_workers),
        gpu_jobs=int(gpu_jobs),
        ram_budget_bytes=(
            resources.ram_budget_bytes if ram_budget_bytes is None else int(ram_budget_bytes)
        ),
    )


@contextmanager
def stage_resource_scope(scope: StageResourceScope):
    """Apply practical process-wide native-thread limits for one stage.

    ``threadpoolctl`` covers BLAS/OpenMP libraries that support runtime limits.
    cKDTree/Python/PyTorch worker counts remain explicit caller parameters and
    are validated by :class:`StageResourceScope`.
    """

    if not isinstance(scope, StageResourceScope):
        raise TypeError("scope must be a StageResourceScope")
    try:
        from threadpoolctl import threadpool_limits
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        yield scope
        return
    # BLAS and OpenMP are independent nesting dimensions.  Limit them
    # separately so a stage using an explicit native OpenMP team does not have
    # to masquerade as Python-worker parallelism or inherit a BLAS limit.
    with threadpool_limits(limits=int(scope.blas_threads), user_api="blas"):
        with threadpool_limits(limits=int(scope.native_openmp_threads), user_api="openmp"):
            yield scope

def detect_gpu_resources(*, memory_fraction: float = 0.9, device: str = "cuda") -> GpuResourceSnapshot:
    fraction = _fraction(memory_fraction, name="gpu_memory_fraction")
    if not str(device).startswith("cuda"):
        return GpuResourceSnapshot(False, 0, None, None, None, None, None, f"device={device}")
    try:
        import torch
    except ModuleNotFoundError:
        return GpuResourceSnapshot(False, 0, None, None, None, None, None, "torch unavailable")
    if not torch.cuda.is_available():
        return GpuResourceSnapshot(False, int(torch.cuda.device_count()), None, None, None, None, None, "CUDA unavailable")
    selected = 0
    if ":" in str(device):
        try:
            selected = int(str(device).split(":", 1)[1])
        except ValueError:
            selected = 0
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info(selected)
        name = torch.cuda.get_device_name(selected)
    except Exception as exc:  # pragma: no cover - hardware dependent
        return GpuResourceSnapshot(True, int(torch.cuda.device_count()), selected, None, None, None, None, f"CUDA present; memory probe failed: {exc}")
    return GpuResourceSnapshot(
        True,
        int(torch.cuda.device_count()),
        selected,
        str(name),
        int(free_bytes),
        int(total_bytes),
        int(float(free_bytes) * fraction),
        "available",
    )


def detect_system_resources(
    *,
    cpu_fraction: float = 0.9,
    ram_fraction: float = 0.8,
    gpu_memory_fraction: float = 0.9,
    device: str = "cuda",
) -> SystemResourceSnapshot:
    cpu_fraction = _fraction(cpu_fraction, name="cpu_fraction")
    ram_fraction = _fraction(ram_fraction, name="ram_fraction")
    gpu_memory_fraction = _fraction(gpu_memory_fraction, name="gpu_memory_fraction")
    cpu_available = available_cpu_threads()
    cpu_budget = max(1, int(math.floor(cpu_available * cpu_fraction)))
    ram_available = available_memory_bytes()
    ram_budget = None if ram_available is None else max(1, int(ram_available * ram_fraction))
    return SystemResourceSnapshot(
        cpu_threads_available=cpu_available,
        cpu_fraction=cpu_fraction,
        cpu_threads_budget=cpu_budget,
        ram_available_bytes=ram_available,
        ram_fraction=ram_fraction,
        ram_budget_bytes=ram_budget,
        gpu_memory_fraction=gpu_memory_fraction,
        gpu=detect_gpu_resources(memory_fraction=gpu_memory_fraction, device=device),
    )


def resolve_worker_count(
    *,
    task_count: int,
    resources: SystemResourceSnapshot,
    requested: int = 0,
    estimated_bytes_per_worker: int | None = None,
    reserved_bytes: int = 0,
    maximum_workers: int | None = None,
) -> int:
    if task_count <= 0:
        return 0
    if requested < 0:
        raise ValueError("requested worker count must be zero (auto) or positive")
    # Explicit worker settings are stage caps inside the campaign-wide CPU
    # fraction.  The only supported way to authorize more host CPU capacity is
    # to change cpu_fraction itself; a stage override must never bypass it.
    cpu_limit = resources.cpu_threads_budget if requested == 0 else min(requested, resources.cpu_threads_budget)
    if reserved_bytes < 0:
        raise ValueError("reserved_bytes must be non-negative")
    memory_limit = task_count
    if (
        estimated_bytes_per_worker is not None
        and estimated_bytes_per_worker > 0
        and resources.ram_budget_bytes is not None
    ):
        worker_budget = max(0, int(resources.ram_budget_bytes) - int(reserved_bytes))
        # Keep one worker available so the stage can make progress even when the
        # persistent parent-side result is already close to the configured RAM
        # budget. The stage-level caller reports this constrained condition.
        memory_limit = max(1, worker_budget // int(estimated_bytes_per_worker))
    limits = [task_count, max(1, cpu_limit), max(1, memory_limit)]
    if maximum_workers is not None and maximum_workers > 0:
        limits.append(maximum_workers)
    return max(1, min(limits))


def configure_worker_thread_environment(env: dict[str, str], *, threads: int = 1) -> dict[str, str]:
    """Prevent nested BLAS/OpenMP oversubscription inside process workers."""
    result = dict(env)
    value = str(max(1, int(threads)))
    for key in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    ):
        result[key] = value
    return result

_PROCESS_THREADPOOL_LIMITER: Any | None = None


def initialize_process_worker() -> None:
    """Initialize a CPU worker without nested BLAS/OpenMP oversubscription."""

    global _PROCESS_THREADPOOL_LIMITER
    value = "1"
    for key in (
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
    ):
        os.environ[key] = value
    try:
        from threadpoolctl import threadpool_limits
    except ModuleNotFoundError:  # pragma: no cover
        return
    _PROCESS_THREADPOOL_LIMITER = threadpool_limits(limits=1)
    _PROCESS_THREADPOOL_LIMITER.__enter__()


def process_pool_context():
    """Prefer copy-on-write fork on Linux; retain a portable fallback."""

    import multiprocessing as mp

    methods = mp.get_all_start_methods()
    return mp.get_context("fork" if "fork" in methods else methods[0])


def bounded_process_map(function: Any, tasks: Any, *, workers: int):
    """Yield process results with at most ``workers`` submitted tasks.

    This backpressure prevents the executor feeder thread from serializing an
    entire large trajectory corpus into its work queue at once.
    """

    from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

    iterator = iter(tasks)
    with ProcessPoolExecutor(
        max_workers=max(1, int(workers)),
        mp_context=process_pool_context(),
        initializer=initialize_process_worker,
    ) as executor:
        pending: dict[Any, None] = {}
        for _ in range(max(1, int(workers))):
            try:
                task = next(iterator)
            except StopIteration:
                break
            pending[executor.submit(function, task)] = None
        while pending:
            done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in done:
                pending.pop(future, None)
                yield future.result()
                try:
                    task = next(iterator)
                except StopIteration:
                    continue
                pending[executor.submit(function, task)] = None


def isolated_process_map(
    module: str,
    function: str,
    tasks: Any,
    *,
    workers: int,
    scratch_directory: str | Path | None = None,
    cpu_only: bool = False,
):
    """Yield one-shot subprocess results with bounded concurrency and disk backpressure."""

    import pickle
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    parent = None if scratch_directory is None else Path(scratch_directory)
    if parent is not None:
        parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="mdstats-feature-", dir=parent))
    iterator = enumerate(tasks)
    active: dict[Any, dict[str, Any]] = {}
    limit = max(1, int(workers))
    environment = configure_worker_thread_environment(dict(os.environ), threads=1)
    if cpu_only:
        # Fresh-interpreter CPU phases must not initialize or reserve accelerator
        # state inherited conceptually from an earlier GPU stage.
        environment["CUDA_VISIBLE_DEVICES"] = ""
    package_root = str(Path(__file__).resolve().parents[2])
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = (
        package_root if not existing_pythonpath
        else package_root + os.pathsep + existing_pythonpath
    )

    def launch(index: int, task: Any) -> None:
        input_path = root / f"task-{index:06d}.pkl"
        output_path = root / f"result-{index:06d}.pkl"
        stderr_path = root / f"task-{index:06d}.stderr.log"
        array_directory = input_path.with_suffix(".arrays")
        from ._array_pickle import dump_with_array_references
        with input_path.open("wb") as handle:
            dump_with_array_references(
                task, handle, array_directory=array_directory
            )
        stderr_handle = stderr_path.open("wb")
        process = subprocess.Popen(
            (
                sys.executable,
                "-m", "mdstats.training_data.feature_worker",
                "--module", module,
                "--function", function,
                "--input", str(input_path),
                "--output", str(output_path),
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr_handle,
            env=environment,
        )
        active[process] = {
            "index": index,
            "input": input_path,
            "output": output_path,
            "stderr": stderr_path,
            "stderr_handle": stderr_handle,
            "array_directory": array_directory,
        }

    try:
        for _ in range(limit):
            try:
                index, task = next(iterator)
            except StopIteration:
                break
            launch(index, task)
        while active:
            completed = []
            for process, item in tuple(active.items()):
                return_code = process.poll()
                if return_code is None:
                    continue
                item["stderr_handle"].close()
                if return_code != 0 or not item["output"].is_file():
                    message = item["stderr"].read_text(encoding="utf-8", errors="replace")[-6000:]
                    raise RuntimeError(
                        f"Isolated feature worker {item['index']} failed with exit code "
                        f"{return_code}:\n{message}"
                    )
                with item["output"].open("rb") as handle:
                    result = pickle.load(handle)
                completed.append((process, result, item))
            if not completed:
                time.sleep(0.05)
                continue
            for process, result, item in completed:
                active.pop(process, None)
                item["input"].unlink(missing_ok=True)
                item["output"].unlink(missing_ok=True)
                item["stderr"].unlink(missing_ok=True)
                shutil.rmtree(item["array_directory"], ignore_errors=True)
                yield result
                try:
                    index, task = next(iterator)
                except StopIteration:
                    continue
                launch(index, task)
    finally:
        for process, item in active.items():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
            try:
                item["stderr_handle"].close()
            except Exception:
                pass
        shutil.rmtree(root, ignore_errors=True)
