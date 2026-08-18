# mdstats 0.20.86a0 patch notes

## Adaptive parallel evaluation and verification

- Added campaign-wide resource-aware parallel checkpoint evaluation across runs and checkpoints.
- Added resource-aware parallel bounded NVE verification.
- Added distinct CUDA streams for admitted independent inference jobs.
- Normalized CPU telemetry to process affinity and effective cgroup/scheduler capacity.
- CUDA inference starts with one job and adds jobs only when projected aggregate
  VRAM and GPU utilization both remain below 90%.
- CPU inference uses bounded outer jobs with a projected 90% host-utilization
  ceiling.
- RAM remains limited to 80% of currently available memory.
- Added shared and phase-specific runtime configuration controls.
- Prevented duplicate concurrent monitor parsing and foundation-baseline inference.
- Ensured every parallel verification case owns a private mutable MACE calculator.
- Kept 0.20.85a0 verification-case cache identity compatible because scheduling
  does not alter the scientific NVE calculation.

## Resource-default revision

- Changed MLFF CPU planning defaults from 80% to 90%.
- Changed MLFF GPU/VRAM planning defaults from 80% to 90%.
- Kept RAM planning at 80%.
- Updated structural-selection automatic CPU planning to 90%.
- Updated atomic-density/framework-rendering CPU thread defaults from 80% to 90%; memory remains 80%.

## Compatibility

- Existing TOMLs remain valid.
- Explicit resource fractions in existing TOMLs are honored.
- Existing evaluation records retain their original scientific cache identity.
- Existing verification cases remain reusable when model, structure, integration,
  acceleration, and dependency identities are unchanged.
