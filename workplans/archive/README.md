# Archived workplans

Retain completed or explicitly superseded workplans here only when their implementation/design lineage remains useful. Archived workplans are non-normative; accepted current structure and behavior must live in architecture manuals and specifications.

An archived plan may retain the status metadata it had at the moment it was superseded. Its location under `workplans/archive/` is the lifecycle authority; such internal status fields are historical snapshot content, not an active-work declaration.

## 2026-09-24 final-production model publication + lightweight MH-1 integration closeout

Independent final Review closes the cycle **PASS** under Protocol 6.4.

- retained executable product: `73aab9e35399c5b7ceec3bbe31e129f76a50cdd8`;
- final immutable test/evidence candidate: `5a6719d9fbabf04ddad7407b2729be0d0d1f76bf`;
- successful GitHub Actions execution: run `36007255491` from workflow descendant `e048aeebcde62301f4ccf6109fd89a238030cf83`;
- durable report: `../qualification/mlff-publication-closeout/actions-validation-report.md` at commit `84a38b45a9ddd0df6bb19dfba6ba240db094aa2e`;
- final PEM candidate-overlay reconciliation: `54e3a350855237002012b136442ec9621fe89a98`.

Final executable evidence: corrected closeout surfaces **104 tests / 0 failures / 2 authorized LAMMPS-runtime skips**; mandatory focused publication/P7/MH-1 surfaces **91 tests / 0 failures / 2 authorized locked-real-MH1 skips**; compileall passed. No `mdstats/**/*.py` product source changed during the evidence-repair cycle.

Archived records:

- `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_WORKPLAN.md`;
- `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_FINAL_CLOSEOUT_2026-09-24.md`;
- historical Revision-27 and Revision-28 closeout/evidence records retained below for provenance.

The temporary validation workflow was removed after successful evidence publication. Long real MH-1/GPU/CUDA-performance/LAMMPS/MLIAP/MD qualification remains deferred to the actual campaign/final-release target host.


## 2026-09-23 provisional final-production model publication evidence record

The Revision-27 execution record remains archived as historical evidence, but its **final PASS/closure assessment was superseded by Revision 28 independent Review**. The executable candidate remains product-code conforming; lifecycle closure was reopened because tests diagnosed as stale/superseded remained ordinary auto-collected failing specifications rather than being retired/remapped at their evidence owners.

Historical evidence record retained:

- `MLFF_FINAL_PRODUCTION_MODEL_PUBLICATION_MH1_INTEGRATION_CLOSEOUT_2026-09-23.md`.

The canonical workplan and successor evidence are now archived in the Revision-28 closeout section above.


## 2026-09-07 MLFF workplan closeout

A repository-hygiene closeout moved the remaining completed or superseded MLFF coordination lineage out of `workplans/active/` after reconciling it against the current implementation and the closure-reviewed multi-size successor plan.

Archived in this closeout:

- the assembled P1-P7/CampaignStore/storage integration hardening, review, progress, and convergence amendments;
- the complete `mlff-storage-io-reset/` authority/revision/review lineage, including its late closure notes;
- the V7 target-size scientific-simplification umbrella and complete `mlff-target-size-v7-packages/` implementation/review/closure lineage;
- prepared-common atomic-reference ordering, MACE restart-epoch handoff, partial-boundary resume, and replay-acceleration bug-fix plans whose owning repairs are present in the current codebase;
- the optimizer-normalization/objective-weight design/review closure lineage after its substantive consequences were incorporated into later current implementation;
- the scalar provisional-selection/auto-diagnostic/horizon-steering predecessor after it was implemented and explicitly superseded by the ordered multi-size successor.

The only active MLFF implementation contract after this closeout is `workplans/active/MLFF_TARGET_SIZE_MULTI_SELECTION_AND_PER_SIZE_HORIZON_WORKPLAN.md`. Historical status markers inside archived files are intentionally left unchanged.

## 2026-09-10 replay/MACE P5 recovery closeout

Independent Software Design review closed the consolidated replay/MACE P5 execution-recovery cycle after source conformance and final affected-surface execution evidence passed under its Protocol 6.0.0 binding. The executable recovery realization remains the reviewed DS-5 production source; DS-6 changed only the serial-orchestration structural oracle and the workplan execution record.

Archived in this closeout:

- `MLFF_REPLAY_MACE_P5_EXECUTION_RECOVERY_CONSOLIDATED_WORKPLAN.md`;
- `MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_WORKPLAN.md`;
- `MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_PROGRESS_RECOVERY_AMENDMENT.md`;
- `MLFF_REPLAY_MACE_EXECUTION_MEMBERSHIP_IDENTITY_REPAIR_SCHEDULER_ARCHITECTURE_AMENDMENT.md`;
- the cycle-local `CURRENT_IMPLEMENTATION_ENTRYPOINT.md` and `CONSOLIDATION_NOTICE.md`.

The final review accepted the revised serial-size oracle because the frozen architecture requires only the outer selected-size dimension to remain serial while allowing the existing scheduler inside each selected size. Historical REPLAY-UNIFY1A/1E tests that require superseded current-manual/current-graph revision/schema text are not current P5 acceptance authority. Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the complete final release package.

## 2026-09-12 replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime closeout

Independent Software Design and Implementation review closed the replay TRUE_DFT default, pseudolabel prepare stage ownership, and CUDA lifetime repair cycle under SSDP Protocol 6.2. All blockers (B1 through B19) were closed: exact qualification-gate validation (B17), cheap-preflight ordering, provider retirement lifecycle (B1), and the qualification observation regression suite (`tests/test_mlff_qualification_status_observation.py`, B19) were verified on the candidate host. The executable realization remains candidate `eb3221397457b5cf374298c4b4979e1e1d0c0c96` (tree `2bc60f52d6eba36f65a25d2f6aa28cf96975a43e`), with 320/320 functional acceptance tests passing alongside target-host E1/E2 CUDA lifetime proofs.

Archived in this closeout:

- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_FIRST_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_SECOND_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_THIRD_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_FOURTH_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_FIFTH_REVIEW_REOPEN.md`;
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_SIXTH_REVIEW_REOPEN.md`.


## 2026-09-21 final-production global TRAIN scheduler closeout

Independent Software Design Review closed the bounded D3/D4 final-production scheduling rework **PASS** at candidate `62d42da57f948f70bbd50ec338435c3a82b22d49`, with no Serious Challenge to D1/D2 or the Revision-8 D3 architecture. The repair replaces serial outer-size production TRAIN orchestration with one collection-global use of the existing adaptive TRAIN scheduler after collection-wide recovery normalization, while keeping EVAL2, per-seed assessment, and publication serial/fail-fast in frozen selected-size order. Recovery classification remains under the existing run-activity owner, each admission remains linearized against the exact current collection signature, and completed authenticated TRAIN2 siblings are reused after failure/restart.

The final review accepted the stakeholder-directed evidence boundary: additional long RAM/VRAM qualification is deferred to actual production runs, and final target-hardware GPU qualification remains deferred to the final release package. Deterministic scheduler/recovery/currentness acceptance is green; no second scheduler, resource registry, or task-aware resource mechanism was added.

Archived in this closeout:

- `MLFF_PRODUCTION_GLOBAL_TRAIN_SCHEDULER_REPAIR_WORKPLAN.md`.

The design branch is retained for normal integration; archival is lifecycle closure of the coordination plan, not branch deletion or self-promotion to accepted-current architecture.
