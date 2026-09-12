---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-5
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
predecessor_review_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-4
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: 2086e80adddb30b93192c7e0b7a5e9c85a89dbbf
evidence_followup: d2f7a6697117cf5d9bba47def25b5246aa991725
highest_affected_domain: D3 replay configuration/currentness owner -> D4 exact-domain implementation and final acceptance evidence
serious_challenge: none
precedence: This review supersedes only the fourth implementation-review disposition. It accepts the B14 final semantic-parent/adoption fence and B15 public-prepare cheap-preflight ordering repairs, and accepts the rerun E2 realization as applicable target-host evidence for executable candidate 2086e80adddb30b93192c7e0b7a5e9c85a89dbbf. All non-conflicting parent R1-R28/final criteria and prior accepted B1/B4/B7/B11/B12 closures remain binding. The work remains open only for the two blockers below.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - fifth implementation Review reopen

## 0. Disposition

Executable candidate `2086e80adddb30b93192c7e0b7a5e9c85a89dbbf`, with target-host evidence follow-up `d2f7a6697117cf5d9bba47def25b5246aa991725`, is **NO-PASS / REOPENED** under SSDP 6.2. No Serious Challenge is active. The accepted D3/workplan remains coherent; the remaining defects are D4 exact-domain conformance and acceptance-evidence closure.

This pass independently reconstructed the final publication/retirement seam, public prepare entry order, canonical replay expectation, qualification-gate owner, E2 provenance, and available final test/CI evidence.

Material closures:

- **B14 stale-builder/adoption race is closed.** Both publication and retirement place the deterministic last-seam hook before the final live configuration/currentness re-resolution. Publication then re-authenticates the replay source and pseudo checkpoint immediately before atomic alias adoption. The strengthened tests exercise split/mode, pseudo qualification, foundation head, source/checkpoint, and retirement-interface changes at the actual final seam and assert the seam fired.
- **B15 is closed.** `execute_current_prepare()` now performs `_replay_topology_preflight(cfg, paths)` before `_single_source_replay_basis(...)`, so invalid replay topology is rejected before the basis can hash the replay source or inspect the foundation checkpoint. The public-route falsification test also guards target-size construction and foundation resolution from running first.
- **E2 is applicable to the executable candidate.** The rerun records commit `2086e80adddb30b93192c7e0b7a5e9c85a89dbbf`, tree `8772e3aae2feb3ab35d6e260ac6bc19af688a618`, and a clean working tree. It continues to show zero doctor replay inference/publication, one prepare-owned provider/executor/close and 128 predictions, zero new P5 inference, matching replay lineage, and a clean pre-TRAIN2 scheduler baseline.

Two genuine blockers remain.

## 1. Blocker B17 - replay qualification gates still violate the parent exact-domain rule

### Finding

The repaired command-start/live replay expectation now delegates its qualification component to `_replay_qualification_gate_semantics(cfg)`, and `_qualify_replay()` consumes the same helper. Consolidating the owner is directionally correct, but that owner still performs coercive interpretation:

```python
"minimum_train_configurations": int(...),
"minimum_monitor_configurations": int(...),
"allow_small_corpus": bool(...),
"require_target_elements": bool(...),
"target_atomic_numbers": tuple(sorted(int(v) for v in ...)),
"allow_unspecified_label_provenance": bool(...),
```

`_load_config()` does not validate these replay qualification fields, and `_replay_topology_preflight()` currently validates the canonical single-source selector/split plus prediction batch/shard controls, but not the qualification-gate domains. Consequently malformed TOML can be silently reinterpreted instead of rejected. Examples include:

- `minimum_train_configurations = 1.5` becoming `1` through `int(...)`;
- a string-valued boolean such as `allow_small_corpus = "false"` becoming `True` through Python truthiness;
- analogous truthiness coercion for `require_target_elements` / `allow_unspecified_label_provenance`.

This is not merely a token/currentness issue. `_qualify_replay()` uses the coerced result to decide whether a replay corpus passes production qualification, so the malformed declaration can change actual accepted behavior. It violates parent R2's already-binding rule that qualification booleans/numerics retain validated exact domains and do not acquire truthiness/int-cast shortcuts.

### Owning-layer repair

Repair the existing qualification-gate owner; do **not** add another basis, validator registry, compatibility parser, or parallel policy object.

1. Make `_replay_qualification_gate_semantics(...)` (or an already-existing narrower canonical owner, if one exists) resolve the accepted qualification-gate domains exactly rather than coercively.
2. Reuse that one resolved result everywhere: cheap prepare preflight, command-start/live currentness expectation, and `_qualify_replay()`.
3. Booleans must be actual supported boolean values, not arbitrary truthy/falsy objects. Integer/count controls must satisfy their already-accepted integer/range domain without truncating floats, accepting booleans as integers, or stringifying/coercing unrelated types. Preserve any intentionally supported lexical form only where an existing canonical owner already defines it.
4. Route invalid gate configuration through the cheap preflight before replay-source hashing/model inspection/target-source reconstruction, just like the already-closed split/batch/shard domains.
5. Do not alter qualification thresholds, scientific meaning, or defaults; this is exact parsing/validation only.

### Required falsification

Add real configuration/preflight tests covering, at minimum:

- fractional and boolean values for the minimum-count fields;
- non-boolean/string values for each replay qualification boolean;
- valid canonical values preserving current behavior;
- public `execute_current_prepare()` rejects malformed gates before expensive replay/foundation/target-size work;
- the replay basis and `_qualify_replay()` consume the same normalized gate semantics rather than independently coercing them.

Use a sensitivity/counterexample where useful: a malformed value that the old `int(...)`/`bool(...)` implementation would have accepted must now fail.

## 2. Blocker B18 - final functional acceptance is still not recoverable for `2086e80a...`

### Closed part

The final target-host **E2** obligation is satisfied for executable candidate `2086e80adddb30b93192c7e0b7a5e9c85a89dbbf`; its raw artifact binds exact commit/tree/clean state and its observations remain consistent with the provider/stage ownership requirements.

The E1 provider-lifetime implementation was not changed by the B14/B15 delta, so the existing E1 realization may remain reusable if final closeout explicitly records that unchanged applicability. If B17 touches only configuration-gate parsing/currentness and not the provider-lifetime implementation, E1 still need not be rerun.

### Remaining finding

There is still no recoverable final functional acceptance realization for the executable candidate:

- GitHub combined status for `2086e80adddb30b93192c7e0b7a5e9c85a89dbbf` contains zero statuses;
- GitHub Actions contains zero workflow runs for that head;
- the implementation commit adds/changes test definitions, but the repository contains no candidate-bound focused/affected/integration/static/build/package execution record after the final executable edits;
- the E2 CUDA qualification is valuable target-host integration evidence, but it does not execute the complete focused replay falsification suite, affected regression surface, or repository build/package checks required by the parent workplan and SSDP 6.2 final assembled acceptance.

A test definition is not an evidence realization. Required checks that cannot be recovered as executed remain blocking.

### Required closeout after B17

On the final executable candidate produced by the B17 repair:

1. Run the focused replay suite, including all first-through-fifth-review falsification cases: exact configuration domains, final publication/retirement seam races, B11 no-retry, B12 nested cleanup, lifecycle snapshot/currentness, source/checkpoint mutation, provider ownership, and P5 read-only behavior.
2. Run the materially affected regression surface: replay unification/invalidation/materialization/P5 integration, lifecycle/currentness, target-size prepare/currentness interactions, qualification observation, and any caller changed by the final repair.
3. Run assembled integration through the public doctor/prepare/replay/P5 boundary.
4. Run the repository-required static/compile/build/package checks applicable to the changed package.
5. Preserve a recoverable execution record that binds the exact final executable commit/tree plus working-tree cleanliness (or equally strong source identity) to commands, exit status, and results. Native CI is sufficient but not required; a committed candidate-bound acceptance log is also acceptable.
6. Rerun E2 if B17 changes executable code used by the E2 public route, and bind it to the exact final candidate/tree. Because B17 necessarily touches replay configuration/currentness execution, treat the current `2086e80a...` E2 as stale for a changed final executable candidate and rerun it.
7. Preserve E1 only with an explicit unchanged-provider-path applicability statement; rerun E1 only if provider-lifetime product code changes.
8. Keep E1/E2 observations separate. Do not broaden this work into the separate TRAIN2 qualification unless the final replay delta changes a TRAIN2 assumption.

## 3. Preserved closures and non-goals

Do not reopen or redesign settled behavior while repairing B17-B18:

- omitted single-source mode -> `TRUE_DFT`; pseudo remains explicit opt-in;
- TRUE_DFT prepare performs zero foundation replay inference and has no pseudo fallback;
- doctor remains validation-only for current single-source replay;
- public `prepare` remains the sole single-source replay-science construction owner;
- P5 remains scientific-read-only and may reconstruct only disposable representations from authenticated parents;
- pseudo train + independent TRUE_DFT monitor semantics remain unchanged;
- same-key cold prediction remains single-flight;
- B1 provider lifetime remains one internal provider owner -> one executor owner with caller ownership preserved;
- prediction inputs remain label-blind and consumed geometry remains authenticated;
- B4 prediction batch/shard and split-seed exact domains remain closed;
- B7 one-snapshot lifecycle currentness/digest validation remains closed;
- B11 TypeError compatibility retry remains removed;
- B12 recursive nested cleanup oracle remains accepted;
- B14 final publication/retirement semantic-parent fence remains closed;
- B15 cheap public prepare preflight ordering remains closed;
- target-size scientific identity remains replay-independent;
- TRAIN2 zero-safe/live-memory safety is not weakened;
- no scientific/numerical/schema/method-version bump is justified by this repair;
- no additive wrapper, fallback, shadow authority, registry, generation system, or new synchronization mechanism where the existing configuration/currentness owner can be corrected directly.

## 4. PASS criteria for the next review

PASS requires one final executable candidate for which:

1. B17 qualification-gate configuration has one exact canonical owner, malformed types cannot be silently coerced, and the public cheap preflight rejects them before expensive work.
2. B14/B15 and all earlier accepted closures remain intact.
3. B18 focused + affected + assembled integration + repository checks are executed, recoverable, and bound to the exact final candidate/tree.
4. E2 is applicable to that final executable candidate; E1 is explicitly preserved by unchanged provider-lifetime applicability or rerun if that path changes.
5. Parent R1-R28 and final criteria 1-36 remain satisfied, including exact alias replacement, mutable-source safety, lifecycle coherence, P5 read-only behavior, target-size independence, and unchanged TRAIN2 safety.
6. No newly discovered genuine blocker or Serious Challenge remains.

Until all six hold, the parent work remains **NO-PASS / ACTIVE-REOPENED**.
