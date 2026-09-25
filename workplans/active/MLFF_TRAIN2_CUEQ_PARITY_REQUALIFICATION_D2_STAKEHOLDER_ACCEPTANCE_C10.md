---
kind: D2-stakeholder-acceptance-record
protocol_version: 6.4.0
status: METHOD_FAMILY_ACCEPTED_EXACT_INSTANCE_BINDING_PENDING
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate: db2ed47e8c999cb61507803610c72c0fa7ffaaf7
candidate_blob: 7843a41172d25c231d4c589aebc0214ddec42bd1
independent_review: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R7.md
review_commit: 9558c24068016dc95d413b21d627a11ab9788399
stakeholder_action: ACCEPTED_METHOD_FAMILY_PROCEED
date: 2026-09-25
---

# Candidate-10 stakeholder acceptance record

## 1. Stakeholder action

The stakeholder explicitly accepted the reviewed Candidate-10 method family and directed the work to proceed after being shown the method.

This records acceptance of the immutable reviewed D2 family:

db2ed47e8c999cb61507803610c72c0fa7ffaaf7

with semantic blob:

7843a41172d25c231d4c589aebc0214ddec42bd1

and fresh independent Review PASS recorded in:

workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R7.md.

## 2. Scope of this acceptance

This acceptance ratifies the reviewed **Candidate-10 method family** as the D2 basis for the next lifecycle step.

It does not fabricate an exact Stage-C qualification instance.

Candidate 10 deliberately defines the following as stakeholder-owned prospective instance coordinates with no generated default:

- \(\eta_{\rm NI}\);
- \(q_{\rm cat}\);
- finite triplet count \(n\);
- exact downstream consumer population \(E\);
- every exact source-owned materiality relation \(\{\mathcal R_e\}\);
- exact qualification design \(\mathcal Q\);
- exact \(\mathcal W_{\rm pre},\mathcal W_R,\mathcal W_C\);
- exact \(P_R^{\rm prod},P_C^{\rm prod}\);
- corresponding projection/evaluator instance coordinates, including \(n_{\rm eval}\) where applicable.

The stakeholder has not previously supplied numerical values for \(\eta_{\rm NI}\), \(q_{\rm cat}\), or \(n\). No such values are inferred from Candidate observations, Stage-A evidence, historical Rev86 rules, the R6 adversary, or implementation convenience.

## 3. Still-binding family constraints

Any exact instance must satisfy Candidate 10 exactly, including:

\[
0\le \eta_{\rm NI}\le q_{\rm cat}<0.10,
\qquad
q_{\rm cat}>0,
\]

and

\[
n\ge
\left\lceil
\frac{\log(0.0125)}{\log(1-q_{\rm cat})}
\right\rceil.
\]

The selected \(n\) must be frozen before Candidate-10 outcomes are inspected. A larger \(n\) is permitted only for an explicit prospective evidence-budget/power reason.

The exact instance must also bind the complete production-equivalent child execution laws and the same \(\mathcal W_C\) used by ordinary production CuEq, not a qualification-only slot mixture or start snapshot.

## 4. Lifecycle consequence

State after this acceptance:

1. immutable Candidate 10: REVIEW PASS;
2. stakeholder acceptance of method family: RECORDED;
3. exact Candidate-10 Stage-C instance: NOT YET RATIFIED;
4. Stage C: BLOCKED ONLY ON EXACT INSTANCE BINDING;
5. D3/D4: BLOCKED PENDING FRESH STAGE-C PASS.

No Stage-C run may begin and no qualification parameters may be silently selected until the exact instance is explicitly ratified.

## 5. Next durable artifact

The next D2 lifecycle artifact must be an exact Candidate-10 instance-ratification record binding every coordinate listed in Section 2.

That record may resolve source-owned coordinates from the accepted parent/current exact role, but it may not invent stakeholder-owned risk values. Only after the complete instance is explicit and ratified may Stage-C evidence begin.
