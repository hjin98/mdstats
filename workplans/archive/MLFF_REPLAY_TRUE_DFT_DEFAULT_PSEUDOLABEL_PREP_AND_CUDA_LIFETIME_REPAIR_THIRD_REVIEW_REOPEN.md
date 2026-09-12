---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-3
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
predecessor_review_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-2
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: 07ef36db48870427d68e266a46ff2c4362875f68
highest_affected_domain: D3 replay current-alias publication/currentness and evidence applicability -> D4 implementation and acceptance
serious_challenge: none
precedence: This review supersedes only the second implementation-review disposition. It accepts the B7 lifecycle coherent-snapshot/digest-authentication repair, the previously accepted B1/B4 repairs, and the newly rerun E1/E2 observations as useful evidence. Every non-conflicting parent R1-R28/final criterion and the separate TRAIN2 zero-safe/live-memory authority remains binding. The work remains open only for the blockers and evidence closure below.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - third implementation Review reopen

## 0. Disposition

Candidate `07ef36db48870427d68e266a46ff2c4362875f68` is **NO-PASS / REOPENED** under SSDP 6.2. No Serious Challenge is active and no D1/D2 redesign is requested.

This pass independently reconstructed the repaired publication, command-start currentness, lifecycle snapshot, provider-failure tests, and target-host evidence rather than inheriting the implementation's intended closure.

The candidate materially closes important parts of the second review:

- **B7 is closed.** `campaign_owner_snapshot()` now authenticates `replay_lineage_digest` with the existing digest validator and captures replay lineage/status together with the target revision and P5/P7 pointers in one SQLite read transaction. Public lifecycle projection passes that captured status into prepare observation rather than re-reading replay lineage after the snapshot. The new interleaved-writer test exercises both directions of the race and keeps the returned lifecycle answer bound to the captured snapshot.
- **B8's requested failure families are now represented.** Fault-injection cases exist for `os.chmod(...)` after executor acquisition and for a post-provider/pre-executor setup failure, with caller-owned-provider variants. The product lifetime control flow remains the accepted single-owner/single-executor structure.
- **E1 and E2 were rerun and their summaries now agree with their raw observations.** E1 again shows bounded non-accumulating post-close residency across two cold builds in a live process. E2 again shows zero replay-wide prediction in doctor, one prepare-owned provider/executor lifetime, zero new P5 provider/prediction work, matching lineage, and clean pre-TRAIN2 scheduler occupancy.
- public `prepare` now captures a command-start replay basis before the long target-size portion, and pseudo publication rechecks the doctor-frozen acceleration realization before current-alias adoption.

Those repairs are substantial, but four genuine blockers remain.

## 1. Blocker B10 - current-alias publication is still not a complete stale-builder/current-parent fence

### Finding A - the new race hook does not falsify the last-check -> commit seam

`_publish_single_source_replay_authority()` enters `store.writer_exclusion()` and invokes `_TEST_REPLAY_PUBLICATION_PRE_REVALIDATION_HOOK` **before** the final lineage/config/source/checkpoint/acceleration checks. The new source/checkpoint race tests therefore mutate a parent before the check and prove only that the check notices an already-mutated parent.

The second review explicitly required a deterministic barrier at the **last revalidation -> alias commit** seam. That seam remains unexercised. This matters because `store.replace_records_atomically(...)` still performs record encoding/externalization before its own SQLite replacement transaction; when called under the outer writer exclusion, that work occurs after the final source/checkpoint hashes and before the alias write. A mutable external source or checkpoint can therefore still change after the last hash and before current aliases become durable.

This is not a demand for a global filesystem lock. It is the existing parent R11/R14 requirement: final mutable-parent authentication must be adjacent enough to adoption that a deliberately interleaved mutation cannot create a stale-current alias set.

### Finding B - command-start replay basis omits material qualification semantics

`_single_source_replay_basis()` manually records only label mode, split ratio/seed, replay locator, and the two minimum-count gates. It omits pseudo-label qualification/currentness inputs that directly affect qualification, eligible geometry membership, split, and therefore replay lineage, including at least:

- `maximum_force_ev_per_angstrom`;
- `force_component_rms_ev_per_angstrom`;
- `maximum_abs_stress_ev_per_angstrom3`;
- `require_stress`;
- realized qualification gates such as target-element/small-corpus policy where they affect whether the prepared replay set qualifies.

A pseudo prepare can therefore build under one threshold policy, observe a different threshold policy at adoption, and still pass `live_basis == command_replay_basis` for every field the basis happens to carry. The later public-stage configuration digest may leave `prepare` WAITING, but parent R11/R14 forbids publishing the stale alias set as current in the first place.

The manual basis also reintroduces `int(...)` conversion for minimum-count fields instead of deriving from their existing validated owners. That is unnecessary duplicate interpretation and cuts against the already-accepted exact-domain/one-owner direction.

### Finding C - live foundation potential/head is not re-resolved at adoption

For pseudo mode, publication rehashes the checkpoint referenced by the **old** `prediction_policy` and reloads the doctor-frozen acceleration realization. `_stored_acceleration_realization()` validates backend/device/dtype/qualification against live configuration, but does not prove that the live campaign still names the same foundation model/head/potential used to create the prediction policy.

A mid-prepare `foundation_model` or foundation-head edit can therefore leave the old checkpoint present and the old acceleration realization internally consistent while the live campaign now denotes a different prediction parent. The stale replay aliases may be installed before the later stage-completion digest detects the config change.

### Finding D - the no-single-source/legacy path can delete a newer winner

The strongest remaining stale-builder counterexample is the early `context is None` branch:

```text
baseline_lineage = ...
context = _construct_single_source_replay_context(command_start_cfg, ...)
if context is None:
    _retire_single_source_replay_aliases(store)
    return None
```

This path bypasses the publication fence entirely.

Counterexample:

1. prepare A starts under no replay / legacy split replay;
2. the campaign changes to single-source replay;
3. prepare B publishes a valid new single-source current alias set;
4. prepare A finishes later, still sees `context is None` from its command-start configuration, and unconditionally retires B's newer aliases.

That violates R10/R11 stale-builder safety even though no GPU work is involved. A stale command must lose; it must never clean up current state belonging to a newer interface generation.

### Owning-layer repair

Repair the existing replay publication owner; do **not** add a replay-generation database, shadow config, watcher, provider registry, compatibility layer, or global lock.

1. Replace the hand-maintained partial replay-basis dictionary with a compact command-start expectation derived from the **existing canonical owners**: interface discriminator, canonical `ReplaySingleSourceConfig` semantics, pseudo qualification-policy identity/gates that affect prepared qualification/currentness, and for pseudo mode the exact foundation/prediction/doctor-frozen acceleration parents consumed by construction. Execution-only batch/shard/graph-cache controls remain outside scientific currentness.
2. Re-resolve the same canonical live owners immediately before adoption. Do not duplicate parsing/coercion in a second dictionary.
3. Route **single-source publication and single-source-alias retirement** through the same stale-builder fence. The no-replay/legacy command may retire old single-source aliases only when the live interface still matches its command-start expectation and no newer authority has won.
4. Pre-encode any compact records that can safely be encoded before the final mutable-parent check so serialization cannot unnecessarily widen the last-check -> database-adoption window.
5. Under the existing short writer/currentness boundary, compare the database lineage/currentness expectation and live canonical semantics, then perform the final source/checkpoint byte re-authentication immediately adjacent to the atomic alias replacement. If a compare-and-recheck form is used, the second recheck must occur after the deterministic race hook and before the database replacement.
6. Re-resolve the live foundation potential/head/prediction identity for pseudo mode, not merely the old checkpoint path and acceleration record.
7. Any mismatch leaves the previous coherent current aliases intact/non-authorizing and prevents false COMPLETE. Losing content-addressed caches may remain if independently authentic.

### Required falsification

Add/strengthen real-owner tests for:

- mutation **after the last ordinary revalidation but before alias replacement**, separately for replay source and foundation checkpoint;
- pseudo qualification-threshold/policy drift during the command;
- live foundation-model/head/potential drift during pseudo preparation;
- stale no-replay/legacy prepare finishing after a newer single-source prepare: the newer aliases must survive;
- the inverse interface transition under a stale competing builder;
- competing single-source publication;
- canonical-equivalent spelling and identical-byte relocation remaining admissible.

The test hook must prove that the targeted final seam actually fired.

## 2. Blocker B11 - production `except TypeError` retry is an unsafe compatibility fallback

### Finding

`execute_current_prepare()` currently invokes replay preparation as:

```python
try:
    _prepare_single_source_replay(
        cfg, paths, store, command_replay_basis=command_replay_basis
    )
except TypeError:
    _prepare_single_source_replay(cfg, paths, store)
```

This is product compatibility machinery introduced around the new keyword so older three-argument test doubles/callers continue to work. It is not an admissible runtime fallback.

Any genuine `TypeError` raised *inside* replay preparation is now interpreted as an old-call-signature problem. The consequential operation is retried from the top without its command-start basis, potentially duplicating expensive construction/publication side effects and hiding the original defect. This is exactly the class of product fallback-for-harness that SSDP testing rules prohibit, and it conflicts with this workplan's explicit reduction-over-wrapper/fallback constraint.

### Owning-layer repair

Remove the `except TypeError` retry completely. The production route calls the current replay owner exactly once with its command-start expectation.

Update affected tests/doubles/callers to accept/forward the actual keyword (or `**kwargs`) instead of making production tolerate an obsolete test signature. Do not replace the retry with signature introspection, a compatibility wrapper, or a second fallback route.

### Required falsification

Inject a genuine internal `TypeError` after replay preparation has been entered and prove:

- the original exception propagates;
- replay preparation was entered exactly once;
- no second call occurs without command-start currentness;
- no duplicate alias/current-state side effect is produced.

## 3. Blocker B12 - B8 product structure is acceptable, but its no-partial-state oracle is too shallow

### Finding

The new B8 tests now exercise the requested chmod and pre-executor setup failures, and their provider-close/caller-ownership assertions are useful. However the assertions intended to prove **no reusable partial cache and no attempt scratch** use shallow paths such as:

```python
cache_root.glob("manifest.json")
cache_root.glob("*.work.*")
```

The production cache layout is nested by key prefix, and the cold-build scratch directory is created under `directory.parent` as `<key>.work.<random>`. A leaked nested scratch directory or nested manifest would therefore not be seen by those assertions. The required evidence could remain green while the precise residual-state defect it claims to falsify is present.

### Evidence-only repair

Strengthen the existing tests; do not change product code unless the corrected oracle exposes a real cleanup defect.

Use the exact resolved prediction-cache directory/key or recursive checks (`rglob`) so every nested `manifest.json` and `<key>.work.*` attempt is covered. Keep the close-count and caller-ownership assertions. Where economical, prove the oracle's sensitivity with a nested sentinel/counterfactual rather than assuming the glob shape is correct.

## 4. Blocker B13 - final acceptance evidence is still not recoverably complete for `07ef36d...`

### Finding

The target-host evidence is materially improved:

- E1 is a fresh two-cycle in-process realization and its README summary now agrees with the raw E1 numbers;
- E2 is a fresh assembled `doctor -> prepare -> P5 -> pre-TRAIN2` realization and its summary agrees with its raw log.

However final SSDP acceptance still cannot be reconstructed for this semantic candidate:

- the repository exposes no commit status or GitHub Actions realization for `07ef36db48870427d68e266a46ff2c4362875f68`;
- no focused/affected/final regression or applicable static/build/package-check realization is committed alongside the candidate;
- the E1/E2 raw evidence does not identify the exact Git commit/tree or dirty/clean working-tree state from which it was run, so applicability to `07ef36d...` cannot be independently recovered from the artifact alone.

The parent final criteria require focused/stage-local/final affected regression and repository checks, E1+E2 target-host evidence, and closure of materially affected evidence. A test *definition* is not an execution result, and an unbound target-host log cannot by itself establish candidate applicability.

### Required closeout after B10-B12

1. Run the focused replay ownership/currentness/concurrency/lifecycle suite, including all first/second/third-review falsification cases and the TypeError no-retry counterexample.
2. Run the complete affected regression surface: replay unification/invalidation/P5 integration, target-size lifecycle/currentness, qualification observation, and any other callers materially touched by the final repair.
3. Run repository-required static/build/package checks applicable to the changed files.
4. Record the exact candidate Git commit/tree plus working-tree cleanliness (or an equivalently strong source identity) with those realizations.
5. Rerun E2 after the final B10/B11 executable changes and bind the evidence to that exact candidate/tree. Rerun E1 only if the provider-lifetime product path changes again; otherwise the current E1 realization may be preserved once its applicability to the final candidate is explicitly bound.
6. Keep E1 and E2 metrics separate and consistent with their raw logs.
7. Reconcile the separate TRAIN2 zero-safe/live-memory evidence only where the final replay delta actually changes its assumptions; do not expand this replay workplan into unrelated TRAIN2 work.
8. Any required check that remains unavailable/unexecuted remains blocking.

## 5. Preserved closures and non-goals

Do not reopen or redesign the parts already established by implementation and evidence:

- omitted single-source mode -> `TRUE_DFT`; pseudo remains explicit opt-in;
- TRUE_DFT prepare performs zero replay foundation inference and has no pseudo fallback;
- doctor remains validation-only for current single-source replay;
- public `prepare` remains the sole single-source scientific replay construction owner;
- P5 remains scientific-read-only and reconstructs only disposable representations from authenticated parents;
- pseudo training plus independent TRUE_DFT monitor semantics remain unchanged;
- same-key cold prediction remains single-flight through the narrow artifact-publication fence;
- B1 provider lifetime control flow remains one internal provider owner -> one executor owner, with one OOM-learning lifetime and caller ownership preserved;
- prediction inputs remain label-blind and consumed frames remain geometry-authenticated;
- B4 exact prediction batch/shard and split-seed domains remain closed;
- B7 one-snapshot lifecycle replay currentness and digest validation remain closed;
- target-size scientific generation remains replay-independent;
- current E1/E2 qualitative CUDA ownership observations remain useful evidence, subject only to final candidate applicability/rerun rules above;
- TRAIN2 zero-safe admission/live-memory envelope is not weakened to compensate for replay;
- no scientific/numerical/schema/method-version bump without a separately justified semantic change;
- no additive wrapper, fallback, shadow authority, readiness registry, second snapshot, global cache, or new long-lived synchronization mechanism where the existing owner can be simplified/parameterized/reordered.

## 6. PASS criteria for the next review

PASS requires all of the following on one final semantic candidate:

1. B10 provides one complete stale-builder/current-parent fence for publication **and interface retirement**, covers all materially current replay/qualification/foundation parents, and closes the last-check -> alias-adoption race without holding the writer across GPU work.
2. B11 removes the TypeError compatibility retry so the replay owner is invoked exactly once and genuine internal errors propagate.
3. B12's corrected nested-state oracle passes without requiring compensating product machinery.
4. B13 focused + affected + repository checks are recoverable and applicable to the final candidate/tree.
5. E2 applies to the final executable candidate; E1 applies to the final provider-lifetime implementation, and both evidence summaries match their raw realizations.
6. Parent R1-R28 and final criteria 1-36 remain satisfied, including exact current alias replacement, mutable-source safety, one coherent lifecycle snapshot, P5 read-only behavior, target-size independence, and unchanged TRAIN2 live-memory safety.
7. No newly discovered genuine blocker or Serious Challenge remains.

Until all seven hold, the parent work remains **NO-PASS / ACTIVE-REOPENED**.
