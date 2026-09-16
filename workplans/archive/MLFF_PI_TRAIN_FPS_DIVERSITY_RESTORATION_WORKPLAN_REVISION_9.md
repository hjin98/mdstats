---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 9
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_assembled_candidate: c76a53476596137aa34ec47bb68b7d1ab4bfe706
reviewed_implementation_commit: af666839188d62d7cd86bbd341c523f49f045840
highest_affected_domain: D4
challenge_state: D4_NO_PASS_REPAIR_REQUIRED
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` MVSEL2-chain restoration — Revision 9 independent D4 review and repair closure

## 0. Composition and verdict

Revision 9 composes immutable Revisions 5-8 and the accepted D1/D2/D3 authority. It changes only the D4 acceptance state and the bounded repair required to close this implementation. No D1, D2, or D3 redesign is authorized by this revision.

Independent assembled-candidate review of `c76a53476596137aa34ec47bb68b7d1ab4bfe706` is **NO-PASS**. The restored ownership/currentness architecture is substantially conformant, but three blocking issues remain:

1. **B1 — REPAIR2 semantic drift:** D4 adds a replacement-frontier early exit that is absent from accepted D2 and can suppress a D2-admissible strict objective improvement.
2. **B2 — representative current-scale performance evidence missing:** the accepted D3/Revision-8 gate requires representative current-scale complete prepare/order/publication/reload performance in this cycle; the recorded performance checkpoint is explicitly a small 32-frame fixture and explicitly does not qualify native scaling.
3. **B3 — affected normative/static validation remains red:** the implementation handoff records `60 passed, 8 failures` in the CLI/spec/help/documentation closure batch. Baseline equality does not close affected-test/documentation impact when the failures are acknowledged stale expectations for the now-current D3/schema/topology/provenance.

These are closure blockers. They do not justify a new selector, compatibility router, wrapper, second currentness owner, new scheduler, semantic migration layer, or altered D1/D2 thresholds.

## 1. Accepted authority and architectural findings

The following remain accepted and must not be reopened by convenience:

- D1 `docs/methods/mlff_target_training_order_scientific_method.md`;
- D2 `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`;
- D3 `docs/arch_manuals/mlff_training_data/45_target_training_order.md` plus the already reconciled canonical MLFF architecture chapters;
- one exact `P_train`, one complete `pi_train`, exact nested `T_N = pi_train[:N]`;
- `prepare` as the sole live-input/build/publication orchestration owner;
- prepared-generation/CampaignStore as the sole completed-generation currentness/adoption owner;
- one `TargetCoverageReference`, one canonical obligation authority, one shared FEAS1/NEIGHBOR1 relation, one MVIDX representation, one MVSEL2/REPAIR2 order owner, and independent MVQUAL;
- same optimized exact selector continuation through all of `P_train`; no UID/scalar/alternate-selector suffix;
- production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

Source inspection found no blocking duplicate-selector/currentness architecture. `target_order/preparation.py` reconstructs selector state from the repaired prefix after accepted repair, continues the same engine to the complete order, publishes transactionally, and keeps subordinate build/checkpoint state below prepared-generation adoption. Those surfaces remain subject to the already required regression evidence but do not require topology expansion.

## 2. B1 — remove the extra REPAIR2 proposal gate

### 2.1 Defect

Accepted D2 §9.2 evaluates the replacement frontier through hard gain, bottleneck coverage, total coverage, hypothetical balance, representative gain, diversity, and UID. D2 §9.3 then admits a swap only when family coverage does not regress and the exact global objective

```text
J = (D_hard, min C_m, sum C_m, U_rep, -sum_g b_g^2)
```

strictly improves.

Current D4 `mdstats/training_data/target_order/repair.py::_build_frontier` adds:

```text
possible = hard_pending or max(totals[c] for c in candidates) > tolerance
```

and `build_repair_plan` evaluates proposals only when `frontier.proposal_possible` is true.

When hard deficit is already zero and every surviving candidate contributes zero *new* coverage, removal/replacement can still leave all family coverage unchanged while strictly improving `U_rep`, or, when earlier objective components are equal, the exact balance component. The extra gate therefore prunes states that accepted D2 requires the later frontier/objective logic to evaluate.

This is a D4 concretization defect, not a D2 ambiguity. The implementation handoff itself records the shortcut as carrier behavior not stated by D2; historical maturity does not override accepted current authority.

### 2.2 Required minimal repair

Prefer deletion over compensation:

1. remove `_Frontier.proposal_possible`;
2. remove the `possible = ...` calculation and its historical-shortcut comment;
3. when a shortlist and frontier exist, call the existing `_best_proposal` unconditionally;
4. preserve the existing D2 frontier filters, coverage non-regression check, `strictly_better` objective gate, deterministic proposal reduction, repair limits, and rank inheritance;
5. do **not** add a special-case replacement path, alternate repair mode, compatibility flag, or D2 rewrite to legalize the shortcut.

### 2.3 Required falsification

Add focused real-owner repair tests that isolate the missing state:

- hard deficit is zero;
- all candidate total new-coverage gains are zero within the accepted tolerance;
- removing the eligible shell member preserves family coverage;
- one replacement strictly improves a later accepted objective component and must be accepted;
- a control case with no strict `J` improvement must make no swap;
- worker/completion-order variation must produce the same repair trace.

At minimum exercise a strict `U_rep` improvement. If a balance-only fixture is straightforward without synthetic authority changes, include it as an additional witness; it is not required to invent new test machinery.

## 3. B2 — close representative current-scale complete-path performance

### 3.1 Evidence gap

Revision 8 criterion 52 and canonical D3 require representative current-scale evidence over the complete prepare critical path. The D4 handoff records a 32-frame/6-family performance checkpoint (`3.37 s`, roughly `208852 KiB` peak RSS, small MVIDX/checkpoint artifacts) and explicitly states that native scaling is **not qualified** and effective runtime width was one. A separate 332-frame assembled functional fixture proves routing/integration but is not recorded as the required representative current-scale performance/resource qualification.

Small-fixture exactness is valid correctness evidence; it is not evidence for the explicit current-scale performance gate.

### 3.2 Required repair/evidence

Do not create a new benchmark framework. Reuse the smallest existing current campaign/data substrate that is already representative of the accepted target-order workload. Record the exact fixture/configuration identity so that “representative” is reviewable rather than asserted.

For one complete real-owner `prepare` run and authenticated reuse/reload, record the Revision-8/D3 §16.5 metrics:

- `|P_train|`, configured sizes, family/witness/edge counts;
- coverage-reference wall/RSS;
- one shared FEAS1/NEIGHBOR1 wall/RSS/I/O and evidence that normal path performs one geometry construction;
- MVIDX adoption/inversion wall/RSS/scratch/final artifact bytes;
- configured-prefix MVSEL/REPAIR wall and evaluated sparse edges;
- Phase-A -> Phase-B transition and lazy refresh/certification rate;
- native preflight probe widths/timings and selected effective width under the accepted `1.05` / `0.05` policy;
- post-final-repair reconstruction cost;
- suffix ranks/wall/edges to `|P_train|` where `|P_train| > Nmax_current`;
- complete-order wall/RSS/I/O;
- checkpoint write/read/recovery cost, including interruption/resume strictly beyond `Nmax_current` when applicable;
- peak mapped FDs and final/scratch disk footprint;
- immutable publication, fresh-process reload, and downstream no-scientific-rebuild routing.

The complete order, repair trace, MVQUAL, and public identities must remain exact under worker/reference/native and fresh/resumed variations already required by D3.

If the representative run exposes a material performance defect, first prove the accepted optimized lazy/native/OOC execution closure is active. Repair by simplifying/rewiring the existing execution path. Do not weaken D1/D2, truncate the complete order, append a UID suffix, tune scientific tolerances, or add a fallback selector. Reopen D3 only if the accepted ownership/resource topology itself cannot realize the current envelope.

Native/OpenMP retention remains governed by accepted D3/Revision-8 policy. Do not invent a new activation threshold merely to obtain a pass; equally, do not preserve unused native complexity by adding compensating machinery if representative evidence shows it has no execution role.

## 4. B3 — reconcile the eight affected normative/static failures

The D4 handoff reports eight architecture/manual static failures as baseline-equal stale expectations for older schema/revision/topology/provenance. The accepted target-order D3 and user-facing source documentation are now current. Final workplan closure cannot carry knowingly stale affected assertions merely because they predate the last product mutation.

Required closure:

1. rerun the exact CLI/spec/help/documentation closure batch and record the eight failing node IDs and assertion mismatches;
2. for each failure, trace the expectation to current canonical D3/spec/manual authority;
3. where the assertion is stale, replace/remove the obsolete expectation and assert the current schema/revision/topology/provenance instead;
4. if any failure instead exposes a current-document/source inconsistency, repair the owning source document rather than weakening the test;
5. do not xfail, skip, blanket-filter, or use “baseline equal” as the acceptance mechanism;
6. regenerate generated PDF siblings only after their source Markdown is correct;
7. rerun the batch to zero unresolved failures.

This is impact reconciliation, not a request to broaden the product patch.

## 5. Evidence applicability boundary

`tests/conftest.py` intentionally substitutes the target-order owner for most `test_mlff_*` downstream suites unless `@pytest.mark.real_target_order` is present. Therefore the reported 334-pass and 289-pass downstream batches remain useful for below-claim P2/P3/publication/post-selection compatibility, but they are **not** primary evidence for the restored target-order owner itself.

No immediate fixture redesign is required. For Revision-9 closure, target-order claims must be grounded in:

- the dedicated `real_target_order` suite;
- the focused B1 regression;
- the representative current-scale assembled real-owner qualification required by B2;
- source/identity/currentness inspection and the affected static/documentation closure required by B3.

Do not inflate acceptance by counting substituted downstream tests as owner-level falsification.

## 6. Re-review gate

The next independent review may PASS only when all of the following are true:

1. B1 shortcut is deleted and focused zero-new-coverage/later-objective repair falsification passes;
2. full existing real-owner selector/repair/restart/OOC/native/package tests remain green;
3. representative current-scale complete-path metrics required by D3/Revision 8 are recorded and show the accepted optimized path is active without semantic weakening;
4. the eight affected documentation/static failures are enumerated, reconciled to current authority, and the closure batch has no unresolved failures;
5. no new selector, fallback, wrapper, currentness store, semantic migration path, or cleanup owner was introduced;
6. the assembled candidate still preserves one complete `pi_train`, repaired-prefix cold reconstruction, same-engine suffix completion, independent MVQUAL, and prepared-generation/CampaignStore ownership;
7. any newly exposed blocker is repaired at its owning layer or routed upward under the existing challenge rules.

Until that evidence is present, keep this workplan **active / D4 repair required**. Do not close or archive it.
