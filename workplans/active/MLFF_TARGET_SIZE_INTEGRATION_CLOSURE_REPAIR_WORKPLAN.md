---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: no-pass
review_round: implementation-review-2
reviewed_candidate_head: bae8e8cc7896286d5342a7421619383096b9dc0c
reviewed_executable_head: 3935c9d0f19d309cbe1191792884680d68336c62
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Review-2 disposition — NO-PASS / remains open

Independent Software Design review of branch candidate `bae8e8cc7896286d5342a7421619383096b9dc0c` and executable implementation `3935c9d0f19d309cbe1191792884680d68336c62` finds that the core executable repair is substantially improved and the accepted scientific architecture remains intact. No new defect was found in exact target membership, ordered multi-size selection/freeze, automatic-screen ranking, optimizer normalization, foundation handling, CV methodology, or final-production methodology.

The plan nevertheless remains **NO-PASS** because three genuine closure blockers persist:

1. the mandatory P5A6 compatibility oracle was changed from the exact frozen P5A6 baseline to a different, later scalar predecessor rather than preserving or explicitly reopening the exact compatibility contract;
2. current normative architecture/specification text still contains campaign-global scalar `T_selected` / one-global-selection claims after the multi-size transition, so R5 is not semantically closed;
3. final affected-surface acceptance is incomplete and its candidate identity is inconsistent: several existing result-view/currentness tests plausibly affected by the executable view change were not in the recorded final run, and the prior evidence named an unresolvable candidate SHA.

Repair these by restoring authority and narrowing ambiguity. Do not add compatibility wrappers, migrations, caches, duplicate view state, new scanners, or new product machinery.

---

## Tier-1 product invariants

These remain unchanged and are not reopened:

1. `select-target-size N --horizon-cv HC --horizon H` is an operator decision over an already prepared qualified ladder. It installs or replaces exactly the per-size tuple `(N, HC, H)` and performs no target-size TRAIN2/EVAL2 work.
2. Automatic target-size screening is advisory and is entered only by explicit `--auto`.
3. Every selected membership is exactly `T_N = pi_train[:N]` through the accepted P2 training-order authority.
4. One prepared generation is shared by all selected sizes. Manual selection must not hydrate unrelated frame/P3 payloads merely to record a decision.
5. The provisional/frozen target design is one ordered unique-by-N collection. `cross-validate` is the sole atomic freeze authority.
6. CV and final production execute independently for every frozen size using its exact membership and role-specific horizon; there is no cross-size winner rule.
7. CV, production, currentness, qualification, optimizer, and foundation semantics accepted by the multi-size architecture remain unchanged.
8. Historical compatibility is append-only and schema-authentic. A compatibility claim must test the exact supported predecessor contract it names; a convenient later snapshot is not interchangeable merely because it has similar scalar fields.
9. Derived result files are non-authoritative presentation. Deleting, corrupting, or editing one cannot change the next projection from authoritative state.
10. Current normative documentation must describe one coherent ordered multi-size architecture and current CLI.

## Frozen high-level architecture

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered unique-by-N selected-size collection;
- manual and automatic selection are separate control branches that converge only at the ordinary proposal merge owner;
- manual selection depends only on the minimum authenticated prepared/P2 authority required to validate N and exact `T_N`;
- automatic diagnostic/P3 execution may use the full prepared numerical payload because it actually screens candidates;
- selection-only result rendering is a pure projection of committed campaign state; explicit diagnostic exposure retains strict P3 currentness validation;
- compatibility qualification uses the real historical producer under its native schema and the real current reopener under the current schema, with no preload migration or rewrite;
- current architecture/specification/user/runbook documents express collection-level semantics and use singular `N_selected`/`T_N` only when explicitly describing one per-size binding/run;
- full real-data/GPU/CuEq/LAMMPS production qualification remains deferred to the established final-release/user-machine stage.

---

## Accepted implementation surfaces — preserve unless new executable evidence fails

### A1 — Narrow manual prepared/P2 dependency

The current manual path through `load_prepared_target_size_definition` is the intended realization. It authenticates the bound prepared manifest/configuration and the aggregate/experiment-definition identity without loading normalized frame data, building a frame-array index, constructing a screen context, or entering TRAIN2/EVAL2.

Do not replace this with another persisted definition, cache, wrapper loader, or synchronized authority.

### A2 — Selection-view self-dependency removed

`build_selection_target_size_result_view()` now projects only `TargetSizeCampaignRevision.state`, and `write_selection_target_size_result_view()` no longer reads the destination `target-size-state.json` before writing. If `state.auto_diagnostic` exists, only committed diagnostic summary fields are projected; P3-only progress fields are absent until strict diagnostic exposure.

This satisfies the frozen dependency direction. Preserve it.

### A3 — Real auto -> manual acceptance now exercises the production owner

The repaired acceptance runs a bounded real `--auto` diagnostic to `DIAGNOSTIC_COMPLETE`, then poisons strict diagnostic exposure/P3/full-frame owners and performs a real manual selection. It verifies the committed manual design and unchanged automatic-diagnostic identity. A separate counterexample forges the old result JSON and proves forged fields do not survive the next manual projection.

Preserve this owner boundary; do not replace it with fabricated post-diagnostic state.

### A4 — Scalar-state structural guard now covers simple aliases

The existing AST guard detects direct retired scalar accesses and simple aliases such as `campaign = revision.state; campaign.frozen`, scans current training-data and qualification surfaces, allows legitimate per-size `.frozen`, and precisely exempts the historical baseline producer by file/function. Keep one guard; do not add a parallel Semgrep/linter framework merely for this rule.

### A5 — Current-side compatibility access

The current reopen side correctly reads the normalized one-entry `frozen_entries` collection while the historical producer uses its native scalar `state.frozen`. Preserve that schema-native split. The remaining compatibility blocker is the **baseline identity**, not this access repair.

---

## Blocking repair R7 — restore the exact P5A6 compatibility contract

### Finding

The implementation changed the compatibility baseline in:

- `qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py`;
- `qualification/p6-p5a6-compat/P5A6_FIXTURE_IDENTITY.json`;
- `tests/test_mlff_target_size_p6_destructive_closure.py`;
- `tests/test_mlff_target_size_p6_p5a6_compatibility.py`.

The previous pin was the exact accepted P5A6 baseline:

```text
commit 1670275487d29bbcde4c59efafdef9d1f8b0ced7
tree   17e2c5609974712bda1efd3375f09f42da830f68
```

The implementation replaced it with:

```text
commit fc69a3d397b7f7f40e905fa6a3a63cc1e038ea85
tree   67cf5f27db7b0f40670236e365fe45d54a522ef4
```

`fc69a3d...` is a real later scalar predecessor, but it is not the exact baseline frozen by `workplans/archive/mlff-target-size-v7-packages/P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md` and carried through `P6_REVISION_12_AUTHORITY.md`. Those authorities explicitly require a workspace produced by exact P5A6 code and forbid substituting semantically similar test data or a different producer.

Changing the implementation and its test oracle together does not prove the original compatibility claim. The later multi-size compatibility rule permits schema-authentic normalization of predecessor-v2 scalar rows but does not silently rename an arbitrary scalar commit as the exact P5A6 fixture.

The remote Git repository currently does not resolve the frozen P5A6 commit/tree, which is evidence that the required compatibility artifact may have become unreachable. Unavailability is not permission to rewrite the baseline.

### Required repair

1. Recover the exact `167027...` commit and `17e2...` tree from an authoritative repository clone, retained worktree, bundle, archive, or other project-controlled Git object source, and make them reachable for the qualification driver without rewriting their bytes.
2. Revert the P5A6 driver, fixture identity, and tests to the exact frozen baseline identifiers.
3. Keep the accepted current-side `frozen_entries` reopener; do not change the historical producer or migrate its workspace before first current load.
4. Run the real driver against that exact baseline and require all three independent cases to pass:
   - exact P5A6 -> current authenticated reopen;
   - current -> current restart/reuse;
   - retired V5/V6 reject-before-reuse.
5. If the exact Git objects genuinely cannot be recovered, leave this compatibility claim **blocking/unavailable** and return only the compatibility scope to Software Design for an explicit supported-history decision. Do not substitute `fc69...`, hand-author a fixture, bless a generated equivalent, add a compatibility bridge, or modify the old frozen authority merely to obtain a green test.

The immediate scalar predecessor may separately deserve its own compatibility regression if current product support requires it, but that is not a replacement for the exact P5A6 claim.

---

## Blocking repair R8 — finish semantic documentation reconciliation at authoritative sources

### Finding

The named R5 sentences were repaired, but current normative sources still contain campaign-global scalar claims. Examples on the reviewed executable candidate include:

- `docs/specs/training_data/mlff_data_stage_plan_spec.md`, fitted-domain isolation:
  - `one pi_train and exact T_selected membership after the target-size freeze`;
  - `final T_selected -> final-training fitted products -> fresh final production`.
- assembled current architecture / its numbered chapter sources:
  - `the current target-size choice is global; post-selection CV may derive fold-local partitions only inside T_selected`;
  - `one protocol-global target-size decision with one exact global selected membership`;
  - `cannot change global T_selected`;
  - collection-level flow followed by `CV partitions inside T_selected` without identifying which per-size binding owns that `T_selected`.

These contradict the ordered frozen collection when read as campaign-global authority. The workplan explicitly required a rescan of authoritative chapter sources and allowed singular language only when the text clearly refers to one per-size binding/run. The strengthened tests presently guard only a subset of the earlier phrases, so they can remain green while these contradictions survive.

### Required repair

1. Rewrite the highest authoritative sources, not the assembled derivative. Inspect at minimum:
   - `docs/arch_manuals/mlff_training_data/00_front_matter.md`;
   - `docs/arch_manuals/mlff_training_data/10_foundations.md`;
   - `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
   - `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`;
   - `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
   - `docs/specs/training_data/mlff_data_stage_plan_spec.md`;
   - current CLI/spec/user/runbook sources and the dependency graph.
2. Campaign-global wording must name the **ordered frozen collection**. Per-size wording may use `N_selected`, `T_N`, or `T_selected` only with an explicit binding such as “for each frozen size/binding”.
3. Replace statements such as “one protocol-global target-size decision with one exact global selected membership” and “global T_selected”; do not preserve them with an explanatory appendix.
4. Make fitted-domain diagrams explicitly branch over each frozen `T_N`: fold-local fitted products/CV and final training are per frozen size even though the method/prepared generation can be shared.
5. Regenerate assembled Markdown and tracked PDFs from authoritative sources.
6. Strengthen existing doc tests with known stale counterexamples from this review, including at least the phrases above. Do not blanket-ban `T_selected`; legitimate explicitly per-size use remains valid.

No scientific redesign is required. This is reconciliation of the already accepted multi-size architecture.

---

## Blocking repair R9 — re-derive and execute the complete affected regression on a resolvable candidate

### Finding

The executable change touched `campaign_target_size_view.py`, so the affected surface includes existing consumers/tests that read, write, or assert behavior of `target-size-state.json` and currentness around it. The recorded final suite did not include several existing directly relevant tests discovered by the review, including:

- `tests/test_mlff_campaign_prepare_boundary.py`;
- `tests/test_mlff_target_size_p4e_terminal_and_invalidation.py`;
- `tests/test_mlff_target_size_p5a_selected_context.py`;
- `tests/test_mlff_target_size_p5f_structure.py` (including the no-result-JSON-as-authority structural contract).

The final evidence also recorded `candidate_head: 4385cf5866fd5b2c1c552ba3a4892001a129cec4`, which is not resolvable in the remote repository. The actual reviewed branch head is `bae8e8cc...`; executable code is `3935c9d...`.

Protocol 5.16 requires final affected-surface re-derivation and complete affected regression on a source identity that can be established. Passing a selected subset is not enough when directly affected existing consumers were omitted.

### Required repair

After R7/R8 are resolved:

1. Commit the final executable/document-source changes to a resolvable branch head.
2. Re-derive the affected surface from that final tree using semantic/reference search where available plus text/structural cross-checks for dynamic/file-based consumers.
3. Run the previously required suites plus the omitted direct result-view/currentness suites above. Prefer a bounded broader target-size/post-selection affected suite if it is cheaper and reduces omission risk.
4. At minimum retain execution of:

```text
pytest -q tests/test_mlff_target_size_multi_selection.py
pytest -q tests/test_mlff_target_size_provisional_selection.py
pytest -q tests/test_mlff_target_size_p4d_runtime_cutover.py
pytest -q tests/test_mlff_target_size_multi_size_integration.py
pytest -q tests/test_mlff_campaign_prepare_boundary.py
pytest -q tests/test_mlff_target_size_p4e_terminal_and_invalidation.py
pytest -q tests/test_mlff_target_size_p5a_selected_context.py
pytest -q tests/test_mlff_target_size_p5f_structure.py
pytest -q tests/test_mlff_doc_arch1_specification.py tests/test_mlff_data9b3_campaign_cli_specification.py
pytest -q tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_target_size_p6_p5a6_compatibility.py
python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
python -m compileall mdstats tests qualification/p6-p5a6-compat
```

5. Run every additional currentness/restart/post-selection/qualification test found by final impact analysis. Repository-required checks remain mandatory.
6. Record the actual final candidate SHA and executable SHA. If later commits only regenerate PDFs or record evidence, make that parent relationship explicit; do not record a nonexistent SHA.
7. Correct evidence prose to name actual owners/functions. The narrow prepared loader currently accepted by review is `load_prepared_target_size_definition`, not a nonexistent `load_qualified_target_size_manifest_and_definition`.

A skipped developer compatibility test may remain skipped when its optional preserved workspace is absent **only if** the mandatory standalone exact-baseline compatibility driver ran and passed; the driver is the closure evidence.

---

## Tooling note for the next implementation/review

Serena and Semgrep were requested and are appropriate for semantic/structural questions here, but this review environment could not execute them: neither binary was installed, `uvx` could not fetch Semgrep because outbound package DNS failed, and a local Git clone of GitHub could not be created because outbound GitHub DNS failed. GitHub repository source, exact diffs, current authorities, and the repository's own AST structural rule were used as the fallback. Tool absence does not change any acceptance requirement.

When the implementation environment has Serena/Semgrep available, use them to improve final affected-surface census and structural cross-checking, but do not add permanent tool infrastructure solely for this workplan.

---

## Implementation sequence

### Stage 1 — Compatibility authority restoration

Recover/reinstate the exact P5A6 baseline or explicitly return the compatibility scope to Design as unavailable. Do not proceed by substituting another scalar commit.

### Stage 2 — Normative documentation reconciliation

Rewrite the remaining scalar campaign-global statements at numbered/source owners, strengthen existing semantic doc guards, and regenerate derivatives.

### Stage 3 — Final affected-surface closure

Re-derive callers/consumers from the final tree; execute complete bounded regression, exact compatibility driver, compile/static/project-required checks, and real-boundary integrations.

### Stage 4 — Independent review

Request another Software Design review only after candidate identity is resolvable and every mandatory compatibility/affected-surface check has executed.

## Simplicity trigger

If implementation begins adding caches, persisted summaries, wrapper loaders, compatibility adapters, migrations, duplicate view-state objects, new state machines, or a second scanner to solve these findings, stop and simplify. The remaining problems are authority substitution, stale prose, and incomplete acceptance. Repair the existing owner/contract/evidence surfaces directly.
