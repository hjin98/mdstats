---
kind: implementation-review-evidence
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
review_revision: 13.4
status: no-pass-reopened
reviewed_implementation_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
reviewed_implementation_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
post_qualification_documentation_head: 6f37e1f2768ed3c2cc185da8c0751a3ae3678597
review_verdict: NO-PASS
reviewed_date: 2026-09-01
---

# P7 revision 13.4 — independent implementation review evidence

## Review target and disposition

Independent review examined the R13.3 executable candidate
`97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree
`9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, against the frozen parent, accepted P1-P6 authorities, R13.3, and all preserved P7 obligations.

Disposition:

| Surface | Result |
|---|---|
| R13.3-B11C generic-runtime identity/control-flow decoupling | **ACCEPTED** |
| R13.3-B7E exact selected CUDA-device environment identity | **ACCEPTED** |
| preserved R11/R12/R13/R13.2 source repairs | **ACCEPTED / no regression found by source review** |
| reported focused + affected P7 regression | **ACCEPTED functional evidence** (`155 passed, 1 skipped`) |
| R13.3-P4 final B11 current-production publication gate | **NOT CLOSED** — recorded publication is the acceptance fixture campaign |
| R13.3-P5 final B12 real-reference production qualification | **NOT CLOSED** — recorded reference protocol is the bounded analytic test fixture |
| R13.3-P6 process-restart reauthentication | **NOT CLOSED** — evidence is same-process fresh-session reconstruction |

Verdict: **NO-PASS / REOPENED**, evidence-boundary only.

## Accepted source repair

The candidate removes mandatory generic probe execution from environment/session construction, deployment parity and `execute_lammps_request()`. `EnvironmentFingerprint` is built from non-executing installation/device facts and excludes the old volatile ML-IAP availability bit from currentness identity. The exact selected `cuda:N` device is parsed and queried; invalid/out-of-range selection fails closed. The selected isolated KOKKOS/mliappy MACE worker remains the semantic runtime owner.

No new executable blocker was found in the R13.3 delta. The candidate can remain frozen for final qualification unless the real production run exposes a source defect.

## Blocking evidence finding 1 — B11 used the test publication fixture

The committed implementation evidence identifies publication member `seed-5`, protocol `bounded-analytic-reference.v1`, and a tiny real MACE execution. Those identities align with `tests/_mlff_qualification_fixture.py` and `tests/_mlff_post_selection_fixture.py`:

- the P7 fixture's default production seed is 5;
- `build_qualified_campaign()` creates a new temporary campaign specifically for tests;
- `real_mace_checkpoint=True` writes a deliberately tiny synthetic multihead MACE model so real export/ML-IAP owners can be exercised;
- the fixture configuration hard-codes `bounded-analytic-reference.v1`.

This is legitimate integration coverage below/around the production owner, but R13.3-P4 explicitly requires the pre-existing actual current durable P5/P6 production publication and forbids a newly manufactured fixture publication as final B11 evidence.

## Blocking evidence finding 2 — B12 used analytic references

The base P7 external-reference contract explicitly distinguishes the two uses: bounded deterministic synthetic/analytic references are valid for functional tests, whereas production scientific qualification requires real external DFT/reference data generated under the frozen request/protocol identity.

The R13.3 evidence records `Reference Request Protocol Identity: bounded-analytic-reference.v1`. The fixture's `supply_analytic_reference_bundle()` generates those energies/forces/stresses directly from `AnalyticPairPotential`/harness evaluation and writes the reference bundle. Therefore the recorded physical/relaxation/dynamics qualification is functional integration evidence, not final production scientific evidence.

B12 remains open until the actual production reference request is fulfilled by independent real external first-principles/DFT results and the production P7 owner reaches `RELEASE_QUALIFIED` on those references.

## Blocking evidence finding 3 — restart proof is not a process restart

R13.3-P6 requires close/reopen after process restart. The implementation evidence itself calls the check a "simulated process restart" and says it re-resolved through a fresh `QualificationSession` context. The committed acceptance test likewise closes one store/session and opens another within the same Python interpreter.

This cannot close a persistence/restart semantic-owner claim because process-global/module/cache state remains alive. Final closure requires termination of the qualifying interpreter followed by a genuinely new process/CLI invocation that reopens the same production store and resolves the identical terminal/release graph.

## Regression evidence

The reported `pytest -n auto -q tests/test_mlff_p7_*.py` result is `155 passed, 1 skipped`. The skip-capable R12 B11 integration explicitly represents unavailable runtime as a skip and cannot itself substitute for the final production B11 gate. Because R13.4 reopens no executable source, the R13.3 regression result remains reusable; documentation-only review changes do not require rerunning it.

## Final review conclusion

P7 is source-ready but not release-qualified. Keep candidate `97fa48fc...` frozen and rerun only the real semantic-owner gates:

1. resolve the already-existing actual current P5/P6 publication from the production campaign;
2. run real B11 through production P7 deployment parity and the selected KOKKOS/mliappy MACE worker;
3. fulfil the actual production reference request with independent external DFT/reference evidence, then complete B12 and one-shot locked closure;
4. terminate the process and reauthenticate the same terminal/release/resource/reference graph in a new process;
5. record exact production identities and request independent closure review.

The successor storage reset remains blocked until P7 receives independent PASS.
