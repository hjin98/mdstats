# MLFF Training-Data Specifications

This directory owns specifications for `mdstats.training_data`. Physical
observable algorithms remain under their analysis-module specifications and
architecture manuals; this branch owns only MLFF data preparation,
orchestration, comparison policy, training-backend calls, and evidence lineage.

## Canonical plan and current status

- `mlff_data_stage_plan_spec.{md,pdf}` freezes the canonical stage order,
  record-family separation, source/label identities, partition feasibility,
  nested checkpoint monitors, protocol identity, fold-local feature/E0 fitting,
  deterministic selection, replay, precision, deployment, observable calls,
  profile migration, sealed-test activation, and active-learning lineage.

Runtime progress through `0.20.61a0`:

- DATA1--DATA8 are implemented (`0.20.29a0`--`0.20.36a0`).
- DATA9A integration and real-MACE qualification span `0.20.37a0`--`0.20.39a0`.
- Complete target-corpus DATA5 qualification is in `0.20.40a0`.
- Selectable FP32/FP64 and critical-FP64 execution are in
  `0.20.41a0`--`0.20.42a0`.
- Deployment-artifact closure is in `0.20.43a0`.
- The analysis-owned observable bridge is in `0.20.44a0`.
- DATA9A6b bridge and documentation consistency closure is in `0.20.45a0`.
- DATA9A6c observable-evidence identity and leakage closure is in `0.20.46a0`.
- DATA9A7a material-profile and atom-group contracts are in `0.20.47a0`.
- DATA9A7b universal structural selection providers are in `0.20.48a0`.
- DATA9A7c phase and geometry profiles are in `0.20.49a0`.
- DATA9A7d optional profile-extension/LTA migration is in `0.20.50a0`.
- DATA9A7e cross-system qualification is implemented in `0.20.51a0`.
- DATA9A8 observable comparison policies are implemented in `0.20.52a0`.
- DATA9A9a restartable checkpoint-bound production DATA6 model sweeps are implemented in `0.20.53a0`.
- DATA9A9b restartable final/fold DATA7 and exact-replay DATA8 materialization is implemented in `0.20.54a0`.
- DATA9A9c production-gate integrity closure is implemented in `0.20.55a0`; the actual production corpus still must execute DATA9A9a/b against its frozen `ProductionCorpusPlan`.
- DATA9B1 campaign/checkpoint control is implemented in `0.20.56a0`.
- DATA9B2 supervised execution, checkpoint evaluation, fold/seed aggregation, committee export, protocol freeze, and sealed-test activation are implemented in `0.20.57a0`.
- DATA9B3 unified campaign CLI, compact orchestration state, manifest approval, source-local precision wrappers, and bounded deployment verification are implemented in `0.20.58a0`. Long production execution remains gated on a passed real DATA9A realization and qualified production replay corpora.
- DATA9B3A frozen cuEquivariance/e3nn backend selection, real-model qualification, and end-to-end campaign propagation are implemented in `0.20.59a0`.
- DATA2A automatic review-manifest inference, exact LTA strain verification, and conservative approval gating are implemented in `0.20.60a0`.
- DATA2 trailing interrupted VASP XML recovery hardening with explicit quality evidence is implemented in `0.20.61a0`.

## Module and stage specifications

- `mlff_data2_source_catalog_spec.{md,pdf}`: source manifest, label-domain,
  named-energy, and atomic-reference contracts.
- `mlff_data2a_manifest_inference_gate_spec.{md,pdf}`: XML metadata inference, filename strain candidates, fixed-cell geometry verification, and review-manifest promotion.
- `mlff_data3_frame_conditions_spec.{md,pdf}`: frame identity, eligibility,
  conditions, duplicate handling, reference cells, and strain.
- `mlff_data4_raw_features_events_spec.{md,pdf}`: generic raw features/events,
  optional profile-extension catalogs, and current DATA4 evidence contracts.
- `mlff_data5_partition_roles_spec.{md,pdf}`: partition units, feasibility,
  evidence roles, independence, nested monitors, blinding, and leakage audits.
- `mlff_data6_selection_descriptors_spec.{md,pdf}`: universal and optional
  profile selection descriptors, restartable model-sweep evidence,
  training-only difficulty, and blinded-prediction contracts.
- `mlff_data7_fitted_metrics_selection_spec.{md,pdf}`: fitted metrics, E0 fits,
  objectives, weights, selection ladders, and coverage.
- `mlff_data8_mace_artifacts_spec.{md,pdf}`: MACE XYZ, replay, protocol,
  compatibility, job-bundle, and sealed-evaluation contracts.
- `mlff_data9b1_campaign_checkpoint_control_spec.{md,pdf}`: passed-gate campaign freezing, checkpoint inventory, metric admissibility, and deterministic constrained selection.
- `mlff_data9b2_execution_aggregation_freeze_spec.{md,pdf}`: supervised and
  restartable execution, exact monitor-bound evaluation, fold/seed aggregation,
  committee export, protocol freeze, and sealed-test activation.
- `mlff_data9b3_campaign_cli_spec.{md,pdf}`: one-config UNIX-style campaign
  interface, digest-approved manifest, one SQLite state database, fail-closed
  advancement, compact results, and bounded deployment verification.
- `mlff_data9b3a_cueq_campaign_spec.{md,pdf}`: frozen e3nn/CuEq backend
  policy, automatic initialization detection, real-model qualification, and
  end-to-end propagation through preparation, training, evaluation, and verification.
- `mlff_data9b4_storage_restart_spec.md`: conservative campaign artifact
  lifecycle, selected-checkpoint retention, active-process ownership, durable
  interruption, completed-run recovery, and disk-pressure continuation.
- `mlff_data9a_integration_qualification_spec.md`: real MACE, foundation,
  replay, and production qualification gate.
- `mlff_data9a2_real_mace_realization_spec.md`: executable MACE realization.
- `mlff_data9a5_deployment_artifact_spec.{md,pdf}`: deterministic FP32/FP64
  deployment artifacts and downstream-runtime boundary.
- `mlff_observable_validation_bridge_spec.{md,pdf}`: immutable pairing and
  orchestration of analysis-owned observables.
- `mlff_data9a7e_cross_system_qualification_spec.{md,pdf}`: bounded
  crystal, amorphous, liquid, interface, and LTA DATA4--DATA7 qualification,
  lazy optional imports, and immutable release evidence.
- `mlff_data9a6b_architecture_consistency_spec.{md,pdf}`: recipe safety,
  initial collection/model lineage, capability schemas, manual/graph correction,
  and thermomechanical-analysis ownership plan.
- `mlff_data9a6c_observable_evidence_leakage_spec.{md,pdf}`: verified symmetric
  lineage, analysis-owned result identities, evidence roles, locked-test gates,
  source/wheel parity, and graph ordering.
- `mlff_data9a7a_material_profile_contracts_spec.{md,pdf}`: compositional phases,
  geometry, chemistry modifiers, structural extensions, atom groups, condition
  axes, independence axes, provider identity, and DATA4 profile threading.
- `mlff_data9a7b_universal_structural_selection_spec.{md,pdf}`: analysis-owned
  local geometry, universal structural provider catalogs, DATA6-v2 integration,
  generic events, DATA7 feature fitting, and per-species environment coverage.
- `mlff_data9a7c_phase_geometry_profiles_spec.{md,pdf}`: phase-composed feature
  and event defaults, geometry-aware atom-group priorities, DATA6-v3 plan
  lineage, and advisory physical-observable call composition.
- `mlff_data9a9a_production_model_sweep_spec.{md,pdf}`: exact DATA5-authorized
  model-sweep planning, restartable descriptor/prediction sidecars, corruption
  recovery, and DATA6-v5 consumption without repeated foundation inference.
- `mlff_parallel_evaluation_verification_spec.md`: adaptive resource-bounded
  checkpoint evaluation and NVE verification concurrency, with 90% CPU/GPU
  utilization and VRAM ceilings and the retained 80% RAM ceiling.
- `mlff_perf_p0_native_target_coverage_spec.{md,pdf}`: current 0.20.179a0
  PERF-P0 authority for canonical native TARGET-DATA2B arrays, authenticated
  NPY-shard persistence, exact historical-v1 migration, shared balanced-weight
  profiles, one-sort weighted statistics, exact uniform-weight radius dispatch,
  matched supplied-data CPU evidence, and the PERF-P1 handoff.
- `mlff_true_inference_telemetry_gate_spec.md`: historical 0.20.87a0 first-forward
  gate and 60-second true-inference window.
- `mlff_mixed_stage_admission_progress_spec.md`: historical 0.20.88a0 heavy-work
  boundary and 20-second mixed-stage admission policy.
- `mlff_single_job_gpu_calibration_spec.md`: historical 0.20.89a0 single-job
  180-second calibration using means over all retained nonzero samples.
- `mlff_upper_tail_gpu_calibration_spec.md`: historical 0.20.90a0 five-minute
  calibration using the highest retained decile after the 1% activity filter.
- `mlff_peak_trimmed_gpu_calibration_spec.md`: historical 0.20.91a0 evaluation/verification
  policy: discard the highest retained decile and average the next decile.
- `mlff_85_95_gpu_calibration_spec.md`: historical/current estimator introduced in 0.20.92a0 for evaluation/verification
  policy: discard the highest 5% of retained activity and average the next-highest 10%
  (approximately the 85th--95th percentile band), freeze GPU-utilization concurrency
  after calibration, and retain only the live VRAM hard guard. CPU evaluation/verification
  stays on a 20-second window and training stays on a 60-second true-epoch window.
- `mlff_work_conserving_inference_queue_spec.md`: historical/current 0.20.93a0 rolling-queue policy;
  admitted evaluation/verification slots are refilled immediately on completion.
- `mlff_parallel_cueq_incremental_export_spec.md`: current 0.20.94a0 runtime policy;
  serialize only thread-unsafe MACE accelerator FX conversion, finalize selection per run,
  atomically publish `models/<run-id>-target.model` while other runs continue, and refill
  all completed-wave slots before selection/export callbacks.

The DATA1 shared sampling specification remains in
`../sampling/shared_sampling_primitives_spec.{md,pdf}`.


- `MLFF-PERF1` (0.20.62a0): profiled one-pass campaign execution, indexed catalogs, vectorized DATA4 kernels, sharded state, and progress contracts.
- `MLFF-PERF2` (0.20.63a0): resource-bounded CPU/RAM/VRAM planning, isolated trajectory workers, compact LTA process transfer, native MACE graph batches, and adaptive CUDA-OOM recovery.
- `MLFF-PERF4` (0.20.86a0): parallel evaluation and verification, projected GPU-utilization/VRAM admission, projected CPU-utilization admission, and package-wide 90% CPU/GPU defaults while RAM remains 80%.
- `MLFF-PERF5` (0.20.87a0): exclude initialization from evaluation/verification telemetry, begin calibration at the first real model forward pass, and require a trailing 60-second inference window before promotion.
- `MLFF-PERF6` (0.20.88a0): begin at the first computation-heavy stage, average the complete evaluation/verification workload for 20 seconds, keep training at 60 seconds, and report per-task stages.
- ADAPT-PREC1 binary learned-model precision is implemented in `0.20.122a0`: new campaigns
  support only `single|double`; staged `refine` remains historical/read-only, while
  mdstats-owned scientific arithmetic remains FP64 under both model modes. See
  `mlff_binary_model_precision_spec.{md,pdf}`.
- ADAPT-MON1 fixed common online monitors are implemented in `0.20.123a0`: new campaign
  preparation binds a deterministic 256-configuration target monitor from the common DATA5
  outer-monitor domain and a deterministic 512-configuration TRUE_DFT replay monitor. See
  `mlff_online_monitor_spec.{md,pdf}`.
- ADAPT-STOP1, ADAPT-RANK1, ADAPT-EVAL1, and ADAPT-VERIFY1 are implemented in
  `0.20.124a0`--`0.20.127a0`; their specifications freeze adaptive stopping, one-champion-per-run
  lightweight ranking, top-K full evaluation, and score-ordered bounded verification.
- ADAPT-MIGRATE1 is implemented in `0.20.128a0`: schema-neutral protocol-freeze authority,
  restart/stale-evidence closure, historical evaluator readability, and storage compatibility. See
  `mlff_adaptive_migration_spec.{md,pdf}`. The seven-gate adaptive revision is complete.

- `mlff_cueq_dep1_runtime_freeze_spec.{md,pdf}`: current `0.20.188a0` CUEQ-DEP1 authority for content-addressed CuEq core/Torch/CUDA-ops distributions, CUDA/determinism provenance, fail-closed runtime capture, and FINAL-GPU1 integration. Positive accelerator evidence remains deferred to the final release workstation run.
- `mlff_mvstate_reuse1_selector_repair_handoff_spec.md`: 0.20.236a0 exact MVSEL-to-REPAIR sparse-state checkpoint handoff, authenticated bundled persistence, post-divergence exactness boundary, and CPU optimization closure.
- `mlff_progress_reporting_format_spec.md`: current 0.20.237a0 presentation-only MLFF progress grammar (`HH:MM:SS` elapsed/ETA, canonical counters/rates/status fields) with revision 103 and FINAL-GPU1 authority unchanged.

- `mlff_mvidx_out_of_core_scaling_spec.md`: 0.20.238a0 exact-equivalence multi-billion-edge MVIDX file-backed/chunked inversion hardening.
