---
kind: implementation-workplan-review-reopen
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-FINAL-EXECUTION-EVIDENCE
parent_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_ACCEPTANCE_CLOSURE_REOPEN.md
governing_workplan_path: workplans/active/MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_REOPEN_WORKPLAN.md
protocol_version: 5.15.0
status: execution-evidence-required
created_date: 2026-09-07
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_executable_commit: 60cd50cd5e7a399257c1f52bca712b51bd751916
design_verdict: pass-frozen-architecture-unchanged
source_conformance_verdict: pass
acceptance_oracle_verdict: pass
implementation_review_verdict: no-pass-execution-evidence-only
precedence: This is a narrow continuation of the existing implementation-review lineage. It records closure of the previously missing A2 acceptance oracles and leaves only the already-required final executable regression/integration evidence open. It creates no new scientific, architectural, compatibility, or implementation requirement.
---

# MLFF MACE execution-semantics alignment — final execution-evidence reopen

## Verdict

**Software Design / frozen architecture: PASS.**
**Source implementation: PASS.**
**Task-specific acceptance oracle design: PASS.**
**Overall implementation closure: NO-PASS solely because required final executable evidence is not available for the exact candidate.**

Reviewed executable candidate: `60cd50cd5e7a399257c1f52bca712b51bd751916` (`Close MACE execution semantics acceptance oracles`), exactly one commit above the prior acceptance-closure review artifact.

No additional product-code repair is requested. Do not redesign P3/P4/P5, alter checkpoint persistence, add another currentness/state authority, or add more acceptance machinery merely because execution evidence is missing.

## A2 acceptance-oracle closure

The two previously open oracle claims are now closed in source:

1. **Serialized v3 -> v4 currentness:** the test constructs an internally coherent v3 method/CV/acceptance chain, serializes it through the existing `to_dict()` schemas, JSON round-trips it, reloads it through the current `from_dict()` readers, verifies the v3 lineage bindings, and then exercises the real final-production authorization owner against the current v4 method. The same owner admits the corrected v4 chain. No migration or parallel historical schema was added.
2. **Earlier native EMA representative through downstream consumers:** the real-MACE replay acceptance now produces multiple native checkpoints, deliberately makes the earlier checkpoint win target-only representative selection, executes held-out outer evaluation through the real P5 owner on that exact earlier checkpoint, and then consumes the same native checkpoint through qualification `member_provider`. The existing counterfactual still proves an explicit historical `live` request fails with or without the bounded numerical forward seam. This oracle would therefore fail if either P5 outer evaluation or P7 member access regressed to the retired hard-coded-live behavior.

These changes are test-only and preserve the previously accepted minimum-complexity product implementation at `bbaf10e...`.

## Sole remaining blocker — executed final acceptance evidence

Repository-visible evidence for executable commit `60cd50cd5e7a399257c1f52bca712b51bd751916` is still absent:

- no GitHub Actions workflow run is attached to the SHA;
- no GitHub check-run or commit-status result is attached to the SHA;
- the candidate commit changes only the two acceptance test files and does not add a run log/evidence record;
- this independent review environment cannot clone the repository because outbound DNS/network access is unavailable, so it cannot execute the suite locally as substitute evidence.

Protocol 5.15 requires the final affected regression/integration to execute. Source review and well-designed tests do not prove that those tests actually pass.

Execute and retain interpretable output for the final acceptance set already specified in `MLFF_MACE_EXECUTION_SEMANTICS_ALIGNMENT_IMPLEMENTATION_REVIEW_ACCEPTANCE_CLOSURE_REOPEN.md`, including the focused EMA/live and v3->v4 checks, real-MACE assembled P3/P5 cases under `mace-torch==0.3.16`, P5 scratch/naive/replay, TRAIN2 restart/boundary, historical DATA8/currentness, outer/qualification member-provider, wrapper/objective/export, and complete affected-surface/project checks. Required skips remain incomplete.

The evidence must identify the exact executable SHA, commands, dependency identity, and pass/fail/skip counts. CI is not mandatory; reproducible local command output or run logs are sufficient.

## Closure rule

Once that exact-candidate executable evidence is available and green with no required skips or affected failures, a fresh independent Software Design review may close/archive the governing MACE execution-semantics workplan and all review amendments together. No further source implementation cycle is required unless the execution itself exposes a genuine failure.
