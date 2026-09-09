# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_WORKPLAN.md`

Its binding Protocol 6 implementation-review amendments are:

- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_REVIEW_REOPEN.md`
- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_PROGRESS_RECOVERY_AMENDMENT.md`
- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_SCHEDULER_ARCHITECTURE_AMENDMENT.md`

The implementation review of candidate `41fd1cf0643fb7f42a8423c22368b2283f9176de` remains **NO-PASS / REOPENED**. The original identity-domain correction is directionally accepted: target execution remains exact on target `frame_uid`, canonical single-source replay can use its existing geometry identity, mixed replay identity domains fail closed, and no new durable replay identity/registry/migration/state machinery was added.

The candidate still has an avoidable replay-I/O regression: the complete replay ExtXYZ is reparsed in the parent P5 authority path and again in the child membership adapter after MACE has loaded it. The prior review amendment requires reuse of existing replay/split authority and MACE-loaded geometry instead of multiplying full-corpus scans across the CV run matrix.

Target-host runtime evidence proved that the apparent post-freeze `cross-validate` hang was healthy live MACE training. The current P5 trainer hides that activity because it launches MACE through blocking `subprocess.run(..., capture_output=True)`. The progress-recovery amendment therefore restores mdstats's qualified historical TRAIN supervision/reporting contract: exact gradient-update progress from MACE's append-only metrics stream, phase visibility, optional GPU/VRAM telemetry, responsive control polling, visible updates controlled by `[execution].training_progress_interval_seconds` (default 10 seconds), and the canonical 0.20.237 progress grammar. Both `cross-validate` and `train-production` must use the recovered reporter.

A second historical execution-control regression is now explicit: `training_parallel.py`, `TrainingConcurrencyPolicy`, `AdaptiveTrainingConcurrency`, NVML/`nvidia-smi` telemetry, configuration knobs, and scheduler tests survived the V7 cutover, but current P5 orchestration no longer constructs or consumes that scheduler. The scheduler/architecture amendment requires rewiring the **existing** adaptive GPU-utilization/VRAM scheduler into both post-selection CV training jobs and final-production training jobs. CUDA auto mode starts one true job and may admit additional independent jobs only after sustained real optimizer activity and safe projected GPU utilization, VRAM, CPU, and RAM. Completion order remains non-authoritative; scientific reductions/publication retain canonical plan order. The scheduler and TRAIN reporter should share live child activity and GPU telemetry rather than create duplicate pollers.

The latest target-host run also exposed a fail-closed checkpoint-authentication error after training: `Candidate MACE configuration reconstructs a different execution architecture from the authenticated TRAIN2 model.` The architecture guard must remain. The amendment requires a complete TRAIN2-versus-reconstruction construction census and closes two concrete drift vectors: (1) phase-separated `training_backend=cueq`, `only_cueq=false` converts the live TRAIN2 model to CuEq before raw checkpoint/runtime-summary persistence while EVAL2 independently reconstructs the portable e3nn configuration; and (2) P5 does not currently force model-affecting `avg_num_neighbors` to the frozen method value, so pinned MACE may derive it from fold-local training data. The repair must authenticate raw TRAIN2 state against the exact configured training realization, then use existing MACE acceleration/conversion authority to expose the authorized portable e3nn provider when required, while keeping real model-field drift fail-closed.

Existing failed-workspace evidence must be classified before deletion/retraining. An otherwise-authorized transient CuEq/e3nn realization mismatch may reuse the authenticated TRAIN2 checkpoint after correct reconstruction/conversion. A checkpoint that actually trained with a different model-affecting normalization/head/topology than the frozen P5 method must be preserved but rejected/recomputed, not migrated or blessed.

The work remains governed by **Scientific Software Development Protocol 6.0.0** as a bounded D4 repair beneath unchanged accepted D3 replay/P5/TRAIN2/MACE architecture. No Serious Challenge is active.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Planning base and previously accepted executable:

- closeout/planning base: `9abb2b89930b48d9e2771addb5f59879bfec1001`
- executable baseline containing the original identity defect: `13859556cd4d472837a9e171c2be32e59d5e6d82`

The prior downstream-integration closure remains archived and is not reopened wholesale:

- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_FINAL_REVIEW.md`

Full long-running real-data/GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the final release qualification package. A tiny bounded CuEq functional reproduction may be used only to close the concrete checkpoint-realization bug where the qualified stack is already available; it is not accelerator-performance/release qualification.
