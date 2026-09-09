---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 6.0.0
protocol_migrated_from: 5.16.0
protocol_adoption_date: 2026-09-09
protocol_adoption_basis: explicit stakeholder instruction during this independent implementation review
status: reopened
created_date: 2026-09-08
last_design_closure_review_date: 2026-09-09
reviewed_candidate_head: 13859556cd4d472837a9e171c2be32e59d5e6d82
reviewed_candidate_tree: bafa9cc93a38cef7f1c07ea668bc244d111cdcd8
reviewed_implementation_commit: 13859556cd4d472837a9e171c2be32e59d5e6d82
implementation_review_verdict: no-pass
open_blockers: final executable acceptance evidence only
precedence: This file is the current binding implementation-review amendment to MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md. It supersedes its own earlier wording and, by explicit stakeholder adoption, supersedes the parent's Protocol 5.16 control-plane binding for all review and remaining closeout work from 2026-09-09 forward. Non-conflicting task-specific scientific/product invariants, accepted D3 architecture, non-goals, preservation requirements, and acceptance claims in the parent remain binding under Protocol 6.
---

# MLFF downstream integration closure — Protocol 6 implementation review

## 0. Verdict

**NO-PASS / REOPENED — evidence closure only.**

Independent Software Design review under SSDP Protocol 6.0 reviewed executable candidate `13859556cd4d472837a9e171c2be32e59d5e6d82` against the parent workplan, the prior binding review amendment, the current MLFF architecture/P5/P7 authorities, and the final implementation delta.

The two source-level blockers from the previous review are now closed:

1. P5 continuation is no longer reusable independently of the materialization/execution authority that produced it.
2. The absolute/tilde/config-relative foundation path matrix now carries the exact campaign-produced request through the real dependency-facing `MacePostSelectionTrainer` owner.

No new blocking source drift was found in the affected P5/P7/replay/TRAIN2 surfaces. The candidate nevertheless cannot receive an overall PASS because no final affected pytest/static/integration execution evidence is available for this executable candidate. GitHub exposes no check runs or commit statuses for `13859556...`, and this review environment cannot clone/run the repository. Protocol 6 explicitly treats an unexecuted required check as incomplete acceptance rather than a source-review proxy pass.

**Do not change product code merely to answer this review.** The next implementation action is to execute and retain the required acceptance evidence on the exact executable candidate. If those runs expose an actual failure, repair the earliest owning D4/D3 surface and rerun the invalidated evidence; otherwise return directly for closure review.

There is **no Serious Challenge** to accepted D1, D2, or D3 authority on current evidence.

---

## 1. Protocol 6 adoption and authority reconciliation

The stakeholder explicitly adopted SSDP Protocol `6.0.0` for this review and all subsequent review/closeout work. This is a deliberate major-version migration, not a silent reinterpretation.

The migration does **not** change MLFF scientific or numerical authority:

- **D1 — scientific formulation unchanged.** Target-size meaning, frozen multi-size experiment semantics, CV scientific role, foundation scientific identity, replay training versus independent TRUE_DFT admissibility, production meaning, and qualification meaning are unchanged.
- **D2 — algorithm/numerical method unchanged.** Candidate selection mathematics, CV acceptance predicates, objective/loss semantics, epoch horizons, precision/dtype policy, numerical tolerances, ranking/reduction behavior, and checkpoint evaluation convention are unchanged by this repair.
- **D3 — affected architecture under review.** Configured-path ownership, foundation locator/content separation, P5 materialization/recovery/currentness, TRAIN2 continuation ancestry, P5 publication ownership, P7 consumer boundaries, and storage/restart integrity are the material architectural concerns.
- **D4 — candidate realization.** The current Python implementation and its tests realize those D3 constraints.

Historical parent-workplan terms map without semantic loss:

```text
Protocol 5 product/scientific invariants
    -> applicable D1/D2 invariants + governed engineering constraints
Protocol 5 Frozen high-level architecture
    -> accepted/current or cycle-scoped D3 architecture
Protocol 5 Tier-2 machinery
    -> delegated D4 realization
```

The parent workplan body therefore remains task-specific authority where non-conflicting, while Protocol 6 governs review, challenge, evidence, routing, and closeout from this review onward.

---

## 2. Accepted implementation closure — preserve

### 2.1 Joint materialization/continuation recovery is now fail-closed

The candidate preserves the shared TRAIN2 continuation validator, then couples any surviving continuation to completed authenticated P5 materialization before resume, full-horizon trainer bypass, or EVAL2 use.

Accepted behavior:

- durable continuation + absent materialization -> typed failure, preserve state, no rebuild;
- durable continuation + incomplete materialization publication -> typed failure, preserve state, no rebuild;
- corrupt/foreign materialization -> typed failure and diagnostic preservation;
- current valid materialization + matching continuation -> reusable;
- faithful pre-fix locator-only materialization with no durable progress -> bounded same-workspace reconciliation remains possible;
- partial/corrupt checkpoint residue is not treated as resumable by file presence.

### 2.2 Continuation is bound to the canonical MACE execution authority

The candidate extracts `_build_post_selection_mace_execution_authority()` as the shared authority construction used by both `MacePostSelectionTrainer` launch and continuation reconciliation. Recovery validates the persisted MACE execution evidence against:

- materialization MACE config digest;
- current method/optimizer execution semantics;
- exact target frame UID-set digest;
- replay frame UID-set digest when replay is active;
- evidence schema/version/content digest.

`train2_runtime` additionally requires the companion and summary copies of MACE execution evidence to agree before continuation is accepted.

This closes the previous split-authority defect without adding a new durable identity, restart record, pointer, registry, state machine, or lock layer.

### 2.3 Foreign sibling continuation counterfactual now targets the real defect

The new real-owner test constructs two P5 sibling runs whose `Train2RuntimePlan` values are equal but whose run/materialization ancestry differs, copies one sibling's authenticated full-horizon continuation beneath the other sibling, and requires rejection before EVAL2 or fold publication.

This is a valid proxy-proof counterfactual for the prior blocker: the P5 recovery owner remains live and only expensive MACE arithmetic is substituted below it.

### 2.4 Full-horizon continuation optimization is now admissible

The full-horizon fast path still avoids a zero-epoch trainer invocation, but only after continuation, completed materialization, and persisted execution authority have jointly authenticated. The optimization therefore no longer bypasses the exact ancestry check that protects fold/production scientific provenance.

### 2.5 Foundation dependency-facing path oracle is closed

For each supported foundation spelling (`absolute`, `~/...`, config-relative) from a foreign CWD, the test now:

1. obtains the request from real campaign/P5 orchestration;
2. passes that exact request through real `MacePostSelectionTrainer`;
3. bounds only subprocess/MACE work below the trainer;
4. verifies dependency-facing `mace_run_config.yaml["foundation_model"]` equals the current canonical locator;
5. verifies immutable internal P5 configuration still contains no `foundation_model` locator.

This closes the previous proxy-proof gap.

### 2.6 Previously accepted downstream invariants remain intact

Source review found no regression in:

- canonical configured-path interpretation for affected campaign paths;
- foundation content/head/family identity with locator-only filesystem path;
- path-free replay source/split scientific lineage and single-source adapter repair;
- canonical replay-set path forms and byte-identical source relocation semantics;
- complete per-size CV verdict accumulation and collection-wide production barrier;
- P5 final-production publication/currentness ownership and P7 consumer-only role;
- P7 explicit reference-root canonicalization;
- architecture documentation already reconciled in the prior implementation round;
- deferred full GPU/CuEq/LAMMPS qualification boundary.

---

## 3. Protocol 6 Challenge Pass and active-simplicity disposition

### 3.1 No Serious Challenge

The accepted scientific/numerical/architectural contract remains coherent and realizable. The previous failure was D3/D4 recovery ancestry nonconformance, not evidence that D1 or D2 is wrong and not evidence that the accepted P5/P7 ownership model is contradictory.

### 3.2 Complexity challenge

The latest implementation adds a stateless continuation/materialization compatibility validation in `campaign_post_selection_runtime.py`, but it simultaneously removes duplicated launch-authority construction by extracting one canonical `_build_post_selection_mace_execution_authority()` owner and reusing it for both launch and restart reconciliation.

On current source evidence this is an acceptable D4 realization rather than a new competing authority:

- no new persistent recovery state exists;
- no new compatibility database/registry/pointer/state machine exists;
- no second scientific or run identity exists;
- the new recovery check derives from existing materialization + TRAIN2 + MACE execution evidence;
- the actual dependency-facing authority construction is shared rather than reimplemented independently.

Therefore the prior active-simplicity requirement is considered **source-conformant**. Do not add another recovery layer. If executable evidence later exposes another recurrence around this mechanism, reassess the shared recovery owner under Protocol 6 convergence/stabilization rules rather than patching another special case.

### 3.3 Shared `record_mace_execution_evidence` change

The candidate allows `record_mace_execution_evidence()` to receive already-resolved evidence by dropping the supplied `evidence_digest` before recomputing the canonical digest. P5 recovery independently authenticates the persisted digest before this call, and the existing ordinary producer constructs unresolved evidence. No current blocking integrity regression was established from source inspection. Treat this as part of the affected regression surface, not as an additional speculative code requirement.

---

## 4. ONLY OPEN BLOCKER E1 — final executable acceptance evidence is missing

GitHub reports no check runs/status checks for executable candidate:

```text
13859556cd4d472837a9e171c2be32e59d5e6d82
```

This review environment also cannot execute the repository locally. Source inspection of strong tests is not equivalent to running them.

### 4.1 Required focused/affected suites

Execute at minimum on the exact executable candidate:

```bash
pytest -q \
  tests/test_mlff_downstream_integration_closure.py \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
  tests/test_mlff_target_size_p5_r9_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_mace_execution_semantics_assembled.py

pytest -q \
  tests/test_mlff_target_size_multi_selection.py \
  tests/test_mlff_target_size_multi_size_integration.py \
  tests/test_mlff_campaign_assembled_lifecycle.py \
  tests/test_mlff_p7_post_production_qualification.py
```

Also execute the currently applicable affected subsets for:

- TRAIN2 continuation/restart/content authentication;
- P5 storage and run-activity-lease integration;
- single-source + legacy replay unification/lineage/path behavior;
- final production/publication/currentness/reclosure;
- configured fast Python lint/type/static checks supported by the repository;
- any broader P5/P7/campaign/storage/replay regression identified by final affected-surface re-derivation.

If final impact cannot be bounded confidently, run the broader available MLFF/campaign suite instead of declaring unexamined paths unaffected.

### 4.2 Evidence identity

Record the exact executable commit/tree and commands/results. A later workplan-only or documentation-only review commit does not invalidate tests tied to the unchanged executable tree, but any subsequent executable change does invalidate affected final regression/integration and requires rerun.

### 4.3 No unnecessary implementation round

If all required checks pass on `13859556...`, **do not make another executable code change**. Return directly for Software Design closure review with the execution evidence.

If a required check fails:

1. classify the earliest affected D1/D2/D3/D4 owner under Protocol 6;
2. repair only the genuine cause;
3. prefer removal/rewiring/consolidation over another wrapper/fallback/state layer;
4. rerun all evidence invalidated by that executable change.

Full production-scale GPU/CuEq/LAMMPS qualification remains deferred to final release qualification and is not part of E1.

---

## 5. Re-review PASS criteria

Software Design may close this parent workplan when all of the following hold on one exact executable candidate:

```text
[x] Protocol 6 review authority explicitly adopted and D1/D2/D3/D4 ownership reconciled
[x] no active Serious Challenge to D1/D2/D3 authority
[x] canonical foundation/replay/P7 configured-path behavior remains source-conformant
[x] foundation locator/content-identity separation remains source-conformant
[x] replay source/split lineage remains path-free
[x] multi-size CV completeness and collection-wide production barrier remain source-conformant
[x] P5 publication/currentness and P7 consumer-only boundary remain source-conformant
[x] corrupt/foreign completed materialization fails typed and is preserved by the implemented owner
[x] durable continuation cannot rebuild absent/incomplete materialization beneath itself
[x] continuation reuse is reconciled with the current materialization execution authority
[x] foreign sibling continuation with equal Train2RuntimePlan is rejected before EVAL2/publication by the implemented owner
[x] full-horizon fast path follows joint authentication
[x] current valid continuation resume/reclosure path is represented by real-owner acceptance tests
[x] foundation path forms reach real MacePostSelectionTrainer dependency projection
[x] no new durable migration/compatibility/recovery state machinery was introduced
[ ] final required pytest/static/integration evidence actually executed and passed on the exact executable candidate
```

The unchecked item is the **only remaining blocker** on current review evidence.

---

## 6. Snapshot-complete handoff and closeout

The current governing handoff is:

1. `MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md` for still-binding task-specific scientific/product/D3 constraints;
2. this amendment as the current review state and Protocol 6 migration authority;
3. current MLFF architecture/P5/P7 authorities referenced by the parent;
4. executable candidate `13859556cd4d472837a9e171c2be32e59d5e6d82` for the implementation under review.

From this amendment forward, review/verification/closeout is governed by **SSDP Protocol 6.0.0**. The parent's historical `protocol_version: 5.16.0` header is superseded for ongoing control-plane purposes by this explicit migration; its non-conflicting task-specific semantics remain carried forward.

After E1 is supplied and independent Software Design review passes, archive/retire the completed parent and amendment according to repository policy and reconcile `workplans/active/README.md`. Closeout must not mutate executable product behavior.
