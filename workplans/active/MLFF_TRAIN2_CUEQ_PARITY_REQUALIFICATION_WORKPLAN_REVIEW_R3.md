---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 5072371da0bbb1693504590db5f2ea9f22dd5be0
supersedes: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R2.md
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R3

## Disposition

**PASS AS WORKPLAN AFTER REVISION-4 REPAIR.**

R3 is the final historical-authority adversarial pass. It corrects one overconstraint introduced by R2.

## Finding R3-1 — CUEQ-PHASE1 is not a universal current campaign prerequisite

R2 correctly found that the located CUEQ-PHASE1/FINAL-GPU1 artifacts remained deferred. It incorrectly inferred that this made e3nn the only authorized ordinary execution path until those artifacts passed.

Revision 60 (`CUEQ-DEFAULT1`) is explicit: the project owner changed newly generated campaign policy to phase-separated CuEq TRAIN2 while deliberately leaving the immutable CUEQ-PHASE1/PERF-CERT1/FINAL-GPU1 records unchanged. Revision 61 hardened selected-head doctor parity as the fail-closed CuEq training realization gate. Later CONFIG1 restored e3nn as the generated MH-1 default, but current project prose still supports explicit opt-in CuEq subject to doctor qualification.

Therefore the correct claim separation is:

- current generated default: e3nn for new MH-1 campaigns;
- explicit CuEq opt-in: admissible only after the current doctor/runtime/parity realization gate passes;
- CUEQ-PHASE1: stronger paired-training evidence and an applicable release-qualification input, not an automatically reintroduced universal runtime prerequisite;
- PERF-CERT1/FINAL-GPU1: their own immutable release/certification claims, not rewritten by a doctor pass.

Revision 4 incorporates this separation throughout Stages A-E and acceptance.

## Findings retained from R1/R2

R3 rechecked and retains all earlier repairs: accepted D1/D2 pinning and composition, confirmed missing source-closed D2 CuEq parity relation, raw-vs-summary MPA-0 evidence handling, all-pairs dependence, order/warm-up/quantile/cardinality checks, probe-domain adequacy, channel dimensions/descriptor role, stale stored realization currentness, training-identity impact, independent oracle requirements, release-handoff rebinding, no retry-until-pass, and runtime/source-compatibility scope.

## Final plan-level state

No remaining plan-level blocker was found after correcting the authority-evolution mistake. The numerical parity relation itself remains under Serious Challenge. No threshold, CuEq realization, CUEQ-PHASE1 result, or FINAL-GPU1 status is accepted by this review.
