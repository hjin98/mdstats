"""MLFF training-data preparation contracts implemented by mdstats."""

from ._common import (
    TrainingDataError,
    TrainingDataInputError,
    TrainingDataSerializationError,
)
from .mace_compatibility import (
    MACE_RUNTIME_COMPATIBILITY_SCHEMA,
    MACE_TORCHSCRIPT_DEPRECATION_CODE,
    MACE_SELECTED_HEAD_COMPATIBILITY_POLICY_SCHEMA,
    MACE_MH1_SELECTED_HEAD_SHIM_VERSION,
    MaceSelectedHeadCompatibilityPolicy,
    MaceRuntimeCompatibilityWarning,
    MaceRuntimeCompatibilityRecord,
    MaceRuntimeCompatibilityCapture,
    mace_runtime_warning_scope,
    mace_runtime_warning_handled,
)
from .manifest import (
    TRAINING_DATA_MANIFEST_SCHEMA,
    TRAINING_DATA_MANIFEST_VERSION,
    TRAINING_DATA_RUN_SPEC_SCHEMA,
    TrainingDataManifest,
    TrainingDataRunSpec,
    discover_vasp_manifest,
)

from .manifest_inference import (
    MANIFEST_INFERENCE_POLICY_SCHEMA,
    MANIFEST_INFERENCE_POLICY_VERSION,
    ManifestInferencePolicy,
    ManifestInferenceResult,
    infer_training_manifest_metadata,
)

from .energy import (
    SELECTED_ENERGY_CHANNEL_SCHEMA,
    VASP_ENERGY_LABEL_POLICY_SCHEMA,
    VASP_ENERGY_LABEL_POLICY_VERSION,
    SelectedEnergyChannel,
    VaspEnergyLabelPolicy,
    select_vasp_energy_channel,
)
from .labels import (
    DERIVATIVE_CONVENTION_SCHEMA,
    ELECTRONIC_STRUCTURE_FINGERPRINT_SCHEMA,
    ENERGY_REFERENCE_IDENTITY_SCHEMA,
    LABEL_COMPATIBILITY_DECISION_SCHEMA,
    LABEL_COMPATIBILITY_POLICY_SCHEMA,
    LABEL_COMPATIBILITY_POLICY_VERSION,
    LABEL_DOMAIN_CATALOG_SCHEMA,
    LABEL_DOMAIN_SCHEMA,
    NUMERICAL_QUALITY_PROFILE_SCHEMA,
    SOFTWARE_PROVENANCE_SCHEMA,
    THEORY_IDENTITY_SCHEMA,
    DerivativeConvention,
    ElectronicStructureFingerprint,
    EnergyReferenceIdentity,
    LabelCompatibilityDecision,
    LabelCompatibilityOutcome,
    LabelCompatibilityPolicy,
    LabelDomain,
    LabelDomainCatalog,
    NumericalQualityProfile,
    SoftwareProvenance,
    TheoryIdentity,
    build_label_domain_catalog,
    compare_label_fingerprints,
)
from .atomic_references import (
    ATOMIC_REFERENCE_IDENTIFIABILITY_CATALOG_SCHEMA,
    ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_SCHEMA,
    ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_VERSION,
    ATOMIC_REFERENCE_IDENTIFIABILITY_REPORT_SCHEMA,
    AtomicReferenceIdentifiabilityCatalog,
    AtomicReferenceIdentifiabilityOutcome,
    AtomicReferenceIdentifiabilityPolicy,
    AtomicReferenceIdentifiabilityReport,
    analyze_atomic_reference_identifiability,
)
from .sources import (
    MLFF_DATA2_PARSER_VERSION,
    SOURCE_AUDIT_POLICY_SCHEMA,
    SOURCE_AUDIT_POLICY_VERSION,
    SOURCE_COMPOSITION_SCHEMA,
    TRAINING_DATA_SOURCE_CATALOG_SCHEMA,
    TRAINING_DATA_SOURCE_SCHEMA,
    VASP_STATIC_SOURCE_METADATA_SCHEMA,
    SourceAssessmentStatus,
    SourceAuditPolicy,
    SourceComposition,
    SourceTrajectoryAssessmentMode,
    TrainingDataSource,
    TrainingDataSourceCatalog,
    VaspStaticSourceMetadata,
    LoadedVaspTrainingSource,
    build_training_data_source_catalog,
    build_training_data_source_catalog_from_loaded,
    build_training_data_source_catalog_from_sources,
    load_vasp_training_source,
)

from .accelerator_runtime_freeze import (
    CUEQ_DEP1_POLICY_SCHEMA,
    CUEQ_DEP1_DISTRIBUTION_SCHEMA,
    CUEQ_DEP1_DEVICE_SCHEMA,
    CUEQ_DEP1_RUNTIME_SCHEMA,
    CUEQ_DEP1_COMPONENTS,
    CueqDep1Policy,
    AcceleratorDistributionEvidence,
    AcceleratorDeviceEvidence,
    CueqDep1RuntimeRecord,
    capture_cueq_dep1_runtime,
    write_cueq_dep1_runtime,
)
from .cueq_phase1 import (
    CUEQ_PHASE1_POLICY_SCHEMA,
    CUEQ_PHASE1_TRAJECTORY_SCHEMA,
    CUEQ_PHASE1_PAIR_SCHEMA,
    CUEQ_PHASE1_QUALIFICATION_SCHEMA,
    CUEQ_PHASE1_VERSION,
    CueqPhase1Policy,
    CueqPhase1TrajectoryRecord,
    CueqPhase1PairedAssessment,
    CueqPhase1QualificationRecord,
    build_cueq_phase1_qualification,
)
from .cueq_phase2 import (
    CUEQ_PHASE2_POLICY_SCHEMA,
    CUEQ_PHASE2_CORPUS_SCHEMA,
    CUEQ_PHASE2_DATA6_PARITY_SCHEMA,
    CUEQ_PHASE2_ASSESSMENT_SCHEMA,
    CUEQ_PHASE2_QUALIFICATION_SCHEMA,
    CUEQ_PHASE2_VERSION,
    CUEQ_PHASE2_MH1_SHA256,
    CUEQ_PHASE2_SOURCE_POTENTIAL_DIGEST,
    CUEQ_PHASE2_SELECTED_HEAD_SHA256,
    CUEQ_PHASE2_SELECTED_HEAD_QUALIFICATION_DIGEST,
    CUEQ_PHASE2_STRATA,
    CueqPhase2Policy,
    CueqPhase2DevelopmentCorpus,
    CueqPhase2Data6ParityRecord,
    CueqPhase2PathAssessment,
    CueqPhase2QualificationRecord,
    build_cueq_phase2_qualification,
    cueq_phase2_execution_realization_digest,
)
from .perf_cert1 import (
    PERF_CERT1_POLICY_SCHEMA,
    PERF_CERT1_TELEMETRY_SCHEMA,
    PERF_CERT1_PROFILE_SCHEMA,
    PERF_CERT1_UPSTREAM_SCHEMA,
    PERF_CERT1_ASSESSMENT_SCHEMA,
    PERF_CERT1_QUALIFICATION_SCHEMA,
    PERF_CERT1_VERSION,
    PERF_CERT1_MH1_SHA256,
    PERF_CERT1_MPA0_SHA256,
    PERF_CERT1_PROFILE_KINDS,
    PROFILE_BASELINE,
    PROFILE_PHASE1,
    PROFILE_PHASE2,
    PROFILE_FALLBACK,
    PerfCert1Policy,
    PerfCert1Telemetry,
    PerfCert1ProfileRecord,
    PerfCert1UpstreamAuthority,
    PerfCert1ProfileAssessment,
    PerfCert1QualificationRecord,
    build_perf_cert1_qualification,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .identity import (
    DUPLICATE_DETECTION_CATALOG_SCHEMA,
    DUPLICATE_GEOMETRY_GROUP_SCHEMA,
    DUPLICATE_LABELED_GROUP_SCHEMA,
    FRAME_IDENTITY_SCHEMA,
    GEOMETRY_FINGERPRINT_POLICY_SCHEMA,
    GEOMETRY_FINGERPRINT_POLICY_VERSION,
    LABEL_FINGERPRINT_POLICY_SCHEMA,
    LABEL_FINGERPRINT_POLICY_VERSION,
    DuplicateDetectionCatalog,
    DuplicateGeometryGroup,
    DuplicateLabeledGroup,
    FrameIdentity,
    GeometryFingerprintPolicy,
    LabelFingerprintPolicy,
    build_duplicate_detection_catalog,
    canonical_wrapped_fractional_positions,
    frame_uid,
    source_occurrence_signature,
    geometry_fingerprint,
    label_payload_digest,
    labeled_configuration_fingerprint,
)
from .conditions import (
    TEMPERATURE_CONDITION_CATALOG_SCHEMA,
    TEMPERATURE_CONDITION_SCHEMA,
    TemperatureConditionCatalog,
    TemperatureConditionRecord,
    TemperatureScheduleKind,
    TemperatureTargetEvidence,
    build_temperature_condition,
)
from .strain import (
    FRAME_STRAIN_RECORD_SCHEMA,
    REFERENCE_CELL_CATALOG_SCHEMA,
    REFERENCE_CELL_POLICY_SCHEMA,
    REFERENCE_CELL_POLICY_VERSION,
    REFERENCE_CELL_RECORD_SCHEMA,
    REFERENCE_CELL_RESOLUTION_SCHEMA,
    STRAIN_POLICY_SCHEMA,
    STRAIN_POLICY_VERSION,
    AssertionVerificationStatus,
    FrameStrainRecord,
    ReferenceCellCatalog,
    ReferenceCellPolicy,
    ReferenceCellRecord,
    ReferenceCellResolution,
    ReferenceCellResolutionMode,
    ReferenceCellResolutionStatus,
    StrainContextClass,
    StrainPolicy,
    TensorStrainClass,
    build_reference_cell_catalog,
    compute_frame_strain,
)
from .eligibility import (
    FRAME_ELIGIBILITY_CATALOG_SCHEMA,
    FRAME_ELIGIBILITY_DECISION_SCHEMA,
    FRAME_ELIGIBILITY_POLICY_SCHEMA,
    FRAME_ELIGIBILITY_POLICY_VERSION,
    FrameEligibilityCatalog,
    FrameEligibilityDecision,
    FrameEligibilityPolicy,
    FrameEligibilityState,
    RequiredLabelContractResult,
    StressRequirement,
    assess_frame_eligibility,
    evaluate_required_label_contract,
)
from .frame_catalog import (
    FRAME_DATA_SCHEMA,
    MLFF_DATA3_PARSER_VERSION,
    TRAINING_FRAME_CATALOG_SCHEMA,
    TRAINING_FRAME_RECORD_SCHEMA,
    FrameData,
    TrainingFrameCatalog,
    TrainingFrameRecord,
    build_training_frame_catalog,
    build_vasp_training_frame_catalog,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .raw_features import (
    MLFF_DATA4_PARSER_VERSION,
    PAIR_FEATURE_RULE_SCHEMA,
    PAIR_GEOMETRY_STATISTICS_SCHEMA,
    RAW_FEATURE_CATALOG_SCHEMA,
    RAW_FEATURE_POLICY_SCHEMA,
    RAW_FEATURE_POLICY_VERSION,
    RAW_FRAME_FEATURE_SCHEMA,
    SPECIES_FORCE_STATISTICS_SCHEMA,
    PairFeatureRule,
    PairGeometryStatistics,
    RawFeatureCatalog,
    RawFeaturePolicy,
    RawFrameFeatureRecord,
    SpeciesForceStatistics,
    build_raw_feature_catalog,
    minimum_image_displacements,
)
from .events import (
    EVENT_DETECTION_POLICY_SCHEMA,
    EVENT_DETECTION_POLICY_VERSION,
    FRAME_EVENT_RECORD_SCHEMA,
    FULL_RESOLUTION_EVENT_CATALOG_SCHEMA,
    EventDetectionPolicy,
    FrameEventRecord,
    FrameEventType,
    FullResolutionEventCatalog,
    detect_full_resolution_events,
)
from .role_budget import (
    PARTITION_ROLE_BUDGET_POLICY_SCHEMA,
    PARTITION_ROLE_BUDGET_POLICY_VERSION,
    PartitionRoleBudgetPolicy,
)
from .data4_bundle import (
    DATA4_FEATURE_BUNDLE_SCHEMA,
    FEATURE_CACHE_FILE_RECORD_SCHEMA,
    FEATURE_CACHE_MANIFEST_SCHEMA,
    Data4FeatureBundle,
    FeatureCacheFileRecord,
    FeatureCacheManifest,
    build_data4_feature_bundle,
    build_vasp_data4_feature_bundle,
    load_vasp_frame_data_by_run,
    read_data4_feature_cache,
    write_data4_feature_cache,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .partition import (
    CROSS_VALIDATION_FOLD_SCHEMA,
    CROSS_VALIDATION_PLAN_SCHEMA,
    OUTER_PARTITION_SCHEMA,
    OUTER_ROLE_ASSIGNMENT_SCHEMA,
    PARTITION_CONDITION_KEY_SCHEMA,
    PARTITION_FEASIBILITY_REPORT_SCHEMA,
    PARTITION_INDEPENDENCE_REPORT_SCHEMA,
    PARTITION_POLICY_SCHEMA,
    PARTITION_POLICY_VERSION,
    PARTITION_UNIT_CATALOG_SCHEMA,
    PARTITION_UNIT_SCHEMA,
    CrossValidationFold,
    CrossValidationPlan,
    IndependenceGrade,
    OuterPartition,
    OuterRole,
    OuterRoleAssignment,
    PartitionConditionKey,
    PartitionFeasibilityOutcome,
    PartitionFeasibilityReport,
    PartitionIndependenceReport,
    PartitionPolicy,
    PartitionUnit,
    PartitionUnitCatalog,
    assess_partition_feasibility,
    build_cross_validation_plans,
    build_independence_reports,
    build_outer_partitions,
    build_partition_unit_catalog,
)
from .blinding import (
    BLINDING_BOUNDARY_CATALOG_SCHEMA,
    BLINDING_POLICY_SCHEMA,
    BLINDING_POLICY_VERSION,
    ROLE_BLINDING_BOUNDARY_SCHEMA,
    BlindingBoundaryCatalog,
    BlindingPolicy,
    EvidenceAccess,
    EvidenceOperation,
    RoleBlindingBoundary,
    build_blinding_boundary_catalog,
)
from .leakage import (
    LEAKAGE_AUDIT_POLICY_SCHEMA,
    LEAKAGE_AUDIT_POLICY_VERSION,
    LEAKAGE_AUDIT_REPORT_SCHEMA,
    LEAKAGE_FINDING_SCHEMA,
    LeakageAuditPolicy,
    LeakageAuditReport,
    LeakageFinding,
    LeakageSeverity,
    audit_partition_leakage,
)
from .data5_bundle import (
    DATA5_PARTITION_BUNDLE_SCHEMA,
    MLFF_DATA5_PARSER_VERSION,
    Data5PartitionBundle,
    build_data5_partition_bundle,
)
from .target_data_roles import (
    TARGET_DATA_CORRELATION_FAMILY_SCHEMA,
    TARGET_DATA_DEVELOPMENT_INTERVAL_SCHEMA,
    TARGET_DATA_DOMAIN_ROLE_FREEZE_SCHEMA,
    TARGET_DATA_ROLE_FREEZE_POLICY_SCHEMA,
    TARGET_DATA_ROLE_FREEZE_SCHEMA,
    TARGET_DATA_ROLE_FREEZE_VERSION,
    TARGET_DATA_SOURCE_LINEAGE_SCHEMA,
    TargetDataCorrelationFamilyRecord,
    TargetDataDomainRoleFreeze,
    TargetDataRoleFreeze,
    TargetDataRoleFreezePolicy,
    TargetDataSourceLineageRecord,
    TargetDevelopmentInterval,
    build_target_data_role_freeze,
)

from .foundation_audit import (
    FOUNDATION_AUDIT_DOMAIN_SCHEMA,
    FOUNDATION_AUDIT_PROBE_CONTRACT_SCHEMA,
    FOUNDATION_AUDIT_VERSION,
    FOUNDATION_TARGET_AUDIT_SCHEMA,
    TARGET_MODEL_AUDIT_METRICS_SCHEMA,
    TARGET_MODEL_AUDIT_POLICY_SCHEMA,
    TARGET_MODEL_CONDITIONED_BIN_SCHEMA,
    TARGET_MODEL_CONDITIONED_SUMMARY_SCHEMA,
    TARGET_MODEL_FORCE_TAIL_SCHEMA,
    TARGET_MODEL_SPECIES_FORCE_METRIC_SCHEMA,
    FoundationAuditDomainRecord,
    FoundationAuditProbeContract,
    FoundationTargetAudit,
    TargetModelAuditMetrics,
    TargetModelAuditPolicy,
    TargetModelConditionedForceBin,
    TargetModelConditionedForceSummary,
    TargetModelForceTailMetric,
    TargetModelSpeciesForceMetric,
    build_foundation_target_audit,
    validate_foundation_target_audit_authority,
)

from .target_coverage import (
    TARGET_COVERAGE_POLICY_SCHEMA,
    TARGET_COVERAGE_EXTENT_SCHEMA,
    TARGET_COVERAGE_ARRAY_SCHEMA,
    TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA,
    TARGET_COVERAGE_FAMILY_SCHEMA,
    TARGET_COVERAGE_STRATUM_SCHEMA,
    TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA,
    TARGET_COVERAGE_DOMAIN_SCHEMA,
    TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA,
    TARGET_COVERAGE_REFERENCE_SCHEMA,
    TARGET_COVERAGE_FAMILY_REPORT_SCHEMA,
    TARGET_COVERAGE_STRATUM_REPORT_SCHEMA,
    TARGET_COVERAGE_REPORT_SCHEMA,
    TARGET_COVERAGE_VERSION,
    TARGET_COVERAGE_PERSISTENCE_VERSION,
    TARGET_COVERAGE_MIGRATION_SCHEMA,
    TargetCoveragePolicy,
    TargetCoverageExtentChannel,
    TargetCoverageFamilyReference,
    TargetCoverageStratumRequirement,
    TargetCoverageDomainReference,
    TargetCoverageReference,
    TargetCoverageMigrationReport,
    TargetCoverageFamilyReport,
    TargetCoverageStratumReport,
    TargetCoverageReport,
    build_target_coverage_reference,
    compare_target_coverage_references_exact,
    score_target_subset_coverage,
    assert_nested_coverage_monotonicity,
    validate_target_coverage_reference_authority,
)

from .target_coverage_feasibility import (
    TARGET_COVERAGE_FEASIBILITY_POLICY_SCHEMA,
    TARGET_COVERAGE_SUPPORT_SCHEMA,
    TARGET_COVERAGE_FAMILY_FEASIBILITY_SCHEMA,
    TARGET_COVERAGE_DOMAIN_FEASIBILITY_SCHEMA,
    TARGET_COVERAGE_FEASIBILITY_SCHEMA,
    TARGET_COVERAGE_FEASIBILITY_VERSION,
    TargetCoverageFeasibilityPolicy,
    TargetCoverageSupportDegreeReport,
    TargetCoverageFamilyFeasibilityReport,
    TargetCoverageDomainFeasibilityReport,
    TargetCoverageFeasibilityReport,
    build_target_coverage_feasibility_artifacts,
    build_target_coverage_feasibility_report,
    validate_target_coverage_feasibility_authority,
)

from .target_coverage_exact_neighborhood import (
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_FAMILY_SCHEMA,
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_DOMAIN_SCHEMA,
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_STORE_SCHEMA,
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_VERSION,
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_PERSISTENCE_VERSION,
    EXACT_NEIGHBORHOOD_METRIC_TOLERANCE,
    EXACT_NEIGHBORHOOD_DISTANCE_SEMANTICS,
    TargetCoverageExactNeighborhoodFamily,
    TargetCoverageExactNeighborhoodDomain,
    TargetCoverageExactNeighborhoodStore,
    ExactNeighborhoodEngine,
    ExactNeighborhoodBuildTelemetry,
    build_target_coverage_exact_neighborhood_store,
    validate_target_coverage_exact_neighborhood_store,
)

from .target_coverage_exact_neighborhood_store import (
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_MANIFEST_SCHEMA,
    TARGET_COVERAGE_EXACT_NEIGHBORHOOD_NATIVE_POINTER_SCHEMA,
    TargetCoverageExactNeighborhoodNativeStoreError,
    write_target_coverage_exact_neighborhood_native_record,
    read_target_coverage_exact_neighborhood_native_record,
)

from .target_coverage_store import (
    TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA,
    TARGET_COVERAGE_NATIVE_POINTER_SCHEMA,
    TARGET_COVERAGE_NATIVE_WEIGHT_PROFILE_SCHEMA,
    TargetCoverageNativeStoreError,
    write_target_coverage_native_record,
    read_target_coverage_native_record,
)

from .target_coverage_sparse_index import (
    TARGET_COVERAGE_SPARSE_INDEX_POLICY_SCHEMA,
    TARGET_COVERAGE_SPARSE_FAMILY_SCHEMA,
    TARGET_COVERAGE_HARD_OBLIGATION_SCHEMA,
    TARGET_COVERAGE_SPARSE_DOMAIN_SCHEMA,
    TARGET_COVERAGE_SPARSE_INDEX_SCHEMA,
    TARGET_COVERAGE_SPARSE_INDEX_VERSION,
    TARGET_COVERAGE_SPARSE_INDEX_PERSISTENCE_VERSION,
    TargetCoverageSparseIndexPolicy,
    TargetCoverageSparseFamilyIndex,
    TargetCoverageHardObligation,
    TargetCoverageSparseDomainIndex,
    TargetCoverageSparseIndex,
    build_target_coverage_sparse_index,
    validate_target_coverage_sparse_index_authority,
    indexed_family_covered_mask,
    indexed_family_covered_mass,
    indexed_family_marginal_gain,
    indexed_obligation_selected_counts,
)

from .target_coverage_sparse_forward_view import (
    TargetCoverageSparseForwardFamilyView,
    TargetCoverageSparseForwardDomainView,
    TargetCoverageSparseForwardIndexView,
    target_coverage_sparse_forward_view,
)

from .target_multi_view_selection_state import (
    TARGET_MULTI_VIEW_SELECTION_STATE_FAMILY_SCHEMA,
    TARGET_MULTI_VIEW_SELECTION_STATE_CHECKPOINT_SCHEMA,
    TARGET_MULTI_VIEW_SELECTION_STATE_DOMAIN_SCHEMA,
    TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_SCHEMA,
    TARGET_MULTI_VIEW_SELECTION_STATE_CACHE_VERSION,
    TARGET_MULTI_VIEW_SELECTION_STATE_PERSISTENCE_VERSION,
    TARGET_MULTI_VIEW_SELECTION_STATE_KERNEL_SCHEMA,
    TargetMultiViewSelectionFamilyStateCheckpoint,
    TargetMultiViewSelectionStateCheckpoint,
    TargetMultiViewSelectionDomainStateCache,
    TargetMultiViewSelectionStateCache,
    selected_prefix_digest,
    restore_domain_state,
    validate_target_multi_view_selection_state_cache,
)

from .target_multi_view_selection_state_store import (
    TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_MANIFEST_SCHEMA,
    TARGET_MULTI_VIEW_SELECTION_STATE_NATIVE_POINTER_SCHEMA,
    TargetMultiViewSelectionStateNativeStoreError,
    write_target_multi_view_selection_state_native_record,
    read_target_multi_view_selection_state_native_record,
)

from .target_multi_view_selector_v2 import (
    TARGET_MULTI_VIEW_SELECTOR_V2_VERSION,
    TARGET_MULTI_VIEW_SELECTION_PLAN_V2_SCHEMA,
    TargetMultiViewSelectorPolicyV2,
    TargetMultiViewSelectionDomainPlanV2,
    TargetMultiViewSelectionPlanV2,
    TargetMultiViewCandidateScoreV2,
    TargetMultiViewPhaseATelemetryV2,
    TargetMultiViewPhaseAChoiceV2,
    TargetMultiViewPhaseBTelemetryV2,
    TargetMultiViewPhaseBChoiceV2,
    TargetMultiViewLazyFrontierV2,
    TargetMultiViewForwardFamilyStateV2,
    TargetMultiViewForwardStateV2,
    build_target_multi_view_forward_state_v2,
    score_target_multi_view_candidate_v2,
    score_target_multi_view_candidates_v2,
    choose_target_multi_view_phase_a_candidate_v2,
    build_target_multi_view_lazy_frontier_v2,
    choose_target_multi_view_phase_b_full_forward_v2,
    choose_target_multi_view_phase_b_candidate_v2,
    select_target_multi_view_candidate_v2,
    deselect_target_multi_view_candidate_v2,
    release_target_multi_view_forward_pages_v2,
    build_target_multi_view_selection_plan_v2,
    validate_target_multi_view_selection_authority_v2,
)

from .target_multi_view_selection_state_v2 import (
    MVSTATE2_SCHEMA,
    MVSTATE2_POINTER_SCHEMA,
    MVSTATE2_PERSISTENCE_VERSION,
    TargetMultiViewSelectionStateV2StoreError,
    TargetMultiViewSelectionIdentityV2,
    TargetMultiViewSelectionCheckpointV2,
    build_target_multi_view_selection_identity_v2,
    checkpoint_target_multi_view_forward_state_v2,
    restore_target_multi_view_forward_state_v2,
    write_target_multi_view_selection_checkpoint_v2,
    read_target_multi_view_selection_checkpoint_v2,
)

from .target_multi_view_repair_v2 import (
    TARGET_MULTI_VIEW_REPAIR_V2_VERSION,
    TARGET_MULTI_VIEW_REPAIR_PLAN_V2_SCHEMA,
    TargetMultiViewRepairPolicyV2,
    TargetMultiViewRepairDomainPlanV2,
    TargetMultiViewRepairPlanV2,
    build_target_multi_view_repair_plan_v2,
    validate_target_multi_view_repair_authority_v2,
)

from .target_coverage_sparse_index_store import (
    TARGET_COVERAGE_SPARSE_INDEX_NATIVE_MANIFEST_SCHEMA,
    TARGET_COVERAGE_SPARSE_INDEX_NATIVE_POINTER_SCHEMA,
    TargetCoverageSparseIndexNativeStoreError,
    write_target_coverage_sparse_index_native_record,
    read_target_coverage_sparse_index_native_record,
    read_target_coverage_sparse_index_forward_view_native_record,
)


__all__ = [name for name in globals() if not name.startswith("_")]


from .size_fidelity import (
    SIZE_FIDELITY_POLICY_SCHEMA,
    SIZE_FIDELITY_EXECUTION_PLAN_SCHEMA,
    SIZE_FIDELITY_METRIC_SCHEMA,
    SIZE_FIDELITY_CANDIDATE_SCHEMA,
    SIZE_FIDELITY_REPORT_SCHEMA,
    SIZE_FIDELITY_VERSION,
    SizeFidelityCalibrationPolicy,
    SizeFidelityExecutionPlan,
    SizeFidelityMetric,
    SizeFidelityCandidateAssessment,
    SizeFidelityQualificationReport,
    build_size_fidelity_execution_plan,
    build_size_fidelity_qualification,
    validate_size_fidelity_qualification,
)

from .profile_extensions import (
    PROFILE_FEATURE_CATALOG_SCHEMA,
    PROFILE_FEATURE_PROVIDER_VERSION, MLFF_DATA9A7D_PARSER_VERSION,
    ProfileFeatureStage,
    ProfileFeatureCatalog,
    wrap_lta_partition_features,
    wrap_lta_selection_features,
    normalize_profile_feature_catalogs,
    find_profile_feature,
    profile_partition_state_changed,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .model_features import (
    MACE_ADAPTER_VERSION,
    MACE_MONITOR_GRAPH_CACHE_SCHEMA,
    MACE_MONITOR_GRAPH_POLICY_VERSION,
    MACE_DESCRIPTOR_FILE_RECORD_SCHEMA,
    MACE_DESCRIPTOR_MANIFEST_SCHEMA,
    MACE_DESCRIPTOR_SIGNATURE_SCHEMA,
    MACE_BATCH_CAPACITY_CALIBRATION_SCHEMA,
    MACE_BATCH_CAPACITY_CALIBRATION_V1_SCHEMA,
    MACE_BATCH_CAPACITY_PROBE_SCHEMA,
    MACE_DESCRIPTOR_POLICY_SCHEMA,
    MACE_DESCRIPTOR_POLICY_VERSION,
    MODEL_CHECKPOINT_IDENTITY_SCHEMA,
    MODEL_PREDICTION_SUMMARY_SCHEMA,
    STATIC_INFERENCE_RUNTIME_PROFILE_SCHEMA,
    AtomicModelPrediction,
    AtomicModelProvider,
    MaceCalculatorProvider,
    StaticInferenceOperatingPointEvidence,
    StaticInferenceRuntimeProfile,
    StaticInferenceRuntimeAuthority,
    StaticMaceInferenceExecutor,
    MaceDescriptorFileRecord,
    MaceDescriptorManifest,
    MaceDescriptorPolicy,
    MaceDescriptorSignature,
    MaceBatchCapacityCalibration,
    MaceBatchCapacityProbe,
    MaceBatchWorkloadMode,
    ModelCheckpointIdentity,
    ModelPredictionSummary,
    SpeciesPredictionSummary,
    build_mace_descriptor_manifest,
    read_mace_descriptor_array,
    recommend_mace_batch_size_from_probes,
    summarize_prediction,
    clear_mace_graph_batch_cache,
    clear_mace_monitor_graph_cache,
)
from .difficulty import (
    BLINDED_PREDICTION_CATALOG_SCHEMA,
    BLINDED_PREDICTION_DOMAIN_SCHEMA,
    DIFFICULTY_FRAME_RECORD_SCHEMA,
    SPECIES_FORCE_ERROR_SCHEMA,
    TRAINING_DIFFICULTY_CATALOG_SCHEMA,
    TRAINING_DIFFICULTY_DOMAIN_SCHEMA,
    BlindedEvaluationPredictionCatalog,
    BlindedPredictionDomain,
    BlindedPredictionDomainKind,
    DifficultyFrameRecord,
    PredictionMaterializationStatus,
    SpeciesForceError,
    TrainingDifficultyDomain,
    TrainingDifficultyDomainKind,
    TrainingDifficultyFeatureCatalog,
    build_blinded_evaluation_prediction_catalog,
    build_blinded_prediction_domains,
    build_training_difficulty_domains,
    build_training_difficulty_feature_catalog,
)
from .data6_bundle import (
    DATA6_FEATURE_BUNDLE_SCHEMA,
    DATA6_POLICY_SCHEMA,
    DATA6_POLICY_VERSION,
    MLFF_DATA6_PARSER_VERSION,
    Data6FeatureBundle,
    Data6Policy,
    build_data6_feature_bundle,
)

__all__ = [name for name in globals() if not name.startswith("_")]
from .feature_metric import (
    FEATURE_BLOCK_POLICY_SCHEMA,
    FEATURE_FIT_DOMAIN_SCHEMA,
    FEATURE_METRIC_POLICY_SCHEMA,
    FEATURE_METRIC_POLICY_VERSION,
    FITTED_FEATURE_BLOCK_SCHEMA,
    FITTED_FEATURE_METRIC_SCHEMA,
    MLFF_DATA7_PARSER_VERSION,
    TRANSFORMED_FRAME_FEATURE_SCHEMA,
    FeatureBlockPolicy,
    FeatureFitDomain,
    FeatureFitDomainKind,
    FeatureMetricPolicyTemplate,
    FeatureScalingKind,
    FittedFeatureBlockMetric,
    FittedFeatureMetric,
    TransformedFrameFeature,
    build_feature_fit_domains,
    fit_feature_metric,
)
from .reference_fit import (
    ATOMIC_REFERENCE_FIT_POLICY_SCHEMA,
    ATOMIC_REFERENCE_FIT_POLICY_VERSION,
    ATOMIC_REFERENCE_FIT_RECORD_SCHEMA,
    AtomicReferenceFitMode,
    AtomicReferenceFitPolicy,
    AtomicReferenceFitRecord,
    fit_atomic_reference_energies,
    fit_foundation_residual_atomic_references,
)
from .objectives import (
    CHECKPOINT_METRIC_POLICY_SCHEMA,
    CHECKPOINT_METRIC_POLICY_VERSION,
    CONFIGURATION_WEIGHT_POLICY_SCHEMA,
    CONFIGURATION_WEIGHT_POLICY_VERSION,
    FRAME_TRAINING_WEIGHT_SCHEMA,
    TRAINING_OBJECTIVE_POLICY_SCHEMA,
    TRAINING_OBJECTIVE_POLICY_VERSION,
    TRAINING_WEIGHT_CATALOG_SCHEMA,
    CheckpointMetricPolicy,
    ConfigurationWeightPolicy,
    FrameTrainingWeight,
    FrameTrainingWeightTable,
    TrainingObjectivePolicy,
    TrainingWeightCatalog,
    build_training_weight_catalog,
)
from .selection import (
    SELECTION_BUDGET_POLICY_SCHEMA,
    SELECTION_BUDGET_POLICY_VERSION,
    SELECTION_COVERAGE_LEVEL_SCHEMA,
    SELECTION_COVERAGE_REPORT_SCHEMA,
    SELECTION_LADDER_LEVEL_SCHEMA,
    SELECTION_MASTER_ENTRY_SCHEMA,
    TRAINING_SELECTION_PLAN_SCHEMA,
    SelectionBudgetPolicy,
    SelectionCoverageLevel,
    SelectionCoverageReport,
    SelectionLadderLevel,
    SelectionMasterEntry,
    TrainingSelectionPlan,
    build_selection_coverage_report,
    build_training_selection_plan,
)
from .data7_bundle import (
    DATA7_PREPARATION_BUNDLE_SCHEMA,
    Data7PreparationBundle,
    build_data7_preparation_bundle,
)

__all__ = [name for name in globals() if not name.startswith("_")]
from .mace_compatibility import (
    MACE_CHECKPOINT_CONTROL_POLICY_SCHEMA,
    MACE_COMPATIBILITY_POLICY_SCHEMA,
    MACE_COMPATIBILITY_POLICY_VERSION,
    MACE_LOADER_DRY_RUN_SCHEMA,
    MACE_SOURCE_PROBE_SCHEMA,
    MaceCheckpointControlMode,
    MaceCheckpointControlPolicy,
    MaceCompatibilityPolicy,
    MaceExposureBackend,
    MaceLoaderDryRun,
    MaceSourceProbe,
    emulate_mace_v0316_loader_dry_run,
    probe_mace_source_texts,
    probe_mace_source_tree,
)
from .replay import (
    DEFAULT_REPLAY_SPLIT_RATIO,
    DEFAULT_REPLAY_SPLIT_SEED,
    REPLAY_GEOMETRY_IDENTITY_SCHEMA,
    REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM,
    REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA,
    REPLAY_SOURCE_ARTIFACT_SCHEMA,
    REPLAY_SPLIT_MANIFEST_SCHEMA,
    REPLAY_SPLIT_RANK_SCHEMA,
    REPLAY_TRUE_LABEL_CACHE_SCHEMA,
    REPLAY_TRUE_LABEL_VIEW_SCHEMA,
    REPLAY_TRUE_LABEL_VIEW_RECEIPT_SCHEMA,
    REPLAY_FILE_ARTIFACT_SCHEMA,
    REPLAY_PREPARATION_PLAN_SCHEMA,
    REPLAY_RETENTION_POLICY_SCHEMA,
    ReplayLabelNamespace,
    ReplaySingleSourceConfig,
    ReplaySourceArtifact,
    ReplaySplitManifest,
    ReplaySplitRole,
    ReplayTrueLabelCache,
    ReplayTrueLabelViewArtifact,
    ReplayFileArtifact,
    ReplayLabelMode,
    ReplayMode,
    ReplayPreparationPlan,
    ReplayRetentionPolicy,
    TrueLabelReplayResolution,
    build_replay_split_manifest,
    build_replay_true_label_cache,
    canonical_replay_geometry_identity,
    build_local_replay_plan,
    inspect_replay_source_extxyz,
    normalize_replay_split_ratio,
    replay_split_rank,
    single_source_replay_config_from_campaign,
    inspect_replay_extxyz,
    materialize_replay_true_label_views,
    materialize_true_label_replay_split,
    resolve_true_label_replay_directory,
)
from .replay_pseudolabel import (
    DEFAULT_REPLAY_MAX_FORCE_EV_PER_A,
    DEFAULT_REPLAY_MAX_FORCE_RMS_EV_PER_A,
    DEFAULT_REPLAY_MAX_STRESS_EV_PER_A3,
    DEFAULT_REPLAY_PREDICTION_BATCH_SIZE,
    DEFAULT_REPLAY_PREDICTION_SHARD_SIZE,
    REPLAY_FOUNDATION_PREDICTION_POLICY_SCHEMA,
    REPLAY_FOUNDATION_PREDICTION_SHARD_SCHEMA,
    REPLAY_FOUNDATION_PREDICTION_CACHE_SCHEMA,
    REPLAY_FOUNDATION_AUDIT_CACHE_SCHEMA,
    REPLAY_PSEUDOLABEL_QUALIFICATION_POLICY_SCHEMA,
    REPLAY_PSEUDOLABEL_QUALIFICATION_SCHEMA,
    REPLAY_PSEUDOLABEL_VIEW_SCHEMA,
    REPLAY_PSEUDOLABEL_VIEW_RECEIPT_SCHEMA,
    ReplayFoundationPredictionPolicy,
    ReplayFoundationPredictionShard,
    ReplayFoundationPredictionCache,
    ReplayPseudolabelQualificationPolicy,
    ReplayPseudolabelQualification,
    ReplayPseudolabelViewArtifact,
    replay_foundation_prediction_cache_key,
    build_replay_foundation_prediction_cache,
    build_replay_pseudolabel_qualification,
    materialize_replay_pseudolabel_views,
)
from .acceleration import (
    MACE_ACCELERATION_POLICY_SCHEMA,
    MACE_ACCELERATION_PROBE_SCHEMA,
    MACE_ACCELERATION_PROBE_LEGACY_SCHEMA,
    MACE_ACCELERATION_PARITY_POLICY_SCHEMA,
    MACE_ACCELERATION_PARITY_RECORD_SCHEMA,
    ACCELERATION_REALIZATION_SCHEMA,
    TRAINING_ACCELERATION_REALIZATION_SCHEMA,
    TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_SCHEMA,
    TRAINING_ACCELERATION_DETERMINISTIC_CONTROL_DIAGNOSTIC_SCHEMA,
    TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_POLICY_SCHEMA,
    TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_RECORD_SCHEMA,
    MaceAccelerationBackend,
    MaceAccelerationKernelMode,
    MaceAccelerationParityPolicy,
    MaceAccelerationParityRecord,
    AccelerationRealizationRecord,
    TrainingAccelerationRealizationRecord,
    TrainingAccelerationRepeatabilityDiagnostic,
    TrainingAccelerationDeterministicControlDiagnostic,
    TrainingAccelerationNoiseNormalizedParityPolicy,
    TrainingAccelerationNoiseNormalizedParityRecord,
    MaceAccelerationPolicy,
    MaceAccelerationProbe,
    acceleration_realization_from_e3nn,
    compare_mace_acceleration_calculators,
    qualify_cueq_realization,
    qualify_training_acceleration_realization,
    diagnose_training_acceleration_repeatability,
    diagnose_training_acceleration_deterministic_control,
    build_training_noise_normalized_parity_record,
    qualify_e3nn_realization,
    detect_default_acceleration_backend,
    probe_mace_acceleration,
)
from .mace_export import (
    MACE_EXTXYZ_ARTIFACT_SCHEMA,
    MACE_EXTXYZ_POLICY_SCHEMA,
    MACE_EXTXYZ_POLICY_VERSION,
    MACE_SIDECAR_MANIFEST_SCHEMA,
    MaceExtxyzArtifact,
    MaceExtxyzPolicy,
    MaceSidecarManifest,
    write_mace_extxyz_artifact,
)
from .mace_head_extraction import (
    MACE_SELECTED_HEAD_EXTRACTION_SCHEMA,
    MACE_SELECTED_HEAD_PARITY_POLICY_SCHEMA,
    MACE_SELECTED_HEAD_PARITY_SCHEMA,
    MACE_SELECTED_HEAD_QUALIFICATION_SCHEMA,
    MaceSelectedHeadExtractionRecord,
    MaceSelectedHeadParityPolicy,
    MaceSelectedHeadParityRecord,
    MaceSelectedHeadQualificationRecord,
    extract_mace_selected_foundation_head,
    qualify_mace_selected_foundation_head,
)
from .foundation import (
    FOUNDATION_CHECKPOINT_IDENTITY_V1_SCHEMA,
    FOUNDATION_CHECKPOINT_IDENTITY_V2_SCHEMA,
    FOUNDATION_INFERENCE_IDENTITY_SCHEMA,
    MACE_FOUNDATION_INSPECTION_SCHEMA,
    FoundationInferenceIdentity,
    FoundationPotentialIdentity,
    MaceFoundationFamily,
    MaceFoundationInspection,
    MaceFoundationSpec,
    inspect_mace_foundation,
    foundation_identity_matches_lineage,
)
from .protocol import (
    FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA,
    MACE_JOB_ARTIFACT_SCHEMA,
    MACE_OPTIMIZER_POLICY_SCHEMA,
    SEALED_EVALUATION_ARTIFACT_SCHEMA,
    TRAINING_PROTOCOL_IDENTITY_SCHEMA,
    FoundationCheckpointIdentity,
    MaceJobArtifact,
    MaceJobKind,
    MaceOptimizerPolicy,
    SealedEvaluationArtifact,
    TrainingMode,
    TrainingProtocolIdentity,
)
from .mace_qualification import (
    INSTALLED_MACE_QUALIFICATION_SCHEMA,
    MACE_QUALIFICATION_POLICY_SCHEMA,
    InstalledMaceQualificationRecord,
    MaceQualificationPolicy,
    qualify_mace_source_environment,
)

from .data8_bundle import (
    DATA8_PREPARATION_BUNDLE_SCHEMA,
    MLFF_DATA8_PARSER_VERSION,
    Data8PreparationBundle,
    build_data8_preparation_bundle,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .mace_runtime_freeze import (
    MACE_RUNTIME_CHECKPOINT_LOAD_SCHEMA,
    MACE_RUNTIME_COMPONENT_CAPABILITY_SCHEMA,
    MACE_RUNTIME_FREEZE_POLICY_SCHEMA,
    MACE_RUNTIME_FREEZE_RECORD_SCHEMA,
    MACE_RUNTIME_SOURCE_EVIDENCE_SCHEMA,
    MACE_V0316_RUNTIME_SOURCE_LOCK,
    MaceRuntimeCheckpointLoadEvidence,
    MaceRuntimeComponentCapability,
    MaceRuntimeFreezePolicy,
    MaceRuntimeFreezeRecord,
    MaceRuntimeSourceEvidence,
    probe_mace_runtime_freeze,
)

from .mace_runtime import (
    MACE_CLI_COMMAND_RESULT_SCHEMA,
    MACE_CLI_SMOKE_POLICY_SCHEMA,
    MACE_CLI_SMOKE_RECORD_SCHEMA,
    MACE_DEPENDENCY_MANIFEST_SCHEMA,
    MACE_DEPENDENCY_REQUIREMENT_SCHEMA,
    MACE_RUNTIME_ENVIRONMENT_SCHEMA,
    MACE_RUNTIME_INSTALL_POLICY_SCHEMA,
    MaceCliCommandResult,
    MaceCliSmokePolicy,
    MaceCliSmokeRecord,
    MaceDependencyManifest,
    MaceDependencyRequirement,
    MaceInstallCommandRecord,
    MaceRuntimeEnvironmentRecord,
    MaceRuntimeInstallPolicy,
    create_mace_runtime_environment,
    discover_mace_dependency_artifacts,
    read_mace_dependency_manifest,
    run_mace_cli_smoke,
)
from .precision import (
    MACE_MODEL_PRECISION_RECORD_SCHEMA,
    MACE_PRECISION_TRANSITION_RECORD_SCHEMA,
    SUPPORTED_MACE_FLOAT_DTYPES,
    MaceModelPrecisionRecord,
    MacePrecisionTransitionRecord,
    build_mace_precision_transition_record,
    inspect_mace_model_precision,
)
from .critical_precision import (
    ASE_MD_STATE_PRECISION_AUDIT_SCHEMA,
    MACE_CRITICAL_PRECISION_AUDIT_SCHEMA,
    MACE_CRITICAL_PRECISION_POLICY_SCHEMA,
    PATCH_ENVIRONMENT_VARIABLE,
    SUPPORTED_MACE_VERSION as CRITICAL_PRECISION_SUPPORTED_MACE_VERSION,
    AseMdStatePrecisionAudit,
    MaceCriticalPrecisionAudit,
    MaceCriticalPrecisionPolicy,
    audit_ase_md_state_precision,
    audit_mace_critical_precision,
    build_mace_critical_precision_calculator,
    configure_torch_critical_precision,
    install_mace_critical_fp64_patch,
    activate_mace_critical_precision_policy,
    mace_critical_fp64_patch_installed,
    uninstall_mace_critical_fp64_patch,
)
from .mace_realization import (
    MACE_CONFIG_REALIZATION_POLICY_SCHEMA,
    MACE_CONFIG_REALIZATION_RECORD_SCHEMA,
    MACE_JOB_EXECUTION_SMOKE_POLICY_SCHEMA,
    MACE_JOB_EXECUTION_SMOKE_RECORD_SCHEMA,
    MaceConfigRealizationPolicy,
    MaceConfigRealizationRecord,
    MaceJobExecutionSmokePolicy,
    MaceJobExecutionSmokeRecord,
    realize_mace_job_config,
    run_mace_job_execution_smoke,
)

__all__ = [name for name in globals() if not name.startswith("_")]
from .production_qualification import (
    MLFF_DATA9A3_PARSER_VERSION,
    PRODUCTION_CORPUS_QUALIFICATION_SCHEMA,
    PRODUCTION_CORPUS_PLAN_SCHEMA,
    PRODUCTION_EXPECTED_RUN_SCHEMA,
    PROFILE_EXTENSION_REQUIREMENT_SCHEMA,
    PRODUCTION_STAGE_RESOURCE_SCHEMA,
    ProductionCorpusPlan,
    ProductionExpectedRun,
    ProfileExtensionEvidenceRequirement,
    ProductionCorpusQualificationRecord,
    ProductionGateStatus,
    ProductionStageResourceRecord,
    build_production_corpus_qualification_record,
)

__all__ = [name for name in globals() if not name.startswith("_")]
from .mace_deployment import (
    MACE_DEPLOYMENT_ARTIFACT_SCHEMA,
    MACE_DEPLOYMENT_EXPORTER_VERSION,
    MACE_DEPLOYMENT_EXPORT_POLICY_SCHEMA,
    MACE_INFERENCE_COMPARISON_SCHEMA,
    MaceDeploymentArtifact,
    MaceDeploymentExportPolicy,
    MaceInferenceComparisonRecord,
    export_mace_deployment_artifact,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .observable_validation import (
    MLFF_OBSERVABLE_VALIDATION_EVIDENCE_SCHEMA,
    MLFF_OBSERVABLE_VALIDATION_PLAN_SCHEMA,
    MLFF_OBSERVABLE_VALIDATION_VERSION,
    MLFFObservableValidationEvidence,
    MLFFObservableValidationEvidenceRecord,
    MLFFObservableValidationPlan,
    ObservableCollectionIdentity,
    ObservableEvidenceRole,
    ObservableValidationActivationRecord,
    TrajectoryGenerationIdentity,
    ObservableRecommendationProfile,
    recommended_observable_ids,
    run_mlff_observable_validation,
)

from .material_profiles import (
    MATERIAL_PROFILE_PROVIDER_IDENTITY_SCHEMA,
    PHASE_COMPONENT_IDENTITY_SCHEMA,
    MATERIAL_PROFILE_IDENTITY_SCHEMA,
    ATOM_GROUP_SELECTOR_SCHEMA,
    ATOM_GROUP_DEFINITION_SCHEMA,
    ATOM_GROUP_CATALOG_SCHEMA,
    CONDITION_AXIS_DEFINITION_SCHEMA,
    CONDITION_AXIS_CATALOG_SCHEMA,
    INDEPENDENCE_AXIS_DEFINITION_SCHEMA,
    INDEPENDENCE_AXIS_CATALOG_SCHEMA,
    MATERIAL_PROFILE_CONTRACTS_SCHEMA,
    MaterialPhaseKind,
    MaterialGeometryKind,
    ChemistryModifier,
    StructuralExtension,
    AtomGroupSelectorKind,
    AtomGroupScope,
    AtomGroupSetOperation,
    AxisValueKind,
    ConditionAxisRole,
    IndependenceAxisScope,
    MaterialProfileProviderIdentity,
    PhaseComponentIdentity,
    MaterialProfileIdentity,
    AtomGroupSelector,
    AtomGroupDefinition,
    AtomGroupCatalog,
    ConditionAxisDefinition,
    ConditionAxisCatalog,
    IndependenceAxisDefinition,
    IndependenceAxisCatalog,
    MaterialProfileContracts,
    SystemProfileProvider,
    build_single_phase_material_profile,
    default_atom_group_catalog,
    default_condition_axis_catalog,
    default_independence_axis_catalog,
    build_material_profile_contracts,
    contracts_from_provider,
    resolve_atom_group_indices,
    focus_atom_group_ids,
    focus_atomic_numbers,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .structural_selection import (
    UNIVERSAL_STRUCTURAL_SELECTION_POLICY_SCHEMA,
    UNIVERSAL_ATOMIC_ENVIRONMENT_SCHEMA,
    UNIVERSAL_FRAME_DESCRIPTOR_SCHEMA,
    GENERIC_STRUCTURAL_EVENT_SCHEMA,
    STRUCTURAL_FEATURE_PROVIDER_IDENTITY_SCHEMA,
    UNIVERSAL_STRUCTURAL_FEATURE_CATALOG_SCHEMA,
    UNIVERSAL_STRUCTURAL_SELECTION_POLICY_VERSION,
    UNIVERSAL_STRUCTURAL_PROVIDER_ID,
    UNIVERSAL_STRUCTURAL_PROVIDER_VERSION,
    MLFF_DATA9A7B_PARSER_VERSION,
    StructuralFeatureProviderIdentity,
    UniversalStructuralSelectionPolicy,
    UniversalAtomicEnvironmentDescriptor,
    UniversalFrameStructuralDescriptor,
    GenericStructuralEventRecord,
    UniversalStructuralFeatureCatalog,
    AtomGroupMembershipProvider,
    StructuralSelectionProvider,
    UniversalStructuralSelectionProvider,
    build_universal_structural_feature_catalog,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .phase_geometry_profiles import (
    PHASE_GEOMETRY_SELECTION_PLAN_SCHEMA,
    PHASE_GEOMETRY_SELECTION_PLAN_VERSION,
    MLFF_DATA9A7C_PARSER_VERSION,
    StructuralFeatureFamily,
    StructuralEventKind,
    PhaseGeometrySelectionPlan,
    derive_phase_geometry_selection_plan,
    recommended_observable_profile_ids,
    universal_structural_policy_from_plan,
)
from .observable_validation import recommended_observable_ids_for_material_profile
from .observable_comparison import (
    OBSERVABLE_COMPARISON_THRESHOLDS_SCHEMA,
    OBSERVABLE_SCORE_UNCERTAINTY_SCHEMA,
    OBSERVABLE_COMPARISON_RULE_SCHEMA,
    OBSERVABLE_COMPARISON_POLICY_SCHEMA,
    OBSERVABLE_RULE_COMPARISON_RESULT_SCHEMA,
    OBSERVABLE_COMPARISON_RESULT_SCHEMA,
    OBSERVABLE_ACCEPTANCE_DECISION_SCHEMA,
    OBSERVABLE_COMPARISON_VERSION,
    MLFF_DATA9A8_PARSER_VERSION,
    ObservableComparisonMetric,
    ObservableValueReducer,
    ObservableComparisonOutcome,
    ObservableComparisonThresholds,
    ObservableScoreUncertainty,
    ObservableComparisonRule,
    ObservableComparisonPolicy,
    ObservableRuleComparisonResult,
    ObservableComparisonResult,
    ObservableAcceptanceDecision,
    compare_mlff_observable_validation,
    decide_observable_acceptance,
    build_profile_aware_observable_comparison_policy,
    recommended_observable_comparison_templates,
)

__all__ = [name for name in globals() if not name.startswith("_")]

# MLFF material-specific LTA contracts are lazy optional exports.  Generic
# imports and workflows therefore do not import the LTA implementation modules.
_LAZY_LTA_EXPORTS = {
    "LTA_FRAME_PARTITION_RECORD_SCHEMA": (".lta_profile", "LTA_FRAME_PARTITION_RECORD_SCHEMA"),
    "LTA_MOBILE_SITE_STATE_SCHEMA": (".lta_profile", "LTA_MOBILE_SITE_STATE_SCHEMA"),
    "LTA_PARTITION_FEATURE_CATALOG_SCHEMA": (".lta_profile", "LTA_PARTITION_FEATURE_CATALOG_SCHEMA"),
    "LTA_PARTITION_PROFILE_POLICY_SCHEMA": (".lta_profile", "LTA_PARTITION_PROFILE_POLICY_SCHEMA"),
    "LTA_PARTITION_PROFILE_POLICY_VERSION": (".lta_profile", "LTA_PARTITION_PROFILE_POLICY_VERSION"),
    "LTA_RING_DEFINITION_SCHEMA": (".lta_profile", "LTA_RING_DEFINITION_SCHEMA"),
    "LtaFramePartitionRecord": (".lta_profile", "LtaFramePartitionRecord"),
    "LtaMobileSiteState": (".lta_profile", "LtaMobileSiteState"),
    "LtaPartitionFeatureCatalog": (".lta_profile", "LtaPartitionFeatureCatalog"),
    "LtaPartitionProfilePolicy": (".lta_profile", "LtaPartitionProfilePolicy"),
    "LtaProfileStatus": (".lta_profile", "LtaProfileStatus"),
    "LtaRingDefinition": (".lta_profile", "LtaRingDefinition"),
    "LtaSiteClass": (".lta_profile", "LtaSiteClass"),
    "build_lta_partition_feature_catalog": (".lta_profile", "build_lta_partition_feature_catalog"),
    "LTA_ATOMIC_ENVIRONMENT_DESCRIPTOR_SCHEMA": (".lta_selection", "LTA_ATOMIC_ENVIRONMENT_DESCRIPTOR_SCHEMA"),
    "LTA_FRAME_SELECTION_DESCRIPTOR_SCHEMA": (".lta_selection", "LTA_FRAME_SELECTION_DESCRIPTOR_SCHEMA"),
    "LTA_SELECTION_FEATURE_CATALOG_SCHEMA": (".lta_selection", "LTA_SELECTION_FEATURE_CATALOG_SCHEMA"),
    "LTA_SELECTION_POLICY_SCHEMA": (".lta_selection", "LTA_SELECTION_POLICY_SCHEMA"),
    "LTA_SELECTION_POLICY_VERSION": (".lta_selection", "LTA_SELECTION_POLICY_VERSION"),
    "LtaAtomicEnvironmentDescriptor": (".lta_selection", "LtaAtomicEnvironmentDescriptor"),
    "LtaFrameSelectionDescriptor": (".lta_selection", "LtaFrameSelectionDescriptor"),
    "LtaSelectionFeatureCatalog": (".lta_selection", "LtaSelectionFeatureCatalog"),
    "LtaSelectionPolicy": (".lta_selection", "LtaSelectionPolicy"),
    "build_lta_selection_feature_catalog": (".lta_selection", "build_lta_selection_feature_catalog"),
}

for _lazy_name in _LAZY_LTA_EXPORTS:
    if _lazy_name not in __all__:
        __all__.append(_lazy_name)

def __getattr__(name: str):
    target = _LAZY_LTA_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module = import_module(target[0], __name__)
    value = getattr(module, target[1])
    globals()[name] = value
    return value


from .cross_system_qualification import (
    IMPORT_ISOLATION_EVIDENCE_SCHEMA,
    CROSS_SYSTEM_QUALIFICATION_POLICY_SCHEMA,
    CROSS_SYSTEM_QUALIFICATION_CASE_SCHEMA,
    CROSS_SYSTEM_QUALIFICATION_SUITE_SCHEMA,
    MLFF_DATA9A7E_PARSER_VERSION,
    CROSS_SYSTEM_QUALIFICATION_VERSION,
    ImportIsolationEvidence,
    CrossSystemCaseKind,
    CrossSystemQualificationPolicy,
    CrossSystemQualificationCaseRecord,
    CrossSystemQualificationSuiteRecord,
    qualify_cross_system_case,
    build_cross_system_qualification_suite,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .production_model_sweep import (
    DATA6_MODEL_SWEEP_PLAN_SCHEMA,
    ATOMIC_MODEL_PREDICTION_FILE_SCHEMA,
    ATOMIC_MODEL_PREDICTION_MANIFEST_SCHEMA,
    DATA6_MODEL_SWEEP_FRAME_SCHEMA,
    DATA6_MODEL_SWEEP_CHECKPOINT_SCHEMA,
    DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA,
    DATA6_RUNTIME_BATCH_CAP_SCHEMA,
    MLFF_DATA9A9A_VERSION,
    Data6ModelSweepPlan,
    AtomicModelPredictionFileRecord,
    AtomicModelPredictionManifest,
    Data6ModelSweepFrameRecord,
    Data6ModelSweepStatus,
    Data6ModelSweepCheckpoint,
    Data6ModelSweepExecutionPolicy,
    Data6RuntimeBatchCap,
    Data6ModelSweepArtifacts,
    PersistentAtomicModelPredictionCache,
    build_data6_model_sweep_plan,
    run_restartable_data6_model_sweep,
    load_data6_model_sweep_artifacts,
    read_atomic_model_prediction,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .production_materialization import (
    PRODUCTION_MATERIALIZATION_POLICY_SCHEMA,
    PRODUCTION_MATERIALIZATION_PLAN_SCHEMA,
    PRODUCTION_DATA7_ARTIFACT_SCHEMA,
    PRODUCTION_DATA8_ARTIFACT_SCHEMA,
    PRODUCTION_MATERIALIZATION_CHECKPOINT_SCHEMA,
    PRODUCTION_MATERIALIZATION_RECORD_SCHEMA,
    MLFF_DATA9A9B_VERSION,
    ProductionMaterializationStatus,
    ProductionMaterializationExecutionPolicy,
    ProductionMaterializationPlan,
    ProductionData7ArtifactRecord,
    ProductionData8ArtifactRecord,
    ProductionMaterializationCheckpoint,
    ProductionMaterializationRecord,
    build_production_materialization_plan,
    run_restartable_production_materialization,
    register_reusable_data7_artifacts,
    load_production_materialization,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .campaign_control import (
    TRAINING_CAMPAIGN_POLICY_SCHEMA,
    TRAINING_CAMPAIGN_RUN_PLAN_SCHEMA,
    TRAINING_CAMPAIGN_PLAN_SCHEMA,
    CHECKPOINT_FILE_RECORD_SCHEMA,
    CANDIDATE_CHECKPOINT_CATALOG_SCHEMA,
    CHECKPOINT_METRIC_RECORD_SCHEMA,
    CHECKPOINT_ADMISSIBILITY_DECISION_SCHEMA,
    CHECKPOINT_SELECTION_RECORD_SCHEMA,
    MLFF_DATA9B1_VERSION,
    CheckpointAdmissibilityOutcome,
    TrainingCampaignPolicy,
    TrainingCampaignRunPlan,
    TrainingCampaignPlan,
    CheckpointFileRecord,
    CandidateCheckpointCatalog,
    CheckpointMetricRecord,
    CheckpointAdmissibilityDecision,
    CheckpointSelectionRecord,
    protocol_family_digest,
    protocol_variant_digest,
    build_training_campaign_plan,
    inventory_mace_checkpoints,
    assess_checkpoint_admissibility,
    select_checkpoint,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .campaign_execution import (
    TRAINING_EXECUTION_POLICY_SCHEMA,
    TRAINING_RUN_ATTEMPT_SCHEMA,
    TRAINING_RUN_EXECUTION_SCHEMA,
    CHECKPOINT_EVALUATION_POLICY_SCHEMA,
    INFERENCE_EXECUTION_PLAN_SCHEMA,
    CHECKPOINT_EVALUATION_RECORD_SCHEMA,
    MODEL_DATASET_METRIC_RECORD_SCHEMA,
    PROTOCOL_VARIANT_AGGREGATE_SCHEMA,
    PROTOCOL_FAMILY_AGGREGATE_SCHEMA,
    LEARNING_CURVE_RECORD_SCHEMA,
    PROTOCOL_COMPARISON_RECORD_SCHEMA,
    COMMITTEE_EXPORT_POLICY_SCHEMA,
    COMMITTEE_MEMBER_RECORD_SCHEMA,
    COMMITTEE_IDENTITY_SCHEMA,
    PROTOCOL_FREEZE_RECORD_SCHEMA,
    EVALUATION_ACTIVATION_DECISION_SCHEMA,
    VERIFICATION_MODEL_RECORD_SCHEMA,
    AVAILABLE_MODEL_VERIFICATION_SET_SCHEMA,
    MLFF_DATA9B2_VERSION,
    MACE_CHECKPOINT_MODEL_CACHE_SCHEMA,
    MACE_CHECKPOINT_MODEL_EXPORT_CONTRACT,
    TrainingRunState,
    EvaluationActivationOutcome,
    VerificationEvidenceLevel,
    TrainingExecutionPolicy,
    TrainingRunAttemptRecord,
    TrainingRunExecutionRecord,
    CheckpointEvaluationPolicy,
    InferenceExecutionPlan,
    CheckpointEvaluationRecord,
    PreparedCheckpointEvaluation,
    CheckpointEvaluationPredictionBundle,
    SharedTargetEvaluationContext,
    ModelDatasetMetricRecord,
    ProtocolVariantAggregate,
    ProtocolFamilyAggregate,
    LearningCurveRecord,
    ProtocolComparisonRecord,
    CommitteeExportPolicy,
    CommitteeMemberRecord,
    VerificationModelRecord,
    AvailableModelVerificationSet,
    CommitteeIdentity,
    ProtocolFreezeRecord,
    EvaluationActivationDecision,
    execute_training_run,
    prepare_mace_checkpoint_evaluation,
    prepare_shared_target_evaluation_context,
    run_prepared_mace_checkpoint_inference,
    finalize_prepared_mace_checkpoint_evaluation,
    evaluate_mace_checkpoint,
    checkpoint_prediction_cache_complete,
    bind_checkpoint_evaluation_replay_provenance,
    materialize_mace_checkpoint_model,
    create_mace_evaluation_state_capsule,
    remove_materialized_mace_checkpoint_model,
    aggregate_protocol_variant,
    aggregate_protocol_family,
    build_learning_curve,
    compare_protocol_families,
    export_target_head_member,
    export_target_head_model_artifact,
    export_target_head_verification_model,
    build_committee_identity,
    freeze_training_protocol,
    activate_sealed_evaluation,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .frame_cache import (
    FRAME_CACHE_SCHEMA,
    finalize_frame_data_cache,
    load_frame_data_cache,
    write_frame_data_cache,
    write_frame_data_cache_entry,
)

from .resources import (
    GpuResourceSnapshot,
    SystemResourceSnapshot,
    StageResourceScope,
    available_cpu_threads,
    available_memory_bytes,
    bounded_process_map,
    build_stage_resource_scope,
    configure_worker_thread_environment,
    detect_gpu_resources,
    detect_system_resources,
    initialize_process_worker,
    isolated_process_map,
    process_pool_context,
    resolve_worker_count,
    stage_resource_scope,
)

from .work_queue import (
    DeterministicWorkQueueError,
    DeterministicWorkQueueTaskError,
    DeterministicWorkQueueMemoryError,
    DeterministicWorkItem,
    DeterministicWorkCompletion,
    DeterministicWorkQueueSnapshot,
    DeterministicOrderedReducer,
    DeterministicWorkQueue,
)

from .evaluation_predictions import (
    EVALUATION_PREDICTION_KEY_SCHEMA,
    EVALUATION_PREDICTION_ARTIFACT_SCHEMA,
    EVALUATION_PREDICTION_NUMERICAL_CONTRACT,
    EvaluationPredictionKey,
    EvaluationPredictionArtifact,
    geometry_order_digest,
    prediction_key,
    write_evaluation_prediction_artifact,
    load_evaluation_prediction_artifact_record,
    load_evaluation_prediction_artifact,
    evaluation_prediction_cache_has,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .evaluation_views import (
    EVALUATION_DATASET_VIEW_SCHEMA,
    EVALUATION_DATASET_VIEW_POLICY_VERSION,
    EvaluationDatasetView,
    build_evaluation_dataset_view,
    metrics_from_prediction_view,
    cached_evaluation_dataset_view,
    clear_evaluation_dataset_view_cache,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .multi_fidelity_evaluation import (
    MULTI_FIDELITY_EVALUATION_POLICY_SCHEMA,
    MULTI_FIDELITY_MONITOR_LADDER_SCHEMA,
    MULTI_FIDELITY_ROUND_RECORD_SCHEMA,
    MULTI_FIDELITY_SURVIVOR_DECISION_SCHEMA,
    MultiFidelityEvaluationPolicy,
    MultiFidelityMonitorLadder,
    MultiFidelityCheckpointRoundRecord,
    MultiFidelitySurvivorDecision,
    deterministic_balanced_order,
    deterministic_block_labels,
    build_monitor_ladder,
    target_primary_block_values,
    replay_degradation_block_values,
    provisional_ranking_key,
    survivor_count,
    conservative_survivor_decision,
)

from .precision_schedule import (
    PRECISION_STAGE_SCHEMA,
    PRECISION_SCHEDULE_POLICY_SCHEMA,
    RESOLVED_PRECISION_STAGE_SCHEMA,
    RESOLVED_PRECISION_SCHEDULE_SCHEMA,
    PrecisionProfile,
    PrecisionStage,
    PrecisionSchedulePolicy,
    ResolvedPrecisionStage,
    ResolvedPrecisionSchedule,
    canonical_precision_schedule_policy,
    legacy_one_stage_precision_policy,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .precision_runtime import (
    PRECISION_RUNTIME_COMPANION_SCHEMA,
    PRECISION_STAGE_TRANSITION_SCHEMA,
    PrecisionRuntimePlan,
    MacePrecisionStageTransitionRecord,
    load_precision_runtime_plan,
    configure_precision_runtime_from_argv,
    install_mace_precision_runtime_patches,
    apply_precision_stage_boundary,
    persist_precision_runtime_companion,
    latest_resumable_precision_epoch,
    companion_path,
    transition_record_path,
    model_dtype_inventory,
    optimizer_dtype_inventory,
    ema_dtype_inventory,
    cast_batch_to_model_dtype,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))
from .storage_accounting import (
    CAMPAIGN_ARTIFACT_OWNERSHIP_CATALOG_SCHEMA,
    CAMPAIGN_STORAGE_REPORT_SCHEMA,
    ArtifactOwnershipClass,
    ArtifactRetentionClass,
    ProtectedInputPath,
    StorageFamilyRecord,
    LargestArtifactRecord,
    CampaignArtifactOwnershipCatalog,
    CampaignStorageReport,
    CampaignOwnershipBoundary,
    configured_protected_inputs,
    build_campaign_storage_report,
)

from .checkpoint_capsule import (
    EVALUATION_STATE_CAPSULE_FILE_SCHEMA,
    EVALUATION_STATE_CAPSULE_RECORD_SCHEMA,
    EVALUATION_STATE_CAPSULE_CONTRACT,
    EvaluationStateCapsuleRecord,
    model_state_sha256,
    load_validated_capsule_payload,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .online_monitor import (
    ONLINE_MONITOR_POLICY_SCHEMA,
    ONLINE_MONITOR_RECORD_SCHEMA,
    OnlineMonitorPolicy,
    OnlineMonitorRecord,
    build_target_online_monitor,
    build_replay_online_monitor,
    materialize_replay_online_monitor,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .adaptive_stop import (
    ADAPTIVE_STOP_POLICY_SCHEMA,
    ADAPTIVE_STOP_STATE_SCHEMA,
    REPLAY_FOUNDATION_BASELINE_SCHEMA,
    ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE,
    MLCV_TARGET_STOP_FRACTION,
    MLCV_REPLAY_STOP_MULTIPLIER,
    AdaptiveTrainingStopPolicy,
    AdaptiveTrainingEpochMetric,
    AdaptiveTrainingStopState,
    ReplayFoundationBaselineRecord,
    adaptive_stop_policy_from_environment,
    validate_adaptive_stop_foundation_baseline,
    adaptive_training_stop_already_terminal,
    adaptive_training_stop_requested,
)

from .lightweight_rank import (
    LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA,
    LIGHTWEIGHT_RUN_CHAMPION_SCHEMA,
    DEFAULT_LIGHTWEIGHT_TOPK_CANDIDATES,
    LightweightCheckpointScore,
    LightweightRunChampionRecord,
    rank_lightweight_run_champion,
    rank_lightweight_run_topk,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))


from .mlcv_select import (
    MLCV_RUN_SELECTION_POLICY_SCHEMA,
    MLCV_FULL_SELECTION_CANDIDATE_SCHEMA,
    MLCV_RUN_SELECTION_RECORD_SCHEMA,
    MlcvRunSelectionPolicy,
    MlcvFullSelectionCandidateRecord,
    MlcvRunSelectionRecord,
    assess_mlcv_full_selection_candidate,
    select_mlcv_run_representative,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .mlcv_aggregate import (
    MLCV_CV_POLICY_SCHEMA,
    MLCV_OUTER_FOLD_EVALUATION_SCHEMA,
    MLCV_METRIC_SUMMARY_SCHEMA,
    MLCV_SEED_CV_AGGREGATE_SCHEMA,
    MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA,
    MlcvCrossValidationPolicy,
    MlcvOuterFoldEvaluationRecord,
    MlcvMetricSummary,
    MlcvSeedCvAggregateRecord,
    MlcvCampaignCvAggregateRecord,
    build_mlcv_outer_fold_record,
    summarize_mlcv_fold_metric,
    aggregate_mlcv_seed_cv,
    aggregate_mlcv_campaign_cv,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))


from .mlcv_final import (
    MLCV_FINAL_SELECTION_POLICY_SCHEMA,
    MLCV_FINAL_SEED_CANDIDATE_SCHEMA,
    MLCV_FINAL_SELECTION_RECORD_SCHEMA,
    MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA,
    MLCV_FINAL_COMMITTEE_SCHEMA,
    MlcvFinalSelectionPolicy,
    MlcvFinalSeedCandidateRecord,
    MlcvFinalSelectionRecord,
    MlcvFinalCommitteeMemberRecord,
    MlcvFinalCommitteeRecord,
    build_mlcv_final_selection,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .adaptive_full_evaluation import (
    ADAPTIVE_FULL_EVALUATION_POLICY_SCHEMA,
    CAMPAIGN_FINALIST_QUEUE_SCHEMA,
    FULL_EVALUATION_CANDIDATE_SCHEMA,
    ADAPTIVE_FULL_EVALUATION_RECORD_SCHEMA,
    AdaptiveFullEvaluationPolicy,
    CampaignFinalistCandidate,
    CampaignFinalistQueueRecord,
    FullEvaluationCandidateRecord,
    AdaptiveFullEvaluationRecord,
    build_campaign_finalist_queue,
    assess_full_evaluation_candidate,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .adaptive_verification import (
    ADAPTIVE_VERIFICATION_POLICY_SCHEMA,
    ADAPTIVE_VERIFICATION_CANDIDATE_SCHEMA,
    ADAPTIVE_VERIFICATION_RECORD_SCHEMA,
    ADAPTIVE_DEPLOYMENT_MODEL_SCHEMA,
    ADAPTIVE_PROTOCOL_FREEZE_SCHEMA,
    AdaptiveVerificationPolicy,
    AdaptiveVerificationCandidateRecord,
    AdaptiveVerificationRecord,
    AdaptiveDeploymentModelRecord,
    AdaptiveProtocolFreezeRecord,
    ordered_admissible_candidates,
    verification_rejection_reasons,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .adaptive_migration import (
    PROTOCOL_FREEZE_AUTHORITY_SCHEMA,
    ADAPTIVE_MIGRATION_RECORD_SCHEMA,
    ADAPT_MIGRATE1_VERSION,
    ProtocolFreezeAuthorityRecord,
    AdaptiveMigrationRecord,
    protocol_freeze_authority_from_historical,
    protocol_freeze_authority_from_adaptive,
    protocol_freeze_authority_from_mlcv,
    protocol_freeze_authority_from_payload,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .mlcv_roles import (
    MLCV_FOLD_ROLE_RECORD_SCHEMA,
    MLCV_REPLAY_ROLE_LINEAGE_SCHEMA,
    MLCV_ROLE_AUTHORITY_VERSION,
    MLCV_ROLE_CATALOG_SCHEMA,
    MlcvDataRole,
    MlcvEvidenceOperation,
    MlcvFoldRoleRecord,
    MlcvReplayRoleLineage,
    MlcvRoleCatalog,
    build_mlcv_replay_role_lineage,
    build_mlcv_role_catalog,
    mlcv_role_allows,
    require_mlcv_checkpoint_ranking_role,
    require_mlcv_checkpoint_stopping_role,
    require_mlcv_role,
    require_mlcv_topk_selection_role,
    require_mlcv_outer_cv_evaluation_role,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .mlcv_monitors import (
    MLCV_MONITOR_POLICY_SCHEMA,
    MLCV_RUN_MONITOR_RECORD_SCHEMA,
    MLCV_REPLAY_MONITOR_RECORD_SCHEMA,
    MLCV_MONITOR_CATALOG_SCHEMA,
    MLCV_DIAGNOSTIC_HISTORY_SCHEMA,
    MlcvMonitorPolicy,
    MlcvRunMonitorRecord,
    MlcvReplayMonitorRecord,
    MlcvMonitorCatalog,
    sample_target_frames,
    build_run_monitor_record,
    build_replay_monitor_record,
    write_replay_light_subset,
    write_mlcv_diagnostic_history,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .mlcv_verification import (
    MLCV_VERIFICATION_POLICY_SCHEMA,
    MLCV_PHYSICAL_ATTEMPT_SCHEMA,
    MLCV_VERIFICATION_RECORD_SCHEMA,
    MLCV_LOCKED_TEST_RECORD_SCHEMA,
    MLCV_PRODUCTION_MODEL_SCHEMA,
    MlcvVerificationPolicy,
    MlcvPhysicalVerificationAttemptRecord,
    MlcvVerificationRecord,
    MlcvLockedTestRecord,
    MlcvProductionModelRecord,
    ordered_mlcv_physical_candidates,
    build_mlcv_verification_record,
    build_mlcv_locked_test_record,
    build_mlcv_production_model_record,
)

__all__ = [name for name in globals() if not name.startswith("_")]

from .mlcv_migration import (
    MLCV_LIFECYCLE_AUTHORITY_SCHEMA, MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA,
    MLCV_LIFECYCLE_AUTHORITY_VERSION, MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION,
    MLCV_PROTOCOL_FREEZE_SCHEMA, MLCV_PROTOCOL_FREEZE_LEGACY_SCHEMA,
    MLCV_MIGRATION_RECORD_SCHEMA, MLCV_MIGRATION_RECORD_LEGACY_SCHEMA,
    MLCV_MIGRATE1_VERSION, MLCV_MIGRATE1_LEGACY_VERSION,
    MLCV_CHECKPOINT_STRATEGY,
    MLCV_TRANSITIONAL_STRATEGY_ALIAS,
    MlcvLifecycleAuthorityRecord,
    MlcvProtocolFreezeRecord,
    MlcvMigrationRecord,
    build_mlcv_lifecycle_authority,
    mlcv_replay_semantics_stale_boundary,
)

__all__ = [name for name in globals() if not name.startswith("_")]


__all__ = [name for name in globals() if not name.startswith("_")]

from .train2_runtime import (
    TRAIN2_RUNTIME_PLAN_SCHEMA,
    TRAIN2_RUNTIME_SUMMARY_SCHEMA,
    TRAIN2_NUMERICAL_FAILURE_SCHEMA,
    TRAIN2_NUMERICAL_FAILURE_FILENAME,
    TRAIN2_NUMERICAL_FAILURE_CODES,
    TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
    TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
    TRAIN2_TRUE_REPLAY_LOG_HEAD,
    Train2RuntimePlan,
    Train2RuntimeSummary,
    Train2NumericalFailure,
    Train2NumericalFailureRecord,
    build_train2_runtime_plan,
    validate_train2_runtime_continuation_artifacts,
    load_train2_runtime_summary,
    load_train2_numerical_failure,
)

from .train2_policy import (
    TRAINING_BUDGET_POLICY_SCHEMA,
    LEARNING_RATE_SCHEDULE_POLICY_SCHEMA,
    CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA,
    CHECKPOINT_SELECTION_POLICY_SCHEMA,
    TRAIN2_POLICY_FAMILY,
    TRAIN2_DEFAULT_REPLAY_DEGRADATION_EV_PER_ANGSTROM,
    TRAIN2_DEFAULT_PRACTICAL_EQUIVALENCE_EV_PER_ANGSTROM,
    TRAIN2_DEFAULT_BOOTSTRAP_REPLICATES,
    TRAIN2_DEFAULT_BOOTSTRAP_CONFIDENCE,
    TRAIN2_DEFAULT_BOOTSTRAP_MIN_BLOCKS,
    TrainingBudgetPolicy,
    LearningRateSchedulePolicy,
    CheckpointAdmissibilityPolicy,
    CheckpointSelectionPolicy,
    validate_train2_policy_set,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .eval2 import (
    EVAL2_TRAJECTORY_POINT_SCHEMA,
    EVAL2_TARGET_BLOCK_METRIC_SCHEMA,
    EVAL2_TARGET_METRIC_SCHEMA,
    EVAL2_CHECKPOINT_RECORD_SCHEMA,
    EVAL2_BOOTSTRAP_COMPARISON_SCHEMA,
    EVAL2_RUN_RECORD_SCHEMA,
    EVAL2_EVALUATION_PLAN_SCHEMA,
    EVAL2_TARGET_ROLE_SCHEMA,
    EVAL2_NUMERICAL_FAILURE_SCHEMA,
    EVAL2_NUMERICAL_FAILURE_CODES,
    Eval2NumericalEvaluationError,
    Eval2TargetRole,
    Eval2TrajectoryPoint,
    Eval2TargetBlockMetric,
    Eval2TargetMetricRecord,
    Eval2CheckpointRecord,
    Eval2BootstrapComparison,
    Eval2EvaluationPlan,
    Eval2RunRecord,
    build_eval2_size_study_target_role,
    build_eval2_coarse_size_study_target_role,
    build_eval2_cv_target_role,
    build_eval2_shortlist,
    eval2_target_metrics_from_prediction_view,
    assess_eval2_checkpoint,
    paired_block_bootstrap_compare,
    order_eval2_admissible_candidates,
    build_eval2_run_record,
    read_train2_trajectory_points,
    next_eval2_checkpoint_batch,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .deploy_verify import (
    DEPLOY_VERIFY_IMPLEMENTATION_VERSION,
    DeployVerifyPolicy,
    DeployVerifyProbeSet,
    DeployVerifyComparison,
    LammpsRun0Record,
    TargetHeadDeploymentIdentity,
    MliapExportRuntimeCapability,
    probe_mliap_export_runtime,
    DeployVerifyRunRecord,
    DeployVerifyCampaignRecord,
    build_deploy_verify_probe_set,
    target_head_export_digest,
    compare_prediction_channels,
    predict_mace_model_on_probe,
    export_mliap_lammps_artifact,
    run_lammps_mliap_run0,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .pes_verify import (
    PES_VERIFY_IMPLEMENTATION_VERSION,
    PESVerifyPolicy,
    PESProbeMode,
    PESProbeGeometry,
    PESProbeSet,
    PESProbeRequestArtifact,
    PESReferenceArtifact,
    PESModeMetric,
    PESModelQualification,
    PESVerifyRunRecord,
    PESVerifyCampaignRecord,
    discover_pes_probe_modes,
    build_pes_probe_set,
    write_pes_probe_request,
    load_pes_reference_extxyz,
    collect_pes_reference_from_vasp,
    prediction_payload_from_mace_view,
    assess_pes_model,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .relax_verify import (
    RELAX_VERIFY_IMPLEMENTATION_VERSION,
    RelaxVerifyPolicy,
    RelaxBaseSet,
    RelaxRequestArtifact,
    RelaxReferenceArtifact,
    RelaxBaseMetric,
    RelaxModelQualification,
    RelaxVerifyRunRecord,
    RelaxVerifyCampaignRecord,
    build_relax_base_set,
    write_relax_reference_request,
    load_relax_reference_extxyz,
    collect_relax_reference_from_vasp,
    assess_relaxed_geometry,
    create_mace_relax_calculator,
    relax_atoms_with_calculator,
    relax_mace_model,
    write_relaxed_model_artifact,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .dyn_verify import (
    DYN_VERIFY_IMPLEMENTATION_VERSION,
    DynVerifyPolicy,
    DynVerifyPlan,
    DynCaseMetric,
    DynCaseCompletionReceipt,
    DynCaseSimulationArtifacts,
    DynVerifyRunRecord,
    DynVerifyCampaignRecord,
    build_dyn_verify_plan,
    assess_dyn_trajectory,
    write_dyn_case_completion_receipt,
    reusable_dyn_case_metric,
    run_lammps_mliap_dynamics_case,
    simulate_lammps_mliap_dynamics_case,
    reduce_lammps_mliap_dynamics_case,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .select2 import (
    SELECT2_VERSION,
    SELECT2_CANDIDATE_SCHEMA,
    SELECT2_SELECTION_SCHEMA,
    SELECT2_FROZEN_CANDIDATE_SCHEMA,
    Select2CandidateRecord,
    Select2SelectionRecord,
    Select2FrozenCandidateRecord,
    build_select2_selection,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .locked_test2 import (
    LOCKED_TEST2_VERSION,
    LOCKED_TEST2_POLICY_SCHEMA,
    LOCKED_TEST2_ACTIVATION_SCHEMA,
    LOCKED_TEST2_RESULT_SCHEMA,
    LOCKED_TEST2_PRODUCTION_SCHEMA,
    LockedTest2Policy,
    LockedTest2ActivationRecord,
    LockedTest2ResultRecord,
    LockedTest2ProductionModelRecord,
    build_locked_test2_result,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .performance_baseline import (
    PERF_BASE0_VERSION,
    PERF_BASE0_ARRAY_SCHEMA,
    PERF_BASE0_JSON_SCHEMA,
    PERF_BASE0_ARTIFACT_SCHEMA,
    PERF_BASE0_CORPUS_SCHEMA,
    PERF_BASE0_SCIENTIFIC_STAGE_SCHEMA,
    PERF_BASE0_TELEMETRY_SCHEMA,
    PERF_BASE0_RECORD_SCHEMA,
    PERF_BASE0_COMPARISON_SCHEMA,
    PerfBase0ArrayReference,
    PerfBase0JsonReference,
    PerfBase0ArtifactIdentity,
    PerfBase0CorpusIdentity,
    PerfBase0ScientificStage,
    PerfBase0ExecutionTelemetry,
    PerfBase0Record,
    PerfBase0Comparison,
    PerfBase0StageMeter,
    perf_base0_runtime_environment,
    compare_perf_base0_records,
    assert_perf_base0_scientific_equivalence,
    write_perf_base0_record,
    read_perf_base0_record,
    render_perf_base0_markdown,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .perfbase1 import (
    PERFBASE1_VERSION,
    PERFBASE1_TRIAL_SCHEMA,
    PERFBASE1_WORKLOAD_SCHEMA,
    PERFBASE1_RECORD_SCHEMA,
    PerfBase1Trial,
    PerfBase1Workload,
    PerfBase1Record,
    PerfBase1TrialMeter,
    write_perfbase1_record,
    read_perfbase1_record,
    render_perfbase1_markdown,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .perf_p2r import (
    PERF_P2R_PARAMETER_GRID_SCHEMA,
    PERF_P2R_STAGE_PLAN_SCHEMA,
    PERF_P2R_EXPOSURE_SCHEMA,
    PerfP2RParameterGrid,
    PerfP2RStagePlan,
    PerfP2RExposure,
    build_perf_p2r_stage_plan,
    build_perf_p2r_exposure,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .final_gpu1 import (
    FINAL_GPU1_POLICY_SCHEMA,
    FINAL_GPU1_EVIDENCE_SCHEMA,
    FINAL_GPU1_QUALIFICATION_SCHEMA,
    FINAL_GPU1_VERSION,
    FINAL_GPU1_REQUIRED_PASS_GATES,
    FINAL_GPU1_MEASURE_ONLY_GATES,
    FINAL_GPU1_OPTIONAL_GATES,
    FINAL_GPU1_RUNTIME_BOUND_GATES,
    FINAL_GPU1_LOCKED_FOUNDATION_SHA256,
    FinalGpu1Policy,
    FinalGpu1EvidenceRecord,
    FinalGpu1QualificationRecord,
    build_final_gpu1_qualification,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))


__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))


__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))


__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))



__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .replay_index import (
    DEFAULT_REPLAY_INDEX_PARSE_CHUNK_SIZE,
    EXTXYZ_SOURCE_INDEX_RECEIPT_SCHEMA,
    EXTXYZ_SOURCE_INDEX_SCHEMA,
    REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA,
    REPLAY_SOURCE_INDEX_SCHEMA,
    ExtxyzSourceIndex,
    ReplaySourceIndex,
    build_extxyz_source_index,
    build_replay_source_index,
    iter_indexed_extxyz_frames,
    iter_indexed_replay_frames,
    replay_source_indices_for_identities,
    validate_extxyz_source_index,
    validate_replay_source_index,
)

from .artifact_staging import (
    IMMUTABLE_ARTIFACT_STAGE_SCHEMA,
    ImmutableArtifactStage,
    stage_immutable_artifact,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

from .replay_invalidation import (
    REPLAY_INVALIDATION_PLAN_SCHEMA,
    REPLAY_INVALIDATION_VERSION,
    ReplayInvalidationPlan,
    build_replay_invalidation_plan,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))

# TARGET-DATA2C-MVQUAL2 direct fixed-universe authority for target-size v5.
from .target_multi_view_qualification_v2 import (
    TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION,
    TARGET_MULTI_VIEW_QUALIFICATION_V2_POLICY_SCHEMA,
    TARGET_MULTI_VIEW_QUALIFICATION_V2_RUNG_SCHEMA,
    TARGET_MULTI_VIEW_QUALIFICATION_V2_DOMAIN_SCHEMA,
    TARGET_MULTI_VIEW_QUALIFICATION_V2_PLAN_SCHEMA,
    TargetMultiViewQualificationPolicyV2,
    TargetMultiViewQualificationRungV2,
    TargetMultiViewQualificationDomainPlanV2,
    TargetMultiViewQualificationPlanV2,
    build_target_multi_view_qualification_plan_v2,
    validate_target_multi_view_qualification_authority_v2,
)
from .target_size_study import (
    TARGET_SIZE_STUDY_VERSION,
    TARGET_SIZE_STUDY_POLICY_SCHEMA,
    TARGET_SIZE_STUDY_CANDIDATE_SCHEMA,
    TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA,
    TARGET_SIZE_TRAJECTORY_FAILURE_EVIDENCE_SCHEMA,
    TARGET_SIZE_STAGE_OUTCOME_SCHEMA,
    TARGET_SIZE_STUDY_PLAN_SCHEMA,
    TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA,
    TARGET_SIZE_CANDIDATE_AUTHORITY_GENERATION,
    LEGACY_FIXED_CANDIDATE_AUTHORITY_SCHEMA,
    LEGACY_FIXED_CANDIDATE_AUTHORITY_GENERATION,
    FIXED_TARGET_SIZES,
    FIXED_TARGET_SIZE_CEILING,
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_AWAITING_COARSE_SCREEN,
    OUTCOME_AWAITING_SHORT_SCREEN,
    OUTCOME_AWAITING_FINAL_SCREEN,
    OUTCOME_SELECTED,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
    STAGE_COARSE,
    STAGE_SHORT,
    STAGE_FINAL_SCREEN,
    FAILURE_PHASE_TRAIN,
    FAILURE_PHASE_TARGET_EVALUATION,
    TARGET_SIZE_SCIENTIFIC_FAILURE_CODES,
    TargetSizeStudyPolicy,
    TargetSizeStudyCandidate,
    TargetSizeTrainingEvidence as TargetSizeStudyTrainingEvidence,
    TargetSizeTrajectoryFailureEvidence,
    TargetSizeStageOutcome,
    TargetSizeStudyPlan,
    build_target_size_study,
    validate_target_size_study_authority,
    authenticated_fixed_predecessor_candidate_authority,
    HISTORICAL_FIXED_CANDIDATE_AUTHORITY_RECEIPT_SCHEMA,
    materialize_candidate_prefix,
    materialize_candidate_prefix_matrix,
    materialize_selected_prefix,
    attach_coarse_outcomes,
    attach_short_outcomes,
    attach_final_screen_outcomes,
    attach_coarse_evidence,
    attach_short_evidence,
    attach_final_screen_evidence,
)

__all__ = sorted(set([name for name in globals() if not name.startswith("_")] + list(_LAZY_LTA_EXPORTS)))
