---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 12
protocol_version: 5.8.0
reviewed_revision_11_commit: d24c16cecfd25f2dfcd83b10e0850981d5b64318
reviewed_revision_11_tree: 2a01d92197ae4663fc7fc789ddb0aa21a97cdb4e
repair_start_commit: 23a7a9c
p7_executable_source_tree_digest: dbdd7ee6ce4035db26ef2f4b5cbf8563174c3c012147e2532d99e47eb5e6dcfb
status: implementation-complete-pending-design-review
recorded_date: 2026-08-31
---

# P7 revision 12 — residual repair implementation evidence

Repair authority: `P7_REVISION_12_AUTHORITY.md` composed with
`P7_REVISION_12_FINAL_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md`, the still
binding revision-11 and revision-10 amendments, the base P7 workplan, and the
frozen parent. Revision 12 is narrow by construction: the revision-11 B1-B6,
B8, and B10 surfaces are preserved, not redesigned.

`P7_REVISION_11_IMPLEMENTATION_EVIDENCE.md` remains historical evidence for the
reviewed revision-11 candidate.

## 1. Disposition

| ID | Disposition |
|---|---|
| R12-B9 | repaired — canonical LAMMPS pressure adapter and capability decision |
| R12-B13 | repaired — exact per-axis periodicity end to end |
| R12-B7 | repaired — measured resource observation and disk-reserve safety |
| R12-B11 | **partially unavailable/blocking** — see section 3 |
| R12-B12 | **not run** — see section 3 |

## 2. Repairs

### R12-B9 — the stress boundary

The defect was real and had two independent halves. LAMMPS `units metal` thermo
pressure is in **bar**, and the worker passed those numbers to the generic
converter as `units="gpa"` — a factor-10,000 error before any tolerance applied.
Separately, pressure is positive in compression while the repository's canonical
ASE/MACE label contract (`mace_export.stress_sign = "ase_tensile_positive"`) is
positive in tension, and the adapter defaulted that conversion to `+1`.

Both are facts about LAMMPS rather than choices, so
`canonical_stress_from_lammps_metal_pressure` now owns them and is deliberately
**not** parameterized by units or sign. `stress_sign` and `stress_voigt_order`
were removed from the qualification specification entirely: making a source's
tensor ordering or sign convention operator configuration is how an ordering
error becomes an accepted "policy".

`stress_applicable` is gone as an operator boolean. `StressCapabilityDecision`
resolves applicability before any component executes, from the accepted training
objective's stress weight, reference stress labels, whether the authenticated
model returns a stress tensor, periodicity, and runtime support. Policy composes
in one direction only — it may require stress, and it may record a justified
inapplicability reason for audit, but it cannot relabel an available trained
channel. A policy that requires stress from a product that cannot supply it is a
contradiction and fails closed rather than being resolved silently. The decision
is immutable, carries its reason codes, and participates in component identity.

### R12-B13 — exact periodicity

`bool(np.all(atoms.get_pbc()))` executed a `[True, True, False]` system as fully
nonperiodic — a different physical system. The exact three-axis vector is now
carried in every deployed static and dynamics request, emitted axis-by-axis as
the LAMMPS boundary command, honoured per axis by the minimum-image safety
reduction, preserved in raw observations, and bound into the dynamics case
identity. A request without periodicity fails closed; there is no default.

### R12-B7 — measured resource evidence and disk safety

The resource-scope digest is identity, not measurement. `ResourceObservation`
now records what each attempt actually cost — total and per-component elapsed
time with reuse marked, workspace filesystem total/free bytes and the attempt's
own footprint at start and end, the configured `[execution].minimum_free_disk_gib`
reserve and whether it held, peak process RSS, and accelerator model/total
VRAM/peak allocation from existing telemetry — bound to the exact binding and
attempt, and pointed at by both the terminal record and the release index.

The existing campaign disk reserve is checked before each component materializes
artifacts or scratch. An attempt that cannot proceed safely aborts; it never
changes a timestep, duration, precision, membership, threshold, or member. No
inventory, archival, deduplication, or cross-owner admission machinery was added.

## 3. Executed checks

```bash
conda run -n mace python -m pytest tests/test_mlff_p7_r12_repair_acceptance.py \
    tests/test_mlff_p7_r11_repair_acceptance.py \
    tests/test_mlff_p7_post_production_qualification.py -n 32 -q -p no:randomly
```
```text
115 passed, 2 skipped
```

The two skips are the R12-B11 real-runtime gates, skipped with their blocking
reason rather than downgraded.

### Affected-surface regression on the final candidate

The revision-12 change set is confined to `training_data/qualification/**`, the
generated `[qualification]` configuration block in `_campaign_cli_core.py`, the
two MLFF test fixtures, and documentation. The affected surface was therefore
derived by dependency — every `test_mlff_*` module that imports the campaign
CLI, the modified fixtures, the qualification package, or the generated config,
plus the architecture-manual specification — rather than by running the whole
repository, whose density/topology/tiling/graphics suites this change cannot
reach:

```bash
conda run -n mace python -m pytest <74 affected MLFF modules> -n 32 -q -p no:randomly
```
```text
58 failed, 678 passed, 4 skipped in 244s
```

Set difference against the fresh P6 baseline: **zero new failing node IDs**; all
58 failures are pre-existing baseline members (predominantly version-pinned
`*_specification` tests). An earlier repository-wide run on this same repaired
source independently confirmed the same conclusion (202 failed / 2964 passed /
100 errors, zero new failures and zero new errors).

## 4. Unavailable / blocking

1. **R12-B11.** The publication path is now driven from an actual frozen member:
   the campaign publishes genuine multihead MACE checkpoint bytes, P5 decides the
   member, and that exact member's authenticated bytes go through the real
   `mace_deployment` exporter at the canonical target head and the real
   `LAMMPS_MLIAP_MACE` builder, which selects that head
   (`built.model.head == 1`). Execution in LAMMPS remains impossible on this
   host: the installed ML-IAP python data object does not expose the
   `forward_exchange` message-passing contract MACE requires. The runtime probe
   detects this before execution, deployment reports unavailable/blocking, and
   the execution test skips with that reason. No analytic ML-IAP substitute is
   presented as product-path evidence.
2. **R12-B12.** Final target-machine qualification with real external reference
   evidence, actual supported MACE deployment execution, and one-shot locked
   closure has not been run. It requires a runtime that can execute the product,
   which item 1 blocks here.

P7 therefore remains **REOPENED / NO-PASS**, and
`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains blocked.
