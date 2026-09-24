# MLFF final-production model publication + MH-1 integration — final closeout

Date: 2026-09-24  
Protocol: SSDP 6.4  
Disposition: **PASS / CLOSED**

## Accepted identities

- Retained executable product: `73aab9e35399c5b7ceec3bbe31e129f76a50cdd8`
- Final test/evidence candidate: `5a6719d9fbabf04ddad7407b2729be0d0d1f76bf`
- Final test/evidence tree: `45ab5adf7b94e58770cecf73a27325e06206b309`
- Actions workflow descendant: `e048aeebcde62301f4ccf6109fd89a238030cf83`
- GitHub Actions run: `36007255491`
- Durable Actions report commit: `84a38b45a9ddd0df6bb19dfba6ba240db094aa2e`
- PEM reconciliation descendant: `54e3a350855237002012b136442ec9621fe89a98`

The evidence-repair lineage changes no `mdstats/**/*.py` production source. The product implementation reviewed at `73aab9e...` therefore remains the executable product subject.

## Final executable evidence

The temporary validation workflow first proved:

```text
git diff --exit-code 5a6719d9fbabf04ddad7407b2729be0d0d1f76bf -- mdstats tests
```

on its execution descendant, then ran the required acceptance.

### Corrected closeout surfaces

```text
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_downstream_integration_closure.py
```

Result: **104 tests, 0 failures, 0 errors, 2 skips**.

The two skips occur only at actual missing target-host LAMMPS/MLIAP runtime boundaries. The corrected P7 tests reach the valid current P5 full-model product and real deployment/runtime path before that unavailability is observed.

### Mandatory focused suites

```text
tests/test_mlff_p5_model_publication_owners.py
tests/test_mlff_p5_model_publication_acceptance.py
tests/test_mlff_p7_deployment_realization.py
tests/test_mlff_p7_product_currentness_fences.py
tests/test_mlff_mh1_publication_integration.py
```

Result: **91 tests, 0 failures, 0 errors, 2 skips**.

The two skips are the explicitly deferred locked-real-MH1-byte checks. Bounded current-owner MH-1 integration executed.

### Static execution

`python -m compileall -q mdstats tests`: **PASS**.

The complete runner environment and exact non-pass details are durably recorded in:

`qualification/mlff-publication-closeout/actions-validation-report.md`

## Closure findings

All post-Revision-28 blockers are closed:

- exact committed evidence binding is established;
- P7 current-product runtime oracles no longer skip on a local head mismatch;
- the weak rename-sensitive checkpoint AST sensor was retired instead of expanded;
- stale/superseded tests were remapped or retired at their evidence owners;
- small-CI resource behavior is bounded only in the toy test fixture;
- PEM records the intervention as a distinct coordinated application episode;
- no production compatibility wrapper, alternate scheduler, registry, binding database, or MH-1-specific product path was added.

No Serious Challenge is active. Revision-22 D3 remains coherent.

## Deferred final-release qualification

The following remain deliberately non-blocking for this workplan:

- real locked MACE-MH-1 campaign execution;
- target-host GPU/CUDA performance and VRAM qualification;
- production LAMMPS/MLIAP execution;
- long production MD validation.

These belong to the actual campaign/final-release qualification package, consistent with the standing MLFF qualification policy.

## Repository hygiene

The temporary GitHub Actions workflow used solely to obtain executable evidence is removed in the archival commit. The successful Actions run and its committed report remain durable evidence.

**Final verdict: PASS / CLOSED.**
