# MLFF training-data current specification index

This directory contains narrow **current-generation** MLFF specifications plus a temporary residue of superseded documents being consolidated into `docs/history/mlff/` by `DOC-MLFF-ARCH-RESET1` A4.

Only the specifications listed in this index are current normative owners. Unlisted release/gate/migration-era files do not override the architecture or this index and are scheduled for historical consolidation/removal.

The cross-cutting architecture is defined by the canonical chapters under `docs/arch_manuals/mlff_training_data/`. This specification layer owns exact current schemas, policy values, algorithms, failure modes, and runtime behavior.

## Cross-cutting system contract

- `mlff_data_stage_plan_spec.md` — stable-filename cross-cutting system invariants; despite the filename, it is not an implementation stage plan.

## Source, labels, evidence roles, and fitted preparation

- `mlff_data2_source_catalog_spec.md` — source catalog, label-domain and source identity.
- `mlff_data2a_manifest_inference_gate_spec.md` — explicit source-manifest inference/validation behavior where applicable.
- `mlff_data3_frame_conditions_spec.md` — frame conditions, reference/strain/stress context and eligibility-facing condition records.
- `mlff_data4_raw_features_events_spec.md` — partition-independent raw features and protected-event evidence.
- `mlff_data5_partition_roles_spec.md` — statistical roles, independence, purge, fold/final training-domain construction.
- `mlff_data6_selection_descriptors_spec.md` — current selection-descriptor and foundation-prediction evidence.
- `mlff_data7_fitted_metrics_selection_spec.md` — domain-local fitted metrics, E0/objective/weights, difficulty, and `TargetSubsetInputBundle`; **no target membership or target-size authority**.

## Multi-view target subset and target size

- `mlff_target_data2b_feas1_support_capacity_spec.md` — FEAS1 full-pool feasibility/support evidence.
- `mlff_neighbor1_exact_neighborhood_spec.md` — exact neighborhood producer semantics shared by current multi-view consumers.
- `mlff_target_data2c_mvidx1_sparse_coverage_index_spec.md` — MVIDX1 authenticated exact sparse coverage index.
- `mlff_mvidx_out_of_core_scaling_spec.md` — exact bounded/file-backed MVIDX realization.
- `mlff_mvidx_queue_backpressure_spec.md` — bounded MVIDX queue/admission behavior.
- `mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md` — current integrated FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL target-subset chain and exact forward/lazy semantics.
- `mlff_target_data2c_mvqual1_same_n_qualification_spec.md` — narrow independent MVQUAL predicate/result details where not superseded by the integrated current contract.
- `mlff_target_subset_size_study_spec.md` — sole exact `TargetSizeStudyPolicy` owner: fixed nominal sizes, materializable/qualified/selected semantics, configurable screen `(n1,n2,n3)` with independent production `n`, paired seeds, funnel, hard admissibility, typed non-convergence/failure.
- `mlff_size_fidelity1_calibration_spec.md` — current target-size-v5 SIZE-FIDELITY1 v2 calibration authority: exhaustive configured-full-horizon trajectories, 3/4/5 coarse hypotheses, monitor/equivalence grid, hard eventual-finalist recall, and deferred FINAL-GPU1 accelerator/scientific qualification.

The following are **not** current target-subset authorities: MVSEL1, REPAIR1, MVSTATE-REUSE1, MVMIGRATE, generated/rescue ladders, or older size-halving/fidelity gate documents. A4 consolidates their useful rationale into history.

## Monitoring, replay, training, checkpointing, and evaluation

- `mlff_online_monitor_spec.md` — `OnlineTargetMonitorPolicy` and `ReplayMonitorPolicy`; monitor cardinalities are not target sizes.
- `mlff_data8_mace_artifacts_spec.md` — current MACE target/replay artifact realization.
- `mlff_adaptive_training_stop_spec.md` — ordinary post-size-freeze training stopping/LR control where current; target-size-study stopping override is owned by `mlff_target_subset_size_study_spec.md`.
- `mlff_data9b1_campaign_checkpoint_control_spec.md` — checkpoint control and candidate retention/evaluation orchestration.
- `mlff_adaptive_full_evaluation_spec.md` — current full candidate evaluation/admissibility behavior where applicable.
- `mlff_adaptive_verification_spec.md` — current deployment/model verification behavior where applicable.
- `mlff_binary_model_precision_spec.md` — model precision policy.
- `mlff_true_label_restart_lineage_spec.md` — true-label restart/source lineage.
- `mlff_mace_torchscript_warning_compatibility_spec.md` — current warning handling where the locked runtime still emits the relevant warnings.

## Cross-validation, final selection, deployment, and campaign realization

- `mlff_mlcv_cross_validation_spec.md` — protocol-matched held-out cross-validation; held-out folds do not choose target size or checkpoint.
- `mlff_mlcv_run_selection_spec.md` — current run/checkpoint aggregation behavior.
- `mlff_mlcv_final_selection_spec.md` — final constrained selection/committee behavior.
- `mlff_mlcv_verification_spec.md` — final protocol/committee verification.
- `mlff_data9a5_deployment_artifact_spec.md` — deployment artifact contract.
- `mlff_data9b2_execution_aggregation_freeze_spec.md` — current aggregation/freeze identity.
- `mlff_data9b3_campaign_cli_spec.md` — current campaign CLI contract.
- `mlff_data9b4_storage_restart_spec.md` — campaign storage/restart behavior.
- `mlff_storage_management_spec.md` — bounded storage/scratch retention policy.

Migration-only specifications are non-current and intentionally omitted.

## Material/profile and physical-observable validation

- `mlff_data9a7a_material_profile_contracts_spec.md` — material/profile declarative extension contracts.
- `mlff_data9a7b_universal_structural_selection_spec.md` — generic structural-provider/current selection-input behavior where compatible with the single-selector architecture.
- `mlff_data9a7c_phase_geometry_profiles_spec.md` — phase/geometry profile semantics.
- `mlff_data9a7e_cross_system_qualification_spec.md` — cross-system/profile qualification evidence.
- `mlff_data9a6c_observable_evidence_leakage_spec.md` — statistical-role restrictions on physical-observable evidence.
- `mlff_observable_validation_bridge_spec.md` — MLFF-to-`mdstats.analysis` observable orchestration boundary.
- `mlff_data9a8_observable_comparison_spec.md` — current observable-comparison policy/result contract.

Profile-migration documents are historical rather than current extension contracts.

## Deterministic and bounded execution

- `mlff_cpu_resource_budget_spec.md` — sole campaign-wide CPU-capacity authority: affinity/cgroup-aware runtime availability, production `cpu_fraction = 0.90`, stage/native/OpenMP ownership, and nested/concurrent admission inside one budget.
- `mlff_parcore1_deterministic_work_queue_spec.md` — shared bounded deterministic CPU work queue.
- `mlff_mvkernel1_sparse_vector_kernels_spec.md` — exact sparse/vector kernel equivalence contract.
- `mlff_repair_par1_deterministic_parallel_proposals_spec.md` — exact deterministic parallel REPAIR2 proposal scoring where current.
- `mlff_mvqual_par1_global_scoring_queue_spec.md` — bounded independent MVQUAL job execution.
- `mlff_replay_perf1_index_cache_spec.md` — authenticated replay-source index/cache.
- `mlff_parallel_evaluation_verification_spec.md` — bounded parallel checkpoint evaluation/deployment verification.
- `mlff_vram1_perf_p4_memory_pipeline_spec.md` — GPU/VRAM bounded execution where current runtime qualification supports it.
- `mlff_progress_reporting_format_spec.md` — shared MLFF progress grammar, including fixed-width `HH:MM:SS` elapsed/ETA.

Performance documents that only record a historical gate, calibration experiment, hotfix, or release qualification are evidence/history rather than permanent current specifications and are intentionally omitted from this index.

## Runtime/backend locks

Runtime/backend specifications are current only while their exact dependency/adapter contract remains supported. The current index includes a runtime lock only when it is an actual accepted execution dependency, not merely because a past release qualified it.

Relevant current runtime sources may include:

- `mlff_cueq_dep1_runtime_freeze_spec.md` — CuEq/MACE/Torch runtime identity where the current configured backend uses that lock.
- `mlff_data9b3a_cueq_campaign_spec.md` — CuEq campaign realization where that backend is explicitly selected and qualified.

Backend qualification reports, hotfix notes, parity diagnostics, and obsolete migration policies are not current semantic owners.

## Authority and compatibility rules

1. Architecture owns cross-subsystem scientific/statistical structure.
2. This index identifies narrow current specification owners.
3. A narrow specification may strengthen its local current contract but cannot contradict the architecture.
4. A workplan, audit, benchmark, release note, generated PDF, or historical document cannot override current architecture/specifications.
5. Unsupported old campaign artifacts fail clearly and require re-preparation; historical readability is not a current product-semantic requirement.
6. If two current listed specifications appear to own the same scientific decision, that is a documentation/design defect and must be resolved to one owner rather than patched with precedence prose.

## Publication rule

Markdown is the editable semantic source for these specifications. Generated PDFs, when maintained for a current specification, must be regenerated from the current Markdown and visually/semantically checked under the repository documentation publication process. Superseded PDFs do not remain current merely because a file exists.
