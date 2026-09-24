---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 8b1f701c91c3875a654bd699ab4a37b23414f862
supersedes: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN_REVIEW_R5.md
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R6

## Disposition

**PASS AS WORKPLAN AFTER REVISION-7 REPAIR.**

R6 rechecked the supposedly closed workplan against the actual current campaign generator and protected regression behavior. It found one material configuration/authority error and repaired it.

## Finding R6-1 — generated default was misread at the phase boundary

Current product code and tests protect the generated split:

```text
source / DATA6 / evaluation backend = e3nn
TRAIN2 backend                     = cueq
```

The earlier workplan shorthand “current generated MH-1 default remains e3nn” conflated source-backend CONFIG1 with TRAIN2 backend policy. CONFIG1 evidence naming e3nn is true for the source side; CUEQ-DEFAULT1 remains the owner of generated TRAIN2 `cueq`.

This distinction is material because the workplan is specifically about TRAIN2 parity.

## Finding R6-2 — previous safe TOML did not disable challenged TRAIN2 CuEq

The prior workplan advised only:

```toml
[acceleration]
backend = "e3nn"
```

In a phase-separated current campaign, `training_backend` remains independently `cueq`. The previous safety instruction therefore could still execute the challenged path.

Revision 7 now requires the bounded repair-time override:

```toml
[acceleration]
backend = "e3nn"
training_backend = "e3nn"
only_cueq = false
require_available = true
```

This is operational containment for a run that must avoid the challenged relation; it is not a generated-default mutation.

## Finding R6-3 — residual accepted-gate wording contradicted confirmed source-closure gap

The workplan still said doctor “correctly realizes the accepted gate” and Gate A still contained a branch for an already accepted CuEq relation. Those phrases contradicted R4/R5's confirmed finding that the accepted D2 source contains no CuEq acceleration-equivalence relation.

Revision 7 now consistently calls Rev86 the current executable D4 fail-closed rule and makes D2 source closure mandatory.

## Retained findings

All R1-R5 repairs remain in force: accepted-parent composition, full role/dtype CuEq parity source closure, raw-vs-summary evidence rules, dependent-pair statistics, order/warm-up/process/quantile/cardinality falsification, probe-domain adequacy, descriptor semantics, stale-realization currentness, training-identity impact, CUEQ-PHASE1/FINAL-GPU1 claim separation, independent oracles, and no retry-until-pass.

No numerical criterion, threshold, CuEq realization, or higher-level qualification is accepted by this review.
