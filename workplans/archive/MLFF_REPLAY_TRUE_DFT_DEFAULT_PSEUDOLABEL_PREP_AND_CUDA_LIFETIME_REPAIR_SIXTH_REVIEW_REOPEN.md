---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-6
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
predecessor_review_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-5
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: eb3221397457b5cf374298c4b4979e1e1d0c0c96
evidence_followup: 7edb84c38f1930106ffeac30f377f45dd66c8539
highest_affected_domain: D4 final acceptance evidence closure
serious_challenge: none
precedence: This review supersedes only the fifth implementation-review disposition. It accepts the B17 exact-domain qualification-gate repair, the rerun E2 realization, explicit E1 applicability, and the recorded focused/affected/integration/static/build/package realizations for executable candidate eb3221397457b5cf374298c4b4979e1e1d0c0c96. All non-conflicting parent R1-R28/final criteria and prior accepted B1/B4/B7/B11/B12/B14/B15 closures remain binding. The work remains open only for the one missing final-acceptance realization below.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - sixth implementation Review reopen

## 0. Disposition

Executable candidate `eb3221397457b5cf374298c4b4979e1e1d0c0c96` (tree `2bc60f52d6eba36f65a25d2f6aa28cf96975a43e`), with evidence/documentation follow-up `7edb84c38f1930106ffeac30f377f45dd66c8539`, is **NO-PASS / REOPENED** under SSDP 6.2. No Serious Challenge is active.

This pass independently reconstructed the fifth-review blockers, the B17 product delta, the final replay preflight/currentness owner, the candidate-bound functional acceptance record, E1/E2 applicability, and the explicitly required affected-regression surface rather than inheriting the implementation's stated verdict.

The implementation is now materially converged. No new product defect was found in the B17 repair.

### Accepted closures

- **B17 is closed.** `_replay_qualification_gate_semantics(...)` no longer applies raw `int(...)` / `bool(...)` coercion to replay qualification gates. Minimum-count fields reject booleans, fractions, strings and negative values; qualification booleans require actual booleans; target atomic-number inputs are normalized through the same gate owner. `_replay_topology_preflight(...)`, `_single_source_replay_basis(...)`, and `_qualify_replay(...)` consume this same resolved semantics rather than independent coercive interpretations.
- **B17 cheap-preflight ordering is closed.** A replay declaration now runs the qualification-gate resolver from the already-established cheap replay topology preflight, before the command-start replay basis can hash the replay source or resolve/inspect the foundation model. The real public-prepare falsification test covers malformed boolean/count values and guards expensive foundation/target-size work from running first.
- **B14/B15 remain closed.** The B17 executable delta is confined to qualification-gate resolution/preflight plus tests; it does not alter the accepted final publication/retirement adoption fence or public prepare ordering.
- **E2 is current for this candidate.** `E2_ASSEMBLED_CLI_STAGE_EVIDENCE.txt` records exact provenance `commit=eb3221397457b5cf374298c4b4979e1e1d0c0c96`, `tree=2bc60f52d6eba36f65a25d2f6aa28cf96975a43e`, `clean=True`, with doctor -> prepare -> P5 -> pre-TRAIN2 passing on the target RTX 3090 host. Doctor constructs zero replay providers/predictions/current aliases; prepare constructs/closes exactly one provider/executor and performs 128 predictions; P5 performs zero new replay inference; post-prepare allocated CUDA memory returns to 45.9 MiB from a 2198.2 MiB inference peak; scheduler baseline is 1.32 GiB with a nonzero admission ceiling.
- **E1 remains applicable.** The executable delta does not modify `mdstats/training_data/replay_pseudolabel.py`; the committed functional acceptance record explicitly binds the existing provider-retirement realization to this candidate by unchanged product-path applicability.
- **Most B18 functional acceptance is now recoverable.** `FUNCTIONAL_ACCEPTANCE_EVIDENCE.txt` binds the exact candidate commit/tree/clean state and records: focused replay suite `118 passed`; replay unification `41 passed`; replay recovery/performance/guards/turnover `57 passed`; downstream integration/assembled semantics `33 passed`; multi-size/cutover/materialization `30 passed`; bytecode compilation PASS; `pip check` PASS; wheel build PASS. The total recorded pytest realization is `279 passed, 0 failed`.

One required final-acceptance realization is still absent.

## 1. Blocker B19 - the explicitly required qualification-observation regression did not execute

### Finding

The fifth review's B18 closeout contract explicitly required the final executable candidate's affected regression to include **qualification observation** in addition to replay unification/invalidation/materialization/P5, lifecycle/currentness, target-size prepare/currentness, and materially changed callers.

The repository contains the dedicated real-owner suite:

`tests/test_mlff_qualification_status_observation.py`

That suite is not a helper-only proxy. It drives the real public `qualification status` command, the real campaign owner snapshot, and real P7 stores/publishers; its corruption and coherence matrices protect the operator-facing observation boundary from reporting unauthenticated or cross-snapshot state as current truth.

The committed `FUNCTIONAL_ACCEPTANCE_EVIDENCE.txt` enumerates every executed pytest command used for the claimed final acceptance. It includes the focused replay suite and four affected-regression command groups, but **does not execute or record** `tests/test_mlff_qualification_status_observation.py`. The recorded `279 passed` total therefore does not include this explicitly required realization. GitHub provides no independent status/Actions realization that closes it either.

Under SSDP 6.2, a required check that did not execute is not a pass. This is now an **evidence-only blocker**: the B17 product repair itself does not need another code patch merely to satisfy the missing realization.

### Required closeout

Do not change product code unless the missing real-owner regression actually fails.

1. On the exact executable candidate `eb3221397457b5cf374298c4b4979e1e1d0c0c96` / tree `2bc60f52d6eba36f65a25d2f6aa28cf96975a43e`, run:

   ```text
   conda run -n mace pytest tests/test_mlff_qualification_status_observation.py
   ```

2. Preserve a recoverable candidate-bound record of the command, exit status, test result/count, exact executable commit/tree, and clean/dirty source state. Updating `FUNCTIONAL_ACCEPTANCE_EVIDENCE.txt` or adding an equally recoverable acceptance artifact is sufficient.
3. If the suite passes and no executable source changes, preserve the existing 279-test realizations, E2, and E1 by applicability; they do **not** need to be rerun merely because an evidence text file changes.
4. If the suite fails and product code must change, the resulting executable commit becomes a new candidate. Re-evaluate affected evidence normally: rerun the focused/affected checks touched by the repair and rerun E2 if its public route is affected. Do not patch around the observation test or weaken its oracle.
5. Do not broaden this closeout into unrelated P7 requalification, TRAIN2 qualification, new CI machinery, or another replay/currentness mechanism. The missing obligation is one already-named regression realization.

## 2. Preserved closures and non-goals

The next pass must not reopen settled architecture merely because one evidence command was omitted:

- omitted single-source mode -> `TRUE_DFT`; pseudo remains explicit opt-in;
- TRUE_DFT prepare performs zero foundation replay inference and has no pseudo fallback;
- doctor remains validation-only for current single-source replay;
- public `prepare` remains the sole single-source replay-science construction owner;
- P5 remains scientific-read-only and reconstructs only disposable representations from authenticated parents;
- pseudo train + independent TRUE_DFT monitor semantics remain unchanged;
- same-key cold prediction remains single-flight;
- B1 provider lifetime remains one internal provider owner -> one executor owner with caller ownership preserved;
- prediction inputs remain label-blind and consumed geometry remains authenticated;
- B4 split seed and prediction batch/shard exact domains remain closed;
- B7 one-snapshot lifecycle currentness/digest validation remains closed;
- B11 TypeError compatibility retry remains removed;
- B12 recursive nested cleanup oracle remains accepted;
- B14 final publication/retirement semantic-parent fence remains closed;
- B15 cheap public prepare preflight ordering remains closed;
- B17 exact qualification-gate domains remain closed;
- target-size scientific identity remains replay-independent;
- TRAIN2 zero-safe/live-memory safety is not weakened;
- no scientific/numerical/schema/method-version bump is justified;
- no additive wrapper, fallback, shadow authority, registry, generation system, or new synchronization mechanism is warranted.

## 3. PASS criteria for the next review

PASS requires only the remaining bounded closure, provided the executable candidate stays unchanged:

1. `tests/test_mlff_qualification_status_observation.py` is executed successfully against exact executable candidate `eb3221397457b5cf374298c4b4979e1e1d0c0c96` / tree `2bc60f52d6eba36f65a25d2f6aa28cf96975a43e`, with recoverable provenance and result.
2. The existing candidate-bound focused/affected/integration/static/build/package evidence remains unchanged and applicable.
3. E2 remains applicable to the same executable candidate and E1 remains explicitly applicable through the unchanged provider-lifetime path.
4. No newly discovered genuine blocker or Serious Challenge appears.

If those four conditions hold without executable edits, close/archive the replay workplan and its review-reopen transition artifacts according to repository convention rather than initiating another implementation round.

Until then, the parent work remains **NO-PASS / ACTIVE-REOPENED**.
