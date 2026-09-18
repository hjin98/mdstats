---
kind: independent-d1-d2-review
protocol_version: 6.4.0
review: R2
result: NO-PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: a09e2b857da64e18fd7a6044f0fdad29aa29365d
binding_handoff: d5b9abdec5b6d616564081ec39ae356954eb9671
pem_basis: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
---

# Independent Review R2 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.** The R2 candidate materially improves the R1 representation and closes most R1 blockers, but it still contains four genuine Protocol-6.4 blocking defects: one D1 validity statement silently strengthens configured-prefix qualification into whole-method failure; replay lineage loses the accepted qualification coordinate; the supposedly complete direct-definition trace still contains unresolved/misbound prerequisites; and D2 uses replay-head E0 as a material lineage coordinate without an exact local definition/import dependency.

No **SERIOUS CHALLENGE** is raised against accepted D1/D2 at `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. The accepted authority remains sufficiently coherent to serve as the correction oracle. The candidate remains proposed and must not be stakeholder-ratified or promoted in this state.

A separate current-D4 conformance defect was also discovered in weighted-quantile realization. That defect is not evidence against accepted D2 or against the R2 candidate's one-normalization definition; it is a downstream implementation mismatch that must be routed for repair before overall project closeout.

## 2. Review posture

This review independently reconstructed accepted meaning from the four accepted D1/D2 method papers at the accepted basis, rechecked the applicable PEM/HAS basis, inspected immutable candidate `a09e2b857da64e18fd7a6044f0fdad29aa29365d`, and treated the R2 author-repair closure, dependency trace, handoff, and PR statements only as evidence to challenge.

Implementation was consulted only as conformance/falsification evidence under applicable `SP-004`; it was not allowed to redefine accepted D1/D2. The review was full-candidate, not a delta-only B1-B9 check.

## 3. R1 closure disposition

- **R1-B1 weighted quantile representation — CLOSED in the candidate.** `D2.DEF.013` performs one binary64 normalization and `D2.DEF.014` consumes stored weights without another normalization.
- **R1-B2 selector/MVQUAL tolerance separation — CLOSED.** `D2.DEF.020` owns `C+1e-12>=0.95`; `D2.DEF.029` separately owns Phase-A completion at `C>=0.95-1e-14`.
- **R1-B3 P1/P2/P3 numerical closure — CLOSED for the originally missing algorithms.** The R2 D2 kernel now defines/imports autocorrelation/block/event semantics, five-step component ordering, exact first-predecessor `M3`, condition-balanced `pi_eval`, structural policy, P3 common preparation, minimum-three admission, funnel/sufficiency/ceiling, and authenticated continuation.
- **R1-B4 required-family catalog — CLOSED.** `D2.DEF.012` restores the accepted family catalog and applicability rules.
- **R1-B5 REPAIR2 — CLOSED.** `D2.DEF.034-037` restore the frontier, objective, limits, rank inheritance/future displacement, reconstruction and terminal continuation.
- **R1-B6 replay — PARTIALLY CLOSED, reopened below as R2-B2/R2-B4.** Label-mode/default/opt-in, geometry invariance and true-reference monitor semantics are restored, but accepted qualification lineage and replay-head E0 source closure are still incomplete.
- **R1-B7 definition/source trace — NOT CLOSED, reopened below as R2-B3/R2-B4.** Most generic roots were repaired, but unresolved/misbound endpoints remain.
- **R1-B8 parameter binding classes — CLOSED.** Fixed method coordinates, configurable families/defaults and derived values are materially separated.
- **R1-B9 PEM/HAS — CLOSED for this target.** Accepted project state and PEM basis remain the R1-recorded basis with no validated candidate overlay.
- **Renderer repair — PASS.** The scoped D2 cardinality and sparse-diversity rewrites are mathematically equivalent representation repairs.

## 4. Blocking findings

### R2-B1 — D1 validity turns any configured membership failure into whole-method failure

Candidate `D1.DEF.018` correctly defines the automatic admitted subset

```text
Q_cfg = {N in N_cfg : Q_mem(N)}
```

and correctly says automatic screening is defined when at least three configured candidates qualify. This agrees with accepted D1: configured prefixes are independently qualified; the automatic reducer operates on the qualified subset; too few comparable candidates gives no recommendation rather than redefining membership.

However candidate Section 9 then states that **“the method fails/defers” when “configured membership fails”**, in the same failure list as impossible reserve construction, impossible monitor, non-identifiable E0, etc. Read literally, one unqualified configured prefix fails the method even when three or more other configured prefixes remain qualified. That contradicts `D1.DEF.018` and silently strengthens accepted D1.

The accepted method instead permits an automatic ladder containing unqualified configured prefixes: those prefixes are excluded from `Q_cfg`; automatic comparison proceeds if at least three qualified candidates remain. Manual/operator admission of an unqualified membership fails, but an unqualified member of the configured ladder does not by itself invalidate the experiment.

**Required repair:** replace the ambiguous global failure clause with the exact accepted distinction. State explicitly that an unqualified configured prefix is excluded from automatic `Q_cfg` and cannot be manually/admissibly selected for training/CV; whole automatic comparison becomes insufficient only when fewer than three qualified configured candidates remain. Preserve `FAIL* -> PASS*` qualification monotonicity.

### R2-B2 — Replay lineage omits the accepted qualification coordinate

Accepted D1 states that changing replay mode, source content, split, prediction policy, foundation identity, **or qualification** changes replay lineage and invalidates affected post-selection evidence.

Candidate `D1.DEF.022` defines replay lineage as

```text
(D_r^geom, label_mode, M_r^true, Phi, Pi_r)
```

and enumerates source/split, label mode, prediction policy, foundation/head, true monitor and exposure as lineage-changing coordinates, but not qualification. Candidate `D2.DEF.052` likewise binds geometry/source/split, label mode, true monitor, foundation/head, replay-head E0, prediction policy and realized exposure, again omitting qualification.

Because these are explicit replay-lineage definitions, the exact import cannot safely recover an omitted coordinate without creating conflicting meanings. A replay qualification-policy/evidence change could therefore be treated as lineage-preserving under the formal kernel even though accepted D1 says it is lineage-changing.

**Required repair:** add the accepted replay qualification identity/state as a first-class lineage coordinate (or exact typed imported coordinate) in D1 and carry it into D2 concretization/currentness. State that changing qualification invalidates dependent P5 evidence without changing replay geometry membership merely by label-mode switch.

### R2-B3 — The “final” direct-definition trace still has unresolved and misbound prerequisites

The R2 trace claims exact, source-resolvable direct `USES_DEFINITION` closure, but at least the following defects remain:

1. `D2.DEF.061` lists the prerequisite **“each object's owned equality/tolerance relation”**. This is not an exact semantic object ID, exact import, or basis-pinned owner locator. It recreates the generic endpoint class R1-B7 required to remove.
2. `D1.DEF.007` (the correlation diagnostic estimand) is traced to `D1.IMP.ROLES`, whose declared import range is general D1 Sections 4.1-4.6. The accepted autocorrelation/effective-count scientific definition is in general D1 Section 2.2, not that role import. The current edge is therefore source-misbound.
3. `D2.DEF.052` materially uses replay-head E0 but its trace does not depend on `D2.IMP.E0` or another exact E0 owner, even though accepted general D2 Section 8.3 owns replay/pretraining-head foundation E0 binding.

These defects matter because the trace is the candidate's bounded completeness/impact artifact; a competent reviewer cannot reverse-traverse them to an exact owner without inference outside the declared graph.

**Required repair:** remove the generic `D2.DEF.061` endpoint by defining an exact composite/equivalence-prerequisite object or enumerating exact source/definition roots; rebind `D1.DEF.007` to its correct exact source (or make it explicitly self-contained with only foundational prerequisites); add the missing replay-head E0 dependency and re-run full forward source-availability plus reverse-impact closure.

### R2-B4 — `D2.DEF.052` uses replay-head E0 before an exact definition/import path is established

Candidate `D2.DEF.052` makes **replay-head E0** part of replay lineage. This is material: accepted D2 requires replay/pretraining-head foundation E0 to come from the authenticated selected foundation head/lineage and to remain separate from the fitted target corrected E0 mapping.

But the candidate's local E0 formalization (`D2.DEF.040-042`) defines the target composition matrix, target foundation-residual correction, and transfer feasibility only. `D2.DEF.052` then introduces “replay-head E0” without a local definition and without directly importing the accepted Section 8.3 replay/pretraining-head mapping. `D2.IMP.REPLAY` points to Section 18, which does not own that E0 extraction rule.

This is a material first-use/source-availability gap under Protocol 6.4 and also explains the missing trace edge in R2-B3.

**Required repair:** define or exact-import the replay/pretraining-head foundation E0 mapping before `D2.DEF.052`; bind it to the same authenticated selected foundation checkpoint/head required by the method; preserve its separation from target corrected E0; then add the exact direct dependency.

## 5. Separate descendant D4 conformance defect discovered during review

### D4-F1 — Current `_weighted_quantiles` rescales the quantile threshold by residual post-normalization mass

Accepted scoped D2 says family weights are normalized **once** by their binary64 sum and stored; weighted quantiles then take the first stable-sorted value whose cumulative stored weight reaches `q`.

Current `coverage_reference.py::correlation_balanced_weights` performs the accepted one-time normalization. But `_weighted_quantiles` then computes

```python
cumulative = np.cumsum(weights[order], dtype=np.float64)
total = float(cumulative[-1])
indices = np.searchsorted(cumulative, requested * total, side="left")
```

so the comparison threshold is `q * sum(stored_weights)` rather than exactly `q`. Because the stored binary64 sum need not equal exactly one, this is not generally equivalent to accepted D2.

Independent binary64 witnesses using the implementation's own weight construction show changes on quantiles actually used by the method:

- two correlation units with witness counts `(2,6)`, `q=0.25`: stored sum `1.0000000000000002`, first cumulative `0.25`; accepted D2 selects index 0, current D4 threshold `0.25000000000000006` selects index 1;
- counts `(50,1)`, `q=0.01`: accepted index 0, current D4 index 1;
- counts `(1,6)`, `q=0.75`: accepted index 4, current D4 index 3;
- counts `(1,150)`, `q=0.99`: accepted index 148, current D4 index 147.

Thus the defect can alter robust scales/extents and downstream neighborhoods/coverage on adversarial FP64 cases. It does **not** invalidate the R2 candidate's corrected one-normalization semantics; it shows current D4 is not exactly conformant to already-accepted D2.

**Required routing:** repair the real owner by consuming the once-normalized stored weights directly, i.e. compare cumulative stored mass to `q` rather than `q*total`; add adversarial tests for the governed `0.01/0.25/0.75/0.99` quantiles. Do not add a wrapper or widen tolerances. Treat this as a D4 descendant repair under unchanged D2 authority and close it before overall formalization/integration closeout.

## 6. Passed checks and Challenge disposition

The repaired candidate now preserves the R1 one-normalization rule, distinct selector/MVQUAL tolerances, required family catalog, exact target-order/repair structure, P3 funnel/sufficiency/ceiling, monitor/fold/threshold separation, replay true/pseudo default/opt-in behavior, fixed/configurable/default binding classes, and PEM/HAS basis. The scoped renderer correction remains mathematically equivalent.

No accepted D1/D2 contradiction, impossibility, or wrong scientific/numerical estimand was found. The D4-F1 mismatch is ordinary descendant nonconformance, not a Serious Challenge to accepted D2.

## 7. R3 gate

A new immutable semantic target is required after repairing R2-B1 through R2-B4. Do not mutate `a09e2b857da64e18fd7a6044f0fdad29aa29365d` in place.

Fresh R3 must review the complete assembled candidate, not just these four findings. At minimum it must independently verify:

1. automatic exclusion of unqualified configured prefixes versus whole-method failure semantics;
2. replay qualification as a lineage/currentness coordinate in both D1 and D2;
3. exact source-resolvable direct trace closure with no generic endpoint and correct correlation/E0 owners;
4. replay-head E0 definition-before-use and selected-head binding;
5. continued closure of all R1 findings and renderer equivalence;
6. disposition of D4-F1 as a downstream conformance repair under unchanged accepted D2;
7. unchanged accepted basis/PEM/HAS or an explicit rebase if those advance before R3.
