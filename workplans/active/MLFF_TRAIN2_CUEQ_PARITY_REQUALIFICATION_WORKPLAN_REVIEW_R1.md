---
kind: workplan-review
protocol_version: 6.4.0
status: pass-as-workplan-after-repair
review_date: 2026-09-24
reviewed_workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: 797328a8c972ebdd908fc08269eb746d417cc1a1
highest_reviewed_domain: D2
authority_acceptance: false
---

# MLFF TRAIN2 CuEq parity requalification — Workplan Review R1

## Disposition

**PASS AS WORKPLAN AFTER REVISION-2 REPAIR.**

This review does not accept a CuEq numerical-equivalence relation. It reviews whether the active plan is adequate to investigate, formulate, falsify, promote, implement, and close the challenged relation without authority inversion, evidence leakage, threshold tuning, stale-state reuse, or duplicate machinery.

## Blocking findings repaired

The reviewed Revision-1 plan was not adequate for execution. The repaired Revision-2 plan closes the following blockers:

1. **Accepted-authority provenance.** Current repository head contains proposed D1/D2 renewal content from another cycle. Revision 2 pins the accepted D1/D2 kernel at `a759e81...`, its exact ratified source at `a4824d2...`, and adds a composition/rebase gate if accepted authority advances.
2. **Owner inversion.** The Rev86 parity specification is historical/backend-qualification material under the current D4 index, not a sufficient D2 semantic owner. Stage A now requires proof of its accepted-D2 import route or formal closure of the missing-D2-authority gap.
3. **Authorization scope.** Instantaneous selected-head parity was being discussed too broadly. Revision 2 preserves CUEQ-PHASE1 short/full paired-training qualification and FINAL-GPU1 as separate higher-level authorities.
4. **Evidence preservation.** Failed doctor already persists the repeatability/parity/policy/realization records. Revision 2 requires authenticating/exporting those existing records before any rerun and forbids a second evidence registry.
5. **MPA-0 provenance.** The located DIAG3 CPU qualification explicitly deferred GPU execution; the workstation values survive as summaries/fixtures unless a raw record is found. Revision 2 requires raw-artifact search or fresh target-host realization before a generic current claim.
6. **Statistical semantics.** Revision 2 distinguishes a finite-sample all-pairs functional from population inference, forbids treating 45/45/100 dependent pairs as independent replication, and requires valid hierarchical uncertainty if inference is claimed.
7. **Execution-order confounding.** Current diagnostic always evaluates e3nn before CuEq. Revision 2 requires order/process diagnostics before attributing the distribution solely to backend stochasticity.
8. **Warm-up and tail resolution.** One warm-up and 10 repeats were historical choices; p99.9 on 45 force components is effectively an extreme-order interpolation. Revision 2 requires adequacy and exact quantile semantics.
9. **Probe-domain inadequacy risk.** Doctor uses one source structure plus deterministic displacement/strain variants. Revision 2 separates cheap campaign smoke from the corpus needed for a generic equivalence claim.
10. **Channel semantics.** One absolute stable-channel ceiling spans energy/atom, stress, and latent descriptors. Revision 2 requires units/scales/protected consequences and resolves the absolute-vs-rtol representation ambiguity before changing D2.
11. **Descriptor role.** Revision 2 requires deciding whether descriptor values are governed outputs or a proxy for exact downstream selection, with near-tie robustness evidence.
12. **Currentness.** The stored TRAIN2 realization loader checks backend/device/dtype/checkpoint and the historical `qualified` flag but not current parity-policy identity. Revision 2 requires direct repair through existing policy/parity/realization owners.
13. **Training identity impact.** Acceleration realization digest is training identity material in current D4. Revision 2 requires a projection analysis rather than automatic retraining or unsafe reuse.
14. **Release binding.** FINAL-GPU1 handoff integrity binds parity-policy digests and forbids source edits inside the sealed handoff. Revision 2 requires regeneration/rebinding rather than in-place mutation.
15. **Oracle independence.** Frozen scalar fixtures test reducer behavior but are not independent evidence for the criterion. Revision 2 requires independent numerical oracles plus real-owner/target-host evidence.
16. **No retry-until-pass.** Revision 2 requires predeclared realization counts/order and treats classification instability as evidence.
17. **Runtime applicability.** Revision 2 binds GPU/runtime/source-compatibility identity, including the current semantic qualification of differing MACE calculator bytes.

## Challenge state

The Serious Challenge remains open against the adequacy and/or formal D2 ownership of the current TRAIN2 FP32 CuEq parity rule. Runtime behavior remains fail closed. No numerical constant is changed by this review.

## Next gate

Execute Stage A only. Do not begin threshold implementation or D3/D4 parity-policy changes until Stage A partitions D4 defects, reconstructs authority provenance, and establishes the evidence basis needed for a D2 candidate.
