---
geometry: "margin=0.75in"
architecture_revision: 105
status: "current normative architecture"
last_updated: "2026-08-22"
---

# MLFF Training-Data and Fine-Tuning Architecture

## Purpose and authority

This manual defines the accepted current scientific, statistical, execution, and evidence architecture for the mdstats MLFF workflow: source-certified atomistic data preparation, leakage-safe evidence roles, fitted preparation, multi-view target-subset construction, target-size selection, MACE fine-tuning, protocol validation, deployment, calibration, and bounded campaign execution.

It is intentionally present-tense and single-generation. A reader does not need release chronology, migration history, or obsolete stage semantics to determine current behavior.

The canonical editable architecture sources are the numbered chapters under `docs/arch_manuals/mlff_training_data/`. The assembled Markdown and PDF are generated publication products of those sources and must not be edited as independent authorities.

Detailed exact behavior is owned by current specifications under `docs/specs/training_data/`. Methods/theory material may explain rationale but does not override architecture or specifications. Proposed transitions live in `workplans/`; completed chronology lives under `docs/history/mlff/`; correctness/performance evidence lives in audits, release evidence, and benchmarks.

## Architectural motive

MLFF campaigns combine state with fundamentally different epistemic roles: physical source facts, eligibility decisions, evidence partitions, fitted transforms, subset-membership decisions, target-size decisions, optimization/checkpoint state, protocol-validation evidence, calibration evidence, locked tests, and deployment decisions. Conflating those roles creates leakage and ambiguous authority even when the numerical code is correct.

The architecture therefore uses immutable/content-addressed evidence, explicit statistical roles, one normative owner per scientific decision, and authenticated dependency direction. Execution realization is kept separate: cache layout, worker count, queue order, out-of-core storage, and scheduler policy may change without changing scientific membership, ordering, coverage, ranking, or evidence roles.

Expensive exact numerical work is computed once per semantic identity and reused wherever its inputs are unchanged. Exactness, deterministic authoritative decisions, bounded materialization, explicit resource ownership, and restartable authenticated state take precedence over nominal utilization.

## Current workflow at a glance

```text
source evidence and labels
  -> eligibility / physical conditions
  -> raw feature and event evidence
  -> evidence-role partitioning
  -> fold/final training domains
  -> fitted descriptors, metrics, E0/objective/weight inputs
  -> multi-view feasibility and exact sparse neighborhood authority
  -> MVSEL2 target order
  -> REPAIR2 repaired master order + MVSTATE2 continuation state
  -> independent MVQUAL prefix qualification
  -> fixed target-size study
  -> one protocol-global selected target size
  -> domain-local target prefixes
  -> training / checkpoint selection
  -> held-out protocol validation
  -> final committee / deployment
  -> calibration and activated locked-test / observable validation
```

The current graph has no alternate MVSEL1/REPAIR1 path and no migration path for superseded campaign generations.

## Reading index

| Need | Primary chapter |
|---|---|
| Scientific motivation, record/evidence model, and scope | Part I - Foundations |
| Source identity, labels, strain/stress, eligibility, raw features/events | Part II - Data and evidence contracts |
| Evidence roles, leakage-safe CV, fitted preparation, objective/weighting/exposure boundaries | Part III - Statistical design and fitted preparation |
| Replay, MACE protocol, checkpointing, validation, deployment, calibration, active learning | Part IV - Training, evaluation, and deployment |
| FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL and target-size study | Part V - Multi-view target subset and size architecture |
| Exact execution, bounded resource/materialization, cache/restart/storage/progress | Part VI - Performance and execution architecture |
| Sole-owner matrix and accepted extension boundaries | Part VII - Ownership and extension boundaries |
| External scientific/algorithmic sources | References |

## Context retrieval index

For targeted human or AI loading, use the smallest current source containing the needed concept:

| Query terms | Load first |
|---|---|
| source/label identity, eligibility, strain/stress, raw features/events | `20_data_contracts.md` |
| evidence roles, leakage, CV, fitted metrics, E0, objective, weighting, exposure | `30_statistical_design.md` |
| replay, MACE, checkpoint, evaluation, deployment, calibration, active learning | `40_training_evaluation.md` |
| FEAS1, MVIDX1, MVSEL2, REPAIR2, MVSTATE2, MVQUAL, target size, 3/10/30 | `50_target_multiview.md` |
| scheduler, sparse execution, out-of-core, memory, persistence, progress | `60_execution_performance.md` |
| owner, dependency direction, unsupported generation, extension boundary | `80_ownership_and_decisions.md` |
| scientific/algorithmic provenance | `90_references.md` |
| superseded design rationale or release chronology | `docs/history/mlff/` |
| proposed transition | `workplans/active/` |

## Stable terminology

- **training domain** — the DATA5-authorized fold/final gradient-training evidence available to fitted preparation and subset construction.
- **target membership** — frame membership in a target-training subset; owned by MVSEL2/REPAIR2 within a training domain.
- **target size** — the protocol-level scientific target-training cardinality chosen by `TargetSizeStudyPolicy`.
- **monitor size** — the cardinality of a monitoring/evaluation evidence set; never target-size authority.
- **master order** — the one repaired REPAIR2 ordering per training domain whose prefixes define candidate target subsets.
- **qualified size** — a materializable nominal size whose prefix passes independent MVQUAL hard requirements in every required training domain.
- **selected size** — the one protocol-global target size selected from the qualified population.
- **authoritative evidence** — persisted information that defines or independently proves a scientific decision.
- **reconstructible execution cache** — discardable state derivable exactly from authoritative inputs.
- **unsupported generation** — an old campaign/artifact generation that current architecture does not interpret or migrate; it requires re-preparation.

## Normative vocabulary

- **SHALL / MUST** — required for scientific, statistical, or execution correctness.
- **SHOULD** — the default design unless measured evidence justifies another exact-equivalent realization.
- **MAY** — optional realization that cannot weaken the scientific contract.

When architecture explains a change-sensitive constant whose exact value is specification-owned, the owning specification remains the sole normative location for changing that value.

## Retrieval and local-context rule

Each major chapter states what its concepts own, consume, emit, and explicitly do not own. Equations and symbols are defined near first use. A chapter may repeat a dependency boundary for local comprehension, but repeated prose must not create a second independently tunable contract.
