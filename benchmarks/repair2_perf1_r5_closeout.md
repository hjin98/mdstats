# REPAIR2 PERF1 R5 product closeout

Date: 2026-08-20
Branch: `codex/repair2-perf1`
Workplan: `DOC-REPAIR2-PERF1`

## Scope

This record closes R5 for the exact forward-only TARGET-DATA2C-REPAIR2 scalar authority after the R1 proposal-frontier factorization. It normalizes the committed R0/R1/R5 workstation evidence and the focused scientific regression result. No REPAIR2 scientific policy, schema, version, persistence lineage, mutation ordering, replacement-pool semantics, filter order, tolerance rule, or content-digest construction changed.

## Product identity

Both R5 runs used the same authenticated product inputs:

- dataset: `lta-dry-alkali-v1`
- label domain: `label-domain-5aa1ee5d50cd0b23`
- candidates: 36,408
- families: 165
- forward MVIDX1 edges: 9,505,021,522
- reference digest: `e79b9fea28d72e42782375bdb4c08dccdf65963852b333bd96b6255e83bee995`
- MVIDX1 digest: `2c9b855794e5e123c0170ebdbf5764b787e3aadfac330366e97bfc68111f79d1`
- MVSEL2 digest: `8c3f999d01d496ebcd7d2e2c08af02590702187e6ab766d3ec54b08367645198`
- REPAIR2 authority version: `mdstats.target-data2c-repair2.forward-state.2026-08.v1`
- REPAIR2 policy digest: `42792a7afb205160a20269b82c412274a45edb499477ceee51f1accac2b9d38e`

## R0 to R1 optimization result

The first pathological/proposal-bearing rung was target size 1,024.

| metric | R0 | R1 | change |
|---|---:|---:|---:|
| 1,024-rung wall | 1058.679 s | 79.604 s | 13.30x faster |
| bounded build wall through 1,024 | 1099.350 s | 120.922 s | 9.09x faster |
| state-invariant frontier wall | 976.749 s | 15.779 s | 61.9x lower |
| repeated/shared frontier forward edges | 56,894,155,008 | 888,971,172 | 64x lower |
| proposal evaluations | 2,048 | 2,048 | unchanged |
| accepted swaps | 32 | 32 | unchanged |

R1 built exactly one lexical shared frontier for each of the 32 unchanged proposal-bearing states. The old scalar proposal path remains reference-only for regression/oracle qualification and is not used by the product loop.

The R1 result exceeded both structural and wall-time acceptance thresholds. Conditional R2/R3/R4 optimization is therefore skipped.

## R5 full product runs

The R5 benchmark ran the canonical REPAIR2 builder through every materializable rung through 16,384 and then loaded the full native MVIDX1 authority for independent validation.

| metric | run 1 | run 2 |
|---|---:|---:|
| full build | 00:08:27 (506.868 s) | 00:08:28 (507.729 s) |
| independent validation | 00:00:59 (59.057 s) | 00:00:49 (48.832 s) |
| build + validation | 00:09:26 | 00:09:17 |
| completed full repair | yes | yes |
| independent validation passed | yes | yes |
| OS swap after run | 0 KiB | 0 KiB |
| repair content digest | `ba4462edabf720308f2024fa31e98a7012b497921610b6730782b186932a750e` | `ba4462edabf720308f2024fa31e98a7012b497921610b6730782b186932a750e` |

The two uncached recomputations therefore prove deterministic repaired authority by identical content digest. Both combined build-plus-validation times are below the workplan's sufficient 10-minute R5 closeout target and comfortably below the former 20-minute enclosing meter.

The benchmark reports zero filesystem output from the REPAIR2 build itself and creates no second product-scale graph. The implementation remains forward-only, reports zero full-state proposal copies, and performs no inverse mutation.

## Independent scientific validation

`validate_target_multi_view_repair_authority_v2()` independently reconstructs each materializable rung from the persisted sparse index. It checks immutable nesting, recomputes family coverage, rejects same-N coverage below the corresponding MVSEL2 rung, recomputes hard-obligation counts, and rejects hard-obligation regression. The R5 runs passed this independent validator.

Focused regression supplied with the R5 closeout:

```text
11 passed, 1 warning in 4.56s
```

The single warning is `VelocityReconstructionWarning` from `mdstats/io/vasp.py` in the production-style multifamily fixture. It concerns reconstructed velocities/high-frequency spectra and is unrelated to REPAIR2 selection, coverage, hard obligations, mutation semantics, serialization, or content digests; it is non-gating for this workplan.

Earlier focused R1 qualification also established exact factored-vs-frozen-scalar proposal equivalence, whole-plan/digest transparency under telemetry, one-frontier-per-state structure, bounded O(candidate-count) frontier storage, and 354/354 valid randomized frozen-oracle matches.

## R5 decision

R5 PASS.

The REPAIR2 pathological gate is closed. No additional R2/R3/R4 execution complexity is justified. The next workplan gate is O0: continue the same real campaign `prepare` path, observe subsequent stages by resource class, and optimize only a downstream stage that crosses the measured workplan threshold or exhibits a demonstrated asymptotic/repeated-scan pathology.

The independent validator currently costs only about 49-59 seconds, so O1 does not trigger from R5 evidence.
