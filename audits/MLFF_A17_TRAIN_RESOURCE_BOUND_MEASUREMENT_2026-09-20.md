# A17 TRAIN2 per-job resource bound - real-child measurement record

**Date:** 2026-09-20
**Workplan:** `workplans/active/MLFF_PRODUCTION_GLOBAL_TRAIN_SCHEDULER_REPAIR_WORKPLAN.md`, section 12.2-12.4 (R2A/R2B/R2C)
**Repository candidate:** `ac9ede33cfda410b45500b30070449ceede28811`

This record exists because the previous A17 host-RAM proof compared
`target_train.extxyz.stat().st_size` with `plan.estimated_ram_bytes_per_job`.
A serialized transport size is not a bound on the resident memory of the MACE
process, so that proof was withdrawn and replaced with the measurements below.

**This is not a physical GPU qualification.** The measurement host is a
development machine, not the production target device. The device numbers here
are used only as a resource *bound* for the D4 admission contract; final
target-hardware throughput/VRAM qualification remains deferred to the release
package.

## 1. What was measured

The peak resident host memory, and the peak device memory, of one real
`mdstats-mace-train` child - the exact P5/MACE child boundary that
`post_selection_execution.PostSelectionRungRequest` execution spawns with
`subprocess.Popen` - over two materially representative TRAIN_REQUIRED
production memberships.

No product code was instrumented. The harness is external: it spawns the
unmodified wrapper entry point and samples `/proc/<pid>/status` for the whole
owned process tree, using the kernel `VmHWM` high-water mark as the second
witness that no excursion between samples was missed.

## 2. Pinned runtime and realization

Taken verbatim from the live campaign's own P5 materialization at
`~/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/.r3-backup-2026-09-13/post-selection/g1/runs/262e6674.../materialization/mace_run_config.yaml`.

| Fact | Value |
| --- | --- |
| MACE | 0.3.16 (`mace.cli.run_train`) |
| torch | 2.13.0+cu126 |
| wrapper | `mdstats-mace-train` -> `mdstats.training_data.critical_precision_cli:train_main` |
| critical-precision policy | `scaleshift_mace_0.3.16_runtime_patch_v1` (the wrapper default with no policy in the environment; the FP64 critical-accumulation variant, i.e. the memory-heavier of the two policies, so the measurement is conservative for the campaign's `single` profile) |
| model | `MACE`, foundation `mace-mpa-0-medium.model`, multiheads finetuning (`pt_head` + `target_head`) |
| parameters / buffers | 9,063,204 / 837,453 -> 34.6 MiB + 3.2 MiB fp32 |
| precision | `default_dtype: float32` |
| batch / valid batch | 2 / 2 |
| loader workers | `num_workers: 0` (no loader subprocesses; measured `nproc_max == 1`) |
| acceleration | `enable_cueq: true`, `only_cueq: false` |
| optimizer | `amsgrad: true`, `ema: true` (`ema_decay 0.99999`), `swa` not configured |
| graph cutoff | `r_max: 5.0`, `apply_cutoff: true`, `compute_avg_num_neighbors: false` |
| replay | `pt_train_file`/`pt_valid_file` = the campaign's true-label replay views; MACE caps the replay head at `num_samples_pt = 10000` train / 2000 valid, independent of `N` |
| horizon | one true training epoch each (`max_num_epochs: 1`) |

## 3. Membership geometry envelope

Every one of the 27 source VASP runs in `04_training_dataset/LTA` has exactly
**168 atoms**. Per-configuration geometry over the whole prepared frame pool
(2,007 real production configurations, measured at `r_max = 5.0`):

| Quantity | Value |
| --- | --- |
| atoms per configuration | 168 (min = max) |
| neighbour-list edges per configuration | 4,232 - 4,956 (mean 4,523) |
| cell volume | 3,391.7 - 3,779.2 A^3 |

`N` therefore buys *more* configurations, never larger or denser ones. The
maximum per-sample geometry is a pool-wide constant that every membership at
every `N` shares, so a common batch-geometry envelope exists by construction.

The measured memberships were built from the densest real configurations
(cycling the pool where `N` exceeds it), so each membership's geometry sits at
or above the pool maximum:

| Membership | unique real configs | edges min / max / mean |
| --- | --- | --- |
| N=512 | 512 | 4,604 / 4,956 / 4,741 |
| N=8192 | 2,007 (cycled) | 4,232 / 4,956 / 4,530 |

## 4. Measurements

Sampled at 4 Hz over the whole child lifetime (dataset parsing and
construction, model/foundation load, one complete true training epoch,
checkpoint and model write, and the post-epoch train/valid evaluation). Each
child was terminated at the same completion boundary the real P5 owner uses -
the `models/<name>.model` artifact - so the measured interval is the interval
the production owner actually owns.

| Membership | samples | peak tree RSS | `VmHWM` | peak device |
| --- | --- | --- | --- | --- |
| N=512 | 6,711 | 7,003.2 MiB | 7,003.2 MiB | 6,152 MiB |
| N=8192 | 3,196 | 9,904.9 MiB | 9,912.0 MiB | 5,154 MiB |

`nproc_max = 1` in both runs, so no simultaneously resident owned
loader/child process exists to add.

### Host RAM scaling

The two points are linear in the configuration count:

```
slope     = (9912 - 7003) / (8192 - 512) = 0.37878 MiB per configuration
intercept = 7003 - 512 * 0.37878         = 6809.1 MiB
```

| N | bound |
| --- | --- |
| 512 | 7,003 MiB (measured) |
| 4096 | 8,361 MiB |
| 8192 | 9,912 MiB (measured) |
| **16384** (configured ladder maximum, `target_size_power_max = 14`) | **13,015 MiB** |

The fixed 6,809 MiB is the framework, foundation model, replay-head dataset
(capped at 10,000 configurations) and CUDA-context term; it does not move with
`N`.

### Device memory scaling

The device peak did **not** grow with `N` - it was *lower* at N=8192 (5,154 MiB)
than at N=512 (6,152 MiB), the difference being caching-allocator reserve
timing. Both sit inside one ~6 GiB envelope. This is the empirical companion to
the source proof in section 5.

## 5. Device-resident state in the pinned realization

Established from the pinned MACE 0.3.16 source, not inferred:

| Device-resident state | Owner | Scaling variables |
| --- | --- | --- |
| model parameters and buffers | `run_train.py:756` `model.to(device)` | model hyperparameters only (37.8 MiB fp32) |
| gradients | autograd | = parameters (34.6 MiB) |
| Adam/AMSGrad optimizer state | `torch.optim` | 3 x parameters (103.7 MiB) |
| EMA shadow | `torch_ema.ExponentialMovingAverage` | 1 x parameters (34.6 MiB) |
| SWA `AveragedModel` | `torch.optim.swa_utils` | **absent** - `--swa` defaults to `False` and the pinned config does not set it |
| one training or validation batch, with its graph/neighbourhood tensors | `tools/train.py:413,490,572` `batch = batch.to(device)` | `batch_size` x (atoms, edges) per configuration |
| forward/backward temporaries | MACE modules | same batch/geometry envelope |
| replay (`pt_head`) state | same model, extra readout head | model hyperparameters; its *data* is CPU-resident and reaches the device only as batches, and its configurations are smaller (10-84 atoms) than the target head's 168 |
| dataset-wide or cached device state | - | **none exists** |

The dataset is a CPU-resident Python list of `AtomicData` built by
`AtomicData.from_config` (`run_train.py:675,997`) and handed to
`torch_geometric.dataloader.DataLoader`; only batches are moved. The two
code paths that would traverse the dataset on the device are both disabled by
the pinned configuration:

* `get_avg_num_neighbors` (`tools/scripts_utils.py:627`) takes the
  `avg_num_neighbors`-supplied branch because `compute_avg_num_neighbors: false`;
* `configure_model` (`tools/model_script_utils.py:55`) short-circuits before any
  `train_loader` statistics pass because `scaling: no_scaling`.

`pin_memory` defaults to `True`, which pins **host** pages per batch; that is a
host cost bounded by batch size, not a device cost and not a function of `N`.

Total persistent device state is therefore **about 211 MiB**, fixed by the
frozen method, and the only task-varying device allocation is bounded by
`batch_size = 2` times the pool-wide per-configuration geometry envelope of
section 3. Neither `N` nor the production horizon `H_prod` appears.

## 6. Consequence for the configured reservations

| Reservation | before | measured bound | after |
| --- | --- | --- | --- |
| `estimated_training_vram_mib_per_job` | 6,144 MiB | 6,152 MiB observed maximum | **8,192 MiB** |
| `estimated_training_ram_mib_per_job` | 8,192 MiB | 13,015 MiB at the ladder maximum | **16,384 MiB** |

Both prior values were non-conservative; the device one was already exceeded at
the *smallest* production size. Both repaired values are **single common
bounds** - no per-size or task-identity-dependent reservation was introduced -
and both keep the existing single `TrainingConcurrencyPlan` usable: on a 24 GiB
device at `training_gpu_memory_fraction = 0.90` the VRAM ceiling is 2 concurrent
jobs, and on the reference host's RAM budget the host ceiling is likewise 2, so
a two-position collection wave still runs concurrently.

## 7. Harness

Evidence-only; deliberately not a repository or product artifact. Reproduce by
writing the following to a scratch directory.

`geometry.py` - pool geometry envelope:

```python
import glob, json, sys
import numpy as np
from ase.io import read
from matscipy.neighbours import neighbour_list as mn

RUNS = ".../post-selection/g1/runs"
frames = []
for path in sorted(glob.glob(f"{RUNS}/*/materialization/target_train.extxyz")):
    frames.extend(read(path, ":"))
rows = [(len(at), len(mn("i", at, 5.0)), float(at.get_volume())) for at in frames]
arr = np.array(rows)
print(json.dumps({"pool": len(frames), "atoms": [int(arr[:,0].min()), int(arr[:,0].max())],
                  "edges": [int(arr[:,1].min()), int(arr[:,1].max())],
                  "edges_mean": float(arr[:,1].mean())}, indent=2))
```

`peak_run.py` - one real child, externally sampled. The essential parts:

```python
cfg = yaml.safe_load((REAL / "mace_run_config.yaml").read_text())   # pinned realization
cfg["max_num_epochs"] = 1
cfg["device"] = "cuda"
(mat / "mace_run_config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))

cmd = [PY, "-m", "mdstats.training_data.critical_precision_cli", "train",
       "--config", "mace_run_config.yaml", "--model_dir", ..., "--checkpoints_dir", ...,
       "--log_dir", ..., "--results_dir", ...]
proc = subprocess.Popen(cmd, cwd=str(mat), env=env, stdin=subprocess.DEVNULL,
                        stdout=so, stderr=se, start_new_session=True)

# sampler thread, 4 Hz, whole owned process tree
for pid in tree(proc.pid):
    rss  += int(VmRSS from /proc/<pid>/status)   # current resident
    hwm  += int(VmHWM from /proc/<pid>/status)   # kernel high-water witness
gpu = max(nvidia-smi --query-compute-apps=used_memory)
```

The target memberships were built by reading the 2,007 real production
configurations, ordering them by descending edge count, and writing the first
`N` (cycling the pool when `N` exceeds it) with `ase.io.write(..., format="extxyz")`.
