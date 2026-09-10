# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

## Current MLFF implementation entrypoint

There is one current Protocol 6 implementation handoff:

- `workplans/active/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

`workplans/active/CURRENT_IMPLEMENTATION_ENTRYPOINT.md` points to the same file. Earlier replay-membership, review-reopen, progress-recovery, and scheduler/architecture workplans/amendments remain provenance only and are not separate implementation stages.

### Current independent review state

Executable candidate `577908bf117d033357e2bfb1847e5ed16047d288` is **NO-PASS / REOPENED** after independent SSDP 6 Software Design review. No Serious Challenge is active; D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE plus serial selected-size architecture remain unchanged.

The implementation closes the prior scheduler-source defects: task liveness now comes from active futures rather than human-readable MACE phase, and true-epoch readiness now uses current training phase plus bounded fresh optimizer activity under the existing activity-timeout control. Current single-source replay also selects the canonical replay identity domain once and no longer enters legacy/file-reread fallback on a canonical mismatch. Preserve those corrections.

Remaining blockers are narrower:

1. the canonical replay representation-equivalence test manually constructs `mace.data.Configuration`; it must instead prove the same identity through MACE's real pinned ExtXYZ/dataset loader for periodic and non-periodic fixtures;
2. the pre-fix TRAIN2 recovery tests currently rewrite the historical summary/companion to inject `model_architecture_digest`; real-owner acceptance must obtain the decisive architecture from authentic TRAIN2/MACE persistence/checkpoint evidence without rewriting history;
3. an authentic architecture-different pre-fix run currently raises a preserved recovery error on every retry, so the required bounded replacement/recompute of only that classified noncurrent run is not yet operationally reachable;
4. final focused/affected regression, integration, real-owner, lint/type/static, and structural evidence must execute on one unchanged candidate. GitHub currently exposes no check-runs/statuses for the reviewed candidate.

Repair only those boundaries. Do not rework the scheduler, introduce cross-size scheduling, add a compatibility database/migration framework, or create another replay/checkpoint/recovery authority.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Full production-scale GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the complete final release package. Tiny real MACE/CuEq functional boundary tests needed for concrete bug closure are implementation evidence, not production qualification.