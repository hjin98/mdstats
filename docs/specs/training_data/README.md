# MLFF training-data current specification index

This directory contains narrow **current-generation** MLFF specifications plus a temporary residue of superseded documents being consolidated into `docs/history/mlff/`.

Only the specifications listed in this index are current normative owners. Unlisted release/gate/migration-era files do not override the architecture or this index.

The cross-cutting architecture is defined by `docs/arch_manuals/mlff_training_data_architecture.md` together with the canonical chapters under `docs/arch_manuals/mlff_training_data/`. This specification layer owns exact current schemas, policy values, failure modes, and runtime behavior under accepted D1-D3 authority.

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

The current target-membership authority is the single `pi_train`/prefix chain described by Architecture Part V and the cross-cutting contract. The paired-seed reducer is an optional automatic diagnostic over that ladder: it recommends a size. The operator owns the provisional choice, and `cross-validate` admission is the one boundary that freezes the ordered collection of selected sizes, their exact memberships, and their role horizons.

The current construction chain separates:

```text
authorized pre-order selection evidence
  -> P_train/M3 split and pi_train/pi_eval
  -> TargetSizeCommonPreparation over exact P_train
```

The P3 common training preparation is not the restored foundation-P5 fitted-preparation authority.

## Monitoring, replay, training, checkpointing, and evaluation

- `mlff_online_monitor_spec.md` — current common target-monitor and replay-monitor record contracts. For restored P5 the target monitor is one exact 256-frame campaign-common `M_mon` with no short-parent success state.
- `mlff_post_selection_p5_spec.md` — **current normative P5 D4 contract** for `PostSelectionMethodIdentity`, foundation UniversalLoss realization, common-monitor ancestry, selected-only CV folds, foundation-residual fitted preparation/transfer, final production/publication, currentness, and failure behavior.
- `mlff_data8_mace_artifacts_spec.md` — current only for generic MACE artifact transport and separately accepted non-restored-P5 consumers (including P3/P5-scratch surfaces that still use its representation). Its historical blanket P5 loss/protocol statements do **not** authorize restored P5; `mlff_post_selection_p5_spec.md` owns current P5.
- `mlff_data9b1_campaign_checkpoint_control_spec.md` — checkpoint control and candidate retention/evaluation orchestration where consistent with the current P5 contract.
- `mlff_binary_model_precision_spec.md` — model precision policy.
- `mlff_true_label_restart_lineage_spec.md` — true-label restart/source lineage.
- `mlff_mace_torchscript_warning_compatibility_spec.md` — current warning handling where the locked runtime still emits the relevant warnings.

`TrainingProtocolIdentity` remains a broad historical/general DATA8 representation. It is not current P5 method authority. Current P5 descends from `PostSelectionMethodIdentity` through role policy/plan, fitted preparation, `PostSelectionMaterialization`, and run evidence.

## Post-selection validation and campaign realization

- `mlff_post_selection_p5_spec.md` — normative post-selection CV/final-production schema/failure/currentness handoff.
- `mlff_data9b3_campaign_cli_spec.md` — current campaign CLI contract, subject to the restored P5 configuration rules above.
- `mlff_adaptive_training_stop_spec.md` — current adaptive-stop/checkpoint scoring semantics; target/replay score weights are distinct from retired training-head scalar weights and current P5 target evidence is `M_mon`.
- `mlff_storage_management_spec.md` — owner-driven campaign storage and I/O management.

The CLI's current implementation ends at selected-only method validation and fresh final production. Deployment parity, physical validation, uncertainty calibration, and locked testing remain separate downstream product contracts; they may consume a frozen final publication but do not feed back into target size, method authority, checkpoint selection, or final-product membership.

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

- `mlff_cpu_resource_budget_spec.md` — sole campaign-wide CPU-capacity authority.
- `mlff_replay_perf1_index_cache_spec.md` — authenticated replay-source index/cache.
- `mlff_parallel_evaluation_verification_spec.md` — bounded staged checkpoint evaluation and resource/provider admission.
- `mlff_vram1_perf_p4_memory_pipeline_spec.md` — GPU/VRAM bounded execution where current runtime qualification supports it.
- `mlff_progress_reporting_format_spec.md` — shared MLFF progress grammar.

Production-scale GPU qualification for the current restoration remains deferred until the complete final release package is ready for one final user-side GPU qualification pass.

## Runtime/backend locks

Runtime/backend specifications are current only while their exact dependency/adapter contract remains supported. Relevant current runtime sources may include:

- `mlff_cueq_dep1_runtime_freeze_spec.md` — CuEq/MACE/Torch runtime identity where the current configured backend uses that lock.
- `mlff_data9b3a_cueq_campaign_spec.md` — CuEq campaign realization where that backend is explicitly selected and qualified.

Backend qualification reports, hotfix notes, parity diagnostics, and obsolete migration policies are not current semantic owners.

## Authority and compatibility rules

1. D1/D2 method papers own accepted scientific/numerical semantics; D3 architecture owns software ownership/topology; this index identifies narrow current D4 owners.
2. A narrow specification may strengthen its local current contract but cannot contradict accepted upstream authority.
3. `mlff_post_selection_p5_spec.md` is the sole current D4 P5 handoff for the restoration and explicitly scopes broad DATA8-era protocol prose away from P5.
4. A workplan, audit, benchmark, release note, generated PDF, or historical document cannot override current D1-D4 authority.
5. Unsupported old campaign artifacts fail clearly and require re-preparation; historical readability is not current product-semantic authorization.
6. If two current listed specifications appear to own the same semantic decision, that is a documentation/design defect and must be resolved to one owner rather than patched with runtime precedence.

## Publication rule

Markdown is the editable semantic source for these specifications. Generated PDFs, when maintained for a current specification, must be regenerated from the current Markdown and visually/semantically checked under the repository documentation publication process. Superseded PDFs do not remain current merely because a file exists.

Retired pre-V7 target-size and lifecycle specifications remain historical and do not create current authority.