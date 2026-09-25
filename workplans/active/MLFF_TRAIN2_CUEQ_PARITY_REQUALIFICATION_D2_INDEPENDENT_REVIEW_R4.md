---
kind: D2-independent-review
protocol_version: 6.4.0
status: NO_PASS
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
reviewed_candidate: 499b1269590db7c8636b32e6c2dd5cebb05ac602
reviewed_candidate_blob: d5e1c72d6cb4c35027e0f43f502f0da48819af3d
lifecycle_head_basis: 88f119ed4163b399e7696d7916a4b8a31957cf56
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
serious_challenge: false
highest_blocking_owner: D2
stage_C_state: BLOCKED
D3_D4_state: BLOCKED
date: 2026-09-25
---

# Candidate-7 fresh independent Protocol-6.4 D2 Review R4

## 1. Immutable binding and disposition

This Review targets immutable Candidate 7 exactly at:

499b1269590db7c8636b32e6c2dd5cebb05ac602

with Candidate-7 Git blob:

d5e1c72d6cb4c35027e0f43f502f0da48819af3d.

The lifecycle descendant 88f119ed4163b399e7696d7916a4b8a31957cf56 is a direct child of Candidate 7 and changes only lifecycle/handoff/workplan state. It was not substituted for Candidate 7 as the semantic Review target.

The accepted parent was reconstructed from:

- accepted D1/D2 kernel a759e81aa1b4c70c8fb513c569ddce57e99cbdb2;
- exact accepted D1/D2 source a4824d28775164aa942fd29fa97ee0957eb87e6f.

Newer proposed canonical-path method files were not treated as accepted parents.

Historical Candidate-4 Review R1, Candidate-5 Review R2, Candidate-6 Review R3, the Candidate-7 repair record, Stage-A MH-1/MPA-0/order-process analyses, the active workplan, and applicable PEM entries FF-001, FF-002, SP-002, SP-003, and SP-004 were used as falsification/evidence context only.

No Candidate-7 Stage-C artifact exists at the reviewed lifecycle head and no Candidate-7 outcome was used.

**Overall disposition: NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

Candidate 7 closes several Candidate-6 defects, but five blocking D2 defects remain in the proposed numerical relation. The earliest defective owner is the Candidate-7 D2 overlay, not accepted parent D1/D2.

Candidate 7 must remain immutable historical state. It must not proceed to Stage C and must not be handed to D3/D4. Any semantic repair is Candidate 8 or later.

## 2. Confirmed Candidate-7 closures before the blocking findings

### 2.1 Final-step portable-state observability is repaired

Review R3's two-coordinate final-step hidden-state counterexample no longer passes by invisibility alone.

Candidate 7 requires complete portable forward-affecting live state after every optimizer update, complete EMA state after every EMA mutation when active, and an explicit final observation after the last optimizer mutation before projection/EVAL2. A final b-coordinate defect therefore enters the protected trace even when no later TRAIN2 batch activates it.

This closes the specific R3 B1 observation hole, subject to the score relation itself being valid. Blocking findings B3 and B4 below show that the compression/adequacy relation over that now-complete trace remains insufficient.

### 2.2 Latent optimizer handling is correctly narrowed

Candidate 7 does not claim elementwise equality of optimizer state across parameterizations. It instead executes every accepted subsequent action through the exact horizon H and observes portable model state after every update. A latent optimizer difference that affects a later model state inside H becomes observable.

A latent optimizer difference that never affects a governed consequence before H ends is outside the cross-backend equivalence claim. Same-backend restart remains separately authenticated and cross-backend restart remains forbidden.

This is a legitimate D2 narrowing and does not require invalid cross-basis optimizer equality.

### 2.3 Complete portable inventory language closes the known ordinary-attribute class

D2.CUEQ7.DEF.007 is broader than state_dict. It includes parameters, registered buffers, heads/order, elemental references, scale/shift/normalization state, architecture/cutoff state, forward-affecting interaction attributes, avg_num_neighbors, other ordinary attributes, flags/configuration, and a catch-all for every additional pinned-dependency item proven to affect portable forward behavior.

Pinned MACE 0.3.16 confirms why this is necessary: both native conversion directions explicitly copy interactions[i].avg_num_neighbors outside state_dict.

No known forward-affecting state category is normatively excluded by Candidate 7 if the independent inventory proof is actually complete.

### 2.4 Held-out leakage is prohibited at D2

E is exact-key identity and its held-out labels/metrics are observation-only for backend qualification. Candidate 7 explicitly forbids feeding them backward into training, checkpoint choice, target membership, or other upstream scientific decisions.

The separation is sound at D2. Stage-C evidence would still have to prove the realized dataflow if Candidate 7 otherwise passed.

### 2.5 Exact IEEE finite rank is correct

For binary32, Candidate 7's rank

r(x)=0 for either signed zero,
r(x)=+m(x) for x>0,
r(x)=-m(x) for x<0

is monotone over all finite numerical values and gives one signed-zero rank.

Independent fixtures verified:

- -min-subnormal, zero, +min-subnormal have ranks -1, 0, +1;
- the subnormal/normal boundary is contiguous in rank;
- ordinary negative and positive exponent transitions are monotone;
- largest finite values are finite terminal ranks;
- NaN/infinity fail closed; and
- cross-dtype comparison is undefined/fail-closed.

Thus Review R3 B3 is closed.

ULP remains a numerical lattice-distance coordinate rather than a physical materiality metric. That distinction matters in B3 below.

### 2.6 Candidate-7 projection independence closes the explicit R3 common-owner list

Candidate 7 correctly forbids an oracle that merely avoids the production mapper call while still sharing:

- get_kmax_pairs;
- symmetric_contraction_proj;
- production key enumeration/correspondence;
- a generated mapping table;
- production projection/pseudoinverse matrices; or
- another semantic inventory/correspondence owner.

Exact inventory/cardinality reconciliation also makes omission, duplicate mapping, wrong semantic identity, and quiescent-state loss structural failures before physical evaluator agreement.

This closes the explicit R3 B4 common-owner loophole. B5 below identifies a different unresolved numerical/source-closure defect in the floating transform itself.

## 3. Blocking finding B1 — the p_max = 0.60 noninferiority margin is not derived from accepted numerical or scientific semantics

Candidate 7 defines

Gamma = 0.90,
eta = 1 - Gamma = 0.10,
p_max = 1/2 + eta = 0.60.

The one-half exchangeability baseline is mathematically meaningful: for an exchangeable pair (X,Y),

P(X>Y)=P(Y>X)=(1-P(X=Y))/2 <= 1/2.

The additional 0.10 has no corresponding derivation.

Gamma=0.90 was introduced by failed Candidate 6 as a one-sided sample-maximum population-content target. It is not an accepted parent D2 constant, a scientific materiality budget, a stochastic-order distance, or a theorem connecting tolerance-content shortfall to the probability that one paired score is strictly worse than another.

Reusing 1-Gamma as sign-test noninferiority slack is therefore a change of meaning, not a derivation.

### False-pass construction

Let the candidate score be strictly worse than reference self in 0.59 of independent comparable triplets and tied/not-worse in 0.41, with every score below the tail ceiling and every exact scientific decision unchanged.

The population satisfies p_worse=0.59<0.60 and therefore satisfies Candidate 7's intended population proposition even though the candidate is more often worse than reference self than not.

Whether such a distribution is numerically interchangeable cannot be decided from the number 0.90 inherited from an unrelated content statement. A physical/materiality guard elsewhere would be capable of making this acceptable, but Candidate 7 has no such source-closed continuous guard; B3 makes that defect explicit.

### Required Candidate-8-or-later repair

Derive the candidate stochastic relation prospectively from the protected D2 consequence.

At minimum:

1. state the exact population proposition that represents numerical noninferiority/equivalence;
2. derive any nonzero worse-probability margin from accepted numerical/scientific semantics, not from Candidate outcomes and not by relabeling Gamma;
3. if no nonzero margin can be warranted, remove it rather than inventing one;
4. freeze the relation before any replacement-Candidate Stage-C outcome; and
5. apply the same repaired semantics, or a separately justified relation, to the projection evaluator.

The R3 0/M adversary must remain rejected, but rejecting that one adversary is not sufficient proof of the new population relation.

## 4. Blocking finding B2 — the fixed six-permutation schedule does not establish the i.i.d. Bernoulli model required for exact Clopper-Pearson authorization

Candidate 7 declares one triplet to be the independent unit and uses a fixed prospective cycle through all six launch permutations. This is useful counterbalancing, but it does not make the Bernoulli events identically distributed.

Stage-A evidence already demonstrated material construction/evaluation/order/process covariance. If launch/order state changes the distribution of

B_p = 1[S_RC > S_RR],

then the six schedule positions can have probabilities p_1,...,p_6.

With n=101, five permutation cells occur 17 times and one occurs 16 times. Conditional on those fixed strata, X is generally Poisson-binomial, not Binomial(101,p). Ordinary one-parameter Clopper-Pearson is therefore not an exact confidence procedure for the stated fixed-cycle experiment unless an additional theorem establishes a common p across strata.

There is also an internal ownership tension:

- if launch order is arithmetic-relevant runtime state, rho says it belongs in the exact qualification key and different orders are different keys;
- if launch order is instead a nuisance intentionally averaged over, the target population and randomization/stratification law must be defined explicitly.

A fixed deterministic cycle by itself resolves neither case.

### Shared R1 is not the defect

The common R1 anchor does not invalidate the Bernoulli event by itself.

If R2 and C are conditionally exchangeable given R1 and all nuisance state under the intended null, strict-worse probability is at most one-half even with ties. The missing step is establishing that conditional exchangeability under the actual scheduled nuisance/order design.

Fresh OS processes and no mutable reuse are necessary isolation conditions; they are not a proof that the six order strata have one common Bernoulli probability.

Candidate 7 must also distinguish the exact scientific RNG/loader seed bound inside A from any auxiliary randomization namespace used only to create independent qualification replicates. "Across triplets, seed namespaces ... are independent" is otherwise ambiguous against A's exact seed/RNG identity.

### Exact arithmetic that is nevertheless conditionally correct

For a genuine Binomial(101,p) variable and one-sided alpha_j=0.025:

- X=50 gives Clopper-Pearson upper bound 0.5963569324904932;
- X=51 gives 0.6059600394771283.

Thus the stated 50/51 arithmetic is correct.

With two families each at alpha=0.025, Bonferroni gives simultaneous confidence at least 0.95 regardless of dependence between the two family statistics, provided each per-family confidence statement is valid.

For the Review-R3 adversary p_worse=0.90, P[X<=50] under a genuine Binomial(101,0.90) is approximately 1.15e-24, so Candidate 7 would reject that adversary with overwhelming probability.

The blocker is not arithmetic; it is the unproved trial model and nuisance-population definition.

### Required Candidate-8-or-later repair

Choose one source-closed experiment/inference contract before outcomes, for example:

- bind one production order per exact key and qualify each materially distinct order separately; or
- make launch permutation an independently randomized nuisance with an exact declared distribution that is part of the population proposition; or
- retain prospective counterbalanced strata but use an exact/valid stratified or composite inference whose assumptions match those strata.

Whichever route is chosen must:

1. define independence and exchangeability at the correct level;
2. preserve fresh-process isolation;
3. separate scientific seed identity from evidence-design randomization;
4. treat warm-up/time/order nuisance prospectively; and
5. state a confidence procedure whose coverage is proved for that exact design.

## 5. Blocking finding B3 — reference adequacy controls discrete margins only, and the catastrophic-tail rule has no candidate-tail population guarantee

Review R3 required two distinct things:

1. reference e3nn self behavior must itself be numerically adequate for the protected continuous consequence; and
2. a rare reference excursion must not mint permissive candidate authority.

Candidate 7 improves the second point for systematic shifts, but its reference-adequacy gate remains limited to discrete threshold/order geometry.

### Continuous decision-stable reference counterexample

For one protected continuous score family, let every reference pair have

S_RR = M

for an arbitrarily large finite M, while all current threshold/order decisions remain far from their boundaries and therefore satisfy D2.CUEQ7.DEF.018-019.

Let every candidate pair also have

S_RC = M.

Then:

- every strict-worse event is zero because the scores tie;
- X=0 passes any p_worse ceiling;
- L=M;
- every candidate score satisfies S_RC<=L;
- exact discrete decisions agree; and
- the reference margin gate passes.

The method therefore authorizes an arbitrarily noisy continuous reference/candidate relation solely because current discrete decisions are stable.

ULP being dimensionless does not cure this. Candidate 7 itself declares complete portable state and role-effective continuous consumers to be protected consequences, not merely their final booleans.

Thus Candidate 7 has not fully closed Review R3 B2: decision geometry is a necessary reference-stability condition but is not sufficient continuous numerical adequacy.

### Rare-but-severe candidate tail counterexample

Let a reference family satisfy L=1 on the realized 101 triplets.

Let candidate cross score be:

- 0 with probability 0.999;
- 10^12 with probability 0.001.

The probability that 101 candidate triplets contain no severe event is

(0.999)^101 = 0.9038873549665952.

On those roughly 90% of qualifications, the tail rule sees no excursion at all and the strict-worse count can also be zero. Yet the candidate has an unbounded-severity rare tail.

At tail probability 0.005, the probability of missing every severe event in 101 draws is still about 0.602742.

The reference maximum has a valid reference-content statement:

1 - 0.90^101 = 0.9999760947410011

for 90% reference content, but that is not a population guarantee on candidate catastrophic-tail probability.

Even zero observed candidate exceedances in 101 would only support a nonzero upper probability bound; it cannot establish absence of an arbitrarily severe rare failure. Severity and occurrence probability must be part of the intended D2 proposition.

### Required Candidate-8-or-later repair

1. Add a source-closed continuous reference-adequacy proposition for every protected continuous family, or narrow the claim so an inadequately repeatable reference cannot authorize that family.
2. Do not derive that adequacy threshold from CuEq outcomes or from the reference sample maximum itself.
3. Define the intended catastrophic-tail population risk and severity semantics prospectively, or replace sampling authority with a structural/numerical bound that rules out the relevant catastrophic mechanism.
4. Preserve exact discrete-decision equality and threshold/order margin rules as additional hard conditions.
5. Cover accepted multi-coordinate/lexicographic/guarded decision surfaces explicitly when they are part of reference adequacy; a scalar-margin template must not silently stand in for a more complex accepted decision owner.

The current tail rule may remain as an observed-sample fail-fast guard, but it cannot be described as closing rare catastrophic candidate tails at population level.

## 6. Blocking finding B4 — one serialized state item per RMS block still permits intra-item dimensional dilution and representation-sensitive broad-shift authority

Candidate 7 repairs the Candidate-6 global RMS by defining one block per portable parameter/buffer/state item, one per loss family, and one per consumer family/reduction.

This prevents an unrelated *different* huge tensor from diluting a smaller tensor. It does not prevent dilution inside a single large state item.

### Dimensional-dilution construction

Consider one parameter tensor block with N=100,000,000 coordinates. A coherent displacement of 1 ULP in m=100 coordinates gives

S_max = 1,
R_block = sqrt(100/100000000) = 0.001.

The same 100-coordinate semantic displacement packed in a 10,000-coordinate semantic block would give R_block=0.1.

Thus the broad-shift statistic depends on tensor packing and on how much unrelated unchanged state shares one serialized item. "One parameter tensor" is an implementation storage boundary, not automatically an accepted semantic block.

The pair (maximum,RMS) also discards displacement direction. Reference self noise in one set of coordinates and a coherent candidate shift in a different sensitive subspace can have identical maximum and RMS. Exact current E consumers can detect the difference only when that subspace is active in E. Candidate 7 introduced complete state precisely to protect final/quiescent state that a finite current consumer set may not activate before publication.

Therefore the current state score is not yet source-closed enough to support the claim that block-balanced RMS protects broad low-amplitude complete-state displacement.

### Required Candidate-8-or-later repair

Before outcomes:

1. derive the semantic partition from accepted representation mathematics/forward ownership, not merely state_dict tensor packaging;
2. make the partition immutable and independently reconstructible;
3. show that no protected semantic subspace can be arbitrarily diluted by unrelated coordinates in the same block; and
4. if maximum plus RMS still cannot bound a materially sensitive direction, add a source-derived consequence/sensitivity relation or narrow the claimed state equivalence.

Do not repair this by outcome-selected block splitting or by adding arbitrary per-layer thresholds.

## 7. Blocking finding B5 — the floating projection inequality self-authorizes arbitrary coefficient error, and A* lacks an exact independent semantic owner

D2.CUEQ7.DEF.011 writes

|yhat - A* x|
<= gamma_n (|Ahat||x|)
 + |Ahat-A*||x|
 + 1/2 ulp_d(A* x).

This is a valid error-decomposition shape, but it is not an adequacy bound on production coefficients.

### Scalar false pass

Take the exact scalar semantic transform

A* = 1,
x = 1.

Let the production mapper use the completely wrong coefficient

Ahat = 100

and evaluate it accurately, so

yhat = 100.

Then

|yhat-A*x| = 99,

while the coefficient-error allowance alone is

|Ahat-A*||x| = 99.

The inequality therefore passes before adding the two other nonnegative terms.

The same triangle-inequality mechanism holds for an arbitrary wrong matrix: if production accurately evaluates Ahat x, the full observed coefficient error is placed on the permitted side of the inequality. A wrong contraction matrix can therefore pass the very relation that Stage C is required to falsify.

The structural oracle independently deriving a coefficient does not fix this because Candidate 7 never places a prospective admissible bound on |Ahat-A*|. It merely measures the error and then allows that measured error in full.

### A* source closure is also incomplete

Candidate 7 says A* is derived from "the accepted representation mathematics" but does not bind an exact normative representation-math source/identity.

Pinned MACE 0.3.16's production helper mace/tools/cg_cueq_tools.py does not provide an independent exact semantic matrix owner: symmetric_contraction_proj constructs two polynomial matrices, computes a1 @ numpy.linalg.pinv(a2), then applies round_to_sqrt_rational. Candidate 7 correctly forbids an independent oracle from reusing that production semantic owner or its generated matrix.

Therefore the Review still needs an exact owner for the mathematical map that both:

- is independent of the production converter implementation; and
- defines the semantic coefficients against which production construction error is bounded.

### Accumulation term

The gamma_n = n*u/(1-n*u) term is a standard forward-error coordinate for an appropriately modeled finite learned-dtype reduction when n*u<1.

Candidate 7 is correct to bind actual reduction structure, accumulation dtype, coefficient construction/rounding, and operation count, and to fail closed when overflow, underflow/subnormal behavior, conditioning, reduction order, or coefficient provenance assumptions cannot be established.

The blocker is that coefficient-construction error itself has no accepted magnitude bound and the exact semantic A* owner is unresolved.

### Required Candidate-8-or-later repair

1. Bind an exact, source-available mathematical owner for every nontrivial representation transform, including normalization/layout/correlation/k-range semantics.
2. Derive A* independently from that owner, not from production converter output.
3. Derive a prospective numerical bound E_A on production coefficient construction error from the actual coefficient algorithm, rounding, pseudoinverse/backward-error/conditioning semantics, and dtype.
4. Require Ahat itself to satisfy that bound. A grossly wrong coefficient/matrix must fail before output agreement can rescue it.
5. Propagate only the independently justified bound E_A through |x| in the output error budget; do not use the observed |Ahat-A*| as its own full allowance.
6. Keep exact inventory/cardinality/correspondence failure structurally dominant over evaluator agreement.
7. Exercise ill-conditioned, wrong-permutation, wrong-k-range, wrong-matrix, underflow/subnormal, overflow, and fused/reordered accumulation adversaries under the repaired relation.

## 8. Projection evaluator relation

D2.CUEQ7.DEF.031 correctly keeps evaluator arithmetic subordinate to the structural projection oracle and correctly fixes post-projection EVAL2 provider identity to e3nn.

However, it reuses D2.CUEQ7.DEF.020-024 wholesale. It therefore inherits B1-B3.

The distinct evaluator stochastic regime must be defined explicitly enough to identify:

- which e3nn evaluation is the common anchor;
- whether the reference-self and transient-CuEq/mapped-e3nn comparison use the same completed portable state;
- which launch/order/runtime nuisance variables are matched or randomized; and
- why the chosen worse-probability/tail proposition is meaningful for evaluator arithmetic.

Evaluator agreement can never rescue B5 structural/transform failure.

This does not create a sixth independent blocker because repairing B1-B3 and B5 necessarily requires rewriting the evaluator relation as well.

## 9. Remaining required falsification outcomes

### 9.1 Exact downstream consumer set E

Candidate 7's exact-key treatment of E is coherent for the role it actually qualifies. E membership/reduction identity is currentness-bearing and held-out information is prohibited from upstream use.

A later consumer outside exact E is another key or outside Candidate-7 authority. A Stage-C realization could not silently use one E population to authorize another.

No separate E-leak blocker was found in the D2 text.

### 9.2 Complete inventory/cardinality reconciliation

With a genuinely independently derived expected inventory, exact set/cardinality reconciliation detects:

- omission;
- duplicate mapping;
- wrong semantic identity;
- missing quiescent state;
- extra fallback destination state; and
- wrong k-range membership when k-range changes the expected inventory.

Wrong permutation/copy items are caught by exact structural value preservation where Candidate 7 classifies them as exact operations.

Wrong floating contraction coefficients are not safely caught because of B5.

### 9.3 Correlated-oracle attacks

An oracle that shares get_kmax_pairs, symmetric_contraction_proj, production key enumeration, state correspondence, or production-generated projection/pseudoinverse matrices violates Candidate 7 explicitly and is invalid evidence.

A subtler correlated oracle built from one common *generated* "mathematical specification" remains unsafe unless that specification is the exact independently accepted source owner. B5's source-closure repair must make this distinction explicit.

### 9.4 avg_num_neighbors and analogous ordinary state

avg_num_neighbors is explicitly covered and MACE 0.3.16 confirms it is forward-affecting ordinary state copied outside state_dict.

The catch-all in DEF.007 is adequate in form for analogous items, but Stage C would have to prove completeness from pinned source rather than infer it from converter enumeration.

### 9.5 Reference threshold/order boundaries

For the scalar decision forms they cover, DEF.018-019 are conservative and unambiguous:

- exact boundary touching is reference-inadequate;
- inclusive/exclusive accepted semantics remain with the parent owner;
- exact ties must be exact in both reference realizations;
- strict near-ties require a self-variation margin smaller than the realized gap; and
- lexicographic resolution is checked at the first resolving coordinate after exact earlier equality.

No boundary-sign error was found.

The remaining defect is B3: these rules do not establish continuous numerical adequacy where no current discrete boundary exists.

### 9.6 ULP numerical meaning

ULP is appropriate as an exact same-dtype lattice-distance observation coordinate. It is not by itself a universal scientific error metric across scales, near zero, or across differently conditioned state/consumer coordinates.

Candidate 7 acknowledges that it is not a physical tolerance. Therefore a valid method needs the independent continuous adequacy/materiality semantics missing in B3 rather than pretending ULP counts alone supply them.

### 9.7 Exact qualification key

K=(K_R,K_C) correctly binds the ordered backend/kernel pair rather than pretending backend identity is common input.

rho is broad enough in wording to require all arithmetic-relevant runtime/device/library/determinism/TF32/matmul state.

B2 must clarify whether launch order is part of rho or part of an explicitly randomized/stratified qualification population.

### 9.8 Accepted P5 loader semantics

Candidate 7 preserves the accepted current P5 loader/exposure semantics:

- replay/pretraining head first and target second before shuffle when replay is active;
- native accepted shuffle/sampler;
- no balancing sampler;
- no intentional target duplication;
- drop_last=true for current foundation-P5 training;
- target-only foundation adaptation remains target-only with its accepted shuffle/drop behavior; and
- distributed execution is not presumed equivalent without separate qualification.

No regression from the accepted parent was found here.

### 9.9 Restart scope

Same-backend restart may be qualified only under exact authenticated same-backend state/currentness.

Cross-backend TRAIN2 restart remains explicitly unsupported.

No regression remains from FF-002/accepted continuation authority.

### 9.10 Source/DATA6 and dtype scope

Generic source/DATA6 CuEq is unambiguously outside Candidate-7 authority.

FP64 CuEq TRAIN2 is explicitly unsupported/fail-closed.

These Candidate-4/5/6 scope defects remain closed.

### 9.11 Routine doctor

The routine doctor remains an authenticated currentness/reachability/finiteness witness only. It cannot estimate new tolerances, generate qualification authority, widen the key, retry until pass, or authorize backend switching.

No blocker remains here.

### 9.12 D2/D3 boundary

Candidate 7 binds concrete runtime/kernel/device facts only where they determine numerical semantics/evidence applicability. Persistence, concurrency, packaging, durable representation, and implementation decomposition remain D3/D4 responsibilities.

The OS-process language is an experimental-isolation requirement, not an authorization for D2 to own implementation architecture.

No D3/D4 patch is warranted from this Review.

## 10. Historical-regression check

Candidate 7 preserves the important improvements from R1-R3:

- no forward-inference tolerance is reused as a TRAIN2 bias budget;
- no two-update/window/recurrence extrapolation remains;
- complete accepted loader/horizon replaces metadata-only sparse windows;
- no finite optimizer-action probe is claimed injective;
- EMA is observed through complete portable state;
- source/DATA6 generic CuEq is narrowed away;
- FP64 TRAIN2 remains unsupported;
- final portable state is observed;
- signed-zero ULP rank is exact;
- projection inventory includes ordinary forward-affecting state;
- common projection semantic owners identified by R3 are prohibited;
- exact scientific-decision mismatch is never rescued by stochastic scores; and
- post-projection EVAL2 is e3nn.

No repair after Candidate 6 was found to regress those closed defects.

The new blockers arise from the replacement score/statistical/projection semantics themselves.

## 11. Required workplan state after Review R4

The workplan must remain open.

Before another fresh independent Review:

1. preserve Candidate 7 unchanged as immutable historical candidate state;
2. create Candidate 8 or later for any semantic repair;
3. close B1 by deriving, not relabeling, the systematic noninferiority population proposition and any nonzero margin;
4. close B2 by making the experimental-unit/order/randomization model match the confidence procedure exactly;
5. close B3 with continuous reference adequacy plus an explicit candidate catastrophic-tail population/structural guarantee;
6. close B4 with source-derived semantic blocks or another non-dilutable broad-shift consequence relation;
7. close B5 with exact independent A* ownership and a prospective coefficient-construction error bound that wrong matrices cannot self-authorize;
8. restate the projection evaluator under the repaired stochastic relation;
9. preserve the already-closed complete-state, ULP, scope, loader, restart, doctor, and e3nn-EVAL2 semantics unless separately falsified;
10. do not run Candidate-7 Stage C;
11. do not use any Candidate-7 outcome to choose Candidate-8 thresholds, margins, blocks, process counts, tail policy, transform bounds, or repair form; and
12. do not authorize D3/D4 until a new immutable D2 candidate passes fresh independent Review and receives exact stakeholder ratification.

## 12. Final disposition

**NO-PASS**

**SERIOUS CHALLENGE to accepted D1/D2 parent authority: NO**

Candidate 7 is not strong enough to proceed to Stage-C testing. The blocking defects remain in proposed D2 numerical authority and are repairable without reopening accepted D1.
