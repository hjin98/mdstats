# DOC-GOV1 G0 — MLFF documentation authority inventory

**Status:** PASS — authority inventory frozen; no normative documentation migrated in G0  
**Migration base branch:** `main`  
**Migration base commit:** `89e8bade5c697152d77942d8d649c135c5d80669`  
**Working branch:** `agent/doc-gov1-g0`  
**Date:** 2026-08-18

## 1. G0 scope and invariant

G0 classifies the active MLFF documentation authority before any semantic migration. It does not change architecture, specification, dependency-graph, builder, index, history, package, or runtime semantics.

The controlling invariant is losslessness: every current scientific, numerical, API, persistence, runtime, workflow, acceptance, and compatibility contract must retain one current normative owner after later gates.

Classification vocabulary:

```text
CURRENT_ARCHITECTURE
CURRENT_SPECIFICATION
RUNTIME_PRODUCT_GATE
DEVELOPER_WORKPLAN
HISTORY
AUDIT_EVIDENCE
BENCHMARK_EVIDENCE
GUIDE_RUNBOOK
REDUNDANT
```

A runtime/product gate remains architecture/specification when it defines current software behavior. A developer implementation gate belongs in a workplan/history/evidence. The word `gate` alone is not a classifier.

## 2. Frozen pre-migration architecture reproduction contract

The pre-migration assembled MLFF architecture is frozen at the migration-base commit above.

Builder:

- `tools/build_mlff_architecture_manual.py`
- blob SHA: `af69367c33506ee71bebba4f7ead3c056b4f81a6`

Ordered source blobs:

| Order | Source | Blob SHA |
|---:|---|---|
| 1 | `docs/arch_manuals/mlff_training_data/00_front_matter.md` | `af972b921cb0e8d9e928ca0a5d0fda69fccf5e16` |
| 2 | `docs/arch_manuals/mlff_training_data/10_foundations.md` | `90f0867a4322e82fbe04bea22e15dd5cecdd8876` |
| 3 | `docs/arch_manuals/mlff_training_data/20_data_contracts.md` | `b7c1f477d19fe639e4557e585525f6103064eb1d` |
| 4 | `docs/arch_manuals/mlff_training_data/30_statistical_design.md` | `73ba363bd383e93a43e8c673f003d01f8ae59808` |
| 5 | `docs/arch_manuals/mlff_training_data/40_training_evaluation.md` | `e85271837f6e445182bf9c32835f30705aa3e173` |
| 6 | `docs/arch_manuals/mlff_training_data/50_target_multiview.md` | `4a884144c94b58b52a2d68e650795824ea4af795` |
| 7 | `docs/arch_manuals/mlff_training_data/60_execution_performance.md` | `f2844dceca3b1ea17989f64a98719a53c9aa4198` |
| 8 | `docs/arch_manuals/mlff_training_data/70_status_and_gates.md` | `39a4d44aaa25ae7838ed40b994e60f775d6af9b5` |
| 9 | `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md` | `36676e94dcc317e34e3c6add667128e474e4ad15` |
| 10 | `docs/arch_manuals/mlff_training_data/90_references.md` | `934ceb1ad8c215984a2dc12f5f2abc3cc76002b3` |

Tracked assembled output:

- `docs/arch_manuals/mlff_training_data_architecture.md`
- blob SHA: `37b44aed940d4fc4ee9e86ca0f0587c7c5f2344f`

The builder deterministically concatenates the ten source chapters above in exactly this order with normalized chapter separation. These identities freeze the pre-migration reproduction target. Later gates must reproduce the base output before modifying builder inputs and must retain this table as the rollback/reference identity.

## 3. Section-level authority migration map

### 3.1 `docs/arch_manuals/mlff_training_data/00_front_matter.md`

| Content | Classification | Later destination |
|---|---|---|
| Purpose, immutable-record motive, canonical documentation layout, normative vocabulary | `CURRENT_ARCHITECTURE` | retain in architecture front matter |
| Reading/context indexes describing current architecture chapters | `CURRENT_ARCHITECTURE` | retain, update after Part VII removal |
| Historical release-by-release boundary paragraphs and patch chronology | `HISTORY` | `docs/history/mlff/` / release notes; current-state consequences retained in owning architecture chapters |
| Performance measurements embedded in release chronology | `BENCHMARK_EVIDENCE` | existing `benchmarks/` authority or references to it |
| `FINAL-GPU1 next` / forward-roadmap wording | `DEVELOPER_WORKPLAN` where it organizes future engineering; `RUNTIME_PRODUCT_GATE` only where software promotion currently depends on it | split by meaning in G2/G3 |

### 3.2 `10_foundations.md`

Primary classification: `CURRENT_ARCHITECTURE`.

Durable scientific motivation, ownership boundaries, invariant definitions, and current design assumptions remain architecture. Any incidental revision/status wording discovered during G2 is removed or redirected without changing the accepted structure it explains.

### 3.3 `20_data_contracts.md`

Primary classification: `CURRENT_ARCHITECTURE`.

Current source, identity, label, evidence, persistence, strain/stress, feature/event, and record-ownership contracts remain architecture. Normative detailed behavior already owned by module specifications remains specification; architecture keeps cross-cutting structure and ownership.

### 3.4 `30_statistical_design.md`

Primary classification: `CURRENT_ARCHITECTURE`.

Current leakage boundaries, partition/CV structure, selection architecture, objective/weighting separation, and statistical ownership remain architecture. Runtime acceptance gates that define current workflow semantics remain architecture/specification.

### 3.5 `40_training_evaluation.md`

Primary classification: `CURRENT_ARCHITECTURE`.

Current replay, MACE adapter, checkpoint/evaluation, protocol freeze, calibration, active-learning lineage, determinism, and deployment structure remain architecture. Version qualification evidence belongs in audit/release evidence where it is evidence rather than structure.

### 3.6 `50_target_multiview.md`

Primary classification: `CURRENT_ARCHITECTURE`.

FEAS1/MVIDX1/MVSEL1/REPAIR1/MVQUAL1 mathematical and ownership semantics, exactness rules, runtime promotion rules, and current multi-view dataflow remain architecture. Historical optimization chronology is not authority.

### 3.7 `60_execution_performance.md`

Mixed but predominantly `CURRENT_ARCHITECTURE`.

| Content | Classification | Later destination |
|---|---|---|
| Work/span model, resource scopes, scheduler ownership, exactness constraints, memory admission, NUMA extension boundary, persistence/cache semantics, current execution algorithms | `CURRENT_ARCHITECTURE` | retain |
| Runtime resource ceilings and current scheduler/promotion behavior | `RUNTIME_PRODUCT_GATE` / `CURRENT_ARCHITECTURE` | retain |
| Measured implementation comparisons and exact-digest qualification results | `BENCHMARK_EVIDENCE` / `AUDIT_EVIDENCE` | keep concise architectural consequence; detailed results in evidence |
| Tables labeled `Planned exact optimization`, rejected experiments, future execution ideas | `DEVELOPER_WORKPLAN` unless they describe an accepted extension boundary | migrate active future work to workplan; historical rejected/complete work to history/evidence |
| Release/version chronology | `HISTORY` | history/release notes |

### 3.8 `70_status_and_gates.md`

This file is the largest mixed authority surface and must **not** be moved wholesale.

| Content | Classification | Later destination |
|---|---|---|
| Current exact execution architecture stated inside gate implementations (scheduler resource ownership, cache identity, sparse-state reuse boundary, exact reduction ordering, direct-API compatibility, fallback behavior) | `CURRENT_ARCHITECTURE` | redistribute to Parts V/VI/ownership chapter as appropriate |
| Runtime/product gates that currently control campaign promotion or release behavior | `RUNTIME_PRODUCT_GATE` | architecture/specification owning that runtime behavior |
| `PERFBASE1` and measured timing/RSS/digest reports | `BENCHMARK_EVIDENCE` / `AUDIT_EVIDENCE` | benchmarks/audits; architecture may summarize consequences |
| `COMPLETE`, `Succeeded by`, `Next gate`, release-number sequence, implementation narratives | `HISTORY` | `docs/history/mlff/` / release notes |
| Still-valid future developer sequence such as workstation qualification planning | `DEVELOPER_WORKPLAN` | active workplan created after G1 infrastructure exists |
| Explicit non-goals that are durable design prohibitions | `CURRENT_ARCHITECTURE` or `CURRENT_SPECIFICATION` depending specificity | retain under owning current contract |
| Documentation/lineage policy paragraph | governance; currently redundant/mixed | superseded by G1 repository governance and concise architecture pointer |

### 3.9 `80_ownership_and_decisions.md`

Primary classification: `CURRENT_ARCHITECTURE`.

Current ownership boundaries and accepted design decisions remain architecture. Revision-specific decision chronology, if present, belongs in history while the accepted decision remains current architecture.

### 3.10 `90_references.md`

Primary classification: `CURRENT_ARCHITECTURE` support/reference material. Retain references needed to substantiate current scientific/algorithmic architecture.

### 3.11 `docs/specs/training_data/README.md`

| Content | Classification | Later destination |
|---|---|---|
| Directory ownership statement and current specification catalog | `CURRENT_SPECIFICATION` index | retain and normalize in G3 |
| `Canonical plan and current status` framing | mixed/obsolete authority wording | replace with current-authority framing in G3 |
| Runtime progress/version chronology (`0.20.29a0` onward) | `HISTORY` | history/release notes |
| Per-spec descriptions of current contracts | `CURRENT_SPECIFICATION` index | retain, verify currentness |
| Historical/current labels embedded in spec list | mixed `HISTORY` + `CURRENT_SPECIFICATION` | split; index should describe current owner only |

### 3.12 `docs/specs/training_data/mlff_data_stage_plan_spec.md`

This document contains real current normative contracts and therefore must not be retired by title alone.

Classification by major section:

| Section | Classification | Surviving normative owner after migration |
|---|---|---|
| Scope — current package dependency boundary and fail-closed publication rule | `CURRENT_SPECIFICATION` | current cross-cutting MLFF system-contract spec or narrower owning specs |
| Normative principles | `CURRENT_SPECIFICATION` | cross-cutting current system-contract spec unless already uniquely owned by narrower specs |
| Record-family contract | `CURRENT_SPECIFICATION` | current system-contract spec / record-owner specs |
| Identity contract | `CURRENT_SPECIFICATION` | DATA2/DATA3 identity specs where complete; cross-cutting remainder stays in system-contract spec |
| Label-domain and energy contract | `CURRENT_SPECIFICATION` | DATA2 source/label specification |
| Atomic-reference contract | `CURRENT_SPECIFICATION` | DATA2/DATA7/DATA8 as applicable; cross-fold leakage rule must have one owner |
| Cell, strain, stress, virial contract | `CURRENT_SPECIFICATION` | DATA2A/DATA3/DATA8 owning specs |
| Event, feature, blinding contract | `CURRENT_SPECIFICATION` | DATA4/DATA5/DATA6/DATA7 owning specs |
| Partition feasibility and outer-role contract | `CURRENT_SPECIFICATION` | DATA5 specification |
| Cross-validation and training-protocol contract | `CURRENT_SPECIFICATION` | DATA5/DATA7/DATA8/campaign specifications, with one cross-cutting owner for protocol identity |
| Selection-budget contract | `CURRENT_SPECIFICATION` | DATA7 / current target-selection specs |
| Training objective, weights, checkpoint metrics | `CURRENT_SPECIFICATION` | DATA7 + checkpoint-control specs |
| Exposure and MACE realization contract | `CURRENT_SPECIFICATION` | DATA8 / execution specs |
| MACE checkpoint-control and replay contract | `CURRENT_SPECIFICATION` | DATA8 + campaign checkpoint specs |
| MACE artifact contract | `CURRENT_SPECIFICATION` | DATA8 / sealed-evaluation specs |
| Calibration and active-learning contract | `CURRENT_SPECIFICATION` | current calibration/acquisition owner; retain cross-cutting rule until a narrower current spec fully owns it |
| `# Stage gates` completed DATA1–DATA9B* implementation chronology | `HISTORY` plus embedded `CURRENT_SPECIFICATION` clauses | chronology to history; normative current clauses to owning current specs before deletion |
| DATA10 and DATA11 future implementation sequence | `DEVELOPER_WORKPLAN` except any already-current runtime contract | active workplan after G1; no future target behavior in current spec |
| Testing requirements | mixed: current conformance obligations are `CURRENT_SPECIFICATION`; implementation sequencing is `DEVELOPER_WORKPLAN` | retain as current conformance requirements where still applicable, otherwise workplan |
| Documentation requirements | governance + history | G1 repository governance; remove stage-planning role |
| MLFF-PERF*/ADAPT* release chronology appended after stage gates | `HISTORY` with embedded current runtime clauses | chronology to history; live runtime behavior remains in dedicated current specs |

## 4. Normative-clause ownership map for the stage-plan specification

The following map is lossless by **normative topic**. Every `MUST`, `MUST NOT`, `SHALL`, `SHALL NOT`, and current `MAY` in `mlff_data_stage_plan_spec.md` must be accounted for under one of these rows during G3. A row cannot be removed until its destination document is verified to contain the complete live contract.

| Normative topic | Current semantic owner to verify/use in G3 | G3 action |
|---|---|---|
| Separation of source facts, eligibility, partition, selection, weighting, exposure, acquisition | cross-cutting system contract + DATA2–DATA8 specs | retain one cross-cutting owner; remove duplicates only after parity review |
| Gradient-used frames are not independent validation evidence | DATA5 partition/leakage spec | verify exact rule, then point system contract to DATA5 |
| Fresh model per held-out CV fold; held-out fold cannot control stopping/checkpointing | DATA5 + campaign execution specs | verify exact fold semantics |
| Disjoint checkpoint-monitor domain | DATA5 | verify |
| Complete `TrainingProtocolIdentity` equality between CV/final and protocol distinctions | DATA7/DATA8/campaign specs | keep one cross-cutting owner if narrower specs split the invariant |
| Fit/selection/E0/difficulty training-domain isolation | DATA5–DATA7 | verify all fitted-object classes |
| Locked-test blinding and post-freeze activation | DATA5/DATA8/DATA9B2 | verify no policy/selection/calibration/acquisition leakage |
| Partition-critical profile features before partition lock | DATA4/DATA5 | verify ordering |
| MACE adapter target-label-domain/head/fixed-file constraints | DATA8 / backend specs | verify against current supported backend behavior |
| Native head ordering/checkpoint control/exposure realization verification | DATA8 + checkpoint-control specs | verify |
| Replay retention constraints and disjoint replay monitor | DATA8 + campaign checkpoint specs | verify |
| Dynamic resampling cannot be claimed by static files | DATA8 | verify |
| Final-committee-bound active-learning calibration/applicability | calibration/acquisition owner | preserve until narrower owner is confirmed |
| Child-dataset role inheritance/new evaluation lineage | calibration/acquisition owner | preserve until narrower owner is confirmed |
| Record-family ownership and forbidden ownership | DATA2–DATA9 record specs | verify each record family; keep cross-cutting table if it remains clearest single owner |
| Versioned schema, deterministic digest, policy identity/failure reasons, parent/provider lineage | record serialization/system contract | verify all current record families or keep cross-cutting owner |
| `frame_uid`, geometry, label payload, labeled-configuration identities | DATA2/DATA3 | verify |
| Leakage audit identity dimensions and temporal proximity | DATA5 | verify |
| Label-domain decomposition and compatibility | DATA2 | verify |
| One compatible target label domain per MACE bundle | DATA8 | verify current behavior |
| Named/consistent energy channel provenance | DATA2/DATA8 | verify |
| Atomic-reference identifiability structure | DATA2 | verify |
| Fold/final E0 fits exclude non-training evidence; missing support fail/explicit policy | DATA7 | verify |
| Explicit MACE E0 mapping, not conceptual record names | DATA8 | verify |
| ASE-row cell convention and deformation gradient | DATA3 | verify |
| Stress units/sign/Voigt/shear and distinct virial keys | DATA3/DATA8 | verify |
| Full-resolution event detection before thinning; protected event families | DATA4 | verify |
| Raw feature providers partition-independent; fitted transforms separated | DATA4/DATA6/DATA7 | verify |
| Foundation descriptor/residual blinding | DATA6 | verify |
| Role feasibility before assignment and no fabricated cohorts | DATA5 | verify |
| Outer roles, deferred calibration, sealed locked tests | DATA5 | verify |
| LTA hierarchical applicable schemas | profile/partition specs | verify current profile owner |
| Machine-readable independence grades | DATA5 | verify |
| Full `TrainingProtocolIdentity` fields | DATA7/DATA8 | verify current schema |
| CV execution ordering and fold-local fitting | DATA5–DATA8 / campaign | verify |
| Rotating inner-validation prohibition; protocol-matched CV | DATA5/campaign | verify |
| Deterministic master order, quota classes, deficit redistribution, exact prefixes | DATA7 / target-selection specs | verify current selector architecture supersession where applicable |
| LTA species-environment coverage requirement | profile/selection current owner | verify whether superseded/generalized; preserve accepted semantics without reviving obsolete schema |
| Objective/config/property weights and species-aware-loss boundary | DATA7/DATA8 | verify current backend semantics |
| Checkpoint metric constraints | checkpoint-control specs | verify |
| Exposure backend meanings and fixed-file limitation | DATA8 | verify |
| `MaceExposureRealizationRecord` fields and duplication fail-closed behavior | DATA8 | verify |
| MACE version lock/current compatibility behavior | dedicated backend specs + DATA8 | migrate away from obsolete hard-coded first-adapter history while retaining current version-lock requirement |
| Target-last/native checkpoint-control behavior where still current | backend/checkpoint specs | verify current supported MACE version behavior before retaining |
| Development/sealed/calibration bundle separation and activation prerequisites | DATA8/DATA9B2 | verify |
| Final-committee calibration and applicability-domain classification | calibration/acquisition owner | preserve |
| Candidate admissibility, acquisition lineage, immutable child generations | acquisition owner | preserve |
| Stage-specific current runtime `SHALL` clauses embedded in DATA2A/DATA9A*/PERF* history | corresponding dedicated current specs | extract/verify before deleting chronology |
| Test obligations protecting all contracts above | owning specs + repository test policy | preserve current conformance obligations; do not treat completed historical test execution as a current spec |

### Clause-map fail-closed rule

If G3 cannot identify a narrower specification that fully owns a normative topic above, that topic remains in a reframed current cross-cutting MLFF system-contract specification. No normative topic may be deleted merely because it appears duplicated or historical.

## 5. Dependency graph classification

`docs/arch_manuals/mlff_training_data_dependency_graph.json` is mixed.

Retain as `CURRENT_ARCHITECTURE` when an edge expresses actual product/data/runtime structure, including current forms of:

```text
execution_requires
fit_domain_requires
optional_enrichment
promotion_requires
release_qualification_requires
replay_triggers
source_identity_requires
supersedes
```

`implementation_requires` must be reviewed edge-by-edge: if it means a real current product dependency, rename/reframe architecturally; if it means development sequencing, it belongs in a workplan.

Project-state fields are not architectural authority and are G4 migration candidates:

- `architecture_revision` when used as chronology rather than schema identity;
- `branch` when it names a development branch rather than a runtime identity;
- description text announcing completed optimization programs or the `next` gate;
- `documentation_gate`;
- any node/edge metadata whose only meaning is developer implementation status.

Runtime `promotion_requires` and `release_qualification_requires` edges remain architectural when software behavior genuinely consumes those predicates.

## 6. Index/navigation classification

### `docs/README.md`

Current artifact-family navigation is useful, but wording that `arch_manuals/` contains `staged architecture`, the MLFF `performance roadmap`, a dependency/**status** graph, `module/gate contracts`, or stale roadmap/version notes is mixed governance/history. G5 will normalize it after authority migration.

### `docs/INDEX.md`

The current index correctly prioritizes current authority over history, but `dependency/status graph` and `module/gate contracts` terminology reflects the mixed model. G5 will update those labels after G2–G4.

### `docs/arch_manuals/README.md`

The opening definition explicitly assigns `staged implementation plans` to architecture manuals; that conflicts with DOC-GOV1. Its MLFF entry also says the manual includes `current status, and forward gates`, and the graph is called a `dependency and gate graph`. These are G5 governance/navigation corrections, not G0 edits.

### `docs/history/mlff/README.md`

This is already close to the intended model: history is non-normative and current contracts live in architecture/specifications. G5 should extend it to name workplans as the active engineering execution class after G1 establishes that tree.

## 7. G0 acceptance evaluation

| Acceptance condition | Result | Evidence |
|---|---|---|
| Migration base explicit | PASS | `main` / `89e8bade5c697152d77942d8d649c135c5d80669` frozen above |
| Pre-migration architecture reproducible | PASS | deterministic builder, ordered source blob identities, and tracked assembled-output blob identity frozen above |
| Every material mixed section has a destination | PASS | section-level maps in §§3, 5, and 6 |
| Every normative clause has a surviving owner | PASS, fail-closed | topic-complete ownership map in §4; unresolved narrower ownership defaults to retained cross-cutting current specification |
| No semantic documentation rewrite occurred in G0 | PASS | only this audit/inventory artifact is added on the G0 branch |

## 8. G1 handoff

G1 may now establish repository-level workplan/governance infrastructure. It must not use this audit as a competing current normative source. This file is migration evidence: it records where authority was found and constrains later lossless moves.

Before G2/G3 deletes or renames any mixed authority, the corresponding row in this inventory must be checked against the destination content. Any ambiguity resolves in favor of retaining the current contract until ownership is proven.
