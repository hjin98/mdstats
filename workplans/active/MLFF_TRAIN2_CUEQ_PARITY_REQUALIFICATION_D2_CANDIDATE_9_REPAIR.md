---
kind: D2-candidate-repair-record
protocol_version: 6.4.0
status: CANDIDATE_9_PREFREEZE_CHALLENGE_CLOSED_AWAITING_FREEZE
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
repairs_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R5.md
superseded_candidate: c6e18ccfce62d47e96dde80600558522c62c28ef
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
date: 2026-09-25
---

# Candidate-9 D2 repair record after independent Review R5

## 1. Repair boundary

Independent Review R5 returned NO-PASS for immutable Candidate 8 solely because the stochastic theorem conditioned on the realized launch-order permutation while relying on randomization across permutations to remove that nuisance.

Candidate 8 remains immutable historical evidence. No Candidate-8 Stage-C result exists and none was used.

Candidate 9 preserves every Candidate-8 surface that R5 passed. It changes only the qualification randomization/null/conditioning and directly dependent evidence-record/evaluator text needed to close R5 B1.

## 2. Exact repair

Candidate 9:

1. replaces the key coordinate \`q_design\` with prospective design-policy identity \(\mathcal Q\);
2. makes realized design entropy/seed/permutations evidence-realization identity rather than semantic method identity;
3. introduces exact renewal/start-state contract \(\mathcal W\);
4. freezes pre-assignment nuisance state \(\Lambda_p\) before label assignment;
5. requires \(\Lambda_p\) to be i.i.d. from one common fresh-start law for the exact target-host key, otherwise qualification fails closed;
6. draws \(R1/R2/C\) assignments independently and uniformly over the six launch-slot permutations only after \(\Lambda_p\) is fixed;
7. defines the exact-equivalence null as \(R2/C\) label-exchange invariance **before** assignment;
8. proves score-pair exchangeability only after pairing assignments \(a\) and \(\tau a\) and marginalizing the assignment law;
9. explicitly forbids fixed-realized-stratum exchangeability;
10. retains exact Binomial/Clopper-Pearson inference only because the repaired renewal contract supplies common independent triplet law;
11. defines no post-hoc alternate estimator if that law is unavailable;
12. makes fixed label-blind prewarm, child failure, infrastructure failure, discard, redraw, and retry behavior prospective;
13. defines no same-key retry-until-pass path; and
14. applies the same repaired theorem to projection evaluator qualification.

## 3. R5 counterexample closure

For the R5 identical-backend, order-only fixture

\[
h=(0,1,2)
\]

with pair score equal to absolute launch-position difference, fixed stratum \((R1,R2,C)\) has

\[
S^{RR}=1,\qquad S^{RC}=2.
\]

Candidate 9 agrees that conditional exchangeability in that fixed stratum is false.

Let \(\tau\) swap \(R2\) and \(C\). The six assignments have equal probability and pair under \(a\leftrightarrow\tau a\). Their strict-worse indicators are

\[
(1,0,0,0,0,1),
\]

so the uniform-assignment marginal strict-worse probability is \(1/3\). The exact-same-backend null is therefore not rejected through the erroneous Candidate-8 fixed-stratum theorem.

## 4. Independence/currentness distinction

\(\mathcal Q\) and \(\mathcal W\) are semantic method/key coordinates.

The realized entropy commitment, seed when present, permutation sequence, renewal records, child identities, and score/event traces are evidence-realization identity. They are retained so the stochastic execution is auditable but are not conditioned on as if their realized values were the population definition.

Changing \(\mathcal Q\) or \(\mathcal W\) is a new key. Merely drawing a different random assignment sequence is not a new method key and cannot reset a failed same-key qualification.

## 5. Persistent host state

Candidate 9 does not pretend that fresh OS processes alone prove independent triplets.

The pre-assignment nuisance state explicitly covers material persistent host/device state, including CUDA/driver/compiler caches, allocator/residency, autotuning/cache state, process-supervisor residue, filesystem/page-cache state, clock/power/thermal regime, and analogous state.

The exact renewal/start-state policy must establish one common independent fresh-start law for the target-host key. If it cannot, Stage C fails closed. Candidate 9 does not add a compensating estimator.

## 6. Failure/no-retry closure

A fixed label-blind prewarm may exist only inside \(\mathcal W\).

Adaptive warm-up, outcome-dependent discarded triplets, permutation reassignment, child replacement, and retry-until-pass are forbidden.

Startup failure, OOM, timeout, crash, unsupported runtime, nonfinite execution, or failure to reach the renewal boundary remains visible terminal evidence. Candidate 9 supplies no rule that can silently remove such a trial and redraw the randomization.

## 7. Preserved Candidate-8 authority surfaces

Unchanged in substance:

- exact realization scope and complete accepted TRAIN2 horizon;
- exact \(E\) consumer closure and final completed-state evaluation;
- source-owned \(\mathcal R_e\) and zero-event catastrophic-risk semantics;
- explicit stakeholder \(\eta_{\rm NI}\), \(q_{\rm cat}\), and \(n\);
- exact ULP rank;
- \(S_{\max}\) and exact unnormalized \(S_\Sigma\);
- exact scientific-decision equality;
- complete live/EMA forward-affecting inventory;
- structural projection-oracle independence;
- independent \(A^\ast\), correct-rounding coefficient equality, and floating transfer bound;
- reduced-CG/non-unique inverse fail-closed behavior;
- same-backend restart only;
- source/DATA6 e3nn narrowing;
- FP64 CuEq TRAIN2 fail-closed behavior;
- e3nn EVAL2 provider identity; and
- non-authorizing routine doctor.

## 8. Lifecycle

Candidate 9 is proposed only.

No Candidate-9 Stage-C evidence may run before immutable freeze, fresh independent D2 Review PASS, and exact stakeholder ratification of the reviewed method instance.

No D2-to-D3/D4 handoff exists yet.

## 9. Prefreeze author-side challenge correction

A first author-side pass over the assembled Candidate-9 text found and removed a stale duplicate Candidate-8 closing tail that survived the mechanical base-copy step. The semantic candidate was not frozen before this correction.

The same pass made two clarifications explicit rather than leaving them implicit:

1. any post-assignment stochastic owner capable of correlating triplets must be regenerated independently under \(\mathcal W\) or represented in the renewal state; otherwise the i.i.d. applicability condition fails; and
2. \(\eta_{\rm NI}\) governs the qualification-comparison strict-worse probability under \(\mathcal Q\), not production catastrophic-event probability and never substitutes for \(q_{\rm cat}\).

No Candidate-9 Stage-C evidence exists.

The final prefreeze challenge also makes renewal evidence non-circular: a nonsignificant stationarity/autocorrelation test cannot establish independence. Stage C must carry an owner-based census showing each known cross-triplet mutable owner is reset/fixed, immutable in \(\rho\), or independently randomized; statistical diagnostics may only falsify that structural claim.

