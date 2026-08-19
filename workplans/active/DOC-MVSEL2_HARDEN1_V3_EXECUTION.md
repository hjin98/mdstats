# DOC-MVSEL2-HARDEN1-V3 execution state

This is a Protocol-v3 coordination/evidence-reference supplement.  It does not
change the frozen design in `DOC-MVSEL2_HARDEN1_V3.md` and is excluded from
candidate product identity by the governing policy.

## Governing identity

- Workplan: `DOC-MVSEL2-HARDEN1-V3` revision 1
- Protocol: `3.0.0`
- Workplan Git blob: `f889a6ea1c72b1995c20d2010137097a7411a422`
- Workplan SHA-256: `ac674abd68dcc43f0fe8f559aecbe913b6e9ae79194e5ff7327b2de531e2716b`
- Analysis base: `e24d5168ce01bf2d773339e1a91d5ded4871a57f`
- Target branch: `feat/mvsel2-forward-lazy`
- Rescue execution policy: GitHub connector for repository traffic; no GitHub-hosted test or benchmark execution

## Bounded stale-plan revalidation

The analyzed base remains an ancestor of the feature branch.  Product changes
since that base are concentrated in the diagnosed hardening surfaces: REPAIR2
policy/trace/no-copy scoring, native forward-only campaign integration,
MVSTATE2 selection continuation, selector-to-repair checkpoint reuse, focused
regressions, benchmark/qualification harnesses, and corresponding candidate
documentation/release status.  Later interrupted-work commits were primarily
GitHub workflow diagnostics.  No inspected change requires alteration of the
frozen MVSEL2/REPAIR1 scientific semantics, MVIDX1 scientific identity, target
sizes, coverage policy, or design-revision triggers.

Result: the workplan is not classified `STALE_WORKPLAN` by bounded source
inspection.  Execution evidence is still required before any qualification or
acceptance PASS.

## Reconciled implementation state

| Gate | Implementation | Qualification | Acceptance | Evidence/state |
|---|---|---|---|---|
| H0 REVIEW-BASELINE | PREPARED | NOT_REQUIRED | PENDING | focused hardening regressions/sentinels are present; local execution unavailable in current rescue runtime |
| H1 REPAIR2-SEM1 | PREPARED | NOT_RUN | PENDING | v2 policy mirrors REPAIR1 defaults/validation; tests compare complete non-empty legacy trace and terminal order |
| H2 MVIDX-FWD-RUNTIME1 | PREPARED | NOT_RUN | PENDING | campaign hardening runtime opens authenticated native forward-only MVIDX view; inverse-open sentinel test present |
| H3 MVSTATE2-RESUME1 | PREPARED | NOT_RUN | PENDING | highest-valid checkpoint fallback, selected-prefix replay, Phase-B exact rebase, and post-divergence state-carry implementation/tests present |
| H4 REPAIR2-SCALE1 | PREPARED | NOT_RUN | PENDING | no-copy analytical proposal implementation present; new full-ladder production harness added at `benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py` |
| H5 QUAL-HARDEN1 | BLOCKED | NOT_RUN | BLOCKED | exact private candidate checkout and repository-prescribed execution environment are unavailable locally in the current rescue runtime |
| H6 CLOSEOUT-HARDEN1 | IN_PROGRESS | NOT_RUN | PENDING | runtime clarification and truthful release-status correction staged; permanent PDF/provenance and final candidate freeze remain pending |

`PREPARED` above means source/test/harness construction is sufficiently present
for the declared remaining qualification.  It is not a qualification or
acceptance PASS.

## Rescue additions

Product/candidate-side additions made during this rescue:

- `benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py`
  - consumes campaign `target_multi_view_selection_v2` authority;
  - requires the materializable fixed-eight ladder through 16,384 on the
    36,408-candidate/165-family production graph;
  - uses default `TargetMultiViewRepairPolicyV2`;
  - reuses authenticated MVSTATE2 rung states where available;
  - records per-rung wall time, proposal counts, shortlist limit, swaps,
    restore/replay mode, RSS, clone count, and inverse-mutation status.
- `scripts/mvsel2_harden1_v3_candidate_identity.py`
  - deterministically hashes included tracked candidate surfaces;
  - excludes only declared coordination/evidence classes;
  - rejects dirty tracked candidate surfaces.
- `docs/specs/training_data/mlff_target_data2c_mvsel2_harden1_v3_runtime_spec.md`
  - documents native-forward campaign execution, highest-valid restart,
    selected-prefix reconstruction, pre-divergence MVSTATE2 reuse,
    post-divergence state carry, and exact no-copy proposal semantics.
- `release/MLFF_MVSEL2_HARDEN1_V3_STATUS_0.20.242a0.json`
  - supersedes the old record only for unresolved hardening acceptance claims;
  - preserves the old record as historical evidence;
  - states merge/workplan completion as false.

## Current hard blocker

Protocol-v3 qualification preflight cannot be satisfied in the current rescue
runtime:

1. the GitHub connector provides private file/commit/PR operations but exposes
   no private repository clone/archive/tree-export primitive;
2. the local runtime contains no mdstats checkout;
3. `conda` is absent locally, so the repository-prescribed `mace` environment
   cannot be invoked;
4. the production campaign database/input graph required for the 36,408 /
   165-family H4 measurement is not available locally.

The network route must not be bypassed with direct `git clone` or raw GitHub
traffic.  GitHub Actions must not be substituted for local qualification.

Therefore H5 is `BLOCKED`, H6 cannot be finalized/frozen, no valid
Qualification Handoff can yet bind a recomputed `candidate_content_identity`,
and the workplan must not be marked `PREPARED_FOR_QUALIFICATION`,
`READY_FOR_VERIFICATION`, or `COMPLETE`.

## Qualification restart boundary

Once the exact candidate can be materialized locally in the prescribed
environment, resume without redesign:

1. verify the governing workplan SHA-256 above;
2. run focused H0-H3 checks first;
3. resolve any source/test defect through implementation and create a new
   candidate commit if necessary;
4. regenerate/verify all required permanent PDF/provenance artifacts;
5. run `scripts/mvsel2_harden1_v3_candidate_identity.py` on a clean candidate;
6. freeze candidate ref/commit/content identity;
7. issue a Protocol-v3 Qualification Handoff with product source mutation
   forbidden;
8. execute focused + adjacent-v1 + full-non-slow + clean-wheel checks locally;
9. execute selector and full-ladder MVSTATE2/REPAIR2 production qualification,
   including the StageResourceScope-wrapped campaign integration path;
10. record GPU as `DEFERRED_NOT_RUN` unless genuinely executed;
11. route exact failures back to implementation and invalidate dependent
    evidence only;
12. after all mandatory qualification passes, perform independent Protocol-v3
    verification before any `COMPLETE` or merge-ready decision.
