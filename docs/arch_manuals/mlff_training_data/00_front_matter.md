---
geometry: "margin=0.75in"
architecture_revision: 109
status: "current normative architecture"
last_updated: "2026-09-13"
---

# MLFF Training-Data and Fine-Tuning Architecture

## Purpose and authority

This manual remains the accepted current normative MLFF architecture while the D1/D2 reconstruction on this branch is under human review. It defines the accepted current scientific, statistical, execution, and evidence architecture for source-certified atomistic data preparation, leakage-safe evidence roles, neutral statistical preparation, one optional automatic target-size diagnostic feeding an operator-owned target-size decision, MACE fine-tuning, selected-only method validation, fresh final production, and bounded campaign execution. Downstream deployment, physical, calibration, and locked-test capabilities remain separately owned product obligations.

This reconstruction branch proposes a clearer future authority split:

- `docs/methods/mlff_scientific_method.md` is the candidate D1 scientific formulation: scientific questions, observables, assumptions, evidence semantics, validity, uncertainty, and permitted claims.
- `docs/methods/mlff_numerical_algorithmic_method.md` is the candidate D2 numerical method: deterministic constructions, fitting and reduction algorithms, optimizer-progress normalization, conditioning/error/failure semantics, and numerical-equivalence requirements.
- after human acceptance and lossless architecture reconciliation, this manual should be narrowed to D3 structure: dependency direction, responsibility boundaries, integration, data/control flow, persistence consequences, and execution architecture.

Until that acceptance, the current architecture and specifications remain controlling. The candidate papers are reconstruction artifacts and cannot override a conflicting current normative contract merely by being present on this branch.

The D1/D2 documents were reconstructed from current and accepted historical evidence because the pre-SSDP architecture accumulated scientific and numerical material before these layers were formally separated. Reconstruction provenance and the independent review/preservation map are recorded under `docs/history/mlff/`.

This manual is intentionally present-tense and single-generation. A reader does not need release chronology, migration history, or obsolete stage semantics to determine current behavior.

The canonical editable architecture sources are the numbered chapters under `docs/arch_manuals/mlff_training_data/`. The assembled Markdown and PDF are generated publication products of those sources and must not be edited as independent authorities.

Detailed exact behavior is owned by current specifications under `docs/specs/training_data/`. Proposed transitions live in `workplans/`; completed chronology lives under `docs/history/mlff/`; correctness/performance evidence lives in audits, release evidence, and benchmarks.

## Architectural motive

MLFF campaigns combine state with fundamentally different epistemic roles: physical source facts, eligibility decisions, evidence partitions, fitted transforms, subset-membership decisions, target-size decisions, optimization/checkpoint state, protocol-validation evidence, calibration evidence, locked tests, and deployment decisions. Conflating those roles creates leakage and ambiguous authority even when the numerical code is correct.

The architecture therefore uses immutable/content-addressed evidence, explicit statistical roles, one normative owner per scientific decision, and authenticated dependency direction. Execution realization is kept separate: cache layout, worker count, queue order, out-of-core storage, and scheduler policy may change without changing scientific membership, ordering, coverage, ranking, or evidence roles.

Expensive exact numerical work is computed once per semantic identity and reused wherever its inputs are unchanged. Exactness, deterministic authoritative decisions, bounded materialization, explicit resource ownership, and restartable authenticated state take precedence over nominal utilization.

## Current workflow at a glance

```text
source evidence and compatible label authority
  -> eligibility / physical conditions / reference-cell and strain-stress context
  -> raw feature and full-resolution event evidence
  -> neutral statistical substrate, outer evidence roles, and protected relations
  -> authorized pre-order fitted selection evidence
  -> one P_train / M3 target-size development split
  -> one canonical training order pi_train and evaluation ladder M1 subset M2 subset M3
  -> one common deterministic target-size training preparation over exact P_train
     (common E0, objective/weights/masks, foundation/head and common model normalization)
  -> optional paired optimizer-seed automatic diagnostic over candidate sizes
     (one target-size reducer -> a *recommended* size or typed no-recommendation)
  -> operator-owned provisional design (ordered collection of (N, CV horizon, production horizon))
  -> cross-validate admission
  -> frozen design: every selected size N_selected, its exact T_selected = pi_train[:N_selected], and role horizons
  -> post-selection cross-validation on the frozen collection
  -> fresh final production on the selected dataset(s)
  -> currentness-fenced final-production publication
  -> separately owned downstream qualification/locked release where supported
```

The distinction between **pre-order fitted selection evidence** and the later
`TargetSizeCommonPreparation` is normative for the current architecture. The
former may help determine the one `pi_train`; the latter is a P3 consumer of
already accepted `P_train/pi_train` authority and cannot feed backward into the
order it follows.

The current graph has exactly one target-size architecture. The retired per-domain multi-view selection generation is not an alternate current path: it is neither migrated nor semantically read forward, and a workspace still holding its derived state is rejected with an actionable destructive reset/reprepare requirement before any candidate, checkpoint, or descendant is reused. Raw scientific inputs and independently valid low-level content caches remain reusable when their recipes do not depend on retired target-size semantics.

## Reading index

| Need | Primary source |
|---|---|
| Candidate reconstructed scientific problem, observables, evidence semantics, validity, uncertainty | `docs/methods/mlff_scientific_method.md` (D1 candidate; pending review) |
| Candidate reconstructed numerical construction, fitting, normalization, reducer, failure/conditioning semantics | `docs/methods/mlff_numerical_algorithmic_method.md` (D2 candidate; pending review) |
| Current normative scientific motivation, record/evidence model, and scope | Part I - Foundations |
| Source identity, labels, strain/stress, eligibility, raw features/events | Part II - Data and evidence contracts |
| Evidence roles, leakage, CV, fitted preparation, objective/weighting/exposure boundaries | Part III - Statistical design and fitted preparation |
| Replay, MACE protocol, checkpointing, validation, deployment, calibration, active learning | Part IV - Training, evaluation, and deployment |
| Target-size split/orders, the optional paired-seed diagnostic and its reducer, the provisional design and its freeze, post-selection CV, fresh final production | Part V - Target-size selection and post-selection validation |
| Exact execution, bounded resource/materialization, cache/restart/storage/progress | Part VI - Performance and execution architecture |
| Sole-owner matrix and accepted extension boundaries | Part VII - Ownership and extension boundaries |
| External scientific/algorithmic sources | References |

## Context retrieval index

For targeted human or AI loading, use the smallest current source containing the needed concept. The candidate D1/D2 papers are additionally useful reconstruction views while pending review:

| Query terms | Load first |
|---|---|
| reconstructed scientific aim, estimand, label/strain/stress meaning, validity, uncertainty, correlated evidence | `docs/methods/mlff_scientific_method.md` plus the current architecture/specification that owns the corresponding behavior |
| reconstructed numerical sampling, target-size algorithm, E0 fitting, optimizer normalization, reducer, numerical failure | `docs/methods/mlff_numerical_algorithmic_method.md` plus the current owning specification/architecture chapter |
| source/label identity, eligibility, strain/stress, raw features/events | `20_data_contracts.md` |
| evidence roles, leakage, pre-order fitted selection evidence, common training preparation, objective, weighting, exposure | `30_statistical_design.md` |
| replay, MACE, checkpoint, evaluation, deployment, calibration, active learning | `40_training_evaluation.md` |
| target size, `pi_train`, `T_selected`, `M1/M2/M3`, `n1/n2/n3`, post-selection CV, final production | `50_target_size_selection.md` |
| scheduler, sparse execution, out-of-core, memory, persistence, progress | `60_execution_performance.md` |
| owner, dependency direction, unsupported generation, extension boundary | `80_ownership_and_decisions.md` |
| reconstruction provenance / preservation review / superseded design rationale | `docs/history/mlff/MLFF_D1_D2_RECONSTRUCTION_EVIDENCE.md`, `docs/history/mlff/MLFF_D1_D2_RECONSTRUCTION_REVIEW_2026-09-13.md`, and `docs/history/mlff/` |
| proposed transition | `workplans/active/` |

## Stable terminology

- **training domain** — an authorized gradient-training evidence partition. The target-size design is an ordered frozen collection; for each frozen size, post-selection CV may derive fold-local partitions only inside its exact membership `T_N = pi_train[:N]`.
- **target membership** — frame membership in a target-training subset; an exact prefix of the one canonical training order `pi_train`.
- **target size** — the protocol-level scientific target-training cardinality the operator chooses, restricted to the configured qualified candidate set.
- **recommended size** — the size the optional automatic diagnostic's reducer ranks best under its short-horizon protocol. It is evidence, never authority.
- **monitor size** — the cardinality of a monitoring/evaluation evidence set; never target-size authority.
- **training order** — the one canonical deterministic ordering `pi_train` of the target-training pool whose prefixes define candidate target subsets.
- **qualified size** — a candidate size admitted by the configured target-size policy for the current experiment definition.
- **pre-order selection evidence** — authorized candidate-independent raw/fitted evidence consumed to construct the one canonical target-training order; it is not target membership authority itself.
- **common target-size training preparation** — the P3 candidate-independent fitted training state over exact `P_train`, constructed after the P2 split/orders and projected without refitting onto each `T_N`.
- **provisional design** — the ordered, unique-by-`N` collection of per-size entries `(N_provisional, its exact membership, selection source, CV horizon, production horizon)` the operator owns until admission. Empty is its canonical unselected state.
- **selected size** — a target size `N_selected` in the ordered frozen design admitted at `cross-validate`, bound to its exact membership `T_selected = pi_train[:N_selected]` and its effective role horizons.
- **authoritative evidence** — persisted information that defines or independently proves a scientific decision.
- **reconstructible execution cache** — discardable state derivable exactly from authoritative inputs.
- **unsupported generation** — an old campaign/artifact generation that current architecture does not interpret or migrate; it requires re-preparation.

## Normative vocabulary

- **SHALL / MUST** — required for scientific, statistical, or execution correctness.
- **SHOULD** — the default design unless measured evidence justifies another exact-equivalent realization.
- **MAY** — optional realization that cannot weaken the scientific contract.

When architecture explains a change-sensitive constant whose exact value is specification-owned, the owning specification remains the sole normative location for changing that value.

## Retrieval and local-context rule

Each major chapter states what its concepts own, consume, emit, and explicitly do not own. Equations and symbols are defined near first use. A chapter may repeat a dependency boundary for local comprehension, but repeated prose must not create a second independently tunable contract. If the proposed D1/D2 split is accepted, duplicate scientific/numerical prose should be reduced only after a lossless comparison proves the upstream papers preserve every accepted claim.
