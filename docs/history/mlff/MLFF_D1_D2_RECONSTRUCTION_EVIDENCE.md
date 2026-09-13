# MLFF D1/D2 reconstruction evidence

**Status:** non-normative reconstruction provenance  
**Reconstructed current head:** `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`  
**Date:** 2026-09-13  
**Independent reconstruction review:** `MLFF_D1_D2_RECONSTRUCTION_REVIEW_2026-09-13.md`

This note records how the missing MLFF D1 scientific-method and D2 numerical-algorithm documents were reconstructed. It is historical/provenance evidence, not a third method authority.

## Reconstruction rule

The reconstruction followed current authority first, using historical material only to explain or recover semantics that remain present in the current product. A historical algorithm was not promoted merely because it once appeared in the architecture manual or an accepted workplan.

Evidence was classified as:

1. **current product authority/evidence** — current architecture, current indexed specifications, current-generation code owners, tests, and authenticated protocol identities;
2. **accepted transition evidence** — archived workplans and commits that explain why a current invariant exists or how an implementation defect was repaired without changing that invariant; and
3. **retired historical design** — superseded selector, migration, compatibility-domain, or implementation machinery that must not be restored as current science.

Where two current documentation files disagreed, the conflict was not silently hidden. The reconstruction review identified the conflict, compared current code plus accepted transition evidence, and proposed a documentation reconciliation on the review branch while keeping the D1/D2 papers non-normative pending human acceptance.

## Current source set

The reconstruction reviewed the current MLFF architecture chapters:

- `docs/arch_manuals/mlff_training_data/10_foundations.md`;
- `20_data_contracts.md`;
- `30_statistical_design.md`;
- `40_training_evaluation.md`;
- `50_target_size_selection.md`;
- `60_execution_performance.md`;
- `80_ownership_and_decisions.md`; and
- `90_references.md`.

It also reviewed the current specification index and the relevant current narrow specifications for:

- source/label identity;
- frame conditions, eligibility, reference cells, strain, and stress;
- shared correlated-sampling primitives;
- raw feature/event evidence;
- DATA5/neutral statistical roles;
- selection descriptors/fitted evidence;
- MACE/replay/checkpoint behavior;
- campaign/post-selection execution; and
- post-production qualification.

Representative executable owners included:

- `mdstats/training_data/neutral_substrate/partition.py`;
- `neutral_substrate/split_exclusion.py`;
- `target_size_experiment.py`;
- `target_size_execution/common.py` and its execution/reducer siblings;
- `reference_fit.py`;
- `objectives.py`;
- `mace_compatibility.py`;
- current post-selection/P5 execution owners; and
- current downstream qualification owners where needed to bound the claim.

## Accepted transition evidence retained

Historical/accepted evidence was used to reconstruct present meaning, especially:

- the V7 target-size reset to one compatibility-neutral statistical substrate;
- P1 neutral source/frame/statistical authority;
- P2 exact protected-relation split, one `pi_train`/`pi_eval`, hard-support qualification, and pure reducer;
- P3 one common candidate-training preparation and paired-screen execution;
- optimizer-progress normalization and practical-ceiling semantics;
- MACE execution-semantics repairs that restored the already-declared weighted-loss/exposure/batch method;
- the operator-owned provisional/multi-size freeze boundary; and
- P5 selected-only post-selection CV plus fresh final production.

Representative accepted commits/workplans include the V7 design/implementation lineage around `832a4e1`, `ea94347`, `bad25874`, `bd1b3ae`, `63aab70`, `d9f7282`, `1bd10f1`, `e5c55b5`, `9af7d70`, `fa05c800`, `f92e6a1`, and `f4a0e77`, together with their later conformance repairs where current main includes them.

## Precise label-domain reconciliation

The reconstruction initially risked describing all label-domain material as stale. The independent review corrected that overstatement.

**Still current scientific authority:**

- source theory/electronic-structure identity;
- energy-reference identity;
- derivative/stress convention;
- numerical-quality/profile provenance; and
- the rule that target training evidence must be label-compatible.

**Retired from the current target-size graph:**

- `label_domain_id` as a target-size partition axis;
- per-label-domain target-size ladders/selectors;
- pre-target-size DATA5/MLCV authority feeding current target-size selection; and
- label-domain/CV descendants as parents of current P2/P3/P5 state.

The current `neutral_substrate/partition.py` states its scope directly: a neutral correlation/statistical substrate “without compatibility domains or CV.” Its condition key omits `label_domain_id`, and current P5 structural evidence excludes DATA5/label-domain authority from the selected-only post-selection path.

The still-indexed DATA5 specification retained older/general `PartitionConditionKey` and `CrossValidationPlan` descriptions without clearly stating this V7 cutover. The reconstruction review therefore clarifies that specification on the review branch rather than deleting the still-exposed older/general public record documentation.

## Pre-order evidence versus P3 common preparation

Another current documentation drift was discovered during review. One Part III paragraph described the “current common preparation” as producing inputs to `pi_train`, while current P2/P3 code and Parts V/VI order the graph as:

```text
pre-order selection evidence
  -> P_train/M3 and pi_train/pi_eval
  -> TargetSizeCommonPreparation over exact P_train
```

The reviewed documentation now distinguishes:

- candidate-independent fitted descriptor/difficulty/selection evidence that may contribute to P2 ordering; and
- P3 common candidate-training state (common E0, weights/masks, common MACE/model normalization, method inputs) that is fitted after P2 authority and projected without refitting onto each `T_N`.

This correction removes a circular dependency without changing executable behavior.

## Retired material deliberately excluded

The reconstruction does **not** promote the following historical designs:

- FEAS1/MVIDX1/MVSEL1 multi-view target-data selection;
- per-domain target-size authorities and competing candidate orders;
- target-size rescue/repair/migration graphs retired by V7;
- old preselection DATA5/MLCV target-size/CV coupling;
- superseded fixed-fidelity or blocking-ceiling reducer meanings; or
- dependency implementation accidents such as forced `UniversalLoss`, hidden target duplication, LR/EMA override, or dropped final target batches.

Those materials remain useful history. They are not current D1/D2 method authority.

## Reconstruction completeness review

The first reconstruction draft was strongest around target-size selection and post-selection validation but not yet information-complete for the whole MLFF branch. The independent review restored current source/condition/strain/stress/eligibility semantics, exact sampling/blocking, fitted-domain blinding, replay modes, constrained checkpoint selection, final-publication membership, downstream qualification boundaries, and additional external background references.

The full preservation map and finding-by-finding closure are recorded in `MLFF_D1_D2_RECONSTRUCTION_REVIEW_2026-09-13.md`.

## Authority status

The revised D1/D2 papers are **reviewed reconstruction candidates**. The current architecture/specifications remain normative until human acceptance promotes the upstream D1/D2 documents and a subsequent lossless D3 narrowing pass removes redundant method ownership from architecture without deleting any accepted semantics.
