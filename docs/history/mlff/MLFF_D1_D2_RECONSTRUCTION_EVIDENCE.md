# MLFF D1/D2 reconstruction evidence

**Status:** non-normative reconstruction provenance  
**Reconstructed current head:** `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`  
**Date:** 2026-09-13

This note records how the missing MLFF D1 scientific-method and D2 numerical-algorithm documents were reconstructed. It is historical/provenance evidence, not a third method authority.

## Reconstruction rule

The reconstruction followed current authority first, using historical material only to explain or recover semantics that remain present in the current product. A historical algorithm was not promoted merely because it once appeared in the architecture manual or an accepted workplan.

Evidence was classified as:

1. **current product authority/evidence** — current architecture, specifications, current-generation code owners, tests, and accepted current protocol identities;
2. **accepted transition evidence** — archived workplans and commits that explain why a current invariant exists or how an implementation defect was repaired without changing the frozen method; and
3. **retired design history** — useful chronology that is explicitly excluded from the reconstructed current method.

## Principal current sources

### Architecture

- `docs/arch_manuals/mlff_training_data/00_front_matter.md`
- `10_foundations.md`
- `20_data_contracts.md`
- `30_statistical_design.md`
- `40_training_evaluation.md`
- `50_target_size_selection.md`
- `80_ownership_and_decisions.md`
- `90_references.md`

These chapters predate the present D1/D2/D3 authority split and therefore contain mixed scientific, numerical, and architectural material. The new method papers factor the first two categories into explicit D1/D2 ownership while the architecture remains responsible for integration and dependency structure.

### Current specifications

Important current contracts include the training-data cross-cutting system contract, partition/evidence-role specifications, MACE-artifact/protocol specifications, post-selection/qualification specifications, and documentation-governance material under `docs/specs/training_data/` and `docs/specs/documentation/`.

### Current executable owners used as conformance evidence

- `mdstats/training_data/target_size_experiment.py`
  - current compatibility-neutral target-size population;
  - protected-relation split construction;
  - exact `P_train/M3` allocation;
  - one deterministic `pi_train` and `pi_eval`;
  - exact-prefix membership and hard-support qualification;
  - pure target-size reducer and deterministic history replay.
- `mdstats/training_data/target_size_execution/common.py`
  - one seed-neutral, `N`-neutral common fitted preparation;
  - common atomic-reference fitting and exact candidate projection;
  - target-only EVAL2 metric policy.
- `mdstats/training_data/target_size_execution/schedule.py` and sibling execution owners
  - continuous fidelity trajectories and exact boundary execution.
- `mdstats/training_data/reference_fit.py`
  - from-scratch and foundation-residual atomic-reference fitting;
  - rank/singular-value/null-space diagnostics.
- `mdstats/training_data/objectives.py`
  - global energy/force/stress objective coefficients;
  - per-configuration weights;
  - local property availability masks as distinct semantic layers.
- `mdstats/training_data/mace_compatibility.py`
  - pinned MACE execution identity;
  - source qualification of dependency behavior;
  - resolved loss/optimizer/exposure and target-batch semantics.
- current post-selection execution/protocol owners
  - fresh fold lineages, checkpoint-monitor separation, held-out evaluation, and fresh final production.

## Accepted transition evidence retained

The following historical transitions materially explain current D1/D2 semantics and were used as evidence without being treated as current product authority:

- V7 target-size reset/simplification workplans and commits, especially the transition to one compatibility-neutral target-size population, one training order, one nested evaluation ladder, and no pre-target-size CV authority;
- P2 target-size statistical-authority implementation and its split-exclusion/hard-support correction;
- P3 paired-screen implementation establishing exact continuous `(N, seed)` trajectories and pure reducer ownership;
- target-size optimizer-normalization/practical-ceiling workplans establishing
  `U_ref=ceil(N_ref/B)`, `U_N=ceil(N/B)`, `s_N=U_ref/U_N`, `LR_N=LR_ref*s_N`, and `beta_N=beta_ref**s_N`;
- MACE execution-semantics alignment, which repaired dependency realization while explicitly preserving the frozen scientific method;
- provisional/multi-size target-selection work establishing that the automatic screen recommends while the operator owns the provisional design; and
- post-selection currentness/authorization work preserving selected-only CV and fresh final production.

Representative commits include `832a4e1`, `ea94347`, `bad25874`, `bd1b3ae`, `63aab70`, `d9f7282`, `1bd10f1`, `e5c55b5`, `9af7d70`, `fa05c800`, `f92e6a1`, `f4a0e77`, and later integration repairs that preserved those invariants.

## Explicitly excluded retired designs

The following historical material was reviewed for provenance but is **not** part of the reconstructed current method:

- the per-domain/multi-view target-data selector generation (`FEAS1`, `MVIDX1`, `MVSEL1`, repair/rescue machinery, and associated target-data role/domain freezes);
- historical target-size migration/read-forward schemes;
- historical pre-target-size cross-validation authority;
- obsolete fixed-fidelity selector generations superseded by the current three-boundary continuous funnel; and
- implementation accidents subsequently repaired at the MACE boundary, including forced `UniversalLoss`, hidden target duplication, optimizer override, and target-batch truncation.

A historical item is not revived simply because it still appears in a snapshot, release patch, stale specification passage, or compatibility reader.

## Documentation inconsistency found during reconstruction

The review found one important residual documentation contradiction.

Current V7-era architecture and executable target-size owners use a compatibility-neutral pre-target substrate and explicitly reject retired `label_domain_id`/per-domain target-size ancestry. Some still-current-located cross-cutting and DATA5-era specification prose retains the older label-domain compatibility/partition framing.

The reconstructed D1/D2 papers follow the current architecture, accepted V7 transition, and executable owners:

- physical/numerical label compatibility remains a source/label-admission concern;
- canonical numerical label identity remains distinct from provenance; but
- the current target-size experiment does not create separate target-size/CV authorities along a historical compatibility-domain axis.

The stale specification wording should be reconciled in a dedicated documentation repair rather than copied into D1/D2 or silently interpreted as current target-size science.

## External-method references recovered

The method papers retain the external sources already used by current MLFF documentation for correlated-data analysis, dependent-data cross-validation, structured cross-validation, MLIP validation, and MACE. The papers intentionally avoid attributing mdstats-specific target-size funnel, optimizer normalization, provenance, or failure semantics to those references.

## Human-review boundary

The new D1 and D2 papers are marked reconstructed/proposed for human review. Consequential scientific or numerical statements should be adjudicated as method authority before the architecture is edited to remove any remaining detailed duplicate ownership. The present branch establishes the authority split and preserves the source evidence required for that review.
