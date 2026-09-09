---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 5.16.0
status: reopened
created_date: 2026-09-08
last_design_closure_review_date: 2026-09-09
reviewed_candidate_head: 8c0e2426ce6f9248bf6b958d48570c140bcef147
reviewed_implementation_commit: cbfd43cabfbd5e26095a564b6bb4a9c9f3787638
reviewed_generated_docs_commit: 8c0e2426ce6f9248bf6b958d48570c140bcef147
implementation_review_verdict: no-pass
precedence: This file is the current binding review amendment to MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md. It supersedes its own earlier wording in place. Every non-conflicting product invariant, Frozen architecture decision, preservation requirement, non-goal, acceptance obligation, and redesign trigger in the parent workplan remains binding.
---

# MLFF downstream integration closure — implementation review reopen 1

## 0. Current verdict and remote-SDP reconciliation

**NO-PASS / REOPENED.**

This amendment has been re-reviewed against the current remote `software-development-protocol` Software Design role and Protocol `5.16.0`. The executable candidate under review is unchanged; this pass corrects and strengthens the implementation handoff itself.

No Frozen MLFF scientific or high-level architecture decision needs to change. The remaining code blocker is still the P5 recovery/materialization owner, but the remote-protocol review changes one conclusion from the previous wording:

- the previous amendment was correct to require replay **scientific method/lineage identity** to remain path-free;
- it was **too broad** to promote arbitrary relocation of generated replay train/monitor execution files (`pt_train_file` / `pt_valid_file`) into a new product requirement merely because those files carry path-independent content identity;
- current P5 authority explicitly freezes arbitrary relocation for the **foundation checkpoint locator**, and the replay-source authority explicitly permits relocation/rebinding of the externally configured replay source locator; it does not independently freeze arbitrary relocation of every generated replay execution view.

Accordingly, this amendment **retracts the earlier requirement that P5 must remove `pt_train_file` / `pt_valid_file` from immutable execution representation or support arbitrary relocation of those generated view files.** Their exact internal representation remains delegated unless a real supported lifecycle exposes a concrete contradiction. Replay path-free method/lineage semantics remain mandatory.

The remaining blocking work is:

1. make P5 recovery distinguish current valid scratch, supported internally valid pre-fix locator-only representation, incomplete run-owned publication, corruption/foreign state, and genuinely authenticated TRAIN2 continuation;
2. stop using file/directory presence as a proxy for resumability;
3. complete the real-owner configured-path acceptance for foundation and the affected **externally configured replay source** path semantics;
4. strengthen structural/failure-path acceptance so the repaired owner cannot pass by deleting evidence or by bypassing the real recovery/currentness owner;
5. execute final affected pytest/static/integration evidence on one exact final executable candidate.

Repair these in existing owners. Do **not** add a migration database, compatibility registry, second materialization pointer, restart state machine, cleanup daemon, path alias table, second replay identity, or another lock/lease layer. If the current helper shape obstructs safe classification, alter/move/remove the helper rather than surrounding it with machinery.

---

## 1. Authority classification and accepted surfaces

### 1.1 Tier-1 / Frozen product and scientific semantics

The parent workplan remains authoritative for the downstream product contract. In particular:

- configured user paths touched by this work have one deterministic `expanduser -> config-directory-relative -> resolve` interpretation;
- foundation checkpoint path is a runtime locator only; authenticated checkpoint content/head/family owns foundation scientific identity and byte-identical relocation is supported;
- every frozen selected size receives its own valid CV verdict unless execution fails before a scientific verdict exists;
- campaign CV accepts only when every frozen size accepts;
- final-production admission is collection-wide and final training is fresh under each frozen `H_prod_i`;
- P5 owns final publication/currentness and P7 consumes it read-only;
- multi-size completion remains terminal/non-release-qualified;
- ordinary single-size nonlocked qualification may route downstream, while locked activation remains explicit-only;
- restart/currentness is fail-closed and accepted/restart-authenticatable work is not discarded merely to make a representation convenient;
- replay training exposure and independent TRUE_DFT replay admissibility remain distinct;
- replay method and replay-lineage identities remain path-free and content/label/source/split based;
- full long real-data/GPU/CuEq/LAMMPS qualification remains deferred.

### 1.2 Accepted implementation behavior to preserve

The following reviewed source behavior is accepted and must survive the repair unless new evidence invalidates it:

1. `_common.resolve_configured_path()` is the shared configured-path semantic owner for the affected campaign fields.
2. P5 receives `paths.config_dir` for configured foundation resolution.
3. Immutable P5 MACE configuration no longer stores `foundation_model`; `MacePostSelectionTrainer` receives the current locator in the authenticated request and re-hashes the reached checkpoint against canonical foundation identity/head before transient parser-facing projection.
4. P5/P7 provider reconstruction receives the current authenticated foundation locator explicitly rather than trusting a stale stored pathname.
5. Consumerless `PostSelectionMethodPolicies.replay_context` is removed; single-source policy parsing is config-directory-aware; source/split replay lineage remains canonical and fail-closed; replay foundation-baseline cache identity no longer falls back to a path digest.
6. Methodological CV rejection is accumulated and later frozen sizes continue to valid per-size verdicts; hard execution/corruption/authority failures remain fail-fast.
7. Explicit P7 qualification reference root uses canonical configured-path semantics and the existing multi-size qualification boundary remains intact.
8. The canonical 40/50/80 architecture sources and generated manual/PDF already express frozen `H_prod_i`, P5 publication ownership/P7 consumption, and ordinary-nonlocked-versus-locked `advance` routing consistently.
9. The earlier single-source runtime `source` / `split` lineage rewire remains mandatory.

### 1.3 Deliberately delegated behavior

The following are not Frozen merely because current code or tests use them:

- `_reclaim_unaccepted_materialization` name, signature, existence, and call position;
- exact module/function that performs recovery classification;
- exact internal representation of generated replay train/monitor execution locators;
- exact helper used for TRAIN2 continuation validation, provided the final real owner authenticates equivalent continuation semantics;
- fixture factoring and low-level bounded numerical doubles;
- exact wording/layout of already-reconciled documentation.

If an equivalent simpler owner replaces a named Tier-2 helper, acceptance must be remapped to the new real owner rather than treating the helper name as authority.

---

## 2. R1 — recovery must classify state before destructive reconciliation

### 2.1 Current defect

`campaign_post_selection_runtime._reclaim_unaccepted_materialization()` currently protects a materialization directory when selected terminal filenames exist or when the checkpoint directory is merely nonempty; otherwise it recursively deletes the materialization directory.

This violates the accepted recovery outcome in two directions:

- malformed/checksum-inconsistent/foreign immutable materialization can be silently converted into absence before an owner authenticates it;
- arbitrary checkpoint residue is treated as restartable merely because a filename exists, even though the existing TRAIN2 continuation owner authenticates plan/protocol/optimizer/budget/LR identities, checkpoint SHA, companion state, and continuation-state digests.

File existence is not a validity or completion contract.

### 2.2 Recovery classification boundary

While holding the existing `post_selection_run_activity_lease(run_root)`, the real P5 recovery/materialization owner must classify the run root without destructive mutation first.

Required semantic classes are:

1. **No materialization publication exists** — ordinary current materialization proceeds.
2. **Current internally valid unaccepted materialization for the exact logical run** — ordinary idempotent create-or-verify/reuse succeeds; do not delete it gratuitously.
3. **Internally valid pre-fix foundation-locator-only materialization for the exact logical run** — if the only relevant incompatibility is the retired `foundation_model` locator representation and all other protected semantics match the current expected run, reconcile/rebuild the minimum necessary run-owned scratch so retry proceeds without operator deletion.
4. **Incomplete run-owned materialization publication** — distinguish an interrupted publication from a corrupt completed record. If ownership is certain, no accepted/restart-authenticatable progress exists, and the state is demonstrably incomplete scratch (for example, publication stopped before the final authenticated materialization record), it may be cleaned/rebuilt through existing ownership. Do not relabel a present-but-malformed final record as merely incomplete.
5. **Malformed, checksum/digest-inconsistent, unsupported-schema, or internally inconsistent completed materialization** — raise an existing typed P5/input/serialization error and preserve diagnostic evidence.
6. **Internally valid materialization belonging to a different run/method/preparation/artifact/semantic configuration** — typed failure and preserve it. Do not generalize locator-only compatibility into a migration mechanism.
7. **Valid restart-authenticatable TRAIN2 progress exists** — preserve and resume/reuse through the real continuation owner. Never delete it merely to obtain newer materialization spelling.
8. **Checkpoint files exist but do not authenticate as a current continuation** — presence is not resumability. Distinguish owner-proven incomplete/disposable attempt scratch from corrupt/foreign durable continuation state using existing TRAIN2/P5 semantics. Corrupt/foreign state fails typed and remains diagnostic evidence; run-owned incomplete scratch may be reclaimed only when ownership and non-authoritativeness are established.
9. **Another live writer owns the run root** — the existing activity lease remains the liveness boundary. Do not add another lock.

### 2.3 Classification must be non-destructive until authenticity is known

Do not discover compatibility by deleting the old tree and seeing whether regeneration succeeds. Do not write current expected bytes over or into an existing ambiguous materialization before classifying the existing final record and protected progress.

If implementation needs current expected materialization/config semantics for comparison, derive them in memory or in clearly run-owned temporary state and compare before publication/destruction. Any replacement publication must follow existing transactional/create-or-verify rules.

This is an integrity constraint, not a mandate for a new migration transaction framework.

### 2.4 Existing authority to reuse

Prefer the current authoritative records/checks rather than parallel classifiers:

- `PostSelectionMaterialization.from_dict` and its content digest;
- immutable internal MACE-config bytes, SHA256, schema, and content digest;
- `run_plan_digest`, `run_identity`, `preparation_digest`, and existing role artifact identities;
- current run-plan/method/replay-lineage owners;
- the existing TRAIN2 continuation validator or an equivalent final real owner that authenticates the same continuation state.

Do not add a duplicate selected-binding/materialization identity merely to simplify recovery.

### 2.5 Destructive scope and external-input safety

After authentication proves state is run-owned, unaccepted, and safely replaceable, destroy/rewrite only what must change. Whole-materialization-tree deletion is permitted only when it is demonstrably the minimum safe/simple action over disposable run-owned scratch.

Recovery must never delete or rewrite externally configured foundation checkpoints, replay source files, legacy replay inputs, qualification reference inputs, or other authoritative user/source data. Run-root cleanup authority does not extend through locators to external inputs.

### 2.6 Required real-owner recovery/failure tests

Keep the real P5 run/recovery/materialization owner live; expensive MACE arithmetic may remain bounded below it.

Required cases:

- **faithful pre-fix foundation-locator materialization:** old immutable config and matching `materialization.json` are internally self-consistent; no accepted/checkpoint progress; corrected retry succeeds in the same workspace without harness deletion;
- **current unaccepted materialization:** idempotent current retry succeeds without destructive churn;
- **interrupted/incomplete materialization publication:** representative run-owned partial publication is classified as incomplete rather than accepted/corrupt-by-default, and the documented safe recovery outcome occurs;
- **corrupt config bytes:** mutate immutable config without updating its authenticated materialization record; retry fails typed and preserves evidence;
- **corrupt final materialization record:** malformed/unsupported/digest-mismatched record fails typed and remains present;
- **foreign internally valid materialization:** alter a protected non-locator semantic while keeping the record internally consistent; retry fails typed and preserves it;
- **valid restartable continuation:** authenticate through the real continuation owner and preserve/resume;
- **partial checkpoint state:** representative lone/truncated/missing-summary-or-companion state is not treated as restartable merely because the directory is nonempty;
- **foreign/corrupt continuation:** plan/protocol/budget/LR/SHA/content mismatch fails typed and is preserved unless an existing owner specifically classifies a file as disposable temporary scratch;
- **live-writer exclusion:** reuse existing activity-lease evidence if it reaches the destructive boundary; otherwise add one bounded production-owner concurrency case;
- **external input safety:** at least one failure-path regression proves recovery does not delete the configured foundation/replay source reached through a locator.

For failpoint-based cases, establish trigger liveness when practical; a green test whose interruption seam never fired is not acceptance evidence.

A helper-only test that directly calls `_reclaim_unaccepted_materialization()` on arbitrary directories cannot close the recovery claim.

---

## 3. R2 — complete configured replay-source path semantics without inventing generated-view relocation

### 3.1 Governing replay contract

Current P5/replay authority establishes:

```text
replay method identity: path-free
replay lineage: train/monitor content identity + SHA + label semantics
single-source lineage: additionally source content digest + source SHA + split manifest
external replay source locator: not scientific identity; identical source may rebind/relocate
```

This is sufficient to require canonical user-configured replay-source path handling and source relocation equivalence. It does **not** by itself require arbitrary relocation of generated materialized replay train/monitor execution files.

### 3.2 Required end state

For the canonical single-source replay interface:

- `[paths].replay_set` obeys the same `~` / config-directory-relative / canonical-resolution semantics independent of invocation CWD;
- the real P5 replay-policy/context/lineage owners consume that canonical source meaning rather than recomputing a CWD-relative interpretation;
- moving/copying the external replay source to another valid configured locator with identical bytes and unchanged label/split semantics does not change the path-free P5 method/replay-lineage identity;
- changing source bytes, labels, split membership/seed, or other governed replay semantics continues to invalidate/fail closed;
- existing legacy replay path behavior remains covered by affected regression and must not regress.

### 3.3 Explicitly retracted overreach

Do **not** modify `pt_train_file` / `pt_valid_file`, replay materialization digests, or pathname-equality checks solely to satisfy the previous amendment's generated-view relocation requirement. Such a change is permitted only if Implementation discovers a concrete supported current lifecycle in which those internal locators create an actual contradiction with existing Tier-1/Frozen semantics.

If such evidence appears, return it as affected-surface evidence under the existing parent contract; do not assume every path-bearing execution field is scientific identity.

### 3.4 Required acceptance

Use a bounded real single-source replay fixture from a CWD different from the configuration directory. Exercise at least:

```text
absolute replay_set
~/... replay_set
../... config-relative replay_set
```

For each representation prove the same intended source reaches:

- canonical campaign replay-source resolution;
- P5 method-policy resolution;
- the real P5 replay resolution/lineage owner used by CV/final currentness.

Then perform an authority-backed relocation counterfactual on the **external source**:

1. record P5 method and replay-lineage identities;
2. copy/move the exact replay source bytes to a different configured locator;
3. update only the configured source locator;
4. re-resolve through the real campaign/P5 replay owners;
5. prove method/replay-lineage identities remain unchanged;
6. mutate source bytes or another governed replay semantic and prove invalidation/fail-closed behavior.

The test must not simulate this by manually constructing the final replay-lineage digest in the harness.

---

## 4. R3 — complete the foundation path-form execution matrix

Parent O1/8.1 requires absolute, tilde, and config-relative foundation spellings to agree through `doctor`, P5 identity/context, **P5 trainer request, and dependency-facing launch** from a foreign CWD.

The current test matrix checks all three forms through path resolution/policies/method identity, while real P5 execution/relocation covers only the config-relative form.

Parameterize/reuse the existing real-owner foundation-backed campaign test so all three spellings reach the trainer/dependency-facing projection and assert the same canonical locator. Keep expensive numerical work below the accepted seam. Do not add another path framework.

The relocation relation remains Frozen for foundation:

```text
identical bytes + same canonical head/family at locator A/B
    -> same method identity
    -> executable/recoverable after reauthentication

changed bytes/head/family
    -> invalidate/reject stale descendants
```

---

## 5. R4 — structural/absence evidence must model the actual forbidden families

Serena/Semgrep are preferred when available and their backend models the relation. The current review harness exposes neither capability, so this review used bounded repository/source inspection. Implementation should use the specialized tool when available; otherwise use a bounded AST/source fallback.

Acceptance-critical structural rules must be validated against representative known-positive and known-negative examples and must state scan scope/limitations.

The affected-owner scan must be able to reject at least these forbidden families:

1. direct or wrapped raw configured-path resolution that bypasses the canonical configured-path owner, including `Path(raw).resolve()`, `Path(str(raw)).resolve()`, subscript/attribute-fed values, and renamed variables in affected P5/P7 campaign configuration paths;
2. immutable P5 `foundation_model` runtime locator reintroduced as scientific/materialization authorization;
3. path-derived foundation or replay **scientific** identity fallback;
4. consumerless `PostSelectionMethodPolicies.replay_context` or equivalent duplicate replay-policy authority;
5. `nonempty checkpoint directory == restart-authenticatable` shortcuts;
6. recovery code that deletes ambiguous/corrupt completed materialization before authenticating it.

Known-positive examples must include the former P5 foundation raw-path pattern, former P7 reference-root pattern, current directory-presence recovery shortcut, and an unsafe delete-before-authenticate pattern. Known-negative examples must include canonical configured-path resolution, content/SHA-based replay scientific authentication, and real TRAIN2 continuation validation.

Do **not** add a structural rule that bans `pt_train_file` / `pt_valid_file` merely for existing in execution configuration; that would reintroduce the requirement-expansion error corrected in Section 3.

Do not create a repository-wide linter or architecture registry solely for this workplan.

---

## 6. R5 — final affected regression, integration, and candidate identity

The reviewed executable commit `cbfd43cabfbd5e26095a564b6bb4a9c9f3787638` has no available final pytest/static/integration completion evidence. Source inspection cannot substitute for functional acceptance.

After R1-R4 are implemented, execute the parent workplan's required focused and downstream suites plus the new closure tests. At minimum:

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

- relevant TRAIN2 continuation/restart tests because R1 depends on authenticated continuation rather than directory presence;
- affected storage/run-lease tests if recovery ownership changes;
- current single-source and legacy replay-unification/lineage/path tests affected by R2;
- P5 final-production/publication/currentness tests proving the repair does not weaken accepted ancestry/currentness;
- repository-configured fast Python lint/type/static checks where available;
- final re-derived broader P5/P7/campaign/storage/replay affected regression.

### Stage-local closure

After each material executable stage, run focused checks plus the affected regression subset for that stage before dependent work proceeds. Do not defer every failure/recovery regression until the final pass.

### Exact candidate/evidence identity

Final Review must name one exact Git commit/tree whose executable/test/static-configuration dimensions match the evidence.

If documentation generation produces a child commit changing only canonical derived documentation/PDF artifacts, executable evidence from its parent may be reused only after verifying the child did not alter any executable/test/configuration/acceptance dimension relevant to those claims. Documentation builder/verification evidence belongs to the generated-doc child. Any later material executable/test/harness change invalidates the affected evidence and requires rerun.

A required real-owner check that did not execute is incomplete acceptance, not a pass.

Long real-data/GPU/CuEq/LAMMPS production qualification remains deferred.

---

## 7. Implementation sequence

### Stage R1 — recovery authority and faithful failure states

Close Section 2 first. Move/narrow/remove the current reclamation helper as needed so classification occurs where both existing authenticated state and current expected semantics are available. Establish current, faithful pre-fix, incomplete publication, corrupt, foreign, partial-checkpoint, restartable, external-input-safety, and live-writer outcomes through the real P5 owner.

Run focused recovery/materialization/TRAIN2/run-lease regressions before dependent work.

### Stage R2 — configured-path acceptance closure

Close Sections 3-4:

- real single-source replay `replay_set` absolute/tilde/config-relative semantics plus external-source relocation/mutation;
- real foundation absolute/tilde/config-relative dependency-facing execution plus existing foundation relocation/mutation.

Do not alter generated replay-view locator semantics without a concrete supported-lifecycle defect.

Run affected replay/P5/path tests plus Stage R1 shared-owner regressions.

### Stage R3 — structural/final assembled acceptance

Close Sections 5-6, re-derive the final affected surface, run complete affected regression/integration/static checks on one unchanged executable candidate, and regenerate documentation only if authoritative current docs actually changed.

Do not request another comprehensive Software Design review before R1-R3 are complete unless implementation reaches a genuine parent redesign trigger.

---

## 8. Re-review PASS criteria

Software Design may close the parent workplan only when all are true:

```text
[ ] parent O1/O2/O3/O6/O7/O8/O9 accepted behavior remains intact
[ ] accepted replay source/split lineage and path-derived-baseline cleanup remain intact
[ ] recovery authenticates/classifies existing state before destructive reconciliation
[ ] faithful internally consistent pre-fix foundation locator-only materialization recovers in place
[ ] current unaccepted materialization remains idempotent
[ ] interrupted owner-proven partial materialization publication has a defined safe recovery outcome
[ ] checksum/digest-corrupt or unsupported completed materialization fails typed and is preserved
[ ] internally valid foreign/non-locator semantic mismatch fails typed and is preserved
[ ] valid TRAIN2 continuation is authenticated and reusable
[ ] partial/corrupt/foreign checkpoint residue is not treated as restartable by file presence
[ ] live-writer exclusion remains effective through the existing run activity lease
[ ] destructive recovery cannot delete externally configured foundation/replay/source inputs
[ ] failure-injection acceptance proves the intended interruption/failpoint actually fired when practical
[ ] single-source replay_set absolute/tilde/config-relative forms are CWD-independent through the real P5 replay owner
[ ] byte-identical external replay-source relocation preserves P5 method/replay-lineage identity
[ ] replay source/label/split mutation still invalidates/fails closed
[ ] no unsupported requirement was introduced for arbitrary relocation of generated pt_train_file / pt_valid_file views
[ ] absolute/tilde/config-relative foundation forms all reach real P5 trainer/dependency projection from a foreign CWD
[ ] foundation same-bytes/head relocation remains executable and changed bytes/head remain fail-closed
[ ] structural absence checks reject representative raw-path, delete-before-authenticate, and checkpoint-presence shortcuts
[ ] baseline single-source replay-lineage behavior remains green
[ ] multi-size CV completeness and collection-wide production barrier remain green
[ ] P5 final publication/currentness and P7 consumer-only qualification remain green
[ ] final affected pytest/static/integration evidence executed on the exact final executable candidate
[ ] generated-document evidence is tied to its exact derived child and does not conceal executable drift
[ ] no new migration database, compatibility registry, materialization pointer, replay identity, path registry, state machine, cleanup daemon, or lock layer was introduced
```

No Frozen architecture reconsideration is currently warranted. If implementation evidence shows that safe recovery of a supported durable P5 format genuinely requires persistent migration machinery, or that a replay execution pathname is itself product/scientific identity contrary to the current replay authorities, stop and return to Software Design with that evidence rather than silently adding machinery.

---

## 9. Snapshot-loss and closeout requirements

### 9.1 Snapshot-loss check before Implementation handoff

The current supplied handoff is the parent workplan plus this amendment plus the current referenced MLFF architecture/P5/P7 authorities under Protocol `5.16.0`. Implementation must not depend on prior chat, superseded amendment wording, or unavailable Git archaeology for any still-binding task-specific semantic.

The parent and this amendment together must recover:

- product/Frozen invariants;
- accepted behavior that must be preserved;
- delegated solution space;
- recovery/path acceptance boundaries;
- real-owner/test-double rules;
- final evidence/candidate requirements;
- redesign/simplification triggers.

If Implementation finds a still-binding requirement that exists only in historical discussion, reconcile it into the current supplied authority before relying on it.

### 9.2 Post-PASS lifecycle closeout

After independent Software Design Review actually passes, reconcile the active workplan lifecycle state: retire/archive the completed parent/amendment according to repository policy and update `workplans/active/README.md` so a reopened plan does not remain advertised as current authority. This is closeout, not executable product work, and must not mutate product behavior.

---

## 10. Deliberately non-blocking observations

The remote-protocol pass records these only to prevent speculative scope growth:

1. `ReplaySingleSourceConfig.content_digest` includes its configured source path, but current P5 method/replay-lineage authority does not use that digest as the scientific authorization described above. Do not redesign that record merely for aesthetic path-freedom unless a real current consumer is shown to violate the governed replay identity.
2. `PostSelectionMaterialization.output_directory` participates in materialization serialization. This task does not define arbitrary whole-workspace relocation as a product capability. Do not broaden the repair into workspace-relocation semantics without existing authority/evidence.
3. Generated replay train/monitor execution locators may remain in the immutable execution representation if they are part of the supported execution layout and do not contradict an existing product/Frozen relocation/currentness contract. Their presence alone is not a defect.

These are scope guards, not acceptance shortcuts.