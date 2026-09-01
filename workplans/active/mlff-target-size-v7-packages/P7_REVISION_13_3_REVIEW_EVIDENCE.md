---
kind: implementation-review-evidence
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
review_revision: 13.3
status: no-pass-reopened
reviewed_implementation_commit: f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7
reviewed_implementation_tree: 56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0
post_qualification_documentation_head: 8f6a2e353cdccfaf37fb17660e55bfbc679b501d
review_verdict: NO-PASS
reviewed_date: 2026-08-31
---

# P7 revision 13.3 — independent implementation review evidence

## Review target and evidence

This review examined revision-13.2 executable candidate
`f59e8bdbe1a09f653cdf2e8a82951ece6c1d24c7`, tree
`56eb8089a18b6660d5fc0eadf8fd92ffed45fcd0`. The later branch head
`8f6a2e353cdccfaf37fb17660e55bfbc679b501d` adds only the revision-13.2 implementation/target-qualification evidence record and does not change importable mdstats source.

The review challenged the candidate against the frozen V7 parent, accepted P1-P6 authorities, current R13.2 amendment/authority, preserved R11-R13 repairs, and the supplied revision-13.2 implementation evidence.

## Accepted findings

Revision 13.2 genuinely repairs the previously identified explicit runtime gate:

- `_require_supported_runtime()` no longer rejects a generic probe result;
- `qualify_deployment_parity()` no longer aborts on `probe.supports_deployed_execution`;
- deployment stress capability defaults to requesting the selected runtime channel rather than letting the generic probe redefine scientific applicability;
- stored deployment capability identity no longer directly follows a generic-probe boolean;
- the selected worker carries KOKKOS launch arguments, activates the ML-IAP/MACE path, preserves callback failure as blocking, and retains process isolation/no-Python-finalization behavior;
- focused R13.2 tests explicitly cover generic-probe-unavailable results, selected-worker execution, applicable stress request/comparison, fail-closed missing stress, diagnostic-probe capability-digest stability, and KOKKOS launch arguments.

The supplied implementation evidence reports `pytest -n auto -q tests/test_mlff_p7_*.py` -> `149 passed, 1 skipped`, plus successful target-machine selected KOKKOS/MACE execution and a `RELEASE_QUALIFIED` terminal result on the frozen candidate. Those results are useful evidence and are not rejected merely because they were executed outside this review environment.

Previously accepted R13 stress/provenance, resource lineage, static PBC/cell, release graph, R12 pressure/sign, and R11 publication/currentness/reference/locked repairs remain accepted.

## Blocking finding R13.3-B11C — generic diagnostics still own binding/currentness and remain on the mandatory path

The explicit boolean veto is gone, but the generic/default LAMMPS probe remains acceptance-critical in two independent ways.

First, environment identity still depends on it:

- `capture_environment_fingerprint()` calls `_lammps_facts()`;
- `_lammps_facts()` calls `probe_lammps_runtime()`;
- `probe_lammps_runtime()` starts a generic/default LAMMPS instance in the parent process and activates mliappy there;
- `EnvironmentFingerprint.content_digest` includes `lammps_version` and `lammps_mliap_available`.

Therefore a generic diagnostic outcome change can change the environment digest, full P7 binding, attempt identity, and public currentness even when executable source, publication/product, selected device/resource contract, and selected KOKKOS/MACE semantic runtime are unchanged. That directly violates R13.2 section 4.2(6): a diagnostic generic-probe flip alone must not reinterpret or stale evidence.

Second, mandatory execution still invokes the same generic probe before the semantic child:

- `qualify_deployment_parity()` calls `probe_lammps_runtime()` before member execution to populate a diagnostic payload;
- `execute_lammps_request()` calls `probe_lammps_runtime()` before spawning the isolated child worker.

A returned `available=False` no longer vetoes the worker, but the diagnostic call itself remains in the critical path. A `BaseException`, hang, or native crash in the in-process generic LAMMPS startup can still suppress the selected child execution. The current focused test monkeypatches the probe to **return** an unavailable object; it does not establish that the production path no longer requires/calls the generic probe.

This is implementation nonconformance to the accepted R13.2 design, not a need to reopen qualification science.

## Blocking finding R13.3-B7E — selected accelerator environment identity still reads GPU 0

`_accelerator_facts(device)` accepts the selected device string but queries `torch.cuda.get_device_properties(0)` unconditionally. `EnvironmentFingerprint.content_digest` includes both `device` and `accelerator_model`. On a supported `cuda:1` selection, the binding can therefore describe `device="cuda:1"` while carrying GPU 0's model.

R13 correctly repaired selected-device resource telemetry, but the claim-relevant environment identity is still inconsistent with the selected execution scope. This is a bounded new independent issue in the same identity owner. The reviewed target run used GPU 0, so this does not falsify its observed execution, but it blocks general P7 closure for the supported selected-device contract.

## Evidence closure gap R13.3-B12E

The revision-13.2 evidence record is useful but does not satisfy its own R13.2-P6 exact-recording requirement. It records full qualification-record, release-index, publication, and resource-observation digests, but only shortened component digests and omits the exact external-reference bundle digest/protocol identity, current member checkpoint SHA, deployed artifact SHA, environment digest, resource-scope digest, predecessor-reclosure identity, and exact post-restart current resolver identities.

Because R13.3 requires another executable candidate anyway, the previous target run becomes historical rather than final closure evidence. The next final record should remain concise but preserve the complete exact identity set needed to audit B11/B12 and close/reopen the final graph.

## Verdict

P7 remains **NO-PASS / REOPENED**.

The reopen is narrow:

1. remove generic/default LAMMPS execution/result from mandatory pre-run environment/currentness and selected-worker control flow;
2. make environment accelerator identity query the exact selected CUDA device;
3. rerun focused and complete affected P7 regression on the repaired source;
4. freeze a new executable candidate;
5. rerun the already-demonstrated actual current-publication B11 and final target-machine B12/locked/close-reopen gates on that candidate;
6. record the complete exact identity chain required by the authority.

`P7_REVISION_13_3_IMPLEMENTATION_REVIEW_RUNTIME_IDENTITY_REOPEN_AMENDMENT.md` is the precise repair authority. `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked until independent P7 PASS.
