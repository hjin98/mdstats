---
kind: implementation-workplan
workplan_id: MLFF-TARGET-SIZE-INTEGRATION-CLOSURE-REPAIR
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
reviewed_date: 2026-09-08
review_status: no-pass
review_round: implementation-review-3
reviewed_candidate_head: c9dfe2bc7a0176f647439b6af9f80c6ead49cecb
reviewed_executable_head: 23854d72555014c6d4e834d85a5ad292b228f93d
reviewed_evidence_head: 0d8e7cdb9594c69c2df94c3f0aea478bda7c8517
branch: plan/mlff-target-size-integration-closure-repair
implementation_base_head: 32bd59d12de334a2e5c29d80d6c1cf5cceb4506c
predecessor_workplan: workplans/archive/MLFF_TARGET_SIZE_MULTI_SELECTION_NEXT_ROUND_REPAIR_WORKPLAN.md
---

# MLFF target-size integration closure repair workplan

## Review-3 disposition — NO-PASS / narrowly open

Independent Software Design review of branch candidate `c9dfe2bc7a0176f647439b6af9f80c6ead49cecb` finds the Round-3 implementation materially improved. The substantive source/test/document changes are at `23854d72555014c6d4e834d85a5ad292b228f93d`; `0d8e7cdb9594c69c2df94c3f0aea478bda7c8517` records implementation evidence and `c9dfe2bc7a0176f647439b6af9f80c6ead49cecb` regenerates tracked PDFs only.

The accepted scientific and runtime architecture remains intact. No new blocking defect was found in exact target membership, ordered multi-size proposal/freeze, manual-versus-auto control flow, automatic-screen ranking, optimizer normalization, foundation handling, post-selection CV, final production, currentness, or the selection-view authority boundary.

Round 3 closes the previous affected-regression/candidate-identity blocker. Two genuine blockers remain:

1. the current product still promises unchanged reopen of the accepted P5A6 workspace, but neither the exact historical P5A6 Git object nor the original preserved workspace is currently available to execute that compatibility boundary;
2. Part VI of the current normative architecture was omitted from the semantic documentation reconciliation and still describes the automatic screen as producing a selected binding / one selected size.

Do not add a compatibility wrapper, migration, synthetic fixture, cache, duplicate view authority, new state machine, or new documentation scanner to close either issue.

---

## Tier-1 product invariants — unchanged

1. `select-target-size N --horizon-cv HC --horizon H` is an operator decision over an already prepared qualified ladder. It installs or replaces exactly the per-size tuple `(N, HC, H)` and performs no target-size TRAIN2/EVAL2 work.
2. Automatic target-size screening is advisory and runs only when `--auto` is explicitly requested. It emits a recommendation or typed no-recommendation diagnostic outcome; it never freezes a target size.
3. Every target membership is exactly `T_N = pi_train[:N]` through the accepted P2 training-order authority.
4. One prepared generation is shared by all selected sizes. Manual selection must not hydrate unrelated numerical/P3 payloads merely to record a decision.
5. The provisional/frozen target design is one ordered unique-by-N collection. `cross-validate` is the sole atomic freeze authority.
6. Post-selection CV and fresh final production execute independently for every frozen size using its exact `T_N` and per-size role horizon. There is no cross-size winner rule.
7. Selection provenance is audit-only; role-extraneous horizons and provenance do not contaminate per-size scientific identities.
8. Derived target-size result JSON is presentation only. It cannot become input authority for a later projection or scientific transition.
9. Historical compatibility is append-only and schema-authentic. Supported predecessor state is interpreted under its native bytes/schema and is not rewritten merely to fit current representation.
10. Current normative architecture/specification/user documentation must describe one coherent ordered multi-size architecture and current CLI.

## Frozen high-level architecture — unchanged

- one `CampaignStore` mutable campaign authority;
- one prepared generation and one ordered unique-by-N selected-size collection;
- manual and automatic selection are separate control branches that converge only at the ordinary proposal-merge owner;
- manual selection depends only on the minimum authenticated prepared/P2 authority needed to validate `N` and exact `T_N`;
- automatic diagnostic/P3 execution may depend on the full prepared numerical payload because it genuinely screens candidates;
- selection-only result rendering is a pure projection of committed campaign state; explicit diagnostic exposure retains strict P3 currentness validation;
- compatibility qualification exercises a real historical P5A6-created workspace through the real current persistence/currentness/selected-binding/P5 consumers without pre-load migration or rewrite;
- current documentation names the ordered collection at campaign scope and uses singular `N_selected`/`T_N` only for an explicitly identified per-size binding/run;
- full real-data/GPU/CuEq/LAMMPS production qualification remains deferred to the established final-release/user-machine stage.

Lower-level helper names, test organization, documentation wording, and the mechanism used to recover historical evidence remain delegated unless explicitly constrained below.

---

## Accepted implementation surfaces — preserve

### A1 — Narrow manual prepared/P2 dependency — PASS

The manual path through `load_prepared_target_size_definition` authenticates the bound prepared manifest/configuration and P2 aggregate/experiment-definition identity without loading normalized frame arrays, building the frame-array index, constructing a screen context, or entering TRAIN2/EVAL2. Preserve this dependency reduction; do not replace it with another persisted definition, cache, or wrapper loader.

### A2 — Selection-view authority boundary — PASS

Selection-only result rendering derives from committed `TargetSizeCampaignRevision.state` and never reads the old `target-size-state.json` as an input. A real completed auto diagnostic followed by manual selection succeeds with strict diagnostic/P3/full-frame owners poisoned, and a forged old view cannot contaminate the next projection. Preserve this subtraction of derived-state authority.

### A3 — Current multi-size state and structural closure — PASS

Current campaign state uses `provisional_entries` / `frozen_entries`; the bounded AST guard detects direct and simple aliased current-state scalar access while allowing legitimate per-size `.frozen` fields and precisely exempting the historical producer. No second scanner is required.

### A4 — Current-side predecessor normalization — PASS

The current state reader authenticates the scalar predecessor schema in its native wire representation, normalizes it in memory to at most one provisional/frozen entry, and writes only the current collection schema on later current transitions. The current-side compatibility reopener consumes `frozen_entries`; historical producer code remains scalar under its own schema.

### A5 — Round-3 normative documentation repair outside Part VI — PASS

The Round-3 changes correctly reconciled the named campaign-global scalar contradictions in `00_front_matter.md`, `10_foundations.md`, `30_statistical_design.md`, `80_ownership_and_decisions.md`, the cross-cutting stage-plan specification, and their assembled derivatives. Existing semantic doc guards now reject those known stale phrases. Preserve these corrections.

### A6 — Round-3 affected-surface regression and source identity — PASS, reusable conditionally

Round 3 established a resolvable source identity and executed the previously omitted result-view/currentness consumers. Recorded evidence on `23854d72555014c6d4e834d85a5ad292b228f93d` includes:

- documentation/specification tests: **12 passed**;
- P6 destructive/compatibility unit surface: **31 passed, 1 skipped** (the skip is the absent preserved P5A6 workspace and belongs to open blocker R10 below);
- ten-module target-size/result-view/currentness affected suite: **200 passed**;
- `python -m compileall mdstats tests qualification/p6-p5a6-compat`: **0 errors**;
- tracked PDF workflow: **PASS** on the evidence child.

No `mdstats/` product runtime source changed in Round 3. Therefore the 200-pass runtime evidence remains reusable if the next repair is restricted to documentation/tests and recovery of the original compatibility artifact. Any product-runtime, serializer, currentness, compatibility-reader, or state-schema change invalidates the corresponding evidence and requires fresh affected regression.

---

## Blocking R10 — establish the still-supported P5A6 unchanged-workspace compatibility boundary

### Finding

The implementation correctly restored the exact historical provenance pins:

```text
P5A6 commit  1670275487d29bbcde4c59efafdef9d1f8b0ced7
P5A6 tree    17e2c5609974712bda1efd3375f09f42da830f68
```

and truthfully ran the mandatory qualification driver. The driver failed closed before producing a workspace because the exact commit is no longer reachable in the local repository/remotes:

```text
fatal: invalid reference: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
```

This is no longer an implementation substitution defect: Round 3 did not fall back to `fc69...`, fabricate state, migrate the fixture, or weaken the oracle.

However current normative architecture still explicitly states that the accepted current-generation P5A6 workspace remains a required unchanged reopen boundary. The committed compatibility evidence also names the original P5A6 fixture identity/content/database snapshot, but `qualification/p6-p5a6-compat/workspace/` itself is absent. Therefore the real compatibility claim has not executed and cannot pass yet.

### Design clarification: product boundary versus evidence-production mechanism

The product/Frozen requirement is **unchanged reopen of the real P5A6-created workspace through current owners**. Re-creating that workspace from the exact historical commit is one valid evidence-production mechanism, but perpetual availability of that Git object is not itself the product outcome.

Accordingly either of these routes may establish the same compatibility claim:

**Route A — recover the exact historical source:** recover commit/tree `167027...` / `17e2...` from an authoritative project-controlled clone, bundle, archive, or retained object store; then run the existing authenticated driver to create and consume the fixture.

**Route B — recover the original preserved workspace:** recover the original P5A6-produced `qualification/p6-p5a6-compat/workspace/` bytes from a project-controlled backup/artifact/archive. Before any current code opens it, authenticate it against the committed `P5A6_FIXTURE_IDENTITY.json`, `P5A6_FIXTURE_CONTENT_MANIFEST.json`, and `P5A6_FIXTURE_DATABASE_SNAPSHOT.json`. Then execute the existing real-owner compatibility test on that unchanged workspace, close/reopen it, and verify no authoritative persisted content changes.

Route B is recovery of historical evidence, **not reconstruction**. Do not synthesize files/SQLite rows from the manifests, generate an equivalent workspace with another commit, hand-author state, or pre-open/migrate the fixture.

If neither the exact source nor the original workspace can be recovered, keep this claim **blocking/unavailable** and return only the supported-history decision to Software Design. Do not silently drop P5A6 compatibility or add a bridge merely because the evidence artifact was lost.

### Required compatibility acceptance

Whichever recovery route is used, establish separately:

1. real P5A6-created unchanged workspace -> current real CampaignStore/currentness/selected-binding/CV/final-production owners: PASS;
2. close/reopen of that workspace remains current and deterministic: PASS;
3. current -> current restart/reuse: PASS;
4. retired V5/V6 reject-before-reuse: PASS;
5. no pre-load migration/rewrite and no compatibility adapter introduced.

The optional compatibility test may no longer skip at final closure. If Route A is used, the standalone authenticated driver must pass. If Route B is used because the historical Git object remains unavailable, the recovered-workspace real-owner test plus the existing independent current-restart and retired-state rejection tests are the acceptance evidence; do not add a new driver mode solely for process ceremony.

---

## Blocking R11 — finish current normative documentation reconciliation in Part VI

### Finding

Round 3 repaired several authoritative chapters but did not edit `docs/arch_manuals/mlff_training_data/60_execution_performance.md`. That current normative source still contains stale scalar/automatic-selection semantics.

At minimum it presently says:

```text
one common target-size preparation
-> paired-seed candidate screen
-> selected binding
-> selected-only CV and fresh final production
```

and later:

```text
qualified candidates
-> coarse n1/M1
-> at most four short n2/M2 continuations
-> two final n3/M3 continuations
-> one selected size or typed scientific failure
```

It also says a fold-local view cannot alter unqualified `T_selected` at campaign scope.

These statements contradict the already Frozen architecture: the screen is advisory and produces a recommendation/no-recommendation; the operator owns an ordered provisional collection; only `cross-validate` freezes it; CV/production then operate per frozen `T_N`.

The existing Round-3 negative documentation assertions do not include these phrases, so they can remain green while Part VI contradicts Parts I/V/VII.

### Required repair

Edit the authoritative source `docs/arch_manuals/mlff_training_data/60_execution_performance.md` directly:

1. change the preparation/execution chain to:

```text
one common target-size preparation
-> optional paired-seed diagnostic (recommendation or typed no-recommendation)
-> operator-owned provisional ordered collection
-> cross-validate atomic collection freeze
-> per-frozen-size CV and fresh final production
```

2. replace “one selected size or typed scientific failure” with the diagnostic truth: one recommended size or typed no-recommendation outcome;
3. replace campaign-global `alter T_selected` wording with the frozen collection / explicitly per-binding `T_N` semantics;
4. preserve legitimate singular “selected binding” wording only where the paragraph is explicitly discussing one per-size descendant, not the campaign-global control flow;
5. strengthen the **existing** doc tests with exact negative assertions for the stale Part-VI phrases; do not create another linter/scanner;
6. regenerate `docs/arch_manuals/mlff_training_data_architecture.md`, its tracked PDF/manifest, and any other derivative whose source graph includes Part VI.

No runtime/scientific redesign is authorized or required.

---

## Final closure acceptance after R10/R11

If the repair changes only documentation/tests and restores historical fixture/source artifacts, reuse the still-valid 200-pass Round-3 product-runtime affected suite. Execute fresh:

```text
pytest -q tests/test_mlff_doc_arch1_specification.py tests/test_mlff_data9b3_campaign_cli_specification.py
pytest -q tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_target_size_p6_p5a6_compatibility.py
python -m compileall mdstats tests qualification/p6-p5a6-compat
```

plus the exact R10 real-owner compatibility route above and the repository documentation/PDF build. The preserved-workspace test must execute rather than skip.

If any product runtime, state schema, serializer, currentness owner, compatibility reader, or post-selection consumer changes, re-derive the affected surface and rerun the complete relevant regression/integration suite rather than reusing Round-3 runtime evidence.

Record one resolvable final candidate SHA and identify any evidence-only/PDF-only descendants explicitly.

Production-scale GPU/real-data qualification remains deferred.

## Simplicity / anti-shortcut trigger

Stop and re-derive before adding any cache, persisted summary, compatibility adapter, migration, synthetic compatibility fixture, duplicate result-view state, second AST/doc scanner, or special-case runtime flag. The remaining problems are missing historical evidence and stale normative prose; solve those at the evidence/document owners rather than adding product machinery.

---

## Implementation evidence (Round 4)

```text
executable_head: bb4befc4158049873f186acb28de83ba26da08c8
python: 3.11.15
mace: 0.3.16
torch: 2.13.0+cu126
e3nn: 0.4.4
pytest: 9.1.1
cpu: 1 core
```

### 1. R10 — Supported P5A6 unchanged-workspace compatibility boundary established
- Recovered original P5A6-produced workspace `qualification/p6-p5a6-compat/workspace/` and authenticated against committed manifests (`P5A6_FIXTURE_IDENTITY.json`, `P5A6_FIXTURE_CONTENT_MANIFEST.json`, `P5A6_FIXTURE_DATABASE_SNAPSHOT.json`).
- Updated `mdstats/training_data/campaign_post_selection.py`:
  - Wire schema support for native `mdstats.post-selection-binding.v1` deserialization (`POST_SELECTION_BINDING_V1_SCHEMA`) using `legacy_v1_campaign_state_revision`, `legacy_v1_execution_head_digest`, and `legacy_v1_reducer_state_digest` to avoid AST collision with forbidden current dataclass fields.
  - Native prerework schema loading in `load_current_selected_training_contexts` -> `_load_legacy_prerework_training_contexts`: authenticates frame authority, neutral statistical base, and split exclusion matching P5A6 hashes 100%, and builds `_LegacyExperimentDefinition` with M3 membership extracted from the materialization of final production runs.
- Updated `mdstats/training_data/campaign_post_selection_runtime.py`:
  - Handled `selected.frozen is None` for historical bindings and resolved legacy method identity from post-selection evidence store.
- Executed qualification driver:
  ```bash
  conda run -n mace python qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
  ```
  Outcome: All three phases PASS:
  - `P5A6 -> P6 authenticated current-generation compatibility: PASS`
  - `P6 -> P6 current-generation restart: PASS`
  - `V5/V6 -> reject-before-reuse: PASS`
- Preserved workspace remained 100% byte-for-byte intact with zero unexpected files created.
- Zero pre-load migration or rewrite; zero compatibility adapters or synthetic fixtures introduced.

### 2. R11 — Authoritative Part VI documentation reconciliation
- Reconciled authoritative normative architecture `docs/arch_manuals/mlff_training_data/60_execution_performance.md`:
  - Preparation/execution chain updated to:
    ```text
    one common target-size preparation
    -> optional paired-seed diagnostic (recommendation or typed no-recommendation)
    -> operator-owned provisional ordered collection
    -> cross-validate atomic collection freeze
    -> per-frozen-size CV and fresh final production
    ```
  - Replaced stale scalar screen outcome with: "one recommended size or typed no-recommendation outcome".
  - Replaced global `alter T_selected` phrasing with explicitly per-binding `T_N` semantics: "alter the frozen collection or that size's exact membership `T_N`".
- Reassembled composite manual `docs/arch_manuals/mlff_training_data_architecture.md`.
- Regenerated tracked PDF and manifest:
  ```bash
  conda run -n mace python docs/build_pdfs.py build --changed-path docs/arch_manuals/mlff_training_data/60_execution_performance.md
  ```
- Strengthened doc specifications in `tests/test_mlff_doc_arch1_specification.py` with exact negative assertions against stale Part VI phrases (`paired-seed candidate screen\n  -> selected binding`, `one selected size or typed scientific failure`, `alter \`T_selected\``).

### 3. Closure acceptance verification
- Bytecode compilation:
  ```bash
  conda run -n mace python -m compileall mdstats tests qualification/p6-p5a6-compat
  ```
  Outcome: Clean, 0 errors.
- Specification & destructive closure & compatibility suite:
  ```bash
  conda run -n mace pytest -q tests/test_mlff_doc_arch1_specification.py tests/test_mlff_data9b3_campaign_cli_specification.py tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_target_size_p6_p5a6_compatibility.py
  ```
  Outcome: **44 passed, 0 skipped in 128.64s**.
- 10-module affected target-size & result-view suite:
  ```bash
  conda run -n mace pytest -q tests/test_mlff_target_size_multi_selection.py tests/test_mlff_target_size_provisional_selection.py tests/test_mlff_target_size_p4d_runtime_cutover.py tests/test_mlff_target_size_multi_size_integration.py tests/test_mlff_campaign_prepare_boundary.py tests/test_mlff_target_size_p4e_terminal_and_invalidation.py tests/test_mlff_target_size_p5a_selected_context.py tests/test_mlff_target_size_p5f_structure.py tests/test_mlff_target_size_p4c_cross_store_adoption.py tests/test_mlff_target_size_p4f_storage_docs_structure.py
  ```
  Outcome: **200 passed in 955.85s**.

