---
memory_schema_version: 1
maintained_under_protocol: 6.3.0
project_id: hjin98-mdstats
repository: hjin98/mdstats
scope: repository
coverage_state: PARTIAL
coverage_basis: "Bounded historical backfill over accepted MLFF campaign/target-size development from August 20 through September 12, 2026. Reviewed archived P1-P7 target-size/campaign workplans and implementation evidence, TRAIN2/EVAL2 architecture and restart repairs, storage-reset R28-R38, scheduler/CUDA lifetime and memory-pressure repairs, assembled campaign/storage integration, and accepted-current architecture/code at b65fa3b02807815d8eca758bc04fb70d514d1f45. Earlier mdstats history, non-MLFF subsystems, and unarchived local incidents are not claimed exhaustive."
reconciled_through: b65fa3b02807815d8eca758bc04fb70d514d1f45
accepted_base:
  project_state: b65fa3b02807815d8eca758bc04fb70d514d1f45
  basis: "Accepted mdstats main baseline at PEM initialization. No prior canonical Protocol 6.3 project PEM exists in the repository."
candidate_overlay: "fix/mlff-p5-train2-eval2-cueq-architecture-recurrence candidate overlay; publication identity is the containing Git commit and is not self-declared accepted."
detail_files: []
---

# Project Engineering Memory

This is mdstats' project-local Project Engineering Memory (PEM). It records evidence-backed recurring failures, successful engineering patterns, and current notices. It is not D1-D4 semantic authority. Current scientific, numerical, architectural, specification, project, and external owners define what must be true. Because this first backfill is deliberately partial, absence here does not establish that no relevant historical lesson exists.

## Active summary

<!-- BEGIN DERIVED PEM SUMMARY -->
High-impact unresolved notices:

- **NT-001** [REVIEW_REQUIRED/HEALTHY]: A current real P5 cross-validation run completed TRAIN2 but failed before EVAL2 because the persisted TRAIN2 CuEq architecture digest differs from independent reconstruction; historical FF-001 is materially relevant, but exact recurrence membership and repair ownership remain subject to the active diagnostic gates.

| ID | Kind | Temperature | Maturity/state | Binding | Guidance | Current evidence | Bounded lesson |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SP-002 | SUCCESS_PATTERN | HOT | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | RECOMMENDED | 3 supporting / 0 neutral / 0 contradicting / 0 inconclusive | Fail-closed authenticated identity/state boundaries catch corruption and semantic drift before downstream consumers can act on plausible-but-wrong data. |
| SP-003 | SUCCESS_PATTERN | HOT | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | RECOMMENDED | 3 supporting / 0 neutral / 0 contradicting / 0 inconclusive | Immutable/content-addressed durable boundaries make expensive workflows restartable and reusable without reconstructing or retraining already accepted work. |
| SP-004 | SUCCESS_PATTERN | HOT | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | RECOMMENDED | 3 supporting / 0 neutral / 0 contradicting / 0 inconclusive | Real-owner integration and target-host qualification expose defects that mocks, local unit seams, or isolated component tests can miss. |
| SP-001 | SUCCESS_PATTERN | WARM | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | RECOMMENDED | 2 supporting / 0 neutral / 0 contradicting / 0 inconclusive | Removing duplicated machinery and returning responsibility to the real owner has repeatedly fixed broad defect families with less state, policy, and code than additive synchronization or wrapper repairs. |
| FF-001 | FAILURE_FAMILY | UNASSESSED | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | OBSERVED | 1 confirmed | Independently reconstructed MACE execution architecture can drift from the model actually trained when model-affecting construction or accelerator realization is duplicated across owners. |
| FF-002 | FAILURE_FAMILY | UNASSESSED | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | OBSERVED | 1 confirmed | Restart correctness fails when scratch, continuation metadata, or checkpoint state is treated as durable authority before the exact authenticated boundary has been established. |
| FF-003 | FAILURE_FAMILY | UNASSESSED | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | OBSERVED | 1 confirmed | Duplicated destructive-storage routing and negative fallthrough can let consequential mutation escape the owner that actually holds authorization and truth about the target. |
| FF-004 | FAILURE_FAMILY | UNASSESSED | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | OBSERVED | 1 confirmed | GPU admission, cancellation, and teardown become unreliable when scheduler policy is allowed to infer facts owned by the process/run owner or when live memory safety is not enforced at the actual residency boundary. |
| FF-005 | FAILURE_FAMILY | UNASSESSED | SUPPORTED/CURRENT | EVIDENCE_ONLY/HEALTHY | OBSERVED | 1 confirmed | Downstream observation/selection commands become expensive and semantically leaky when they reconstruct preparation-owned scientific state instead of consuming an immutable prepared generation. |
<!-- END DERIVED PEM SUMMARY -->

## Families

### FF-001 — Realized-model identity drift across duplicated construction paths

```yaml pem-family
id: FF-001
kind: FAILURE_FAMILY
state: CURRENT
maturity: SUPPORTED
temperature: UNASSESSED
summary: Independently reconstructed MACE execution architecture can drift from the model actually trained when model-affecting construction or accelerator realization is duplicated across owners.
semantic_identity:
  invariant_or_claim: A checkpoint may be admitted to EVAL2 only when independently reconstructed training-realization identity matches the execution architecture that actually owned TRAIN2 state.
  owner_class: TRAIN2/EVAL2 model-construction and checkpoint-authentication boundary
  mechanism_family: duplicated or incomplete reconstruction of model-affecting MACE configuration and transient accelerator realization
  applicability_dimensions: MACE 0.3.16, target-size P3/P5, multihead/foundation models, avg_num_neighbors, CuEq/OEq realization, architecture digests
aggregation_scope: mdstats MACE training/evaluation paths that independently reconstruct a model before authenticated checkpoint state is loaded
coverage_state: PARTIAL
coverage_basis: Reviewed the archived P3 realized-architecture repair/evidence and the later P5 phase-separated CuEq architecture analysis through accepted baseline b65fa3b; broader MACE history is not claimed exhaustive.
applicability:
  - TRAIN2 EVAL2 architecture digest mismatch
  - independent MACE reconstruction
  - CuEq realization
  - foundation or replay head realization
  - avg_num_neighbors
  - checkpoint provider authentication
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: OBSERVED
relations: []
occurrences:
  - id: O01
    event_identity: "hjin98/mdstats@a06e67525a40c2d4e8217fe99bf4ca6821e0ce84"
    lifecycle_context: target-size P3 realized-MACE architecture repair
    source_project: local
    surfaces:
      - P3 TRAIN2 construction
      - independent EVAL2 reconstruction
      - MACE head/default construction
      - model-affecting normalization and calibration buffers
    observation: A bounded real pinned-MACE construction census found four concrete pre-repair differences between the model MACE realized and mdstats' independent reconstruction: head identity, avg_num_neighbors, scale/shift shape, and atomic-energy shape.
    cause_claim: Model-affecting construction semantics were represented in more than one path, allowing the independent reconstruction to diverge from the model that actually owned training state.
    cause_evidence:
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-target-size-v7-packages/P3_TRAIN2_EVAL2_REALIZED_MACE_ARCHITECTURE_IMPLEMENTATION_EVIDENCE.md"
    repair: NONE
    repair_acceptance: NONE
    provenance_cluster: p3-realized-mace-architecture
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: CONFIRMED
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-target-size-v7-packages/P3_TRAIN2_EVAL2_REALIZED_MACE_ARCHITECTURE_IMPLEMENTATION_EVIDENCE.md"
```

### FF-002 — Continuation authority admitted before an authenticated restart boundary

```yaml pem-family
id: FF-002
kind: FAILURE_FAMILY
state: CURRENT
maturity: SUPPORTED
temperature: UNASSESSED
summary: Restart correctness fails when scratch, continuation metadata, or checkpoint state is treated as durable authority before the exact authenticated boundary has been established.
semantic_identity:
  invariant_or_claim: A resumed TRAIN2/target-size execution must continue only from authenticated durable state belonging to the exact run and boundary; uncommitted scratch must never masquerade as continuation authority.
  owner_class: target-size/TRAIN2 persistence and restart ownership
  mechanism_family: premature reuse or incomplete binding of continuation state across interruption/restart
  applicability_dimensions: first-rung interruption, boundary summaries, continuation companions, raw checkpoints, restart epoch handoff, resume after process failure
aggregation_scope: mdstats target-size and post-selection training continuation paths
coverage_state: PARTIAL
coverage_basis: Reviewed first-rung restart-gap repair, corrupt-component restart matrix, and restart-epoch repair lineage through accepted baseline b65fa3b; earlier restart history is not exhaustive.
applicability:
  - restart
  - resume
  - continuation companion
  - checkpoint boundary
  - restart epoch
  - interrupted training
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: OBSERVED
relations: []
occurrences:
  - id: O01
    event_identity: "hjin98/mdstats@0c57ef6e36b9d06aad0af1f244466b23a49602bf"
    lifecycle_context: target-size restart and durable-state integration repair
    source_project: local
    surfaces:
      - first-rung workspace
      - TRAIN2 runtime summary
      - continuation companion
      - raw MACE checkpoint
      - restart epoch handoff
    observation: An interrupted first rung could leave partial checkpoint bytes in a deterministic workspace that a retry then reused even though no authenticated continuation boundary existed; later falsification also exposed corrupt-summary and restart-epoch handoff defects.
    cause_claim: The continuation path did not uniformly distinguish uncommitted scratch from exact authenticated durable boundary state.
    cause_evidence:
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_TARGET_SIZE_MACE_RESTART_EPOCH_HANDOFF_BUGFIX_WORKPLAN.md"
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/train2_runtime.py"
    repair: NONE
    repair_acceptance: NONE
    provenance_cluster: train2-restart-boundary
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: CONFIRMED
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_TARGET_SIZE_MACE_RESTART_EPOCH_HANDOFF_BUGFIX_WORKPLAN.md"
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/train2_runtime.py"
```

### FF-003 — Destructive-storage authority duplicated across routing and fallback paths

```yaml pem-family
id: FF-003
kind: FAILURE_FAMILY
state: CURRENT
maturity: SUPPORTED
temperature: UNASSESSED
summary: Duplicated destructive-storage routing and negative fallthrough can let consequential mutation escape the owner that actually holds authorization and truth about the target.
semantic_identity:
  invariant_or_claim: Consequential storage mutation must be authorized continuously by the exact current owner and executed through one destructive path that preserves target identity, mutation truth, and durability semantics.
  owner_class: campaign storage cleanup/removal architecture
  mechanism_family: duplicated cleanup engines, negative fallthrough, pathname re-discovery, and split mutation/accounting authority
  applicability_dimensions: cleanup, recursive removal, owner-scoped artifacts, P7 released attempts, filesystem identity, interruption, partial mutation
aggregation_scope: mdstats campaign storage cleanup and destructive mutation implementation
coverage_state: PARTIAL
coverage_basis: Reviewed storage reset revision 28 through revision 38, implementation reopens, and assembled P1-P7 storage integration through accepted baseline b65fa3b; pre-R28 storage history is not exhaustive.
applicability:
  - storage cleanup
  - destructive mutation
  - recursive removal
  - owner authorization
  - filesystem identity
  - partial mutation truth
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: OBSERVED
relations: []
occurrences:
  - id: O01
    event_identity: "hjin98/mdstats@d18a8252400ca557a5ebd8d389ed053d6bba4b2f"
    lifecycle_context: storage I/O reset review/reduction lineage
    source_project: local
    surfaces:
      - StorageExecutor cleanup routing
      - generic/default cleanup engine
      - owner-specific removal
      - P7 released-attempt cleanup
      - recursive filesystem traversal
      - mutation accounting and fsync
    observation: Repeated independent review found that duplicated cleanup routing/destructive paths could classify unknown owner state as generic, lose live authority between check and mutation, or report mutation/bytes inaccurately.
    cause_claim: One destructive invariant was represented by multiple routing and mutation owners; negative fallthrough and pathname-based rediscovery forced synchronization machinery while still leaving semantic gaps.
    cause_evidence:
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
    repair: NONE
    repair_acceptance: NONE
    provenance_cluster: storage-reset-r28-r38
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: CONFIRMED
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
```

### FF-004 — Resource-control decisions inferred outside the process/residency owner

```yaml pem-family
id: FF-004
kind: FAILURE_FAMILY
state: CURRENT
maturity: SUPPORTED
temperature: UNASSESSED
summary: GPU admission, cancellation, and teardown become unreliable when scheduler policy is allowed to infer facts owned by the process/run owner or when live memory safety is not enforced at the actual residency boundary.
semantic_identity:
  invariant_or_claim: TRAIN2 resource admission may control scheduling, but child-process outcome, teardown completion, and live accelerator residency must be established by the owners that actually hold those resources.
  owner_class: P5 TRAIN scheduler, TRAIN2 process supervision, and CUDA residency lifetime
  mechanism_family: cross-layer resource inference, delayed residency release, and scheduler-owned timing/classification of process-local facts
  applicability_dimensions: CUDA TRAIN2 concurrency, memory pressure, cancellation, demotion/backoff, child reaping, EVAL2 phase transition
aggregation_scope: P5 TRAIN2 GPU scheduling and process/resource lifetime repairs
coverage_state: PARTIAL
coverage_basis: Reviewed zero-safe admission workplan, two memory-pressure reopen passes, final review closure, and target-host evidence through accepted baseline b65fa3b; earlier scheduler history is not exhaustive.
applicability:
  - CUDA OOM
  - TRAIN scheduler
  - memory-pressure backoff
  - cancellation teardown
  - child process ownership
  - CUDA lifetime
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: OBSERVED
relations: []
occurrences:
  - id: O01
    event_identity: "hjin98/mdstats@f8755f05d35a6327608be76aba73a8e31f065f9d"
    lifecycle_context: P5 TRAIN2 CUDA lifetime, zero-safe admission, and memory-pressure backoff cycle
    source_project: local
    surfaces:
      - adaptive TRAIN admission
      - live VRAM safety
      - run cancellation/demotion
      - child process teardown
      - TRAIN-to-EVAL2 phase boundary
    observation: A real N=512 campaign reached OOM/resource-safety failure; later reviews exposed additional cases where scheduler intent/timing could misclassify process outcomes or active memory residency.
    cause_claim: Scheduling policy and process/resource ownership were not cleanly separated at every boundary, so admission/backoff logic sometimes inferred teardown, cancellation, or memory safety instead of observing it from the responsible owner.
    cause_evidence:
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md"
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FINAL_REVIEW_CLOSURE.md"
    repair: NONE
    repair_acceptance: NONE
    provenance_cluster: p5-train2-cuda-resource-cycle
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: CONFIRMED
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FINAL_REVIEW_CLOSURE.md"
```

### FF-005 — Downstream command reconstructs preparation-owned state

```yaml pem-family
id: FF-005
kind: FAILURE_FAMILY
state: CURRENT
maturity: SUPPORTED
temperature: UNASSESSED
summary: Downstream observation/selection commands become expensive and semantically leaky when they reconstruct preparation-owned scientific state instead of consuming an immutable prepared generation.
semantic_identity:
  invariant_or_claim: Preparation owns construction of expensive scientific substrate; downstream selection, status, and execution should consume the accepted prepared generation rather than re-read live sources or rebuild upstream state merely to establish currentness.
  owner_class: campaign preparation/currentness and downstream observation/control flow
  mechanism_family: downstream reconstruction of upstream scientific graph from live source/configuration
  applicability_dimensions: prepare, select-target-size, status, DATA4/source restoration, currentness checks, content-addressed prepared generations
aggregation_scope: MLFF campaign prepared-generation and downstream command routing
coverage_state: PARTIAL
coverage_basis: Reviewed prepared-generation repair and assembled P1-P7 integration evidence through accepted baseline b65fa3b; earlier preparation implementations are not exhaustive.
applicability:
  - prepare
  - select-target-size
  - status
  - redundant preparation
  - DATA4 restore
  - live source reread
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: OBSERVED
relations: []
occurrences:
  - id: O01
    event_identity: "hjin98/mdstats@e5c55b5b9662035e96ef9084d5b5c918c8335dd8"
    lifecycle_context: prepared-generation stage-boundary repair
    source_project: local
    surfaces:
      - prepare
      - select-target-size
      - campaign status
      - qualification status
      - prepared frame/component cache
    observation: Downstream commands rebuilt the scientific graph from live inputs simply to prove currentness, making observation/selection O(dataset) and dependent on sources they did not own.
    cause_claim: The campaign persisted identities of preparation components but not one immutable prepared generation that downstream consumers could authenticate and load directly.
    cause_evidence:
      - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
    repair: NONE
    repair_acceptance: NONE
    provenance_cluster: prepared-generation-stage-boundary
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: CONFIRMED
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
```

### SP-001 — Repair at the owning layer by reduction and consolidation

```yaml pem-family
id: SP-001
kind: SUCCESS_PATTERN
state: CURRENT
maturity: SUPPORTED
temperature: WARM
summary: Removing duplicated machinery and returning responsibility to the real owner has repeatedly fixed broad defect families with less state, policy, and code than additive synchronization or wrapper repairs.
semantic_identity:
  invariant_or_claim: When one invariant is split across duplicated implementations or cross-layer policy, consolidating the behavior under the real owner can close the defect family while reducing synchronization and representation burden.
  owner_class: D3/D4 ownership and implementation topology
  mechanism_family: deletion/rewiring/consolidation onto one semantic or resource owner
  applicability_dimensions: duplicated cleanup paths, scheduler/process ownership, redundant policy fields, wrapper/fallback accumulation
aggregation_scope: accepted mdstats repair cycles where the implemented fix materially reduced competing ownership rather than adding another compatibility mechanism
coverage_state: PARTIAL
coverage_basis: Reviewed supporting implementations and the failed/reopened intermediate states in storage R28-R38 and TRAIN2 memory-pressure backoff; no materially contradicting accepted episode was found in those bounded lineages.
applicability:
  - duplicate owner
  - fallback path
  - wrapper accumulation
  - redundant policy
  - simplify by deletion
  - move responsibility to owner
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: RECOMMENDED
positive_guidance_eligible: true
counterevidence_search:
  state: COMPLETE_FOR_DECLARED_SCOPE
  scope: storage R28-R38 and P5 TRAIN2 memory-pressure/backoff repair lineages
  search_basis: Reviewed final supporting repairs plus intermediate independent-review reopens and no-pass states for evidence that consolidation/reduction caused loss of required behavior or required additive shadow machinery.
  outcomes_reviewed: [SUPPORTING, NEUTRAL, CONTRADICTING, INCONCLUSIVE]
  blind_spots: Earlier storage/scheduler history and unrelated mdstats subsystems were not exhaustively searched.
  evidence:
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FINAL_REVIEW_CLOSURE.md"
relations: []
applications:
  - id: A01
    episode_identity: "hjin98/mdstats@a8d229b480e0a37e266c92a934c87028f98470d7"
    lifecycle_context: storage Revision 38 simplification consolidation
    source_project: local
    surfaces:
      - cleanup routing
      - destructive removal implementation
      - owner authorization
      - storage tests/specification
    provenance_cluster: storage-r38-reduction
    subject: remove duplicate cleanup classifier/default destructive engine and route consequential cleanup through one owner-backed removal implementation
    comparator: pre-R38 duplicated cleanup engines and synchronization machinery
    intended_benefit: Preserve the accepted safety envelope while reducing competing destructive authorities and synchronization burden.
    outcome: SUPPORTING
    observation: The final reduction removed the alternate destructive path and associated classifier/synchronization machinery while retaining accepted cleanup safety semantics.
    quantitative_effect: "Approximately one thousand product-source lines removed according to the accepted repair record."
    uncertainty: Bounded to the storage cleanup architecture; not evidence that deletion is always the correct repair.
    costs_tradeoffs: Required specification reconciliation and focused/assembled regression after topology reduction.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
  - id: A02
    episode_identity: "hjin98/mdstats@04bd758b3f72ae021d4d84cceeef4ab11540f63c"
    lifecycle_context: TRAIN2 memory-pressure backoff second review closure
    source_project: local
    surfaces:
      - scheduler demotion barrier
      - run cancellation
      - child-process teardown
      - concurrency policy
    provenance_cluster: train2-backoff-owner-reduction
    subject: delete scheduler-side teardown deadline/policy and keep child termination timing/classification in the actual process/run owner
    comparator: scheduler inference using a cross-layer teardown deadline
    intended_benefit: Prevent false terminal resource errors while preserving a strict reuse barrier and bounded child reaping.
    outcome: SUPPORTING
    observation: The repaired design eliminated the false cross-layer timeout, preserved explicit cancellation semantics, and closed the final review blockers without adding another watchdog or queue.
    quantitative_effect: NONE
    uncertainty: Bounded to the TRAIN2 scheduling/process-ownership defect family.
    costs_tradeoffs: Required additional race and structural falsification tests after the first repair proved incomplete.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_MEMORY_PRESSURE_BACKOFF_AND_TERMINAL_INFEASIBILITY_FINAL_REVIEW_CLOSURE.md"
```

### SP-002 — Fail closed on authenticated identity and durable-state disagreement

```yaml pem-family
id: SP-002
kind: SUCCESS_PATTERN
state: CURRENT
maturity: SUPPORTED
temperature: HOT
summary: Fail-closed authenticated identity/state boundaries catch corruption and semantic drift before downstream consumers can act on plausible-but-wrong data.
semantic_identity:
  invariant_or_claim: Consequential consumers should act only after the relevant persisted identity, ancestry, and state have been independently authenticated; absence, corruption, staleness, and mismatch remain distinct typed outcomes.
  owner_class: persistence, currentness, and consumer-admission boundaries
  mechanism_family: canonical digest/identity binding plus independent revalidation before consequential use
  applicability_dimensions: TRAIN2 checkpoints, campaign CAS state, CV/currentness, storage target identity, restart components
aggregation_scope: accepted mdstats boundaries where persisted state gates consequential training/evaluation/storage transitions
coverage_state: PARTIAL
coverage_basis: Reviewed restart corruption matrix, canonical campaign-state/CAS design, and storage identity/mutation repairs including failed intermediate review states; no accepted counterexample was found in the declared scope.
applicability:
  - fail closed
  - digest mismatch
  - corrupt durable state
  - stale plan
  - currentness
  - exact identity
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: RECOMMENDED
positive_guidance_eligible: true
counterevidence_search:
  state: COMPLETE_FOR_DECLARED_SCOPE
  scope: TRAIN2 restart authentication, canonical target-size campaign state, and storage final-apply identity lineages
  search_basis: Reviewed supporting implementations together with the defects found by corruption/substitution counterfactuals and storage implementation reviews; searched for evidence that strict identity binding itself caused acceptance of wrong state or required bypass to preserve correct behavior.
  outcomes_reviewed: [SUPPORTING, NEUTRAL, CONTRADICTING, INCONCLUSIVE]
  blind_spots: Other mdstats persistence domains and historical pre-V7 implementations were not exhaustively searched.
  evidence:
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/train2_runtime.py"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:docs/arch_manuals/mlff_training_data_architecture.md"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
relations: []
applications:
  - id: A01
    episode_identity: "hjin98/mdstats@be442a5f42596ea9d08a31a71e8bd270b9f8082e"
    lifecycle_context: TRAIN2 restart corruption/falsification matrix
    source_project: local
    surfaces:
      - raw checkpoint
      - runtime summary
      - continuation companion
      - foreign candidate state
    provenance_cluster: train2-durable-auth-matrix
    subject: authenticate every restart-critical TRAIN2 component and reject corruption, deletion, or foreign substitution without fresh restart
    comparator: weaker parsing/existence checks and untyped corrupt-summary failure
    intended_benefit: Prevent a different trajectory or foreign state from being accepted as continuation of the same run.
    outcome: SUPPORTING
    observation: The assembled falsification matrix rejected deleted, corrupt, and foreign predecessor components and exposed/fixed an untyped JSON corruption path.
    quantitative_effect: NONE
    uncertainty: Evidence is strong for the bounded TRAIN2 restart component set, not every future persistence format.
    costs_tradeoffs: More explicit authentication and typed failure handling at restart boundaries.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/train2_runtime.py"
  - id: A02
    episode_identity: "hjin98/mdstats@c9ffc670212a3bdaea8a290886718768756a73c0"
    lifecycle_context: P4 canonical target-size campaign state
    source_project: local
    surfaces:
      - CampaignStore
      - canonical generation
      - transition identity
      - predecessor CAS
    provenance_cluster: target-size-campaign-cas
    subject: serialize campaign transitions through one mutable authority with exact predecessor compare-and-set and deterministic transition identity
    comparator: distributed mutable state without one exact predecessor authority
    intended_benefit: Make interrupted retries idempotent while rejecting divergent successors and stale writers.
    outcome: SUPPORTING
    observation: Campaign state gained one canonical generation/attempt authority, append-only transition lineage, and typed conflict behavior for changed authoritative references.
    quantitative_effect: NONE
    uncertainty: Bounded to campaign-state transitions, not a blanket prescription for all persistence.
    costs_tradeoffs: Introduced explicit transition identity and serialized SQLite write transaction at the canonical state boundary.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:docs/arch_manuals/mlff_training_data_architecture.md"
  - id: A03
    episode_identity: "hjin98/mdstats@3bb1ec3f94e52107b710c1d0990b0abc2b88e5fc"
    lifecycle_context: storage final-apply identity and durability hardening
    source_project: local
    surfaces:
      - live filesystem target identity
      - owner capability
      - descriptor-relative mutation
      - durability accounting
    provenance_cluster: storage-transition-exactness
    subject: carry live owner/target identity continuously from authorization through the exact mutation and durability boundary
    comparator: pathname-based re-discovery and post-hoc inference of what was mutated
    intended_benefit: Prevent replacement objects or ambiguous mutation outcomes from inheriting a stale plan's authority.
    outcome: SUPPORTING
    observation: Consequential cleanup was bound to opened descriptors and exact live identity, with mutation/durability truth reported from the transition that actually occurred.
    quantitative_effect: NONE
    uncertainty: Bounded to the storage destructive boundary.
    costs_tradeoffs: Required fd-relative acquisition, explicit mutation outcomes, and additional counterfactual tests.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-storage-io-reset/STORAGE_IO_MANAGEMENT_RESET_SIMPLICITY_CONSOLIDATION_REVISION_38.md"
```

### SP-003 — Durable immutable boundaries enable exact restart and reuse

```yaml pem-family
id: SP-003
kind: SUCCESS_PATTERN
state: CURRENT
maturity: SUPPORTED
temperature: HOT
summary: Immutable/content-addressed durable boundaries make expensive workflows restartable and reusable without reconstructing or retraining already accepted work.
semantic_identity:
  invariant_or_claim: Expensive completed work can be safely reused when its inputs, identity, and outputs are durably authenticated at a stable stage boundary that downstream owners consume directly.
  owner_class: campaign stage-boundary persistence and recovery
  mechanism_family: immutable/content-addressed publication plus exact ancestry/currentness authentication
  applicability_dimensions: prepared generation, completed CV folds, TRAIN2 summaries/checkpoints, restart/resume, storage retention
aggregation_scope: MLFF campaign stages with expensive preparation or training whose accepted outputs persist across process lifetimes
coverage_state: PARTIAL
coverage_basis: Reviewed prepared-generation integration, post-selection resume behavior, and TRAIN2 restart/resource repair evidence including failure cases; no accepted contradiction was found in the declared scope.
applicability:
  - immutable prepared generation
  - content addressed
  - resume without retraining
  - restart boundary
  - completed fold reuse
  - expensive stage reuse
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: RECOMMENDED
positive_guidance_eligible: true
counterevidence_search:
  state: COMPLETE_FOR_DECLARED_SCOPE
  scope: prepared-generation publication, post-selection completed-run reuse, and TRAIN2 summary/checkpoint restart boundaries
  search_basis: Reviewed successful reuse episodes together with interrupted-run, corrupt-component, stale/currentness, and storage-survival failure cases; searched for cases where reuse of authenticated accepted work itself produced wrong continuation.
  outcomes_reviewed: [SUPPORTING, NEUTRAL, CONTRADICTING, INCONCLUSIVE]
  blind_spots: Other expensive mdstats stages and historical persistence formats were not exhaustively searched.
  evidence:
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/campaign_post_selection_runtime.py"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md"
relations: []
applications:
  - id: A01
    episode_identity: "hjin98/mdstats@e5c55b5b9662035e96ef9084d5b5c918c8335dd8"
    lifecycle_context: prepared-generation stage-boundary repair
    source_project: local
    surfaces:
      - prepare
      - frame cache
      - select-target-size
      - status/qualification status
    provenance_cluster: prepared-generation-publication
    subject: publish one immutable content-addressed prepared generation and make downstream commands load it directly
    comparator: reconstructing the scientific graph from live sources on downstream commands
    intended_benefit: Make currentness cheap, restartable, and independent of source rereads outside the preparation owner.
    outcome: SUPPORTING
    observation: Assembled integration later measured select, resume, and status with zero DATA4 restores, zero source reads, and zero preparation builds while downstream consumers continued to load the current generation.
    quantitative_effect: "For the measured assembled commands: zero DATA4 restores, zero source reads, and zero preparation builds."
    uncertainty: Measured on the bounded assembled campaign used by the integration workplan.
    costs_tradeoffs: Requires immutable generation publication and append-only/content-addressed component retention.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
  - id: A02
    episode_identity: "hjin98/mdstats@50206bdccf0f637845f757ed9a4c8b91c3708d02"
    lifecycle_context: post-selection cross-validation and production resume
    source_project: local
    surfaces:
      - completed CV fold evidence
      - completed production run evidence
      - rerun scheduling
    provenance_cluster: post-selection-run-reuse
    subject: reauthenticate completed post-selection run evidence and exclude already accepted runs from relaunch
    comparator: retraining all runs after interruption
    intended_benefit: Resume interrupted campaigns without repeating expensive accepted training work.
    outcome: SUPPORTING
    observation: Completed folds/runs became reusable after exact run-plan and acceptance-predicate authentication rather than being retrained solely because the process restarted.
    quantitative_effect: NONE
    uncertainty: Benefit scales with amount of completed accepted work at interruption.
    costs_tradeoffs: Requires durable run evidence and exact currentness checks before reuse.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:mdstats/training_data/campaign_post_selection_runtime.py"
  - id: A03
    episode_identity: "hjin98/mdstats@7f64ca980698575bcb3f25e3fd69684e78fedc4d"
    lifecycle_context: TRAIN2 resource-failure recovery
    source_project: local
    surfaces:
      - TRAIN wave failure
      - authenticated TRAIN2 summary
      - next-invocation resume
      - EVAL2 phase admission
    provenance_cluster: train2-summary-restart-boundary
    subject: stop a failed TRAIN wave before EVAL2 while retaining authenticated completed TRAIN2 summaries as the restart boundary
    comparator: continuing into EVAL2 after TRAIN failure or discarding completed training evidence
    intended_benefit: Preserve completed valid work without allowing a failed wave to leak into evaluation.
    outcome: SUPPORTING
    observation: The repaired orchestration terminates/reaps on TRAIN failure and relies on authenticated TRAIN2 summaries so a healthy later invocation resumes without retraining accepted runs.
    quantitative_effect: NONE
    uncertainty: Bounded to the current P5 TRAIN2 summary/checkpoint contract.
    costs_tradeoffs: Requires strict phase separation and durable per-run summary authentication.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md"
```

### SP-004 — Qualify through real owners and real deployment regimes

```yaml pem-family
id: SP-004
kind: SUCCESS_PATTERN
state: CURRENT
maturity: SUPPORTED
temperature: HOT
summary: Real-owner integration and target-host qualification expose defects that mocks, local unit seams, or isolated component tests can miss.
semantic_identity:
  invariant_or_claim: Acceptance evidence for cross-boundary behavior is materially stronger when it executes the production owner chain and, where hardware semantics matter, the real target regime rather than substituting the decision owner itself.
  owner_class: testing/qualification at semantic-owner and deployment boundaries
  mechanism_family: assembled real-owner counterfactuals plus bounded target-host execution
  applicability_dimensions: MACE construction, CUDA memory behavior, restart, storage integration, campaign lifecycle, orchestration
aggregation_scope: mdstats qualification episodes where production-owner composition or target hardware materially affected correctness
coverage_state: PARTIAL
coverage_basis: Reviewed P3 real-MACE architecture evidence, assembled P1-P7 storage/campaign integration, and P5 target-host CUDA qualification including failed intermediate review rounds; no accepted counterexample was found in the declared scope.
applicability:
  - real owner integration
  - target host
  - CUDA qualification
  - production routing
  - counterfactual
  - mock insufficiency
authority_binding: EVIDENCE_ONLY
binding_health: HEALTHY
guidance_level: RECOMMENDED
positive_guidance_eligible: true
counterevidence_search:
  state: COMPLETE_FOR_DECLARED_SCOPE
  scope: P3 real-MACE construction, assembled P1-P7 campaign/storage integration, and P5 target-host CUDA resource qualification
  search_basis: Reviewed supporting qualification as well as failed fixtures, reopened reviews, pre-existing-baseline comparisons, unavailable toolchain evidence, and target-host failures to determine whether real-owner/real-regime testing produced misleading acceptance guidance.
  outcomes_reviewed: [SUPPORTING, NEUTRAL, CONTRADICTING, INCONCLUSIVE]
  blind_spots: Hardware regimes beyond the qualified target host and unrelated mdstats subsystems were not exhaustively searched.
  evidence:
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-target-size-v7-packages/P3_TRAIN2_EVAL2_REALIZED_MACE_ARCHITECTURE_IMPLEMENTATION_EVIDENCE.md"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
    - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md"
relations: []
applications:
  - id: A01
    episode_identity: "hjin98/mdstats@a06e67525a40c2d4e8217fe99bf4ca6821e0ce84"
    lifecycle_context: P3 realized MACE architecture qualification
    source_project: local
    surfaces:
      - pinned MACE configure_model
      - mdstats independent reconstruction
      - architecture descriptor
    provenance_cluster: p3-real-mace-census
    subject: intercept real pinned-MACE construction and compare the complete realized descriptor against independent reconstruction
    comparator: configuration-level or mocked-model parity alone
    intended_benefit: Detect construction drift at the actual dependency boundary before checkpoint admission.
    outcome: SUPPORTING
    observation: The real-owner census exposed four previously hidden differences and verified zero descriptor differences after repair.
    quantitative_effect: "Four concrete pre-repair architecture divergences were identified in the bounded census."
    uncertainty: P3 evidence did not cover every later P5 foundation/replay/CuEq regime.
    costs_tradeoffs: Requires running pinned MACE construction in a bounded integration fixture rather than relying only on lightweight stand-ins.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/mlff-target-size-v7-packages/P3_TRAIN2_EVAL2_REALIZED_MACE_ARCHITECTURE_IMPLEMENTATION_EVIDENCE.md"
  - id: A02
    episode_identity: "hjin98/mdstats@7f64ca980698575bcb3f25e3fd69684e78fedc4d"
    lifecycle_context: P5 target-host CUDA memory qualification
    source_project: local
    surfaces:
      - real N=512 TRAIN2 campaign
      - CUDA VRAM residency
      - scheduler admission
      - authenticated checkpoint persistence
    provenance_cluster: p5-rtx3090-memory-qualification
    subject: execute the exact frozen CuEq training method on the supported target GPU past the historical failure point
    comparator: resource estimates and CPU/mock scheduler tests alone
    intended_benefit: Determine whether the scientific method itself is infeasible or the implementation/resource ownership is defective.
    outcome: SUPPORTING
    observation: Target-host execution reached 10,370 updates with approximately 6.29 GiB worker residency and no OOM after the ownership/lifetime repair, supporting a D4 implementation diagnosis rather than reopening the scientific method.
    quantitative_effect: "10,370 updates; approximately 6.29 GiB per worker; approximately 11.65 GiB aggregate against a 21.6 GiB envelope; about 4.3x past the historical failure point."
    uncertainty: Hardware-specific evidence for the qualified target regime; not universal GPU sizing evidence.
    costs_tradeoffs: Requires bounded target-host qualification and cannot be replaced by CPU-only proof when CUDA realization matters.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md"
  - id: A03
    episode_identity: "hjin98/mdstats@9b406fec4ba7276d310befaa6f49ecf9ca173efc"
    lifecycle_context: assembled P1-P7 campaign/storage integration
    source_project: local
    surfaces:
      - prepare through qualification
      - process restart between stages
      - storage report/cleanup/deduplicate/archive
      - lifecycle projection
    provenance_cluster: assembled-p1-p7-integration
    subject: drive one fresh campaign through real parser/dispatch/owners with reopen/re-observe between stages and real storage operations
    comparator: isolated stage tests or uninterrupted one-process execution
    intended_benefit: Expose composition, restart, lifecycle-projection, and storage-survivability defects that component suites do not observe.
    outcome: SUPPORTING
    observation: The assembled test found a real waiting_for_reference terminal-state bug, verified downstream generation survival across storage operations, and distinguished newly introduced failures from pre-existing baseline failures.
    quantitative_effect: "85 deterministic interleaving walks were reported in the bounded integration evidence."
    uncertainty: Bounded campaign fixture; some qualification-tail behavior remained blocked by an intentionally non-convergent stand-in potential at that stage.
    costs_tradeoffs: Higher qualification cost and more exact baseline comparison than isolated unit testing.
    assessments:
      - id: AS01
        state: ADMISSIBLE
        conclusion: SUPPORTS_BOUNDED_CLAIM
        evidence:
          - "hjin98/mdstats@b65fa3b02807815d8eca758bc04fb70d514d1f45:workplans/archive/MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md"
```

## Current notices

### NT-001 — Active P5 TRAIN2/EVAL2 CuEq architecture-authentication recurrence investigation

```yaml pem-notice
id: NT-001
state: REVIEW_REQUIRED
summary: A current real P5 cross-validation run completed TRAIN2 but failed before EVAL2 because the persisted TRAIN2 CuEq architecture digest differs from independent reconstruction; historical FF-001 is materially relevant, but exact recurrence membership and repair ownership remain subject to the active diagnostic gates.
normative_status: NON_AUTHORITATIVE
owner: NONE
applicability:
  - P5 cross-validate
  - TRAIN2 completed EVAL2 authentication failed
  - CuEq architecture digest mismatch
  - active recurrence repair workplan
binding_health: HEALTHY
evidence:
  - "hjin98/mdstats@4a4ea51d45ea3082fa1ccb733192c71a10e3cac9:workplans/active/MLFF_P5_TRAIN2_EVAL2_CUEQ_ARCHITECTURE_RECURRENCE_REPAIR_WORKPLAN.md"
review_trigger:
  type: accepted_base_change
  basis: b65fa3b02807815d8eca758bc04fb70d514d1f45
```

## Coverage and maintenance note

This initial PEM intentionally records a small number of high-leverage families rather than converting every archived bugfix into a memory entry. The reviewed history shows a repeated project-local pattern: mdstats failures frequently arise at ownership, identity, persistence, resource-lifetime, and stage boundaries even when the scientific objective remains sound. The positive guidance above is bounded to the searched regimes and is evidence-backed rather than universal doctrine.

Future material work should extend this file when new evidence changes a family, when an accepted repair creates a defensible recurrence relation, or when a materially relevant historical episode falls outside this initial bounded coverage. Success patterns must retain neutral, contradicting, and inconclusive applications when such evidence appears rather than preserving only wins.
