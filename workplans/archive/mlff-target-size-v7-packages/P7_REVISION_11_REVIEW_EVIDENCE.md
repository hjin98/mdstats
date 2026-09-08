---
kind: independent-design-review-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision_reviewed: 10
review_revision: 11
protocol_version: 5.8.0
reviewed_implementation_commit: afe4d690f1f7c084ac33077ecdcb24d67cd14802
reviewed_implementation_tree: ab4c1d32e44585615ba0501fb44d5666afe82190
post_implementation_documentation_head: f86b2de68072394dd189d21c46b8b0d4987a1a7c
verdict: NO-PASS
recorded_date: 2026-08-31
---

# P7 revision 11 — independent implementation review evidence

This record preserves the independent closure review that reopened P7. It is evidence, not a replacement for the governing workplan. The current repair authority is `P7_REVISION_11_AUTHORITY.md` composed with `P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and the frozen parent.

## Reviewed candidate

Executable source reviewed: `afe4d690f1f7c084ac33077ecdcb24d67cd14802` / tree `ab4c1d32e44585615ba0501fb44d5666afe82190`.

The later branch commit `f86b2de68072394dd189d21c46b8b0d4987a1a7c` changes generated PDF documentation only and therefore does not alter the source-review verdict. It does close the implementation evidence's stale-PDF item.

## Evidence basis

The review inspected the frozen parent, P7 base/revision-2/revision-10 authority, P5/P6 predecessor owners, the P7 implementation evidence, and the affected implementation modules including publication intake, identity/specification, persistence/currentness, deployment/runtime, physical/reference/relaxation/dynamics/calibration/locked reduction, resource ownership, CLI exposure, and representative predecessor P5 execution/publication code.

The implementation evidence reports substantial bounded functional coverage and no newly failing/erroring repository-wide node IDs relative to its fresh baseline. Those facts were treated as positive implementation evidence, but they do not waive missing real-owner or frozen scientific obligations.

## Blocking findings retained for repair

1. `single_best_final_seed` remains accepted configuration but is intentionally unsupported by P7 because P5 did not durably publish the pre-qualification cross-seed member-decision evidence. This is an explicit design-reopen trigger.
2. Deployment export/ML-IAP construction passes `head=None` instead of the canonical P5 target head, so multihead-replay product identity is not sealed through deployment.
3. P7 public current record/release resolution is only selected-binding fenced and can expose an old terminal verdict after P7 specification/executable/environment/publication currentness changes.
4. Exact external reference-bundle content is not part of the reference-dependent component reuse key; same-request bundle replacement can leave stale PES/relaxation evidence current.
5. Dynamics runs from original OUTER_MONITOR frames rather than authenticated reference-relaxed starting geometries and omits required NVE-temperature and persistent protected displacement/bond/angle degradation diagnostics.
6. Locked activation is published before locked evidence, and an interruption in that window leaves the same cohort permanently marked activated with no supported resume-to-terminal path.
7. Case scheduling uses only available CPU threads rather than the accepted campaign resource scope/admission owner, and same-member deployment artifact construction is not synchronized for restart/concurrency.
8. External reference protocol can remain the placeholder `external-reference-protocol-unset` rather than failing closed for production reference-dependent qualification.
9. Stress is omitted from deployed/reference evidence and strain qualification even though the base workplan requires E/F/stress parity when available and stress/strain response where applicable.
10. Qualification-local bond/angle/connectivity algorithms are retained despite canonical `mdstats.analysis` atomic connectivity/bond-angle/framework topology surfaces; ownership equivalence was not established.
11. The claimed real runtime smoke executes an analytic `MLIAPUnifiedLJ`, not an actual P5 MACE target-head artifact through the real MACE deployment owner.
12. Mandatory final target-machine qualification with real external references has not been run.

## Verdict rationale

Any one of findings 1, 2, 3, 5, 6, 11, or 12 is sufficient to block P7 closure because it changes or fails to prove release semantics. The remaining findings are also binding frozen-workplan gaps and are included in the revision-11 repair gate rather than deferred as optional hardening.

P7 is therefore **NO-PASS / REOPENED**. The post-P7 storage reset remains blocked.