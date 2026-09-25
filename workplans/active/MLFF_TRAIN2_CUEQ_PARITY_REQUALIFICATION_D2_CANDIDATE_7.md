---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_NOT_ACCEPTED
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate_id: MLFF-TRAIN2-CUEQ-EQUIVALENCE-D2-CANDIDATE-7
date: 2026-09-25
parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
parent_d2_exact_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
stage_a_cross_family_basis: 24734c8113dfaeaba4ae32c2bb0b80f3c0c72e82
supersedes_candidate: f3035317dcea1448c9d6d825c6f2d9f156aaec24
superseded_candidate_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R3.md
human_ratification_required: true
---

# Proposed D2 complete-state acceleration-equivalence overlay for MACE e3nn / CuEq TRAIN2 — Candidate 7

## 1. Lifecycle, authority, and repair scope

Candidate 7 is a proposed D2 overlay. Repository presence does not make it accepted authority.

It supersedes immutable Candidate 6 after fresh independent Review R3 returned NO-PASS. Candidate 6 remains historical candidate state and is not composed into Candidate 7 as authority.

Candidate 7 preserves the Candidate-6 reductions that survived independent falsification:

1. qualification is bound to an exact FP32 TRAIN2 realization;
2. every accepted TRAIN2 update is executed;
3. no recurrence extrapolation or sampled-window authorization exists;
4. no finite optimizer-action probe is treated as complete optimizer-state proof;
5. no mid-run e3nn/CuEq backend switching is authorized;
6. generic CuEq source/DATA6 execution is not proposed;
7. FP64 CuEq TRAIN2 remains unsupported and fails closed;
8. the routine doctor is not an authority-generating calibration surface; and
9. EVAL2 executes the portable e3nn provider after a qualified completed-state projection.

Candidate 7 repairs Review-R3 defects by replacing finite witness-only trajectory authority with complete portable-state observation, replacing a global sample-maximum equivalence rule with a prospective systematic-shift comparison plus a distinct tail guard, defining one exact IEEE ULP rank, and strengthening projection-oracle independence against shared semantic owners.

The accepted D1 scientific method, robust objective, replay semantics, target-size method, checkpoint rules, CV/production thresholds, and publication rules remain unchanged.

## 2. Exact realization and protected consequence

### D2.CUEQ7.DEF.001 — authorizing realization key

An authorizing TRAIN2 relation is keyed by

$$
A=(d,\theta_0,q_0,D,E,O,H,K,\rho,m),
$$

where:

- d is the learned-model dtype;
- theta_0 and q_0 identify the exact authenticated initial model and mutable training state;
- D is the exact authenticated target/replay corpus plus accepted loader, sampler, shuffle, batch, drop-last, seed, and head layout;
- E is the exact role-specific downstream continuous-consumer population and reduction identity that the completed TRAIN2 product can feed, including common-monitor and EVAL2 geometry/membership where applicable;
- O is the exact accepted objective/head/property-mask identity;
- H is the exact optimizer-update horizon plus checkpoint/monitor schedule;
- K is the resolved backend/kernel realization;
- rho is arithmetic-relevant runtime, hardware, determinism, TF32/matmul, library, and device identity; and
- m is the immutable Candidate-7 method identity.

A qualification applies only to its exact bound key. Another corpus, seed, horizon, objective, initial state, topology, consumer population, runtime, device class, backend realization, or material arithmetic state is another key.

E is observation-only for backend qualification. Its held-out labels or metrics cannot feed training, checkpoint choice, target membership, or any other accepted upstream scientific decision.

### D2.CUEQ7.DEF.002 — complete-horizon consequence

For one exact accepted TRAIN2 realization, Candidate 7 asks whether pure CuEq execution is numerically interchangeable with the accepted e3nn reference over the complete realized horizon and at the completed-state consumer boundary.

The protected consequence contains:

1. exact loader/example/head/property-mask exposure;
2. finite optimizer-consumed total and applicable per-property/per-example loss contributions;
3. the complete portable forward-affecting live-model state after initialization and after every optimizer update;
4. the complete portable forward-affecting EMA state at the same boundaries when EMA is active;
5. exact governed scheduler/counter/checkpoint events;
6. every role-effective continuous monitor quantity actually consumed by checkpoint/admissibility/retention logic;
7. the completed portable state supplied to EVAL2/publication;
8. continuous e3nn-provider predictions and reductions on exact E at every state boundary at which the accepted role consumes them; and
9. every governed discrete scientific decision derived from those quantities.

Candidate 7 does not claim cross-parameterization equality of latent optimizer moments. Optimizer state is protected by executing every subsequent accepted update inside H. A hidden optimizer difference that changes a later state is therefore observed in the complete portable state. A hidden optimizer difference that never changes any governed consequence before H ends is outside this equivalence claim.

The final state is not exempt from observation: there is always a portable-state observation after the final optimizer mutation and before completed-state projection/EVAL2 authorization.

## 3. Exact accepted execution semantics

### D2.CUEQ7.DEF.003 — common numerical inputs

Reference e3nn and candidate CuEq trajectories begin from identical upstream-owned numerical inputs:

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

Backend-specific representation layout and kernels may differ only where Candidate 7 explicitly treats them as the deliberate acceleration coordinate.

### D2.CUEQ7.DEF.004 — complete accepted loader

Qualification executes the real accepted TRAIN2 loader and every optimizer update it realizes.

For current multihead replay foundation P5, the authenticated pre-shuffle corpus is replay/pt_head first and target second, then native accepted shuffle/sampler behavior is applied with drop_last=true and no balancing sampler or intentional target duplication.

For current naive target-only foundation adaptation, accepted shuffled target-only drop_last=true semantics apply.

Candidate 7 does not import P3 target-size complete-batch drop_last=false semantics into P5.

A distributed route is outside applicability until separately accepted.

### D2.CUEQ7.DEF.005 — full horizon

If the accepted realization contains U optimizer updates, every reference and candidate trajectory executes all U updates.

There is no sampled-window, recurrence-horizon, secant, e-folding, state-anchor, or metadata-class extrapolation.

Same-backend restart/resume, when claimed, is part of A and is exercised at a predeclared boundary. A qualification for uninterrupted execution does not authorize restarted execution.

## 4. Canonical portable state

### D2.CUEQ7.DEF.006 — portable coordinate

Let P_R be identity on an e3nn reference state.

For a CuEq snapshot, P_C is the qualified dependency-native CuEq-to-e3nn semantic projection applied to an immutable snapshot. P_C may never mutate the measured training trajectory.

At every required state boundary, compare P_R(reference) and P_C(candidate) in the same portable e3nn coordinate.

### D2.CUEQ7.DEF.007 — complete forward-affecting inventory

Portable state inventory is not state_dict-only.

It contains every item that can alter portable forward execution, including:

- parameters;
- registered floating/integer/bool buffers;
- head inventory and head ordering;
- atomic-number and elemental-reference state;
- scale/shift and normalization state;
- cutoff and architecture coordinates;
- interaction-local forward-affecting attributes;
- avg_num_neighbors and any analogous ordinary module attribute used by forward execution;
- representation/correlation/irreps coordinates;
- forward-affecting flags or configuration not serialized as a tensor; and
- every additional state item proven by the pinned dependency to influence portable forward behavior.

Each inventory item has one canonical semantic identity, dtype/type, shape/domain, and source/destination owner.

Missing, duplicated, aliased-to-the-wrong-semantic, or unaccounted state is failure even when currently quiescent on all physical evaluation structures.

Pure integer/bool/string/discrete inventory compares exactly.

### D2.CUEQ7.DEF.008 — live and EMA state boundaries

The live portable state is observed at k=0 and after each optimizer update k=1,...,U.

When EMA is enabled, the complete portable EMA state is observed after every accepted EMA mutation and at every checkpoint boundary at which EMA can be consumed.

When EMA is disabled, both reference and candidate must agree exactly on its absence.

A final-step mutation that changes a portable state coordinate cannot escape observation merely because no later training batch activates that coordinate.

## 5. Independent structural projection oracle

### D2.CUEQ7.DEF.009 — independence contract

The production CuEq-to-e3nn mapper and the structural oracle may share only:

1. the accepted mathematical architecture/representation specification;
2. immutable raw source tensor/value access; and
3. primitive arithmetic libraries whose results are themselves covered by the oracle error relation.

The oracle MUST independently derive:

- complete source inventory;
- complete destination inventory;
- semantic source/destination correspondence;
- contraction-layer and k-range membership;
- reshape/permutation definitions;
- representation-basis transforms;
- every floating transform coefficient; and
- exact output cardinality.

The oracle MUST NOT call, import, wrap, copy generated output from, or reuse a semantic owner from the production mapping implementation for any of those derivations.

In particular, for pinned MACE 0.3.16 the oracle cannot reuse the production converter or inverse converter, their generated mapping table, get_kmax_pairs, symmetric_contraction_proj, production key-enumeration/correspondence logic, or a production-generated projection/pseudoinverse matrix.

A separately named function that shares one of those semantic owners is correlated evidence and is not an independent oracle.

### D2.CUEQ7.DEF.010 — exact inventory reconciliation

Before numerical comparison:

- source and destination semantic identity sets must match the independently derived expected sets;
- each expected semantic item must have exactly one source and one destination;
- no extra destination item may obtain a value from an unproved fallback;
- exact-copy/reshape/permutation items must satisfy exact value preservation after the declared structural operation; and
- every forward-affecting non-tensor item must be compared or independently reconstructed from authenticated architecture state.

Inventory failure cannot be rescued by physical-output agreement.

### D2.CUEQ7.DEF.011 — floating linear transfer

For a semantic floating transform

$$
y=A^\ast x,
$$

the oracle derives A* independently at higher precision from the accepted representation mathematics.

Let Ahat be the actual production coefficient representation and let yhat be the production learned-dtype output. For a length-n reduction in learned-model dtype with unit roundoff u and nu<1,

$$
\gamma_n=\frac{nu}{1-nu}.
$$

The production mapping passes only if, componentwise,

$$
|\widehat y-A^\ast x|
\le
\gamma_n\,\bigl(|\widehat A|\,|x|\bigr)
+
|\widehat A-A^\ast|\,|x|
+
\frac12\,\operatorname{ulp}_d(A^\ast x),
$$

with the actual reduction structure, accumulation dtype, coefficient construction, coefficient rounding, and operation count bound to mapping identity.

The second term explicitly accounts for production coefficient error; a higher-precision semantic matrix and a float32/float64 pseudoinverse are not silently treated as identical.

If overflow, underflow/subnormal behavior, condition number, reduction order, accumulation dtype, coefficient provenance, or another assumption needed by this bound cannot be established for the realized mapping, the mapping relation fails closed.

## 6. Exact IEEE floating-distance primitive

### D2.CUEQ7.DEF.012 — finite rank

Candidate 7 supports the learned-model IEEE binary dtype d explicitly bound by A. Candidate 7 currently proposes CuEq TRAIN2 only for binary32.

Let w be the storage width, s=2^(w-1) the sign mask, and b_d(x) the unsigned IEEE bit-pattern integer of finite x in exact dtype d.

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

### D2.CUEQ7.DEF.013 — protected floating trace

For one comparison of two complete realizations, construct one ordered protected floating trace from:

1. all optimizer-consumed loss contributions required by the accepted objective;
2. every floating item in the complete portable live state at every required boundary;
3. every floating item in the complete portable EMA state at every required boundary;
4. every continuous monitor/replay-retention/checkpoint quantity actually consumed by the role; and
5. every e3nn-provider prediction/reduction on exact E at the state boundary where that consumer is actually used.

The trace contains exact semantic identity and boundary identity for every component. No fixed finite geometry witness substitutes for complete portable state.

### D2.CUEQ7.DEF.014 — rare and broad discrepancy scores

For protected-component ULP distances z_i at observation boundary k, define

$$
M(k)=\max_i z_i,
$$

and, when the boundary contains at least one floating component,

$$
R(k)=\sqrt{\frac1{n_k}\sum_{i=1}^{n_k}z_i^2}.
$$

For a complete realization pair,

$$
S_{\max}=\max_k M(k),
\qquad
S_{\rm rms}=\max_k R(k).
$$

The authorizing continuous score vector is exactly

$$
S=(S_{\max},S_{\rm rms}).
$$

S_max protects rare single-coordinate errors. S_rms protects broad low-amplitude displacement. Neither can rescue failure of exact inventory or exact scientific decisions.

## 8. Independent triplet design

### D2.CUEQ7.DEF.015 — independent experimental unit

The independent experimental unit is one replicate triplet p.

Each triplet contains three freshly constructed OS-process trajectories under the same exact A:

- R1_p: accepted e3nn;
- R2_p: accepted e3nn;
- C_p: pure CuEq.

No child process reuses mutable model, optimizer, EMA, RNG, CUDA graph, or loader state from another child.

Across triplets, seed namespaces and mutable process state are independent.

Within a triplet, R1/R2/C deliberately share the exact upstream scientific key so reference-self and cross-backend discrepancies are comparable.

The six child-launch permutations are assigned prospectively in a fixed counterbalanced cycle; counts differ by at most one. Launch order is evidence-design identity and cannot be selected from outcomes.

### D2.CUEQ7.DEF.016 — triplet scores

For j in {max,rms}, define

$$
S^{RR}_{p,j}=S_j(R1_p,R2_p),
$$

and

$$
S^{RC}_{p,j}=S_j(R1_p,C_p).
$$

R2 and C are not asserted to be independent of R1; that common anchor is deliberate.

Each triplet contributes one reference-self score and one candidate cross-backend score per family.

## 9. Reference adequacy

### D2.CUEQ7.DEF.017 — reference stability

Before CuEq can be authorized, every e3nn reference pair must satisfy:

- finite complete trajectories;
- exact common-input and inventory identities;
- exact agreement of every governed discrete scientific decision;
- same-backend restart consistency when the key claims restart;
- no unsupported/missing consumer;
- and the decision-margin adequacy relation below.

Failure is REFERENCE_METHOD_UNSTABLE. It cannot widen a candidate tolerance.

### D2.CUEQ7.DEF.018 — threshold margin adequacy

For any accepted scalar decision y <= T or y < T, let y1,y2 be the two e3nn reference values and let the accepted inclusive/exclusive boundary semantics determine the valid side.

The pair must produce the same decision and satisfy

$$
|y_1-y_2|
<
\min(|T-y_1|,|T-y_2|),
$$

after any already-accepted fixed floating guard owned by that decision.

An exactly boundary-touching self realization is not margin-adequate for backend qualification even if both implementations happen to classify it the same way.

### D2.CUEQ7.DEF.019 — ordering margin adequacy

For an accepted ordering comparison of quantities a and b, the two reference realizations must have the same strict/tie classification.

For a strict order, define realized gaps g_r=|a_r-b_r|. Reference self variability must satisfy

$$
|a_1-a_2|+|b_1-b_2|
<
\min(g_1,g_2).
$$

For an accepted exact-tie branch, exact tie semantics must hold in both reference realizations; a stochastic near-tie cannot be promoted to exact equality.

For lexicographic decisions, apply this requirement at the first coordinate that actually resolves the order after exact equality of all earlier coordinates.

These conditions derive reference adequacy from the accepted decision geometry; they do not introduce a physical error tolerance.

## 10. Systematic-shift noninferiority relation

### D2.CUEQ7.DEF.020 — process-content coordinate

Retain the prospective process-content target

$$
\Gamma=0.90.
$$

Define the allowed probability-of-worse slack

$$
\eta=1-\Gamma=0.10,
$$

and the Candidate-7 systematic-shift ceiling

$$
p_{\max}=\frac12+\eta=0.60.
$$

The one-half term is the exchangeability baseline for a candidate score and a reference-self score drawn from the same score population; the additional 0.10 is the entire predeclared process-content shortfall. This is a stochastic noninferiority coordinate, not a physical tolerance and not a machine-epsilon rule.

### D2.CUEQ7.DEF.021 — worse event

For j in {max,rms}, define

$$
B_{p,j}=\mathbf 1[S^{RC}_{p,j}>S^{RR}_{p,j}].
$$

Exact ties count as not worse. Under exact exchangeability, strict-worse probability is at most one-half even for discrete/tied score distributions.

Let

$$
X_j=\sum_{p=1}^{n}B_{p,j}.
$$

### D2.CUEQ7.DEF.022 — fixed cardinality and exact confidence

Candidate 7 fixes

$$
n=101
$$

independent triplets before any Candidate-7 CuEq outcome exists.

For each j, let U_j be the one-sided Clopper-Pearson upper confidence bound for the Bernoulli worse probability with per-family error allocation

$$
\alpha_j=\frac{1-0.95}{2}=0.025.
$$

Candidate 7 requires

$$
U_j\le0.60
$$

for both j=max and j=rms.

For n=101 this is equivalent to requiring at most 50 strict-worse triplets in each score family; 50 gives an upper bound below 0.60, while 51 does not.

By Bonferroni, both population statements hold simultaneously with confidence at least 0.95.

This directly rejects the Review-R3 adversary in which reference self score is 0 with probability 0.90 and M with probability 0.10 while candidate score is M/2 in every process: the candidate is strictly worse than the reference self score in approximately 90% of matched draws, far above the 0.60 ceiling.

No Candidate-7 observation may change n, Gamma, eta, p_max, the score definitions, or the confidence allocation.

## 11. Separate catastrophic-tail guard

### D2.CUEQ7.DEF.023 — reference tail limit

For j in {max,rms}, define

$$
L_j=\max_{1\le p\le101}S^{RR}_{p,j}.
$$

The sample maximum is retained only as a catastrophic-tail guard; it is no longer the substantive backend-equivalence relation.

For one family and Gamma=0.90,

$$
\Pr[F_j(L_j)\ge0.90]\ge1-0.90^{101},
$$

which exceeds 0.99997. Its purpose is only to prevent a candidate excursion beyond every observed accepted-reference self excursion.

### D2.CUEQ7.DEF.024 — candidate tail rule

Every candidate triplet must satisfy

$$
S^{RC}_{p,j}\le L_j
$$

for both score families.

Any exceedance fails qualification. There is no outcome-selected rerun.

If L_j=0, every candidate score in that family must be exactly zero.

The tail rule cannot rescue failure of D2.CUEQ7.DEF.022. A rare reference excursion therefore cannot mint authority for a systematic candidate shift.

## 12. Exact scientific decisions

### D2.CUEQ7.DEF.025 — discrete preservation

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

### D2.CUEQ7.DEF.026 — latent optimizer state

Runtime authenticity continues to bind complete mutable state

$$
\Xi=(\theta,q_{\rm opt},q_{\rm ema},q_{\rm sched},q_{\rm rng},q_{\rm backend}).
$$

Candidate 7 does not require elementwise cross-basis equality of q_opt.

Every subsequent accepted optimizer action is executed through H, while theta is observed in the complete portable coordinate after every update. Therefore a latent optimizer difference that later changes model state is authorizing evidence and cannot hide behind a finite probe family.

### D2.CUEQ7.DEF.027 — no cross-backend restart

A CuEq-qualified run resumes CuEq from authenticated CuEq state. An e3nn run resumes e3nn from authenticated e3nn state.

No e3nn-to-CuEq or CuEq-to-e3nn TRAIN2 restart conversion is authorized.

Completed-state CuEq-to-e3nn projection occurs only after the final TRAIN2 state enters the separate projection relation.

## 14. Source/DATA6 and dtype scope

### D2.CUEQ7.DEF.028 — source/DATA6

Candidate 7 does not promote any generic CuEq source/DATA6 relation.

Generated/current source-side and DATA6 execution remain e3nn unless another independently accepted D2 relation authorizes otherwise.

Historical source/DATA6 CuEq records remain evidence/history only and cannot authorize pseudolabel generation, E0/source inference, descriptor/FPS selection, or another consumer.

### D2.CUEQ7.DEF.029 — FP32 only

Binary32 pure-CuEq TRAIN2 is the only TRAIN2 acceleration member proposed here.

FP64 CuEq TRAIN2 is unsupported and fails closed.

Forward-only FP64 evidence cannot authorize a training operator.

## 15. Completed-state projection

### D2.CUEQ7.DEF.030 — projection relation

Only a completed state produced by a current Candidate-7-qualified TRAIN2 realization may enter completed-state projection.

Projection requires:

1. exact completed CuEq state authentication;
2. immutable snapshot input;
3. D2.CUEQ7.DEF.007 complete portable-forward inventory;
4. dependency-native production projection;
5. D2.CUEQ7.DEF.009-011 independent structural oracle;
6. exact source-state non-mutation;
7. exact inventory/cardinality reconciliation;
8. projection evaluator qualification below; and
9. EVAL2 provider identity e3nn after projection.

### D2.CUEQ7.DEF.031 — projection evaluator triplets

Projection evaluator arithmetic is a separate, cheaper stochastic relation and reuses the Candidate-7 triplet method rather than a sample-maximum-only envelope.

For the exact completed state and exact E consumer geometry, each projection-evaluator triplet contains:

- two fresh e3nn evaluations of the same canonical portable reference state;
- one transient-CuEq evaluation paired with the mapped-e3nn result according to the exact projection role.

Construct S_max and S_rms over all required E/F/stress and other role-effective physical components.

Use n=101 independent evaluator triplets, D2.CUEQ7.DEF.020-024 systematic-shift and tail rules, and exact discrete-decision equality.

Evaluator qualification cannot substitute for the structural oracle.

### D2.CUEQ7.DEF.032 — EVAL2 identity

After projection passes, EVAL2 executes the canonical portable e3nn provider.

Stored measurement identity names e3nn as the numerical forward. CuEq is provenance of the completed TRAIN2 state, not the EVAL2 provider.

## 16. Qualification record and currentness

### D2.CUEQ7.DEF.033 — authorizing record

An authorizing record binds at least:

- immutable Candidate-7 commit/blob/digest;
- exact accepted parent identities;
- exact A;
- initial checkpoint/model/head;
- corpus/replay/label lineage;
- exact E consumer membership and reduction identity;
- loader/sampler/shuffle/batch/drop-last/seed/head layout;
- objective, optimizer, EMA, scheduler, and horizon;
- MACE/Torch/CUDA/CuEq/runtime/device/kernel identities;
- determinism/TF32/matmul state;
- complete portable-state inventory identity;
- production mapper identity;
- independent structural-oracle identity and independence proof record;
- ULP rank version;
- fixed 101-triplet evidence design and counterbalanced launch schedule;
- every triplet identity and S_RR/S_RC pair;
- X_max, X_rms, their exact confidence bounds, and pass/fail;
- L_max, L_rms and every tail comparison;
- reference decision-margin evidence;
- exact scientific decision traces;
- same-backend restart mode/boundary when claimed; and
- completed-state projection/evaluator identities when applicable.

A material change in any bound coordinate stales the record.

Candidate-6 and earlier evidence cannot authorize Candidate 7.

## 17. Routine doctor

### D2.CUEQ7.DEF.034 — cheap currentness/reachability witness

Routine doctor may only:

1. authenticate an exact current accepted Candidate-7 qualification record applicable to the requested realization; and
2. execute a cheap real finite forward/backward reachability witness under the requested current state.

Routine doctor cannot estimate or change p_max, Gamma, triplet count, score definitions, tail limits, projection bounds, or oracle identities; authorize another key; retry until pass; revive stale Candidate-6/Rev86 evidence; authorize source/DATA6 CuEq; or authorize a mid-run backend switch.

## 18. Candidate-7 Stage-C obligations

Fresh Stage-C evidence may begin only after Candidate 7 receives fresh independent D2 Review PASS and stakeholder ratification of the exact immutable candidate.

Stage C must realize, at minimum:

1. MH-1 / omat_pbe FP32 exact key;
2. MPA-0-medium / default FP32 exact key;
3. the complete accepted TRAIN2 horizon for every child trajectory;
4. exactly 101 independent R1/R2/C training triplets per qualified key;
5. predeclared counterbalanced six-permutation launch scheduling;
6. complete portable live-state observation at k=0 and after every optimizer update;
7. complete EMA-state observation at every accepted EMA boundary when active;
8. exact E continuous-consumer observation at every role-effective boundary;
9. exact S_max/S_rms construction;
10. exact one-sided Clopper-Pearson and family-wise 0.95 systematic-shift decision;
11. the fixed p_max=0.60 criterion and <=50-worse-count boundary;
12. catastrophic-tail guard with zero outcome-selected reruns;
13. reference threshold/order margin adequacy;
14. injected final-step hidden-state defect that affects an EVAL2-only configuration and must fail;
15. injected latent optimizer defect that changes a later update and must fail;
16. injected broad low-amplitude state shift and rare single-coordinate state shift;
17. explicit 0/M reference-mixture versus constant M/2 candidate adversary and rejection;
18. ULP signed-zero/subnormal/normal/exponent/NaN/infinity fixtures;
19. same-backend restart/resume where claimed;
20. attempted mid-run backend switching and FP64 CuEq TRAIN2, both fail closed;
21. attempted source/DATA6 authorization from TRAIN2 evidence, fail closed;
22. exact complete projection inventory including avg_num_neighbors or analogous forward-affecting non-state_dict state;
23. deliberate production/oracle shared get_kmax_pairs, symmetric_contraction_proj, key-enumeration, and projection-matrix owner attempts, all rejected as non-independent;
24. omission, duplicate, wrong permutation, wrong k-range, wrong contraction matrix, and quiescent-state-loss projection faults, all detected;
25. floating projection coefficient-error and accumulation-bound fixtures;
26. 101-triplet projection-evaluator qualification under the same systematic-shift/tail semantics; and
27. EVAL2 measurement identity e3nn after successful projection.

No Candidate-7 threshold, score family, process count, consumer set, or oracle independence rule may be changed after Candidate-7 CuEq outcomes are inspected.

## 19. Review-R3 counterexample closure

| Review-R3 issue | Candidate-7 treatment |
|---|---|
| final-step hidden state invisible to finite W | complete portable live/EMA state observed after every mutation, including final state, plus exact E consumers |
| finite W cannot protect downstream continuous EVAL2 | E is exact key material and its role-effective continuous consumer outputs are protected |
| rare reference maximum mints universal tolerance | sample maximum demoted to tail-only guard; systematic equivalence uses worse-probability relation |
| reference 0/M vs candidate M/2 | p_worse approximately 0.90 and fails p_max=0.60 |
| noisy reference silently widens tolerance | reference decision-margin adequacy can fail independently; noise cannot change p_max |
| ambiguous signed-zero ULP | exact rank r_d defined with signed-zero quotient |
| correlated inverse converter | explicit shared-semantic-owner prohibition |
| shared key/k-range/projection logic | independently derived inventories, k ranges, correspondences, matrices required |
| state_dict-only projection inventory | all forward-affecting state, including ordinary module attributes, is required |
| Candidate-6 Bonferroni wording error | no candidate zero-exceedance family claim; exact binomial worse-event inference is normative |
| FP64 inferred from forward evidence | unsupported/fail closed |
| generic source/DATA6 CuEq | not proposed |
| recurrence/window extrapolation | absent; complete horizon retained |

## 20. Author-side Challenge and handoff state

The author-side Challenge Pass found no SERIOUS CHALLENGE to accepted D1 or accepted parent D2.

Candidate 7 intentionally chooses a stricter, more expensive evidence method rather than allowing an observed failing backend to set its own tolerance. Its main cost is 101 complete R1/R2/C triplets per exact TRAIN2 qualification key. That cost is accepted at D2 candidate stage because it replaces repeated threshold-tuning cycles with a prospectively fixed falsifiable population claim; D3 may optimize execution only after acceptance without changing the method.

Candidate 7 remains proposed. It requires:

1. immutable freeze;
2. genuinely fresh independent D2 Review;
3. stakeholder ratification of the exact passing candidate;
4. fresh Stage-C qualification under the exact ratified method; and
5. only then D3/D4 handoff.

No Candidate-7 Stage-C evidence has been used to formulate this method.
