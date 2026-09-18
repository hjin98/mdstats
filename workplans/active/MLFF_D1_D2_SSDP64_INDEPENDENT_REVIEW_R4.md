---
kind: independent-review-record
protocol_version: 6.4.0
status: NO_PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 86fa8acec3cfc84584bfbd380163545d80de7a27
binding_handoff: 9b6f296f0362ba6b6d45ed80001cf120f2ce51c3
prior_candidate_target: 045cb5a052fdb83b6c6cd561142b24fdf5d023b5
prior_review_result: R3_NO_PASS
serious_challenge: NONE
---

# Independent Review R4 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.**

No Serious Challenge is raised against accepted D1/D2 authority at
`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

The immutable R4 target closes R3-B2: the direct D4 weighted-quantile repair now
has current focused and real-owner affected-surface executable evidence, and
that evidence remains applicable to the immutable target.

The R3 D1/D2 semantic kernels remain substantively lossless on fresh review,
the renderer repair remains equivalent and safe, and the accepted basis/PEM/HAS
state has not drifted.

One genuine Protocol-6.4 blocker remains: **R3-B1 is not fully closed.** The R4
dependency graph is structurally well-formed but still omits material direct
`USES_DEFINITION` edges under the active workplan's own direct-edge criterion.

## 2. Review basis and independence

This Review reconstructed accepted meaning from the four canonical method papers
at accepted basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`:

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_target_training_order_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

At review time, `main` still resolves exactly to the accepted basis. PR #16 is
open/draft and its branch head is the R4 handoff descendant, not a changed
semantic target.

The R4 handoff, author closure, R3 review, CI outcomes and prior review
conclusions were treated as evidence/challenges only. They were not used as
authority.

The current accepted Project Engineering Memory blob remains
`67e3130d3703d9fc26ed0afe94fa2506a176e9ce`, reports no high-impact unresolved
notice, and remains evidence-only. Fresh HAS challenge supports the same bounded
dispositions:

```yaml
has:
  - {id: SP-001, disposition: APPLICABLE}
  - {id: SP-002, disposition: APPLICABLE}
  - {id: SP-003, disposition: APPLICABLE}
  - {id: SP-004, disposition: APPLICABLE}
  - {id: FF-001, disposition: APPLICABLE}
  - {id: FF-002, disposition: APPLICABLE}
  - {id: FF-003, disposition: NOT_APPLICABLE}
  - {id: FF-004, disposition: NOT_APPLICABLE}
  - {id: FF-005, disposition: APPLICABLE}
```

GPU scheduler/admission history remains outside this formalization and GPU
qualification remains deferred.

## 3. D1 review — substantive semantics pass

The proposed D1 kernel remains byte-identical to R3 blob
`dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`, but its semantics were rechecked
against accepted D1 rather than inherited from R3.

Material surfaces remain lossless:

- source occurrence, geometry, label and compatibility semantics;
- energy-conserving energy/force/stress meaning and imported cell/stress
  conventions;
- protected-relation closure and role/noninterference semantics;
- correlation diagnostic estimand from exact statistical import
  `D1.IMP.STAT`;
- exact `U_size = P_train dot-union M3` and controlled target-size experiment;
- one complete deterministic `pi_train`, exact nested prefixes and strict
  selector-information boundary;
- required family roles, equal correlation-unit reference mass, fixed
  `0.95` coverage and `0.01/0.99` extent coordinates;
- canonical hard-support obligations, repair continuity and independent
  membership qualification;
- exclusion of an unqualified configured prefix without whole-method failure
  when at least three other configured candidates remain qualified;
- foundation-P5 `1:10:1` E/F/S objective semantics, selected-head E0
  identifiability and replay lineage/currentness;
- one protected 256-frame common target monitor;
- configurable CV fold count `K>=2`, default 3;
- independent `tau_CV`, `theta_CV`, `tau_prod` generated-default
  coordinates with current defaults `45/45/30 meV/angstrom`;
- fixed-budget all-position CV, fresh production and downstream no-feedback.

No D1 semantic blocker or upward Challenge was found.

The kernel front matter still uses the historical R3 round label. Because R4 is
explicitly permitted to reuse the exact R3 kernel blobs and the R4 workplan and
handoff bind the current lifecycle externally, this is classified as
non-semantic round nomenclature, not a blocking authority drift. Changing the
kernel solely to rename the round would create an unnecessary semantic-target
delta.

## 4. D2 review — substantive semantics pass

The proposed D2 kernel remains byte-identical to R3 blob
`74c0c0588617b7f48fd93bc21e534f538f037ef8`. Fresh comparison against accepted
D2 found no method drift in the material numerical chain:

- unbiased finite-sequence autocovariance, Geyer IPS truncation, complete-frame
  blocks and protected-event/relation closure;
- structural target-size policy, five-step protected-component order and exact
  first-predecessor M3 allocation;
- condition-balanced `pi_eval` and candidate-common P3 preparation;
- complete required target-order family catalog/applicability;
- one and only one binary64 family-weight normalization;
- stable weighted quantile using cumulative stored weight against direct
  governed `q`;
- IQR/98%-span/population-std robust scale, leave-one-out local radius and exact
  adjacency;
- distinct MVQUAL `1e-12` and MVSEL2 `1e-14` coverage predicates;
- canonical obligations, FEAS1, exact MVSEL2 priorities, certified-lazy
  termination/guard and complete REPAIR2 semantics;
- independent MVQUAL and minimum-three-qualified automatic admission;
- P3 optimizer-progress normalization, estimator, practical-equivalence
  reducer, funnel/sufficiency and configured-ceiling rule;
- foundation target E0 fit/null-space transfer and separate replay/pretraining
  head E0 mapping;
- true-reference default/pseudo explicit opt-in replay, replay qualification
  currentness and replay-first `drop_last=true` exposure;
- common monitor, fold construction/purge, role-effective checkpoint predicates,
  all-position CV and fresh production;
- authenticated continuation, bounded numerical-equivalence registry and
  execution noninterference.

No accepted D2 numerical-method defect or upward D2 Challenge was found.

## 5. R4-B1 — direct dependency trace remains semantically incomplete

**Blocking.**

The active workplan defines a direct semantic edge

`A USES_DEFINITION -> B`

when materially changing `B` can change the denotation, domain, validity or
interpretation of `A`. The R4 trace passes mechanical graph checks but fails
that semantic completeness criterion.

### 5.1 Definitive witness: covered-mass concretization is disconnected from its D1 owner

`D1.DEF.015` defines the scientific covered mass

```text
C_m(S) = mu_m({w : N_m(w) intersects S})
```

and owns its scientific interpretation.

`D2.DEF.019` directly concretizes that same quantity numerically:

```text
n_m(w;S) = sum_{c in S} A_m(w,c)
C_m(S) = sum_w omega_m(w) 1[n_m(w;S)>0]
```

Changing the D1 definition of covered mass can therefore directly change the
denotation and validity of `D2.DEF.019`.

The R4 trace row is nevertheless:

```text
D2.DEF.019 -> D2.DEF.013; D2.DEF.018
```

and omits `D1.DEF.015`.

This is not a transitive-edge preference. `D2.DEF.019` is the numerical
concretization of the D1 object itself. The omission also breaks reverse-impact
reachability from the D1 coverage definition into D2 users of covered mass such
as selector and repair state unless another unrelated edge happens to reach a
subset of those descendants.

That single witness is sufficient to falsify the R4 trace-completeness claim.

### 5.2 Additional direct-edge omissions found during the challenge pass

The same defect class remains elsewhere:

1. **`D1.DEF.023 — Common target monitor`** states that `M_mon` is
   protected-relation-disjoint from **every configured target prefix**. The
   trace row names `D1.DEF.005`, `D1.DEF.006` and `D1.IMP.P5`, but omits:
   - `D1.DEF.012`, which defines exact target prefix `T_N`; and
   - `D1.DEF.009`, which defines the configured candidate-size family.
   Materially changing either can directly change the quantified set from which
   monitor separation must hold and therefore the validity of `D1.DEF.023`.

2. **`D1.DEF.024 — Post-selection folds`** assigns exact parts of `T_N` to
   gradient, held-out and purge/exclusion **roles**. The trace row omits
   `D1.DEF.006`, the formal evidence-role vocabulary/permission owner.
   Changing role semantics changes the interpretation of the fold partition
   directly, not merely through a transitive numerical descendant.

3. **`D2.DEF.041 — Foundation-residual fit`** explicitly fixes the CV fit
   domain to the exact fold gradient membership and final-production fit domain
   to exact `T_selected`. Its row includes `D1.DEF.020` and the accepted D2
   E0 import, but omits the local D1 owners that directly define those role
   domains:
   - `D1.DEF.024` for fold gradient membership; and
   - `D1.AX.010` for fresh-production exact target membership.
   A material change to either D1 role-domain definition changes the admissible
   E0 fit domain of `D2.DEF.041`.

These witnesses show that the R4 author-side “106/106, resolved, acyclic” check
proved graph structure, not direct semantic completeness.

### 5.3 Required repair

Do not alter accepted D1/D2 semantics to repair this finding. Repair only the
derived dependency representation unless a fresh audit exposes an actual kernel
defect.

1. Add the missing direct edges above.
2. Re-run a complete subject-by-subject **semantic** directness audit over all
   106 formal objects. Do not use “all rows present / all endpoints resolve /
   no cycle” as a completeness proxy.
3. For every local D1 scientific object that is numerically concretized by a D2
   definition, explicitly test the D2 -> D1 parent edge.
4. For every object that quantifies over another local object's domain
   (configured prefixes, evidence roles, fold domains, monitor domains,
   replay/currentness domains), test whether changing that local object changes
   the subject's denotation/domain/validity/interpretation.
5. Retain the R4 distinction that value-producing operands are not automatically
   direct prerequisites of `D2.DEF.060A`; do not solve this by densely
   connecting the graph.
6. Keep exact basis-pinned imports and omit genuinely transitive-only edges.
7. Re-run reverse-impact checks from every fixed/configurable/derived parameter
   and high-risk D1 owner, then verify acyclicity.
8. Cut a **new immutable target** after the repaired trace; do not mutate
   `86fa8ace...`.

## 6. R4-B2 — D4 executable acceptance is closed

**PASS for the reviewed D4 repair and affected target-order boundary.**

The real owner
`mdstats/training_data/target_order/coverage_reference.py::_weighted_quantiles`
at immutable R4 target has blob
`15d20eae5a7b481d636d20fc2281c743e9abe0df` and uses:

```python
indices = np.searchsorted(cumulative, requested, side="left")
```

with `cumulative[-1]` retained only for positive/finite mass validation. No
second normalization, fallback or tolerance widening is present.

The focused regression blob is
`8da42708ac601b335dfb3c9d818c302baccb1a78`; the real-owner suite blob is
`01c6d99872c136cff91777e65ce8331807f8a016`.

Primary run `35300235175` at
`dbe6c552b216d583caf9230d2c1e0879b68f8c3e` and confirmatory run
`35300268107` at
`17af93877ba312600ab1bf7a2f1f2990c9c2ef00` both completed successfully,
including the exact required commands:

```text
pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py
pytest -q tests/test_mlff_target_order_real_owner.py
```

The validation workflows used Python 3.11 and the supported CPU MLFF stack,
including CPU PyTorch, `mace-torch==0.3.16`, ASE, pytest and Hypothesis.
Earlier missing-`torch`, missing-`torch_ema` and missing-`hypothesis`
probes are correctly classified as incomplete-environment evidence rather than
product passes.

Applicability to immutable R4 is current: the D4 owner, focused regression and
real-owner suite blobs are byte-identical across both passing evidence commits
and target `86fa8ace...`. Changes after the evidence commits are limited to
the temporary workflow and review/workplan documentation; the temporary
workflow is absent from the immutable target.

Independent binary64 reconstruction also reproduces all four committed
discriminators:

```text
(2,6),   q=.25: direct 0, old residual-rescaled 1
(50,1),  q=.01: direct 0, old residual-rescaled 1
(1,6),   q=.75: direct 4, old residual-rescaled 3
(1,150), q=.99: direct 148, old residual-rescaled 147
```

R3-B2 is therefore closed.

## 7. Renderer, parameterization and prior blockers

Renderer repair: **PASS**.

The scoped target-order D2 renderer commit changes raw cardinality
`\#\{...\}` to explicit set cardinality and replaces the nested named mean
with the algebraically identical explicit finite sums/cardinalities. Direct
inspection finds no `\operatorname` or raw escaped-hash cardinality form on
the reviewed candidate surfaces.

Parameter binding remains aligned with accepted authority: target-order
`0.95`, extents `0.01/0.99`, normalization count, numerical tolerances,
Huber thresholds/factors, P5 coefficients, corpus order and monitor
cardinality/seed remain fixed coordinates; ladders/seeds/epsilon remain
configured families; replay mode, CV K and role thresholds retain their
specified configurable/default semantics.

Prior blocker disposition:

- R1 B1-B6, B8-B9: **CLOSED**.
- R1 B7 definition/source trace: **NOT FULLY CLOSED** because R4-B1 remains.
- R2 B1-B4: **CLOSED**.
- R3-B1 trace completeness: **NOT CLOSED**.
- R3-B2 D4 executable acceptance: **CLOSED**.

## 8. Lifecycle disposition

The immutable R4 target
`86fa8acec3cfc84584bfbd380163545d80de7a27` remains **NO-PASS** and must not be
ratified or promoted.

The active workplan remains `REVIEW_NO_PASS_REOPENED`.

The next review requires a new immutable target containing a semantically
complete direct dependency trace. Because the D1/D2 kernels and D4 repair need
not change for this blocker, still-applicable D4 evidence may be reused if its
owner/test/environment applicability remains byte-for-byte valid and the new
target introduces no executable changes.

Fresh review must again inspect the assembled candidate and must not inherit
this record's conclusion.
