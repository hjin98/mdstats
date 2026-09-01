---
kind: implementation-review-evidence
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
review_revision: 13.2
status: no-pass-reopened
reviewed_implementation_commit: cc098c18b39bbfdc65be6d5266fc2582d9bc9e01
reviewed_implementation_tree: 918d7670a6441a5431c95313c452499387b5ec60
review_verdict: NO-PASS
reviewed_date: 2026-08-31
---

# P7 revision 13.2 — independent implementation review evidence

## 1. Review target

This review independently examined P7A3 executable commit
`cc098c18b39bbfdc65be6d5266fc2582d9bc9e01`, tree
`918d7670a6441a5431c95313c452499387b5ec60`, directly against:

1. the frozen V7 parent scientific workplan;
2. accepted/reclosed P1-P6 authorities;
3. P7 revision 13.1 B11 KOKKOS/MACE runtime correction;
4. P7 revision 13 residual source/evidence requirements;
5. still-binding revision-12/revision-11/revision-10/base-P7 requirements.

P7A3 is one executable commit directly above the revision-13.1 authority head. Its changed surface is confined to P7 qualification owners and affected tests. Review did not infer conformance from test names or implementation comments; production owners were inspected independently.

## 2. Review disposition

| Surface | Review disposition |
|---|---|
| R13-B9A claim-scoped stress capability | ACCEPTED source repair |
| R13-B9B fail-closed stress + external reference provenance | ACCEPTED source repair |
| R13-B7 attempt-wide resource evidence / disk headroom | ACCEPTED source repair |
| R13-B13 static executed PBC/cell evidence | ACCEPTED source repair |
| R13-B14 release/resource/terminal referential integrity | ACCEPTED source repair |
| R13.1 selected KOKKOS/mliappy worker mechanics | ACCEPTED in part; preserve worker implementation |
| R13.2-B11A semantic runtime authority | BLOCKING source drift |
| R13.2-B11B actual current-publication target execution | BLOCKING / not closed |
| R13.2-B12 final target-machine real-reference + locked release | BLOCKING / not closed |

Verdict: **NO-PASS / REOPENED**.

## 3. Accepted implementation findings

### 3.1 Stress ownership and provenance

The reviewed source no longer uses one member-0/session-wide stress decision. Stress decisions bind component, claim kind, publication member, exact geometry/cohort, product capability, periodic applicability, component policy and reference availability. Deployment and physical reducers consume member-scoped decisions and fail closed when an applicable channel lacks required evidence. Component input identity incorporates the exact capability set before completed evidence is reused.

External reference stress now crosses an explicit source boundary: raw source representation, units, sign convention, ordering, virial volume semantics where needed, source/canonicalization provenance and resulting canonical tensor are authenticated together and replayed on deserialization. Required-stress geometry identities are frozen in the external request and missing/unprovenanced stress fails closed.

### 3.2 Resource attempt lineage

The reviewed implementation extends immutable resource observations through predecessor digests, carries cumulative elapsed/component/filesystem observations across resume, records locked-test timing, stores stable resource-scope material and selected-device telemetry, and applies configured disk reserve plus owner-bounded incremental headroom before materialization. Public terminal/release resolution traverses and authenticates the resource chain.

### 3.3 Exact deployed geometry evidence

The LAMMPS worker returns the post-build cell and exact three-axis PBC for static execution; the adapter verifies both against the authenticated request and rejects mismatch. Existing exact mixed-axis dynamics behavior is preserved.

### 3.4 Release graph

Public currentness now dereferences the resource observation and its predecessor chain. Release-index resolution dereferences the single terminal qualification record and checks the release index against that authority for the accepted binding/publication/member/executable/spec/environment/plan/locked/predecessor/resource/component identities. Missing/corrupt/substituted objects fail closed.

### 3.5 Selected worker mechanics

The real child worker now applies the requested KOKKOS arguments to the live LAMMPS instance, activates mliappy on that same instance, loads the actual unified MACE artifact, executes the real callback, returns structured runtime evidence only after successful execution, and closes the worker-owned instance without invoking Python finalization. These mechanics are accepted and should be reused.

## 4. Blocking source finding — generic runtime preflight still vetoes semantic execution

Revision 13.1 made the actual selected KOKKOS/MACE product execution authoritative. P7A3 correctly demoted the static `forward_exchange` diagnostic, but retained a broader generic gate:

- `probe_lammps_runtime()` starts a separate generic LAMMPS instance without the selected qualification KOKKOS launch arguments;
- `_require_supported_runtime()` treats generic `supports_deployed_execution` as required;
- `execute_lammps_request()` calls that requirement before spawning the selected semantic worker;
- deployment parity independently gates on the same generic capability before member execution;
- deployment stress capability and stored-capability reuse compare against the generic probe result.

This is materially observable. A generic/default startup or mliappy failure can stop the exact selected `-k on g N -sf kk` worker from ever executing, even though the selected path may be valid. The same generic result can suppress stress requests before the actual worker has established whether it can report the scientifically applicable channel.

That violates the frozen revision-13.1 semantic-owner contract and is a genuine blocking source defect. The precise repair and acceptance are frozen in `P7_REVISION_13_2_IMPLEMENTATION_REVIEW_RUNTIME_GATE_REOPEN_AMENDMENT.md`.

## 5. B11 real-owner gate remains unclosed

The repository contains bounded tests for the new worker lifecycle and callback-failure handling, but the reviewed candidate does not contain accepted evidence that the exact current durable P5 publication decision/member bytes were executed through the final P7 session using the selected target KOKKOS resource contract and then compared for E/F/applicable-stress parity.

The existing real-MACE test surface is not by itself B11 closure because a fixture-produced publication and/or a direct runtime helper cannot substitute for the durable current P5 publication and final deployment-parity owner. B11 is a final real-runtime integration gate, not a unit-test label.

## 6. B12 final release qualification remains unclosed

No new accepted target-machine qualification evidence accompanies P7A3 showing, on the same frozen repaired candidate:

- real authenticated external reference evidence under the repaired stress provenance contract;
- all mandatory nonlocked components succeeding through the selected real MACE runtime;
- target-machine cumulative resource measurements;
- explicit one-shot locked activation after nonlocked closure;
- terminal qualification record + release index + complete descendant graph;
- successful process restart and current close/reopen authentication.

Therefore B12 independently blocks P7 closure even if all bounded source tests are green.

## 7. Test-evidence qualification

This review inspected the committed acceptance tests and production source but did **not** treat their presence as proof of execution. The reviewed GitHub commit has no attached status checks. The review environment was also unable to independently clone/run the repository because its container could not resolve `github.com`. Accordingly:

- committed tests are design/coverage evidence only in this review unless accompanied by an executed result;
- no required real B11/B12 gate is inferred from a skip-capable test;
- final closure must record fresh affected regression/integration results for the repaired candidate plus the actual target-machine B11/B12 evidence required by the authority.

## 8. Final review verdict

P7A3 is a substantial improvement and closes the previously broad R13 source set, but it is not releasable. P7 remains **REOPENED / NO-PASS** for three precise reasons:

1. remove the remaining generic runtime-preflight veto and generic-probe stress/currentness coupling;
2. freeze the resulting executable and execute the exact current P5 publication through the selected KOKKOS/MACE deployment owner with E/F/applicable-stress parity;
3. complete final target-machine real-reference qualification, one-shot locked closure, and durable terminal/release/resource/reference close-reopen on that same candidate.

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked until independent P7 PASS.
