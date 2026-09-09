# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_WORKPLAN.md`

Its binding Protocol 6 implementation-review amendments are:

- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_REVIEW_REOPEN.md`
- `workplans/active/MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_PROGRESS_RECOVERY_AMENDMENT.md`

The implementation review of candidate `41fd1cf0643fb7f42a8423c22368b2283f9176de` remains **NO-PASS / REOPENED**. The original identity-domain correction is directionally accepted: target execution remains exact on target `frame_uid`, canonical single-source replay can use its existing geometry identity, mixed replay identity domains fail closed, and no new durable replay identity/registry/migration/state machinery was added.

The candidate is not yet acceptable because its execution realization reparses the complete replay ExtXYZ in the parent P5 authority path and reparses it again in the child MACE membership adapter after MACE has already loaded the data. Those redundant corpus-wide scans sit inside the CV seed/fold run matrix and are not represented by the tiny new fixtures.

Target-host runtime evidence additionally proved that the apparent post-freeze `cross-validate` hang was in fact a healthy live MACE training child: the child was appending optimizer/evaluation records to `results/*_train.txt` at epoch 5. The current P5 trainer hides that activity because it launches MACE through blocking `subprocess.run(..., capture_output=True)` and therefore bypasses mdstats's historical supervised MACE progress path.

The progress-recovery amendment restores the established reporting contract rather than inventing a new dialect: MACE metrics-file probing with exact completed/total gradient-update percentage, current MACE phase, optional GPU/VRAM telemetry, responsive control polling, visible updates controlled by `[execution].training_progress_interval_seconds` (default 10 seconds), and the canonical 0.20.237 MLFF grammar (`status; progress; elapsed; eta; rates; telemetry`, fixed `HH:MM:SS`, `--:--:--` until ETA is known). P5 `cross-validate` must also expose N/seed/fold run-matrix context and restored-versus-executing state.

The binding review amendments therefore require: removal of avoidable replay reparsing using already-authenticated replay source/split authority and, where exact equivalence is established, geometry retained by MACE's loaded `Configuration`; recovery/rewiring of the existing supervised TRAIN progress behavior rather than raw stdout or a new daemon; missing replay-mutation/continuation counterfactuals; multi-size real-owner coverage; and actual execution of the final affected regression/integration/static surface.

The work remains governed by **Scientific Software Development Protocol 6.0.0** as a bounded D4 repair beneath unchanged accepted D3 replay/MACE architecture. No Serious Challenge is active.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Planning base and previously accepted executable:

- closeout/planning base: `9abb2b89930b48d9e2771addb5f59879bfec1001`
- executable baseline containing the original identity defect: `13859556cd4d472837a9e171c2be32e59d5e6d82`

The prior downstream-integration closure remains archived and is not reopened wholesale:

- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_FINAL_REVIEW.md`

Full long-running real-data/GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the final release qualification package.
