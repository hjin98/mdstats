---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 5.16.0
status: reopened
created_date: 2026-09-08
last_design_closure_review_date: 2026-09-08
reviewed_candidate_head: 8c0e2426ce6f9248bf6b958d48570c140bcef147
reviewed_implementation_commit: cbfd43cabfbd5e26095a564b6bb4a9c9f3787638
reviewed_generated_docs_commit: 8c0e2426ce6f9248bf6b958d48570c140bcef147
implementation_review_verdict: no-pass
precedence: This file is the current binding review amendment to MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md. It supersedes its own earlier wording in place. Every non-conflicting product invariant, Frozen architecture decision, preservation requirement, non-goal, acceptance obligation, and redesign trigger in the parent workplan remains binding.
---

# MLFF downstream integration closure — implementation review reopen 1

## 0. Current verdict and routing

**NO-PASS / REOPENED.**

A second design-closure pass over the unchanged executable candidate confirms that the original implementation materially improved the downstream architecture, but the current handoff still has several implementation and acceptance gaps that must be closed before another independent Review.

No Frozen MLFF scientific or high-level architecture decision needs to change. The remaining defects are all Tier-2 integration/ownership errors under already accepted authority:

1. recovery currently treats unaccepted materialization as broadly disposable and does not distinguish valid obsolete representation from corruption/foreign state;
2. the recovery shortcut treats any nonempty checkpoint directory as restart-authenticatable progress instead of asking the existing TRAIN2 continuation owner;
3. foundation locator/identity separation was corrected, but the same path-overbinding defect remains sideways in replay: `pt_train_file` / `pt_valid_file` runtime locators are still hashed into immutable P5 materialization and authorized by pathname equality even though replay method/lineage identity is path-free;
4. the full foundation path-form execution matrix and structural negative oracle remain incomplete;
5. final affected pytest/static/integration evidence is still unavailable for the reviewed executable candidate.

Repair these in the existing owners. Do **not** add a migration database, compatibility registry, second materialization pointer, restart state machine, cleanup daemon, path alias table, second replay identity, or another lock/lease layer. Where the current helper shape makes safe classification awkward, alter/move/remove that helper rather than building machinery around it.

## 1. Accepted implementation surfaces — preserve unless new evidence invalidates them

The following source behavior is accepted and must survive the repair:

1. **Canonical configured-path owner.** `_common.resolve_configured_path()` is the shared campaign path semantic; `_campaign_cli_core` consumes it and P5 receives `paths.config_dir` for configured foundation resolution.
2. **Foundation locator/identity separation.** Immutable P5 MACE configuration no longer stores `foundation_model`. The current locator reaches `MacePostSelectionTrainer` through the authenticated request; the trainer hashes the reached checkpoint and checks canonical foundation identity/head before creating transient parser-facing configuration.
3. **Checkpoint/provider reconstruction.** P5/P7 provider reconstruction receives the current authenticated foundation locator explicitly rather than reading a stale immutable foundation pathname.
4. **Replay cleanup — partially accepted.** Removal of consumerless `PostSelectionMethodPolicies.replay_context`, config-directory-aware single-source policy parsing, canonical source/split lineage, and removal of the path-derived foundation-baseline digest fallback are accepted. **Replay execution locator handling is not accepted yet:** Section 3 below closes the remaining `pt_train_file` / `pt_valid_file` overbinding.
5. **Multi-size CV.** Methodological rejections are accumulated and later frozen sizes continue to valid per-size CV verdicts before campaign rejection is reduced. Hard execution/corruption/authority failures remain fail-fast.
6. **P7 reference-root path semantics.** Explicit qualification reference root uses the shared configured-path resolver and preserves the multi-size qualification boundary.
7. **Architecture documentation.** The authoritative 40/50/80 chapters now state frozen `H_prod_i`, P5 publication ownership/P7 consumer ownership, and ordinary-nonlocked-versus-locked `advance` routing consistently; the assembled manual/PDF was regenerated through the documentation workflow.
8. **Single-source replay lineage adapter.** The earlier runtime `source` / `split` rewire remains mandatory and fail-closed.
9. **P5 scientific replay semantics.** Replay training exposure remains distinct from independent TRUE_DFT replay admissibility; replay receives no target-ranking credit; current P5 method identity and replay lineage remain path-free and content/label/source/split based.

The repair must not reopen these surfaces merely because they are nearby.

---

## 2. R1 — make P5 materialization recovery integrity-aware, not deletion-by-absence

### 2.1 Current defect

`campaign_post_selection_runtime._reclaim_unaccepted_materialization(run_root, material_directory)` currently behaves approximately as:

```text
if materialization absent: return
if selected terminal files exist: preserve
if checkpoint directory contains anything: preserve
otherwise: delete materialization directory recursively
```

This is insufficient in two directions:

- it can erase malformed/checksum-inconsistent/foreign immutable materialization and silently turn corruption into absence;
- it treats the mere presence of any checkpoint-directory entry as proof that state is restart-authenticatable, so partial/truncated/foreign checkpoint residue can permanently block the intended same-workspace repair.

The parent O4 requirement remains authoritative: **corrupt state is a typed failure, not stale scratch.** The supported recovery need is narrower: internally valid unaccepted state whose only incompatible representation is a locator-only field retired by this closure must not block forever.

### 2.2 Do not freeze the current helper or its call order

The current helper is called before the owner has constructed enough of the current expected run/materialization context to compare old and new semantics. Its name, signature, existence, and early call position are Tier 2.

Implementation may move the classification into the materialization/create-or-verify boundary, pass the already-resolved expected run/materialization facts into a narrower helper, or remove the helper entirely in favor of direct owner-local reconciliation. Prefer the location where **both existing authenticated state and current expected state are available**. Do not add an outer recovery state machine.

### 2.3 Required classification

While holding the existing `post_selection_run_activity_lease(run_root)`, the real P5 owner must distinguish:

1. **No materialization exists** — ordinary current materialization proceeds.
2. **Current internally valid unaccepted materialization for this exact run** — ordinary idempotent create-or-verify/reuse succeeds; do not delete it gratuitously.
3. **Internally valid pre-fix locator-only materialization for this exact run** — if its only relevant difference from the current representation is a locator field retired by this closure, reconcile/rebuild the minimum necessary run-owned scratch so retry proceeds without operator deletion.
4. **Malformed, checksum/digest-inconsistent, unsupported-schema, or internally inconsistent materialization** — raise an existing typed P5/input/serialization error and preserve the evidence for diagnosis.
5. **Internally valid materialization belonging to a different run/method/preparation/artifact/semantic config** — typed failure and preserve it. Do not relabel it as locator-only compatibility.
6. **Valid restart-authenticatable TRAIN2 progress exists** — preserve and resume/reuse through existing TRAIN2/P5 owners. Never delete it merely to obtain a newer materialization spelling.
7. **Checkpoint files exist but do not authenticate as current continuation** — presence alone is not resumability. Use the existing TRAIN2 continuation authentication/currentness owner to distinguish valid continuation from partial/corrupt/foreign checkpoint state. Corrupt/foreign durable state fails typed and remains available for diagnosis unless an existing owner already classifies a specific file as disposable run-owned temporary scratch.
8. **Another live process owns the run root** — the existing activity lease is the liveness boundary. Do not add another lock.

Where applicable, reuse `PostSelectionMaterialization.from_dict`, immutable config SHA/content verification, run-plan identity, and existing TRAIN2 continuation validation rather than inventing parallel classifiers.

### 2.4 Exact comparison boundary

Do not add a new selected-binding field merely to make recovery convenient. Authenticate and compare through existing ownership:

- `PostSelectionMaterialization` schema/content digest;
- `run_plan_digest` and `run_identity`;
- `preparation_digest`;
- target/monitor/outer artifact identities and bytes as required by the existing owner;
- immutable internal MACE config SHA/content digest and its **path-free semantic content**;
- current run-plan/method/replay lineage already owning upstream binding/currentness.

A field absent from the existing authoritative graph is not a reason to duplicate it into materialization.

### 2.5 Minimum destructive scope

After authentication proves a supported obsolete locator-only representation, destroy/rewrite only what must change. Deleting the whole materialization tree is permitted only if it is demonstrably run-owned, unaccepted, and simpler/safer than preserving its valid generated artifacts. Do not use broad `shutil.rmtree` as the default substitute for classification.

This is a Tier-2 simplicity constraint, not a requirement to build partial-artifact reuse machinery.

### 2.6 Required recovery/failure tests through the real owner

Use deterministic bounded failure injection below the real P5 recovery/materialization owner. Required cases:

- **faithful pre-fix foundation-locator materialization:** old immutable config **and matching materialization record** are internally self-consistent; no accepted/checkpoint progress; corrected retry succeeds in the same workspace without harness deletion;
- **faithful pre-fix replay-locator materialization** if Section 3 retires replay locators from immutable config; corrected replay-enabled retry succeeds under the same rules;
- **corrupt config bytes:** mutate immutable config without updating its record; retry fails typed and does not delete/rewrite it;
- **corrupt materialization record:** malformed/unsupported/digest-mismatched record fails typed and remains present;
- **foreign internally valid materialization:** change a protected semantic beyond the explicitly retired locator-only fields while keeping the record internally consistent; retry fails typed and preserves it;
- **current unaccepted materialization:** idempotent current retry succeeds without destructive churn;
- **valid restartable continuation:** authenticate through existing TRAIN2 continuation owner and preserve/resume;
- **partial checkpoint residue:** representative lone/truncated/mismatched summary, companion, or raw checkpoint must not be treated as restart-authenticatable merely because the checkpoint directory is nonempty;
- **foreign checkpoint continuation:** plan/protocol/budget/LR/SHA mismatch fails typed and remains diagnostic evidence;
- **live-writer exclusion:** reuse existing run-activity-lease coverage if it reaches this exact destructive boundary; otherwise add one bounded real-owner concurrency case.

A helper-only test that directly constructs arbitrary directories cannot close the recovery claim.

---

## 3. R2 — finish locator/identity separation for replay execution

### 3.1 Evidence and governing authority

Current P5 authority already freezes these facts:

```text
replay method identity is path-free
exact replay bytes belong to replay plan/lineage
current replay lineage binds train/monitor content identity + SHA
single-source lineage additionally binds source content/SHA + split manifest
no replay lineage payload contains filesystem paths
```

`ReplaySourceArtifact` and `ReplayFileArtifact` likewise compute `content_digest` without their `path` field, and the replay source/index contract explicitly permits relocation of identical source content.

The current P5 execution representation nevertheless stores replay runtime locators in immutable config:

```text
pt_train_file = replay_resolution.train_path
pt_valid_file = replay_resolution.monitor_path
```

Those strings enter `mace_config_sha256`, `mace_config_digest`, and therefore immutable `PostSelectionMaterialization`. `MacePostSelectionTrainer` then resolves the stored paths and requires pathname equality with the current authenticated request paths. This makes relocation of byte-identical replay artifacts change/block immutable execution identity even though the accepted replay scientific authority is path-free.

This is the same semantic family as the already-fixed foundation locator defect and must close in the same workplan.

### 3.2 Required end state

For `multihead_replay`:

```text
replay train/TRUE_DFT monitor content + labels + source/split lineage
        -> scientific / authorization identity

current replay train/monitor filesystem locator
        -> authenticated runtime address only
        -> transient dependency-facing MACE config / TRAIN2 true-replay environment
```

Concretely:

- immutable P5 scientific/materialization identity must not authorize replay by absolute runtime pathname;
- trainer/request still requires both canonical replay artifacts and current locators;
- immediately before launch, trainer authenticates the current train/monitor files against their artifact SHA/content/label contracts and runtime-plan TRUE_DFT SHA exactly as today or more strongly;
- the transient parser-facing MACE config receives the **current authenticated** replay train and monitor locators;
- `MDSTATS_TRAIN2_TRUE_REPLAY_PATH` likewise receives the current authenticated TRUE_DFT monitor locator;
- remove pathname-equality authorization against an immutable `pt_train_file` / `pt_valid_file` rather than adding aliases/fallback lookup;
- replay source/train/monitor byte or lineage changes continue to invalidate/fail closed according to existing currentness rules;
- target/replay head names and MACE multihead configuration semantics remain unchanged.

The exact internal config representation is delegated. A clean realization may omit runtime replay locator fields from the immutable config and inject them only into the transient executable projection, analogous to foundation. Do not create a second replay context or locator registry.

### 3.3 Scope

Cover both currently supported P5 replay interfaces where they reach the same execution owner:

- canonical single-source replay;
- supported legacy split replay.

Do not expand replay scientific modes or revive unsupported historical compatibility paths.

### 3.4 Replay relocation and mutation acceptance

Add real-owner metamorphic evidence with expensive MACE arithmetic bounded below the trainer/inference seam:

1. resolve a replay-enabled current P5 context and record method/replay-lineage identities;
2. relocate/copy the authenticated replay train and independent TRUE_DFT monitor bytes to different valid current locators without changing bytes/content/label semantics;
3. re-resolve the real replay owner so artifacts point at the new locators;
4. prove method identity and replay-lineage identity are unchanged;
5. prove an interrupted/unaccepted P5 run can re-execute/recover using the new locators through `MacePostSelectionTrainer` / dependency projection without manual deletion;
6. prove parser-facing `pt_train_file`, `pt_valid_file`, and TRAIN2 TRUE-replay environment use the new authenticated locators;
7. mutate train bytes, monitor bytes, label/source/split identity, or monitored SHA as appropriate and prove authentication/currentness fails closed rather than accepting relocation as semantic equivalence.

Exercise at least one replay-enabled final-production/restart path or demonstrate through an existing real final-production test that the same `execute_post_selection_run` materialization/trainer owner is reached. CV-only evidence is insufficient to claim downstream closure through final production/publication.

---

## 4. R3 — complete the configured foundation path-form execution matrix

Parent O1/8.1 requires absolute, tilde, and config-relative foundation spellings to agree through `doctor`, P5 identity/context, **P5 trainer request, and dependency-facing launch** from a foreign CWD.

The existing matrix checks all three spellings through path resolution/policies/method identity, while the real P5 execution/relocation test exercises only config-relative spelling.

Parameterize/reuse the existing real-owner foundation-backed campaign test so all three spellings reach the trainer/dependency projection and assert the same canonical locator. Keep expensive numerical work below the accepted seam. Do not add another path framework.

---

## 5. R4 — strengthen structural/absence evidence over the actual defect families

Serena/Semgrep were not available in the review environment; implementation should use them if available and directly suitable. Otherwise use a bounded AST/source fallback with known-positive/known-negative self-tests.

The acceptance scan must be strong enough to reject representative variants of these forbidden families in the affected P5/P7 owners:

1. direct or wrapped raw configured-path resolution that bypasses `resolve_configured_path`, including `Path(raw).resolve()`, `Path(str(raw)).resolve()`, subscript/attribute-fed values, and renamed variables;
2. immutable P5 `foundation_model` runtime locator reintroduced into scientific/materialization config;
3. replay runtime locator strings (`pt_train_file` / `pt_valid_file`) reintroduced as immutable authorization rather than transient executable inputs after R2;
4. pathname-equality authorization between immutable replay paths and current request paths;
5. path-derived foundation/replay scientific identity fallback;
6. consumerless `PostSelectionMethodPolicies.replay_context` or equivalent duplicate replay transport authority;
7. `nonempty checkpoint directory == restart-authenticatable` shortcuts in the repaired recovery owner.

Known-positive rule tests must include representative former P5 foundation, former P7 reference-root, replay-path-overbinding, and checkpoint-presence patterns. Known-negative examples must include canonical configured-path resolution, content/SHA-based replay authentication, and existing TRAIN2 continuation validation.

Keep scan scope bounded to the affected owners and state limitations honestly. Do not introduce a repository-wide linter or architecture registry solely for this workplan.

---

## 6. R5 — final affected regression, integration, and exact candidate identity

The reviewed executable commit `cbfd43cabfbd5e26095a564b6bb4a9c9f3787638` has only a successful documentation check recorded on GitHub. Source inspection is not functional acceptance.

After R1-R4 are implemented, execute the parent workplan's minimum suites plus the new closure tests. At minimum:

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

Also run:

- the relevant TRAIN2 continuation/restart tests because R1 now depends on authenticated continuation rather than directory presence;
- relevant storage/run-lease integration if recovery ownership changes;
- current replay-unification/replay-lineage tests affected by R2;
- final-production/publication/currentness tests proving locator-only changes do not alter published scientific ancestry;
- the repository's configured fast Python lint/type/static checks where available;
- the final re-derived broader affected P5/P7/campaign/storage/replay regression surface.

A required slow/real-owner test that did not execute remains incomplete acceptance.

### Candidate/evidence identity

Final Review must name one exact Git commit/tree. If documentation generation produces a child commit that changes only derived documentation/PDF artifacts, executable evidence from its parent may be reused **only after verifying the child's executable/test/config tree is byte-identical in all dimensions relevant to that evidence**. Documentation builder/verification evidence belongs to the generated-doc child. Any later executable, test, static-config, or acceptance-harness change that could alter a claim invalidates and requires the affected evidence to be rerun.

Long real-data/GPU/CuEq/LAMMPS production qualification remains deferred exactly as in the parent plan.

---

## 7. Repair sequence

### Stage R1 — recovery authority and faithful counterfactuals

Close Section 2 first. Replace directory-presence heuristics with existing materialization/TRAIN2 authentication and establish faithful pre-fix, corrupt, foreign, partial-checkpoint, restartable, and live-writer outcomes through the real P5 owner.

### Stage R2 — replay locator separation

Close Section 3 as the sibling of the already-accepted foundation locator repair. Reuse existing replay artifact/lineage authentication and dependency-facing projection; remove pathname authorization rather than adding compatibility aliases.

### Stage R3 — acceptance closure

Complete the foundation path matrix and structural family checks, re-derive the final affected surface, run complete affected regression/integration/static checks on one unchanged executable candidate, and regenerate documentation only if authoritative docs actually changed.

Do not request another comprehensive Software Design closure review before R1-R3 are complete unless implementation hits a parent redesign trigger.

---

## 8. Re-review PASS criteria

Software Design may close the parent workplan only when all are true:

```text
[ ] accepted O1/O2/O3/O6/O7/O8/O9 behavior remains intact
[ ] accepted replay source/split lineage and path-derived-baseline cleanup remain intact
[ ] recovery does not delete arbitrary unaccepted materialization merely because terminal/checkpoint evidence is absent
[ ] faithful internally consistent pre-fix foundation locator-only materialization recovers in place
[ ] faithful internally consistent pre-fix replay locator-only materialization recovers if replay locator representation changed
[ ] checksum/digest-corrupt or unsupported materialization fails typed and is preserved
[ ] internally valid foreign/non-locator semantic mismatch fails typed and is preserved
[ ] current unaccepted materialization remains idempotent
[ ] valid TRAIN2 continuation is authenticated and reusable
[ ] partial/corrupt/foreign checkpoint residue is not treated as restartable by file presence
[ ] live-writer exclusion remains effective through the existing run activity lease
[ ] replay train/TRUE_DFT monitor paths are runtime locators, not scientific/materialization pathname authorization
[ ] replay relocation with identical authenticated content preserves method/replay-lineage identity and executes through real P5 owner
[ ] replay byte/label/source/split mutations still invalidate/fail closed
[ ] transient MACE pt_train_file / pt_valid_file and TRAIN2 TRUE-replay path use current authenticated locators
[ ] at least one final-production/restart path exercises the repaired locator/materialization owner
[ ] absolute/tilde/config-relative foundation forms all reach real P5 trainer/dependency projection from a foreign CWD
[ ] structural absence checks reject representative former P5/P7 raw-path, replay-path-overbinding, and checkpoint-presence shortcuts
[ ] baseline single-source replay-lineage behavior remains green
[ ] multi-size CV completeness and collection-wide production barrier remain green
[ ] P5 final publication/currentness and P7 consumer-only qualification remain green
[ ] final affected pytest/static/integration evidence executed on the exact final executable candidate
[ ] generated-doc evidence is tied to the exact derived child and does not conceal executable drift
[ ] no new migration database, compatibility registry, materialization pointer, replay identity, path registry, state machine, cleanup daemon, or lock layer was introduced
```

No Frozen architecture reconsideration is currently warranted. If implementation evidence shows that safe recovery of a supported durable P5 format genuinely requires a persistent migration mechanism, or that replay pathname is actually a scientific identity contrary to the current P5/replay authorities, stop and return to Software Design under the parent's redesign triggers rather than adding such machinery silently.

---

## 9. Deliberately non-blocking observations

The closure review noticed two path-bearing records outside the current blocker contract:

- `ReplaySingleSourceConfig.content_digest` includes its configured replay-set path, but current P5 method/replay-lineage authority does not consume that digest as scientific authorization; do not broaden this work merely to normalize an unused transport/config digest unless implementation evidence finds a real current consumer that violates the path-free replay contract.
- `PostSelectionMaterialization.output_directory` participates in materialization serialization. This review found no current product/Frozen requirement for arbitrary whole-workspace relocation. Do not invent such a requirement in this repair unless existing storage/restore authority demonstrates that it is already governed.

These observations are recorded only to prevent speculative scope growth.