# mdstats 0.20.67a0 bounded preflight and live accelerator progress

## Observed behavior

The required real-MACE preflight emitted only a generic heartbeat such as:

```text
[PREFLIGHT training] still running; elapsed=4m00s, stdout=0.0 MiB, stderr=0.0 MiB
```

This did not identify the active CPU/GPU device, did not expose MACE's training
phase, and gave no quantitative progress. More importantly, the nominally
"bounded" one-epoch smoke used the complete final-development target and replay
files. With roughly 9,934 replay configurations and batch size 2, the smoke
could perform thousands of gradient updates before production training began.

## Correction

- Preflight now creates deterministic temporary extxyz subsets from the already
  verified DATA8 files. Defaults are 32 target-train, 8 target-valid,
  64 replay-train, and 8 replay-valid configurations.
- Target sampling extends beyond the nominal cap only when needed to cover every
  atomic number declared by `target_head`; the production DATA8 tree is never
  modified.
- The smoke configuration still exercises real MACE graph construction,
  multi-head loading, loss/backpropagation, checkpoint export, target-head
  extraction, and finite stress-enabled evaluation.
- The preflight launch line reports the exact resolved device, GPU model and
  memory, dtype, and e3nn/cuEquivariance backend.
- Heartbeats parse MACE's append-only metrics file and report exact completed
  gradient updates and percentage. They also report the current MACE phase and,
  when available, `nvidia-smi` GPU utilization and VRAM use.
- Production `train` heartbeats use the same exact update counter across all
  configured epochs.
- Generic subprocess heartbeats no longer say only "still running"; they use a
  compact elapsed/phase format.
- Interrupting the patched preflight terminates its detached MACE process group
  before propagating `KeyboardInterrupt`, preventing orphan GPU workers.

## GPU policy

The campaign remains protocol-frozen: MACE receives `[training].device`
explicitly. A campaign initialized on a CUDA-capable workstation normally has
`device = "cuda"`, and both preflight and production training therefore run on
the GPU. mdstats does not silently change a frozen CPU campaign to CUDA because
that would make the preflight environment differ from the recorded DATA8
training protocol. The new launch line makes this choice unambiguous.

## Restart behavior

This release does not change DATA8 identity or any prepared scientific artifact.
Install the wheel, stop the old preflight child if it is still running, and run
`preflight` again. Do not rerun `prepare`.

```bash
python -m pip install --force-reinstall --no-deps \
    dist/mdstats-0.20.67a0-py3-none-any.whl
python tools/mdstats-mlff-campaign.py --config campaign.toml preflight
```

Existing campaign defaults need no TOML edit. Optional bounds can be added under
`[preflight]`:

```toml
target_train_configurations = 32
target_valid_configurations = 8
replay_train_configurations = 64
replay_valid_configurations = 8
```
