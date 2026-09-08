---
kind: independent-design-review-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision_reviewed: 11
review_revision: 12
protocol_version: 5.8.0
reviewed_implementation_commit: d24c16cecfd25f2dfcd83b10e0850981d5b64318
reviewed_implementation_tree: 2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e
post_implementation_documentation_head: 4f8b624acedf23c0cf15a59ba5d7994336dc9755
verdict: NO-PASS
recorded_date: 2026-08-31
---

# P7 revision 12 — independent implementation review evidence

This record preserves the independent review of the revision-11 repair implementation. The governing repair authority is `P7_REVISION_12_AUTHORITY.md` composed with `P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md` and the frozen parent.

## Reviewed candidate

Executable source reviewed: `d24c16cecfd25f2dfcd83b10e0850981d5b64318` / tree `2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e`.

The later branch commit `4f8b624acedf23c0cf15a59ba5d7994336dc9755` regenerates PDF documentation only and therefore does not alter the source-review verdict.

## Positive closure evidence

Revision 11 materially improved the implementation. Source review accepts the following repaired boundaries, subject to ordinary regression after remaining fixes:

- P5 now owns and durably persists the final-production publication decision for both `all_qualified_final_seeds` and `single_best_final_seed`; P7 contains no cross-seed ranking owner.
- The canonical P5 target head is now part of publication/member/deployment identity and is mandatory at both the real mdstats exporter and real MACE ML-IAP builder.
- Public P7 currentness resolution validates the exact current qualification binding rather than treating the P4 selected-binding pointer as scientific authority.
- Reference-dependent component identity now binds exact authenticated reference-bundle content and has appropriately scoped invalidation.
- Dynamics starts from authenticated reference-relaxed coordinates and implements the required NVT/NVE/safety/protected-topology, displacement, bond and angle diagnostic vocabulary.
- Locked activation is crash-resumable after disclosure while disclosure history remains permanently one-shot.
- CPU/RAM/GPU case scheduling and nested thread limits use accepted resource owners, and deployed artifacts are create-once/re-authenticated across restart/concurrency.
- Placeholder reference protocol identities fail closed.
- Qualification topology/minimum-image operations have been reconciled to canonical `mdstats.analysis` ownership where an equivalent owner exists.
- The implementation evidence reports broad revision-11/revision-10/P5/P6 affected acceptance passes. Those are positive functional evidence, not substitutes for the remaining release gates.

## Residual and newly surfaced blockers

### 1. R12-B9 — incorrect LAMMPS stress conversion and unresolved applicability authority

`qualification/_lammps_worker.py` correctly comments that LAMMPS `units metal` thermo pressure is in bar, then reads `pxx/pyy/pzz/pxy/pxz/pyz`, but passes those numeric pressure values to the canonical converter as `units="gpa"`. This introduces a factor-10,000 unit error.

The same adapter defaults the source-to-canonical sign to `+1`, even though the repository canonical label contract is ASE/MACE Cauchy stress while LAMMPS thermo values are pressure. The pressure-to-tensile-stress sign is a source-convention fact and must not be an arbitrary operator default.

The revision-11 stress tests validate the generic converter but do not execute the production LAMMPS pressure adapter with known bar/shear/sign values, so they do not catch this defect.

Finally, `stress_applicable` remains primarily a qualification configuration boolean. Revision 11 required applicability to be resolved before execution from accepted product/training/reference/runtime capability plus policy. A user-switch alone can suppress an otherwise available stress channel and is therefore not sufficient scientific authority.

### 2. R12-B13 — exact periodicity is lost at the deployed runtime boundary

Deployed static and dynamics requests collapse the exact ASE three-axis PBC vector with `all(...)` into one scalar `periodic`. The LAMMPS worker consequently emits only `boundary p p p` or `boundary f f f`, and its minimum-image safety path also consumes a scalar periodic flag.

A legitimate configuration such as `[True, True, False]` is therefore executed as `[False, False, False]`, silently changing the physical system. P7 does not prohibit mixed periodicity and requires exact geometry/runtime identity and periodic displacement handling, so this is a blocking semantic defect.

### 3. R12-B7 — release resource evidence is incomplete

Revision-11 scheduling/resource-owner integration is substantially correct, but the release evidence records only a stable resource-scope identity. It does not record the disk availability/usage required by the revision-11 disk-admission fallback, nor the measured timing/resource observations required by revision 10 for target-machine qualification.

The repository already has an execution disk reserve (`minimum_free_disk_gib`) and owner-local disk-reserve logic in existing training-data materialization code. P7 should reuse that policy/safety concept without implementing the post-P7 storage inventory/admission subsystem.

### 4. R12-B11 — actual published MACE product execution remains unavailable/blocking

The repaired tests now exercise a real multihead MACE model through the real mdstats target-head exporter and real `LAMMPS_MLIAP_MACE` artifact builder. This closes the prior test-only proxy overstatement.

However, the installed development-host LAMMPS ML-IAP Python data interface lacks the message-passing `forward_exchange` capability needed by MACE. The actual MACE-in-LAMMPS execution test therefore truthfully skips as `UNAVAILABLE/BLOCKING`. Functional owner construction is positive evidence, but it is not the required real publication runtime proof.

### 5. R12-B12 — final target-machine / real-reference qualification is absent

The revision-11 implementation evidence explicitly states that final target-machine qualification with an exact frozen publication, real external reference evidence, actual supported MACE target-head deployment runtime, and one-shot locked closure has not been run. Revision 10/11 make that a mandatory P7 independent-PASS gate.

## Verdict rationale

P7 is **NO-PASS / REOPENED**. R12-B9 and R12-B13 are source-level scientific/runtime correctness defects. R12-B11 and R12-B12 are mandatory release-evidence gates that remain genuinely unavailable/unexecuted. R12-B7 is a binding target-machine resource-evidence obligation needed before the final qualification can be accepted.

Revision 12 deliberately preserves the repaired B1-B6/B8/B10 architecture and limits new source work to the residual surfaces above. The post-P7 storage reset remains blocked.