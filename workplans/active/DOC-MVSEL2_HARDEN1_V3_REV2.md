---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 2
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.0.0
lineage:
  source_workplan_id: DOC-MVSEL2-HARDEN1-V3
  source_plan_revision: 1
  source_protocol_version: 3.0.0
analysis_base_ref: feat/mvsel2-forward-lazy
analysis_base_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
qualification_regression_baseline_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
qualification_regression_baseline_role: pre-hardening analysis base
assumption_paths:
  - workplans/active/DOC-MVSEL2_HARDEN1.md
  - workplans/archive/DOC-MVSEL2_forward_lazy_selector.md
  - release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_coverage_sparse_index_store.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_mvsel2_forward.py
  - tests/test_mlff_mvstate2.py
  - tests/test_mlff_repair2.py
  - tests/test_mlff_mvmigrate2.py
  - qualification/evidence/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_REPORT.md
  - workplans/active/DOC-MVSEL2_HARDEN1_V3_IMPLEMENTATION_RETURN.md
architecture_refs:
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/arch_manuals/mlff_training_data/50_target_multiview.md
  - docs/arch_manuals/mlff_training_data/60_execution_performance.md
spec_refs:
  - docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md
expected_change_paths:
  - workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.md
  - workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_HANDOFF.template.md
  - workplans/active/DOC-MVSEL2_HARDEN1_V3_QUALIFICATION_DRIVER.py
  - workplans/active/DOC-MVSEL2_HARDEN1_V3_EXECUTION.md
  - workplans/active/DOC-MVSEL2_REPO_HANDOFF.md
  - qualification/
  - benchmarks/
default_gate_approval: AUTO
candidate_identity_policy: include all tracked product/runtime source, tests, specifications, architecture, package/build/config/schema, release metadata, and tracked generated product artifacts; exclude only workplans, qualification/verification coordination artifacts, and benchmark/evidence logs that cannot affect build/runtime/scientific/package behavior
---

# DOC-MVSEL2-HARDEN1-V3 — MVSEL2 Post-Implementation Conformance Hardening

## 1. Revision-2 authority and diagnosis

Revision 2 is a narrow Protocol-v3 design revision after target qualification of revision 1 returned `DESIGN_REVISION_REQUIRED` for H5/Q3. All frozen MVSEL2/REPAIR2 scientific, algorithmic, persistence, recovery, resource, performance, package-content, and release semantics from revision 1 remain unchanged.

The failed revision-1 qualification established that the exact candidate `a9cb41ad9b1c6305de195f1a88b71ea098e582b7` passed focused v2 and adjacent-v1 checks but the repository-wide command `pytest -q -m 'not slow'` completed with 3,187 passed and 307 failed. The retained failures span historical version/specification/architecture/example/compatibility/documentation contracts outside the MVSEL2 hardening change surface. Requiring absolute zero failures for this already-non-green repository confounds inherited repository debt with regressions introduced by the hardening candidate.

The earliest violated invariant is therefore the revision-1 H5 regression-oracle design, not an MVSEL2 algorithm defect: a broad regression gate must distinguish inherited failures from candidate-introduced failures while retaining absolute gates for the changed subsystem.

## 2. Objective

Preserve the completed MVSEL2 hardening candidate semantics while replacing only the unsound H5/Q3 absolute full-suite oracle with an authenticated same-environment differential regression oracle. Correct the independent Q4 installed-origin command so distribution qualification executes outside the source checkout.

This revision MUST NOT redesign MVSEL2 scoring/lazy certification, REPAIR1/REPAIR2 scientific semantics, MVIDX1/MVSTATE2 schema or recovery rules, target-data policy, production performance thresholds, package contents, or unrelated repository contracts.

## 3. Frozen implementation design

The revision-1 correction design remains frozen exactly:

1. REPAIR2 policy/default/validation is a semantic mirror of REPAIR1 except v2 authority/schema identity.
2. Complete persisted REPAIR2 swap records and terminal order match REPAIR1 for shared fixtures/policies.
3. Production MVSEL2/REPAIR2 execution obtains MVIDX runtime state through the native forward-only reader without inverse-array mapping inside the v2 execution boundary.
4. Campaign interrupted selection resumes from the highest valid compatible MVSTATE2 checkpoint, reconstructs historical entries by selected-candidate-only forward replay, and performs one exact Phase-B frontier rebase after restore when needed.
5. REPAIR2 consumes MVSTATE2 at selector-to-repair boundaries, uses selected-prefix forward replay only as fallback, and never restores later pure-selector state after the first accepted repair divergence.
6. REPAIR2 rejected proposals use no full forward-state clones; proposal scoring is the exact analytical hypothetical, and accepted mutation happens exactly once after the winner is chosen.

No product-source modification is required or authorized merely to satisfy revision-2 Q3. If differential qualification identifies a candidate-introduced failure, route that concrete failure to implementation normally.

## 4. H5/Q3 differential regression oracle

### 4.1 Baseline identity

The only approved broad-suite regression baseline is exact commit:

`e24d5168ce01bf2d773339e1a91d5ded4871a57f`

This is the original Protocol-v3 analysis base immediately preceding the hardening changes and already carries package version `0.20.242a0`; therefore version identity is comparable to the candidate. No moving branch name, `main`, later coordination commit, or locally modified checkout may substitute for this SHA.

### 4.2 Execution comparability

Baseline and candidate broad-suite runs MUST use:

- the same workstation/host class and same final `mace` environment;
- the same Python, pytest, installed dependency versions, environment variables relevant to tests, and marker expression;
- detached clean tracked/staged checkouts with undeclared shadowing/untracked execution-affecting files absent;
- exact command semantics `pytest -q -m 'not slow'` plus JUnit XML emission only;
- source-origin evidence proving each run imports from its intended checkout;
- no product-source mutation during either run.

If these dimensions differ materially, the differential evidence is `BLOCKED` rather than comparable.

### 4.3 Canonical failure signature

Each non-slow run MUST emit JUnit XML. The qualification comparator shall canonicalize every `failure` or `error` testcase as:

`(nodeid, outcome_kind, exception_type, normalized_primary_message)`

where normalization may remove only absolute checkout prefixes, platform path separators, line/column locations, elapsed-time values, and nondeterministic temporary-directory identifiers. It MUST NOT remove expected/actual values, exception types, semantic identifiers, versions, array/value content, or assertion text.

The comparator artifact MUST list baseline signatures, candidate signatures, candidate-only signatures, baseline-only signatures, and common signatures, with counts and the normalization policy version.

### 4.4 Q3 acceptance

Q3 is PASS only when all of the following hold:

1. Both baseline and candidate runs complete collection/execution sufficiently to emit valid JUnit XML; infrastructure/collection aborts are not treated as inherited test failures.
2. The candidate has **zero candidate-only failure/error signatures** after canonicalization.
3. Every candidate `failure`/`error` signature is present in the baseline signature set.
4. Every testcase that is new in the candidate relative to the baseline has no `failure` or `error` outcome.
5. Every testcase that PASSed on the baseline and is present in the candidate does not become `failure` or `error` on the candidate.
6. Candidate collection errors are zero unless the exact same canonical collection-error signature exists in the baseline; any new collection error fails Q3.
7. The report records total passed/failed/error/skipped/deselected counts for both sides, but aggregate counts alone never determine PASS.

A baseline failure disappearing in the candidate is permitted. A common failing nodeid with a changed semantic failure signature is candidate-only and therefore fails.

### 4.5 Evidence reuse

The existing candidate Q3 run from the failed revision-1 qualification MAY be reused only if qualification proves all of these dependencies remain identical:

- candidate commit `a9cb41ad9b1c6305de195f1a88b71ea098e582b7`;
- candidate content identity `56fdec9a708e99119cd3ba3708f3cf26f95867e648ca1729c890ca40d0feb956`;
- exact final `mace` environment identity and material test environment variables;
- exact non-slow marker semantics;
- source-origin/cwd semantics sufficient for source tests;
- retained authoritative candidate log SHA-256 `b5456e6170e9d41c9519767c04ed28e7149c55c2970ce4eb3dd6b41ed29c5e7f`.

Because revision 1 did not require JUnit XML, reuse of its stdout log alone is insufficient for differential PASS. If a trustworthy JUnit artifact for that exact run does not already exist, rerun candidate Q3 with JUnit XML. Do not synthesize missing structured evidence from the summary report.

## 5. Q4 installed-artifact qualification correction

Q4 remains mandatory absolute PASS. The wheel must be built from the exact candidate, installed with `--no-deps --target` into declared qualification scratch, and imported from outside the repository checkout using an absolute install-target `PYTHONPATH`. The assertion must prove `mdstats.__file__` is underneath that absolute install target and version is `0.20.242a0`. Wheel-content inspection must prove `workplans/` is absent.

Running the installed-origin assertion from repository root is forbidden because Python's empty-path entry can shadow the target installation.

## 6. Gate state and barriers

All gates remain AUTO. H0-H4 implementation preparation remains accepted from revision 1. H5 has `qualification_barrier: yes`; H6 remains prepared but final acceptance/archive is downstream.

| Gate | Implementation | Qualification | Acceptance | Barrier |
|---|---|---|---|---|
| H0 REVIEW-BASELINE | PREPARED | historical PASS evidence | PENDING verification | no |
| H1 REPAIR2-SEM1 | PREPARED | Q1 PASS | PENDING verification | no |
| H2 MVIDX-FWD-RUNTIME1 | PREPARED | pending production Q5 | PENDING | no |
| H3 MVSTATE2-RESUME1 | PREPARED | pending production Q5 | PENDING | no |
| H4 REPAIR2-SCALE1 | PREPARED | pending Q6/Q7 | PENDING | no |
| H5 QUAL-HARDEN1 | PREPARED after revised handoff | Q2 PASS; Q3 differential pending; Q4 rerun; Q5-Q7 pending | PENDING | yes |
| H6 CLOSEOUT-HARDEN1 | PREPARED | pending final qualification/verification | PENDING | yes |

## 7. Absolute acceptance retained outside Q3

The following remain absolute and MUST NOT be converted to baseline-relative criteria:

- focused v2 hardening regressions (Q1);
- adjacent v1 regression test file (Q2);
- Q4 clean wheel/install/import/package-content checks;
- production MVSEL2/MVSTATE2 continuation and corrupt-newest fallback checks;
- production REPAIR2 full-ladder telemetry and zero-copy/inverse-mutation assertions;
- StageResourceScope integration and frozen combined >=10x performance floor;
- candidate preflight/postflight content-identity and source-immutability checks.

GPU remains nonblocking `DEFERRED_NOT_RUN` unless genuinely executed, per revision 1.

## 8. Evidence dependencies and invalidation

- Q1/Q2 PASS evidence may be reused only for the unchanged candidate identity and unchanged material runtime/test environment; otherwise rerun.
- Revision-1 Q3 FAIL remains historical diagnostic evidence but is not by itself revision-2 Q3 acceptance evidence.
- Q3 revision-2 PASS requires the authenticated baseline/candidate differential artifacts defined above.
- Revision-1 Q4 FAIL is invalidated because the command had incorrect source-origin semantics; Q4 must rerun under the corrected command.
- Q5-Q7 remain NOT RUN and must execute under a revised exact handoff.
- Any product-candidate change invalidates candidate identity and all source-dependent qualification evidence unless the handoff explicitly proves dependency-safe reuse.

## 9. Implementation change surface

Implementation is limited to coordination/qualification surfaces needed to realize this design:

- revise the exact Qualification Handoff and template to bind revision 2 and its digest;
- add or revise a deterministic JUnit differential comparator under workplan/qualification coordination surfaces;
- correct Q4 cwd/source-origin command semantics;
- update execution/repository handoff records;
- do not modify product/runtime/tests/specs/package/release files unless a later differential failure returns a concrete candidate defect to implementation.

## 10. Design-revision triggers

Return `DESIGN_REVISION_REQUIRED` if:

- the baseline commit cannot execute comparably in the final target environment;
- baseline/candidate test identities cannot be compared deterministically enough to distinguish inherited from candidate-introduced failures;
- a proposed normalization would need to erase semantic assertion content to obtain equivalence;
- a candidate-only failure requires changing frozen scientific/algorithmic semantics;
- any revision-1 trigger fires, including weakened repair-trace equivalence, MVIDX1 scientific schema/content change, restoring pure-selector state after repair divergence, approximate/stochastic repair, or inability to retain the >=10x floor without algorithmic redesign.

Use `BLOCKED` for missing target runtime/data prerequisites that do not contradict the design.

## 11. Candidate and qualification handoff

The frozen product candidate remains `a9cb41ad9b1c6305de195f1a88b71ea098e582b7` unless implementation identifies a genuine product defect. Its existing content identity remains valid if recomputed cleanly under policy `mdstats.mvsel2-harden1-v3.candidate-identity.v1`.

Implementation shall issue a revision-2 Qualification Handoff that binds exact workplan revision/digest, candidate commit/content identity/policy, baseline commit, comparator policy/version, exact commands/cwds, evidence paths/classes/dependencies, retry modes, and allowed write paths. Product source mutation remains forbidden during qualification.

Implementation may end at `PREPARED_FOR_QUALIFICATION`; only qualification may produce gate evidence and only verification may decide `MERGE_READY` / `NOT_READY` / `DESIGN_REVISION_REQUIRED`.
