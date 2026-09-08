---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: no-pass
review_round: implementation-review-4
reviewed_candidate_head: eef79ed3a0829d4d385c881456ce40c30c58e5bb
reviewed_executable_head: bb4befc4158049873f186acb28de83ba26da08c8
reviewed_evidence_head: d910becd2c054955078824f7d30dde20e39ad47b
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Review-4 disposition — NO-PASS / compatibility architecture reopened

Independent Software Design review of candidate `eef79ed3a0829d4d385c881456ce40c30c58e5bb` finds that the Round-4 Part-VI documentation repair is correct, and the recovered exact P5A6 workspace is valuable evidence. The substantive executable implementation is `bb4befc4158049873f186acb28de83ba26da08c8`; `d910becd2c054955078824f7d30dde20e39ad47b` records implementation evidence and `eef79ed3a0829d4d385c881456ce40c30c58e5bb` regenerates documentation artifacts.

Round 4 is nevertheless **NO-PASS**. Recovering the real P5A6 workspace exposed a real compatibility failure, but the implementation repaired it by adding a large prerework reconstruction path inside the current post-selection owner. That path synthesizes upstream target-size/P2-like authority from persisted P5 descendants and broadens all prerework-v1 state into a new product-semantic branch. This contradicts the frozen dependency direction, the current module contract, and the original P6 compatibility authority, which explicitly required a Design reopen rather than an unplanned compatibility bridge when valid P5A6 current-generation state could not reopen after cleanup.

The central current-v3/multi-size scientific implementation remains accepted. The reopened surface is only historical P5A6 compatibility and the acceptance needed to prove it.

---

## Tier-1 product invariants — unchanged

1. Manual `select-target-size N --horizon-cv HC --horizon H` is an operator decision over the prepared qualified ladder and performs no target-size TRAIN2/EVAL2 work.
2. `--auto` is advisory only: the screen emits a recommendation or typed no-recommendation and freezes nothing.
3. Every selected membership is exactly `T_N = pi_train[:N]` under the authenticated P2 training order.
4. One prepared generation is shared by all selected sizes; manual selection does not hydrate unrelated P3/frame-array work.
5. The provisional/frozen design is one ordered unique-by-N collection; `cross-validate` is the sole atomic freeze authority for current designs.
6. Post-selection CV and fresh final production run independently for every frozen size with its exact membership and role horizon; there is no cross-size winner rule.
7. Derived target-size result JSON is presentation only and never scientific/currentness input.
8. Historical compatibility is append-only and schema-authentic. The exact accepted P5A6 current-generation workspace remains a supported unchanged-reopen boundary until Design explicitly changes that product support decision.
9. A supported historical child may authenticate against its historical parent schema, but a descendant can never manufacture or redefine an upstream scientific authority merely to make itself current.
10. Current normative documentation describes one coherent ordered multi-size architecture and current CLI.

## Frozen high-level architecture — current runtime surfaces remain unchanged

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered current selected-size collection;
- separate manual and automatic selection control branches converging only at the proposal merge owner;
- minimum authenticated P2 dependency for manual selection;
- full P3 numerical dependency only for the automatic diagnostic that genuinely screens candidates;
- pure committed-state selection-view projection and strict diagnostic exposure currentness;
- current per-size P5 ancestry flows P1/P2/P4 -> selected binding -> method/CV -> final production, never backward;
- production GPU/CuEq/LAMMPS qualification remains deferred to the final-release/user-machine stage.

### Bounded compatibility-architecture reopen for exact P5A6

The recovered fixture proves that the prior assumption “the existing current readers are already sufficient” was false. The compatibility realization is therefore reopened, but the product requirement is not.

The repaired high-level compatibility design is now frozen as follows:

1. Exact P5A6 persisted bytes remain authoritative under their **native historical schemas**. Current code may retain/restore the minimum native deserializers/currentness comparators needed to authenticate those bytes.
2. The historical selected `N/T` ancestry must be established from its historical P4/P2 authority **before** P5 CV/final-production descendants are consulted.
3. Every compatibility edge remains parent -> child: historical selection/binding -> method/CV plan -> CV acceptance -> final plan -> completion/publication.
4. No P5 descendant may be used to construct a fake P2 experiment definition, evaluation order, target-size aggregate, selected membership authority, or other ancestor that is then used to validate that same descendant.
5. The support boundary is the exact accepted P5A6 current-generation contract, not a blanket “all prerework-v1 workspaces are current” rule.
6. No preload rewrite/migration is allowed. If native historical bytes cannot be authenticated through a minimal reader/currentness restoration, return this compatibility surface to Design rather than synthesizing an equivalent current state.
7. A historical decoder is allowed only when it directly reads the historical wire contract. It must not become a second current scientific authority or a bridge that fabricates current-v3 objects.

This is the only Frozen architecture changed by Review 4.

---

## Accepted implementation surfaces — preserve

### A1 — Current-v3 target-size/multi-size runtime — PASS

The previously accepted manual/P2 dependency reduction, ordered proposal/freeze, per-size CV/production behavior, selection-view purity, auto->manual owner-boundary tests, current `provisional_entries`/`frozen_entries`, and scalar-v2 normalization remain accepted. Do not churn them to solve the P5A6 problem.

### A2 — Part VI normative documentation — PASS

`docs/arch_manuals/mlff_training_data/60_execution_performance.md` now correctly states:

```text
optional paired-seed diagnostic (recommendation or typed no-recommendation)
-> operator-owned provisional ordered collection
-> cross-validate atomic collection freeze
-> per-frozen-size CV and fresh final production
```

Its candidate funnel now ends in a recommendation/no-recommendation, and fold-local wording is explicitly per frozen `T_N`. The strengthened existing doc assertions and regenerated assembled/PDF derivatives are accepted.

### A3 — Historical artifact recovery — useful evidence, not compatibility PASS by itself

Round 4 reports that the original P5A6-created workspace was recovered locally and authenticated against the committed fixture identity/content/database snapshots. That is the correct evidence artifact and should be preserved unchanged. The exact historical commit remains unavailable through the public remote, but the compatibility product boundary is the authenticated workspace bytes, not Git reachability by itself.

The recovered fixture does **not** make the new compatibility interpretation correct automatically. The real-owner path still has to preserve authority direction and native semantics.

---

## Blocking R12 — remove the synthetic prerework reconstruction bridge

### Finding

Round 4 adds a general branch in `load_current_selected_training_contexts()`:

```text
if revision.state.is_prerework_schema:
    return _load_legacy_prerework_training_contexts(...)
```

and adds `_LegacyEvaluationOrder`, `_LegacyExperimentDefinition`, `_LegacyTargetSizeAggregate`, plus a large `_load_legacy_prerework_training_contexts()` reconstruction path.

That path does not merely deserialize old bytes. It creates new ancestor-like state from descendants:

- selected membership is reconstructed from the first persisted CV fold;
- the historical P2/evaluation authority is represented by synthetic `_Legacy*` objects rather than the real historical owner;
- `target_size_policy` is resolved from the **current config** and placed into the synthetic historical definition without first proving it is the historical policy named by the campaign-state digest;
- M3 membership/digest is taken from the stored final-production plan and one final-production materialization, then inserted into the synthetic definition;
- `_LegacyEvaluationOrder.membership_digest()` returns the same digest for every requested evaluation size and `_LegacyExperimentDefinition.evaluation_membership()` returns the same M3 membership for every size;
- the branch activates for any `is_prerework_schema` state, broader than the exact P5A6 supported-history boundary.

This is a second product-semantic path and reverses the accepted authority graph. It also contradicts the owning module's own contract that post-selection is not an authority and that selected membership is re-established from authenticated P2/P4 ancestry.

The original P6 compatibility amendment is explicit: if valid P5A6 current-generation state cannot reopen because a required current-generation decoder/currentness contract was removed, trigger Design reopen; do **not** add an unplanned compatibility bridge or seed reconstructed current state.

### Required repair

Prefer deletion and restoration over another patch on this bridge:

1. Remove `_LegacyEvaluationOrder`, `_LegacyExperimentDefinition`, `_LegacyTargetSizeAggregate`, and `_load_legacy_prerework_training_contexts()`.
2. Remove the generic `is_prerework_schema -> synthetic selected context` routing from `load_current_selected_training_contexts()`.
3. Revert other compatibility-only runtime machinery that exists solely to support that reconstruction, unless the exact historical wire bytes independently require a native decoder.
4. Use the recovered exact P5A6 source/workspace and accepted P6 history to identify the **specific historical schema/decoder/current-pointer/currentness contracts** that destructive cleanup or later selection redesign stopped honoring. Restore the smallest native reader/currentness behavior at those owning boundaries.
5. `PostSelectionBinding.v1` may be deserialized under its historical wire schema when needed to reproduce/authenticate existing bytes. Legacy head/reducer fields may survive only as historical-v1 wire data needed for that digest/currentness check; they must not be renamed into a new current scientific ancestry or flow into current-v3 bindings.
6. Establish historical P4 selected `N`, exact membership identity, and its actual upstream P2/training-order authority **without opening P5 CV/final descendants first**. If the exact P5A6 persisted inputs/source cannot supply that parent authority through a minimal native reader/rebuild, stop and return to Design; do not derive it from a CV plan or final run.
7. Validate historical P5 descendants directly against independently loaded parents. Child records may contribute their own payload and stored parent digest, never the expected parent value.
8. Scope the compatibility acceptance to the exact P5A6 current-generation contract represented by the authenticated fixture/native schemas. Do not make arbitrary prerework-v1 state a blanket supported current-generation path.
9. Do not change current-v3 multi-size semantics or add a migration, compatibility database, synthetic fixture, sidecar state, wrapper hierarchy, or current-state rewrite.

The preferred outcome is less code than `bb4bef...`: native historical deserialization/currentness at existing owners, not a parallel reconstruction subsystem.

---

## Blocking R13 — restore independent compatibility/currentness oracles

### Finding 1: P4 selection acceptance was weakened

The compatibility driver previously required a frozen selection. Round 4 instead treats `revision.state.auto_diagnostic.recommended_target_size` / membership digest as the P4 terminal selection and lets the new P5 reconstruction path manufacture the selected context later.

That does not establish the P6 Rev-4 claim “authenticate P4 terminal N_selected/T_selected” through the actual historical selection owner. It conflates the current product meaning of `auto_diagnostic` (recommendation only) with historical P5A6 `terminal_selected` semantics.

### Finding 2: final-plan M3 validation is circular

`_load_legacy_prerework_training_contexts()` reads the stored `FinalProductionPlan`, takes its `m3_membership_digest`, reads M3 frames from a final-production materialization, and installs both into the synthetic `_LegacyExperimentDefinition`. Later `resolve_current_final_production_plan()` calls `validate_final_production_plan()`, whose `frozen_m3_development_evidence()` obtains the expected M3 membership/digest from that synthetic definition.

The descendant therefore supplies the “ancestor” used to validate itself. A mutually self-consistent wrong descendant can survive this oracle; the real P2 M3 authority is not what rejects it.

### Finding 3: existing structural test became lexical rather than semantic

The current structural test says P5 must not use the diagnostic execution-head/reducer as its ancestry and checks only for exact dataclass field names. Round 4 adds semantically equivalent `legacy_v1_execution_head_digest` / `legacy_v1_reducer_state_digest` fields, so the test remains green by spelling. Historical v1 wire data may legitimately contain those values, but the oracle must distinguish “retained solely to authenticate v1 bytes” from “used as current P5 ancestry”; name avoidance is not sufficient evidence.

### Required acceptance repair

After R12 removes the synthetic bridge:

1. Exact preserved-fixture selected-context acceptance must establish historical `N/T` through the real/native historical parent boundary **with P5 descendant access poisoned**. In the test, make reads of CV/final-plan records fail if they occur before selected `N/T` currentness is established.
2. Then open the real persisted v1 binding/method/CV/acceptance/final records through current production readers and prove each child binds the independently authenticated parent digest.
3. Add a negative/counterfactual on a disposable copy of the recovered fixture (never mutate the preserved source fixture): corrupt or replace a final-plan M3 lineage while leaving the historical P2 ancestor unchanged and prove current final-plan resolution rejects it. The expected M3 must come from P2, not the final plan/materialization being checked.
4. Add an analogous selected-membership counterexample if the repair touches the historical selected-context resolver: a CV descendant must never be able to define a different selected membership that becomes current.
5. Refine the existing structural/currentness guard semantically: current v3 bindings must not depend on diagnostic head/reducer; v1 wire fields may be retained only inside v1 deserialization/authentication and must not feed current-v3 binding construction or synthetic upstream authority.
6. Restore the mandatory three-phase qualification driver to a real-owner oracle:
   - P5A6 unchanged workspace -> current native historical selection/binding/P5 reopen PASS;
   - current -> current restart PASS;
   - retired V5/V6 reject-before-reuse PASS.
7. Evidence prose must state exactly what compatibility mechanism exists. Do not claim “zero compatibility adapters” while a dedicated reconstruction branch exists.

---

## Blocking R14 — complete affected regression for the actual Round-4 executable surface

### Finding

Round 4 changed central production owners by roughly 400 lines in:

- `mdstats/training_data/campaign_post_selection.py`;
- `mdstats/training_data/campaign_post_selection_runtime.py`.

The recorded 200-test rerun is the earlier ten-module target-size/result-view set. It does not cover many direct P5/P7 consumers of the changed owners. Repository reference inspection identifies, among others:

- `tests/test_mlff_target_size_p5_r6_guards.py`;
- `tests/test_mlff_target_size_p5_r6_cutover_authorization.py`;
- `tests/test_mlff_target_size_p5_r7_guards.py`;
- `tests/test_mlff_target_size_p5_r8_guards.py`;
- `tests/test_mlff_target_size_p5_r9_guards.py`;
- `tests/test_mlff_target_size_p5e_production_and_restart.py`;
- `tests/test_mlff_target_size_p5g_assembled_integration.py`;
- `tests/test_mlff_target_size_p5h_publication_decision.py`;
- `tests/test_mlff_mace_execution_semantics_assembled.py`;
- P7/qualification consumers that call `build_post_selection_context()` or final-production currentness.

Passing the exact fixture plus the prior target-size suite does not establish this broader affected surface.

### Required repair/evidence

After the compatibility implementation is simplified and final:

1. Re-derive callers/consumers from the **final** tree using Serena/reference search when available, with text/config/dynamic cross-checks.
2. Run the focused compatibility tests and mandatory standalone driver.
3. Run the complete P5 affected regression. A practical bounded minimum is the relevant `test_mlff_target_size_p5*.py` suite plus directly affected assembled/runtime tests; broaden further if final reference analysis finds additional consumers.
4. Include downstream P7/qualification tests whose currentness/provider paths call `build_post_selection_context()` / `resolve_current_final_production_*`.
5. Retain the already required current target-size/multi-size/result-view suite because the compatibility reader shares persistence/state types.
6. Run documentation tests, repository-required fast static checks, and:

```text
python -m compileall mdstats tests qualification/p6-p5a6-compat
python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
```

7. Record one resolvable final executable SHA and one final candidate SHA. Later evidence/PDF-only children may be named separately.

Full production-scale GPU/CuEq/LAMMPS qualification remains deferred and must not be added to this repair cycle.

---

## Tooling note

Serena and Semgrep are appropriate for the semantic-reference and structural-family questions in this review. They are not executable in the present web review environment, so repository API source/reference inspection and the repository's existing AST/behavioral tests were used as fallback. Their absence does not relax the final affected-surface or structural requirements.

When available in Implementation, Serena should be used to trace the recovered historical decoder/currentness owners and final callers. Semgrep may be used as a one-off structural cross-check for the synthetic `_Legacy*` family/descendant-to-ancestor reconstruction, but do not add a permanent second scanner when existing tests can encode the durable semantic rule more directly.

---

## Implementation sequence

### Stage 1 — Subtract the Round-4 bridge

Remove the synthetic prerework reconstruction classes/path and generic prerework dispatch. Confirm current-v3 behavior remains unchanged.

### Stage 2 — Restore the minimum native P5A6 read/currentness contract

Using the recovered exact P5A6 source/workspace and P6 authority, restore only the native historical decoders/currentness comparisons needed to authenticate the existing parent -> child chain. Do not fabricate current P2/P4 objects from P5 descendants.

### Stage 3 — Adversarial compatibility acceptance

Run the exact preserved fixture plus the poisoned-descendant selected-context test and descendant-corruption tests. The compatibility evidence must fail when an upstream authority or child-parent edge is wrong.

### Stage 4 — Final affected-surface closure

Re-derive the final P5/P7/currentness affected surface, run complete bounded regression/integration and repository-required checks, record exact candidate identity, then request another independent Software Design review.

## Simplicity stop condition

If the next implementation still needs a fake experiment definition/evaluation order/aggregate, reconstructs parent authority from CV/final descendants, introduces another historical state database/sidecar, or adds another broad prerework runtime branch, stop. That is evidence the repair is again solving a Tier-2 compatibility mechanism instead of restoring the supported native historical contract.
