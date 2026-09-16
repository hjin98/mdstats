---
kind: proposed-D1-authority-overlay
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: PROPOSED_REVIEW_PASS_AWAITING_STAKEHOLDER_RATIFICATION
owner_after_ratification: docs/methods/mlff_scientific_method.md
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
---

# R1 proposed D1 authority — restored multi-view `pi_train` scientific meaning

## 1. Authority rule

This file is the consolidated proposed D1 overlay to accepted-current `docs/methods/mlff_scientific_method.md` for the MVSEL2 restoration. Independent D1/D2 review has returned **PASS**. It remains **proposed, not accepted-current authority**, until the stakeholder ratifies this exact D1/D2 pair and the canonical method papers are explicitly promoted/reconciled.

The scope is narrow: restore the scientific meaning of `pi_train`, membership admissibility, and multi-view coverage beneath the current one-`P_train` target-size method. Accepted current P1 split roles, `pi_eval/M1/M2/M3`, P3 training/evaluation/reducer method, post-selection cross-validation (CV), replay, production, threshold separation, and downstream qualification remain unchanged except for consuming the restored target memberships.

At promotion, preserve all current method-paper text not explicitly replaced or amended below.

## 2. Authority/provenance amendment

After stakeholder ratification, append a revision paragraph recording that the target-order method was reconstructed from the latest mature pre-P6 multi-view selection lineage under workplan `MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1`, independently falsified, and stakeholder-ratified. Do not rewrite the 2026-09-13/14/15 reconstruction, post-selection restoration, or threshold-separation provenance as though those earlier reviews had already covered this later target-order correction.

## 3. Replace Section 2.3 target-size design paragraph

Use:

> The target-size method uses one deterministic **candidate-independent multi-view training order**, exact nested training prefixes, one target-size evaluation ladder, common candidate-independent training preparation, paired optimizer seeds, and an explicit short-horizon comparison policy. The order is constructed from the already-frozen training population before candidate training and is designed to progressively cover the accepted scientific variation of that population while preserving hard support. Configured prefixes are independently qualified for training-set coverage/support before model training. Those membership gates are not model-accuracy gates and do not rank already-qualified sizes. The automatic screen remains diagnostic evidence that can recommend a size; the operator owns the provisional downstream design, and post-selection cross-validation evaluates that frozen design rather than feeding backward into it.

## 4. Replace Section 5.1 — pre-order target-membership evidence

### 5.1 Pre-order target-membership evidence

The exact `P_train` population is the sole target-order domain. Membership evidence is fixed before any target-size candidate training and may use only evidence belonging to `P_train` or partition-independent ancestors whose applicability to those frames is authenticated.

The restored baseline multi-view method uses these scientific evidence classes:

1. **universal structural/environment evidence** — accepted material-neutral local-structure summaries and raw pair-geometry/coordination evidence;
2. **target-development response evidence** — accepted labels and derived physical response channels of frames already assigned to `P_train`;
3. **profile selection evidence** — only when an accepted current material/profile provider explicitly supplies selection-stage features/environment classes;
4. **foundation-weakness evidence** — only when the target-size training protocol itself uses an authenticated frozen foundation checkpoint, using its pre-candidate residuals on exact `P_train`;
5. **condition, event, extent, and protected-correlation support evidence** needed to define hard membership obligations.

Using `P_train` labels to design `P_train` membership is intentional training-design evidence. It does **not** make those labels held-out validation evidence. Conversely, `M3`/`M1`/`M2` labels or predictions, target-size candidate outcomes, reducer evidence, post-selection CV, replay-monitor evidence, calibration/locked/challenge data, and downstream physical/deployment evidence may not influence `pi_train`.

Any transform, reference distribution, residual, density, local radius, or other fitted selector quantity is fitted only on its declared authorized domain. For the restored post-split order, that domain is exact `P_train`. A historical final-development or label-domain selector fit may not be reused when it contains frames outside current `P_train`.

For this target-order chain, **`TargetCoverageReference` is the sole selector-specific fitted numerical owner**. Historical DATA7 retains logical lineage/input semantics needed to authenticate the selector inputs, but it does not create a second fitted metric/scaler/principal-component/reference owner. The fitted evidence defines inputs to one target-order method; it does not create one selector per candidate size.

## 5. Replace Section 6.2 in full

### 6.2 One canonical multi-view training order

Let

$$
P_{\mathrm{train}}=\{x_1,\ldots,x_n\}
$$

be the exact training population produced by the accepted `U_size -> P_train + M3` split. The target-size method constructs exactly one deterministic permutation

$$
\pi_{\mathrm{train}}=(x_{(1)},x_{(2)},\ldots,x_{(n)})
$$

before target-size candidate training. Candidate membership is exactly

$$
T_N=\pi_{\mathrm{train}}[:N].
$$

Therefore `N_a < N_b` implies `T_{N_a} \subset T_{N_b}` with exact prefix identity. There is no independent per-`N` membership selector.

#### 6.2.1 Scientific measures

The target-order method intentionally distinguishes four measures:

- **configuration cardinality** — `N` counts selected configurations;
- **coverage reference mass** — multi-view coverage gives equal total mass to each represented P1 correlation unit within a feature family and divides that unit mass among participating frames;
- **training-loss influence** — P3 objective/property/configuration weights and masks remain separate and cannot choose membership;
- **evaluation estimand** — the accepted P3 `M1/M2/M3` target-force evaluation/reducer semantics remain separate from training-set coverage.

Correlation-balanced coverage therefore does not redefine target size as an effective-sample count.

#### 6.2.2 Required multi-view families

The restored method represents the scientific variation of `P_train` through required families covering:

- universal local structure and environment;
- pair geometry and coordination;
- target-development force/energy/thermodynamic/strain/stress response channels defined for the accepted training evidence;
- accepted profile-specific selection features when an active profile provider supplies them; and
- frozen foundation-model weakness/residual channels when the target-size method itself is foundation-based.

The exact channel catalog, missingness rules, scaling, and metric are D2-owned. A family that is inapplicable because its governing scientific provider is not part of the current protocol is absent; it is not fabricated by acquiring an unrelated provider.

#### 6.2.3 Correlation-balanced reference coverage

For each required family `m`, let `W_m` be its reference witnesses and let `mu_m` be the normalized empirical reference measure that assigns equal total mass to each represented P1 correlation unit and equal mass to participating witnesses within that unit.

Each witness has an authorized local neighborhood in the fitted family metric. For selected set `S`, define family covered mass

$$
C_m(S)=\mu_m\left(\{w\in W_m: w\text{ has at least one selected representative in its local neighborhood}\}\right).
$$

The restored hard criterion is

$$
C_m(S)\ge 0.95
$$

for every required family. No active named-family threshold override was instantiated in the coherent recovery chain; any future family-specific threshold is a new D1/D2 policy change.

For family channels designated as **extent-bearing**, coverage also requires selected support reaching both the lower 1% and upper 99% reference quantiles of the channel. This protects distributional tails that a pure local mass criterion could otherwise miss.

These are training-membership support criteria. They are not target-force accuracy thresholds and do not imply deployment adequacy.

#### 6.2.4 Canonical hard membership obligations

One canonical membership-obligation authority combines the restored automatic obligations with current explicit hard-support policy.

The restored automatic obligations require, where applicable:

- at least one selected frame from every current P2 condition represented in `P_train`;
- at least one from every P1 correlation interval/unit represented in `P_train`;
- at least one from every recognized structural-event type represented in `P_train`;
- at least one from every active profile-environment class; and
- support on both sides of every required extent-bearing channel.

Current explicitly configured hard-support obligations remain current policy and may strengthen those automatic baselines with larger minimum counts.

A **support locus** is the scientific support concept being required: its obligation kind, applicability scope/domain, relevant family identity, target selector/identity, and directional relation/side. Requirement strength is separate from locus identity. If an automatic and an explicit obligation describe the **same support locus** and project to the **same exact incidence set in current `P_train`**, they form one canonical obligation whose required minimum is the strongest accepted requirement:

$$
k_{\mathrm{canonical}}(L)=\max_{o\in L} k(o).
$$

Thus an automatic `condition=A, minimum=1` plus an explicit `condition_id=A, minimum=2` means one canonical requirement `count(A) >= 2`; it is not a contradiction and not two hard-support votes. Source-local IDs or aliases do not create additional scientific obligations.

If records presented as the same support locus disagree on their exact candidate incidence or accepted applicability/provider semantics, preparation fails closed. Different scientific loci remain distinct even when their incidence happens to overlap or be identical.

P2 `condition_id` remains the sole target-size condition identity. P1 correlation-unit identity is a separate protected-relation/provenance concept used for coverage weighting, mandatory support, and representation balance; it may not recreate a historical label-domain target-size partition.

If complete `P_train` cannot satisfy the required family/obligation policy, preparation fails as method infeasibility. Requirements are not relaxed to manufacture a target size.

#### 6.2.5 Coverage-progressive order

While any canonical hard obligation or required-family coverage criterion is unsatisfied, the order gives priority, in sequence, to:

1. reducing hard-obligation deficits;
2. advancing the least-covered required family;
3. advancing total required-family coverage;
4. balancing representation across P1 correlation units;
5. improving representative coverage utility; and
6. improving sparse diversity.

After hard requirements are satisfied, the same one order continues by representative utility, correlation balance, and sparse diversity. Exact numerical ranking/tie semantics are D2-owned.

This behavior is candidate-independent: it depends only on frozen pre-candidate selector evidence and the selected prefix accumulated by the deterministic order itself.

#### 6.2.6 Configured-shell repair without loss of nesting

The latest mature method includes deterministic repair at configured target-size shell boundaries. Repair may alter only the newly added active shell; every already-completed smaller configured prefix is immutable. A replacement is admissible only when it preserves canonical hard obligations, does not regress required-family coverage beyond D2 numerical tolerance, and strictly improves the accepted repair objective.

Repair produces one repaired master order. It is not an independent per-size selector. After the largest configured shell, the same multi-view selection method continues deterministically from the final repaired prefix until all `P_train` frames are ordered. There is no UID-only suffix and no unconfigured repair shell.

#### 6.2.7 Independent membership qualification

Every configured candidate prefix is independently qualified from authenticated primitive selector evidence. A candidate is eligible for the target-size learning experiment only when:

- the exact prefix exists;
- required training labels are usable;
- every required multi-view family passes hard mass coverage and required extents; and
- every canonical hard membership obligation passes at its effective minimum.

Because configured prefixes are nested and these predicates are positive support/coverage predicates, qualification is monotone: after a configured prefix passes, a larger configured prefix may not fail under unchanged authority. A PASS->FAIL pattern is an invariant violation.

Coverage qualification may reject an inadmissible membership, but among qualified candidates it has no ranking/tie-break authority. The current P3 target-force reducer and practical-equivalence rule remain the sole target-size comparison authority.

## 6. Preserve Section 6.3 and later target-size evaluation semantics unchanged

Current Section 6.3 already states that one independent `pi_eval` over `M3` defines nested direct `M1 subset M2 subset M3` evaluation populations. No Section-6.3 textual or semantic change is proposed. Sections 6.4–6.7 likewise remain current except that their candidate memberships now come from the restored, independently qualified `T_N` prefixes above.

## 7. Amend Section 15 falsification and reopen conditions

Add these conditions to the current list:

- `pi_train` is generated by condition-round-robin/UID fallback rather than the accepted multi-view method;
- a required coverage family, extent obligation, condition/event/profile/correlation support obligation is omitted without an accepted applicability reason;
- selector fitting uses `M3`, held-out CV, calibration/locked, candidate-outcome, or downstream evidence;
- a foundation residual used for membership comes from an unauthenticated foundation identity or frames outside exact `P_train`;
- a scratch/non-foundation protocol acquires an unrelated foundation model solely to construct `pi_train`;
- current P2 condition identity is replaced by historical label-domain/DATA5 target-size fan-out;
- same-locus automatic and explicit obligations with identical incidence are treated as independent hard-gain votes instead of one canonical strengthened requirement;
- a valid stronger explicit minimum on an identical support locus is rejected merely because it exceeds the automatic baseline;
- conflicting same-locus incidence/applicability is silently merged instead of failing closed;
- a configured prefix fails independent multi-view qualification but is admitted to target-size training;
- hard qualification changes from PASS to FAIL at a larger nested configured prefix under unchanged evidence;
- a REPAIR2 action changes an earlier configured prefix or decreases required-family coverage beyond the accepted D2 tolerance;
- ranks after the largest configured candidate are completed by UID/arbitrary fallback instead of the same multi-view method; or
- changing execution width/backend/chunking/restart state changes the scientific master order, repair trace, or qualification result.

These are D1/D2 method violations. D3/D4 may not compensate by lowering thresholds, adding rescue sizes, fabricating provider evidence, or creating a second target-order owner.

## 8. Amend Section 16 reproducibility/provenance list

Bind, as applicable:

- exact `P_train/M3` split;
- target-order evidence/provider identities and exact `P_train` fit domain;
- required multi-view family catalog, coverage-policy identity, and family reference identities;
- canonical hard-obligation authority including effective minima;
- exact sparse neighborhood/MVIDX scientific identity;
- MVSEL2 policy and complete master-order identity;
- configured-shell REPAIR2 policy, repaired prefixes, and repair-plan identity;
- independent MVQUAL evidence for every configured prefix;
- final current `TargetTrainingOrder`, exact `T_N` memberships, and unchanged independent `pi_eval/M_i` identities.

Execution-only queue/backend/timing state is not scientific provenance unless needed to interpret a qualification environment.

## 9. Amend Section 17 D1 -> D2 handoff

D2 must preserve:

1. one exact `P_train` target-order domain and one complete deterministic `pi_train`;
2. separate configuration-count, correlation-balanced coverage, training-loss, and evaluation measures;
3. the accepted required multi-view family roles and applicability conditions;
4. the uniform 0.95 hard family coverage criterion and lower-1%/upper-99% extent-support meaning;
5. one canonical automatic + explicit hard-obligation set, where support-locus identity is independent of requirement strength, identical-incidence same-locus requirements compose by strongest minimum, and true semantic/incidence conflicts fail closed;
6. current P2 condition identity and separate P1 correlation-unit identity;
7. exact candidate-independent MVSEL2 ordering semantics, deterministic tie behavior, and complete-order continuation;
8. active-shell-only repair preserving lower configured prefixes and non-regressing hard coverage/support;
9. independent MVQUAL membership qualification, monotonicity, and separation from target-size model-error ranking; and
10. the leakage boundary excluding `M3`, candidate outcomes, and downstream evidence from membership construction.

D2 may choose numerically equivalent execution algorithms only inside those semantics. D3/D4 optimization and persistence choices remain downstream.

## 10. Non-changes

This D1 proposal does **not** change:

- the accepted `U_size -> P_train + M3` scientific role split itself;
- `pi_eval`, `M1/M2/M3`, EVAL2, or the current target-force response;
- candidate sizes as a configurable current policy;
- optimizer-seed/fidelity/reducer/practical-equivalence semantics;
- post-selection CV, replay, production, or threshold separation;
- source-label compatibility policy;
- final GPU qualification deferral.

Its scientific correction is restoring what constitutes a defensible target-training membership/order and explicit membership admissibility under one multi-view support authority.
