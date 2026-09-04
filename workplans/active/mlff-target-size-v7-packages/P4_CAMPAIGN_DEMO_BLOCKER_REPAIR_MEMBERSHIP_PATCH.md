---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-P4-CAMPAIGN-DEMO-BLOCKER-REPAIR-MEMBERSHIP-PATCH
parent_workplan_id: CODE-MLFF-P4-CAMPAIGN-DEMO-BLOCKER-REPAIR
protocol_version: 5.14.0
status: active
baseline_observed: 973e633d95f086f32a477ff495cb1d909c9e174c
created_date: 2026-09-04
---

# P4 Campaign Demonstration Blocker Repair — Candidate Membership Projection Patch

## Amendment scope and verdict

This amendment extends `P4_CAMPAIGN_DEMO_BLOCKER_REPAIR.md` with one newly demonstrated production blocker found during the real `select-target-size` campaign demonstration. It has precedence only for the affected P2/P3 candidate-projection surface. All unrelated requirements, Frozen architecture, and acceptance obligations in the parent emergency workplan remain unchanged.

**Design verdict: PASS — immediate implementation repair.**

The failure is a bounded P3 implementation nonconformance exposed by P4 production data. It does **not** invalidate the accepted target-size architecture, the P2 `P_train`/`pi_train` ownership split, or the P3 common-preparation design.

Observed production failure:

```text
Boundary 1: executing 16 surviving (N, optimizer seed) cells.
...
TrainingDataInputError:
Candidate membership is not an exact ordered projection of the common membership.
```

The VASP `VelocityReconstructionWarning` and `InterruptedXmlWarning` messages preceding the exception are not the owner of this failure. The exception occurs before the first candidate is materialized or MACE training begins.

---

## 1. Root cause

The accepted authority chain intentionally contains **two different order concepts**:

```text
P2 split owner
  -> P_train                     # exact authorized training membership

P2 training-order owner
  -> pi_train                    # separate deterministic priority order over P_train
  -> T_N = pi_train[:N]          # exact candidate membership/order

P3 common preparation
  -> fit once over exact P_train

P3 candidate projection
  -> select frozen common fitted values for exact T_N
```

Current implementation constructs these authorities correctly up to the P3 projection boundary:

- `split_target_size_population()` derives `training_frame_uids` from the canonical population order after removing `M3`;
- `build_target_training_order()` deliberately constructs a potentially different condition-balanced deterministic `pi_train` over those same training frames;
- `definition.candidate_membership(N)` correctly returns the exact `pi_train[:N]` prefix;
- `build_target_size_common_preparation()` correctly binds `common_membership` to exact `aggregate.split.training_frame_uids` / `P_train`.

The defect is inside `project_target_size_candidate_preparation()` in `mdstats/training_data/target_size_execution/common.py`. After correctly deriving exact `T_N` from P2 and verifying that every member belongs to the common preparation, it additionally computes each candidate UID's position in `common.common_membership` and rejects unless those positions are monotonically increasing.

That extra condition means:

```text
T_N must be a subsequence of P_train's stored tuple order
```

but the accepted architecture requires only:

```text
set(T_N) subset of set(P_train)
T_N order == exact P2 pi_train prefix order
```

For realistic multi-condition data, `pi_train` is condition-balanced and therefore normally differs from the canonical/split storage order of `P_train`. The production LTA dataset exposes exactly this valid case.

This is why synthetic P3 tests could remain green while the real campaign failed: their fixture did not force a material `P_train` order versus `pi_train` order disagreement at candidate projection.

---

## 2. Frozen product and architecture invariants

The following remain Frozen and must not be changed to make the test pass:

1. `P_train` is the exact P2 training-side membership produced by the one accepted `U_size -> P_train + M3` split.
2. `pi_train` is the one separate deterministic P2 target-training order over `P_train`.
3. Every candidate is exactly:

   ```text
   T_N = pi_train[:N]
   ```

4. `definition.candidate_membership(N)` and its P2 prefix digest remain the sole candidate-membership authority.
5. P3 common fitted quantities are computed once over exact `P_train`, not once per candidate and not over a reordered substitute authority.
6. P3 candidate preparation is selection/projection only: it selects the already-fitted common values belonging to `T_N`; it does not refit, renormalize, rebalance, repair, or reorder P2 membership.
7. Candidate trajectory/materialization must preserve the exact P2 `T_N` membership identity and order.
8. Common per-frame fitted weights may remain stored in their existing canonical UID order because they are selected by frame UID; storage order of the weight table is not the scientific candidate order.
9. Existing candidate qualification, funnel/reducer state, seed ordering, evaluation ladder, restart authentication, and P4 CampaignStore ownership remain unchanged.

---

## 3. Required implementation repair

### 3.1 Remove the accidental `P_train` relative-order gate

Repair `project_target_size_candidate_preparation()` at its owning layer.

Required end state:

```text
membership = exact definition.candidate_membership(N)
verify exact P2 membership digest
verify every T_N UID is present in common P_train / common fitted state
project the frozen common fitted values by UID
preserve T_N itself exactly as the P2 prefix
```

The projector must **not** require the sequence of `T_N` UIDs to be monotonically ordered by their positions in `common.common_membership`.

The preferred implementation is reduction: remove the positional/subsequence check and keep only the genuine authority/containment checks already required by P2/P3. Do not add an adapter, alternate order field, translated membership, reconciliation pass, or fallback mode.

### 3.2 Preserve exact candidate ordering downstream

The repair must not replace exact P2 candidate order with any of the following:

- `sorted(T_N)`;
- `P_train`-relative subsequence order;
- frame-catalog order;
- materialization-file order chosen independently of P2;
- a newly persisted candidate order.

`TargetSizeCandidatePreparation.candidate_membership`, candidate trajectory identity, and target-train materialization continue to carry the exact `definition.candidate_membership(N)` tuple.

Projected weights remain exact common fitted weights selected by UID. Their existing canonical storage order may remain unchanged because `TargetSizeCandidatePreparation` already validates weight coverage independently from candidate membership ordering and exposes a UID-keyed weight table to materialization.

### 3.3 Do not alter P2 or common-preparation authority to satisfy the faulty guard

The following are forbidden repairs:

- reorder `split.training_frame_uids` to equal `pi_train`;
- change `build_target_size_common_preparation()` so `common_membership` becomes `pi_train` rather than exact `P_train`;
- change `build_target_training_order()` so it preserves P_train storage order;
- sort `definition.candidate_membership(N)` before projection;
- weaken or change `target_training_prefix_digest()`;
- construct an N-specific common preparation;
- catch this `TrainingDataInputError` and retry through an alternate membership path.

Each of those either destroys an accepted authority distinction or adds machinery around an invalid Tier-2 constraint.

---

## 4. Focused bug reproducer and regression closure

### 4.1 Required direct reproducer

Add a P3-A focused test whose P2 fixture **guarantees** that:

```text
set(definition.training_order.frame_uids)
    == set(aggregate.split.training_frame_uids)

but

definition.training_order.frame_uids
    != aggregate.split.training_frame_uids
```

Prefer a small deterministic multi-condition fixture that forces condition-balanced `pi_train` to differ from canonical P_train storage order. Do not make the test depend on accidental hash/UID ordering.

For at least one qualified `N`, prove:

- `project_target_size_candidate_preparation()` succeeds;
- `projection.candidate_membership == definition.candidate_membership(N)` exactly, including order;
- candidate membership is a subset of `common.common_membership` as a set;
- every projected frame weight is byte/value-identical to the corresponding common fitted weight;
- no refitting or normalization occurs.

This reproducer must fail on the currently broken positional/subsequence guard.

### 4.2 Preserve negative authority checks

Retain or add focused negatives proving that projection still rejects:

- a common preparation bound to another experiment definition;
- an unqualified candidate size;
- candidate membership that is not contained in the bound common P_train if such a malformed object is constructed through the lowest legitimate validation seam.

Do not weaken exact P2 prefix digest authentication in order to remove the false order check.

### 4.3 P3 materialization boundary

Exercise the real candidate trajectory/materialization path with the order-divergent fixture and prove:

- trajectory membership equals exact P2 `T_N`;
- target-train artifact membership equals exact trajectory/P2 `T_N`;
- membership digest remains the P2 prefix digest;
- projected common weights attach to the correct frames by UID;
- no candidate-specific common refit occurs.

Expensive MACE numerical training may remain substituted below the P3 semantic owner; the real P3 trajectory/projection/materialization owners must execute.

### 4.4 P4 assembled selection boundary

Add or extend one current-runtime P4 `select-target-size` integration fixture so its real P2 `P_train` and `pi_train` orders differ. The test must reach at least first-boundary candidate construction through:

```text
execute_current_select_target_size
  -> build_screen_context
  -> _execute_candidate_cell
  -> build_target_size_candidate_trajectory
  -> project_target_size_candidate_preparation
```

The test must not patch `project_target_size_candidate_preparation()`, `build_target_size_candidate_trajectory()`, or P2 candidate membership to desired values.

A cheap trainer/inference double remains allowed below the candidate execution owner so no GPU/long training is required.

---

## 5. Affected surface and validation sequence

Expected primary executable surface:

- `mdstats/training_data/target_size_execution/common.py` — remove/narrow the invalid relative-order requirement;
- `tests/test_mlff_target_size_execution_p3a.py` — direct order-divergence projection reproducer;
- `tests/test_mlff_target_size_execution_p3b.py` or nearest existing real materialization test — exact-order downstream proof;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py` / `tests/test_mlff_target_size_p4g_assembled_integration.py` or the nearest existing current-runtime screen integration — assembled production-path proof.

Do not modify P2 order/split implementation unless new evidence independently proves a P2 defect. The current observed failure does not do so.

Run, in cheapest high-signal order:

```text
1. focused P3-A order-divergence reproducer
2. complete affected P3-A projection/common-preparation regression
3. affected P3-B trajectory/materialization regression
4. P2 statistical-authority regression covering P_train, pi_train and exact T_N identity
5. current P4 select-target-size assembled regression with divergent orders
6. repository-required Python/package/import/static checks for the changed surface
```

Then resume the real campaign `select-target-size` from the current generation. The failed invocation reached no successful first candidate completion, so no scientific boundary evidence from that failed cell may be fabricated or marked complete. Existing authenticated prior state, if any, remains governed by normal P3/P4 reconciliation.

---

## 6. Relation to the earlier post-DATA4 latency finding

The previously observed silent post-DATA4 rebuild/serial execution issue is **not required to fix this membership exception** and must not be mixed into this patch merely because both appear in `select-target-size` startup. The current emergency objective is to remove this correctness blocker first.

A later performance repair may separately restore the already-existing worker/progress plumbing if still needed, provided it preserves identical P1/P2/P3 identities. Do not combine that optimization with candidate membership semantics unless profiling or implementation coupling makes the combination genuinely necessary.

---

## 7. Reopen triggers

Reopen only the smallest affected Design surface if implementation demonstrates one of these facts:

- some genuinely consumed training mathematics depends on common P_train **tuple order**, rather than membership plus UID-bound fitted values, such that projecting exact P2 `T_N` cannot be correct without changing the common-preparation architecture;
- target-train artifact ordering is independently proven to be a scientific trajectory variable that must intentionally differ from exact P2 `pi_train` prefix order;
- exact P2 `T_N` is not actually a subset of accepted P_train on a valid aggregate, indicating a P2 split/order lineage defect rather than the current false P3 gate;
- removing the positional check exposes a second genuine authority ambiguity rather than an ordinary downstream implementation bug.

Absent such evidence, do not reopen P2/P3 architecture.

---

## Implementation handoff

**PASS — ready for immediate implementation.**

The minimal justified repair is to remove the false relative-order constraint at the P3 projection owner while preserving exact P2 candidate order, P_train common fitting, UID-bound frozen fitted values, and real assembled P4 acceptance. This removes machinery rather than adding a compatibility path and directly addresses the demonstrated production blocker.
