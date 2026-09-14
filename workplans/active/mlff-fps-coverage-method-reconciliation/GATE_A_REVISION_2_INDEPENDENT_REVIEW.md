# Gate A Revision 2 independent D1/D2 review

Date: 2026-09-13
Reviewed candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 2
Candidate branch head before this review: `f94619411401c7a33940bea350854183e72df0a6`
Basis review: `GATE_A_INDEPENDENT_D1_D2_REVIEW.md`
Protocol: SSDP 6.3
Disposition: **NO PASS FOR PROMOTION**

## 1. Challenge disposition

Revision 2 materially improves the candidate. The previous B1/B4/G1/G2/G4 defects are conceptually repaired: the evaluation estimand is now explicitly component-weighted; selection, training-loss influence, and evaluation measures are separated; condition anchors are classified as method feasibility rather than optional qualification; target size is explicitly configuration cardinality rather than effective sample size; and stale-descendant impact is bounded.

However, promotion remains blocked. Four authority defects remain, and the candidate's own mandatory falsification evidence has not yet been realized. These are D1/D2 issues, not D3/D4 implementation details.

## 2. Blocking findings

### R2-B1 — the claimed SRSWOR evaluation design is not actually SRSWOR

Revision 2 states that `pi_eval` is a deterministic realization of simple random sampling without replacement (SRSWOR), then assigns each M3 frame a priority hash from:

```text
fixed policy seed
condition_id
geometry_fingerprint
```

with `kappa` only as a tie-break.

This does not realize uniform frame-cluster SRSWOR for two independent reasons.

1. **The seed is fixed, not randomly drawn.** A fixed deterministic priority rule has no design-randomization distribution from which a design-based sampling standard error follows. It can be described as a deterministic pseudo-random ordering, but not as an actual probability sample unless the randomization variable is itself sampled independently according to an explicit design and then frozen.
2. **Geometry duplicates share the same priority.** Two distinct M3 frame occurrences with equal `(condition_id, geometry_fingerprint)` receive the same primary priority and are then ordered adjacent by `kappa`. Even if the seed were genuinely randomized, this clusters duplicates and is not a uniform random permutation of M3 frame occurrences.

Therefore the finite-population ratio-estimator standard error in Section 3.10 does not have the claimed design-based interpretation.

**Required repair:** choose one coherent evaluation design:

- **Probability-sampling route:** define a genuine campaign-level randomization seed drawn independently of scientific data at experiment initialization, persist it as immutable design authority, and construct a pseudorandom priority from the **unique frame occurrence key** (for example keyed HMAC-SHA256 over `kappa`, or another explicitly defined uniform-permutation mechanism). Then state the precise randomization/PRF assumption under which prefixes realize SRSWOR and retain the finite-population uncertainty route; or
- **Deterministic-design route:** retain a deterministic hash/quasi-random order but remove SRSWOR/design-based standard-error claims and define deterministic balance/discrepancy adequacy instead.

Do not combine deterministic geometry clustering with probability-sampling inference.

### R2-B2 — training-support priority is still soft at the `P_train/M3` boundary

Revision 2 says training support has priority and every nonempty condition **remaining in P_train** gets a representative anchor. The split objective minimizes additive condition depletion:

```text
sum_c selected_count(c) / U_size_count(c)
```

but does not impose a hard condition-preservation constraint before allocation.

Minimal counterexample: `U_size` contains a scientifically declared condition represented by one indivisible protected component. If exact `M3` cardinality is reachable only by allocating that component to M3, the proposed algorithm may remove the condition entirely. The later anchor invariant is vacuous because the condition no longer exists in P_train.

That is inconsistent with the candidate's own statement that scarce support may deliberately remain training-side and with the historical training-priority meaning unless D1 explicitly permits condition extinction.

**Required repair:** D1 must decide which support classes are training-mandatory at the split boundary. At minimum, if every neutral condition is claimed mandatory training support, exact split feasibility must require `P_train` to retain at least one complete admissible component/frame for every such condition. If exact `M3` is then unreachable, the result is scientific infeasibility rather than permission to erase the condition. If some conditions may be sacrificed, D1 must define that regime explicitly instead of letting an additive cost decide implicitly.

The additive depletion objective can remain a secondary objective among hard-feasible splits.

### R2-B3 — the split still protects condition counts but can discard the only structurally unique support

Even when every condition remains present, the additive depletion objective cannot distinguish structurally redundant from structurally unique components inside the same condition. Two exact-feasible M3 subsets with identical per-condition counts receive identical depletion cost, so component-key tie-breaking can place the only structurally unique configuration into M3 while leaving near-duplicates in P_train.

That directly conflicts with the D1 training-side claim that the target order provides frame-level structural coverage and with the historical phrase “redundant residual support”: condition redundancy alone is not structural redundancy.

Counterexample: one abundant condition has 99 nearly duplicate frames plus one distant valid structural mode. An exact M3 choice removing one duplicate and one removing the unique mode have the same condition-depletion cost. The proposed split treats them as scientifically tied even though subsequent FPS cannot recover the removed mode in P_train.

**Required repair:** either:

1. narrow D1 explicitly so “training support priority” means only neutral-condition support and accept that structurally unique support may be allocated to M3; **or**, preferably given the stated coverage purpose,
2. include a label-blind pre-split structural-redundancy objective using an authorized `U_size` geometry transform/metric. This may be a lexicographic secondary objective after hard support preservation and condition depletion, but it must be fitted on a non-circular pre-split domain and defined exactly enough to reproduce allocation.

A deterministic tie key is not a substitute for a scientific objective when the alternatives are structurally different.

### R2-B4 — D2 metric identity is still not fully reconstructible or justified

Revision 2 improves the metric substantially, but two material gaps remain.

**Family mapping is not exact.** The universal structural families are described as provider-enabled semantic families “for example pair-distance, radial-environment, ...”. The D2 method does not define the canonical mapping from every serialized `UniversalFrameStructuralDescriptor` coordinate name to exactly one metric family. Because every family receives equal total weight, regrouping one coordinate changes distances and therefore medoids/FPS membership. This mapping is numerical authority and cannot be delegated implicitly to current code naming conventions.

**The proposed floating-point tie envelope is not derived for the full transform.** `8*gamma_d` bounds a simple fixed-coordinate summation model, but the governing scores depend on quantile interpolation, median subtraction, scale division, fallback-scale selection, family normalization, and squared differences. The conditioning error of those transformations is not captured merely by `gamma_d`, especially when a scale is small but above the separate degeneracy threshold. The factor 8 is acknowledged as a proposed guard requiring falsification, not a demonstrated error envelope.

Since numerical tie classification changes membership, promotion cannot treat those choices as settled D2 authority without either a defensible bound or a simpler exact reference semantics.

**Required repair:**

- enumerate or normatively define the complete coordinate-to-family mapping rule, with no “for example” ambiguity;
- either derive an equivalence envelope that includes transform conditioning, or define one canonical scalar binary64 reference ordering and require optimized realizations to reproduce its discrete selections exactly (with slow reference recomputation for near ties if needed). Do not make an unvalidated tolerance part of accepted membership authority.

## 3. Evidence blockers

Even if R2-B1 through R2-B4 are repaired textually, Revision 2 is not yet promotable because its own Section 7 marks the following as required pre-promotion falsification and no new independent realization was committed with Revision 2:

- variable-atom-count evaluation estimator test;
- heterogeneous-error evaluation fixture;
- split alternatives with different depletion/support quality;
- real-family metric sensitivity/ablation and rare-local-structure counterexample;
- higher-precision quantile/scale/distance/tie differential tests;
- simple-reference medoid/FPS/coverage comparison;
- input/UID/column metamorphic checks;
- stale-generation rejection and dependency-bounded impact check;
- current structural-provider lineage authentication; and
- representative CPU/resource evidence.

The previous bounded fixture is explicitly stale for the revised split, metric, and evaluation semantics. It cannot serve as independent acceptance evidence for Revision 2.

## 4. Findings from the previous review

Disposition of the original findings after this re-review:

| Original finding | Revision 2 status |
| --- | --- |
| B1 frame-count evaluation vs component EVAL2 | **conceptually closed**, but replacement SRSWOR design is defective (R2-B1) |
| B2 no evaluation approximation/error semantics | **reopened through R2-B1** because probability-design premise is false as written |
| B3 split lacked scientific objective | **partially closed**, but hard-support extinction and structural redundancy remain (R2-B2/R2-B3) |
| B4 selection vs training-loss measure conflated | **closed** |
| B5 metric scope/weighting unjustified | **partially closed**, but exact family ownership and sensitivity evidence remain (R2-B4 + evidence blockers) |
| B6 numerical identity under-specified | **partially closed**, but tie envelope remains unsupported (R2-B4) |
| G1 anchor authority | **closed** |
| G2 correlation interpretation | **closed** |
| G3 repackaging sensitivity | **closed enough for proposed scope** |
| G4 stale impact map | **closed at D1/D2 abstraction level** |

## 5. Promotion decision

**NO PASS. Do not promote Revision 2 into the permanent D1/D2 method papers.**

The next repair should be narrow:

1. make the evaluation design either genuinely randomized SRSWOR over unique frame occurrences or explicitly deterministic with no design-based inference;
2. make training-critical support a hard split-feasibility condition rather than only a depletion preference;
3. decide whether structurally unique support must be protected at the split boundary and, if yes, define one pre-split label-blind redundancy objective;
4. close exact metric-family mapping and replace/justify the proposed floating-point tie envelope;
5. realize the candidate's own required falsification evidence on the repaired revision.

The strong parts of Revision 2 should remain unchanged: one split/order topology, exact prefixes, separation of `mu_sel`/`mu_loss`/`mu_eval`, no label/foundation leakage into membership, no GPU prerequisite, soft/hard separation, bounded resources, and fail-closed old-generation semantics.

Human ratification remains premature until these blockers are repaired and a fresh independent review passes.