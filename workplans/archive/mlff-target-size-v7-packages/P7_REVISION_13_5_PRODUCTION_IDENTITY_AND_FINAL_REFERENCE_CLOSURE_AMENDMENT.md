---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.4
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.5
status: reopened
reviewed_evidence_head: cdb6a3c5ac90c585ac3992fdc546908dd1467919
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
frozen_source_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
review_verdict: NO-PASS
amended_date: 2026-09-01
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: preserve all accepted source repairs; accept the demonstrated fresh-process reopen mechanism; require truthful executable/runtime identity, actual pre-existing production publication lineage, real external DFT completion, one-shot locked closure, and final RELEASE_QUALIFIED reauthentication
precedence: revision 13.5 supersedes revision 13.4 only for the latest evidence disposition and remaining closure instructions; all accepted executable/scientific/runtime/resource/currentness contracts remain binding
---

# P7 revision 13.5 — production identity and final-reference closure amendment

## 1. Review disposition

The R13.4 evidence at `cdb6a3c5ac90c585ac3992fdc546908dd1467919` does **not** close P7.

No new executable defect is established. Keep executable candidate `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6` frozen unless a genuine production run exposes a source defect.

The new evidence does establish one previously open boundary: a genuinely new Python process can reopen and authenticate the durable qualification graph. Preserve that mechanism. It presently reauthenticates an intermediate `WAITING_FOR_REFERENCE` graph, so it must be repeated after final release qualification.

The remaining blockers are evidence/production-lineage blockers, not another implementation redesign.

## 2. R13.5-B11E — claimed production publication lineage is still not established

The R13.4 evidence calls its campaign the production campaign, but its identifying facts strongly match the bounded acceptance fixture rather than the operator's established production campaign:

- it reports selected target size `N=4`;
- the repository's P4/P5 acceptance fixture config uses target-size powers 1..3, i.e. candidate sizes `{2,4,8}`;
- it reports publication member `seed-5` and checkpoint SHA `44297de809ab54e4604524ceb5b463ea21ca1336a2ab1e88fff062aba7d8cabb`;
- that checkpoint SHA is exactly the same SHA recorded in the already-rejected R13.3 tiny-MACE fixture evidence.

Renaming a fixture-created campaign "production" does not cross the semantic owner boundary. Final B11 must consume the operator's pre-existing campaign/workspace whose P1-P6 state and P5 publication existed independently of this P7 qualification attempt.

### Required end state

Before any B11 execution, resolve the campaign using the same operator config/workspace used for the actual target-size/CV/final-production workflow. Do not create or regenerate P1-P5 state for qualification.

Record from production owners, before deployment execution:

- campaign ID/generation and selected-binding digest;
- actual `N_selected` and exact `T_selected` identity;
- post-selection CV acceptance identity;
- final-production plan/reclosure identity;
- current P5 publication digest;
- publication member ID/run identity/checkpoint locator/checkpoint SHA/target head.

Then execute through the production P7 owner:

```text
existing production campaign
 -> current P5/P6 publication resolver
 -> exact existing published checkpoint bytes
 -> production QualificationSession
 -> default_deployment_exporter
 -> default_mliap_artifact_builder
 -> deployment-parity owner
 -> selected KOKKOS/mliappy child worker
 -> actual MACE callback
 -> E/F/applicable-stress parity + exact PBC/cell
```

Forbidden for final B11: test campaign builders, `tmp_path` campaign creation, `QualificationHarness`, `PostSelectionHarness`, synthetic training seams, or a direct runtime smoke that bypasses the production publication/deployment-parity owner.

If the operator's actual campaign has not yet reached a current P5 publication, B11 remains unavailable; do not manufacture one solely for qualification.

## 3. R13.5-B11F — executable/package identity must be proven from the running process

The R13.4 evidence is internally inconsistent:

- it claims frozen commit `97fa48fc...`, tree `9e4be0fc...`, and source digest `7772ad5f...`;
- but it records package version `0.20.198a0`;
- the source at commit `97fa48fc...` contains `mdstats/_version.py` with `__version__ = "0.20.242a0"`;
- the prior R13.3 evidence for the same commit/source digest also records `0.20.242a0`.

This may be only an evidence transcription error or a stale installed-distribution metadata issue, but final acceptance cannot guess. The actual qualifying interpreter must prove which mdstats source it imports.

### Required preflight evidence

From the exact Python interpreter that will run B11/B12, record the output of the production identity owner (or equivalent direct inspection) showing:

- `mdstats.__file__` / package root;
- `mdstats._version.__version__`;
- `resolve_executable_candidate_identity().package_version`;
- `resolve_executable_candidate_identity().source_tree_digest`;
- Git commit/tree audit metadata when available;
- environment/package metadata if separately recorded.

For this frozen candidate the executable identity must resolve to:

- package version `0.20.242a0`;
- source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`;
- Git commit/tree `97fa48fc...` / `9e4be0fc...` when the checkout is available.

If import path/source digest differs, stop: the wrong installation/checkout is executing and no B11/B12 evidence from that process can close this candidate. Do not edit source to hide the mismatch; fix invocation/environment selection.

If only distribution metadata differs while imported source identity is exact, record both facts accurately and do not substitute the stale distribution version for `ExecutableCandidateIdentity.package_version`.

## 4. R13.5-B12H — real external reference qualification is still intentionally incomplete

The R13.4 evidence correctly records:

- production reference protocol `dft-pbe-ts-reference.v1`;
- reference request digest `08e2c389ec348d66d581e8bf3ccdf20585bc1917453ad508680ea58a8b19ebcf`;
- real external calculations **not yet produced/imported**;
- `physical_pes`, `relaxation`, and `dynamics` as `waiting_for_reference`;
- locked test unopened;
- terminal state `WAITING_FOR_REFERENCE`.

That is truthful and correct intermediate behavior. It is explicitly not P7 PASS under R13.4.

### Required end state

Use the exact frozen production reference request. Obtain independent external first-principles/DFT results under `dft-pbe-ts-reference.v1` (or the already-frozen actual production protocol if the true production campaign resolves a different identity). Import/authenticate the bundle through the production reference owner.

For every requested geometry require exact geometry identity and authenticated E/F; where stress is applicable, preserve source representation, units, sign, component ordering, volume/virial semantics when applicable, provenance, and canonicalization record.

Then run the production qualification owner to completion:

- deployment parity remains passed/current for the exact production publication;
- physical PES passes;
- relaxation passes;
- dynamics passes;
- calibration passes or is explicitly `not_applicable` only under its frozen policy;
- explicitly activate the one-shot locked test after all required prelocked evidence is ready;
- execute the locked result exactly once;
- terminal verdict must be `RELEASE_QUALIFIED`.

`WAITING_FOR_REFERENCE`, unopened locked state, synthetic/analytic reference data, or a hand-written terminal record cannot satisfy this gate.

## 5. R13.5-B12I — repeat fresh-process reauthentication after final closure

The R13.4 evidence does satisfy the process-separation mechanism: the qualifying process exits and a new interpreter reopens the durable graph. Accept this mechanism.

However, it currently proves only that the **waiting** graph reopens. After real DFT import, final component completion, and locked closure:

1. terminate the process that reached `RELEASE_QUALIFIED`;
2. launch a genuinely new interpreter/CLI invocation;
3. reopen the exact same production campaign/store through public current resolvers;
4. require the same executable/binding/publication/reference/component/resource/locked/terminal/release identities;
5. require terminal verdict `RELEASE_QUALIFIED` and a current release index.

## 6. Regression and executable-change policy

The R13.3/R13.4 affected regression result `155 passed, 1 skipped` remains accepted because no executable source changed after candidate freeze. Do not rerun it merely for R13.5 documentation.

If and only if real production qualification exposes a genuine executable defect:

- stop qualification;
- route the source defect explicitly;
- repair it under Software Implementation;
- rerun focused and complete affected P7 regression/integration;
- freeze a new executable candidate;
- repeat each real production gate whose claim could be affected by the edit.

## 7. Binding completion sequence

```text
R13.5-P1  keep 97fa48fc... executable frozen
R13.5-P2  prove qualifying interpreter imports exact candidate identity/version/source
R13.5-P3  resolve the operator's pre-existing actual production P1-P6/P5 publication
R13.5-P4  execute production B11 through publication -> deployment parity -> selected KOKKOS/MACE owner
R13.5-P5  obtain/import independent real DFT bundle for exact frozen production reference request
R13.5-P6  finish production nonlocked components, explicitly activate/execute one-shot locked test, reach RELEASE_QUALIFIED
R13.5-P7  terminate process and reauthenticate the final complete graph in a new process
R13.5-P8  record exact identities/results and request independent Software Design closure review
```

## 8. Final closure evidence

One concise final record must contain the actual production identities, not fixture approximations:

- executable import path, package version, commit/tree/source digest;
- actual production campaign/generation/selected binding and `N_selected` identity;
- CV/final-production/reclosure identities;
- actual production publication/member/checkpoint/target-head identities;
- deployment artifact and ML-IAP artifact SHAs plus selected KOKKOS launch evidence;
- environment/resource-scope identities;
- real DFT protocol/request/bundle identities;
- exact full component statuses/digests;
- locked activation/result identities;
- cumulative resource observation digest;
- terminal qualification-record/release-index digests;
- fresh-process final reauthentication result with `RELEASE_QUALIFIED`;
- still-valid affected-regression result.

## 9. Closure gate

P7 may PASS only when all of the following hold simultaneously:

1. the exact frozen executable candidate is proven to be the code actually running;
2. B11 consumes the operator's pre-existing actual production P5/P6 publication rather than any acceptance fixture;
3. B12 consumes independent real external DFT/reference data for the exact production request;
4. all mandatory components plus the explicit one-shot locked result succeed on that same candidate/publication;
5. terminal verdict is `RELEASE_QUALIFIED`;
6. a genuinely new process reauthenticates the same complete release graph as current;
7. exact production identities are recorded without internal contradictions; and
8. independent Software Design review finds no remaining blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
