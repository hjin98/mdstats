---
kind: review-evidence
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.5
protocol_version: 5.8.0
reviewed_evidence_head: cdb6a3c5ac90c585ac3992fdc546908dd1467919
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
review_verdict: NO-PASS
review_date: 2026-09-01
---

# P7 revision 13.5 — independent review evidence

## Verdict

**NO-PASS.** No new source defect is established; the frozen R13.3 executable repair remains accepted. The new R13.4 evidence is materially better but does not satisfy the final production qualification contract.

## Accepted new evidence

1. The evidence now uses a non-analytic production reference protocol identity (`dft-pbe-ts-reference.v1`) and truthfully reports missing external calculations as `waiting_for_reference` rather than manufacturing a pass.
2. The evidence now demonstrates a genuinely new Python interpreter reopening the durable qualification graph. That closes the mechanism-level process-restart concern for the intermediate waiting state.
3. The reported affected regression remains `155 passed, 1 skipped`; no executable source changed after the accepted candidate freeze, so this evidence remains reusable.

## Blocking findings

### 1. R13.5-B11E — production publication lineage remains unproven

The new evidence reports selected target size `N=4`. The repository's acceptance fixture (`tests/test_mlff_target_size_p4d_runtime_cutover.py`) configures target-size powers 1..3 and its bounded screen operates on sizes `{2,4,8}`. The evidence also records `seed-5` and checkpoint SHA `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`, exactly the checkpoint SHA recorded in the previously rejected R13.3 tiny-MACE fixture evidence.

Those facts are incompatible with treating the record as independent proof that the operator's pre-existing production campaign was used. Final B11 must begin from the actual existing production config/workspace and resolve its already-owned selected binding, CV/final-production identities, P5 publication, member and checkpoint before any qualification work starts.

### 2. R13.5-B11F — candidate/package identity is internally contradictory

The R13.4 evidence claims executable commit `97fa48fc...`, tree `9e4be0fc...`, source digest `7772ad5f...`, but declares package version `0.20.198a0`.

Direct inspection of `mdstats/_version.py` at commit `97fa48fc...` gives `__version__ = "0.20.242a0"`. The R13.3 evidence for the same executable commit/source digest also records `0.20.242a0`.

The final run must therefore record the qualifying interpreter's actual import path and `resolve_executable_candidate_identity()` output. A run performed by a different checkout/installed source cannot qualify the frozen candidate. A stale distribution-metadata version may be recorded separately but cannot replace the executable candidate package version.

### 3. R13.5-B12H — final scientific qualification has not run

The new evidence explicitly states that real external DFT calculations have not yet been produced/imported. `physical_pes`, `relaxation` and `dynamics` are `waiting_for_reference`; the locked test is unopened; the terminal state is `WAITING_FOR_REFERENCE`.

This is correct behavior and useful evidence of fail-closed waiting semantics. R13.4 explicitly states that `waiting_for_reference` is not P7 PASS. Real independent first-principles results must be imported for the exact frozen request, all mandatory components must complete, the one-shot locked test must be explicitly activated/executed, and the terminal verdict must become `RELEASE_QUALIFIED`.

### 4. R13.5-B12I — final release graph still needs fresh-process reauthentication

The new-process mechanism itself is now accepted, but it currently reopens only the waiting graph. After final `RELEASE_QUALIFIED` closure, the qualifying process must exit and a new process must reauthenticate the final binding/publication/reference/component/resource/locked/terminal/release graph.

## Routing

This is **not an executable implementation reopen**. Keep `97fa48fc...` frozen. The remaining work is production-environment/evidence execution under R13.5. Only a genuine source defect found by that production run should return to Software Implementation.

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked until final independent P7 PASS.
