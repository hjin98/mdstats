# Current MLFF implementation entrypoint

Implement the current repair from exactly one snapshot-complete workplan:

- `MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`

That consolidated handoff supersedes the earlier replay-membership parent workplan and its implementation-review, progress-recovery, and scheduler/architecture amendments **for implementation purposes**. Those files remain provenance only; an implementation agent should not treat them as separate stages or independently selectable repair packages.

The consolidated workplan covers, in one D4 implementation stage:

1. canonical single-source replay membership identity through the real P5/MACE boundary;
2. elimination of redundant parent/child full replay ExtXYZ reparsing;
3. recovery of the historical supervised TRAIN progress reporter for both `cross-validate` and `train-production`;
4. recovery of the existing adaptive GPU-utilization/VRAM scheduler for both paths;
5. exact TRAIN2/EVAL2 architecture parity, including transient CuEq training realization versus portable e3nn evaluation representation and frozen `avg_num_neighbors` realization;
6. same-workspace/restart preservation, adversarial counterfactuals, multi-size composition, and one final affected-surface regression/integration/static evidence set.

No separate review should be requested between those sub-repairs unless a reopen trigger in the consolidated workplan fires. Full production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final release package.
