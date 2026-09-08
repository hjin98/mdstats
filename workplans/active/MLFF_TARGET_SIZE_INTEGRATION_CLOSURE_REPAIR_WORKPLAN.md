---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: no-pass
review_round: implementation-review-1
reviewed_candidate_head: 2199bbd4bffc3a950a6b63b010c48e32c829c5b3
reviewed_executable_head: 07bdd51f6857eb052aa05e7e23a1ec89a53e0e6c
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## 0. Independent implementation review - NO-PASS / reopened

The implementation was independently reviewed at candidate head `2199bbd4bffc3a950a6b63b010c48e32c829c5b3`. Its executable source is the parent implementation head `07bdd51f6857eb052aa05e7e23a1ec89a53e0e6c`; the child commit regenerates affected documentation PDFs only.

The core scientific architecture remains intact. No new defect was found in exact target membership, ordered multi-size selection/freeze, CV/production scientific identities, optimizer normalization, foundation handling, or the explicit manual-versus-`--auto` branch decision. The review nevertheless remains **NO-PASS** because integration closure is incomplete.

### Review finding F1 - R1 dependency reduction is structurally correct; preserve it

The manual command now authenticates the current manifest and a narrow P2 experiment definition, validates the campaign-bound aggregate/definition identity, and commits through the existing proposal owner. It does not need the normalized frame payload, frame-array index, screen context, TRAIN2, or EVAL2. This is the intended dependency reduction and must not be replaced by a cache, wrapper, or second persisted definition.

This finding is **not a repair request**. Keep the narrow loader unless later executable evidence exposes a real correctness defect.

### Review finding F2 - blocking: the new selection view depends on an older non-authoritative view

`write_selection_target_size_result_view()` currently reads the existing `target-size-state.json`, and `build_selection_target_size_result_view()` copies diagnostic fields from that old file when only generation and execution attempt match. The copied fields include reducer status, active candidates, completed boundaries, recommendation identity, and terminal reason codes. The newly written file then carries the current campaign revision/sequence.

That violates the frozen presentation boundary. A derived view is deletable/rebuildable presentation, not an input authority. A stale, corrupted, or manually edited old view can therefore be carried forward into a fresh-looking view after a manual selection even though committed campaign state says something else. This also adds a solution-created state dependency solely to avoid strict P3 revalidation.

**Required repair:** remove the old-view input/copy path. Selection-only rendering must be a pure projection of the committed `TargetSizeCampaignRevision` state. If `state.auto_diagnostic` exists, it may project the terminal summary fields that are actually carried and authenticated there. P3-only progress fields that are not present in committed state may simply be absent from a selection-only refresh. Keep strict `expose_current_target_size_auto_diagnostic()` / `write_current_target_size_result_view()` validation unchanged for commands that explicitly expose, claim, or consume diagnostic evidence.

Do not add a new view cache, freshness flag, sidecar, or synchronized diagnostic summary. The correct repair is subtraction of the derived-file dependency.

**Required counterexample test:** after a real completed auto diagnostic, corrupt or forge diagnostic fields in `target-size-state.json` while leaving generation/attempt plausible, then make a manual selection. The rewritten view must derive from authoritative state; forged old-view fields must not survive or be stamped with the new revision.

### Review finding F3 - blocking: R2 real-owner acceptance is split across proxies

The implementation has one real auto-then-manual steering test that proves the diagnostic state survives, and a separate poison-exposure test that directly fabricates `TargetSizeAutoDiagnostic` state. Neither test alone proves the required claim: **a real completed auto diagnostic followed by a manual selection performs zero new strict P3 diagnostic validation/training/evaluation work while preserving the real diagnostic evidence**.

**Required repair to acceptance only:** run the real bounded auto diagnostic through the production owner using the existing accepted numerical seams; after it reaches `DIAGNOSTIC_COMPLETE`, poison the strict diagnostic exposure/P3/full-frame owners and execute a manual selection through the real public runtime. Assert the manual tuple is committed, the prior `auto_diagnostic` record is byte/identity-equivalent, and no poisoned owner is reached. Reuse the existing test harness; do not create a second diagnostic harness.

### Review finding F4 - R3 implementation is structurally correct but mandatory compatibility execution is missing

The historical baseline producer correctly retains scalar `revision.state.frozen` under baseline code. The current reopen side now reads the normalized one-entry `frozen_entries` collection. This is the intended native-schema split and should be preserved.

However the required real compatibility qualification has no recorded execution evidence on this candidate. The repository test/CI evidence available to review contains only the documentation-PDF workflow. A skipped developer test is not equivalent evidence.

**Required execution:** from the candidate repository root run:

```bash
python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
```

The command must PASS all three built-in cases: P5A6 -> current authenticated compatibility, current -> current restart/reuse, and retired V5/V6 reject-before-reuse. A failure is implementation evidence to repair at the existing owner; do not wrap or migrate historical state.

### Review finding F5 - blocking acceptance weakness: the scalar-state structural oracle is syntax-narrow

The existing AST guard now scans both `mdstats/training_data` and top-level `qualification`, and it correctly exempts the historical producer. That closes the escaped path dimension. But its positive oracle recognizes only direct `<expr>.state.frozen|proposal` and variables literally named `state`; it can miss the same retired access after a trivial local alias such as `campaign = revision.state; campaign.frozen`.

Because this guard is the acceptance mechanism for an already escaped structural defect family, strengthen the **existing** guard rather than adding Semgrep infrastructure or a second scanner. At minimum its known-positive cases must include a simple local alias to campaign state, while known-negative per-size uses such as `context.frozen` remain allowed. Scope the historical exemption to the intended baseline producer path/function rather than making an arbitrary same-named function globally invisible if practical.

This is an oracle repair, not authorization for application-code machinery.

### Review finding F6 - blocking: R5 current documentation remains internally contradictory

The documentation pass corrected many visible scalar statements, but current normative sources still contradict the frozen ordered multi-size architecture.

Required corrections include at least:

1. `docs/specs/training_data/mlff_data_stage_plan_spec.md` - normative Principle 10 still describes **the selected target size** and both horizons as one protocol-global scalar freeze. Reconcile the fitted-domain diagrams and identity wording wherever singular phrasing means one campaign-global selection rather than an explicitly per-size binding.
2. `docs/arch_manuals/mlff_training_data_dependency_graph.json` - the top-level description still says **one selected binding**; `POST_SELECTION_CV_ACCEPTANCE` and `FRESH_FINAL_PRODUCTION` summaries still describe one exact `T_selected`. Make the collection/per-size dependency explicit.
3. root `README.md` - the current architecture diagram still says fresh final production on **the complete `T_selected`**, and current qualification prose still speaks of **the selected target size** where the product can contain multiple selected sizes.
4. `docs/guides/mlff_final_gpu1_workstation_runbook.md` and the current tracked runbook/spec derivative - the current handoff diagram still ends in fresh final production on singular `T_selected` after describing an ordered collection.
5. Re-scan the authoritative architecture chapter sources, assembled Markdown, current CLI/specification sources, and generated tracked derivatives for the same semantic contradiction. Singular language remains valid only where the text is explicitly describing one per-size binding/run, not the campaign-global selected design.

Strengthen the existing documentation tests so known stale scalar sentences/summaries fail. Positive token presence such as `post-selection cross-validation on the frozen collection` is insufficient when contradictory current text can remain in the same document. Prefer exact semantic assertions against the affected current owners rather than a blanket ban on the token `T_selected`, because per-size use is legitimate.

Regenerate tracked Markdown/PDF derivatives from their authoritative sources after the source corrections; do not hand-patch only generated output.

### Review finding F7 - blocking: final functional acceptance is unestablished

No affected-regression, integration, compile/static, or P5A6 qualification result is recorded for the reviewed implementation. The only branch GitHub Actions run available to review is the successful documentation-PDF build. Protocol 5.16 treats required checks that did not execute as incomplete acceptance, not a pass.

After F2-F6 repairs, re-derive the final affected surface and execute the complete affected regression plus assembled integration on the final executable candidate. At minimum the final evidence must include:

```text
pytest -q tests/test_mlff_target_size_multi_selection.py
pytest -q tests/test_mlff_target_size_provisional_selection.py
pytest -q tests/test_mlff_target_size_p4d_runtime_cutover.py
pytest -q tests/test_mlff_doc_arch1_specification.py tests/test_mlff_data9b3_campaign_cli_specification.py
python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
python -m compileall mdstats tests qualification/p6-p5a6-compat
```

Also run every additional target-size/post-selection/currentness/qualification regression discovered by final affected-surface re-derivation. Existing P5 currentness/restart tests remain in scope if the view/runtime repair can plausibly affect their callers. Repository/project-required checks remain mandatory.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains deferred to the established final-release/user-machine qualification stage.

---

## Objective / problem invariants / non-goals

The objective is to make the assembled MLFF target-size product behavior, compatibility path, and current documentation agree with the accepted multi-size target-selection architecture without adding compensating machinery.

Tier-1 product invariants remain unchanged:

1. Manual target-size selection is an operator decision over the already prepared qualified ladder. `select-target-size N --horizon-cv HC --horizon H` installs or replaces exactly the per-size tuple `(N, HC, H)` and performs no target-size TRAIN2/EVAL2 work.
2. Automatic target-size screening is advisory and executes only when `--auto` is explicitly requested.
3. Exact membership remains `T_N = pi_train[:N]` through the accepted P2 training-order authority.
4. One prepared generation is shared by all selected sizes; manual selection must not duplicate preparation or hydrate unrelated numerical payloads merely to record the decision.
5. `cross-validate` remains the sole atomic freeze authority for the ordered selected-size collection.
6. CV, production, currentness, and qualification semantics established by the accepted multi-size architecture remain unchanged.
7. Historical campaign compatibility remains append-only and schema-authentic.
8. Current normative documentation must describe one coherent current architecture and public CLI.
9. Derived result files are non-authoritative presentation. Deleting or corrupting one must not alter or contaminate the next authoritative-state projection.

Non-goals:

- no redesign of successive halving, ranking, CV methodology, production methodology, target membership, optimizer normalization, foundation handling, or multi-size semantics;
- no new cache, persistence schema, wrapper binding, compatibility registry, scheduler, view authority, or parallel runtime merely to hide latency or repair stale interfaces;
- no production-scale/GPU qualification in this round.

## Frozen high-level architecture and engineering envelope

The following high-level architecture is frozen for this cycle:

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered unique-by-N selected-size collection;
- manual and automatic target-size selection are separate control branches that converge only at the ordinary proposal merge owner;
- manual selection depends only on the minimum authenticated prepared/P2 authority needed to validate qualified N and exact `T_N` identity;
- automatic diagnostic/P3 execution may depend on the full prepared numerical payload because it genuinely performs the screen;
- derived presentation/status files remain non-authoritative; selection-only rendering derives from committed campaign state, while explicit diagnostic exposure retains strict P3 currentness validation;
- compatibility qualification executes the real baseline producer and real current reopener under their native schemas;
- current architecture/specification/user documentation expresses the same ordered multi-size semantics and current CLI spellings.

Performance envelope for manual selection: eliminate redundant corpus-scale prepared-data loading, hashing, frame-array indexing, and P3 diagnostic validation from the manual decision path. This is efficiency by dependency reduction, not a quantitative speedup promise.

Delegated details include helper names, exact module placement, local deserialization shape, and formatting of non-authoritative views, provided the frozen dependency/authority boundaries above are satisfied with minimum justified complexity.

## Implementation obligations and delegated solution space

### R1 - Narrow manual selection dependency path - implementation accepted, preserve and execute

The reviewed narrow manifest/P2-definition loader is the intended realization. Manual selection must authenticate the current prepared generation and the qualified P2 definition needed to establish `N`, exact `T_N`, and lineage, then commit through the existing proposal owner. It must not load normalized frame arrays, build the P3 frame-array index, build a screen context, execute TRAIN2/EVAL2, or enter automatic-screen preparation.

Acceptance must poison or otherwise prove absence of the full frame-data/index/screen/trainer/evaluator path and retain fail-closed rejection of unqualified N and corrupt/mismatched prepared P2 identity.

### R2 - Selection-only derived view must be state-pure

Implement F2 and F3. Remove the existing-view read/copy dependency. Preserve strict diagnostic validation only at explicit diagnostic exposure/consumption. Close through both cold-manual and **real prior-auto-then-manual** cases, plus the forged-old-view counterexample.

### R3 - P5A6 compatibility reopen - implementation accepted, mandatory driver still required

Preserve baseline scalar access under baseline code. Preserve current-side normalized `frozen_entries` access. Execute the mandatory compatibility driver on the final candidate and repair only real-owner failures if any appear.

### R4 - Structural scalar-state census must reject the actual defect family

Keep one bounded AST structural guard. It must scan all current target-size-state consumers including top-level qualification tooling, exempt only genuine historical-baseline execution, detect direct and simple aliased current-state scalar access, and avoid misclassifying legitimate per-size `.frozen` values.

Required positive/negative examples include:

```python
revision.state.frozen                 # reject
campaign = revision.state
campaign.frozen                       # reject
context.frozen                        # allow: per-size context, not campaign state
state.frozen_entries                  # allow: current collection
```

Do not add a parallel linter or runtime compatibility wrapper.

### R5 - Reconcile current normative documentation and public CLI

Implement F6 at authoritative Markdown/JSON sources. Current documentation must consistently state:

- ordered unique-by-N provisional/frozen collection;
- per-size `(N, H_cv, H_prod)` design;
- exact per-size membership `T_N = pi_train[:N]`;
- manual selection is ordinary and zero-screen-work;
- `--auto` alone invokes automatic screening;
- `--horizon-cv` and `--horizon` are the current public spellings;
- CV/production operate per frozen size while campaign-level admission/completion accounts for the whole requested collection;
- qualification semantics for `k == 1` versus `k > 1` match current architecture.

Rewrite contradictory current prose rather than adding corrective appendices. Regenerate tracked assembled/PDF derivatives from sources. Documentation tests must detect the known contradictory scalar sentences/summaries, not merely assert that some multi-size tokens also exist.

### R6 - Final assembled functional acceptance

After all executable repairs, reconcile the workplan against the final candidate, re-derive the affected surface, execute focused checks, complete affected regression, real-boundary integration, the mandatory compatibility driver, compile/static/project-required checks, and record exact candidate identity plus results in this workplan before requesting another independent review.

A skipped/unavailable mandatory check is not a pass. If an execution dependency is genuinely unavailable, leave the plan open and identify the blocking dependency rather than substituting static inspection.

## Implementation authority

### Frozen

- Manual selection is a zero-screen-work operator decision over authenticated existing prepared/P2 authority.
- Auto screen runs only on explicit `--auto` and remains advisory.
- Exact `T_N = pi_train[:N]`, ordered multi-size collection, per-size horizons, atomic cross-validation freeze, and existing CV/production/qualification scientific semantics remain unchanged.
- Compatibility is append-only/schema-authentic; baseline historical behavior is interpreted under its native schema, current behavior under current schema.
- Derived views are presentation only and cannot become input authority for later projections.
- Current normative documentation and public CLI are self-consistent.

### Delegated

- helper/function names and module layout;
- narrow prepared-object deserialization mechanics;
- exact derived-view formatting;
- structural-test implementation details;
- documentation-test implementation details.

Existing full-load helpers, view helpers, wrappers, test machinery, and the submitted implementation are not frozen merely because they exist.

### Reopen only on evidence

Reopen Design only if evidence shows that authenticating manual selection cannot be done from existing prepared immutable objects/campaign bindings without a new persisted authority, or if current compatibility semantics conflict with append-only native-schema architecture. Do not reopen scientific target-size, CV, production, optimizer, or foundation architecture for ordinary implementation difficulties.

## Affected surface and task-specific acceptance

Expected affected surfaces include:

- `mdstats/training_data/campaign_target_size_runtime.py`;
- `mdstats/training_data/campaign_prepared_generation.py`;
- `mdstats/training_data/campaign_target_size_view.py`;
- target-size proposal/definition owners and callers affected by the narrow load;
- `qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py`;
- structural guard tests for current-state scalar access;
- manual/auto provisional selection regression/integration tests;
- current architecture/specification/user/runbook documentation, dependency graph, generated architecture/PDF output, and their tests;
- post-selection/currentness/restart consumers plausibly affected by final executable edits.

Implementation must re-derive the final affected surface after edits. Run focused tests after each material executable stage, then final complete affected regression and assembled integration. The compatibility driver is mandatory.

Production qualification: **deferred**. Full real-data/GPU/CuEq/LAMMPS production qualification remains at the established final-release/user-machine stage.

## Implementation sequence and genuine redesign / simplification triggers

### Stage 1 - Preserve accepted manual-path reduction

Do not churn R1. Repair only if executable evidence proves a real defect.

### Stage 2 - Remove derived-view self-dependency

Make selection-only view refresh a pure committed-state projection. Run cold-manual, real-auto-then-manual with strict diagnostic/P3 owners poisoned after auto completion, and forged-old-view counterexample tests.

### Stage 3 - Structural and compatibility closure

Strengthen the existing structural guard in place, then run the mandatory P5A6/current restart/reject driver.

### Stage 4 - Documentation reconciliation

Correct authoritative Markdown/JSON sources, strengthen semantic guards, regenerate tracked derivatives, and verify no current document retains campaign-global scalar semantics except explicitly per-size context.

### Stage 5 - Final assembled acceptance

Reconcile every obligation, re-derive the affected surface, execute the complete regression/integration/static/compatibility set on one final executable candidate, record evidence, then request independent Software Design review.

### Simplicity trigger

If repair begins adding caches, persisted summaries, wrapper loaders, duplicate view-state objects, compatibility adapters, or special-case flags around the existing owners, stop and simplify. The remaining defects are over-broad or wrong dependency direction, weak acceptance, and stale documentation; solve them by removal, narrowing, or rewiring unless evidence establishes a genuinely missing capability.
