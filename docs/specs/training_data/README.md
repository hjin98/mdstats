# MLFF training-data current specification index

This directory contains narrow MLFF specification owner paths plus a temporary residue of superseded documents being consolidated into `docs/history/mlff/` by `DOC-MLFF-ARCH-RESET1` A4. On `design/mlff-replay-retention-target-admissibility-rework`, `mlff_post_selection_p5_spec.md` is a **proposed renewal candidate**; its pre-renewal version remains accepted-current until Gate D review/acceptance.

Only the specifications listed in this index are current normative owners. Unlisted release/gate/migration-era files do not override the current D1-D4 authority and are scheduled for historical consolidation/removal where applicable.

The cross-cutting D3 architecture is defined by `docs/arch_manuals/mlff_training_data_architecture.md` together with the canonical chapters under `docs/arch_manuals/mlff_training_data/`. This specification layer owns exact current schemas, policy values, algorithms, failure modes, and runtime behavior under accepted D1-D3 authority.

## Cross-cutting system contract

- `mlff_data_stage_plan_spec.md` — stable-filename cross-cutting system invariants; despite the filename, it is not an implementation stage plan.

## Source, labels, evidence roles, and fitted preparation

- `mlff_data2_source_catalog_spec.md` — source catalog, label-domain and source identity.
- `mlff_data2a_manifest_inference_gate_spec.md` — explicit source-manifest inference/validation behavior where applicable.
- `mlff_data3_frame_conditions_spec.md` — frame conditions, reference/strain/stress context and eligibility-facing condition records.
- `mlff_data4_raw_features_events_spec.md` — partition-independent raw features and protected-event evidence.
- `mlff_data5_partition_roles_spec.md` — statistical blocks, outer evidence roles, independence, purge, blinding/leakage semantics, plus the legacy/general DATA5 record family. Its V7 clarification is normative: DATA5 label-domain/preselection `CrossValidationPlan` records are **not** current target-size or P5 CV authority; current target-size uses the compatibility-neutral `NeutralStatisticalBase` with no pre-target CV.
- `mlff_data6_selection_descriptors_spec.md` — current selection-descriptor and foundation-prediction evidence.

## Target-size and selected-data authority

The current target-membership authority is the single `pi_train`/prefix chain
described by Architecture Part V and the cross-cutting contract. The paired-seed
reducer is an *optional automatic diagnostic* over that ladder: it recommends a
size. The operator owns the provisional choice, and `cross-validate` admission
is the one boundary that freezes the ordered collection of selected sizes $\{N_i\}$,
their exact memberships $T_{N_i} = \pi_{\mathrm{train}}[:N_i]$, and their per-size
training horizons. Retired multi-view, migration, generated-rescue, label-domain
per-target-size, and pre-target CV authorities are historical/reject-only and do
not create a current specification.

The current construction chain deliberately separates two fitted stages:

```text
authorized pre-order selection evidence
  -> P_train/M3 split and pi_train/pi_eval
  -> TargetSizeCommonPreparation over exact P_train
```

Pre-order descriptor/difficulty evidence may feed the one canonical order. The
later P3 common training preparation (including current P3 E0/weights/model
normalization) is a consumer of P1/P2 authority and is not an input to `pi_train`.
It is also not the current foundation-P5 fitted-preparation authority.

- `mlff_data_stage_plan_spec.md` — cross-cutting evidence-role, fitted-partition, target-size, method/protocol, currentness, and downstream-boundary invariants.
- `mlff_data5_partition_roles_spec.md` — statistical-role/protected-relation foundations and the current neutral-substrate clarification.
- `mlff_data6_selection_descriptors_spec.md` — authorized descriptor/foundation evidence that may feed canonical ordering without owning membership.

## Monitoring, replay, training, checkpointing, and evaluation

- `mlff_online_monitor_spec.md` — `OnlineTargetMonitorPolicy` and `ReplayMonitorPolicy`; restored P5 uses one exact 256-frame campaign-common target monitor with no short-parent success state; replay-monitor semantics remain separately owned.
- `mlff_post_selection_p5_spec.md` — sole restored-P5 D4 owner path; this branch carries its proposed renewal candidate for training/assessment identity separation, replay retention, strict target-minimum selection, and historical reassessment. The pre-renewal revision remains accepted-current until the candidate passes Gate D.
- `mlff_data8_mace_artifacts_spec.md` — current MACE artifact transport and broad `TrainingProtocolIdentity`/`Data8PreparationBundle` contracts for separately current non-P5 consumers and historical provenance. Its broad DATA8 protocol graph does **not** authorize restored P5.
- `mlff_data9b1_campaign_checkpoint_control_spec.md` — checkpoint control and candidate retention/evaluation orchestration where consistent with the current owning method/specification.
- `mlff_binary_model_precision_spec.md` — model precision policy.
- `mlff_true_label_restart_lineage_spec.md` — true-label restart/source lineage.
- `mlff_mace_torchscript_warning_compatibility_spec.md` — current warning handling where the locked runtime still emits the relevant warnings.

For restored P5, `PostSelectionMethodIdentity` is the sole training-method identity. The proposed renewal makes the lineage acyclic and projection-specific: `training method + pre-fit training position -> fitted preparation -> materialization/TRAIN2`, then assessment-independent measurements, role assessment under hard policy + D2.DEF.059A, and aggregate publication under D2.DEF.059B where applicable. Broad `TrainingProtocolIdentity` records remain available only for separately current non-P5 consumers/history and cannot become current P5 through deserialization.

## Post-selection validation and campaign realization

- `mlff_post_selection_p5_spec.md` — restored-P5 CV/final-production D4 owner path; the branch version is the proposed renewed schema/failure/monitor/fitted-preparation/publication/currentness contract pending Gate D.
- `mlff_data9b3_campaign_cli_spec.md` — current campaign CLI contract; P5-specific replay defaults/retired fields/failure rules are constrained by the P5 specification.
- `mlff_adaptive_training_stop_spec.md` — current adaptive-stop/checkpoint scoring semantics where still applicable; P5 target evidence is the exact common monitor and score weights remain distinct from retired training-head scalar weights.
- `mlff_storage_management_spec.md` — owner-driven campaign storage and I/O management.

The CLI's current implementation ends at selected-only method validation and
fresh final production. Deployment parity, physical validation, uncertainty
calibration, and locked testing remain separate downstream product contracts;
they may consume a frozen final publication but do not feed back into target
size, method authority, checkpoint selection, or final-product membership.

- `mlff_data9a5_deployment_artifact_spec.md` — downstream model-artifact boundary; it does not add a current campaign lifecycle stage.
- `mlff_p7_post_production_qualification_spec.md` — current downstream qualification/locked-release behavior; current release qualification is single-size only.

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
- `mlff_replay_perf1_index_cache_spec.md` — authenticated replay-source index/cache.
- `mlff_parallel_evaluation_verification_spec.md` — bounded staged checkpoint evaluation and resource/provider admission; downstream verification is a separate consumer.
- `mlff_vram1_perf_p4_memory_pipeline_spec.md` — GPU/VRAM bounded execution where current runtime qualification supports it.
- `mlff_progress_reporting_format_spec.md` — shared MLFF progress grammar, including fixed-width `HH:MM:SS` elapsed/ETA.

Performance documents that only record a historical gate, calibration experiment, hotfix, or release qualification are evidence/history rather than permanent current specifications and are intentionally omitted from this index.

Production-scale GPU qualification for the present P5 restoration is deferred until the complete final release package is assembled, at which point one final user-side GPU qualification package is produced rather than iterating GPU qualification during development.

## Runtime/backend locks

Runtime/backend specifications are current only while their exact dependency/adapter contract remains supported. The current index includes a runtime lock only when it is an actual accepted execution dependency, not merely because a past release qualified it.

Relevant current runtime sources may include:

- `mlff_cueq_dep1_runtime_freeze_spec.md` — CuEq/MACE/Torch runtime identity where the current configured backend uses that lock.
- `mlff_data9b3a_cueq_campaign_spec.md` — CuEq campaign realization where that backend is explicitly selected and qualified.

Backend qualification reports, hotfix notes, parity diagnostics, and obsolete migration policies are not current semantic owners.

## Authority and compatibility rules

1. Accepted D1 method papers own scientific meaning; accepted D2 method papers own numerical algorithms/equivalence; current D3 architecture owns software ownership/topology; this index identifies narrow current D4 specification owners.
2. `mlff_post_selection_p5_spec.md` is the sole D4 P5 owner path for the restoration; on the active design branch its renewed contents remain proposed until Gate D acceptance. Broad DATA8 protocol prose is explicitly scoped away from P5 rather than resolved by runtime precedence.
3. A narrow specification may strengthen its local current contract but cannot contradict accepted upstream authority.
4. A workplan, audit, benchmark, release note, generated PDF, or historical document cannot override current D1-D4 authority.
5. Unsupported old campaign artifacts fail clearly and require re-preparation; historical readability is not a current product-semantic authorization path.
6. If two current listed specifications appear to own the same scientific/numerical/software decision, that is a documentation/design defect and must be resolved to one owner rather than patched with precedence prose.

## Publication rule

Markdown is the editable semantic source for these specifications. Generated PDFs, when maintained for a current specification, must be regenerated from current Markdown and visually/semantically checked under the repository documentation publication process. Superseded PDFs do not remain current merely because a file exists.

Retired pre-V7 target-size and lifecycle specifications were archived to `docs/history/mlff/retired_specs/` by the destructive target-size generation cutover. They are historical and are not current authority.