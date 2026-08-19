# DOC-MVSEL2-HARDEN1-V3 execution state

This is a Protocol-v3 coordination/evidence-reference supplement. It does not change the frozen design in `DOC-MVSEL2_HARDEN1_V3.md` and is excluded from candidate product identity by the governing policy.

## Governing identity

- Workplan: `DOC-MVSEL2-HARDEN1-V3` revision 1
- Protocol: `3.0.0`
- Workplan Git blob: `f889a6ea1c72b1995c20d2010137097a7411a422`
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Analysis base: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Target branch: `feat/mvsel2-forward-lazy`
- Execution policy: GitHub connector for repository traffic; no GitHub-hosted qualification substitution

## Bounded stale-plan revalidation

The analyzed base remains an ancestor of the feature branch. Product changes since that base are concentrated in the diagnosed hardening surfaces: REPAIR2 policy/trace/no-copy scoring, native forward-only campaign integration, MVSTATE2 selection continuation, selector-to-repair checkpoint reuse, focused regressions, benchmark/qualification harnesses, and corresponding candidate documentation/release status. No inspected change requires alteration of the frozen MVSEL2/REPAIR1 scientific semantics, MVIDX1 scientific identity, target sizes, coverage policy, or design-revision triggers.

Result: the workplan is not `STALE_WORKPLAN`. Execution evidence is still required before any qualification or acceptance PASS.

## Reconciled implementation state

| Gate | Implementation | Qualification | Acceptance | Evidence/state |
|---|---|---|---|---|
| H0 REVIEW-BASELINE | PREPARED | NOT_REQUIRED | PENDING | focused hardening regressions/sentinels are present |
| H1 REPAIR2-SEM1 | PREPARED | NOT_RUN | PENDING | v2 policy mirrors REPAIR1 defaults/validation; tests compare complete non-empty legacy trace and terminal order |
| H2 MVIDX-FWD-RUNTIME1 | PREPARED | NOT_RUN | PENDING | campaign hardening runtime opens authenticated native forward-only MVIDX view; inverse-open sentinel test present |
| H3 MVSTATE2-RESUME1 | PREPARED | NOT_RUN | PENDING | highest-valid checkpoint fallback, selected-prefix replay, Phase-B exact rebase, and post-divergence state-carry implementation/tests present |
| H4 REPAIR2-SCALE1 | PREPARED | NOT_RUN | PENDING | no-copy analytical proposal implementation and full-ladder production harness are present |
| H5 QUAL-HARDEN1 | PENDING | NOT_RUN | PENDING | reserved for exact frozen-candidate execution in the user's local `mace` environment with production campaign inputs |
| H6 CLOSEOUT-HARDEN1 | IN_PROGRESS | NOT_RUN | PENDING | hosted repository-local closeout is being finalized before candidate freeze; final acceptance remains verification-owned |

`PREPARED` means source/test/harness construction is sufficiently present for the declared remaining qualification. It is not a qualification or acceptance PASS.

## Hosted closeout responsibility

Before workstation qualification, complete every deterministic repository-local task available in the ChatGPT environment rather than spending target-environment Codex capacity on it. This includes permanent documentation/release-metadata correction, removal of temporary GitHub diagnostic workflows, generated product artifact/provenance preparation when reproducible under the repository policy, coordination cleanup, and source review.

The target workstation is required only for candidate-bound checks whose validity depends on the exact local checkout/environment and for production-data measurements unavailable here. Candidate content must not be mutated during qualification.

## Remaining transition to qualification

1. finish permanent candidate PDF/provenance closeout under the established renderer policy;
2. finalize truthful candidate release status without converting any `NOT_RUN` result into PASS;
3. establish the final candidate commit and deterministic candidate content identity from a clean checkout;
4. bind a narrow Protocol-v3 Qualification Handoff;
5. execute focused/adjacent/full-non-slow/wheel qualification against that exact frozen candidate in the prescribed workstation environment;
6. execute selector and full-ladder MVSTATE2/REPAIR2 production qualification, including the StageResourceScope-wrapped campaign path, using the real production input graph;
7. record GPU as `DEFERRED_NOT_RUN` unless genuinely executed;
8. route any source defect back to implementation and recompute candidate identity before affected reruns;
9. after all mandatory qualification passes, perform independent Protocol-v3 verification before any `COMPLETE` or merge-ready decision.
