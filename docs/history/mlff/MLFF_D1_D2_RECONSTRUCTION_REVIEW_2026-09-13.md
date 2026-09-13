# MLFF D1/D2 reconstruction review — 2026-09-13

**Status:** non-normative reconstruction review evidence  
**Baseline reviewed:** `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`  
**Review branch:** `docs/mlff-d1-d2-method-reconstruction`  
**Layers reviewed:** D1 scientific formulation, D2 numerical algorithm design, and directly affected D3/specification documentation

This note records the independent lossless-representation review of the reconstructed MLFF D1 and D2 method papers. It is evidence about the reconstruction, not a replacement method authority.

## 1. Review rule

The review used the current accepted repository first:

- canonical MLFF architecture chapters `10`, `20`, `30`, `40`, `50`, `60`, `80`, and `90`;
- the current specification index and the narrow source/frame/sampling/DATA5/training/campaign/qualification specifications;
- current P1 neutral-substrate, P2 target-size, P3 common-preparation/MACE, and P5 post-selection owners; and
- accepted historical V7 transition/workplan/commit evidence only where needed to disambiguate current intent.

A reconstruction statement was retained only when it was supported by current authority or by accepted history that is still realized by current authority. Historical algorithms retired by the V7 cutover were not promoted because they were once documented.

The review sought four failure classes:

1. **loss** — a material current scientific/numerical rule present in the repository but absent from D1/D2;
2. **fabrication** — a D1/D2 claim stronger than current evidence or not present in the current method;
3. **drift** — a reconstructed claim that follows a retired design or current implementation accident instead of the accepted method; and
4. **ownership error** — D1/D2/D3/D4 material placed at the wrong authority layer.

## 2. Findings and closure

### R1 — D1 was too target-size-centric — CLOSED

The first D1 draft captured the target-size/CV core but under-represented current scientific contracts for:

- source occurrence versus content identity;
- geometry versus label versus labeled-configuration identity;
- theory/energy-reference/derivative/stress compatibility;
- explicit target energy-channel semantics;
- ensemble/temperature distinction;
- reference-cell, deformation, strain, and stress conventions;
- eligibility versus rarity/difficulty;
- event-before-thinning semantics;
- independence hierarchy and feasibility/deferral;
- feature blinding and fitted-domain isolation;
- material/profile applicability; and
- the downstream physical/deployment qualification boundary.

The revised D1 restores these concepts and retains the target-size method as one part of the complete MLFF scientific workflow.

### R2 — D2 omitted foundational numerical methods — CLOSED

The first D2 draft focused on P2/P3/P5. It omitted numerical contracts already relied upon by current MLFF evidence construction. The revised D2 now includes:

- row-vector cell/deformation and polar-decomposition conventions;
- stress normalization/round-trip semantics;
- exact shared autocorrelation estimator and effective-sample convention;
- complete-frame block construction and protected-event merging;
- canonical protected-relation closure;
- the distinction between pre-order fitted selection evidence and post-order common candidate-training preparation;
- common configuration-weight/property-mask and MACE neighbor/model normalization; and
- constrained post-selection checkpoint/final-product selection semantics.

The D2 paper continues to delegate pure software/persistence machinery to D3/D4.

### R3 — “independent validation” wording could overclaim available evidence — CLOSED

The first D1 could be read as claiming statistically independent post-selection validation in all campaigns. Current architecture records a hierarchy from independent replicas/runs down to purged temporal blocks and explicitly records weak/slow-state limitations.

The revised D1 uses “held-out evidence with explicit independence strength/limitations” and states that temporal blocking does not create independent metastable-state evidence.

### R4 — replay was described as true-label-only — CLOSED

The first papers emphasized true-label replay and omitted the current explicit pseudo-label replay mode. Current architecture supports true-reference replay as the canonical default and foundation pseudo-label replay only by explicit opt-in, with a separate true-reference replay monitor.

The revised D1/D2 preserve both modes and explicitly separate replay from the target-size screen, which remains target-only.

### R5 — current documentation collapsed two fitted stages — CLOSED on this branch

Part III previously said that the “current common preparation” emitted products that are inputs to the canonical training order. Current P2/P3 code and Parts V/VI instead define:

```text
pre-order selection evidence
  -> P2 P_train/M3 split and pi_train/pi_eval
  -> P3 TargetSizeCommonPreparation over exact P_train
```

The first item may include fitted descriptor/difficulty evidence used to construct `pi_train`. The second contains candidate-training common state such as common E0, weights/masks, and common MACE/model normalization. P3 common preparation cannot feed backward into P2 order construction.

The revised D1/D2, architecture front matter, Part III, and specification index now use this two-stage terminology.

### R6 — label-domain contradiction was initially stated too broadly — CLOSED

The first reconstruction evidence note called current label-domain prose “stale” too generally. That would have incorrectly retired legitimate source-label compatibility science.

The precise current distinction is now:

- source theory/energy-reference/derivative compatibility and one-compatible-target-label-domain rules remain current;
- the V7 **target-size substrate** is compatibility-neutral and has no `label_domain_id` partition axis or pre-target-size CV authority; and
- old DATA5 label-domain/CV records cannot become parents of current P2/P5 target-size/CV state.

The still-indexed DATA5 specification had not made this cutover explicit and therefore appeared to contradict current V7 code/history. It has been reconciled on this branch without deleting its still-exposed older/general public record documentation.

### R7 — exact `M3` allocation was under-specified — CLOSED

The first D2 said “deterministically ordered” components plus exact subset-sum. That was insufficient because multiple exact component subsets can have cardinality `M3`; changing tie-breaking changes scientific membership.

The revised D2 records the current component-size/condition round-robin order and the first-predecessor deterministic exact subset-sum semantics. It explicitly permits a different implementation data structure only when the selected `M3` membership is output-equivalent.

### R8 — optimizer normalization could be misread as exact path equivalence — CLOSED

The revised D2 now states that

$$
LR_N U_N=LR_{ref}U_{ref}
$$

and the analogous EMA relation are first-order progress normalizations. Minibatch stochasticity, Adam/AMSGrad moment history, finite learning-rate discretization, and candidate-dependent gradients remain residual differences. The method does not claim optimizer-path invariance across `N`.

### R9 — MACE 0.3.16 guards were placed too close to timeless D2 authority — CLOSED

The numerical invariant is the resolved mathematical loss/optimizer/exposure/batch semantics. The exact pinned dependency version, source markers, and wrapper repair mechanism are current D3/D4 conformance evidence.

The revised D2 keeps the current 0.3.16 behavior as an explicit realization note while stating that a future dependency may replace it only by proving the same D2 semantics or by reopening D2.

### R10 — downstream product status was incomplete — CLOSED

The first D1 described downstream qualification generically but omitted the current product limitation that release qualification is single-size only. The revised D1/specification index now state that a multi-size frozen design is a valid comparative completed experiment but is not silently a release-qualified product family.

### R11 — external/background references were too sparse — CLOSED

The first papers carried only the MACE/correlated-data/CV core references. The revised D1 adds the current foundation-model, data-generation, committee/UQ context already present in repository references; D2 adds Geyer's autocorrelation reference and keeps version-qualified MACE dependency references at the realization boundary.

No new scientific claim was introduced solely because a citation was added.

## 3. Preservation map

| Current repository subject | Reconstructed owner | Review result |
|---|---|---|
| PES energy/force/stress meaning | D1 §2; D2 §2 | preserved |
| source occurrence/geometry/label identities | D1 §3; D2 §2 | restored |
| label compatibility and target energy channel | D1 §3 | restored; target-size/domain distinction clarified |
| ensemble/temperature/reference cell/strain/stress | D1 §3; D2 §2 | restored |
| eligibility vs rare/difficult physics | D1 §3; D2 §2 | restored |
| autocorrelation/effective sample/blocking | D1 §2/4; D2 §3 | restored with exact shared estimator |
| event-before-thinning/protected relations | D1 §4; D2 §3 | preserved/expanded |
| independence hierarchy/feasibility/deferred roles | D1 §4 | restored |
| fitted-domain blinding | D1 §4; D2 §4 | restored |
| pre-order selection inputs | D1 §5.1; D2 §4.1 | separated from P3 common training prep |
| `P_train/M3` exact split | D1 §6; D2 §5 | preserved; tie algorithm made explicit |
| canonical `pi_train`/`pi_eval` and prefixes | D1 §6; D2 §6 | preserved |
| hard-support qualification | D1 §6; D2 §7 | preserved |
| common P3 target-size preparation | D1 §5.2; D2 §4.2/8 | preserved and ordered correctly |
| E0 residual fitting/conditioning | D1 §7; D2 §8 | preserved/expanded |
| objective/configuration/property weights | D1 §7; D2 §8/9 | preserved |
| optimizer-progress normalization | D1 §6; D2 §10 | preserved; non-equivalence limits restored |
| continuous fidelity trajectories/restart | D1 §6; D2 §11 | preserved |
| EVAL2 force RMSE | D1 §6; D2 §12 | preserved |
| reducer/practical equivalence/ceiling semantics | D1 §6; D2 §13 | preserved |
| operator recommendation-vs-decision boundary | D1 §6 | preserved/expanded |
| constrained checkpoint selection | D1 §7; D2 §15 | restored |
| post-selection fold semantics | D1 §9; D2 §14 | preserved; DATA5/P5 distinction clarified |
| replay modes/retention separation | D1 §8; D2 §16 | corrected/expanded |
| fresh final production and seed publication | D1 §10; D2 §17 | expanded |
| downstream qualification/observable ownership | D1 §11 | restored |
| material/profile applicability and LTA context | D1 §12 | restored |
| validity/uncertainty/falsification | D1 §13–15; D2 §19–22 | expanded |
| execution/resource/cache exactness boundary | D2 §19–22; D3 Part VI | preserved without duplicating D3 machinery |

## 4. Retired material deliberately not restored as current method

The review found no basis to promote the following historical systems back into D1/D2:

- FEAS1/MVIDX1/MVSEL1 multi-view target-size selection;
- per-label-domain target-size ladders and per-domain candidate authorities;
- pre-target-size DATA5/MLCV coupling as current P2/P5 authority;
- rescue/migration/read-forward target-size generations;
- obsolete fidelity ladders or blocking-ceiling terminal semantics; and
- dependency implementation accidents (forced UniversalLoss, hidden target duplication, LR/EMA override, `drop_last=True`) as intentional method.

Historical documents remain useful provenance for why current invariants exist, but they are not current algorithm owners.

## 5. Current-documentation repairs made by this review

The review changes current documentation on the reconstruction branch only where multiple current sources were already inconsistent with the assembled current implementation/history:

1. Part III now distinguishes pre-order fitted selection evidence from later P3 common target-size training preparation.
2. Architecture front matter reflects the same dependency order.
3. DATA5 specification now distinguishes still-documented legacy/general record APIs from the V7 neutral target-size substrate and P5 post-selection CV authority.
4. The training-data specification index records these boundaries explicitly.

No executable code, scientific constant, candidate membership, model, or stored campaign artifact is changed by this documentation review.

## 6. Remaining authority transition

After these repairs, the reconstructed D1/D2 papers are materially information-complete relative to the reviewed current MLFF method **for promotion purposes**, but they remain candidate authorities until human acceptance.

Therefore the architecture still intentionally retains overlapping D1/D2 prose. The next step after acceptance is a mechanical/lossless D3 narrowing pass:

- promote the accepted D1/D2 papers to normative upstream authority;
- replace duplicated architecture equations/method paragraphs with concise consequences and links only after a concept-by-concept preservation check;
- retain source-specific current specifications for exact schemas/constants/runtime behavior; and
- regenerate publication artifacts and run the documentation consistency checks.

Deleting the old architecture method prose before acceptance would reduce reviewability and create the very information-loss risk this reconstruction is intended to eliminate.
