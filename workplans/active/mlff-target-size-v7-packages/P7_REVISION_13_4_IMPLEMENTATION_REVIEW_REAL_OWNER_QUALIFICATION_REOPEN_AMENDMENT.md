---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.3
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.4
status: reopened
reviewed_implementation_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
reviewed_implementation_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
post_qualification_documentation_head: 6f37e1f2768ed3c2cc185da8c0751a3ae3678597
review_verdict: NO-PASS
amended_date: 2026-09-01
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: accept the R13.3 executable repair; reopen only the final B11/B12 semantic-owner and process-restart evidence because the recorded closure used the bounded analytic test campaign/reference fixture rather than the actual current production publication and real external reference bundle
precedence: revision 13.4 supersedes revision 13.3 only for implementation disposition and the remaining final qualification/evidence boundary; all accepted source repairs and non-conflicting frozen-parent/R13.3/R13.2/R13.1/R13/R12/R11/R10/base-P7 requirements remain binding
---

# P7 revision 13.4 — real-owner qualification evidence reopen amendment

## 1. Verdict and scope

Independent Software Design review of executable candidate
`97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree
`9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, accepts the revision-13.3 executable repair but gives P7 **NO-PASS** because the claimed final B11/B12/P6 evidence does not cross the frozen real production-owner boundaries.

The source repair is accepted:

- mandatory environment/session construction no longer starts `probe_lammps_runtime()`;
- deployment parity and `execute_lammps_request()` no longer call the generic probe before selected execution;
- generic probe state no longer participates in binding/currentness;
- exact `cuda:N` device properties are queried and invalid/out-of-range selection fails closed;
- the accepted R11/R12/R13/R13.2 qualification/runtime/resource/PBC/release repairs remain intact.

Do **not** modify executable source merely to satisfy this amendment. The reviewed candidate remains the frozen executable candidate unless the required real production run exposes an actual executable defect. Documentation-only review commits do not invalidate its executable source identity.

## 2. Blocking finding R13.4-B11D — the recorded B11 publication is a manufactured test campaign

Revision 13.3 requires execution of the exact **current durable P5 publication already owned by the production campaign**. The recorded evidence does not establish that boundary.

The evidence identifies:

- publication member `seed-5`;
- reference protocol `bounded-analytic-reference.v1`;
- a zero-energy tiny MACE execution.

Those identities match the repository's P7 test fixture. `tests/_mlff_qualification_fixture.py` constructs a new temporary selected/P5 campaign through `build_qualified_campaign(...)`; its default production seed is `5`; and its configuration hard-codes `[qualification.reference].protocol = "bounded-analytic-reference.v1"`. With `real_mace_checkpoint=True`, the fixture deliberately publishes a tiny synthetic multihead MACE checkpoint so real export/ML-IAP code can be exercised. That is valid functional/integration evidence, but it is a publication manufactured for the acceptance harness.

R13.3-P4 explicitly forbids manufacturing a separate publication solely to close B11. Therefore the recorded target execution proves that the corrected KOKKOS/mliappy owner can run a real MACE artifact, but it does **not** close the final current-production-publication gate.

### Required end state

Run B11 against the operator's existing production campaign/workspace whose P1-P6 state is already current and whose P5 final publication exists independently of this qualification attempt.

Required production chain:

```text
pre-existing current campaign
 -> current authenticated P5/P6 publication resolver
 -> exact already-published member checkpoint bytes + SHA
 -> production P7 session (no test fixture/harness publication creation)
 -> real mdstats target-head exporter
 -> real LAMMPS_MLIAP_MACE artifact
 -> selected target resource scope
 -> selected KOKKOS/mliappy child worker
 -> actual callback
 -> production deployment-parity reducer over E/F/applicable stress + exact cell/PBC
```

Forbidden substitutions for final B11 closure:

- `tests._mlff_qualification_fixture` or `tests._mlff_post_selection_fixture` campaign builders;
- `tmp_path`/new temporary P1-P5 campaign creation solely for B11;
- `QualificationHarness`, `PostSelectionHarness`, analytic inference/deployed/dynamics seams, or synthetic P5 trainer output as the publication under acceptance;
- a direct `deployed_static_evaluation()` smoke without the production publication resolver and deployment-parity owner.

Before execution, record the current publication digest/member ID/checkpoint SHA/target head from the production resolver. After execution, the B11 component evidence must bind those same identities and the exact deployment artifact SHA/effective selected launch arguments.

## 3. Blocking finding R13.4-B12F — the recorded B12 reference bundle is analytic test evidence, not real external DFT evidence

The frozen base P7 contract is explicit:

> bounded deterministic synthetic/analytic references are valid below the external-reference boundary for functional tests; **production scientific qualification uses real external DFT references generated under the frozen request/protocol identity**.

The revision-13.3 evidence instead records:

```text
Reference Request Protocol Identity: bounded-analytic-reference.v1
```

The test fixture's `supply_analytic_reference_bundle()` constructs those observations from `AnalyticPairPotential`/harness evaluation and writes the bundle itself. That is exactly the allowed functional-test seam and exactly the forbidden substitute for final production scientific qualification.

Thus the recorded physical-PES/relaxation/dynamics `RELEASE_QUALIFIED` result is valuable assembled functional evidence but cannot close B12.

### Required end state

On the same frozen executable and actual current production publication used for B11:

1. run the production qualification owner until it publishes/fixes the exact external reference request and reaches `waiting_for_reference` where required;
2. execute or obtain the requested external first-principles/DFT calculations independently of the candidate MLFF under an explicit real reference protocol identity;
3. import the resulting bundle through the production reference authentication owner;
4. for every applicable stress geometry, preserve the authenticated raw source representation, units, sign, ordering, volume semantics where relevant, source provenance, and canonicalization record already required by R13;
5. run the mandatory physical-PES, relaxation, dynamics, calibration-if-applicable, and then explicit one-shot locked components through the production P7 owner;
6. require the final terminal verdict to be `RELEASE_QUALIFIED` without fallback, member substitution, threshold changes, or analytic fixture data.

Forbidden final-reference protocols/sources include `bounded-analytic-reference.v1`, `supply_analytic_reference_bundle()`, `AnalyticPairPotential`, or any reference numerically generated from the candidate/fixture harness rather than the independent external reference method.

If the real external calculations have not yet been produced, the truthful P7 state is `waiting_for_reference`; that is not a software failure but it is not P7 PASS.

## 4. Blocking finding R13.4-B12G — close/reopen evidence is same-process reconstruction, not a process restart

R13.3-P6 requires the terminal/release/resource/reference graph to reauthenticate **after process restart**. The recorded evidence calls its result a "simulated process restart" and describes rebuilding a fresh `QualificationSession` in the same Python process. The committed R13.3 acceptance test likewise closes one session and opens another in-process.

That does not prove the required persistence boundary. Process-global caches, module state, open descriptors, or other interpreter-owned state could still mask a reopen defect.

### Required end state

After successful real B11/B12/locked closure:

1. end the Python process that performed qualification;
2. start a genuinely new Python process/CLI invocation with no inherited in-memory P7 session/store/cache state;
3. reopen the same production campaign/store through the public current resolver path;
4. resolve the terminal qualification record and release evidence index;
5. verify the exact same binding/publication/reference/component/resource/locked/terminal/index digests and `RELEASE_QUALIFIED` verdict.

A subprocess, a second shell invocation of the production CLI/status path, or another genuinely new interpreter is sufficient. Constructing a second session object in the original interpreter is not.

## 5. Regression/evidence disposition

The reported focused R13.3 checks and `pytest -n auto -q tests/test_mlff_p7_*.py` result (`155 passed, 1 skipped`) are accepted as functional source evidence for the R13.3 repair. The remaining skip-capable real-runtime test does not itself close B11; final B11 is owned by the production campaign execution above.

Because no executable defect is reopened, do not rerun the entire affected suite solely because this review created documentation. Reuse the R13.3 regression result unless the real production qualification exposes a source defect or executable source changes.

## 6. Binding completion sequence

```text
R13.4-P1  keep executable candidate 97fa48fc... / tree 9e4be0fc... frozen
R13.4-P2  resolve and record the pre-existing actual current P5/P6 production publication
R13.4-P3  run B11 through the production P7 deployment-parity owner and selected KOKKOS/mliappy worker
R13.4-P4  freeze/import real external DFT reference evidence under the production reference request/protocol
R13.4-P5  complete production nonlocked qualification + explicit one-shot locked result on the same candidate/publication
R13.4-P6  terminate the qualifying interpreter, reopen in a new process, and reauthenticate the complete current graph
R13.4-P7  record exact production identities/results and request independent Software Design closure review
```

No test-fixture-generated publication or analytic reference bundle can satisfy P2-P6. No executable change is permitted during P2-P6. If the real run exposes a source defect, stop, repair it, rerun affected regression/integration, freeze a new executable candidate, and repeat every real gate plausibly affected by that edit.

## 7. Final evidence record

One concise final evidence record is sufficient. It must identify the actual production run, not merely a test fixture, and include:

- executable commit/tree/source digest/package version;
- actual current publication digest, member ID/run identity/checkpoint SHA/target head;
- deployment artifact SHA and effective selected worker launch arguments;
- environment/resource-scope/predecessor identities;
- real external reference protocol, request digest and bundle digest;
- exact full component statuses/digests;
- locked activation/result identities;
- cumulative resource observation digest;
- terminal qualification record and release-index digests;
- the independent new-process reopen result with the same current identities;
- the already accepted R13.3 affected-regression result, unless executable source changed.

## 8. Closure gate

P7 may PASS only when:

1. the accepted R13.3 executable repair remains unchanged and source/regression evidence remains valid;
2. B11 executes the actual pre-existing current P5 production publication through the real production P7 owner;
3. B12 uses real independent external DFT/reference data, not the bounded analytic fixture;
4. all required production components and one-shot locked result succeed on the same frozen candidate/publication;
5. a genuinely new process reopens and reauthenticates the complete durable release graph;
6. exact production identities are recorded; and
7. independent Software Design review finds no remaining genuine blocker.

Until then P7 remains **REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
