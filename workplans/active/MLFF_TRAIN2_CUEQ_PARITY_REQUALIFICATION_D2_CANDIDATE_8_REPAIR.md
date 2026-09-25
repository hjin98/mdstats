---
kind: D2-candidate-repair-record
protocol_version: 6.4.0
status: FROZEN_PENDING_FRESH_INDEPENDENT_REVIEW
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R4.md
superseded_candidate: 499b1269590db7c8636b32e6c2dd5cebb05ac602
replacement_candidate_file: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_8.md
immutable_candidate_commit: c6e18ccfce62d47e96dde80600558522c62c28ef
immutable_candidate_blob: 60598fa33048df16f9cc41e6adf761dd952aa28f
date: 2026-09-25
---

# Candidate-8 D2 repair record

Candidate 8 repairs the five blocking findings of independent Review R4 without modifying Candidate 7 and without using any Candidate-7 Stage-C outcome.

## R4-B1 — unsupported p_max=0.60 derivation

Removed.

Candidate 8 no longer derives a noninferiority slack from Gamma or confidence.

\(\eta_{\rm NI}\) is an explicit stakeholder-ratified method coordinate with no default. It is part of the exact qualification key and cannot be selected from Candidate outcomes.

The admissible family satisfies \(0\le\eta_{\rm NI}\le q_{\rm cat}<0.10\).

## R4-B2 — fixed launch-order cycle versus binomial inference

The fixed six-permutation cycle is removed.

Each triplet independently samples one of the six R1/R2/C child-launch permutations uniformly from a dedicated qualification-only RNG namespace. That RNG cannot affect scientific child state.

Production-internal arithmetic order remains bound in the exact backend/kernel key.

The intended binomial population is therefore the i.i.d. uniform nuisance mixture, not six hidden fixed strata.

## R4-B3 — continuous reference adequacy and rare candidate tails

Candidate 8 defines a source-owned consumer materiality relation \(\mathcal R_e\) for every governed continuous consumer.

If no accepted owner supplies such a relation, the role fails closed.

Reference and candidate each have one joint materiality-failure Bernoulli event. Qualification requires zero observed events and an exact one-sided population upper bound no larger than stakeholder-ratified \(q_{\rm cat}<0.10\).

A sample maximum no longer owns catastrophic-tail semantics.

Raw parameter-state ULP magnitude is removed as a scientific-materiality claim; Candidate 8 chooses the complete-actual-consumer closure route allowed by Review R3.

## R4-B4 — RMS dimensional dilution

Block RMS is removed.

The broad-displacement score is

\[
S_{\Sigma}=\sum_i U_d(a_i,b_i)
\]

over the canonical atomic consumer trace, accumulated as an exact integer.

Unchanged coordinates add zero and cannot dilute it. Tensor/block split or merge cannot change it.

\(S_{\max}\) remains the rare-coordinate companion.

## R4-B5 — projection coefficient self-allowance

The observed production coefficient error is no longer placed on the allowed side of its own inequality.

The oracle derives exact semantic \(A^\ast\) independently from accepted representation equations and certifies the correctly rounded production-dtype matrix \(A_d^\ast\).

Production must satisfy exact bit-pattern equality

\[
\widehat A=A_d^\ast
\]

before output error is considered.

The output budget contains only learned-dtype accumulation error plus independently certified coefficient-rounding error.

Non-unique, rank-deficient, ill-conditioned, or uncertifiable transforms fail closed.

## Preserved closures

Candidate 8 preserves:

- exact-realization scope;
- complete accepted TRAIN2 horizon;
- accepted P5 loader/replay/head/drop semantics;
- same-backend restart only;
- no cross-backend TRAIN2 restart;
- source/DATA6 e3nn narrowing;
- FP64 CuEq TRAIN2 fail-closed;
- exact signed-zero ULP rank;
- complete structural portable-state inventory including ordinary attributes such as avg_num_neighbors;
- semantic-owner independence of the projection oracle;
- exact scientific-decision preservation;
- e3nn EVAL2 identity after projection; and
- routine doctor as currentness/reachability only.

No Stage-C evidence was run or used in this repair.
