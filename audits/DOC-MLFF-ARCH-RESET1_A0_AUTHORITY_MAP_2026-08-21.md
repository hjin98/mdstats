# DOC-MLFF-ARCH-RESET1 A0 — authority inventory and semantic-preservation map

**Status:** PASS — A0 authority map frozen; no product behavior changed  
**Workplan:** `DOC-MLFF-ARCH-RESET1`  
**Analysis base:** `main@36420c2fc67b832e8be5783716bba97932b80d4a`  
**Working branch:** `docs/mlff-architecture-reset`  
**Protocol:** software-development-protocol 5.2.0; software-design + software-documentation review  
**Date:** 2026-08-21

## 1. Purpose and classification rule

A0 freezes the semantic inventory before the architecture/specification rewrite. It does not infer intended architecture from current product code. Product behavior is conformance evidence only; the frozen design in `workplans/active/DOC-MLFF-ARCH-RESET1.md` controls the intended single-generation model.

Every normative-looking MLFF document is assigned one of four reset dispositions:

- **current-owner** — already describes a durable current contract and remains a normative owner after reconciliation;
- **merge/rewrite** — contains current requirements, but ownership/narrative is duplicated, generation-shaped, or otherwise incompatible with the frozen model;
- **historical-useful** — non-current design/evidence with durable explanatory or reproducibility value;
- **discardable** — obsolete bookkeeping/duplicate material whose unique information is already preserved by Git history, evidence, or a consolidated historical narrative.

The Aug-18 `DOC-GOV1_G0_AUTHORITY_INVENTORY_2026-08-18.md` is retained as losslessness evidence for pre-migration contracts. This reset does not restore its old source graph; it uses that inventory to ensure still-valid clauses are not accidentally deleted.

## 2. Canonical source chain

| Artifact | A0 disposition | Reset rule |
|---|---|---|
| `docs/arch_manuals/mlff_training_data/*.md` numbered chapters | **current-owner / merge-rewrite** | Editable canonical architecture sources. Rewrite here first. |
| `docs/arch_manuals/mlff_training_data_architecture.md` | derived | Rebuild only from canonical chapters; never patch independently. |
| `docs/arch_manuals/mlff_training_data_architecture.pdf` and provenance metadata | derived | Regenerate after canonical Markdown stabilizes. |
| `docs/arch_manuals/mlff_training_data_dependency_graph.json` | **merge/rewrite** | Current graph contains generation/supersession-era structure; rebuild from the frozen single-generation dependency model. |
| `docs/arch_manuals/mlff_training_data/README.md` | **merge/rewrite** | Source-chain index is stale: it still lists removed `70_status_and_gates.md` and describes the assembled output as authority rather than clearly distinguishing canonical source from derived publication artifact. |
| `docs/arch_manuals/README.md` | **merge/rewrite if affected** | Repair navigation/source-chain wording after A2/A5. |
| `docs/specs/training_data/README.md` | **merge/rewrite** | Current index mixes current, historical, and `historical/current` entries and points at obsolete release/gate authority. |
| `docs/history/mlff/README.md` | **merge/rewrite** | History index still points to superseded single-file authority wording; repair after new current source graph is frozen. |
| `workplans/active/DOC-MLFF-ARCH-RESET1.md` | temporary transition authority | Controls this redesign only; archive after A6. |
| audits / benchmarks / release evidence | evidence | Never semantic authority. |

### Source-chain defects found

1. `docs/arch_manuals/mlff_training_data/README.md` lists `70_status_and_gates.md`, but that canonical chapter no longer exists.
2. `docs/specs/training_data/README.md` advertises a training-doc verifier path that is absent from the current repository tree.
3. `docs/history/mlff/README.md` describes current authority using superseded assembled/single-file wording.
4. The current dependency graph includes a `supersedes` edge type; the reset graph must represent the present dependency model without requiring legacy-generation interpretation.

These are documentation-governance defects, not reasons to restore deleted legacy structure.

## 3. Canonical architecture chapter inventory

Current chapter blobs at A0 are frozen for rollback/reference:

| Chapter | Blob SHA | Disposition | Required reset action |
|---|---|---|---|
| `00_front_matter.md` | `147e51a1950431f62eb90890e34731c72607bdeb` | merge/rewrite | Current authority/source chain, concept-first reading map, stable glossary; remove chronology-shaped context. |
| `10_foundations.md` | `4217bd9b63c1e3ad19a6964159921a457688d528` | current-owner / rewrite | Preserve scientific/reproducibility foundations; align terminology and ownership to one generation. |
| `20_data_contracts.md` | `d34b68db3cfd14db1bf8da6ae43d17684f2592ab` | current-owner / rewrite | Preserve source/identity/labels/evidence contracts; remove obsolete generation language. |
| `30_statistical_design.md` | `6714712ede6b87b15bd0f87358c068d657e061af` | merge/rewrite | Remove DATA7/`SelectionBudgetPolicy` as an independent target-membership owner; preserve role separation, leakage, CV, weighting/exposure invariants. |
| `40_training_evaluation.md` | `772c4d351030c78fec527fbf99426b9d875050c7` | merge/rewrite | Preserve protocol/checkpoint/replay/evaluation/deployment invariants; align size-study stopping/fidelity authority. |
| `50_target_multiview.md` | `8225b1fc35dc19c5c141488826fbcd7b525ca176` | **major merge/rewrite** | Remove MVSEL1/REPAIR1/MVSTATE-REUSE1 as readable/current authorities; make MVSEL2/REPAIR2/MVSTATE2/MVQUAL sole chain; introduce fixed target-size model. |
| `60_execution_performance.md` | `628a5f4db62c734f1479da7bb860deca88156aaa` | merge/rewrite | Preserve exactness/resource/restart/persistence invariants; remove obsolete runtime-generation and qualification chronology. |
| `80_ownership_and_decisions.md` | `e515b42daa348b2f47038aee16a8e3faad8f19b2` | merge/rewrite | Freeze single-owner matrix and extension boundaries. |
| `90_references.md` | `934ceb1ad8c215984a2dc12f5f2abc3cc76002b3` | current-owner / verify | Retain references supporting surviving scientific/algorithmic claims; remove references used only for deleted chronology. |

`70_status_and_gates.md` is not present at A0 and is not restored. Status/gate chronology remains outside current architecture.

## 4. Specification-layer disposition

A0 classifies specifications by semantic family. A3 performs file-by-file consolidation/deletion only after the surviving clauses have a verified owner.

### 4.1 Cross-cutting system contract

`mlff_data_stage_plan_spec.md` -> **merge/rewrite**.

Despite its historical filename, it contains real current cross-cutting invariants identified by DOC-GOV1. Preserve only durable system-wide rules that are not better owned by a narrow specification: evidence-role separation, fit-domain isolation, protocol identity, locked-test blinding, record identity/lineage, fail-closed publication, and cross-module ownership boundaries. Delete stage/gate chronology and future implementation sequencing from the current contract.

### 4.2 Data/evidence preparation specifications

DATA2/DATA2A/DATA3/DATA4/DATA5/DATA6 and material-profile/structural-provider specifications -> **current-owner / merge-rewrite where terminology conflicts**.

Surviving responsibilities include source/label identity, eligibility/conditions, raw feature/event evidence, role feasibility/leakage/blinding, fold-local descriptor/difficulty preparation, profile-owned condition axes, and deterministic evidence lineage. None may choose final target membership.

### 4.3 DATA7 fitted preparation

`mlff_data7_fitted_metrics_selection_spec.*` -> **major merge/rewrite**.

Survive: fold/final-domain fitted transforms/metrics, E0 fits, objective/weights, difficulty evidence, condition/provenance structure, and selection-input products.

Superseded: an independent quota/FPS `TrainingSelectionPlan`, target-membership ladder, or any second selector authority. Representative/diversity/environment/event/difficulty concepts become MVSEL2 inputs, obligations, or objective terms under the single target-subset policy.

### 4.4 Multi-view selector/repair/state/qualification specifications

- MVSEL2 -> **current-owner / rewrite current-only**.
- REPAIR2 -> **current-owner / rewrite current-only**.
- MVSTATE2 -> **current-owner / rewrite current-only**.
- MVQUAL -> **current-owner / align naming and independent-verification boundary**.
- MVSEL1, REPAIR1, MVSTATE-REUSE1 -> **historical-useful**, consolidated into selector/repair design history; not current readable fallback authorities.
- MVMIGRATE1 and low-level legacy construction/readability contracts -> **historical-useful or discardable** depending unique rationale; no current migration contract survives.

### 4.5 Target-size and monitor policy specifications

Existing SIZE-HALVE2/SIZE-FIDELITY2 material -> **merge/rewrite** into one durable target-subset/target-size-study specification.

The new exact normative owner is `TargetSizeStudyPolicy`; distinct monitor families remain separately owned:

- `OnlineTargetMonitorPolicy` -> online-monitor specification;
- `ReplayMonitorPolicy` -> replay/evaluation specification;
- `SizeScreenEvaluationPolicy` -> separate only if a distinct screen-evaluation subset remains scientifically necessary.

No integer equality creates semantic equivalence between these record families.

### 4.6 Training/evaluation/deployment specifications

DATA8, campaign checkpoint/control, execution/aggregation, CLI/storage/restart, deployment artifact, adaptive stopping/ranking/evaluation/verification, binary precision, online monitor, bounded parallel evaluation/verification, progress format, and current runtime-dependency specifications -> **current-owner / merge-rewrite as needed**.

Preserve only current behavior. Remove release-number chronology, superseded generation readability, and FINAL-GPU1-as-future-authority language. Runtime locks such as a supported MACE/CuEq/Torch combination survive only if they remain an actual current product requirement when A3 is reconciled.

### 4.7 Historical and migration-era specifications currently indexed as normative

The following classes are not current semantic owners:

- `mlff_true_inference_telemetry_gate_spec.md` -> **historical-useful**;
- `mlff_mixed_stage_admission_progress_spec.md` -> **historical-useful**;
- `mlff_single_job_gpu_calibration_spec.md` -> **historical-useful**;
- `mlff_upper_tail_gpu_calibration_spec.md` -> **historical-useful**;
- `mlff_peak_trimmed_gpu_calibration_spec.md` -> **historical-useful**;
- historical portions of `mlff_85_95_gpu_calibration_spec.md` -> **merge/rewrite** only if its estimator is still current, otherwise historical-useful;
- historical portions of `mlff_work_conserving_inference_queue_spec.md` -> **merge/rewrite** only if rolling refill remains current, otherwise historical-useful;
- `mlff_adaptive_migration_spec.*` -> **historical-useful**;
- `mlff_mvstate_reuse1_selector_repair_handoff_spec.md` -> **historical-useful**;
- `FINAL_GPU1_WORKSTATION_RUNBOOK.*` -> **historical-useful/discardable as a current spec**; FINAL-GPU1 no longer controls this redesign.

A4 should consolidate these into a small number of concept-oriented historical narratives rather than preserve one historical spec per gate.

### 4.8 Generated PDFs

A Markdown/PDF pair has one semantic owner: the canonical Markdown source. PDFs are publication products. Superseded duplicate PDFs are **discardable** unless an exact historical snapshot is required to interpret durable evidence.

## 5. Single-owner semantic map

| Material contract | Current conflicting/overlapping surfaces | Post-reset normative owner |
|---|---|---|
| target membership | DATA7 quota/FPS selection + MVSEL chain | MVSEL2 policy/spec; DATA7 emits inputs only |
| target order | MVSEL1 readable path + MVSEL2 | MVSEL2 only |
| repair | REPAIR1 + REPAIR2 | REPAIR2 only |
| continuation state | MVSTATE-REUSE1 + MVSTATE2 | MVSTATE2 only |
| independent subset qualification | selector counters + MVQUAL | MVQUAL only for independent hard evidence |
| scientific target-size population | generic selection budget + SIZE-HALVE/FIDELITY + pool cardinality conventions | `TargetSizeStudyPolicy` |
| target online monitor | generic target-size/budget records + online monitor | `OnlineTargetMonitorPolicy` |
| replay monitor | generic budget records + replay/evaluation specs | `ReplayMonitorPolicy` |
| fold membership | partition/CV + target selector | DATA5 owns role/domain definition; MVSEL2 owns membership **within** each authorized training domain |
| selected size across folds/final | local selectors + size-study controls | one protocol-global `N_selected` from target-size study |
| stopping in size experiment | ordinary adaptive stopping + size-fidelity controller | target-size-study training control; ordinary success early stop disabled at 3/10/30 comparison boundaries |
| ordinary production/CV stopping | adaptive stop/checkpoint policy | current adaptive training/checkpoint specification |
| migration / obsolete generation readability | MVMIGRATE/ADAPT-MIGRATE/legacy readers | no current owner; unsupported old campaign generations |
| resource/materialization semantics | fixed ladder + MVIDX/MVSEL/repair execution specs | architecture Part VI + narrow execution specs; one master order/sparse authority, prefix metadata, bounded caches |
| campaign authority | active workplans, release gates, campaign specs | current architecture/specs only; workplans coordinate transitions and do not define product semantics |

## 6. Change-sensitive constants and exact owners

| Constant/policy | Normative owner after reset | Architectural treatment |
|---|---|---|
| nominal ladder `{128,256,512,1024,2048,4096,8192,16384}` | target-size-study spec | Architecture defines the conceptual fixed-population invariant and may show the frozen ladder while naming the spec as exact policy owner. |
| minimum qualified count `q >= 3` | target-size-study spec | Explain fail-closed requirement. |
| funnel `q -> min(q,4) -> 2 -> 1` | target-size-study spec | Explain successive-fidelity structure. |
| fidelity boundaries `3/10/30` epochs | target-size-study spec | Architecture explains exact continuation and common comparison trajectory. |
| practical-equivalence width `1 meV/Angstrom` at early screens | target-size-study spec | Architecture explains smaller-size preference but does not create a second tunable constant. |
| target monitor cardinality `256` if retained | online-monitor spec | Explicitly not target-size authority. |
| replay monitor cardinality `512` if retained | replay-monitor/evaluation spec | Explicitly not target-size authority. |
| target/replay hard admissibility thresholds | current evaluation/checkpoint specs | Constraints, not ranking bonuses unless explicitly redesigned. |
| exact coverage thresholds/radii/obligation rules | target-subset/MVQUAL specs | Architecture owns hard-view/no-regression invariants, not duplicated numeric tuning. |
| resource ceilings | resource/runtime spec | Architecture owns boundedness and semantic independence from execution tuning. |

## 7. Still-valid requirements that must survive the refactor

The following requirements are preserved from the current architecture, DOC-GOV1 inventory, and the frozen reset target:

1. **Evidence separation and leakage control.** Gradient-training domains, checkpoint monitors, held-out CV evaluation, calibration, and locked tests remain role-distinct and lineage-bound.
2. **Fold-local fitted products.** Transforms, metrics, E0 fits, difficulty evidence, and target subset membership are fitted/constructed only from evidence authorized for that fold/final training domain.
3. **Protocol identity.** CV/final comparisons bind the complete training protocol; unsupported protocol mismatch fails closed.
4. **DATA7 preparation boundary.** DATA7 may fit/prepare selection inputs but does not choose target membership.
5. **Exact multi-view geometry.** Hard scientific neighborhood/coverage semantics remain exact; execution optimization cannot silently substitute approximate neighbors or relaxed hard coverage.
6. **One nested repaired order per domain.** Candidate rungs are prefixes of one authoritative REPAIR2 order.
7. **Coverage monotonicity.** Under nested prefixes, hard coverage/obligation satisfaction cannot regress with increasing `N`; pass/fail/pass is an invariant violation.
8. **Independent qualification.** MVQUAL recomputes hard predicates independently of selector-internal counters while sharing authenticated primitive inputs where appropriate.
9. **Available/materializable/qualified/selected distinction.** Arbitrary pool cardinality never silently becomes a training size.
10. **Domain-local membership / protocol-global size.** Each required training domain has its own leakage-safe order; one selected size is frozen across required domains.
11. **Size-study evidence discipline.** Held-out CV evaluation and locked-test evidence cannot select target size; size selection uses authorized development/model-selection evidence.
12. **Fixed fidelity and paired seeds.** 3 -> 10 -> 30 is exact continuation with common frozen seeds and otherwise common training protocol.
13. **Size-study stopping boundary.** Ordinary target-success early stopping is disabled during the size comparison; hard numerical/scientific failure remains admissible rejection.
14. **Final hard admissibility.** Replay retention, target/focus metrics, energy/stress, integrity/relaxation/deployment, and other mandatory constraints remain constraints at final selection rather than score bonuses by default.
15. **Typed terminal outcomes.** Non-convergence and insufficient-candidate states are explicit; the system does not synthesize rescue sizes.
16. **No current migration requirement.** Unsupported old campaign artifacts fail clearly and require re-preparation.
17. **Bounded execution.** The eight-rung scientific ladder must not materialize eight product-scale descriptor/graph/data copies; caches are reconstructible and resource-bounded.
18. **Execution/scientific separation.** Worker count, chunking, out-of-core inversion, cache layout, scheduler concurrency, and similar optimizations cannot alter membership, ordering, coverage, ranking, evidence roles, or numerical decision authority.
19. **Current-only permanent documentation.** Architecture/specs are present-tense authorities; workplans/history/evidence cannot override them.

## 8. Superseded-document retention decisions

A4 must apply these deliberate categories rather than moving every obsolete file mechanically:

### Consolidate into history

Preserve durable rationale in a small set of narratives covering:

1. selector/repair evolution: eager inverse MVSEL1/REPAIR1/MVSTATE-REUSE1 -> forward/lazy MVSEL2/REPAIR2/MVSTATE2;
2. target-size evolution: generated/free-form/budget-derived sizes -> fixed nested target-size study and explicit non-convergence;
3. campaign compatibility evolution: migration/readability layers -> unsupported superseded generations;
4. performance/qualification lessons where failed exhaustive or memory-heavy approaches materially explain bounded current design.

### Exact snapshots only when evidence requires them

Retain a superseded exact schema/spec snapshot under history only when a durable release/audit/benchmark cannot be interpreted without it.

### Discard from current tree

Delete duplicated gate bookkeeping, obsolete future plans, duplicate generated PDFs, release-number chronology, migration prose already captured in consolidated history, and specifications whose only unique content is preserved by Git history/evidence.

## 9. A0 design-review findings

### Complexity

The defect is primarily **authority multiplicity**, not insufficient documentation. Adding another compatibility layer would increase conceptual state count and contradict the frozen single-generation target. The reset therefore reduces the number of semantic paths rather than adding adapters.

### Target-scale/resource feasibility

The fixed eight-size ladder is scientifically feasible only if represented as metadata/prefix views over one exact per-domain sparse/selection authority. Eight independent MVIDX/descriptor/dataset realizations would scale storage/RSS roughly with rung count and violate the workplan's bounded-execution requirement. The normative architecture must therefore make single-master-order/prefix materialization an invariant before code conformance is attempted.

### Statistical feasibility

The global-size/fold-local-membership design preserves held-out CV independence provided size selection never consumes held-out fold performance. The common target monitor is development/model-selection evidence and must remain role-distinct from held-out CV and locked tests. No contradiction requiring nested CV was found in the frozen design.

### Design risks carried into A1/A2

- DATA7 wording currently creates a second selection authority and must be rewritten, not caveated.
- Part V currently keeps legacy selector/repair paths as readable authorities and must be replaced wholesale with one current chain.
- Size, monitor, and generic budget terminology is currently overloaded and needs typed names.
- Dependency-graph `supersedes` semantics and migration edges must disappear from the current graph.
- Runtime/version locks must be separated from historical release facts during A3.

No A0 redesign trigger requires changing the frozen target architecture.

## 10. A0 acceptance

- **PASS — single intended owner map:** every material decision named by the workplan has one post-reset normative owner above.
- **PASS — deliberate superseded disposition:** obsolete generation/migration/gate families have retain/consolidate/discard rules.
- **PASS — semantic preservation:** still-valid scientific/statistical/execution requirements are enumerated before deletion.
- **PASS — no code promotion:** no current implementation behavior was elevated to normative architecture merely because code exists.

A1 may proceed on this frozen authority map.
