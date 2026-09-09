---
kind: implementation-workplan
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 5.16.0
status: active
created_date: 2026-09-08
baseline_branch: fix/mlff-p5-single-source-replay-lineage-adapter
baseline_commit: 0dcb43611409b540b85089912761ffc0394f166c
implementation_branch: fix/mlff-downstream-integration-closure
scope: downstream MLFF integration closure from post-selection CV through final production/publication, restart/currentness, and qualification entry
supersedes: workplans/active/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md
parent_authority: current MLFF training-data architecture manual plus P5/P7 current specifications and accepted multi-size design
review_verdict: NO-PASS / implementation repair required
design_disposition: preserve frozen science and ownership; simplify duplicated Tier-2 path/configuration machinery and reconcile current documentation
---

# MLFF downstream integration closure workplan

## 0. Executive disposition and consolidation

This workplan is the snapshot-complete Software Design -> Implementation handoff for the next downstream MLFF repair round.

The narrow single-source replay-lineage adapter defect is already implemented on the baseline candidate `0dcb43611409b540b85089912761ffc0394f166c`: P5 now consumes the canonical single-source `source` and `split` owners directly, mandatory lineage fields are populated, and the real producer -> adapter -> digest seam has regression coverage. That bounded plan is therefore retired as a current implementation authority. Its still-binding preservation requirements are incorporated here where relevant.

The broader review of the assembled downstream chain remains **NO-PASS**. The remaining blockers are not a failure of the frozen MLFF scientific method or of the multi-size target-size design. They are integration nonconformances and documentation drift across configuration/path ownership, P5 execution/restart, multi-size CV orchestration, and P7 configuration intake.

This plan deliberately does **not** invent a new path registry, compatibility database, migration layer, publication owner, training wrapper, or downstream state machine. Repeated path interpretation has now exposed a small family of duplicated Tier-2 authorities; the repair must consolidate or rewire those existing routes before adding any durable machinery.

---

## 1. Objective / product invariants / non-goals

### 1.1 Product and scientific invariants

The repaired downstream campaign must satisfy all of the following:

1. A campaign configuration has one deterministic path interpretation. A configured path containing `~` expands to the user home; an ordinary relative path is interpreted relative to the campaign configuration directory, not the process CWD; equivalent invocation CWDs cannot change the file a campaign means.
2. Foundation **scientific identity** is the authenticated checkpoint content/head/family identity. The filesystem path is a runtime locator only. Relocating byte-identical foundation content with the same selected head must not change the method identity or by itself invalidate CV/final authorization.
3. Changing foundation bytes, selected head, family, or another method-semantic input must continue to invalidate stale descendants fail-closed.
4. P5 cross-validation validates the frozen training method for every frozen selected size, each against its own exact `T_N`, own `H_cv`, and own binding. No selected size can borrow membership, horizon, CV evidence, or current pointers from a sibling.
5. A campaign-level CV pass requires every frozen size to pass every required fold/seed predicate. A methodological rejection of one size must not silently remove another size from the frozen experiment.
6. Final production remains a collection-wide admission barrier: no new production run starts unless every frozen size has current accepted CV ancestry of its own.
7. Final production remains fresh from the accepted foundation/initialization, with fresh optimizer/RNG/run state, on each size's complete exact `T_N` and frozen `H_prod`. Screen or CV checkpoints are never production parents.
8. P5 owns the final-production publication decision and currentness-fenced publication. P7 consumes that exact P5 product read-only; P7 cannot rerank or alter target size, CV acceptance, production seeds, representatives, or published members.
9. Multi-size completion remains terminal and non-release-qualified until a separate explicit release-selection design exists. No qualification command may silently choose one size.
10. For a single-size campaign, ordinary nonlocked qualification may be routed by public orchestration after current final production, but locked activation remains explicit and is never reached automatically.
11. Restart/currentness remains fail-closed and useful: completed accepted evidence is preserved and reauthenticated; incomplete/stale execution scratch may be reclaimed only under established ownership and may not become a second scientific authority.
12. Replay training exposure and independent TRUE_DFT replay admissibility remain distinct. The completed single-source replay-lineage repair at baseline must not regress.
13. Full production/GPU/CuEq/LAMMPS qualification is outside this implementation round. Functional, bounded real-owner integration and CPU-safe dependency-facing evidence are required; long target-machine qualification remains a later release activity.

### 1.2 Non-goals

This work does not:

- change target-size recommendation science, candidate ladder, nested-prefix membership, practical-equivalence semantics, or operator selection authority;
- change CV fold science, acceptance thresholds, target-only ranking, replay admissibility role, production committee policy, or P7 scientific qualification thresholds;
- invent a cross-size release selector or qualification reducer;
- introduce a new configuration schema merely to fix path handling;
- make filesystem path a scientific digest input;
- add aliases/fallbacks that accept several competing path interpretations;
- migrate historical accepted scientific evidence merely because an execution locator moved;
- weaken immutable publication/currentness checks;
- treat MACE/PyTorch legacy TorchScript warnings as causal to these failures.

---

## 2. Final review findings and disposition

### F1 — BLOCKER: P5 foundation path has split-brain configuration resolution

The campaign CLI already has canonical configured-path semantics via `_resolve_path()` / `_path_cfg()`: `expanduser()`, then config-directory-relative resolution for non-absolute values, then canonical resolution.

P5 bypasses that owner. `resolve_post_selection_method_policies()` reads raw `[paths].foundation_model` and currently resolves the execution locator with `Path(f_model_raw).resolve()`, while foundation inspection separately uses `Path(path).expanduser().resolve()`. Both ordinary relative paths and `~/...` can therefore disagree with `doctor` and with each other, and behavior can depend on process CWD.

The observed failure:

```text
Foundation model file is missing:
.../FP32/~/QE/.../mace-mpa-0-medium.model
```

is one concrete manifestation of this split.

**Disposition:** implementation nonconformance. Restore one canonical configured-path owner; do not patch only the failing `Path.resolve()` call.

### F2 — BLOCKER: foundation runtime locator is over-bound inside the immutable P5 execution representation

P5 materialization writes `foundation_model` into the internal immutable MACE configuration. The trainer later compares that stored locator with the current request locator and the executable projection can carry the stored path into MACE.

That contradicts the already-frozen P5 rule that the path is a locator only while checkpoint content/head is scientific identity. A byte-identical checkpoint moved from path A to path B can retain the same method identity yet fail restart/execution solely because the stored locator differs.

**Disposition:** retain content/head authentication and make the currently authenticated runtime locator authoritative only for launch. Do not weaken foundation byte/head verification.

### F3 — BLOCKER / recovery acceptance gap: the fix must recover the same failed workspace

The observed failure occurs after materialization is created but before accepted training evidence exists. Correcting canonical path resolution can change the generated internal config bytes for the same logical run, so a naive create-or-verify retry can collide with stale pre-fix materialization.

P5 already executes a run under `post_selection_run_activity_lease(run_root)`. The next repair must work in the same workspace left by a pre-fix failure without requiring manual deletion. Existing accepted progress/completion must remain immutable and reusable; only unaccepted execution-local scratch may be reconciled/reclaimed, and only while ownership is established.

**Disposition:** acceptance requirement on the existing recovery owner, not permission for a new restart state machine.

### F4 — HIGH: a dead `PostSelectionMethodPolicies.replay_context` interface carries another CWD-dependent locator

`PostSelectionMethodPolicies.replay_context` is declared and populated but has no downstream production consumer. Its value is produced by `single_source_replay_config_from_campaign(config)` without the campaign config directory, so a relative replay source may be resolved relative to process CWD even though the real replay execution path later rebuilds the canonical context with `paths.config_dir`.

**Disposition:** retire the dead transport field rather than preserving or special-casing it. Any semantic replay-policy resolution still needed by P5 must use config-directory-aware or path-free canonical semantics.

### F5 — HIGH: path-derived replay baseline fallback contradicts canonical foundation identity

Replay admissibility normally keys the foundation baseline by `foundation_identity.canonical_content_digest`, but retains a fallback equivalent to `digest({"foundation_model": foundation_model})` when foundation identity is absent.

A valid foundation-backed P5 run is already required to have authenticated canonical foundation identity. A path-derived fallback therefore weakens the ownership model and can reintroduce location into what should be content/head identity.

**Disposition:** remove the fallback and fail closed if an allegedly foundation-backed replay evaluation reaches this boundary without its required foundation identity.

### F6 — HIGH: multi-size CV says "every size" but stops at the first methodological rejection

The frozen multi-size architecture requires cross-validation once per frozen size in frozen order and a campaign pass only when every size is accepted. The current implementation appends the first rejection and then `break`s from the size loop.

This makes later siblings unreachable on an unchanged frozen design when an earlier size produces a legitimate methodological rejection. The collection remains frozen, so silently not evaluating the remaining requested sizes contradicts the defined experiment.

**Disposition:** methodological rejection is accumulated as a per-size result; continue through the remaining frozen sizes. Hard corruption/execution exceptions may still abort because they are not valid scientific verdicts.

### F7 — HIGH / latent downstream defect: P7 reference-root configuration repeats the tilde/canonicalization bug

`qualification.runtime._reference_root()` interprets an explicit reference root with `Path(str(configured))` and config-directory joining but without home expansion/canonical resolution. `~/qualification-reference` therefore becomes `<config-dir>/~/qualification-reference`.

**Disposition:** consume the same canonical configured-path semantics as the campaign rather than keeping a second path interpreter.

### F8 — DOCUMENTATION AUTHORITY DRIFT: current architecture contains contradictory downstream ownership statements

The current canonical architecture/manual set contains at least these contradictions:

1. an ownership-table row still implies final-production publication belongs to P7, while the same current architecture and executable owner place the publication decision in P5 before qualification;
2. one ownership chapter says `advance` never runs qualification, while the current lifecycle router and later accepted assembled integration permit ordinary nonlocked `qualification run` and still forbid locked activation;
3. older final-production prose says production runs under mutable `[training].max_num_epochs`, while the current multi-size architecture freezes per-size `H_prod_i` at selection/freeze and P5 consumes that frozen role horizon.

**Disposition:** reconcile the editable numbered architecture chapters to the already-accepted current owner model, then deterministically regenerate the assembled Markdown/PDF. Do not patch the generated assembled manual independently.

### F9 — WORKPLAN/INDEX DRIFT: active coordination state is inaccurate

`workplans/active/README.md` says there are no active MLFF workplans while the narrow replay repair plan is present. The narrow plan is now implemented and superseded by this broader closure.

**Disposition:** retire the narrow plan and make the active index name this workplan as the sole current downstream repair authority.

---

## 3. Frozen high-level architecture and engineering envelope

The following is deliberately Frozen for this implementation cycle.

### 3.1 One configured-path semantic owner

All campaign/user path semantics touched by this work descend from one canonical interpretation:

```text
raw configured locator
  -> expand `~`
  -> if relative, anchor to campaign configuration directory
  -> canonical resolved path
  -> consuming owner
```

The exact helper/module name is delegated. What is Frozen is the absence of independent CWD-based interpretations for the same configured field.

### 3.2 Foundation identity and locator separation

```text
canonical runtime locator -----------------------> launch / filesystem access
          |
          +-> inspect exact bytes/head/family ---> canonical foundation identity
                                                   |
                                                   +-> method / authorization identity
```

The locator does not become scientific identity. Execution must still authenticate that the file reached through the current locator has the exact bytes/head/family bound by the method.

### 3.3 Multi-size post-selection control

```text
frozen ordered collection [(N_i, T_i, H_cv_i, H_prod_i)]
  -> for each N_i: complete CV methodology
  -> campaign CV accepted iff every N_i accepted
  -> collection-wide production admission barrier
  -> for each N_i: fresh final production under H_prod_i
  -> one P5 publication decision per binding
```

There is no cross-size reducer for ranking/release and no silent subset execution.

### 3.4 Publication and qualification ownership

P5 owns the final publication decision and currentness-fenced product. P7 is a downstream consumer. Qualification cannot alter P5 choices.

For single-size campaigns, orchestration may route ordinary nonlocked qualification after production. Locked activation remains explicit-only. For multi-size campaigns, all-production-complete is terminal/non-release-qualified and no qualification attempt is created.

### 3.5 Recovery ownership

Authenticated completed/accepted P5 evidence is durable authority. Incomplete execution-local materialization/checkpoint state has only the recovery meaning granted by existing P5/TRAIN2 owners. Destructive reconciliation is allowed only when ownership is established and may not delete accepted evidence.

---

## 4. Delegated solution space and simplification rules

Implementation may choose the minimum coherent realization that preserves Section 3. In particular, it may:

- reuse `_resolve_path()` directly, relocate that helper to a neutral campaign/config module, or replace duplicated local path handling with an equivalent single canonical resolver;
- change `resolve_post_selection_method_policies()` arguments so production provides `paths.config_dir` or an already-resolved foundation locator;
- remove `PostSelectionMethodPolicies.replay_context` outright;
- adjust how the immutable internal P5 config represents a foundation locator, provided scientific identity remains path-free and the executable launch receives the authenticated current locator;
- reuse/reconcile stale unaccepted materialization under the existing run activity lease, or safely rebuild it, provided restart semantics and immutable accepted evidence are preserved;
- reorganize focused tests around a shared fixture if that reduces duplication.

Implementation must **not** add a second path registry, path alias table, compatibility lookup chain, migration database, second replay context, second foundation identity, mutable "current materialization" pointer, broad cleanup daemon, or new campaign state machine.

If fixing the affected path family requires preserving multiple synchronized locator authorities, stop and simplify/rederive the owner boundary instead.

---

## 5. Implementation obligations

### O1 — Canonicalize downstream campaign path intake at the actual configuration boundary

**Concern:** the same TOML value currently means different files to `doctor`, P5 identity, P5 execution, and P7.

**Required end state:** foundation model and P7 reference-root resolution use the same `~`/config-dir-relative/canonical semantics as other campaign paths. Production behavior is invariant to invocation CWD.

**Preservation:** absolute paths continue to work unchanged; missing files still fail before expensive work; no path is added to scientific identity.

**Acceptance:** execute equivalent configurations from a CWD deliberately different from the config directory for absolute, `~/...`, and `../...` forms and prove all affected owners resolve the intended path.

### O2 — Make P5 foundation identity/execution consume one canonical locator

**Concern:** foundation inspection and trainer request currently derive different paths from raw configuration.

**Required end state:** the exact same canonical foundation locator feeds foundation inspection/authentication and the runtime request. The trainer continues to hash the reached file and compare it against canonical foundation identity before launch.

**Anti-shortcut:** adding `.expanduser()` to only one existing `Path.resolve()` call is insufficient because ordinary relative paths would remain CWD-dependent.

### O3 — Keep the foundation locator out of scientific authorization and use the authenticated current locator for MACE launch

**Concern:** immutable internal config currently over-binds the pathname and trainer equality checks can reject a byte-identical relocation.

**Required end state:** same foundation bytes/head/family at a different valid locator preserve method identity and are executable after reauthentication. The transient dependency-facing MACE config uses the currently authenticated runtime path. A stale/internal locator cannot override the request locator.

**Preservation:** changed bytes/head/family must still fail closed; the internal method/config digest and TRAIN2 authority must remain mutually consistent.

**Suggested realization (delegated):** treat any stored internal locator as execution provenance/non-authoritative metadata and inject/overwrite the executable `foundation_model` from the authenticated `PostSelectionRungRequest` after identity checks, or use an equivalent simpler representation that does not make locator equality an authorization condition.

### O4 — Same-workspace recovery after the pre-fix path failure

**Concern:** the failed run can leave immutable materialization bytes before accepted training evidence exists.

**Required end state:** after upgrading to the fix, rerunning `cross-validate` in the same workspace proceeds without requiring manual deletion solely because the pre-fix locator representation changed.

Required cases:

- pre-fix failure after materialization but before accepted TRAIN2 progress -> fixed retry safely reuses or reclaims only stale unaccepted scratch and launches with the canonical locator;
- accepted/restart-authenticatable progress exists -> the repair does not delete it to force a fresh run;
- another live process owns the same P5 run root -> existing activity lease/ownership prevents destructive interference;
- corrupt state remains a typed failure, not silently discarded as "stale".

**Anti-shortcut:** a test that starts from a fresh temporary directory does not close this requirement.

### O5 — Remove dangling replay path state and the path-derived foundation fallback

**Required end state:**

- remove unused `PostSelectionMethodPolicies.replay_context` or prove a real current consumer requires it; do not retain a dead locator carrier merely for compatibility with tests;
- any remaining single-source replay policy parsing in P5 receives config-directory-aware/path-free semantics rather than process-CWD semantics;
- replay baseline evaluation requires canonical foundation identity and contains no path-derived substitute such as `digest({"foundation_model": ...})`.

**Acceptance:** structural/source census over the affected P5 family plus focused runtime tests. A valid foundation-backed replay path without canonical foundation identity must fail closed.

### O6 — Complete every frozen size's CV verdict before reducing a methodological campaign rejection

**Required end state:** a valid rejection for size `N_i` is recorded/accumulated and the command continues to later frozen sizes. After all requested sizes have valid verdicts, campaign CV is failed if any rejected. Existing sibling evidence remains reusable.

Hard execution, corruption, lineage, or authority exceptions may still abort immediately because they do not constitute a valid scientific CV verdict.

**Acceptance boundary:** real `execute_current_cross_validate` / P5 orchestration with expensive training replaced only below the run owner. With frozen `[N1, N2]`, force `N1` to a valid rejection and `N2` to a valid acceptance (and the converse in a second case). Prove both sizes execute/publish their per-size evidence and the overall command rejects; no production job is authorized.

### O7 — Canonicalize P7 reference-root path semantics without opening multi-size qualification

**Required end state:** explicit `[qualification.reference].root` supports the same absolute/tilde/config-relative semantics and is CWD-independent. Default workspace-owned reference root remains unchanged.

**Preservation:** multi-size qualification continues to fail closed before attempt creation; locked activation remains explicit-only.

### O8 — Reconcile current architecture/manual authority

Update only the authoritative editable chapter sources needed to make the current model self-consistent:

- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md` — final-production prose must describe frozen per-size `H_prod_i`, not a mutable post-freeze `[training].max_num_epochs` as direct authority;
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md` — preserve collection-wide CV/production semantics and multi-size terminal boundary; reconcile any stale command wording if affected;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md` — P5 owns final publication; P7 consumes it; ordinary nonlocked single-size qualification is routable by `advance`, locked activation never is; multi-size remains terminal.

Then regenerate `docs/arch_manuals/mlff_training_data_architecture.md` from the chapter sources with the repository assembler and regenerate/verify the tracked PDF through the documented publication flow. Do not directly hand-edit the generated assembled Markdown/PDF as independent authority.

Review the P5/P7 specifications and CLI user guide for the same statements; edit only those that actually conflict after the architecture rewrite.

### O9 — Preserve the completed replay-lineage adapter repair

The baseline `0dcb436...` source/split rewire and its TRUE_DFT/pseudolabel/restart/mutation coverage remain accepted baseline behavior. Do not reintroduce persistence-record names at the runtime-context boundary, make mandatory single-source lineage optional, or substitute path identity for source/split content identity.

---

## 6. Implementation authority

### Frozen

- Section 1 product/scientific invariants.
- Section 3 high-level ownership/control architecture.
- One canonical configured-path semantic for affected campaign fields.
- Foundation path is locator-only; bytes/head/family own scientific identity.
- Every frozen size receives a valid CV verdict unless execution fails before a scientific verdict exists.
- Collection-wide production admission barrier.
- P5 final publication ownership / P7 consumer-only role.
- Single-size ordinary nonlocked qualification may be routed automatically; locked activation may not.
- Multi-size completion is terminal/non-release-qualified.
- Same-workspace recovery must not require manual deletion solely for this repair.

### Delegated

- exact path-helper module/name/signature;
- exact `PostSelectionMethodPolicies` field layout after dead-field cleanup;
- whether a stored internal foundation locator is removed, retained as non-authoritative provenance, or normalized differently;
- exact stale-unaccepted-scratch reconciliation mechanics inside existing ownership/recovery boundaries;
- test fixture factoring and fake MACE implementation below the real owner boundary;
- exact documentation sentence structure.

### Reopen only on evidence

Return to Software Design only if implementation demonstrates one of:

1. campaign relative-path semantics are intentionally different for a governed downstream field and that difference is documented by a higher product contract;
2. foundation pathname, rather than checkpoint content/head/family, is genuinely required as scientific identity;
3. a supported accepted P5 evidence format cannot remain restart-safe without a durable migration mechanism;
4. fail-fast-after-first-CV-rejection is an intentional scientific/cost policy that must replace the current all-size experiment semantics;
5. P7, rather than P5, is intended to choose final production membership/publication;
6. automatic ordinary qualification from `advance` must be removed as a product-level lifecycle decision rather than documentation drift.

Absent such evidence, do not broaden into architectural redesign.

---

## 7. Affected surface

Expected executable owners/consumers include at least:

- `mdstats/training_data/_campaign_cli_core.py` — canonical campaign path semantics / context construction as applicable;
- `mdstats/training_data/post_selection_identity.py` — P5 method/foundation/replay policy resolution and dead replay field;
- `mdstats/training_data/campaign_post_selection_runtime.py` — context assembly, foundation request routing, replay baseline identity, multi-size CV orchestration, restart/run-root owner;
- `mdstats/training_data/post_selection_execution.py` — immutable internal MACE config, authenticated request validation, dependency-facing executable projection;
- `mdstats/training_data/qualification/runtime.py` — reference-root resolution;
- `mdstats/training_data/campaign_lifecycle.py` and `qualification/commands.py` — inspect for semantic consistency; change only if implementation evidence shows code, not docs, is wrong;
- path/currentness/storage owners only to the extent same-workspace recovery actually crosses them.

Expected tests include at least:

- `tests/test_mlff_target_size_p5_r7_guards.py`;
- `tests/test_mlff_target_size_p5_r9_guards.py`;
- `tests/test_mlff_target_size_p5_r10_guards.py`;
- `tests/test_mlff_target_size_p5_r11_guards.py`;
- `tests/test_mlff_mace_executable_config.py`;
- `tests/test_mlff_mace_execution_semantics.py`;
- `tests/test_mlff_mace_execution_semantics_assembled.py`;
- `tests/test_mlff_target_size_multi_selection.py`;
- `tests/test_mlff_target_size_multi_size_integration.py` or current equivalent;
- `tests/test_mlff_campaign_assembled_lifecycle.py`;
- `tests/test_mlff_p7_post_production_qualification.py`;
- affected qualification/storage integration tests if reference-root/restart representation reaches them.

Documentation owners:

- `docs/arch_manuals/mlff_training_data/{40,50,80}_*.md`;
- generated `docs/arch_manuals/mlff_training_data_architecture.md` and PDF/manifest through the official builder;
- affected P5/P7 specs and CLI guide only where reconciliation finds a real contradiction;
- `workplans/active/README.md`.

This list is provisional. Implementation must re-derive the final affected surface from the assembled candidate.

---

## 8. Task-specific acceptance and oracle strength

### 8.1 Config-path metamorphic matrix

Use one campaign config directory and invoke from at least one different CWD. Exercise the same foundation bytes under:

```text
absolute path
~/... path
../... config-relative path
```

For each supported representation prove the intended canonical path is the same at the relevant owner boundary and that `doctor`, P5 context/identity, P5 trainer request, and dependency-facing launch do not disagree.

A test that only calls a path helper is insufficient.

### 8.2 Foundation relocation metamorphic relation

Given identical bytes/head/family at paths A and B:

```text
method_identity(A) == method_identity(B)
```

and an interrupted/current P5 run may resume/re-execute from B after authenticating those bytes. Conversely, changing bytes or head must change/reject the scientific identity and stale descendants.

### 8.3 Pre-fix failure recovery counterfactual

Construct a workspace using the pre-repair behavior far enough to publish the same kind of materialization involved in the observed failure, then run the corrected assembled owner on that same workspace.

Required observables:

- no manual file deletion in the harness;
- no accepted evidence is erased;
- stale unaccepted locator-only scratch cannot block forever;
- the corrected launch reaches the intended foundation checkpoint;
- corrupt/foreign accepted state still fails closed.

### 8.4 Multi-size rejection completeness

Real orchestration, bounded numerical doubles below it:

```text
frozen [N1, N2]
N1 -> valid rejection
N2 -> valid acceptance
=> both verdicts/evidence exist, campaign rejects, production blocked
```

and the converse ordering. This test must fail under the current `break` implementation.

### 8.5 P7 reference-root path matrix

With single-size current final publication, resolve/publish a bounded qualification reference request under absolute, tilde, and config-relative roots from a non-config CWD. The request must land under the intended root. Do not require external DFT completion to prove this locator contract.

### 8.6 Publication/currentness preservation

Existing P5 final-publication tests must continue to prove:

- publication decision is made before P7;
- currentness/reclosure authenticates selected binding, final plan/policy, method, CV authorization, M3 lineage, completion, committee policy, member evidence, and executable predecessor identity as currently required;
- P7 cannot change published membership.

### 8.7 Structural/absence evidence

Use Semgrep/AST/source inspection when available, or a bounded equivalent fallback, to establish at minimum:

- no affected P5 production path independently interprets raw `foundation_model` with process-CWD semantics;
- no P7 reference-root duplicate interpretation remains;
- no path-derived fallback stands in for required canonical foundation identity;
- `PostSelectionMethodPolicies.replay_context` is removed if it remains consumerless;
- no second path resolver/alias/fallback was added to preserve the defect.

Validate any acceptance-critical structural rule against known-positive and known-negative constructs before treating zero findings as evidence.

---

## 9. Implementation sequence

### Stage A — canonical downstream path/foundation/restart closure

One coherent stage because the configuration, identity, materialization, trainer request, and retry semantics are one failing chain.

Implement O1-O5 together:

- consolidate path interpretation;
- route one canonical foundation locator to identity and execution;
- make executable launch use that authenticated current locator without pathname authorization;
- remove dead replay context/path-derived fallback;
- close same-workspace pre-fix recovery.

Then run focused path/identity/restart tests plus the affected P5/MACE regression subset before proceeding.

### Stage B — multi-size CV and P7 downstream closure

Implement O6-O7:

- complete all valid per-size CV verdicts before campaign rejection reduction;
- canonicalize explicit qualification reference root;
- preserve multi-size terminal boundary and explicit-only locked activation.

Run focused multi-size/lifecycle/P7 regression plus Stage A regressions that share configuration owners.

### Stage C — architecture/documentation reconciliation and final assembled acceptance

Implement O8 and verify O9:

- edit authoritative chapter sources;
- regenerate assembled architecture Markdown/PDF through the official source graph;
- reconcile affected spec/guide statements;
- update active workplan index;
- re-derive final affected surface;
- run final complete affected regression and assembled integration on the final candidate.

Documentation edits do not excuse executable divergence; executable repair and documentation must converge on the same owner model.

---

## 10. Minimum validation commands / suites

Implementation should map to current filenames, but the minimum intended coverage is:

```bash
pytest -q \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r9_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_mace_execution_semantics_assembled.py
```

Then the downstream orchestration surface:

```bash
pytest -q \
  tests/test_mlff_target_size_multi_selection.py \
  tests/test_mlff_target_size_multi_size_integration.py \
  tests/test_mlff_campaign_assembled_lifecycle.py \
  tests/test_mlff_p7_post_production_qualification.py
```

Then broader affected P5/P7/campaign regression using the repository's current test layout. If impact cannot be bounded confidently, use the existing broader MLFF/campaign/storage selection and compare new failures with the true unmodified baseline rather than suppressing them.

Run the repository's configured fast Python static/lint/type checks for changed files when available.

For documentation, run the MLFF architecture assembler and the official PDF publication/verification flow required by repository documentation ownership. The generated assembled Markdown must be byte-deterministic from chapter sources, and the tracked PDF must be regenerated/render-verified if affected by repository policy.

A skipped/unavailable required real-owner path test is not a pass. Long production/GPU qualification remains deferred.

---

## 11. Acceptance checklist

Implementation is ready for independent Software Design review only when all are true:

```text
[ ] baseline single-source replay lineage repair still passes
[ ] foundation path semantics are identical across doctor/P5 identity/P5 execution
[ ] absolute, tilde, and config-relative paths are CWD-independent
[ ] no direct raw-foundation CWD resolver remains in affected P5 production code
[ ] same bytes/head relocation preserves method identity
[ ] relocated same checkpoint can execute/recover through the real P5 owner
[ ] changed bytes/head still invalidate/fail closed
[ ] current MACE launch receives the authenticated current locator
[ ] stored/internal locator cannot override current authenticated locator
[ ] same workspace left by pre-fix materialization failure recovers without manual deletion
[ ] accepted/restart-authenticatable P5 evidence is never deleted by that recovery
[ ] live-writer ownership is respected during any destructive scratch reconciliation
[ ] dead replay_context field is removed if no real consumer is found
[ ] no path-derived foundation identity fallback remains
[ ] both sizes receive valid CV verdicts when the first size is methodologically rejected
[ ] campaign CV fails when any size rejects and production remains collection-wide blocked
[ ] successful sibling evidence remains reusable
[ ] P7 explicit reference root supports absolute/tilde/config-relative canonical semantics
[ ] multi-size qualification remains unavailable/terminal before attempt creation
[ ] locked activation remains explicit-only
[ ] P5 final publication/currentness/reclosure tests remain green
[ ] architecture chapters consistently state P5 publication ownership
[ ] architecture consistently states frozen per-size H_prod authority
[ ] architecture/current user contract consistently states ordinary nonlocked advance routing and locked prohibition
[ ] assembled architecture Markdown/PDF regenerated from canonical chapter sources
[ ] active workplan index names this plan and no superseded narrow plan remains active
[ ] focused stage-local regression passed after each executable stage
[ ] final affected-surface regression and assembled integration passed on one unchanged candidate
[ ] no new path registry/fallback/migration/state-machine machinery was introduced without a redesign trigger
```

---

## 12. Independent review gate

After Implementation reports completion, Software Design must reconstruct this contract from the current supplied artifacts and review the exact implementation candidate.

**PASS** requires both:

1. semantic/conformance closure of all Sections 1-11, including absence of duplicated path authority and documentation contradictions; and
2. executed final affected regression/integration through the real downstream owners.

Green helper tests are insufficient if the assembled CLI/P5/P7 owner path is still broken. Conversely, a successful production run cannot substitute for missing regression/currentness/restart evidence.

If the implementation accumulates another locator adapter, compatibility fallback, or duplicated synchronized config representation to satisfy these findings, treat that as a Tier-2 simplification failure and reduce the mechanism before accepting the repair.

---

## 13. Handoff summary

### Problem / product invariant

From post-selection CV through final publication and qualification entry, one campaign configuration and one frozen scientific design must mean the same thing to every downstream owner, independent of CWD or checkpoint relocation, while restart/currentness remains exact and multi-size experiments remain complete.

### Frozen architecture

One configured-path semantic; content/head foundation identity with locator-only path; complete per-size CV; collection-wide production barrier; P5 publication ownership; P7 consumer-only qualification; explicit-only locked activation; multi-size terminal/non-release boundary.

### Delegated implementation solution

Consolidate existing path/configuration wiring, remove dead/weak fallback state, make MACE launch consume the authenticated current locator, reconcile stale unaccepted execution scratch within existing ownership, remove the methodological-rejection loop break, and update the canonical documentation source graph.

### Required proof

CWD/path-form matrix, foundation relocation and byte-mutation counterfactuals, same-workspace pre-fix recovery, two-size first-rejection completeness, P7 reference-root matrix, preserved P5 publication/currentness tests, structural absence checks, and final assembled affected regression.

### Genuine unresolved risk

The main implementation risk is recovery interaction with pre-fix immutable P5 materialization already present in a user's workspace. The plan intentionally freezes the observable recovery outcome but leaves the minimum safe realization delegated so existing accepted TRAIN2/P5 evidence is not discarded merely to make the new representation convenient.
