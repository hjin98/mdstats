---
kind: implementation-evidence
package_id: CODE-MLFF-TARGET-SIZE-V7-P7
package_revision: 11
protocol_version: 5.8.0
reviewed_revision_10_commit: afe4d690f1f7c084ac33077ecdcb24d67cd14802
reviewed_revision_10_tree: ab4c1d32e44585615ba0501fb44d5666afe82190
repair_start_commit: f815ec490f31e2c087f6b16c08adcc939e87dd4e
p7_executable_source_tree_digest: a7a5f2c21910170cc0a7a232998c1d006b13ba755cae51ac913f47e3ed6a075d
predecessor_executable_source_tree_digest: 744e080f427da4c48fe114dbd2efa7653231b091d3039cb74b135dc5e7328710
status: bounded-implementation-complete-pending-target-machine-qualification
recorded_date: 2026-08-31
---

# P7 revision 11 — repair implementation evidence

Repair authority: `P7_REVISION_11_AUTHORITY.md` composed with
`P7_REVISION_11_IMPLEMENTATION_REVIEW_REOPEN_AMENDMENT.md`, the still-binding
revision-10 amendment, the base P7 workplan, and the frozen parent.

`P7_IMPLEMENTATION_EVIDENCE.md` remains the historical record for the reviewed
revision-10 candidate and is unmodified.

## 1. Disposition of the twelve blocking findings

| ID | Disposition | Where |
|---|---|---|
| R11-B1 | repaired at the P5 owner | `post_selection_publication.py`, `campaign_post_selection_runtime.py` |
| R11-B2 | repaired | `qualification/publication.py`, `qualification/runtime.py`, `qualification/deployment.py` |
| R11-B3 | repaired | `qualification/store.py`, `qualification/runtime.py` |
| R11-B4 | repaired | `qualification/reference.py`, `qualification/runtime.py` |
| R11-B5 | repaired | `qualification/dynamics.py`, `qualification/spec.py` |
| R11-B6 | repaired | `qualification/runtime.py`, `qualification/store.py` |
| R11-B7 | repaired | `qualification/resource_scope.py`, `qualification/runtime.py`, `target_size_execution/persistence.py` |
| R11-B8 | repaired | `qualification/reference.py`, `qualification/runtime.py` |
| R11-B9 | repaired | `qualification/stress.py`, `qualification/deployment.py`, `qualification/physical.py` |
| R11-B10 | repaired | `qualification/geometry.py` |
| R11-B11 | **partially unavailable** | see section 4 |
| R11-B12 | **not run** | see section 4 |

## 2. Repairs

### R11-B1 — the publication decision moved to its real owner

`train-production` now finishes by publishing an immutable
`FinalProductionPublicationDecision`. It is taken at the only moment when every
input exists and no downstream release evidence does.

Two predecessor gaps had to close first. Each completed production run now
durably publishes the exact records that chose its representative — the
representative EVAL2/admissibility record and its M3 target metric record —
which were previously referenced by digest alone, leaving nothing for a
cross-seed decision to authenticate. A run root written before those records
were durable is re-evaluated through the real EVAL2/provider owner on its exact
authenticated checkpoints and must reproduce the digests its run evidence
already bound; nothing is synthesized from a digest.

Both configured committee policies are now decided by P5.
`single_best_final_seed` ranks only the already-frozen per-seed representatives
through the accepted target-only EVAL2 ordering over the common frozen M3
evidence, with tie material descending from the final-production plan identity.
No downstream metric participates, and replay evidence remains
admissibility-only. P7 contains no cross-seed ranking at all — proven
structurally in `test_r11b1_qualification_consumes_the_p5_decision_and_ranks_nothing`.

`PredecessorReclosureRecord` binds the reclosure and rebind identity: selected
binding, publication, plan, member digest, decision-policy identity, and the
executable source-tree digest that produced them.

### R11-B2 / R11-B11 — canonical target head through the real owners

The canonical P5 `target_head` travels with every published member and is part
of the member identity, the publication member digest, and the deployment
identity. Deployment export and the MACE ML-IAP builder are both called with it;
neither accepts `None` for a multihead-capable product, and a model whose heads
do not contain it fails closed.

The ML-IAP import path was also wrong in the reviewed candidate
(`mace.calculators.lammps_mace` instead of `mace.calculators.lammps_mliap_mace`),
so the "real" builder could never have run.

### R11-B3 — exposure-time currentness

Every public resolver for the plan, terminal record, and release index
re-establishes the current `QualificationInputBinding` at exposure time and
validates the located object against it. The campaign-store pointer is a locator
only, and there is deliberately no unfenced public read. Locked disclosure
history lives outside that fence in an append-only reveal index, so a
currentness change can make a verdict historical without making a revealed
cohort fresh.

### R11-B4 — component-input identity

Reference-dependent components are keyed by a component-input identity including
the exact frozen request and the exact authenticated bundle digest. Replacing a
bundle under the same request stales PES, relaxation, and dynamics while
deployment and calibration remain reusable; old evidence stays immutable.

### R11-B5 — reference-relaxed dynamics and the complete diagnostics

Each case starts from the authenticated `relaxed_positions_angstrom` of its
base; a missing relaxed reference is `waiting_for_reference`, never a fallback
to the unrelaxed geometry. The worker returns raw observations only; the reducer
decides NVT and NVE temperature behaviour, energy drift, minimum pair distance,
maximum force, and protected topology, displacement, bond, and angle
degradation, under a consecutive-sample persistence rule that is part of the
specification digest.

A nonfinite observation is now a rejection *reason* rather than a serialization
crash: immutable evidence stays JSON-exact and records the measurement absent.

### R11-B6 — crash-resumable one-shot activation

Opening the cohort and completing the locked result are recorded as separate
facts. A crash in between resumes onto the same activation identity; a second
activation is refused only once the terminal record *and* the release index both
reference that activation. The retention reference is acquired before
prerequisite work and released only on terminal close or abort.

### R11-B7 — accepted resource ownership, race-free artifacts

Concurrency, nested thread budgets, and worker counts come from the accepted
`resources` owner. Deployed artifacts publish create-once under an advisory
per-artifact lock exposed from the existing persistence owner
(`artifact_publication_lock`), and are re-authenticated from a durable receipt
plus their bytes before every reuse, including after restart with an empty
cache. The resource scope is bound separately from the numerical environment
identity, so capacity is recorded without making a numerical claim
machine-specific while a materially different scope still cannot reuse a
performance claim.

### R11-B8 / B9 / B10

The placeholder reference protocol fails closed before any reference-dependent
work. Stress is resolved as an explicit capability with a canonical conversion
owner and is compared when applicable, with unavailability recorded rather than
silently claimed. Qualification topology/geometry now adapts the canonical
`mdstats.analysis` connectivity, cutoff, and periodic-neighbour owners; that
reconciliation surfaced a real correctness guard — the canonical neighbour owner
refuses a cutoff exceeding the safe minimum-image radius, which the previous
local implementation would have silently violated.

## 3. Executed checks

The effective CPU owner on this host exposed one available worker (`nproc` = 1)
even though the host reports 32 online CPUs (`getconf _NPROCESSORS_ONLN` = 32).
All concurrent test commands therefore used `-n 1 --dist=loadfile`; this also
stays below the frozen P6 maximum of 16 testing processes.

Revision-11 repair acceptance, on the final source candidate:

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_p7_r11_repair_acceptance.py
```
```text
41 passed, 1 skipped, 223 warnings in 529.08s (0:08:49)
```

The final stress-unit normalization path was then exercised directly:

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_p7_r11_repair_acceptance.py -k 'r11b9'
```
```text
3 passed, 11 warnings in 24.86s
```

The still-binding revision-10 P7 acceptance surface passed:

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_p7_post_production_qualification.py
```
```text
44 passed, 182 warnings in 532.30s (0:08:52)
```

Affected predecessor and integration surfaces passed independently:

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_target_size_p5*.py
```
```text
175 passed, 187 warnings in 990.74s (0:16:30)
```

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_target_size_p6_destructive_closure.py tests/test_mlff_target_size_p6_p5a6_compatibility.py tests/test_mlff_stor1_storage_accounting.py tests/test_mlff_stor3_safe_reclamation.py tests/test_mlff_stor4_manual_reclamation.py tests/test_mlff_stor5_archive_deduplication.py
```
```text
55 passed, 26 warnings in 129.45s (0:02:09)
```

```bash
conda run -n mace python3 qualification/p6-p5a6-compat/qualify_p5a6_to_p6.py
```
```text
P5A6 -> P6 authenticated current-generation compatibility: PASS
P6 -> P6 current-generation restart: PASS
V5/V6 -> reject-before-reuse: PASS
```

```bash
conda run -n mace python3 -m pytest -n 1 --dist=loadfile -q tests/test_mlff_target_size_p4g_assembled_integration.py tests/test_mlff_campaign_cli.py tests/test_mlff_doc_arch1_specification.py
```
```text
21 passed, 12 warnings in 36.75s
```

The collection preflight found 3,233 tests and one pre-existing collection
error because `tests/data/mesh_topology_revision_stage1_cases.json` is absent.
The exact repository-wide pytest run and a complete target-size/storage batch
were started with the same one-worker setting but manually interrupted before
an aggregate result; neither is reported as passed here.

Documentation publications were rebuilt with the archived repository Typst
0.15.1 binary after the default `PATH` lookup reported Typst unavailable. The
architecture PDF is 35 pages and its manifest source/PDF hashes match the
rebuilt Markdown/PDF; the direct campaign-guide PDF is 5 pages and its text
contains the current qualification/target-head/reference-relaxed guidance.
The build report is `build/docs/p7_r11_publications.json`.

## 4. Unavailable / blocking

1. **R11-B11 — real MACE ML-IAP execution is unavailable on this host.** The
   owner-level path is proven as far as the host allows: a genuine multihead
   MACE model is exported through the real `mace_deployment` owner at the
   canonical target head, and the real `LAMMPS_MLIAP_MACE` builder produces the
   artifact with that exact head selected (`built.model.head == 1`). Execution
   then fails inside LAMMPS because this build's ML-IAP python data object does
   not expose `forward_exchange`, the halo exchange MACE's ML-IAP model
   requires; the Kokkos/GPU path additionally hits a device-side assert. This is
   detected up front by the runtime probe (`mace_mliap_supported`), reported as
   unavailable/blocking, and skipped with that reason rather than being claimed.
   The analytic `MLIAPUnifiedLJ` smoke remains labelled as process-plumbing
   evidence only.
2. **R11-B12 — final target-machine, real-reference qualification is not run.**
   It requires a real production MACE product, real external DFT references
   under an explicit protocol, and a runtime that can execute the product; the
   third is blocked by item 1 on this host.

Both are recorded as blocking for the revision-11 closure gate. P7 remains
**REOPENED / NO-PASS** and `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` remains
blocked.
