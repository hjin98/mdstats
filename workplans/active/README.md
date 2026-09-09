# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`

Its current binding implementation-review amendment is:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`

Remote-SDP Software Design review of implementation commit `12ad13413e7d4a346c80b576be57633914219d97` returned **NO-PASS / REOPENED** on 2026-09-09 under Protocol `5.16.0`.

Most earlier downstream repairs are accepted and must be preserved: canonical configured-path semantics, foundation locator/content-identity separation, path-free replay source/split lineage, complete multi-size CV verdicts, collection-wide final-production admission, P5 publication ownership/P7 consumption, P7 reference-root canonicalization, and the reconciled architecture documentation.

The remaining blocking work is narrow but integrity-critical:

- P5 currently authenticates TRAIN2 continuation separately from the materialization/execution authority that produced it. Because `Train2RuntimePlan` does not identify the exact run/materialization, a foreign continuation with a coincidentally equal runtime plan can be attached to another valid materialization; the full-horizon fast path may then skip `MacePostSelectionTrainer` and reach EVAL2 without reconciling persisted MACE execution evidence with the current materialization.
- A durable continuation must never cause absent/incomplete materialization to be rebuilt beneath it. Continuation reuse must require an intact authenticated compatible materialization and the existing persisted execution authority; otherwise fail typed and preserve evidence.
- Repair this by consolidating/reducing the split recovery decision in existing owners, not by adding another recovery state machine, compatibility record, pointer, registry, lock, or wrapper.
- The absolute/tilde/config-relative foundation acceptance matrix still needs to pass each real campaign-produced request through real `MacePostSelectionTrainer` and prove the dependency-facing `mace_run_config.yaml` receives the current canonical foundation locator.
- Final affected pytest/static/integration evidence is still required on one exact repaired executable candidate; the reviewed implementation commit has no available GitHub check-run evidence.

Implementation continues on `fix/mlff-downstream-integration-closure`. Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains deferred until the final release qualification package.

The narrow single-source replay-lineage adapter repair is implemented and retired to:

- `workplans/archive/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md`

The most recently closed target-size integration plan before these repairs is:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

After independent Software Design Review passes, retire/archive the completed active plan/amendment according to repository policy and reconcile this index as lifecycle closeout.
