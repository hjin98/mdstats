---
kind: implementation-review-closure
workplan_id: MLFF-MACE-EXECUTION-SEMANTICS-ALIGNMENT-REOPEN
protocol_version: 5.15.0
status: PASS
completed_date: 2026-09-07
reviewed_executable_commit: 60cd50cd5e7a399257c1f52bca712b51bd751916
execution_evidence_commit: c6d09318795b9ca0087d0bee0f057a11af6ede02
reviewed_branch: rework/mlff-target-size-normalization-practical-ceiling
---

# MLFF MACE execution-semantics alignment — final independent closure

## Verdict

**PASS / close and archive the MACE execution-semantics repair lineage.**

The frozen scientific method and high-level P3/P4/P5 architecture remain unchanged. The implementation now realizes the method actually executed by pinned `mace-torch==0.3.16`, and the previously reopened source, state-representation, compatibility/currentness, storage-reduction, and acceptance-oracle findings are closed.

## Candidate identity

- Exact executable candidate: `60cd50cd5e7a399257c1f52bca712b51bd751916`.
- Exact executable tree: `554f72d68982f7e322b7cfff5668c6e3d37e0d36`.
- The execution-evidence checkout was the review-only child `9a5dddc322e875e0bd2ac08d220cbcd440f93b88`; candidate-bound diff checks confirmed no product source, test, build, or runtime difference from `60cd50cd...`.
- The evidence record was committed at `c6d09318795b9ca0087d0bee0f057a11af6ede02`; commits after the executable candidate affected workplan/evidence documentation only.

## Functional closure

The final evidence executed the affected regression/integration set under:

- Python 3.11.15;
- PyTorch 2.13.0+cu126;
- `mace-torch==0.3.16`;
- CPU execution with thread caps and bounded pytest concurrency.

Recorded required affected partitions total **474 passed, 0 failed, 0 skipped**. This includes:

- optimizer/currentness/P5-R6 and P3A4 acceptance;
- P5 R7-R11, P5a-P5h, final production, restart, and publication;
- historical DATA8/MACE compatibility;
- MACE wrapper/executable configuration/objective/export weighting;
- real non-divisible P3 and EMA/live preservation;
- TRAIN2 checkpoint/boundary/restart/continuation;
- selected P7 provider/authority consumers;
- the real pinned-MACE assembled scratch, naive-fine-tuning, and replay cases.

The real replay case produces multiple native EMA checkpoints, selects an earlier checkpoint, executes held-out outer evaluation through that representation, consumes the same frozen checkpoint through qualification `member_provider`, and rejects explicit historical `live` requests with and without the bounded numerical forward seam.

## Independent evidence challenge

The execution record also reported five diagnostic failures outside the accepted affected regression. They do not block this repair:

1. Three campaign-warning CLI tests are unchanged from the governing pre-implementation commit `4635b89fd9edd1a475a4c1873263f13faefc5fd6`, and their `campaign_cli` owner is likewise outside the task diff. Their failures concern stale command/parser assumptions, not MACE execution semantics.
2. Two TRAIN2 specification tests are also unchanged from the governing pre-implementation commit. Their asserted architecture-manual literals (`TRAIN2A is implemented ...` and `## Gate TRAIN2B`) were already absent at the pre-task baseline, so the failures are pre-existing documentation-test drift rather than regressions introduced by this repair.

Two task-modified static test modules were not named in the recorded 474-test partitions. This does not leave an uncovered behavioral claim:

- `tests/test_mlff_target_size_corrected_identity_cutover.py` changed only the expected whole-package structural absence of the retired `"loss": "universal"` emission. Independent closure inspection confirmed no such emission remains in current `mdstats/training_data/data8_bundle.py`; the other schema/currentness/loss-family claims are covered by the executed compatibility/currentness/objective suites.
- `tests/test_mlff_data9a2_specification.py` added only the documentation-conformance requirement that the DATA9A2 spec state parsed loss is `stress`; independent closure inspection confirmed that current specification text explicitly binds parsed `stress` to native `WeightedEnergyForcesStressLoss`.

No proxy-proof acceptance gap remains.

## Source and architecture closure

Accepted end state:

- native MACE `WeightedEnergyForcesStressLoss` remains the one loss owner;
- replay preserves explicit LR/EMA and zero target-duplication threshold;
- target-size normalized training preserves complete non-divisible target exposure and ceil update geometry;
- P5 ordinary reconstruction uses the correct `Default` namespace/E0 authority;
- one latest TRAIN2 continuation companion remains; historical checkpoints use raw MACE bytes plus immutable per-epoch JSON boundaries rather than duplicated full companions;
- EMA-enabled P5 checkpoint evaluation uses the policy-derived EMA representation, while EMA-disabled execution uses live state;
- bounded numerical forward overrides cannot weaken native checkpoint provenance/state admission;
- v3 P5 evidence remains readable history but cannot authorize current v4 execution;
- P7 qualification consumes the same policy-derived checkpoint state;
- no second trainer, loss engine, checkpoint/state registry, currentness system, or compatibility hierarchy was introduced.

The final Tier-2 realization is sufficiently simple relative to the frozen architecture. No further repair or architecture-GC change is justified by this review.

## Deferred boundary

This closure is CPU functional/regression acceptance. Full production/GPU qualification remains deliberately deferred to the final release package under the established project policy; it is not a blocker for this workplan.

## Disposition

Archive the governing workplan and all implementation-review amendments together. Preserve the final execution evidence and this closure record under `audits/` as permanent correctness evidence.
