# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

## Current MLFF implementation entrypoint

There is one current Protocol 6 implementation handoff:

- `workplans/active/MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

`workplans/active/CURRENT_IMPLEMENTATION_ENTRYPOINT.md` points to the same file. Earlier replay-membership, review-reopen, progress-recovery, and scheduler/architecture amendments remain provenance only.

### Current independent review state

Executable candidate `dadb83e680032a30fe55b42baf77bf13538f94a7` is **NO-PASS / REOPENED** after independent SSDP Protocol 6 Software Design review. No Serious Challenge is active; D1 scientific formulation, D2 numerical method, and accepted D3 replay/P5/TRAIN2/MACE plus serial selected-size architecture remain unchanged.

Source/conformance corrections now accepted and to be preserved:

- append-only MACE optimizer metrics count every newly consumed complete `mode="opt"` line, including byte/content-identical consecutive rows;
- scheduler liveness comes from active futures and readiness uses current training phase plus bounded fresh optimizer activity;
- selected sizes remain serial;
- current single-source replay selects canonical loaded-geometry identity once and cannot enter legacy/file-reread fallback on mismatch;
- immediately-pre-fix continuation classification uses persisted actual TRAIN2 architecture rather than today's interpretation of a missing historical key;
- architecture-different exact pre-fix state now has a nominal bounded same-run replacement path instead of raising forever;
- bounded tests now retain the real per-size scheduler, real `MacePostSelectionTrainer`, real metrics observer/process termination owner, and real TRAIN2 persistence owner.

One D4 product blocker remains: stale-run replacement currently removes `materialization/` before `checkpoints/`. An interruption between those successful removals leaves durable continuation with no materialization; the next retry intentionally refuses rebuild and permanently blocks the same run. Reorder or otherwise make the existing cleanup transition interruption-idempotent without adding persistent recovery machinery. A bounded public-path failure-injection test must prove retry from the inter-cleanup interruption, with sibling evidence unchanged and foreign/corrupt state never deleted.

Final functional acceptance also remains open. GitHub exposes no statuses/checks or Actions runs for `dadb83e...`, and the review host could not clone/execute the repository because shell-network access to GitHub is unavailable. The final focused + affected regression + integration + configured static/structural checks must execute on the unchanged post-repair candidate.

Do not add a scheduler, cross-size queue, progress daemon, registry/database, migration framework, restart state machine, second wrapper, second architecture authority, or permanent stale-run archive merely to close this issue.

Implementation/review coordination remains on:

- `fix/mlff-replay-mace-membership-identity`

Full production-scale GPU/CuEq/LAMMPS/MLIAP target-machine qualification remains deferred until the complete final release package. Bounded real MACE/CuEq functional tests required for concrete correctness claims are implementation evidence, not production qualification.
