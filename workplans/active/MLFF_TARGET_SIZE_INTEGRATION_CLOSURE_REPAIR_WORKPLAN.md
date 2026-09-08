---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
review_status: no-pass
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Objective / problem invariants / non-goals

The recent MLFF target-size rounds are scientifically close to the frozen design, but independent integration review found residual implementation and documentation drift that prevents genuine closure. The objective of this repair is to make the assembled product behavior, compatibility path, and current documentation agree with the accepted multi-size target-selection architecture without adding compensating machinery.

Tier-1 product invariants remain unchanged:

1. Manual target-size selection is an operator decision over the already prepared qualified ladder. `select-target-size N --horizon-cv HC --horizon H` installs or replaces exactly the per-size tuple `(N, HC, H)` and performs no target-size TRAIN2/EVAL2 work.
2. Automatic target-size screening is advisory and executes only when `--auto` is explicitly requested.
3. Exact membership remains `T_N = pi_train[:N]` through the accepted P2 training-order authority.
4. One prepared generation is shared by all selected sizes; manual selection must not duplicate preparation or hydrate unrelated numerical payloads merely to record the decision.
5. `cross-validate` remains the sole atomic freeze authority for the ordered selected-size collection.
6. CV, production, currentness, and qualification semantics established by the accepted multi-size architecture remain unchanged.
7. Historical campaign compatibility remains append-only and schema-authentic.
8. Current normative documentation must describe one coherent current architecture and public CLI.

Non-goals:

- no redesign of successive halving, ranking, CV methodology, production methodology, target membership, optimizer normalization, foundation handling, or multi-size semantics;
- no new cache, persistence schema, wrapper binding, compatibility registry, scheduler, or parallel runtime merely to hide latency or repair stale interfaces;
- no production-scale/GPU qualification in this round.

## Frozen high-level architecture and engineering envelope

The following high-level architecture is frozen for this cycle:

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered unique-by-N selected-size collection;
- manual and automatic target-size selection are separate control branches that converge only at the ordinary proposal merge owner;
- manual selection depends only on the minimum authenticated prepared/P2 authority needed to validate qualified N and exact `T_N` identity;
- automatic diagnostic/P3 execution may depend on the full prepared numerical payload because it genuinely performs the screen;
- derived presentation/status files remain non-authoritative and must not force expensive diagnostic revalidation when the command does not claim or consume that diagnostic evidence;
- compatibility qualification must execute the real baseline producer and real current reopener under their native schemas;
- current architecture/specification/user documentation must express the same multi-size semantics and current CLI spellings.

Performance envelope for manual selection: eliminate redundant corpus-scale prepared-data loading, hashing, frame-array indexing, and P3 diagnostic validation from the manual decision path. This is efficiency by dependency reduction, not a quantitative speedup promise.

Delegated details include helper names, exact module placement, local deserialization shape, and how the non-authoritative view is refreshed, provided the frozen dependency boundaries above are satisfied with less or equal total complexity.

## Implementation obligations and delegated solution space

### R1 — Narrow the manual selection dependency path

**Concern / rationale.** Current `_execute_manual_target_size_proposal()` calls the full prepared-generation loader. That loader deserializes every prepared component, loads normalized frame-data cache records, authenticates their files, and builds the P3 frame-array index. Manual selection only needs the authenticated P2 experiment definition/training order required to verify N and derive exact membership identity. This can produce minute-scale disk work that resembles preparation despite no screen being requested.

**Required end state.** The public manual command:

```text
select-target-size 512 --horizon-cv 30 --horizon 60
```

must authenticate the current prepared generation and the qualified P2 definition needed to establish `N=512`, exact `T_512`, and lineage, then commit the tuple through the existing proposal owner. It must not load normalized frame arrays, build the P3 frame-array index, build a screen context, execute TRAIN2/EVAL2, or otherwise enter automatic-screen preparation.

**Delegated solution space.** Reduce or split the existing prepared-loader dependency so the manual path obtains only the authenticated selection definition. Reuse existing manifest/component digests and current campaign binding. Do not add another persisted definition, shadow cache, or synchronized authority unless evidence proves the existing immutable prepared objects cannot support a narrow authenticated read.

**Acceptance boundary.** Exercise the real public/manual runtime owner. Expensive trainer/evaluator dependencies may be poisoned or doubled below that owner, but the test must observe that production control flow never reaches the full frame-data/P3 preparation owners.

**Required evidence.** Tests must fail on the current heavyweight path and prove absence of calls to at least the effective equivalents of `load_prepared_frame_data`, `build_frame_array_index`, `build_screen_context`, target-size trainer, and target-size evaluator. Also prove rejection of unqualified N and corrupt/mismatched prepared P2 identity remains fail-closed.

### R2 — Prevent diagnostic-view revalidation from leaking into manual selection

**Concern / rationale.** A prior completed `--auto` diagnostic can leave lifecycle state `DIAGNOSTIC_COMPLETE`. A later manual proposal preserves that diagnostic evidence, then `_refresh_target_size_view()` may call the strict current auto-diagnostic exposure path merely to rewrite a derived view. That path rebuilds/validates P3 execution context and adopted diagnostic evidence even though the manual command neither requests nor consumes auto recommendation evidence.

**Required end state.** Manual selection preserves valid existing automatic-diagnostic evidence without re-running or revalidating the P3 diagnostic stack solely for presentation refresh. Strict diagnostic validation remains required when a command actually exposes, claims, or consumes the auto diagnostic.

**Delegated solution space.** Simplify the derived-view refresh boundary. A selection-only non-authoritative projection may be rendered from committed campaign state without claiming fresh diagnostic validation. Do not weaken the strict diagnostic validation owner itself, and do not introduce a second authoritative view/state object.

**Required evidence.** Cover both: (a) campaign with no prior auto diagnostic; and (b) campaign with an existing completed auto diagnostic. In both cases a manual selection performs zero new P3 diagnostic validation/training/evaluation work while preserving the diagnostic evidence record.

### R3 — Repair P5A6 compatibility reopen against the current collection schema

**Concern / rationale.** `qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py` intentionally runs baseline code to produce a historical scalar workspace, then current code to reopen it unchanged. The baseline producer's scalar `revision.state.frozen` access is legitimate under its native schema. The current reopen path still uses the scalar attribute even though current state uses normalized `frozen_entries`, so the mandatory compatibility command can fail before proving reopen compatibility.

**Required end state.** Preserve the baseline producer exactly as a baseline-schema consumer. Repair only the current reopen side so it observes the current normalized one-entry frozen collection / canonical selected-context owner and proves the unchanged historical workspace reopens through current production code.

**Delegated solution space.** Rewire the current-side access to the existing collection owner. Do not add a compatibility wrapper around both sides or rewrite historical state.

**Required evidence.** Execute the mandatory P5A6 compatibility driver or an equivalent real-owner integration command that creates the baseline workspace under baseline code and reopens that exact workspace under the candidate current code. The structural test must also cover compatibility/qualification scripts, not only `mdstats/training_data`.

### R4 — Expand structural census to the actual affected repository surface

**Concern / rationale.** Existing scalar-state structural guards scan only `mdstats/training_data`, so stale scalar accesses in qualification tooling escaped detection.

**Required end state.** The structural absence check for retired current-schema scalar selection access covers every repository surface that is expected to consume current target-size state, including qualification compatibility tooling. Native baseline-schema code explicitly executed under a historical ref remains allowed.

**Delegated solution space.** Prefer expanding the existing bounded census/guard rather than adding another linter or duplicate scanner.

**Required evidence.** A known-positive stale scalar access in an in-scope current consumer must be detected; known legitimate baseline/historical use must not be misclassified.

### R5 — Reconcile current normative documentation and public CLI

**Concern / rationale.** Current documentation still contains scalar claims such as one selected `N_selected`, singular operator choice/freeze wording, and retired `--select-horizon*` CLI spellings, while the current architecture is ordered multi-size with `--horizon-cv` / `--horizon`.

**Required end state.** Reconcile all current normative/user-facing MLFF target-size documentation so it consistently states:

- ordered unique-by-N provisional/frozen collection;
- per-size `(N, H_cv, H_prod)` design;
- manual selection is ordinary and zero-screen-work;
- `--auto` alone invokes automatic screening;
- `--horizon-cv` and `--horizon` are the current public spellings;
- qualification semantics for `k==1` versus `k>1` match current architecture.

At minimum inspect and reconcile the affected sections of:

- `docs/specs/training_data/README.md`;
- `docs/arch_manuals/mlff_training_data/00_front_matter.md`;
- `docs/arch_manuals/mlff_training_data/10_foundations.md`;
- assembled `docs/arch_manuals/mlff_training_data_architecture.md` and its source chain;
- current dependency/ownership diagrams or summaries that still describe a scalar selected set;
- root `README.md` MLFF target-size usage;
- GPU/workstation runbook or other current operational docs using scalar/retired CLI semantics.

**Delegated solution space.** Rewrite current prose coherently at its authoritative source. Do not add corrective appendices that leave contradictory current text in place.

**Required evidence.** Documentation tests/structural checks must assert semantic multi-size/current-CLI invariants rather than merely token presence. Regenerate any tracked assembled derivative from its authoritative sources rather than hand-patching only the derivative.

## Implementation authority

### Frozen

- Manual selection is a zero-screen-work operator decision over authenticated existing prepared/P2 authority.
- Auto screen runs only on explicit `--auto` and remains advisory.
- Exact `T_N = pi_train[:N]`, ordered multi-size collection, per-size horizons, atomic cross-validation freeze, and existing CV/production/qualification scientific semantics remain unchanged.
- Compatibility is append-only/schema-authentic; baseline historical behavior is interpreted under its native schema, current behavior under current schema.
- Current normative documentation and public CLI must be self-consistent.

### Delegated

- helper/function names and module layout;
- narrow prepared-object deserialization mechanics;
- exact derived-view formatting/refresh implementation;
- structural-test implementation details;
- documentation test implementation details.

Existing full-load helpers, view helpers, wrappers, and test machinery are not frozen merely because they exist.

### Reopen only on evidence

Reopen Design only if evidence shows that authenticating a manual selection cannot be done from existing prepared immutable objects and campaign bindings without introducing a new persisted authority, or if current compatibility semantics conflict with the append-only native-schema architecture. Do not reopen scientific target-size, CV, production, or optimizer architecture for ordinary implementation difficulties.

## Affected surface and task-specific acceptance

Expected affected surfaces include:

- `mdstats/training_data/campaign_target_size_runtime.py`;
- prepared-generation/component loading owners in `campaign_prepared_generation.py` and related cache/index code;
- target-size proposal/definition owners in `target_size_execution/common.py` or their current equivalents;
- target-size derived view/reporting owners;
- compatibility qualification driver under `qualification/p6-p5a6-compat/`;
- structural guard tests for current-state scalar access;
- manual/auto provisional selection regression/integration tests;
- current architecture/specification/user/runbook documentation and generated architecture output.

Implementation must re-derive the final affected surface after edits. Run focused tests after each material behavior stage, then final affected regression and assembled integration. A required check that is skipped because a real compatibility workspace was not produced is not closure evidence; run the driver that produces and reopens it.

Production qualification: **deferred**. This round changes control/dependency behavior, compatibility access, tests, and documentation; full real-data/GPU qualification remains at the established final-release/user-machine stage.

## Implementation sequence and genuine redesign / simplification triggers

### Stage 1 — Manual-path dependency reduction

Narrow the real manual command to the minimum authenticated P2/selection authority and remove P3/full-frame hydration from that branch. Close with focused manual-selection tests and affected regression for prepared loading/proposal persistence.

### Stage 2 — Derived-view control-path cleanup

Remove the selection-only dependency on strict auto-diagnostic revalidation while preserving strict validation where auto evidence is actually exposed/consumed. Close with both cold-manual and prior-auto-then-manual integration cases.

### Stage 3 — Compatibility and structural closure

Repair the current-side P5A6 reopen access, broaden the existing structural census, and execute the mandatory baseline-produce/current-reopen integration.

### Stage 4 — Documentation reconciliation

Rewrite current authoritative docs to one coherent multi-size/current-CLI description, regenerate derived architecture artifacts if tracked, and strengthen semantic doc guards where useful.

### Stage 5 — Final assembled acceptance

Reconcile the workplan against the assembled candidate, re-derive the affected surface, run complete affected regression and real-boundary integration, then independent Software Design review.

### Simplicity trigger

If implementation begins adding caches, persisted summaries, wrapper loaders, duplicate view-state objects, compatibility adapters, or special-case flags around the existing full loader, stop and simplify the dependency graph instead. The observed defect is unnecessary work caused by an overly broad dependency boundary; repair by narrowing/removing dependencies unless evidence establishes a genuinely missing capability.
