---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 293bc8e3fcdb0cdda6a22608d2a280fdd7a97ab4
supersedes: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R8.md
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R9

## Disposition

**PASS AS WORKPLAN AFTER REVISION-10 REPAIR.**

R9 follows the challenged parity relation through doctor admission, stored realization reuse, optimizer-reachable model state, transient CuEq checkpoint authentication, dependency-native CuEq -> e3nn state transfer, and P5 EVAL2 measurement identity.

## Finding R9-1 — model-state applicability was previously undefined

Doctor qualifies the exact selected-head starting checkpoint, while TRAIN2 produces new parameter states. Existing recurrence-repair evidence exercises perturbed trained CuEq states and native projection, but that evidence is not D2 authority and does not by itself prove that the doctor witness transports over the full compatible model-state domain.

Revision 10 now requires D2 to define whether acceleration equivalence is an operator-level relation uniform over a specified model-state/architecture domain or a state-scoped relation. Starting-checkpoint admission, trained-state backend behavior, and trained-state CuEq -> portable-e3nn projection may share one relation only if their validity domains are established.

## Finding R9-2 — EVAL2 measurement realization is mislabeled

Current checkpoint authentication correctly authenticates state in the transient CuEq model and then transfers that state into the canonical portable e3nn shell before returning the EVAL2 provider. However, `campaign_post_selection_runtime._checkpoint_provider_realization()` records the TRAIN2 backend in the measurement identity. For generated CuEq TRAIN2 this says `cueq` even though the actual EVAL2 forward is e3nn.

Revision 10 requires direct repair at the existing provider-realization/measurement-identity owner. It does not weaken transient CuEq architecture/state authentication. Old mislabeled EVAL2 measurement evidence becomes stale through its own content identity; authenticated TRAIN2 roots remain reusable when otherwise current.

## Finding R9-3 — source-side stored realization has the same parity-currentness class

The earlier plan already identified that stored TRAIN2 realizations could survive a parity-policy change. The source-side `_stored_acceleration_realization` has the same class of defect: backend/device/dtype plus historical qualification do not prove current parity-method ancestry.

Revision 10 extends the currentness repair to both existing realization families and adds no parallel registry.

## Finding R9-4 — generated policy and runtime representation remain distinct

The generated phase split remains source-side e3nn / TRAIN2 cueq. P5 EVAL2 after CuEq TRAIN2 is nevertheless a portable e3nn numerical forward after authenticated state transfer. Revision 10 now keeps these separate:

- generated TRAIN2 policy: cueq;
- checkpoint state provenance: transient CuEq realization;
- EVAL2 numerical provider: portable e3nn;
- repair-time avoidance path: explicit TRAIN2 e3nn override.

This prevents backend labels from being reused as if they described all lifecycle roles.

## Retained constraints

All R1-R8 findings remain active: accepted D1/D2 composition, complete acceleration-family source closure, no threshold tuning, raw-vs-summary evidence classification, dependent-pair statistics, quantile/tail-resolution checks, probe-domain adequacy, channel/descriptor semantics, source-e3nn/TRAIN2-cueq generated split, CUEQ-PHASE1/FINAL-GPU1 claim separation, no retry-until-pass, and exact target-host evidence.

No numerical relation, threshold, CuEq realization, or higher-level release qualification is accepted by this review.

## Final review result

At candidate `293bc8e3fcdb0cdda6a22608d2a280fdd7a97ab4`, the workplan is sufficiently precise to proceed to **Stage A**. The numerical Serious Challenge remains open and requires an accepted D2 candidate plus fresh independent review and stakeholder ratification before any parity-threshold change can authorize current CuEq execution.
