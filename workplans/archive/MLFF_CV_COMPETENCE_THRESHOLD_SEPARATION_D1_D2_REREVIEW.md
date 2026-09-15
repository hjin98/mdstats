---
kind: independent-d1-d2-rereview
protocol_version: 6.3.0
status: pass
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
reviewed_candidate_commit: 6745778adb3647b47efebf9eefdca08fc4fca166
review_disposition: PASS
stakeholder_ratification: "2026-09-15: all three values configurable by design; defaults 45/45/30 meV/angstrom"
closeout_record: workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md
---

# MLFF CV threshold policy — D1/D2 independent re-review

*Historical review record of candidate `6745778a`.* The threshold delta files it names as current authority were later incorporated into the broad canonical owners (D1 `docs/methods/mlff_scientific_method.md` §10.3/§11, D2 `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7) and removed; current lifecycle state is owned by `workplans/active/README.md`.

## Disposition

**D1 PASS. D2 PASS.** No Serious Challenge remains.

The prior NO-PASS correctly identified that the proposed papers confused a current/default production value with an immutable scientific constant. The stakeholder has now clarified the stronger governing rule: **all three foundation post-selection thresholds are independently configurable policy parameters**, with current/generated defaults `45 / 45 / 30 meV/angstrom`.

That clarification resolves the earlier D1-R1/D2-R1 defect and also makes the same parameterization explicit for the CV checkpoint threshold, which the earlier candidate had still treated as fixed.

## Accepted D1 meaning

Current branch D1 threshold authority is `docs/methods/mlff_post_selection_threshold_policy.md`.

The accepted scientific semantics are:

- `tau_cv`: configured foundation-CV checkpoint competence threshold on `M_mon`;
- `theta_cv`: configured held-out CV acceptance threshold, dimensioned by its outer metric;
- `tau_prod`: configured fresh-production checkpoint-quality threshold on `M_mon`;
- generated/current defaults `0.045 / 0.045 / 0.030` for the default target-force outer metric;
- every required fold/seed must pass configured CV checkpoint and held-out predicates;
- fixed-budget training, monitor/held-out separation, scratch isolation, replay/integrity gates and downstream qualification separation remain unchanged; and
- changing a threshold changes a role policy, not the shared adaptation method.

The stakeholder's explicit clarification in this review cycle satisfies the required human ratification for this threshold-policy decision.

## Accepted D2 meaning

Current branch D2 threshold authority is `docs/methods/mlff_post_selection_threshold_numerical_policy.md`.

The numerical predicate remains `A_rho(c) = S(c) AND r_mon(c) <= tau_rho`, but `tau_cv` and `tau_prod` are resolved policy values rather than hard-coded universal constants. `theta_cv` remains separately dimensioned by the outer metric. Inclusive IEEE-754 boundary semantics apply to each resolved target-force threshold.

The invalidation graph is exact and asymmetric: CV-threshold edits move CV policy/evidence and stale dependent production authorization; production-threshold edits move production only; shared constraint edits move the shared method and both roles. Stored metrics are never re-thresholded into current evidence.

## Downstream consequence

D3/D4 must now expose the already role-owned CV checkpoint value as a configuration knob in addition to the existing CV outer threshold and production threshold. This requires no new policy owner or schema merely because configurability is exposed. The dedicated D3/D4 threshold authority files on this branch state the exact ownership/configuration contract.

The assembled D4 implementation is therefore no longer fully conforming until the foundation CV checkpoint resolver and generated/public configuration surface accept the new explicit CV checkpoint field while preserving default `0.045` and scratch behavior.

## Acceptance state

D1 and D2 threshold authority are accepted on this branch after independent re-review and stakeholder ratification. The active cycle remains open only for downstream D3/D4 representation/implementation reconciliation, executable regression, canonical-document consolidation, and ordinary closeout/history obligations.
