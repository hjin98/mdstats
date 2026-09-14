# Gate A Revision 5 capability-transfer map

Date: 2026-09-13
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Candidate: Revision 5
Status: Gate-A historical capability reconciliation; non-authoritative evidence/coordination artifact.

## 1. Purpose

This map satisfies parent-workplan Section 11.9 by separating historical capability from historical mechanism. A historical success can justify preserving or challenging a capability hypothesis; it does not automatically restore the old topology, quotas, score constants, or labels.

Disposition vocabulary:

- `CURRENT_AUTHORITY`: already accepted in current D1/D2 and preserved;
- `PROPOSED_FOR_PROMOTION`: Revision 5 proposes the capability as part of new D1/D2;
- `EVIDENCE_ONLY`: useful implementation/verification pattern or historical evidence, not current scientific/numerical authority;
- `RETIRED`: mechanism/constant intentionally not carried into the baseline method.

## 2. Immutable historical/source routes

The map draws from these frozen/current sources:

- early DATA-series architecture: `docs/history/mlff/manual_snapshots/mlff_training_data_architecture_pre_doc_gov1.md`;
- early DATA-series stage-plan snapshot: `docs/history/mlff/manual_snapshots/mlff_data_stage_plan_spec_pre_doc_gov1.md`;
- later target-coverage/MV lineage: `docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV72.md`;
- V7 reset: `workplans/archive/MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`;
- V7 P2 statistical package: `workplans/archive/mlff-target-size-v7-packages/P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md`;
- accepted current FPS/coverage kernels: `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d:mdstats/training_data/selection.py`;
- accepted current D1/D2: `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d:docs/methods/{mlff_scientific_method,mlff_numerical_algorithmic_method}.md`.

The early DATA7 lineage and later MVSEL/MVQUAL lineage are not collapsed into one historical mechanism: they overlapped in coverage/diversity goals but differed in products, diagnostics, and qualification structure.

## 3. Capability transfer

| Historical capability | Historical source/identity | Disposition | Revision-5/current replacement | Acceptance / oracle route | Omission rationale where not preserved |
| --- | --- | --- | --- | --- | --- |
| one canonical master training order with exact nested prefixes | early DATA selector lineage; later V7 reset/current D1/D2 | CURRENT_AUTHORITY + PROPOSED_FOR_PROMOTION | one `pi_train`; `T_N=pi_train[:N]` | exact prefix/permutation/cardinality metamorphics | preserved; central experimental invariant |
| mandatory condition/support anchors | early quota/anchor selection lineage | PROPOSED_FOR_PROMOTION | one `d_P` median-medoid anchor per nonempty P_train neutral condition | anchor inclusion; `N_min >= #conditions`; UID/input-order metamorphics | historical quota mechanics not retained |
| representative/centroid support | early representative-density/centroid queues | PROPOSED_FOR_PROMOTION | coordinate-wise median medoid under canonical fitted `d_P` | direct medoid reference fixture | centroid/reduction machinery replaced by deterministic medoid |
| configuration-level exact FPS/maximin diversity | early DATA7 exact FPS; accepted `selection.py` kernels | PROPOSED_FOR_PROMOTION | exact condition-local FPS through `K=max N` | simple scalar FPS reference; nonincreasing full-population covering radius | preserved capability, consolidated into one order owner |
| species/environment coverage queues | early species/environment queues | PROPOSED_FOR_PROMOTION in generalized form | material-neutral element-resolved local-structure metric families | real-feature family sensitivity/ablation; coordinate-lineage audit | LTA/material-specific queues retired from baseline |
| material/profile site/group coverage | early application-specific queues and later profile products | RETIRED from baseline membership; diagnostic/future explicit obligation only | no declared/profile groups in baseline metric | provider-policy audit; future D1 acceptance required for hard/profile use | prevents material-specific baseline semantics |
| rare/protected-event prioritization | early rare-event queue | RETIRED as automatic queue; CURRENT/PROPOSED as explicit obligation/diagnostic | P1 protection governs split; event counts remain soft; explicit accepted hard obligations may gate prefixes | hard/soft separation tests | no implicit event quota or automatic ordering credit |
| foundation residual/difficulty enrichment | early/later difficulty queues | RETIRED from membership; EVIDENCE_ONLY after membership freeze | no foundation/difficulty split/order input | stage-by-evidence leakage tests | avoids model-dependent target-size membership and GPU prerequisite |
| near-duplicate pruning / redundancy control | early redundancy queues / protected relations | PROPOSED_FOR_PROMOTION in replacement form | P1 protected/duplicate components plus retained-set structural-redundancy split and FPS | mutual-redundancy counterexample; J*/completion reference | no separate pruning selector/topology |
| condition balancing | historical interleaving and current condition round-robin | PROPOSED_FOR_PROMOTION | exact integer proportional deficit scheduler after anchors | prefix condition-count discrepancy reference | deterministic and exact; no floating deficits |
| correlation/protected balancing | DATA5/legacy partition relations, later selection balancing | CURRENT_AUTHORITY for split exclusion; EVIDENCE_ONLY for post-split balancing | protected components indivisible; correlation remains diagnostic | protected-component split tests | no second correlation-driven order owner |
| maximum covering radius `D_max` | later MV coverage lineage | PROPOSED_FOR_PROMOTION as soft diagnostic | `R_max(N)=max_x min_{y in T_N} d_P(x,y)` | independent full-P_train rescoring; monotonicity | renamed to current single-metric semantics |
| aggregate distance `D_sum` | later MV coverage lineage | RETIRED baseline | no current normative equivalent | future promotion only with scientific role/normalization | redundant/scale-dependent under current compact baseline |
| `N95` historical coverage statistic | later MV coverage lineage | RETIRED baseline | Q95 nearest-selected distance retained instead | diagnostic direct reference | historical definition/mechanism not needed for current method |
| uncovered witness/radius mass | later MVQUAL lineage | RETIRED baseline | Q90/Q95/Q99 + R_max + support summaries | diagnostic direct reference | no accepted current radius threshold; avoids resurrecting arbitrary constants |
| selected-to-selected nearest-neighbor diagnostics | early/later diversity evidence | PROPOSED_FOR_PROMOTION as soft diagnostics | selected-NN Q50/Q90/Q95 | direct rescoring | useful anti-collapse telemetry, not hard gate |
| condition/environment/event coverage counts | early/later selection qualification evidence | PROPOSED_FOR_PROMOTION as soft evidence; hard only when explicitly configured | represented-condition/family/event summaries + explicit hard obligations | monotonic support-count oracles | preserved capability without implicit quotas |
| independent rescoring rather than selector-internal coverage flags | later MVQUAL discipline | EVIDENCE_ONLY verification pattern | independently rescore full P_train for each configured prefix | direct reference scorer vs selector result | verification method, not scientific membership authority |
| sparse/lazy/reference-equivalent FPS kernels | historical performance qualification + current `selection.py` | EVIDENCE_ONLY D3/D4 concretization option | any bounded implementation reproducing canonical D2 decisions | optimized-vs-scalar differential at downstream gate | implementation identity remains replaceable |
| public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL product topology | later multi-view architecture | RETIRED | one P2 split/order owner and ordinary diagnostics | architecture conformance review | capability survives without historical machinery; SP-001 |
| historical fixed quota fractions | early DATA7 queue schedules | RETIRED / EVIDENCE_ONLY | no fixed quota schedule; hard condition anchors + proportional mass + FPS | D1/D2 review | no current scientific justification for copied constants |
| historical radius/coverage thresholds | later MVQUAL policies | RETIRED / EVIDENCE_ONLY | coverage remains soft unless a future explicit hard policy is accepted | D1 acceptance needed for any future threshold | coverage is not adequacy by default |
| changing M1/M2/M3 evaluation populations as automatic decision ladder | current pre-repair D1/D2/V7 screen | RETIRED by Revision 5 proposal | exact M3 at every automatic fidelity boundary; M1/M2 diagnostic SRSWOR only | full-M3 estimator oracle; diagnostic-permutation invariance | removes uncontrolled evaluation-sampling elimination risk |
| EVAL2 Cartesian force-component RMSE | current accepted D1/D2 | CURRENT_AUTHORITY | unchanged exact component-weighted M3 target-force RMSE | direct SSE/component-count reference | preserved exactly |
| one study, no target-size label-domain fanout | V7 reset/current D1/D2 | CURRENT_AUTHORITY | preserved | identity/topology review | avoids reintroducing retired domain fanout |
| target-size screening target-only / replay excluded | current accepted D1/D2 | CURRENT_AUTHORITY | unchanged | leakage and experiment-identity checks | replay remains post-selection method evidence |

## 4. Historical constants and mechanism boundary

The map intentionally does **not** promote old queue fractions, radius thresholds, multi-view score weights, rescue-size logic, or material-specific selector labels. Those values remain discoverable historical evidence and can inform future challenges, but Revision 5 has its own explicitly reconstructible method.

The current proposal reuses historical capability only where the capability still answers the present scientific question:

```text
condition support
+ representative anchor
+ material-neutral frame-level structural coverage
+ exact nested prefixes
+ independent coverage diagnostics
```

It deliberately excludes historical mechanisms that would recreate the retired multi-owner selector topology.

## 5. Evidence-stage ownership

The capability-transfer decision itself is Gate-A coordination evidence. Subsequent production realization belongs downstream:

- Gate A: scientific/numerical adequacy, historical transfer, reference cases, sensitivity, feasibility;
- Gates B-E: architecture ownership, persistence/currentness, implementation equivalence, real integration, regression and release evidence.

This map therefore closes the Section-11.9 transfer obligation without pretending the future D3/D4 mechanism already exists.