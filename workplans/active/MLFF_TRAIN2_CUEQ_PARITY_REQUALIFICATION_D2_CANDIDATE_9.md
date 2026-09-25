---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-9
date: 2026-09-25
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_candidate: c6e18ccfce62d47e96dde80600558522c62c28ef
superseded_candidate_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R5.md
human_ratification_required: true
---

# Proposed D2 consumer-closed acceleration-equivalence overlay for MACE e3nn / CuEq TRAIN2 — Candidate 9

## 1. Lifecycle, authority, and repair scope

Candidate 9 is the semantic repair of independent Review R5 NO-PASS for immutable Candidate 8.

Candidate 8 remains immutable historical proposed authority. Candidate 9 does not reinterpret or mutate Candidate 8 and uses no Candidate-8 Stage-C result; none exists.

The accepted D1/D2 parent remains exactly:

- accepted D1/D2 kernel: \`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2\`;
- exact accepted D1/D2 source: \`a4824d28775164aa942fd29fa97ee0957eb87e6f\`.

Candidate 9 preserves every Candidate-8 repair that Review R5 passed and changes only the stochastic design/null semantics that R5 blocked:

1. the qualification design now separates the **prospective randomization/renewal policy** from its realized assignment sequence;
2. every measured triplet begins from one prospectively declared renewal/start-state contract before any child label is assigned;
3. the pre-assignment nuisance state \(\Lambda_p\) is frozen before assignment and must be an independent draw from one common renewal law across triplets;
4. \(R1/R2/C\) labels are then assigned independently and uniformly to the three launch slots;
5. the backend-equivalence null is label-exchange invariance before assignment, so the strict-worse symmetry is proved only after marginalizing over the uniform assignment law and is never asserted conditional on a realized permutation;
6. the exact Binomial/Clopper-Pearson model is retained only when the common independent renewal law is established; Candidate 9 defines no looser fallback estimator; and
7. warm-up, child failure, infrastructure failure, discard, redraw, and retry semantics are prospective and cannot select favorable evidence.

Candidate 9 remains a parameterized D2 method family. Two risk coordinates and the prospective evidence cardinality have no default and MUST be explicitly bound by stakeholder ratification of the exact Candidate-9 method instance before Stage C:

- \(\eta_{\rm NI}\): allowed excess marginal strict-worse probability above the exact-exchangeability baseline;
- \(q_{\rm cat}\): allowed fresh-renewal-process probability of a joint source-defined materiality violation; and
- \(n\): prospective triplet count.

Finite executable bindings satisfy

\[
0\le \eta_{\rm NI}\le q_{\rm cat}<0.10,
\qquad
q_{\rm cat}>0.
\]

The strict \(q_{\rm cat}<0.10\) ceiling remains only a falsification constraint: a method instance may not target a risk budget as loose as the Review-R3 adversary whose reference method has materially bad continuous excursions with probability \(0.10\). It is not a claim that any value near \(0.10\) is desirable. The exact lower risk budget is a stakeholder decision.

Candidate 9 remains proposed until fresh independent Review PASS and exact stakeholder ratification. A PASS does not accept CuEq, does not create Stage-C evidence, and does not authorize D3/D4.

## 2. Exact realization and protected consequence

### D2.CUEQ9.DEF.001 — authorizing realization key

An authorizing TRAIN2 relation is keyed by

\[
A=(d,\theta_0,q_0,D,E,O,H,K,\rho,m,R),
\]

where:

- \(d\) is the learned-model dtype;
- \(\theta_0\) and \(q_0\) identify the exact authenticated initial model and mutable training state;
- \(D\) is the exact authenticated target/replay corpus plus accepted loader, sampler, shuffle, batch, drop-last, seed, and head layout;
- \(E\) is the exact role-specific downstream consumer population and reduction identity that the completed TRAIN2 product is authorized to feed;
- \(O\) is the exact accepted objective/head/property-mask identity;
- \(H\) is the exact optimizer-update horizon plus checkpoint/monitor schedule;
- \(K=(K_R,K_C)\) is the exact ordered reference/candidate backend-kernel pair, with \(K_R\) the accepted e3nn realization and \(K_C\) the proposed pure-CuEq realization;
- \(\rho\) binds the common runtime/hardware context plus every arithmetic-relevant backend-specific runtime, determinism, TF32/matmul, library, device, construction, execution, and production-start coordinate needed to interpret \(K_R,K_C\);
- \(m\) is immutable Candidate-9 method identity; and
- \(R=(\eta_{\rm NI},q_{\rm cat},n,\mathcal Q)\) is the ratified qualification-risk/evidence-design tuple.

\(\mathcal Q\) is the **prospective design-policy identity**, not a realized random seed or permutation sequence. It binds:

1. the exact renewal/start-state contract \(\mathcal W\);
2. the exact uniform assignment law on the six permutations of \(R1,R2,C\);
3. the design-entropy/precommitment rule;
4. fixed label-blind prewarm behavior, if any; and
5. terminal child/infrastructure-failure and no-retry semantics.

\(\eta_{\rm NI}\), \(q_{\rm cat}\), and \(n\) have no default. They must be bound before Stage C and cannot be selected from Candidate outcomes.

Candidate 9 fixes simultaneous confidence target

\[
\kappa=0.95.
\]

There are four population statements: two systematic-shift score families, one joint reference-materiality event, and one joint candidate-materiality event. Each receives

\[
\alpha=\frac{1-\kappa}{4}=0.0125.
\]

The predeclared \(n\) must satisfy at least

\[
1-\alpha^{1/n}\le q_{\rm cat},
\]

so zero observed joint materiality events can support the ratified population-risk ceiling. Equivalently,

\[
n\ge
\left\lceil
\frac{\log\alpha}{\log(1-q_{\rm cat})}
\right\rceil.
\]

Larger \(n\) is allowed only if fixed before Candidate-9 execution for an explicit evidence-budget/power reason; outcome-selected sample-size increase is forbidden.

A qualification applies only to its exact bound key. Another corpus, scientific seed, horizon, objective, initial state, topology, consumer population, runtime, device class, backend/kernel pair, renewal/start-state policy, risk tuple, or material arithmetic state is another key.

The realized design seed/entropy commitment and realized permutation sequence are **evidence-realization identity** under \(\mathcal Q\), not semantic method coordinates. A different realized sequence does not create a new method key and therefore cannot be used to reset a failed same-key qualification.

The production realization authorized by a passing record must satisfy the exact production-start predicates bound in \(\rho\) that make it a member of the fresh-process population generated by \(\mathcal W\). A launch outside that start-state envelope is another key and is not authorized.

\(E\) is observation-only for backend qualification. Held-out labels or metrics cannot feed training, checkpoint choice, target membership, early stopping, or another accepted upstream scientific decision.

### D2.CUEQ9.DEF.002 — chosen closure path: exact downstream consumer population

Candidate 9 chooses the second repair route permitted by Review R3: it binds and observes the complete actual downstream continuous-consumer population for the exact qualified role rather than claiming raw stochastic equality of every parameter coordinate.

The protected TRAIN2 consequence contains:

1. exact loader/example/head/property-mask exposure;
2. finite optimizer-consumed objective execution;
3. exact structural identity of the complete portable forward-affecting live and EMA state at every required state boundary;
4. exact governed scheduler/counter/checkpoint events;
5. every role-effective continuous monitor/replay-retention/checkpoint quantity actually consumed by the role;
6. the completed portable state supplied to completed-state projection;
7. continuous portable-e3nn consumer quantities and reductions on exact \(E\), including an explicit completed-state evaluation after the final optimizer/EMA mutation; and
8. every governed discrete scientific decision derived from those quantities.

Raw portable parameter/state ULP magnitude is not a standalone scientific-materiality claim in Candidate 9. Complete state is structurally protected by inventory/projection identity; numerical adequacy is owned by the complete actual consumer consequence \(E\).

Therefore a final hidden coordinate defect that can affect the qualified EVAL2/monitor/publication use is activated by the completed-state \(E\) evaluation and cannot escape merely because no later TRAIN2 batch consumes it.

A future consumer outside exact \(E\) is not authorized by this qualification. Generic open-ended publication/reuse outside the bound consumer population requires separate qualification or a separately accepted broader D2 relation.

Candidate 9 does not claim cross-parameterization equality of latent optimizer moments. A hidden optimizer difference that affects a later state inside \(H\) is exercised by the complete horizon; one that never affects any governed consequence inside \(H\) and cannot affect exact \(E\) is outside this bounded claim.

## 3. Exact accepted execution semantics

### D2.CUEQ9.DEF.003 — common numerical inputs

Reference e3nn and candidate CuEq trajectories begin from identical upstream-owned semantic numerical inputs. Backend-native representations may differ only through the explicitly bound K pair:

- architecture/head topology and authenticated initial model;
- target/replay lineage and label mode;
- target and replay elemental-reference state where applicable;
- objective coefficients, robust-loss parameters, masks, and availability;
- optimizer, learning-rate, scheduler, and EMA configuration;
- exact corpus membership and replay-first/target-second layout for multihead replay;
- loader seed, native shuffle/sampler, batch size, and drop_last;
- accepted preprocessing;
- exact epoch/update horizon; and
- every other upstream value that can alter the accepted training operator.

Backend-specific representation layout and kernels may differ only where Candidate 9 explicitly treats them as the deliberate acceleration coordinate.

### D2.CUEQ9.DEF.004 — complete accepted loader

Qualification executes the real accepted TRAIN2 loader and every optimizer update it realizes.

For current multihead replay foundation P5, the authenticated pre-shuffle corpus is replay/pt_head first and target second, then native accepted shuffle/sampler behavior is applied with drop_last=true and no balancing sampler or intentional target duplication.

For current naive target-only foundation adaptation, accepted shuffled target-only drop_last=true semantics apply.

Candidate 9 does not import P3 target-size complete-batch drop_last=false semantics into P5.

A distributed route is outside applicability until separately accepted.

### D2.CUEQ9.DEF.005 — full horizon

If the accepted realization contains U optimizer updates, every reference and candidate trajectory executes all U updates.

There is no sampled-window, recurrence-horizon, secant, e-folding, state-anchor, or metadata-class extrapolation.

Same-backend restart/resume, when claimed, is part of A and is exercised at a predeclared boundary. A qualification for uninterrupted execution does not authorize restarted execution.

## 4. Canonical portable state

### D2.CUEQ9.DEF.006 — portable coordinate

The portable completed-state coordinate is canonical e3nn representation under the exact authenticated architecture/head/model identity.

CuEq is a transient TRAIN2 execution representation only. It never becomes EVAL2 numerical-provider identity.

Portable-state projection used for qualification is from immutable snapshots and may not mutate the live TRAIN2 source state.

### D2.CUEQ9.DEF.007 — complete forward-affecting inventory

The structural portable-state inventory is complete over every item that can influence the portable forward, including at least:

- learned parameters;
- registered floating/integer/bool buffers;
- head-local parameters/buffers and head ordering;
- elemental-reference state;
- scale/shift and normalization state;
- cutoff/radial/interaction configuration carried in state;
- forward-affecting interaction attributes including \`avg_num_neighbors\`;
- other forward-affecting ordinary module attributes;
- forward-affecting flags/configuration not serialized as tensors; and
- every additional state item proven by the pinned dependency to influence portable forward behavior.

Each inventory item has one canonical semantic identity, type/dtype, shape/domain, and source/destination owner.

Missing, duplicated, wrong-semantic, unaccounted, or quiescent-but-forward-capable state is structural failure.

Integer/bool/string/discrete inventory compares exactly.

### D2.CUEQ9.DEF.008 — state boundaries and consumer activation

The complete live inventory is authenticated at initialization and after every optimizer update. EMA inventory is authenticated after every EMA mutation and at every boundary where EMA can be consumed.

Candidate 9 does not compress raw state-value difference into an authorizing stochastic score. Instead, each state boundary at which the accepted role consumes a continuous quantity is evaluated through the portable e3nn provider, and the final completed state is always evaluated on exact \(E\) before authorization.

This makes raw storage partitioning irrelevant to numerical acceptance while preserving the final-step hidden-state closure required by Review R3.

When EMA is disabled, reference and candidate agree exactly on its absence.

## 5. Independent structural projection oracle

### D2.CUEQ9.DEF.009 — independence contract

The production CuEq-to-e3nn mapper and the structural oracle may share only:

1. the accepted mathematical architecture/representation specification;
2. immutable raw source tensor/value access; and
3. primitive arithmetic libraries whose results are themselves covered by the oracle relation.

The oracle MUST independently derive:

- complete source inventory;
- complete destination inventory;
- semantic source/destination correspondence;
- contraction-layer and k-range membership;
- reshape/permutation definitions;
- representation-basis transforms;
- every semantic floating transform coefficient; and
- exact output cardinality.

The oracle MUST NOT call, import, wrap, copy generated output from, or reuse a semantic owner from the production mapping implementation for any of those derivations.

For pinned MACE 0.3.16 the oracle cannot reuse the production converter or inverse converter, their generated mapping table, \`get_kmax_pairs\`, \`symmetric_contraction_proj\`, production key-enumeration/correspondence logic, or a production-generated projection/pseudoinverse matrix.

A separately named function sharing one of those semantic owners is correlated evidence and is not independent.

### D2.CUEQ9.DEF.010 — exact inventory reconciliation

Before numerical comparison:

- independently derived source and destination semantic identity sets must match the expected sets;
- each expected semantic item has exactly one source and one destination;
- no destination item may obtain a value from an unproved fallback;
- exact-copy/reshape/permutation items satisfy exact value preservation after the declared structural operation; and
- every forward-affecting non-tensor item is compared exactly or independently reconstructed from authenticated architecture state.

Inventory failure cannot be rescued by evaluator agreement.

### D2.CUEQ9.DEF.011 — semantic transform ownership and coefficient qualification

For each nontrivial linear representation transform, let

\[
y=A^\ast x
\]

denote the exact semantic map defined by the accepted representation mathematics: \(A^\ast\) is the unique linear map on the active authenticated coefficient subspace that makes the source and destination basis functions represent the same polynomial/forward contribution for all admissible inputs.

This definition is independent of any production converter, \`numpy.linalg.pinv\`, generated projection matrix, or converter helper.

The oracle must construct a certified higher-precision enclosure of \(A^\ast\) directly from the accepted e3nn/CuEq representation equations and prove existence/uniqueness on the active subspace. If the active map is non-unique, rank-deficient for the required inverse, or too ill-conditioned to certify the required rounding result, projection fails closed.

Let

\[
A_d^\ast=\operatorname{RN}_d(A^\ast)
\]

be componentwise correctly rounded IEEE representation in the actual production coefficient dtype using round-to-nearest, ties-to-even.

Let \(\widehat A\) be the actual production coefficient matrix. Before any output bound is evaluated, Candidate 9 requires exact bit-pattern equality

\[
\widehat A=A_d^\ast.
\]

Thus production coefficient construction has a prospective source-derived admissibility rule. A grossly wrong coefficient matrix cannot place its own observed coefficient error on the allowed side of the output inequality.

For the actual learned-dtype reduction of length \(n_r\), unit roundoff \(u\), and \(n_r u<1\),

\[
\gamma_{n_r}=\frac{n_r u}{1-n_r u}.
\]

With exact learned-state input \(x\) interpreted as real values, production output \(\widehat y\) must satisfy componentwise

\[
|\widehat y-A^\ast x|
\le
\gamma_{n_r}\bigl(|A_d^\ast|\,|x|\bigr)
+
|A_d^\ast-A^\ast|\,|x|.
\]

The second term is now only the independently certified coefficient-rounding error, not the full observed production coefficient error.

Actual reduction structure, accumulation dtype, fused-kernel order, coefficient dtype, operation count, rounding mode, coefficient provenance, and kernel identity are bound to the mapping identity.

Overflow, unsupported underflow/subnormal behavior, uncertified conditioning, ambiguous semantic map, or inability to prove correct coefficient rounding fails closed.

For the scalar adversary \(A^\ast=1,\widehat A=100,x=1\), coefficient qualification fails immediately because \(\widehat A\ne\operatorname{RN}_d(A^\ast)\); output agreement cannot rescue it.

## 6. Exact IEEE floating-distance primitive

### D2.CUEQ9.DEF.012 — finite rank

Candidate 9 defines the rank separately for every exact IEEE binary dtype that occurs in an authorizing consumer trace or projection comparison. CuEq TRAIN2 acceleration itself remains proposed only for learned-model binary32; accepted binary64 control/reduction quantities may nevertheless appear as binary64 consumer coordinates and are ranked in binary64, never coerced to binary32.

For one exact coordinate dtype d, let w be its storage width, s=2^(w-1) the sign mask, and b_d(x) the unsigned IEEE bit-pattern integer of finite x in exact dtype d.

Define

$$
m_d(x)=b_d(x)\ \&\ (s-1).
$$

The finite rank is

$$
r_d(x)=
\begin{cases}
0, & x=+0\ \text{or}\ x=-0,\\
+m_d(x), & x>0,\\
-m_d(x), & x<0.
\end{cases}
$$

For finite same-dtype a,b,

$$
U_d(a,b)=|r_d(a)-r_d(b)|.
$$

NaN or infinity is unconditional failure. Cross-dtype comparison is undefined and fails closed unless another accepted relation explicitly converts both values first.

This quotient collapses signed zero to one rank. Therefore -min-subnormal, zero, and +min-subnormal have ranks -1, 0, +1 respectively.

Required ULP fixtures include ordinary signed values, signed zero, the minimum subnormal neighbors, the subnormal/normal boundary, exponent transitions, largest finite values, exact equality, and NaN/infinity rejection.

ULP is a dimensionless numerical observation coordinate, not a physical tolerance.

## 7. Complete continuous score pair

### D2.CUEQ9.DEF.013 — source-closed consumer trace

For each exact role, construct one canonical ordered floating trace only from role-effective continuous consumer quantities whose numerical/materiality relation is source-available from accepted parent authority.

The trace includes, as applicable:

1. continuous monitor quantities actually consumed by checkpoint/admissibility/retention logic;
2. exact role-effective EVAL2/outer-evaluation reductions;
3. any publication/selection continuous quantity actually consumed by the bound role; and
4. completed-state \(E\) consumer quantities required to close the final-state consequence.

A raw parameter/state coordinate is not inserted into this trace merely because it exists.

A continuous quantity with no accepted materiality/equivalence/decision-geometry relation is not assigned a new tolerance by Candidate 9. The corresponding role is unqualifiable until its owning authority supplies one or the role is narrowed so the quantity is not a governed consumer.

For a pair of realizations, convert each same-dtype floating coordinate difference to exact ULP distance \(z_i\) using D2.CUEQ9.DEF.012.

The ordered trace identity and cardinality are bound before outcomes.

### D2.CUEQ9.DEF.014 — rare and broad discrepancy scores without dimensional dilution

Define

\[
S_{\max}=\max_i z_i
\]

and

\[
S_{\Sigma}=\sum_i z_i,
\]

where the sum is accumulated as an exact integer of sufficient range.

\(S_{\max}\) protects a rare large coordinate.

\(S_{\Sigma}\) protects broad low-amplitude displacement. It is deliberately **not divided by trace cardinality**. Adding unchanged coordinates contributes zero and therefore cannot dilute a changed subset. Splitting or merging storage tensors cannot change \(S_{\Sigma}\) because the score is over the canonical atomic consumer trace, not serialization blocks.

The two score families are

\[
j\in\{\max,\Sigma\}.
\]

Scientific/material adequacy is not inferred from these ULP scores alone; it is enforced independently by D2.CUEQ9.DEF.017-019.

## 8. Independent triplet design

### D2.CUEQ9.DEF.015 — pre-assignment renewal state and qualification-only label randomization

The independent experimental unit is one replicate triplet \(p\).

Each measured triplet contains three freshly constructed OS-process trajectories under the same exact scientific key:

- \(R1_p\): accepted e3nn;
- \(R2_p\): accepted e3nn;
- \(C_p\): pure CuEq.

No child process reuses mutable model, optimizer, EMA, RNG, CUDA graph, loader, calculator, allocator-owned model state, or other backend state from another child.

Before any child label is assigned, the qualification harness executes the exact prospectively bound renewal/start-state contract \(\mathcal W\) from \(\mathcal Q\). After \(\mathcal W\) completes and before any assignment draw, freeze the triplet pre-assignment nuisance state

\[
\Lambda_p.
\]

\(\Lambda_p\) contains every residual host/process coordinate not already deterministic in \(\rho\) that can affect protected numerical outputs, including where material persistent CUDA/driver/compiler state, allocator/residency state, autotuning/cache state, process-supervisor residue, filesystem/page-cache state, clock/power/thermal regime, and analogous cross-triplet state.

For Candidate-9 Binomial authorization, the renewal contract MUST establish that

\[
\Lambda_1,\ldots,\Lambda_n
\stackrel{\rm iid}{\sim}
P_\Lambda
\]

for one prospectively declared common fresh-start law \(P_\Lambda\), independently of qualification assignment entropy. A deterministic identical renewal state is the degenerate special case.

All post-assignment stochastic state capable of correlating triplets must either be regenerated independently under \(\mathcal W\) or be represented inside the pre-assignment renewal state. A shared mutable RNG stream, evolving accelerator cache/state, or other cross-triplet stochastic owner outside this model violates the Candidate-9 applicability contract.

This is a method applicability condition, not an empirical tolerance. If the target host cannot establish the common independent renewal law strongly enough for the exact qualification claim, Candidate-9 qualification fails closed. Candidate 9 defines no post-hoc stratified, Poisson-binomial, martingale, or enlarged-tolerance fallback.

After \(\Lambda_p\) is fixed, draw

\[
A_p\sim {\rm Uniform}(S_3)
\]

independently across triplets, where \(S_3\) is the six permutations assigning labels \(R1,R2,C\) to the three launch slots. The assignment draw uses only the design-entropy rule in \(\mathcal Q\). It cannot enter child scientific RNG, loader order, model initialization, optimizer state, or training arithmetic.

A design seed or entropy commitment, when used, is committed before the first governed child output is observed. It is recorded for audit but is not conditioned on as a semantic method coordinate.

A fixed label-blind prewarm may exist only inside \(\mathcal W\), must execute identically for every triplet, and cannot inspect candidate/reference scores or choose a later assignment. Adaptive warm-up is forbidden.

Child startup failure, OOM, timeout, crash, unsupported runtime, nonfinite execution, or inability to reach the authenticated renewal boundary is terminal qualification failure/inconclusive evidence according to the prospectively bound failure type; it is never a discarded Bernoulli unit. Candidate 9 defines no same-key redraw or retry-until-pass path and no reassignment after observed child behavior.

Production-internal construction/evaluation order that can change arithmetic is not randomized here; it remains bound inside \(K_R,K_C,\rho\). Another production order is another key.

### D2.CUEQ9.DEF.016 — triplet scores

For \(j\in\{\max,\Sigma\}\),

\[
S^{RR}_{p,j}=S_j(R1_p,R2_p),
\]

and

\[
S^{RC}_{p,j}=S_j(R1_p,C_p).
\]

\(R2\) and \(C\) are not asserted independent of the common anchor \(R1\), nor are they asserted exchangeable conditional on the realized assignment \(A_p\).

The realized permutation is audit evidence only. The symmetry used by Candidate 9 is the pre-assignment label-exchange theorem of D2.CUEQ9.DEF.021 after marginalizing over \(A_p\).

Under the exact renewal law and independent assignment design, separate triplets are the independent identically distributed Bernoulli units used by D2.CUEQ9.DEF.019 and D2.CUEQ9.DEF.022.

## 9. Reference adequacy

### D2.CUEQ9.DEF.017 — source-available continuous materiality relation

For every governed continuous consumer \(e\), Candidate 9 requires an exact accepted source relation

\[
\mathcal R_e(a,b)
\]

that says when two values are numerically/materially interchangeable for that consumer.

\(\mathcal R_e\) may be supplied only by:

- an accepted fixed numerical-equivalence tolerance owned by that consumer;
- exact accepted threshold/guard geometry;
- exact accepted ordering/practical-equivalence geometry; or
- another explicitly accepted parent relation with matching units, scope, and consequence.

Historical D4 tolerances, Candidate outcomes, ULP counts, sample maxima, Huber transition scales, or convenience constants cannot create \(\mathcal R_e\).

If a governed continuous consumer has no source-available \(\mathcal R_e\), Candidate-9 qualification for that role is undefined and fails closed.

For the current accepted parent, the source registry is explicit rather than inferred from implementation:

- target checkpoint/monitor force-RMSE admissibility uses accepted D2.CUEQ9 parent import D2.DEF.058 with the exact role-specific \(\tau_{CV}\) or \(\tau_{prod}\) boundary semantics;
- replay-retention admissibility uses the exact shared checkpoint constraint \(S(c)\) imported by accepted D2.DEF.057, including its authenticated true-reference replay relation;
- CV outer evaluation uses accepted D2.DEF.059 and exact \(\theta_{CV}\) boundary semantics;
- representative/checkpoint ordering uses the exact accepted target-side ranking/practical-equivalence owner imported by D2.IMP.CV / D2.IMP.MONITOR;
- exact-tie, lexicographic, and role-threshold guards retain their accepted owner semantics; and
- a reported continuous metric that is not consumed by one of these accepted relations is not silently promoted into an authorizing Candidate-9 channel.

This registry may be extended only by another already accepted parent relation; D4 behavior cannot extend it by existence.

### D2.CUEQ9.DEF.018 — decision geometry as a source relation

For an accepted scalar decision \(y\le T\) or \(y<T\), reference/candidate values must preserve the exact accepted inclusive/exclusive classification and, after any already accepted fixed guard,

\[
|y_1-y_2|
<
\min(|T-y_1|,|T-y_2|).
\]

An exactly boundary-touching self realization is inadequate for acceleration qualification.

For an accepted strict ordering of \(a,b\), both realizations must have the same strict/tie classification and

\[
|a_1-a_2|+|b_1-b_2|
<
\min(g_1,g_2),
\qquad
g_r=|a_r-b_r|.
\]

Accepted exact-tie branches remain exact. Lexicographic decisions apply this relation at the first coordinate that resolves the order after exact equality of preceding coordinates.

These are local source-derived materiality relations; they do not define generic physical tolerances for unrelated continuous quantities.

### D2.CUEQ9.DEF.019 — joint reference/candidate materiality events and population risk

For triplet \(p\), define joint reference materiality failure

\[
C^R_p=1
\]

iff any governed continuous consumer \(e\) fails \(\mathcal R_e\) between \(R1_p\) and \(R2_p\), or any required exact discrete/reference condition fails.

Define joint candidate materiality failure

\[
C^C_p=1
\]

iff any governed continuous consumer \(e\) fails \(\mathcal R_e\) between \(R1_p\) and \(C_p\), or any required exact candidate condition fails.

The joint event means severity cannot be diluted by the number of consumers: any one source-defined material failure is an event.

A child that reaches governed numerical execution and produces a nonfinite/invalid governed consequence is a materiality/failure event as required by its accepted owner. A child that cannot validly enter the governed trial at all is terminal qualification failure under D2.CUEQ9.DEF.015 and is not silently coded as zero.

Candidate 9 requires **zero** observed \(C^R_p\) and **zero** observed \(C^C_p\) over the predeclared \(n\) completed valid triplets.

Under the Candidate-9 renewal contract, each completed triplet is an independent draw from one common fresh-start law and one common assignment law. Therefore, for either event population, zero failures in \(n\) i.i.d. triplets gives the exact one-sided Clopper-Pearson upper bound

\[
Q=1-\alpha^{1/n}.
\]

The ratified method instance requires

\[
Q\le q_{\rm cat}.
\]

Thus reference continuous adequacy and candidate catastrophic-tail risk are explicit fresh-renewal-process population propositions, not sample-maximum anecdotes.

A reference method with materially bad continuous behavior at probability \(0.10\) is outside every admissible Candidate-9 instance because \(q_{\rm cat}<0.10\). A rare severe candidate event is governed by the same joint population-risk ceiling regardless of its magnitude.

## 10. Systematic-shift noninferiority relation

### D2.CUEQ9.DEF.020 — ratified noninferiority coordinate

Candidate 9 preserves Candidate 8's removal of the Candidate-7 derivation

\[
\Gamma=0.90\Rightarrow\eta=0.10\Rightarrow p_{\max}=0.60.
\]

There is no such derivation.

Instead, \(\eta_{\rm NI}\) is an explicit stakeholder-ratified D2 method coordinate with no default. Its meaning is exactly the allowed excess **marginal fresh-renewal-process strict-worse probability**, above the exact-exchangeability baseline, for the candidate consumer-score realization relative to reference self. This is a qualification-comparison probability under \(\mathcal Q\); it is not a production catastrophic-event probability and cannot substitute for \(q_{\rm cat}\).

Define

\[
p_{\max}=\frac12+\eta_{\rm NI}.
\]

The method additionally requires

\[
0\le\eta_{\rm NI}\le q_{\rm cat}<0.10.
\]

This coupling is a conservative stakeholder admissibility restriction, not a mathematical identity between the two event families. It is not inferred from confidence level, \(\Gamma\), machine epsilon, or Candidate observations.

### D2.CUEQ9.DEF.021 — strict-worse event and pre-assignment exchangeability theorem

For \(j\in\{\max,\Sigma\}\),

\[
B_{p,j}=\mathbf 1[S^{RC}_{p,j}>S^{RR}_{p,j}].
\]

Exact ties count as not worse.

Let \(\tau\) be the transposition that swaps the labels \(R2\) and \(C\) while leaving \(R1\) unchanged.

For one fixed pre-assignment nuisance state \(\Lambda_p=\lambda\), Candidate-9's exact backend-equivalence null requires **label-exchange invariance before assignment**: the joint protected-response law obtained under assignment \(a\in S_3\) is mapped by \(\tau\) to the same law under assignment \(\tau a\), with the \(R2\) and \(C\) protected responses exchanged and every \(R1\) response unchanged.

The null does **not** assert exchangeability conditional on a realized permutation.

Because

\[
\Pr(A_p=a)=\Pr(A_p=\tau a)=\frac16,
\]

pairing every assignment \(a\) with \(\tau a\) gives, after marginalizing over \(A_p\),

\[
(S^{RR}_{p,j},S^{RC}_{p,j})\mid \Lambda_p=\lambda
\overset d=
(S^{RC}_{p,j},S^{RR}_{p,j})\mid \Lambda_p=\lambda.
\]

Therefore

\[
\Pr(B_{p,j}=1\mid\Lambda_p=\lambda)
=
\Pr(S^{RR}_{p,j}>S^{RC}_{p,j}\mid\Lambda_p=\lambda)
\le \frac12,
\]

including discrete/tied distributions.

The R5 identical-backend order-only counterexample is therefore handled correctly. For deterministic launch-position nuisance \(h=(0,1,2)\) with pair score absolute difference, the fixed stratum \((R1,R2,C)\) has \(S^{RR}=1,S^{RC}=2\), so fixed-stratum exchangeability is false; over all six uniform assignments the strict-worse indicators are \((1,0,0,0,0,1)\), so the marginal strict-worse probability is \(1/3\).

Since \(\Lambda_p\) are i.i.d. from the common renewal law and assignments/post-assignment child randomness are independent under the exact design, the \(B_{p,j}\) are i.i.d. Bernoulli variables with one common marginal probability

\[
p_j=\Pr(B_{p,j}=1).
\]

Under exact exchangeability, \(p_j\le1/2\). Candidate-9 noninferiority permits the separately ratified relaxation \(p_j\le1/2+\eta_{\rm NI}\).

### D2.CUEQ9.DEF.022 — exact finite-sample confidence

Let

\[
X_j=\sum_{p=1}^{n}B_{p,j}.
\]

For each \(j\), let \(U_j\) be the exact one-sided Clopper-Pearson upper confidence bound for the Binomial\((n,p_j)\) marginal worse probability with per-statement error \(\alpha=0.0125\).

Candidate 9 requires

\[
U_j\le\frac12+\eta_{\rm NI}
\]

for both \(j=\max\) and \(j=\Sigma\).

By the four-way Bonferroni allocation in D2.CUEQ9.DEF.001, the two systematic-shift statements plus the reference/candidate materiality-risk statements hold simultaneously with confidence at least \(0.95\).

No Candidate-9 observation may alter \(\eta_{\rm NI}\), \(q_{\rm cat}\), \(n\), \(\mathcal Q\), \(\mathcal W\), score definitions, materiality relations, launch-assignment distribution, renewal rule, failure disposition, or confidence allocation.

If the common independent renewal law required by D2.CUEQ9.DEF.015 is not established, the Binomial model is unavailable and qualification fails closed. Candidate 9 does not replace it with a post-hoc alternative.

## 11. Catastrophic-tail semantics

### D2.CUEQ9.DEF.023 — observed-sample fail-fast guard

D2.CUEQ9.DEF.019 is the population catastrophic-risk authority.

In addition, every observed triplet must satisfy every source-owned \(\mathcal R_e\). Any observed materiality violation fails immediately.

No sample maximum creates or widens a tolerance.

A reference excursion cannot mint candidate authority, and an unobserved rare candidate tail is represented by the explicit \(q_{\rm cat}\) population-risk statement rather than being silently treated as impossible.

### D2.CUEQ9.DEF.024 — no tolerance from zero/reference extrema

If a source-owned relation requires exact equality, candidate and reference must satisfy exact equality.

If reference self happens to be exact in an observed score or consumer, that observation does not create a new positive tolerance.

Conversely, a large reference self excursion that remains inside a source-owned relation does not enlarge that relation; \(\mathcal R_e\) remains fixed by its accepted owner.

## 12. Exact scientific decisions

### D2.CUEQ9.DEF.025 — discrete preservation

In every triplet, R1 and C must agree exactly on every governed discrete scientific consequence reached by the qualified role, including when applicable:

- scheduler/checkpoint event identities;
- checkpoint admissibility;
- selected checkpoint identity;
- target/replay retention/admissibility classification;
- production checkpoint-quality classification;
- outer-evaluation acceptance;
- strict representative/final ordering; and
- any other accepted discrete decision consuming the protected trace.

A passing stochastic score cannot rescue a different decision.

## 13. Optimizer, EMA, and restart scope

### D2.CUEQ9.DEF.026 — latent optimizer state

Runtime authenticity continues to bind complete mutable state

\[
\Xi=(\theta,q_{\rm opt},q_{\rm ema},q_{\rm sched},q_{\rm rng},q_{\rm backend}).
\]

Candidate 9 does not require elementwise cross-basis equality of \(q_{\rm opt}\).

Every accepted optimizer action is executed through complete horizon \(H\). Every role-effective consumer boundary is observed, including a completed-state evaluation on exact \(E\). Therefore a latent optimizer difference that later changes a governed consumer consequence is authorizing evidence and cannot hide behind a finite action-probe family.

A latent optimizer difference that never changes any governed consequence inside \(H\) and cannot change exact \(E\) is outside this bounded equivalence claim.

### D2.CUEQ9.DEF.027 — no cross-backend restart

A CuEq-qualified run resumes CuEq only from authenticated CuEq state. An e3nn run resumes e3nn only from authenticated e3nn state.

No e3nn-to-CuEq or CuEq-to-e3nn TRAIN2 restart conversion is authorized.

Completed-state CuEq-to-e3nn projection occurs only after final TRAIN2 state enters the separate projection relation.

## 14. Source/DATA6 and dtype scope

### D2.CUEQ9.DEF.028 — source/DATA6

Candidate 9 does not promote any generic CuEq source/DATA6 relation.

Generated/current source-side and DATA6 execution remain e3nn unless another independently accepted D2 relation authorizes otherwise.

Historical source/DATA6 CuEq records remain evidence/history only and cannot authorize pseudolabel generation, E0/source inference, descriptor/FPS selection, or another consumer.

### D2.CUEQ9.DEF.029 — FP32 only

Binary32 pure-CuEq TRAIN2 is the only TRAIN2 acceleration member proposed here.

FP64 CuEq TRAIN2 is unsupported and fails closed.

Forward-only FP64 evidence cannot authorize a training operator.

## 15. Completed-state projection

### D2.CUEQ9.DEF.030 — projection relation

Only a completed state produced by a current Candidate-9-qualified TRAIN2 realization may enter completed-state projection.

Projection requires:

1. exact completed CuEq state authentication;
2. immutable snapshot input;
3. D2.CUEQ9.DEF.007 complete portable-forward inventory;
4. dependency-native production projection;
5. D2.CUEQ9.DEF.009-011 independent structural/coefficient oracle;
6. exact source-state non-mutation;
7. exact inventory/cardinality reconciliation;
8. projection evaluator qualification below; and
9. EVAL2 provider identity e3nn after projection.

Structural inventory/correspondence/coefficient failure is terminal. Evaluator agreement cannot rescue it.

### D2.CUEQ9.DEF.031 — projection evaluator population

Projection evaluator arithmetic is a separate stochastic relation over the exact completed state and exact role-effective EVAL2 consumer population.

Each evaluator triplet contains:

- \(R1_p\): fresh e3nn evaluation of the canonical portable reference state;
- \(R2_p\): a second fresh e3nn evaluation of that same state; and
- \(C_p\): transient-CuEq evaluation paired with the mapped-e3nn result according to the exact projection role.

Only role-effective continuous EVAL2 quantities with source-available \(\mathcal R_e\) enter authorizing consumer traces.

The evaluator uses the same Candidate-9 definitions D2.CUEQ9.DEF.015-024, with its own exact ratified \(n_{\rm eval}\) and prospective design-policy identity \(\mathcal Q_{\rm eval}\). Its \(\eta_{\rm NI}\) and \(q_{\rm cat}\) cannot be looser than the TRAIN2 method instance.

\(\mathcal Q_{\rm eval}\) has its own renewal contract, assignment law, entropy/precommitment rule, and terminal failure disposition. Realized evaluator entropy/seed and permutations are evidence-realization identity, not method-key coordinates.

The evaluator's \(R2/C\) symmetry is the same pre-assignment label-exchange theorem: it is obtained only after marginalizing the uniform assignment law and is never asserted conditional on a realized permutation.

If the evaluator cannot establish its common independent renewal law, evaluator qualification fails closed.

Evaluator qualification never substitutes for structural projection proof.

### D2.CUEQ9.DEF.032 — EVAL2 identity

After projection passes, EVAL2 executes the canonical portable e3nn provider.

Stored measurement identity names e3nn as the numerical forward. CuEq is provenance of completed TRAIN2 state, not EVAL2 provider.

## 16. Qualification record and currentness

### D2.CUEQ9.DEF.033 — authorizing record

An authorizing record binds at least:

- immutable Candidate-9 commit/blob/digest;
- exact accepted parent identities;
- exact \(A\);
- ratified \(\eta_{\rm NI},q_{\rm cat},n,\mathcal Q\);
- exact renewal/start-state contract \(\mathcal W\) and its applicability/independence justification;
- initial checkpoint/model/head;
- corpus/replay/label lineage;
- exact \(E\) consumer membership and reduction identity;
- every source owner supplying \(\mathcal R_e\);
- loader/sampler/shuffle/batch/drop-last/scientific-seed/head layout;
- objective, optimizer, EMA, scheduler, and horizon;
- MACE/Torch/CUDA/CuEq/runtime/device/kernel identities;
- determinism/TF32/matmul state;
- complete structural portable-state inventory identity;
- production mapper identity;
- independent structural-oracle identity and independence proof record;
- semantic transform source identity and certified \(A^\ast\);
- correctly rounded coefficient identity \(A_d^\ast\) and production equality proof;
- ULP rank version;
- exact design-entropy/precommitment record plus realized launch-assignment sequence as evidence-realization identity;
- exact renewal record for every triplet and any fixed label-blind prewarm record;
- every child/triplet completion or terminal-failure identity;
- every triplet identity and \(S^{RR}/S^{RC}\) score pair;
- \(X_{\max},X_{\Sigma}\), exact Clopper-Pearson bounds, and pass/fail;
- joint reference/candidate materiality-event traces and zero-event population bounds;
- exact scientific-decision traces;
- same-backend restart mode/boundary when claimed; and
- completed-state projection/evaluator identities when applicable.

A material change in any bound semantic coordinate stales the record.

A different realized randomization sequence under the same \(\mathcal Q\) is a different evidence realization, not a different method key. Candidate 9 defines no procedure that can discard a failed or aborted same-key realization and keep rerunning random assignments until one passes. Any future multi-attempt aggregation rule would be a new D2 method.

Candidate 8 and earlier evidence cannot authorize Candidate 9. Stage-A evidence remains method-design evidence only.

## 17. Routine doctor

### D2.CUEQ9.DEF.034 — cheap currentness/reachability witness

Routine doctor may only:

1. authenticate an exact current accepted Candidate-9 qualification record applicable to the requested realization; and
2. execute a cheap real finite forward/backward reachability witness under the requested current state.

Routine doctor cannot estimate or change the ratified risk tuple, triplet count, score definitions, source-owned materiality relations, projection bounds, or oracle identities; authorize another key; retry until pass; revive stale Candidate-8/Candidate-7/Candidate-6/Rev86 evidence; authorize source/DATA6 CuEq; or authorize a mid-run backend switch.

## 18. Candidate-9 Stage-C obligations

Fresh Stage-C evidence may begin only after:

1. immutable Candidate 9 receives fresh independent D2 Review PASS; and
2. the stakeholder ratifies the exact Candidate-9 method instance, including \(\eta_{\rm NI},q_{\rm cat},n,\mathcal Q,\mathcal W\), exact \(E\), and the exact consumer/materiality source set.

Stage C must then realize, at minimum:

1. MH-1 / omat_pbe FP32 exact qualification key;
2. MPA-0-medium / default FP32 exact qualification key;
3. complete accepted TRAIN2 horizon for every valid triplet child;
4. the predeclared \(n\) triplets under the exact renewal/start-state contract \(\mathcal W\);
5. evidence that \(\mathcal W\) establishes one common independent pre-assignment nuisance law for the exact target-host qualification population, or fail closed before Binomial authorization;
6. one design-entropy/precommitment record fixed before the first governed child output;
7. independent uniform six-permutation label assignments drawn only after each \(\Lambda_p\) is frozen;
8. exact source-owner resolution for every \(\mathcal R_e\);
9. zero observed joint reference materiality failures;
10. zero observed joint candidate materiality failures;
11. exact population upper bounds no larger than ratified \(q_{\rm cat}\);
12. \(S_{\max}\) and exact-integer \(S_{\Sigma}\) collection over the canonical consumer trace;
13. exact Clopper-Pearson systematic-shift bounds no larger than \(1/2+\eta_{\rm NI}\);
14. exact scientific-decision equality;
15. the R5 identical-backend/order-only fixture \(h=(0,1,2)\), proving that fixed-stratum conditional exchangeability is rejected while uniform pre-assignment randomization yields the correct marginal symmetry;
16. a deliberate attempt to condition the inferential theorem on the realized permutation, which must be rejected by the qualification oracle;
17. injected persistent cross-triplet host-state drift; unless the exact renewal contract removes it or restores the declared common law, qualification must fail closed;
18. child startup/OOM/timeout/crash/nonfinite and post-output infrastructure-failure fixtures proving no discard/redraw/reassignment/retry-until-pass path exists;
19. injected final-step hidden-state defect that affects an \(E\) consumer and must fail;
20. injected large decision-stable continuous reference noise outside a source-owned relation and must produce REFERENCE_METHOD_UNSTABLE;
21. injected rare severe candidate consumer violation and must count as the joint catastrophic event;
22. storage/tensor repartition with identical consumer trace and therefore identical \(S_{\Sigma}\);
23. same-backend restart/resume when claimed;
24. attempted cross-backend restart, which must fail closed;
25. stale qualification after any bound-key/risk/materiality-source/design-policy/renewal-policy change;
26. attempted FP64 CuEq TRAIN2, which must fail closed;
27. attempted source/DATA6 CuEq authorization from TRAIN2 evidence, which must fail closed;
28. projection omission/duplicate/wrong-permutation/wrong-k-range/quiescent-state injections, which must fail structurally;
29. wrong production projection coefficient including scalar \(A^\ast=1,\widehat A=100\), which must fail before evaluator comparison;
30. independently derived correctly rounded coefficient fixtures;
31. ill-conditioned/non-unique semantic transform, which must fail closed;
32. underflow/subnormal/overflow/fused-reduction adversaries for the realized projection kernel;
33. projection-evaluator execution under its own \(\mathcal Q_{\rm eval}\) and renewal law with the same pre-assignment exchangeability theorem; and
34. evaluator-agreement attempts after structural failure, which must remain failures.

No Candidate-8 or Candidate-9 outcome may be used to choose the ratified risk coordinates, consumer relation, score definition, transform definition, process count, randomization law, renewal policy, failure policy, or launch distribution.

## 19. R3/R4/R5 counterexample closure

| Counterexample | Candidate-9 treatment |
|---|---|
| final-step hidden state affects later EVAL2 consumer | completed-state exact \(E\) evaluation observes it |
| latent optimizer difference affects later update | complete horizon executes the real later update and downstream consumer |
| raw cross-basis optimizer equality demanded | explicitly not claimed |
| reference 0/M at 0.90/0.10 with material \(M\) | reference joint materiality population is inadmissible for every \(q_{\rm cat}<0.10\) instance |
| candidate constant \(M/2\) systematic shift | source materiality event and/or systematic-shift test; no sample maximum can authorize it |
| Candidate-7 \(p_{\max}=0.60\) relabeling | removed; \(\eta_{\rm NI}\) is separately ratified with no default |
| fixed six-order cycle violates binomial model | replaced by independent prospective random assignment after a common renewal/pre-assignment boundary |
| R5 fixed-stratum conditional exchangeability defect | explicitly rejected; symmetry is proved only after pairing \(a\) with the equally likely \(\tau a\) and marginalizing the assignment law |
| identical-backend order-only \(h=(0,1,2)\) adversary | fixed stratum may be worse, but six-assignment marginal strict-worse probability is \(1/3\), so exact same-backend behavior is not rejected by the false conditional theorem |
| realized randomization seed placed in semantic key | forbidden; \(\mathcal Q\) is key identity, realized entropy/assignments are evidence-realization identity |
| persistent target-host state destroys common triplet law | exact renewal/start-state contract must establish one common independent law or qualification fails closed |
| child failure discarded and redrawn | forbidden; failure disposition is prospective and no same-key retry-until-pass method exists |
| shared \(R1\) anchor | retained; no independence from the anchor is required by the pre-assignment label-swap theorem |
| continuous reference instability with stable booleans | joint source-owned continuous materiality population gate |
| rare severe candidate tail | explicit joint population-risk ceiling \(q_{\rm cat}\), not an observed maximum |
| huge unchanged tensor dilutes RMS | RMS removed; exact ULP mass \(S_{\Sigma}\) is non-dilutable by zeros |
| outcome-selected semantic block partition | no semantic block partition exists in the score |
| wrong production coefficient matrix self-authorizes | exact correctly-rounded coefficient equality fails before output bound |
| production \`pinv\` treated as semantic owner | forbidden; \(A^\ast\) comes from independent representation equations |
| non-unique reduced-CG inverse | unsupported/fails closed until an independent accepted active-subspace/canonical inverse exists |
| correlated converter/oracle helpers | forbidden as in Candidate 8 |
| \`avg_num_neighbors\` omitted | complete structural inventory failure |
| evaluator agreement rescues projection defect | explicitly impossible |
| generic publication outside \(E\) inferred | outside Candidate-9 authority |
| source/DATA6 CuEq inferred | explicitly forbidden |
| FP64 TRAIN2 inferred | explicitly forbidden |

Candidate 9 deliberately keeps the successful Candidate-8 narrowing and changes only the stochastic conditioning semantics required by Review R5.

## 20. Author-side Challenge and handoff state

Author-side falsification after the R5 repair found no remaining known D2 false-pass or exact-same-backend false-rejection route inside the declared Candidate-9 family.

The R5 defect is closed at its actual owner. Candidate 9 no longer conditions on the realized launch permutation and then invokes the randomness that was conditioned away. The qualification design instead has the exact order:

\[
\text{renew/start}
\rightarrow
\Lambda_p\ \text{frozen}
\rightarrow
A_p\sim{\rm Uniform}(S_3)
\rightarrow
\text{children execute}
\rightarrow
\text{scores/events}.
\]

The exchangeability theorem is a pre-assignment label-symmetry statement marginalized over \(A_p\). The realized assignment sequence is retained for audit/evidence but is not a semantic conditioning coordinate.

Candidate 9 deliberately does not add a second estimator for hosts that violate the renewal model. If one common independent fresh-start law cannot be established for the exact key, qualification fails closed and the D2 method must be reopened rather than switching post hoc to a stratified/Poisson-binomial/martingale rule.

The two risk quantities that cannot be derived from mathematics alone remain exposed:

- \(\eta_{\rm NI}\) is a stakeholder numerical-noninferiority risk choice;
- \(q_{\rm cat}\) is a stakeholder population materiality-risk choice.

Neither has a default, neither is inferred from \(\Gamma\), confidence, machine epsilon, or observed CuEq behavior, and both are part of the exact qualification key.

All Candidate-8 consumer closure, source-owned materiality, ULP/score, complete-state, projection-oracle, correctly-rounded coefficient, loader/restart, source/DATA6, FP64, EVAL2, and doctor restrictions remain unchanged except for Candidate-9 identity and the repaired qualification design.

No Candidate-9 Stage-C result exists.

Candidate 9 must now be frozen immutably and subjected to a genuinely fresh independent D2 Review. A fresh Review must challenge the renewal/common-law applicability condition, the pre-assignment label-swap proof, the separation of randomization-policy identity from realized assignments, failure/no-retry semantics, and verify that the previously passed Candidate-8 surfaces remain preserved.

No D2-to-D3/D4 handoff exists before independent PASS, exact stakeholder ratification, and subsequent fresh Stage-C qualification.
