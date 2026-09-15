---
kind: independent-d1-d2-review
protocol_version: 6.3.0
status: no-pass
branch: fix/mlff-cv-competence-threshold-separation
accepted_baseline_commit: 8553ebe9ed86b24dfe910c9e43acc6230d3ece90
reviewed_candidate_commit: eb4a09119e6a595dd94af77fdf4714ad9c0ba954
highest_open_owner: D1
review_disposition: NO-PASS
---

# MLFF CV Competence Threshold Separation — Independent D1/D2 Review

## Disposition

**D1: NO-PASS. D2: NO-PASS downstream of the same authority defect.**

No Serious Challenge is raised against the scientific purpose of separating foundation-CV competence from fresh-production checkpoint quality, nor against the proposed `45 / 45 / 30 meV/angstrom` generated/default policy. The evidence-role separation, all-required-fold/seed consistency rule, fixed-budget semantics, scratch isolation, replay/integrity preservation, calibration provenance, and downstream qualification boundary are coherent.

One material authority mismatch blocks acceptance: the proposed D1/D2 papers state the foundation-production checkpoint ceiling as an unconditional fixed `0.030 eV/angstrom`, while the preserved public/current policy surface defines production checkpoint quality through `[acceptance].maximum_target_force_rmse_ev_per_angstrom` with **default** `0.030`. Current D4 resolution and the assembled counterfactual test both permit an explicit production-only ceiling change to create a different authenticated production-policy/run identity without changing the shared method or accepted CV evidence.

This is an upstream representation/authority defect, not a reason to change the working D3/D4 split.

## D1 review

The proposed D1 revision correctly establishes:

- CV asks whether the shared foundation-adaptation method consistently reaches a competence regime, not whether disposable folds reach production-quality late convergence;
- foundation CV checkpoint competence is `45 meV/angstrom` on the protected common monitor;
- default held-out target-force acceptance is `45 meV/angstrom` on separate held-out evidence;
- every required fold/seed must pass both predicates; mean/majority/best-seed rescue is forbidden and dispersion remains diagnostic;
- training remains fixed-budget and the CV horizon is a separately frozen design choice;
- the `45 meV/angstrom` calibration is explicitly stakeholder-authorized historical recollection rather than fabricated repository evidence;
- scratch semantics remain separate; and
- neither CV nor the production common-monitor criterion is external adequacy or release qualification.

### D1 blocker D1-R1 — production policy is presented as fixed rather than parameterized

Section 11 currently says a foundation-production checkpoint is admissible only at `<= 30 meV/angstrom`, and the D1->D2 handoff repeats production checkpoint quality `<= 30 meV/angstrom` as an unconditional predicate. That is too strong for the preserved campaign policy actually authorized by this workplan and existing public configuration surface.

The current D4 contract resolves foundation production from `[acceptance].maximum_target_force_rmse_ev_per_angstrom`, default `0.030`, while foundation CV is deliberately decoupled and fixed at `0.045`. The real-path identity test changes only the production ceiling to `0.045`, preserves the shared method and accepted CV evidence, and requires a new production run position. Therefore production ceiling is already modeled as a role-policy parameter, not a universal scientific constant.

**Required D1 repair:** express `30 meV/angstrom` as the current/generated default frozen production checkpoint-quality policy, while defining the scientific invariant parametrically: fresh production uses its own explicitly frozen/authenticated production target-force ceiling and CV's `45 meV/angstrom` can never substitute for or implicitly relax it. An explicit production-policy override is a distinct campaign policy instantiation whose identity/currentness must change. Preserve the current generated/default value `30 meV/angstrom` and the statement that this cycle does not relax it by default.

If the stakeholder instead intends `30 meV/angstrom` to be an unoverrideable scientific constant for all foundation production, that is a different decision: revoke/fail-closed the existing production threshold configuration surface and reopen affected D3/D4. The current workplan, implementation, and selective-invalidation design support the smaller parameterized interpretation.

All other scoped D1 Challenge targets pass this review. Re-review may be bounded to this authority repair plus consistency of affected references/provenance.

## D2 review

Subject to the D1 repair above, the proposed D2 role-predicate construction is otherwise coherent and sufficiently reconstructable:

- one effective predicate `A_rho(c) = S(c) AND r_mon(c) <= tau_rho`;
- inclusive IEEE-754 double boundaries;
- `tau_CV = 0.045 eV/angstrom` for foundation CV;
- default outer target-force threshold `theta_CV = 0.045 eV/angstrom` on a different population;
- alternate outer metrics retain their own dimensions and never supply `tau_CV`;
- every required fold/seed must have a nonempty admissible set and pass its outer predicate;
- no stored candidate classification is reinterpreted under a changed role ceiling;
- no threshold changes the fixed training budget; and
- scratch retains its pre-separation behavior.

### D2 blocker D2-R1 — `tau_prod` is incorrectly frozen to 0.030 in the generic predicate

Section 17.1 currently defines `tau_prod = 0.030 eV/angstrom` without representing the existing production role-policy parameter. Section 23.7 similarly treats the 30-meV boundary as unconditional. This makes D2 stricter than the actual accepted/configured policy family and leaves D3/D4 capable of executing a numerically different production predicate that D2 does not authorize.

**Required D2 repair after D1 is corrected:** define `tau_prod` as the authenticated/frozen foundation-production target-force ceiling for the campaign, resolved from the accepted production policy; state that its generated/current default is `0.030 eV/angstrom`. Boundary semantics apply to the resolved `tau_prod`: equality passes and the next representable double above it fails. Keep the current default oracle (`0.030` pass, `nextafter(0.030,+inf)` fail, `0.042` fail under the default policy) and add/retain the counterfactual oracle that an explicit production-only ceiling change moves production-policy/run identity without moving the shared method or applicable CV evidence.

Do not make `tau_CV` depend on this production policy and do not add a second threshold owner.

All other scoped D2 Challenge/oracle targets pass this review. Re-review may be bounded to the repaired `tau_prod` parameterization and dependent wording/oracles.

## Acceptance state

The D1/D2 pair remains **proposed / NO-PASS**. No stakeholder ratification should be requested until the production-policy parameterization is reconciled and independently re-reviewed PASS.

After a bounded repair:

1. re-review D1 for the distinction between fixed foundation-CV competence and parameterized production role policy with generated/default `30 meV/angstrom`;
2. re-review D2 for exact parameterized `tau_prod` boundaries/currentness and preserved default 30-meV oracle;
3. if both pass, obtain explicit stakeholder ratification of the assembled D1/D2 revision; and
4. only then promote the authority and return to final lifecycle closeout.

No product-code repair, wrapper, compatibility layer, new protocol identity, or EVAL2 machinery is authorized by this finding.