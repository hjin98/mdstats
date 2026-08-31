---
kind: independent-design-review-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision_reviewed: 12
review_revision: 13
protocol_version: 5.8.0
reviewed_implementation_commit: 89c6d9bf5c21236436342043e5afca194b3da4e7
reviewed_implementation_tree: 7d6ebd9ecf6423de0a6dc01448b932a760eda383
post_implementation_documentation_head: d10c643349a646b361357fc3a09372b4fb3306c6
verdict: NO-PASS
recorded_date: 2026-08-31
---

# P7 revision 13 — independent implementation review evidence

This record preserves the independent Software Design review of the revision-12 repair candidate. The governing repair authority is `P7_REVISION_13_AUTHORITY.md` composed with `P7_REVISION_13_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and the frozen parent.

## Reviewed candidate

Executable source reviewed: `89c6d9bf5c21236436342043e5afca194b3da4e7` / tree `7d6ebd9ecf6423de0a6dc01448b932a760eda383`.

The later branch head `d10c643349a646b361357fc3a09372b4fb3306c6` regenerates affected PDFs only and therefore does not alter the executable review verdict.

The implementation evidence reports a focused P7 suite of `115 passed, 2 skipped`, an affected MLFF regression of `58 failed, 678 passed, 4 skipped` with zero new failing node IDs versus its stated compatible baseline, and an earlier full-repository run with zero new failing/error node IDs. Those results were reviewed as supplied evidence; this independent review did **not** rerun them because the review container could not resolve `github.com` to clone the repository. No unexecuted check is treated as PASS.

## Positive findings

Revision 12 materially closes several prior defects:

- LAMMPS `units metal` thermo pressure is now converted from bar, not GPa, and the source-specific adapter fixes the positive-compression -> canonical positive-tension sign.
- Named stress components are explicitly mapped, including shear, before canonicalization.
- The static/dynamics request path carries exact three-axis PBC; the LAMMPS boundary command and worker minimum-distance reduction honor axes individually.
- Dynamics case identity and raw dynamics samples carry exact PBC/cell.
- A typed immutable resource-observation record is stored and referenced by terminal/release objects.
- The real-owner acceptance test now drives an actual frozen P5 publication member through the real mdstats target-head exporter and real `LAMMPS_MLIAP_MACE` builder.
- Prior revision-11 publication/currentness/reference/dynamics/locked/resource-owner/canonical-analysis repairs remain structurally present.

These repairs should be preserved.

## Blocking findings

### R13-B9A — stress capability scope/ownership remains wrong

`QualificationSession.stress_capability()` resolves one cached decision from `publication.members[0]`, always reads `COMPONENT_DEPLOYMENT_PARITY` policy, derives periodicity from the first caller's atom cohort, and then returns that same cached decision to later callers including physical qualification.

Consequences:

- one committee member can incorrectly define stress capability for all members;
- first-call cohort periodicity can suppress or enable stress for a different physical cohort;
- `[qualification.physical].stress_required` and physical inapplicability policy are bypassed by deployment policy;
- a capability change is not part of the actual component-input digest used by `completed_component()`, despite tests asserting only that the capability object's own digest changes.

### R13-B9B — applicable stress still has fail-open paths and reference provenance is unauthenticated

Deployment parity counts unavailable stress, but unless `stress_required=true` it can still pass an otherwise applicable trained stress channel with no deployed stress comparison. Physical qualification similarly treats reference comparability as applicability and can skip or tolerate missing reference stress under the default policy.

The external reference boundary stores `stress_ev_per_angstrom3` as if already canonical. It does not authenticate source stress units, pressure/stress sign, Voigt/tensor order, virial volume source, or canonicalization recipe. Thus a wrong-unit/wrong-sign external result can be content-authenticated yet scientifically misinterpreted.

The revision-12 test named `missing_required_reference_stress_fails_closed` constructs a capability object and checks flags; it does not execute the production reducer or prove a required missing reference/runtime stress cannot PASS.

### R13-B7 — resource evidence is not yet complete attempt evidence

Every rebuilt `QualificationSession` starts a fresh `ResourceObservationRecorder`; the current terminal record points to only the latest invocation's observation. Earlier waiting/resume/nonlocked measurements remain immutable but are neither accumulated nor linked into the final complete-attempt observation.

Locked-test execution is not recorded as a component timing. The observation stores a resource-scope digest but not the stable selected CPU/GPU/thread topology material needed to interpret it. CUDA telemetry queries device 0 rather than the selected device. Disk safety checks `free >= reserve` but does not require reserve plus the bounded amount about to be materialized, so it can start work that immediately consumes the promised reserve.

### R13-B13 — static PBC execution is requested but not observed

The static worker result omits executed `cell_angstrom` and `pbc`; `DeployedEvaluation` and deployment evidence therefore cannot authenticate that the runtime actually executed the requested mixed boundary. Dynamics raw observations do carry those fields. Revision 12 required them in every deployed static/dynamics observation, so this remains a bounded implementation nonconformance.

### R13-B14 — release evidence graph is not fully reauthenticated

Terminal records and release indexes carry `resource_observation_digest`, but public currentness resolution does not dereference the resource observation or validate its binding/attempt/resource-scope identity. A missing or corrupt resource object can therefore leave a terminal/release pointer exposed as current.

When resolving a `ReleaseEvidenceIndex`, the resolver also does not dereference `qualification_record_digest` and prove the indexed single terminal verdict owner exists, is current, and agrees with the index's verdict/locked/resource/predecessor identities. The index can therefore outlive or disagree with the object it is supposed only to index.

### R12-B11 — real MACE publication execution remains unavailable/blocking

The candidate correctly refuses to call product construction a runtime PASS. Its real publication execution test skips when the installed ML-IAP data interface lacks `forward_exchange`. This is truthful unavailability, but the frozen real-owner gate remains unexecuted.

### R12-B12 — final target-machine qualification remains unexecuted

The implementation evidence explicitly states that final target-machine qualification with real external reference evidence, supported real MACE deployment execution, and one-shot locked closure has not run. This is a mandatory P7 PASS gate.

## Verdict rationale

P7 is **NO-PASS / REOPENED**. The original R12 bar/sign bug and main PBC request/execution defect are repaired, but R13-B9A/B9B can still suppress an applicable trained stress claim, R13-B7/B14 leave final resource/release evidence incompletely closed across restart and public exposure, and R13-B13 leaves static boundary execution unauthenticated. Independently, R12-B11 and R12-B12 remain mandatory unavailable/unexecuted gates.

Revision 13 preserves all unrelated accepted repairs and limits source rework to these surfaces. `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
