# DOC-MVSEL2-HARDEN1-V3 execution state

This is a Protocol-v3 coordination/evidence-reference supplement. It does not change the frozen design in `DOC-MVSEL2_HARDEN1_V3.md` and is excluded from candidate product identity by the governing policy.

## Governing identity

- Workplan: `DOC-MVSEL2-HARDEN1-V3` revision 1
- Protocol: `3.0.0`
- Workplan Git blob: `f889a6ea1c72b1995c20d2010137097a7411a422`
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Analysis base: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Target branch: `feat/mvsel2-forward-lazy`
- Frozen candidate commit: `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`
- Candidate identity policy: `mdstats.mvsel2-harden1-v3.candidate-identity.v1`
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
| H6 CLOSEOUT-HARDEN1 | PREPARED | NOT_RUN | PENDING | deterministic repository-local closeout is complete; final evidence/acceptance remains qualification/verification-owned |

`PREPARED` means source/test/harness construction is sufficiently present for the declared remaining qualification. It is not a qualification or acceptance PASS.

## Repository-local closeout completed

The implementation authority completed the deterministic closeout before candidate freeze:

- temporary GitHub diagnostic qualification workflows removed;
- Protocol-v3 repository handoff updated;
- historical patch-note acceptance wording corrected;
- permanent HARDEN1-v3 runtime clarification staged;
- patch-notes and runtime-spec PDFs regenerated and visually verified under the established `pandoc-typst-v2` policy using Pandoc 3.10.2 and Typst 0.15.1;
- matching SHA-256 provenance manifests committed;
- release-status metadata corrected without promoting any unexecuted qualification result to PASS;
- candidate-facing content frozen at `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`.

Subsequent changes to this execution supplement, repository handoff, and `qualification/` records are coordination/evidence-only paths excluded by `mdstats.mvsel2-harden1-v3.candidate-identity.v1`; they do not alter the frozen candidate content identity.

## Remaining transition to qualification

1. materialize commit `a9cb41ad9b1c6305de195f1a88b71ea098e582b7` in a clean workstation checkout;
2. require an empty `git status --porcelain=v1 --untracked-files=all` before qualification bootstrap and review any shadowing/import source explicitly;
3. verify the governing workplan SHA-256 equals `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`;
4. compute `candidate_content_identity` using `scripts/mvsel2_harden1_v3_candidate_identity.py` and bind it into the exact Protocol-v3 Qualification Handoff;
5. execute only the handoff-enumerated focused/adjacent/full-non-slow/wheel and production-data checks against that immutable candidate;
6. include selector/checkpoint-resume/REPAIR2 full-ladder evidence and a separate `StageResourceScope`-wrapped campaign integration execution on the real production graph;
7. record GPU as `DEFERRED_NOT_RUN` unless genuinely executed;
8. route any product-source/test-contract defect back to implementation; do not patch the frozen candidate during qualification;
9. after all mandatory qualification passes, perform independent Protocol-v3 verification before any `COMPLETE` or merge-ready decision.

The implementation-owned workstation bootstrap contract is `qualification/handoffs/DOC-MVSEL2-HARDEN1-V3_WORKSTATION_BOOTSTRAP.md`.
