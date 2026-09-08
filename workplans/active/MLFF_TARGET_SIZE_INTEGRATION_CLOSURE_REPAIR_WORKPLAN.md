---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: no-pass
review_round: implementation-review-5
reviewed_candidate_head: 69e5b54f0e71f73853b106d25f322829a7ee73dc
reviewed_executable_head: 5ae3fbc8acb166881e5cb880a6bb3c88baad21b0
reviewed_evidence_head: 69e5b54f0e71f73853b106d25f322829a7ee73dc
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Review-5 disposition — NO-PASS / final current-P2 and acceptance repair

Independent Software Design review of candidate `69e5b54f0e71f73853b106d25f322829a7ee73dc` accepts the main Round-5 compatibility correction. The substantive executable implementation is `5ae3fbc8acb166881e5cb880a6bb3c88baad21b0`; the candidate head records implementation evidence only.

The previous synthetic descendant-to-ancestor bridge is gone. Historical selected membership is now re-established from authenticated P1/P2 owners before P5 descendants are opened, the exact V1 policy/aggregate/definition/training-order digests are checked against the preserved P5A6 state, descendant access is poisoned during selection resolution, and the final-plan M3 corruption counterexample is checked against independently rebuilt P2 authority. This is the correct architecture direction and must be preserved.

Round 5 is nevertheless **NO-PASS** for three narrow blocking reasons:

1. the shared current P2 policy validator accidentally stopped rejecting negative optimizer seeds, violating a frozen scientific invariant and disagreeing with downstream execution validators;
2. the recorded final regression does not cover the actual affected surface of the modified P2 and post-selection owners, including several direct P5 R6-R9/assembled consumers explicitly required by the previous review;
3. the required semantic structural/currentness guard for historical V1 head/reducer fields is still only partially implemented: current source appears correct, but the test only checks spelling/absence of `_Legacy*` classes rather than proving those V1 wire fields cannot feed current-V3 binding ancestry.

No new blocker was found in the manual-selection, advisory-auto, ordered multi-size freeze, per-size CV/production, result-view, optimizer-normalization, or Part-VI documentation architecture.

---

## Tier-1 product invariants — unchanged

1. Manual `select-target-size N --horizon-cv HC --horizon H` is an operator decision over the prepared qualified ladder and performs no target-size TRAIN2/EVAL2 work.
2. `--auto` is advisory only: it emits a recommendation or typed no-recommendation and freezes nothing.
3. Every selected membership is exactly `T_N = pi_train[:N]` under authenticated P2 training-order authority.
4. P2 owns one canonical target-size scientific policy, one population/split, one `pi_train`, one `pi_eval`, and one nonempty ordered set of **unique nonnegative** optimizer seeds.
5. One prepared generation is shared by all selected sizes; manual selection does not hydrate unrelated P3/frame-array work.
6. The provisional/frozen design is one ordered unique-by-N collection; `cross-validate` is the sole atomic freeze authority for current designs.
7. Post-selection CV and fresh final production run independently for every frozen size with its exact membership and role horizon; there is no cross-size winner rule.
8. Derived target-size result JSON is presentation only and never scientific/currentness input.
9. The exact accepted P5A6 current-generation workspace remains a supported unchanged-reopen boundary under its native historical schemas; historical children validate parent -> child and may not manufacture an upstream authority.
10. Production-scale GPU/CuEq/LAMMPS qualification remains deferred to the established final-release/user-machine stage.

## Frozen high-level architecture — preserve

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered current selected-size collection;
- separate manual and automatic selection branches converging only at the proposal merge owner;
- minimum authenticated P2 dependency for manual selection;
- full P3 numerical dependency only for the automatic diagnostic that actually screens candidates;
- pure committed-state result-view projection and strict diagnostic exposure currentness;
- current per-size ancestry `P1/P2/P4 -> selected binding -> method/CV -> final production`;
- supported P5A6 ancestry follows the same parent -> child direction under native historical wire identities, with no preload migration or rewrite.

---

## Accepted Round-5 surfaces — preserve

### A1 — Synthetic compatibility bridge removal — PASS

Preserve the deletion of `_LegacyEvaluationOrder`, `_LegacyExperimentDefinition`, `_LegacyTargetSizeAggregate`, and descendant-derived selected/P2 reconstruction. The current `_load_p5a6_selected_training_context()` direction is acceptable insofar as it rebuilds P1/P2 from native upstream inputs, authenticates state digests, and derives `T_N` from `definition.training_order.candidate_membership(N)` before opening P5 descendants.

### A2 — Independent compatibility counterexamples — PASS

Preserve the existing tests that:

- poison P5 post-selection store/pointer access while resolving the historical selected context;
- delete post-selection descendants and still recover the same selected membership/binding from P1/P2;
- corrupt a disposable final-production plan's M3 lineage and require `resolve_current_final_production_plan()` to reject it against independently rebuilt P2 M3 authority;
- run the standalone P5A6 -> current / current -> current / V5-V6 reject-before-reuse qualification driver.

### A3 — Current V1 binding isolation in production source — structurally plausible, acceptance incomplete

The reviewed source keeps `legacy_v1_campaign_state_revision`, `legacy_v1_execution_head_digest`, and `legacy_v1_reducer_state_digest` in the historical V1 binding payload, while ordinary `target_size_binding()` for current V3 does not populate them. Preserve that source direction. The remaining blocker is proof strength, not a request to redesign this binding.

### A4 — Previously accepted current runtime and documentation — PASS

Preserve the narrow manual P2 loader, ordered proposal/freeze semantics, pure committed-state selection view, real auto->manual poisoned-P3 acceptance, current multi-size post-selection behavior, Part-VI architecture wording, and regenerated documentation derivatives.

---

## Blocking R15 — restore the current P2 optimizer-seed invariant

### Finding

Round 5 changed `ResolvedTargetSizePolicy.__post_init__()` from rejecting

```text
not integer OR seed < 0
```

to rejecting only non-integers, while leaving the error message unchanged: `optimizer_seeds must be one nonempty ordered set of nonnegative integers.`

That is a current scientific-semantic regression. The frozen P2 authority requires exactly one nonempty ordered set of **unique nonnegative** optimizer seeds. Downstream target-size evidence classes still reject a negative `optimizer_seed`, so the candidate can now construct/hash a policy that later execution cannot legally realize.

Historical P5A6 V1 wire reproduction does not justify this relaxation: schema identity changes whether `terminal_decision_policy` is serialized, not the domain of optimizer seeds.

### Required repair

1. Restore the `seed < 0` rejection in the existing `ResolvedTargetSizePolicy` validator. Apply the same nonnegative domain to V1 and V2 unless exact authenticated P5A6 evidence proves a different historical seed domain; do not invent such an exception speculatively.
2. Keep one validator. Do not add a schema-specific wrapper, second seed validator, migration, or compatibility adapter.
3. Add direct regression to the existing P2 statistical-authority test proving negative seeds are rejected by both direct policy construction/replacement and config resolution, while ordered nonnegative seeds continue to affect policy identity exactly as before.
4. Preserve all current V2 defaults and payload semantics.
5. Historical V1 schema construction must remain internal compatibility machinery; ordinary current callers/configuration must continue to resolve V2 by default. Do not add a user-facing schema selector or broaden supported-history semantics while fixing this bug.

---

## Blocking R16 — final affected regression is incomplete for the Round-5 executable surface

### Finding

Round 5 materially changed both:

- `mdstats/training_data/campaign_post_selection.py`; and
- `mdstats/training_data/target_size_experiment.py`.

The recorded evidence covers the compatibility tests, a selected P5a-P5f subset, two P7 suites, and documentation, but it does **not** include several direct consumers that the previous review explicitly named, including:

- `tests/test_mlff_target_size_p5_r6_guards.py`;
- `tests/test_mlff_target_size_p5_r6_cutover_authorization.py`;
- `tests/test_mlff_target_size_p5_r7_guards.py`;
- `tests/test_mlff_target_size_p5_r8_guards.py`;
- `tests/test_mlff_target_size_p5_r9_guards.py`;
- `tests/test_mlff_target_size_p5g_assembled_integration.py`;
- `tests/test_mlff_target_size_p5h_publication_decision.py`;
- `tests/test_mlff_mace_execution_semantics_assembled.py`.

The newly modified P2 policy owner also directly affects `tests/test_mlff_target_size_statistical_authorities.py` and target-size execution/coordinator/candidate consumers. Those were not recorded in the Round-5 closure evidence. Therefore the statement that all affected suites executed is not established for the reviewed executable candidate.

### Required evidence

After R15/R17 are final:

1. Re-derive callers/references from the final tree. Use Serena when available for semantic reference discovery and cross-check dynamic/configuration surfaces textually; its absence does not relax the required scope.
2. Run the full bounded P5 affected family, preferably `pytest -q tests/test_mlff_target_size_p5*.py`, rather than another hand-selected early-P5 subset.
3. Run `tests/test_mlff_mace_execution_semantics_assembled.py` and any other directly discovered post-selection runtime/qualification consumers.
4. Run the P2 statistical-authority suite and directly affected target-size execution/coordinator/candidate suites, including the new negative-seed counterexample.
5. Re-run the compatibility tests, standalone three-phase compatibility driver, and the previously accepted current target-size/multi-size/result-view integration slice because the final patch still shares policy/state/binding types with those paths.
6. Re-run the downstream P7/qualification suites that consume `build_post_selection_context()` / `resolve_current_final_production_*`.
7. Re-run documentation checks and `python -m compileall mdstats tests qualification/p6-p5a6-compat`.
8. Record exact commands/results and every skip. A skip is acceptable only when it is genuinely the already-deferred production GPU/CuEq/LAMMPS qualification or another independently established non-applicable check.

Do not substitute a production-scale qualification run for this functional regression. GPU qualification remains deferred.

---

## Blocking R17 — complete the semantic historical-binding architecture guard

### Finding

The previous review required the structural/currentness oracle to distinguish:

```text
historical V1 head/reducer fields retained solely to reproduce/authenticate V1 wire identity
```

from

```text
head/reducer fields participating in current-V3 selected binding ancestry
```

The current test still mainly proves that the literal old dataclass names are absent and that no `_Legacy*` classes remain. That would not catch a future refactor that copied `legacy_v1_execution_head_digest` or `legacy_v1_reducer_state_digest` into current `target_size_binding()` while keeping those spellings.

The reviewed production source appears correct today: current `target_size_binding()` does not populate the V1 fields. This blocker is an acceptance-oracle gap, not evidence that the source currently violates the architecture.

### Required repair

Strengthen the existing structural/currentness test rather than adding a new scanner or framework:

1. Prove a normal current-V3 `target_size_binding()` produces schema V3 with all `legacy_v1_*` fields unset.
2. Prove a historical V1 binding round-trips the historical head/reducer fields only in the V1 payload and reproduces its historical digest.
3. Add a focused AST/source assertion that the V1 head/reducer state fields cannot flow into current `target_size_binding()` / current-V3 construction. Keep this bounded to the existing owner; do not create repository-wide compatibility machinery.
4. Keep the existing negative assertion that no synthetic `_Legacy*` experiment/aggregate classes remain.
5. Reconcile the stale comment in `campaign_target_size_state.py` that says a pre-rework terminal-selected row is structurally incapable of authorizing post-selection work. The supported P5A6 exception now reopens **historical descendants** through native historical identity; clarify that such a row still cannot create a current-V3 freeze/new current binding. This is documentation of the implemented compatibility boundary, not a semantic expansion.

---

## Final implementation sequence

### Stage 1 — one-owner P2 invariant repair

Restore nonnegative seed validation in the existing `ResolvedTargetSizePolicy` owner and add the direct P2 regression. Do not otherwise alter P2 mathematics, ordering, qualification, or current V2 identity.

### Stage 2 — finish the existing architecture oracle

Strengthen the current V1/V3 binding guard and correct the stale state-module compatibility comment. Do not redesign the accepted historical reconstruction path.

### Stage 3 — final affected-surface closure

Re-derive the final P2/P5/P7 affected surface, run all bounded functional regression/integration and repository-required checks, record exact executable/candidate identities, and request independent Software Design review.

## Minimum final command set

The final evidence must include at least:

```text
python -m compileall mdstats tests qualification/p6-p5a6-compat
python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
pytest -q tests/test_mlff_target_size_statistical_authorities.py
pytest -q tests/test_mlff_target_size_p6_p5a6_compatibility.py
pytest -q tests/test_mlff_target_size_p5*.py
pytest -q tests/test_mlff_mace_execution_semantics_assembled.py
pytest -q tests/test_mlff_p7_post_production_qualification.py tests/test_mlff_p7_r11_repair_acceptance.py
```

plus the directly affected target-size execution/current multi-size/result-view suites found by final reference re-derivation and the repository-required documentation checks.

## Simplicity stop condition

Stop and return to Design if this repair starts adding a second P2 policy class, a historical policy registry, another compatibility database/sidecar, descendant-to-ancestor reconstruction, a current-state migration, or a new general scanner. The expected repair is smaller than Round 5: restore one lost validation predicate, strengthen existing tests, reconcile one source comment, and run the complete affected regression.

## Review tooling note

Serena/Semgrep are appropriate to the semantic-reference and structural-family questions, but they were not executable in the present web review environment and the local container could not resolve GitHub. This review therefore used GitHub source/commit/reference inspection and independently challenged the recorded evidence. No independent local pytest/Semgrep/Serena execution is claimed.
