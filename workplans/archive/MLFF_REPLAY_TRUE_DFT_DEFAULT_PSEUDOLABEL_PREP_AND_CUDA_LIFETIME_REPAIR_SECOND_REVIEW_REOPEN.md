---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-2
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
predecessor_review_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-1
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: 6d860b2cededde77fa685e9bdb9e8ba7473d8f60
highest_affected_domain: D3 replay currentness/publication/lifecycle coherence/resource ownership -> D4 implementation and evidence
serious_challenge: none
precedence: This review supersedes only the first implementation-review disposition. It accepts the first-review B1 implementation repair, B4 exact-domain repair, and the existence/shape of E2, while preserving every non-conflicting parent R1-R28/final criterion and the separate TRAIN2 zero-safe/live-memory authority. The work remains open only for the blockers and evidence closure below.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - second implementation Review reopen

## 0. Disposition

Candidate `6d860b2cededde77fa685e9bdb9e8ba7473d8f60` is **NO-PASS / REOPENED** under SSDP 6.2. No Serious Challenge is active and no D1/D2 change is requested.

The repair materially closes several first-review findings:

- **B1 executable ownership is repaired:** after an internally constructed replay provider is acquired, ASE import, provider validation, executor construction, scratch creation/chmod, prediction, I/O/publication, and catchable failure are now inside one `try/finally`; ownership transfers once to the existing `StaticMaceInferenceExecutor`, otherwise the provider owner retires it. Caller-supplied providers remain caller-owned and one executor/OOM-learning lifetime spans the cold build.
- **B4 is repaired:** exact positive-integer normalizers now own replay prediction batch/shard domains, the executor no longer silently clamps/casts them, and replay invalidation uses the exact split-seed normalizer.
- **B5/E2 is newly realized:** the target-host assembled evidence drives real `doctor -> prepare -> P5 -> pre-TRAIN2` owners with explicit pseudo mode and records 0 doctor replay predictions, 1 prepare provider/executor, 128 prepare predictions, explicit close back to the pre-prepare process baseline, 0 P5 predictions/providers, matching replay lineage, and admissible pre-TRAIN2 memory.
- public `prepare` now captures its command-start preparation digest and refuses to mark COMPLETE if the live preparation projection changed before completion.

Three implementation blockers and one evidence-closeout blocker remain.

## 1. Blocker B6 - current-alias publication still has an unfenced final parent-currentness window

### Finding

`_publish_single_source_replay_authority()` now checks replay source bytes, changed `campaign.toml` replay semantics, and the pseudo foundation checkpoint before entering `store.writer_exclusion()`. The actual `replay_current_lineage` compare and `replace_records_atomically(...)` happen afterwards under the writer gate. This leaves the same final check-to-commit race the first review required the repair to close: source/checkpoint/config parents can change after their final check but before current aliases are installed.

There is a second command-scope mismatch. `start_config_bytes` is captured only when the replay substage begins, after the target-size part of public `prepare` may already have run for a long time. If `campaign.toml` changes between public-command entry and replay-substage entry, replay construction still uses the command-start in-memory `cfg`, while `start_config_bytes` names the already-modified file; because the file then appears unchanged during the replay substage, the publisher can install an alias set built from the older configuration. The later command-completion digest check correctly leaves public `prepare` WAITING, but the stale alias set has already been published as current, contrary to parent R11/R14 and first-review B3.

For explicit pseudo mode the publisher also does not revalidate the doctor-frozen `acceleration_realization` / foundation-inference parent that `_construct_single_source_replay_context()` used to form `ReplayFoundationPredictionPolicy`. A concurrent/recent doctor turnover can therefore move this parent without moving `replay_current_lineage`; checkpoint bytes alone do not prove the current prediction execution identity.

### Owning-layer repair

Repair the existing `execute_current_prepare` / replay publication currentness flow. Do **not** add a second readiness database, shadow configuration file, provider registry, background watcher, global lock, or new replay generation.

1. Capture the canonical replay/currentness basis from the already-loaded **public-command-start** `cfg`, not from the later replay-substage entry. Pass the needed compact expectation into the existing replay publisher rather than opening another authority.
2. Always compare the live canonical replay semantics against that command-start basis before current-alias adoption; do not make the comparison conditional only on bytes changing after replay-substage entry.
3. Revalidate every long-build parent named by first-review B3: replay source content, effective mode/split/qualification semantics as applicable, pseudo foundation checkpoint/prediction identity, and the doctor-frozen acceleration realization/foundation-inference binding.
4. Make the final parent revalidation and CampaignStore lineage compare adjacent to the atomic alias replacement under the existing short publication/currentness fence, or use the parent workplan's accepted equivalent compare-and-recheck pattern. Never hold the campaign writer across GPU inference.
5. A mismatch at any point must leave the previous coherent current alias set intact (or non-authorizing under the changed configuration), must not publish the stale builder's aliases as current, and must not mark public `prepare` COMPLETE.
6. Preserve identical-byte relocation and canonical-equivalent spelling as non-scientific changes; preserve losing content-addressed cache bytes when independently valid.

### Required falsification

Use deterministic barriers at the **last revalidation -> alias commit** seam, not only mutations immediately after context construction. Falsify at least:

- replay source replacement in the final publication window;
- foundation checkpoint replacement in that window;
- command-start replay/config semantic drift that occurs before the replay substage begins;
- doctor `acceleration_realization` turnover after the prediction policy was constructed;
- competing prepare publication.

In every case assert no stale/hybrid current aliases and no false COMPLETE state. Retain explicit tests for canonical-equivalent spelling and identical-byte relocation.

## 2. Blocker B7 - lifecycle replay currentness is neither fully coherent nor fully authenticated

### Finding

`campaign_owner_snapshot()` now carries both replay-lineage value and status, but public lifecycle projection does not actually use that snapshot as its sole replay-currentness read:

- `project_campaign_lifecycle()` first calls `campaign_owner_snapshot(store)`;
- `_prepare_step()` then calls `_durable_prepare_stage()` -> `_effective_stage(..., "prepare")`, whose new prepare branch opens another database read and calls `_current_replay_lineage_snapshot(...)`;
- if that returns COMPLETE, `_prepare_step()` performs yet another `store.get_payload_optional("replay_current_lineage")` read.

Thus one status answer can combine target/P5/P7 pointers from one SQLite instant with prepare/replay currentness from one or two later instants. This directly violates parent R25/R26 and first-review B2's preserved requirement for one coherent target + replay + P5/P7 snapshot.

The compact lineage parser also treats every nonempty `replay_lineage_digest` string as `"valid"`. A syntactically valid JSON row containing an invalid/non-digest value therefore bypasses the new malformed fail-closed path. The owner already has `validate_digest`; no new integrity mechanism is needed.

### Owning-layer repair

Reduce the duplicate reads rather than adding another snapshot/reconciliation layer.

1. `campaign_owner_snapshot()` must read/parse the replay-current record once inside its transaction and validate the lineage digest through the existing digest validator. Missing, unreadable, non-mapping, empty, or invalid-digest content must be distinguishable from a valid lineage.
2. Public `project_campaign_lifecycle()` and its prepare/P5/P7 projections must consume that one replay-currentness observation. They must not re-read `replay_current_lineage` through `_effective_stage`, `get_payload_optional`, or another database connection after the owner snapshot.
3. If `_effective_stage("prepare")` still needs replay-currentness when called outside lifecycle projection, reuse the same currentness owner or accept an already-observed value; do not create a second semantic decision path.
4. Single-source campaigns with unavailable/invalid lineage remain WAITING/BLOCKED/not-current. Legacy split/no-replay campaigns remain unaffected.
5. Keep status/advance/qualification observation side-effect free: no source parse, provider, prediction, materialization, scientific resplit, or write.

### Required falsification

Add/strengthen tests for:

- valid JSON carrying an invalid lineage digest such as a non-hex/incorrect-length string -> fail closed;
- a writer transition deliberately interleaved **after** `campaign_owner_snapshot()` but before lifecycle step construction -> the returned status must remain a projection of the captured snapshot, not a hybrid later read;
- missing/corrupt single-source lineage -> prepare/P5/P7 non-current and `advance` routes no farther than `prepare`;
- no-replay and legacy-split campaigns -> no false blockage;
- status/qualification observation remains non-mutating and construction-free.

## 3. Blocker B8 - first-review B1 falsification is incomplete

### Finding

The B1 implementation structure is now correct on inspection, and new tests cover an injected `mkdtemp` failure, a mid-prediction failure, and caller-owned provider success/failure. The first review, however, explicitly required post-acquisition fault injection across **scratch creation/chmod and a catchable import/setup failure**, because those were the uncovered escape families.

The candidate has no corresponding chmod/import/setup fault realization. Under SSDP 6.2 a required check that did not execute is not converted into a pass merely because adjacent tests are green.

### Required evidence-only repair

Do not change product code unless one of these tests exposes a defect. Add bounded fault injection for:

1. `os.chmod(work, ...)` failure after executor acquisition;
2. a catchable post-provider import/setup failure before executor ownership is established.

For each, assert exactly one internal-provider terminal retirement, caller ownership preserved where applicable, no reusable cache manifest, and no live attempt scratch. Preserve the existing mkdtemp/prediction/cancellation/OOM-lifetime checks.

## 4. Blocker B9 - final evidence applicability is not closed on candidate `6d860b2...`

### Finding

E2 is present and is useful real-owner target-host evidence. It can be retained as evidence for the current assembled route until B6 changes that route; after B6 it must be rerun on the final candidate.

E1, however, was **not** rerun after B1 materially changed the provider-lifetime control flow. `E1_REPLAY_PROVIDER_RETIREMENT_EVIDENCE.txt` is byte-identical to the pre-repair realization and records the earlier high-water values (for example cycle A max allocated 1437.6 MiB, cycle B max reserved 2920.0 MiB). The updated qualification README instead reports E1 values of 2198.2/2864.0 MiB, which are the new E2 prepare high-water values rather than the unchanged E1 artifact. The evidence summary therefore contradicts its referenced realization and obscures that E1 is stale for the changed lifetime candidate.

No GitHub Actions/status realization exists for commit `6d860b2...`, and the repair commit contains no recoverable final focused/affected regression or package/static-check result. The first review required those checks on the final semantic candidate.

### Required closeout

After B6-B8 are closed on one final candidate:

1. run the focused replay ownership/currentness/concurrency/lifecycle suite including all first- and second-review falsification tests;
2. run the complete affected regression surface named by the parent/first review, including replay unification/invalidation/P5 integration, target-size lifecycle/currentness guards, and materially affected qualification observation;
3. run applicable repository static/build/package checks;
4. rerun **E1** on target-host CUDA because the provider lifetime implementation changed after its stored realization; bind the result to the final candidate and retain two disjoint cold-build/non-accumulation evidence while the process stays alive;
5. rerun **E2** after the final publication/currentness repair so the assembled `doctor -> prepare -> P5 -> pre-TRAIN2` evidence applies to the final code;
6. correct the qualification README to summarize the actual E1 and E2 artifacts independently; do not copy E2 metrics into E1;
7. record enough candidate/environment identity for E1/E2 and final regression applicability to be independently recoverable;
8. reconcile the separate TRAIN2 zero-safe/live-memory evidence only where this final executable delta materially affects its assumptions; do not require unrelated TRAIN2 work to close this replay workplan.

## 5. Preserved closures and non-goals

Do not reopen or redesign the accepted parts merely to satisfy this review:

- omitted single-source mode -> TRUE_DFT; pseudo remains explicit opt-in;
- TRUE_DFT prepare performs zero replay foundation inference and has no pseudo fallback;
- doctor is validation-only for single-source replay;
- public `prepare` remains the sole single-source scientific replay construction owner;
- P5 remains scientific-read-only and may rebuild only disposable representations from authenticated parents;
- pseudo training and independent TRUE_DFT monitor semantics remain unchanged;
- same-key cold prediction remains single-flight through the existing narrow artifact-publication fence;
- one cold-build executor and one OOM-learning lifetime remain authoritative;
- prediction inputs remain label-blind and consumed frames remain geometry-authenticated;
- exact atomic mode/interface alias replacement and history/content-addressed preservation remain unchanged;
- exact batch/shard/split-seed validation remains in the existing replay owner;
- target-size scientific generation remains replay-independent;
- TRAIN2 zero-safe admission/live-memory envelope is not weakened or modified to compensate;
- no scientific/numerical/schema/method-version bump without an independently justified semantic change;
- no additive wrapper, fallback, shadow authority, readiness registry, second snapshot, or global cache when removal/parameterization/rewiring of the existing owners is sufficient.

## 6. PASS criteria

PASS on the next review requires all of the following on one final semantic candidate:

1. B6 closes the command-start and final publication/currentness races, including the doctor-frozen acceleration parent.
2. B7 restores one coherent authenticated replay-currentness observation for lifecycle and fails closed on invalid digest content without disturbing legacy/no-replay behavior.
3. B8 required post-acquisition fault-injection cases pass without product workaround.
4. B9 focused + affected + repository checks are recoverable and applicable to the final candidate.
5. Target-host E1 and E2 both apply to the final candidate and their summaries agree with raw evidence.
6. Parent R1-R28 and final criteria 1-36 remain satisfied, including current alias atomicity, mutable-source safety, P5 read-only behavior, target-size independence, and no D1/D2 drift.
7. No newly discovered genuine blocker or Serious Challenge remains.

Until then this work remains **NO-PASS / ACTIVE-REOPENED**.