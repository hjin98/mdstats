---
kind: D2-candidate-instance-risk-binding
protocol_version: 6.4.0
status: RATIFIED_PROSPECTIVE_INSTANCE_COORDINATES
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate: db2ed47e8c999cb61507803610c72c0fa7ffaaf7
candidate_blob: 7843a41172d25c231d4c589aebc0214ddec42bd1
independent_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R7.md
stakeholder_acceptance: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_STAKEHOLDER_ACCEPTANCE_C10.md
date: 2026-09-25
---

# Candidate-10 exact-instance risk binding

## 1. Binding

Under the stakeholder direction to choose an appropriate prospective value and proceed, bind the Candidate-10 Stage-C instance risk coordinates as:

\[
\eta_{\rm NI}=0.09,
\qquad
q_{\rm cat}=0.09,
\qquad
n=300.
\]

For the projection evaluator use the same noninferiority/materiality ceilings and:

\[
n_{\rm eval}=300.
\]

These are **instance coordinates**, not new Candidate-10 family defaults. Candidate 10 remains unchanged and continues to define no generated default.

## 2. Rationale independent of Candidate outcomes

The choice is made prospectively from the frozen Candidate-10 finite-sample semantics and not from any Candidate-10 realization.

Candidate 10 requires:

\[
0\le\eta_{\rm NI}\le q_{\rm cat}<0.10
\]

and allocates per-statement error:

\[
\alpha=0.0125.
\]

The 0.09 value:

1. stays strictly below the family ceiling 0.10;
2. gives the systematic noninferiority test enough margin to avoid an obviously underpowered minimum-cardinality instance;
3. leaves source-owned materiality relations and every exact discrete scientific decision as independent hard gates; and
4. does not weaken the realized materiality statement because \(n=300\) plus the required zero-event rule gives a much tighter exact bound than 0.09.

The algebraic minimum from materiality alone would be:

\[
n_{\min}
=
\left\lceil
\frac{\log(0.0125)}{\log(0.91)}
\right\rceil
=
47.
\]

That minimum is intentionally not used because it is inadequate for the separate systematic noninferiority statement near the exact-exchangeability boundary.

## 3. Prospective finite-sample properties

For \(n=300\) and zero materiality events, the exact one-sided Clopper-Pearson upper bound is:

\[
Q
=
1-0.0125^{1/300}
=
0.014500594315008053.
\]

Thus every passing Stage-C record under this instance certifies:

\[
q_R^\ast\le 0.014500594315008053,
\qquad
q_C^\ast\le 0.014500594315008053
\]

at the per-statement confidence allocation, which is materially stronger than the ratified ceiling \(q_{\rm cat}=0.09\).

For each systematic score family, the acceptance boundary is:

\[
U_j\le0.59.
\]

At \(n=300\), the largest accepted strict-worse count is:

\[
X_j=157,
\]

for which the exact one-sided upper bound is:

\[
U_j=0.5889955188269194.
\]

At \(X_j=158\),

\[
U_j=0.5922654009522088,
\]

so the statement fails.

If exact backend equivalence lies at the worst-case continuous exchangeability boundary \(p_j=0.5\), the exact probability that one systematic family satisfies this finite-sample boundary is approximately:

\[
P[X_j\le157\mid X_j\sim{\rm Binomial}(300,0.5)]
=
0.8067450864436305.
\]

This approximately 80% one-family boundary power is the explicit prospective reason for choosing \(n=300\) rather than the materiality-only minimum.

No independence between the two systematic families is assumed or used to claim a joint power value.

## 4. Interpretation

The numerical noninferiority coordinate permits:

\[
p_j\le0.59
\]

for each strict-worse score family, but this does **not** authorize a source-material scientific mismatch.

A passing record still additionally requires:

- zero source-material reference events;
- zero source-material candidate events;
- every governed \(\mathcal R_e\) to pass;
- every exact discrete scientific decision to agree;
- structural projection proof;
- exact production-coefficient qualification; and
- all Candidate-10 production-law/currentness/failure semantics.

Therefore the 0.09 systematic margin is not a 9% physical-error tolerance.

## 5. Current lifecycle state

Bound now:

- \(\eta_{\rm NI}=0.09\);
- \(q_{\rm cat}=0.09\);
- \(n=300\);
- evaluator \(\eta_{\rm NI}=0.09\);
- evaluator \(q_{\rm cat}=0.09\);
- \(n_{\rm eval}=300\).

Still required before Stage C:

- exact \(E\);
- every source-owned \(\mathcal R_e\);
- exact \(\mathcal Q\);
- exact \(\mathcal W_{\rm pre},\mathcal W_R,\mathcal W_C\);
- exact \(P_R^{\rm prod},P_C^{\rm prod}\);
- exact evaluator production laws and projection/oracle instance coordinates;
- exact per-key scientific/runtime identities for MH-1 and MPA-0.

Those remaining coordinates must be reconstructed from accepted source/current production ownership and the target-host regime; they may not be chosen from Candidate-10 outcomes.
