---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.4
status: reopened
reviewed_implementation_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
reviewed_implementation_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
post_qualification_documentation_head: 6f37e1f2768ed3c2cc185da8c0751a3ae3678597
review_verdict: NO-PASS
current_amendment: P7_REVISION_13_4_IMPLEMENTATION_REVIEW_REAL_OWNER_QUALIFICATION_REOPEN_AMENDMENT.md
current_review_evidence: P7_REVISION_13_4_REVIEW_EVIDENCE.md
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.4 — authoritative reopened workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the controlling scientific and architectural verdict.

Independent Software Design review of executable candidate
`97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree
`9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, accepts the revision-13.3 executable repair. The later `6f37e1f2768ed3c2cc185da8c0751a3ae3678597` head records implementation/qualification evidence only and does not change importable mdstats source.

P7 nevertheless remains **NO-PASS / REOPENED** because the recorded final qualification evidence did not cross three frozen production-owner boundaries: it used the repository's manufactured P5/P7 acceptance fixture publication, it used `bounded-analytic-reference.v1` rather than real external first-principles references, and it demonstrated same-process session reconstruction rather than an actual process restart.

## Current authority precedence

Read P7 as one composed authority in this order:

1. frozen parent scientific workplan;
2. accepted/reclosed predecessor P1-P6 authorities;
3. `P7_REVISION_13_4_IMPLEMENTATION_REVIEW_REAL_OWNER_QUALIFICATION_REOPEN_AMENDMENT.md` — current final qualification/evidence boundary;
4. `P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md` — accepted executable repair and preserved runtime/environment identity contract;
5. R13.2/R13.1/R13/R12/R11/R10/base-P7 authorities where non-conflicting;
6. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor boundary.

`P7_REVISION_13_4_REVIEW_EVIDENCE.md` records the independent review of the R13.3 candidate and its evidence. Earlier review/implementation records remain historical evidence only.

## Accepted executable surfaces — preserve

Do not redesign or edit these absent contradictory real-production evidence:

- R13.3 generic/default LAMMPS diagnostics are removed from mandatory environment/session construction, deployment parity and selected-worker pre-control; diagnostic state no longer owns binding/currentness.
- Environment identity queries the exact selected `cuda:N` device and rejects invalid/out-of-range selection.
- P5 owns final publication membership; P7 never ranks, shrinks, substitutes or falls back among members.
- Canonical target-head identity remains mandatory through publication/export/ML-IAP/runtime execution.
- R12 LAMMPS bar/pressure-sign canonical stress conversion remains fixed at the source adapter.
- R13 stress capability is component/member/claim/geometry scoped, missing applicable stress fails closed, and external stress source provenance is authenticated.
- R13 cumulative resource lineage, disk reserve/headroom, exact PBC/cell observation, and release/terminal/resource/reference referential integrity remain accepted.
- R13.2 selected KOKKOS/mliappy MACE child-worker execution, callback evidence, abnormal-exit blocking, process isolation and no external Python finalization remain accepted.
- One-shot locked semantics and accepted R11/R12 publication/currentness/reference behavior remain binding.

The reported R13.3 focused/affected regression result (`155 passed, 1 skipped`) remains reusable because this revision requires no executable edit. Documentation-only review changes do not invalidate it.

## Current blockers

### R13.4-B11D — final B11 publication evidence used a test-created campaign

The R13.3 evidence records member `seed-5` and `bounded-analytic-reference.v1`, matching the repository's P7 acceptance fixture. That fixture creates a new temporary selected/P5 campaign and can publish a deliberately tiny synthetic multihead MACE checkpoint for real exporter/ML-IAP integration testing.

That is valid functional evidence, but R13.3-P4 requires the **pre-existing actual current durable P5/P6 publication from the production campaign**. A fixture-manufactured publication or direct runtime smoke cannot close final B11.

Keep executable candidate `97fa48fc...` frozen and run B11 through the production P7 owner over the actual current publication. Record the publication digest/member/checkpoint SHA/target head before qualification and require the deployment-parity evidence to bind those same identities plus the real deployment artifact SHA and selected worker launch arguments.

### R13.4-B12F — final B12 reference evidence is analytic, not real external DFT

The base P7 contract permits synthetic/analytic references for functional tests only. Production scientific qualification requires real independent external first-principles/DFT references generated under the frozen production request/protocol identity.

The R13.3 evidence instead records `Reference Request Protocol Identity: bounded-analytic-reference.v1`; the fixture's `supply_analytic_reference_bundle()` constructs that bundle from `AnalyticPairPotential`/harness evaluation. The resulting physical/relaxation/dynamics pass is therefore assembled functional evidence, not final production scientific qualification.

The production campaign must publish/freeze its exact reference request, receive independently generated real external reference results, authenticate/import that bundle, and then run the mandatory nonlocked components and explicit one-shot locked component to terminal `RELEASE_QUALIFIED` on the same frozen candidate/publication. Until real reference work exists, the truthful state is `waiting_for_reference`.

### R13.4-B12G — restart proof is same-process only

R13.3-P6 requires close/reopen after process restart. The recorded evidence calls its check a "simulated process restart" and rebuilds a fresh `QualificationSession` in the same interpreter. That does not exercise the process-level persistence boundary.

After successful real B11/B12/locked closure, terminate the qualifying interpreter and start a genuinely new Python process/CLI invocation. Reopen the same production campaign/store through the public current resolver and prove the exact same binding/publication/reference/component/resource/locked/terminal/release digests and `RELEASE_QUALIFIED` verdict.

## Binding completion sequence

```text
R13.4-P1  keep executable 97fa48fc... / tree 9e4be0fc... frozen
R13.4-P2  resolve and record the pre-existing actual current P5/P6 production publication
R13.4-P3  run real B11 through production deployment parity + selected KOKKOS/mliappy worker
R13.4-P4  fulfil the production reference request with independent real external DFT/reference evidence
R13.4-P5  complete production nonlocked qualification + explicit one-shot locked result
R13.4-P6  terminate the process; reopen/re-authenticate the complete graph in a new process
R13.4-P7  record exact production identities/results and request independent Software Design closure
```

Forbidden final-gate substitutes include `tests._mlff_qualification_fixture`, `tests._mlff_post_selection_fixture`, `QualificationHarness`, `PostSelectionHarness`, `AnalyticPairPotential`, `supply_analytic_reference_bundle()`, `bounded-analytic-reference.v1`, a new temporary P1-P5 campaign created solely for qualification, or an in-process fresh-session reconstruction presented as a process restart.

No executable source edit is permitted during R13.4-P2-P6. If the real production run exposes a source defect, stop, repair it, rerun affected regression/integration, freeze a new candidate, and repeat each real gate plausibly affected by that edit.

## Final closure record

One concise production evidence record must contain:

- executable commit/tree/source digest/package version;
- actual current production publication digest, member ID/run identity/checkpoint SHA/target head;
- deployed artifact SHA and effective selected worker launch arguments;
- environment/resource-scope/predecessor identities;
- real external reference protocol, request digest and bundle digest;
- exact full component statuses/digests;
- locked activation/result identities;
- cumulative resource observation digest;
- terminal qualification-record and release-index digests;
- independent new-process reopen result showing those same identities current;
- the still-valid R13.3 affected-regression result unless executable source changed.

## Closure gate

P7 may receive PASS only when all of the following hold on the same frozen executable candidate and actual production publication:

1. accepted R13.3 executable/source/regression closure remains valid;
2. B11 executes the pre-existing actual current P5/P6 publication through the production P7 deployment owner and selected KOKKOS/mliappy MACE worker;
3. B12 uses independent real external first-principles/DFT reference data rather than the analytic fixture;
4. all mandatory production components and the one-shot locked result succeed without fallback or selection changes;
5. a genuinely new process reopens and authenticates the complete durable graph;
6. exact production identities/results are recorded; and
7. independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
