---
kind: independent-d1-d2-review
protocol_version: 6.4.0
review: R1
result: NO-PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: c9d3a9b4d8a226a7298e4e6088d3db19e98c1ea2
binding_handoff: 8afab888267415b8d4ffec3dd531874b194aa65f
---

# Independent Review R1 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.** The candidate has genuine blocking D2 semantic drift plus material Protocol-6.4 definition/source/traceability omissions. The renderer-only formula repair is accepted as mathematically equivalent. No Serious Challenge is raised against the accepted D1/D2 authority at `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`; the defects are in the proposed formalization.

The candidate remains proposed and must not be promoted or stakeholder-ratified as the Protocol-6.4 D1/D2 authority in its current form.

## 2. Review posture and evidence

This review independently reconstructed the accepted D1/D2 authority from the four current method papers at the accepted basis, checked current target-order implementation only as conformance/disambiguation evidence, inspected the candidate D1/D2 kernels and dependency trace at immutable target `c9d3a9b4...`, and treated the workplan/handoff/candidate equivalence statements as claims to falsify rather than proof.

Protocol 6.4 requires formal-first definition closure, explicit family/instance/default semantics, exact owner/source availability, and direct material `USES_DEFINITION` traceability. The workplan additionally requires the candidate kernels to be complete and lossless over the bounded MLFF D1/D2 authority family.

## 3. Blocking findings

### B1 — D2 weighted quantiles renormalize the stored binary64 weight vector twice

Accepted scoped D2 defines family witness weights by normalizing the binary64 vector **once** by its binary64 sum and storing those normalized values. Weighted quantiles then consume those already-normalized weights directly.

Candidate `D2.DEF.004` performs the accepted one-time normalization, but `D2.DEF.005` says to normalize the weights again by their binary64 sum before the cumulative comparison. That is not generally numerically equivalent.

A concrete binary64 counterexample exists with two represented correlation units containing 37 and 2 witnesses. Before the accepted one-time normalization the binary64 preweight sum is `0.9999999999999999`; after it, the stored weight sum is `1.0000000000000002`. In stable witness order, the once-normalized cumulative mass after witness index 36 is `0.5000000000000006`, so `Q(0.5)` selects index 36. Renormalizing the stored vector a second time moves that cumulative value to `0.4999999999999995`, so the candidate selects index 37.

This can alter robust scales, extent quantiles, local radii, adjacency, coverage, REPAIR2/MVQUAL evidence, and ultimately `pi_train`. This is direct numerical-method drift.

**Required repair:** `D2.DEF.005` must consume the canonical stored normalized weights from `D2.DEF.004` without a second normalization. Add an adversarial binary64 oracle covering a non-unit stored sum and require exact quantile parity with accepted D2.

### B2 — Phase-A coverage completion is not bound to the accepted `1e-14` selector tolerance

Candidate `D2.DEF.010` defines the independent hard family-qualification predicate with `C_m(S)+1e-12 >= 0.95`. Candidate `D2.DEF.021` then states that Phase A remains active while a family fails its “current coverage predicate under selector tolerance,” but does not give the exact predicate. The dependency trace points `D2.DEF.021` at `D2.DEF.010`, which makes the `1e-12` qualification predicate a plausible formal reading.

Accepted MVSEL2 uses the distinct selector rule

```text
coverage_mass < 0.95 - 1e-14
```

for Phase-A continuation. The interval between `0.95-1e-12` and `0.95-1e-14` therefore distinguishes the two methods.

**Required repair:** define the Phase-A coverage predicate explicitly as the accepted `1e-14` selector-tolerance rule and give it its own direct dependency/parameter source. Keep independent qualification (`1e-12`) and selector completion (`1e-14`) as separate numerical predicates.

### B3 — The proposed D2 kernel is not definition-closed over accepted P1/P2/P3 numerical authority

The candidate claims a complete D2 formal kernel, but material accepted algorithms are left behind opaque phrases such as “accepted D2 component-order rule” and “repeat according to the accepted funnel.” In particular it omits or fails to define:

- the exact five-step protected-component ordering used before the `M3` exact subset-sum allocation;
- the exact condition-balanced `pi_eval` construction and priority/UID ordering;
- the current P2 structural-policy domain: candidate/evaluation-size power-of-two/cardinality restrictions, three fidelity boundaries, and ordered unique nonnegative seed population;
- the minimum-three-qualified-candidates admission rule before automatic screening;
- the exact reducer funnel `q -> min(q,4) -> 2 -> 1`, boundary success-sufficiency rules, and configured-ceiling material-superiority rule;
- the accepted autocorrelation estimator/truncation, complete-frame block construction, protected-event merge, and related neutral statistical-unit numerical definitions despite D1 explicitly delegating the correlation truncation estimator to D2.

These definitions can change exact memberships, screening admission, candidate elimination, and recommendation outcomes. A formal-first entry point cannot require a reader to reverse-engineer them from the old paper while claiming complete definition closure.

**Required repair:** either formalize these accepted algorithms as first-class D2 definitions in dependency order, or explicitly scope the kernel as partial and retain exact source/section imports as normative owners. The current “complete kernel”/acceptance claim is not compatible with opaque source references.

### B4 — The exact target-order required-family catalog and applicability semantics are missing

The accepted scoped D2 authority specifies the required universal structural families, profile-selection families, raw pair-geometry families, target-development response families, and foundation-residual families together with extent-bearing/applicability rules. The candidate defines only an abstract required family `m`; the exact catalog (`pair_distance`, `radial_environment`, `coordination`, `connectivity`, `chemical_environment`, `local_density`, `angular_environment`, `orientational_order`, response/residual families, etc.) is absent.

That omission permits a materially different selector family set while still satisfying the formal kernel.

**Required repair:** formalize the accepted family catalog and conditional provider/applicability rules, or make an exact specialized import of the current scoped owner that leaves no ambiguity over which families are required in each method mode. Add corresponding direct dependency edges.

### B5 — REPAIR2 is materially incomplete

Candidate D2 formalizes shell bounds, removal eligibility, representative utility, and the global objective, but omits accepted decision semantics that can change the repaired master order:

- the exact replacement-frontier lexicographic ranking;
- per-shell limits of at most 2 passes and 32 accepted swaps;
- replacement rank inheritance and the future-rank displacement rule;
- the no-extra/unconfigured-repair-shell boundary as a numerical continuation rule.

**Required repair:** restore these accepted REPAIR2 definitions explicitly and trace their prerequisites. Add repair-trace equality oracles against the accepted scoped D2 method.

### B6 — Accepted replay scientific/numerical semantics are not losslessly represented

The D1 candidate mentions replay separation and absence of a training-head scalar but does not formalize the accepted replay label-mode family: true-reference/DFT replay as canonical default when available, foundation pseudo-label replay only by explicit opt-in, pseudo targets bound to the frozen foundation checkpoint/head, separate mandatory true-reference replay-monitor evidence, geometry/source/label lineage separation, and label-mode changes not changing replay geometry membership.

The D2 candidate formalizes corpus order/exposure and a replay-retention checkpoint conjunct, but contains no pseudo-label/true-reference label-mode definition.

**Required repair:** add the accepted D1 replay-lineage/label-mode definitions and D2 concretization, preserving default/opt-in semantics, foundation identity binding, true-monitor independence, and geometry-membership invariance. Trace them directly into P5 exposure/checkpoint constraints/currentness.

### B7 — The Protocol-6.4 definition trace is incomplete and contains unresolved/dangling prerequisites

The trace uses non-resolvable labels such as “accepted source-compatibility policy,” “accepted P1 relation providers,” “accepted role vocabulary/policy,” “configured candidate-size family,” and “shared P5 method policy” instead of exact owner/source identifiers or specialized imports. It also records `D1.DEF.007 -> D2 truncation definition`, but the D2 candidate has no such definition.

Additional source gaps include `D1.DEF.004`, whose stress derivative uses volume/strain/source conventions without tracing the accepted strain/stress convention owner, and `D1.DEF.006`/`D1.AX.003`, where `Perm(role)` is materially consumed without a formally typed operation universe/mapping or exact imported owner.

Because B3-B6 omit material formal objects entirely, their nodes and reverse-impact edges are necessarily absent too.

**Required repair:** replace generic policy/provider labels by exact current owner/source references or first-class definitions; remove every dangling prerequisite; add all missing material nodes/edges; then perform forward definition-before-use and reverse-impact traversal from each material parameter/owner.

### B8 — Parameter-family/instance/default classification is ambiguous for fixed method coordinates

The D1 ledger uses one “Current/default instance” column for semantically different classes. In particular, accepted target-order coverage `0.95`, extent quantiles `0.01/0.99`, current monitor cardinality `256`, and foundation-P5 `1:10:1` coefficients are not interchangeable with configurable policy coordinates that merely have generated defaults such as `K=3` or `tau_CV/theta_CV/tau_prod=45/45/30`.

The accepted MVSEL2 realization freezes coverage threshold `0.95`; changing it is a D1/D2 method change, not simply choosing another ordinary instance.

**Required repair:** split the ledger into explicit binding class (`fixed method coordinate`, `configurable family`, `configurable with generated default`, `derived`) plus current value/default and owner. Preserve structural constraints on the candidate ladder rather than describing it only as an arbitrary increasing configured family.

### B9 — Required Protocol-6.4/6.3 PEM/HAS interface is missing from the active workplan

This is substantial mature-project D1/D2 rework, so the project-memory trigger applies. The accepted basis contains PEM schema 1 with active success/failure families, but the workplan contains no canonical `pem_basis` + `has` block.

The review used the unchanged PEM blob published at `hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md` (same blob present at accepted basis). Session-local applicability is:

```yaml
pem_basis:
  accepted_project_state: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
  accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: formalization must preserve one canonical semantic owner instead of creating duplicated authority
  - id: SP-002
    disposition: APPLICABLE
    reason: fail-closed exact identity and state boundaries are central to D1/D2 definitions
  - id: SP-003
    disposition: APPLICABLE
    reason: immutable/content-addressed candidate and continuation identities are material
  - id: SP-004
    disposition: APPLICABLE
    reason: real-owner/current-implementation comparison is needed to falsify numerical equivalence
  - id: FF-001
    disposition: APPLICABLE
    reason: foundation checkpoint/head and realized-model identity are material to E0 and P5 authority
  - id: FF-002
    disposition: APPLICABLE
    reason: authenticated continuation/restart authority is formalized by this candidate
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: destructive storage routing is outside this D1/D2 documentation formalization
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU admission/cancellation/residency policy is outside the semantic candidate
  - id: FF-005
    disposition: APPLICABLE
    reason: formal ownership must prevent downstream reconstruction of preparation-owned scientific state
```

**Required repair:** place the canonical `pem_basis`/`has` interface in the workplan before R2 and reconcile any newer validated project overlay if one exists at the repair candidate.

## 4. Non-blocking / passed checks

### Renderer repair — PASS

The scoped D2 hard-gain rewrite from raw `#` cardinality to `|set|` is exact. The sparse-diversity rewrite explicitly defines nonempty family witness sets and expands the previous inner and outer arithmetic means as finite sums divided by cardinalities. This matches the accepted implementation's inner `mean` over witness inverse multiplicities and outer `mean` over nonempty family rows. No tolerance, rank, tie, or decision semantics changed.

The candidate D1/D2 files contain no remaining unsupported `operatorname` macro or raw `\#` cardinality syntax in the reviewed formulas.

### D1/D2 authority challenge — no Serious Challenge

The accepted authority reviewed here is sufficiently coherent to serve as the correction oracle. The review found no evidence requiring reopening accepted D1/D2 scientific meaning. Repairs belong to the proposed Protocol-6.4 representation.

## 5. R2 acceptance conditions

A repaired candidate may return for fresh R2 only after all B1-B9 are closed. R2 must, at minimum:

1. reproduce accepted weighted quantiles under adversarial binary64 one-time-normalization cases;
2. distinguish selector `1e-14` coverage completion from MVQUAL `1e-12` qualification;
3. reconstruct exact `M3`, `pi_eval`, structural-policy admission, P3 funnel/sufficiency/ceiling, and neutral correlation/block semantics from the formal source alone or exact specialized imports;
4. reconstruct the exact target-order family catalog and REPAIR2 trace;
5. reconstruct replay label-mode/lineage semantics;
6. show a complete, source-resolvable, acyclic direct definition trace with no dangling prerequisite;
7. show explicit fixed/configurable/default binding classes;
8. include canonical PEM/HAS basis in the workplan; and
9. retain the renderer repair unchanged unless a new representation defect is found.

Any repair changes the semantic candidate identity; a new immutable target and fresh independent review are required.