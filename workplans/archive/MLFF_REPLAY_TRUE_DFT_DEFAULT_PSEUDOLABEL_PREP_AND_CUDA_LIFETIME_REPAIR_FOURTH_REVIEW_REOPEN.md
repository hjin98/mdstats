---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-4
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
predecessor_review_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-3
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: 71a9b9f4f2217c6e102d41e8245b04cc183f15e2
evidence_followup: f8da6e1219e3982a96e420d36eacace5c47b25fa
highest_affected_domain: D3 replay current-alias publication/currentness and prepare-entry ordering -> D4 implementation and final acceptance evidence
serious_challenge: none
precedence: This review supersedes only the third implementation-review disposition. It accepts the B11 no-retry repair and B12 nested-state oracle repair, and accepts the rerun E2 realization as applicable evidence for executable candidate 71a9b9f4f2217c6e102d41e8245b04cc183f15e2. All non-conflicting parent R1-R28/final criteria, prior accepted B1/B4/B7 closures, and the separate TRAIN2 zero-safe/live-memory authority remain binding. The work remains open only for the blockers and evidence closure below.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - fourth implementation Review reopen

## 0. Disposition

Executable candidate `71a9b9f4f2217c6e102d41e8245b04cc183f15e2`, with evidence/documentation follow-up `f8da6e1219e3982a96e420d36eacace5c47b25fa`, is **NO-PASS / REOPENED** under SSDP 6.2. No Serious Challenge is active. The accepted D3/workplan remains coherent and realizable; the remaining findings are D4 conformance and acceptance-evidence defects.

This pass independently reconstructed the final replay-publication seam, no-replay/legacy retirement route, command-start expectation construction, public prepare ordering, B11/B12 tests, and E2 provenance rather than inheriting the implementation's stated closure.

The candidate materially closes important parts of the third review:

- **B11 is closed in product structure.** `execute_current_prepare()` invokes `_prepare_single_source_replay(...)` once with `command_replay_basis`; the `except TypeError` compatibility retry is gone. A new counterexample test injects an internal `TypeError`, requires propagation, and counts exactly one replay-owner entry.
- **B12 is closed in evidence specification.** The B8 cleanup assertions now use recursive nested-layout checks (`rglob`) and a sensitivity test proves the old shallow glob would miss the production-shaped nested manifest/work residue while the new oracle detects it.
- **The file-byte half of B10's last seam is repaired.** Replay records are pre-encoded before the final seam; `_TEST_REPLAY_PUBLICATION_PRE_COMMIT_SEAM_HOOK` now sits after ordinary validation; replay source and foundation-checkpoint bytes are rehashed after that hook and immediately before atomic database replacement. New tests exercise source and checkpoint mutation at that seam and establish that the seam fired.
- **E2 is now a recoverable realization for this executable candidate.** `E2_ASSEMBLED_CLI_STAGE_EVIDENCE.txt` records commit `71a9b9f4f2217c6e102d41e8245b04cc183f15e2`, tree `c2c0001c81ded4b9eccfe768825a0adeec536e1d`, and `clean=True`. The rerun still shows doctor performing zero replay prediction/publication, prepare owning exactly one provider/executor/close and 128 predictions, P5 performing zero new replay inference with matching lineage, and a clean pre-TRAIN2 scheduler baseline. The README summary agrees with the raw realization.

Those closures are real. Three genuine blockers remain.

## 1. Blocker B14 - B10 is only half-closed: the final semantic-parent seam still admits stale alias adoption/retirement

### Finding A - post-hook revalidation authenticates bytes but not canonical replay/configuration semantics

`_publish_single_source_replay_authority()` now performs ordinary live-currentness checks, pre-encodes the records, invokes `_TEST_REPLAY_PUBLICATION_PRE_COMMIT_SEAM_HOOK`, then performs a second recheck. That second recheck authenticates only:

- the current replay-source bytes; and
- for pseudo mode, the checkpoint bytes referenced by the already-built prediction policy.

It does **not** reload the campaign configuration or rederive/recompare the canonical replay expectation after the hook.

A deterministic stale-current counterexample therefore remains:

1. a TRUE_DFT prepare builds under split/mode/qualification semantics A;
2. ordinary live-config/source checks pass under A;
3. records are pre-encoded;
4. the final seam hook changes `campaign.toml` to semantics B, for example a different split seed, label mode, qualification gate, or replay interface, while leaving the replay file bytes unchanged;
5. the post-hook source-byte check still passes and TRUE_DFT has no foundation checkpoint to check;
6. the old A alias set is committed as current under live configuration B.

The later public-stage configuration digest may correctly leave `prepare` WAITING, but that does not repair the D3 violation: R11/R14 and the third review require the stale builder to lose **before current aliases are adopted**, not merely for stage completion to notice afterward.

The same failure family applies to pseudo semantic parents. A final-seam edit of a pseudo qualification threshold, foundation head/family/model locator, acceleration-relevant model setting, or interface can occur after the last canonical-owner comparison. The post-hook checkpoint rehash proves only that the old checkpoint bytes still exist; it does not prove that the live campaign still denotes the same canonical prediction parent.

The new qualification-policy and foundation-head drift tests mutate configuration before ordinary revalidation. They therefore do not falsify this last semantic-parent seam.

### Finding B - interface retirement still has an earlier semantic check followed by a separate delete path

The `context is None` route is substantially safer than before: it now holds the existing writer exclusion, checks the baseline lineage, reloads live configuration, and refuses an interface mismatch before calling `_retire_single_source_replay_aliases()`.

However the final live-interface check is still separated from the actual alias deletion by the retirement helper's own record-key enumeration and `replace_records_atomically(...)` call. The writer exclusion blocks competing campaign-state writers but does not freeze `campaign.toml`. A configuration edit can therefore occur after the interface check and before deletion. The stale command can then retire aliases even though its command-start interface is no longer live.

This is the same B10 semantic family, not a request for another lock or generation system: publication and retirement both need one final compare-and-recheck boundary immediately adjacent to the atomic state mutation.

### Finding C - the expanded replay basis is still duplicated reconciliation machinery rather than one compact canonical expectation

`_single_source_replay_basis()` grew into a hand-maintained dictionary containing overlapping representations of the same semantics:

- `config_semantics` plus separate `label_mode`, `split_ratio`, and `split_seed` fields;
- `qualification_gates` plus separate duplicated minimum-train/minimum-monitor values;
- source locator/hash fields mixed with semantic parents;
- pseudo policy digest plus policy payload;
- foundation-potential digest/reference/checkpoint hash;
- acceleration and inference digests plus runtime device/dtype.

Publication then manually compares a selected subset of those fields rather than comparing one canonical expectation as a whole. Several pseudo-owner resolutions are also wrapped in broad `except Exception: pass`, so the token can silently become partial instead of failing at the owner that could not be resolved.

This is not merely cosmetic duplication. The incomplete final semantic recheck above is exactly the recurrence the third review tried to prevent by requiring one command-start expectation derived from canonical owners and the same live expectation at adoption. Under the Protocol 6.2 convergence rule, another additive list of field-by-field rechecks is the wrong repair direction.

### Owning-layer repair

Repair and simplify the existing publication/currentness owner; do **not** add a replay generation database, shadow configuration, watcher, global filesystem/config lock, compatibility wrapper, second registry, or another field-by-field currentness table.

1. Reduce `_single_source_replay_basis()` to one compact immutable expectation assembled from the existing canonical owners. It should carry only the interface discriminator and material replay/configuration/qualification/prediction parents needed to decide whether this builder may adopt state. Remove redundant copies and fields that are not part of that decision. Execution-only prediction batch/shard/graph-cache controls remain excluded.
2. Resolve failures explicitly. If a required pseudo parent cannot be resolved, fail through its existing owner; do not silently omit it from the expectation with broad `except Exception: pass`.
3. Pre-encode records and precompute the retirement delete set before the final currentness boundary where safe.
4. Under the existing short writer/currentness boundary, after the deterministic final-seam hook, reload the live configuration and derive **the same compact canonical expectation** again. Compare it as a whole to the command-start expectation, with the already-accepted identical-byte replay-source relocation equivalence preserved.
5. Immediately after that semantic comparison, perform the final replay-source/checkpoint byte authentication and then the atomic alias replacement/deletion. Do not insert serialization, alias discovery, or another material operation between final validation and state mutation.
6. Route single-source publication and no-replay/legacy alias retirement through this same final adoption fence. A retirement command may delete single-source aliases only if its live interface/currentness expectation still matches its command-start expectation and no newer lineage won.
7. A mismatch preserves the previous coherent current namespace and leaves the command non-authorizing; content-addressed losing cache bytes may remain if independently authentic.

### Required falsification

Strengthen the real-owner tests so the final seam itself is exercised for semantic parents, not only files:

- TRUE_DFT: change split seed or label mode at `_TEST_REPLAY_PUBLICATION_PRE_COMMIT_SEAM_HOOK`; old aliases must not commit;
- pseudo: change a qualification threshold/policy and foundation head/model identity at the final seam; old aliases must not commit;
- retirement: change no-replay/legacy -> single-source (and the inverse where applicable) at the final retirement seam; stale deletion must not occur;
- preserve the existing final-seam source/checkpoint mutation tests, competing-publication test, canonical-equivalent spelling test, and identical-byte replay-source relocation test;
- every hook-based test must prove the intended seam actually fired.

## 2. Blocker B15 - the expanded command-start basis now violates R3 cheap-preflight ordering

### Finding

`execute_current_prepare()` currently does:

```text
load config
open store
compute preparation digest
compute _single_source_replay_basis(...)
require doctor complete
run _replay_topology_preflight(...)
```

But the new `_single_source_replay_basis()` is no longer cheap configuration normalization. For single-source campaigns it hashes the replay source; for pseudo campaigns it calls `_resolved_foundation_potential_identity(...)`, which resolves a `MaceFoundationSpec` from the checkpoint and therefore loads/inspects the MACE model, and it resolves the doctor-frozen acceleration/prediction parents.

That work now occurs **before** the code comment and parent R3's cheap topology/configuration preflight. Consequently a knowable invalid replay topology can pay replay-file I/O and a foundation-model load before being rejected. The existing R3 tests call `_replay_topology_preflight()` directly and therefore cannot detect this public-route ordering regression.

This is a product-path violation of an already-binding requirement, not a request to weaken or reinterpret R3.

### Owning-layer repair

1. Restore public prepare ordering so `_replay_topology_preflight(cfg, paths)` and the required cheap doctor/stage prerequisite checks happen before any replay-wide source work or foundation checkpoint load introduced by the command-start currentness token.
2. Only after that cheap preflight succeeds, capture the compact command-start expectation required by B14, before the long target-size/replay construction whose adoption it fences.
3. Do not create a second cheap basis plus an expensive basis. The simplification in B14 should make the ordering obvious: cheap canonical topology validation first, then one material currentness expectation for the long operation.

### Required falsification

Add a public `execute_current_prepare()` test with an invalid/conflicting replay topology and sentinels on the expensive replay/foundation owners. Prove the command rejects the configuration before foundation checkpoint inspection/model loading, replay-wide source hashing/parsing, prediction construction, or target-source reconstruction. The test must exercise the public route rather than `_replay_topology_preflight()` in isolation.

## 3. Blocker B16 - B13 final acceptance is still incomplete even though E2 provenance is fixed

### Closed part

The target-host E2 provenance problem is closed for `71a9b9f4f2217c6e102d41e8245b04cc183f15e2`: the committed raw evidence identifies the exact executable commit/tree and clean working tree. Its raw observations and README summary are consistent.

The prior E1 realization remains reusable for the current candidate because this repair did not modify the provider-lifetime implementation in `replay_pseudolabel.py`; its governed provider-retirement path is unchanged. That applicability may be preserved unless the next repair changes that path.

### Remaining finding

No recoverable final functional acceptance realization accompanies the executable candidate:

- GitHub combined status for `71a9b9f4f2217c6e102d41e8245b04cc183f15e2` has zero statuses;
- GitHub Actions reports zero workflow runs for that head;
- the implementation commit contains test **definitions**, but no committed/recoverable focused, affected-regression, integration, or repository static/build/package execution record applicable to the final executable candidate.

Under SSDP 6.2, a required check that did not execute is not a pass, and a test definition is not an evidence realization. This remains blocking independently of the product defects above.

### Required closeout after B14-B15

1. Run the focused replay ownership/currentness/concurrency/lifecycle suite, including all first/second/third/fourth-review falsification cases, B11 no-retry, B12 nested cleanup, and the final semantic-seam counterexamples.
2. Run the complete affected regression surface: replay unification/invalidation/P5 integration, lifecycle/currentness, target-size prepare/currentness interactions, qualification observation, and materially affected callers.
3. Run assembled integration through the real public prepare/replay/P5 boundary after the final executable changes.
4. Run repository-required static/build/package checks applicable to the changed files.
5. Record exact final executable commit/tree and clean/dirty state with those realizations.
6. Rerun E2 after the final B14/B15 executable repair and bind it to that exact final candidate/tree. The current E2 remains valid evidence for `71a9b9f...` but becomes stale for any changed executable candidate.
7. Preserve E1 only if the provider-lifetime product path remains unchanged; explicitly bind that preserved applicability in the final acceptance record. If that path changes, rerun E1.
8. Keep E1 and E2 metrics separate. Do not rerun or broaden the separate TRAIN2 qualification unless the final replay delta changes a TRAIN2 assumption.
9. Any required check that remains unavailable/unexecuted remains blocking.

## 4. Preserved closures and non-goals

Do not reopen or redesign the already-established behavior while repairing B14-B16:

- omitted single-source mode -> `TRUE_DFT`; pseudo remains explicit opt-in;
- TRUE_DFT prepare performs zero replay foundation inference and has no pseudo fallback;
- doctor remains validation-only for current single-source replay;
- public `prepare` remains the sole single-source scientific replay construction owner;
- P5 remains scientific-read-only and reconstructs only disposable representations from authenticated parents;
- pseudo training plus independent TRUE_DFT monitor semantics remain unchanged;
- same-key cold prediction remains single-flight through the narrow artifact-publication fence;
- B1 provider lifetime remains one internal provider owner -> one executor owner with one OOM-learning lifetime and caller ownership preserved;
- prediction inputs remain label-blind and consumed frames remain geometry-authenticated;
- B4 exact prediction batch/shard and split-seed domains remain closed;
- B7 one-snapshot lifecycle replay currentness/digest authentication remains closed;
- B11 production TypeError retry remains removed;
- B12 recursive nested cleanup oracle remains the accepted evidence specification;
- target-size scientific generation remains replay-independent;
- TRAIN2 zero-safe admission/live-memory safety is not weakened to compensate for replay;
- no scientific/numerical/schema/method-version bump without a separately justified semantic change;
- no additive wrapper, fallback, shadow authority, readiness registry, second snapshot, global cache, replay generation, or new long-lived synchronization mechanism where the existing owner can be simplified/reordered.

## 5. PASS criteria for the next review

PASS requires one final executable candidate satisfying all of the following:

1. B14 uses one compact canonical command-start/live expectation and one final compare-and-recheck fence for both publication and interface retirement; semantic configuration/prediction parents and mutable source/checkpoint bytes cannot change at the final seam without aborting adoption.
2. B15 restores cheap public prepare topology/configuration preflight before replay-wide/model work while still capturing the command-start expectation before the long operation it governs.
3. B11 and B12 remain closed without compatibility fallback or weaker cleanup evidence.
4. B16 focused + affected + assembled integration + repository checks are executed, recoverable, and applicable to the exact final candidate/tree.
5. E2 is rerun on that final executable candidate; E1 is either explicitly preserved by unchanged provider-lifetime applicability or rerun if that path changes.
6. Parent R1-R28 and final criteria 1-36 remain satisfied, including exact current alias replacement, external-source safety, one coherent lifecycle snapshot, P5 read-only behavior, target-size independence, and unchanged TRAIN2 live-memory safety.
7. No newly discovered genuine blocker or Serious Challenge remains.

Until all seven hold, the parent work remains **NO-PASS / ACTIVE-REOPENED**.
