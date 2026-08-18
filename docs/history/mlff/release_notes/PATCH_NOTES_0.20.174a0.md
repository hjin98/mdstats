# mdstats 0.20.174a0 patch notes

## Gate

`RELAX-VERIFY1` - matched zero-K DFT/MLFF relaxation qualification with hard periodic topology preservation and quantitative relaxed-geometry fidelity.

## Implemented

- Consume only PES-VERIFY1-qualified target-only deployment candidates and inherit up to four candidate-independent, correlation-balanced PES base structures as common zero-K relaxation starts.
- Add immutable RELAX-VERIFY1 policy, base-set, DFT-request, DFT-reference, per-base metric, model-qualification, per-run, and campaign authority records.
- Materialize `results/relax-verify1/relax-request.extxyz`, a manifest, and one frozen VASP `POSCAR` directory per base. `verify` returns `WAITING` until authenticated matched fixed-cell DFT relaxations are available.
- Auto-collect VASP references only when every base has `INCAR`, `KPOINTS`, `POTCAR`, and `vasprun.xml`; require identical input bytes across bases, unchanged request POSCAR bytes, fixed cell/PBC/atom identity, final force convergence, and an intact protected DFT topology. External relaxed ExtXYZ requires an explicit protocol digest.
- Freeze first-release MLFF relaxation to ASE FIRE, fixed cell, `fmax = 0.03 eV/A`, and at most 500 optimizer steps. Non-finite predictions, optimizer failure, changed model bytes, or failure to converge reject the candidate.
- Make protected-group periodic connectivity a hard safety authority. Generated LTA campaigns protect the profile-declared `framework` group under a frozen 1.20 covalent-radius cutoff scale; Li/Na/K guest motion is outside that graph. Candidate bonded-pair and coordination identities must match the DFT-relaxed reference exactly, while harmless periodic wrapping is equivalent.
- Add independent geometry-fidelity gates on every common base: protected-group RMS/max displacement <= 0.15/0.40 A, protected-bond RMSE/max error <= 0.08/0.20 A, protected-angle RMSE/max error <= 8/20 degrees, fixed-cell strain norm <= 1e-4, and final maximum force <= 0.03 eV/A.
- Persist relaxed-candidate ExtXYZ artifacts plus exact PES/model/reference/policy/protocol/topology/metric lineage. Reuse is allowed only when those identities still authenticate.
- Wire TRAIN2 `verify` as DEPLOY-VERIFY1 -> PES-VERIFY1 -> RELAX-VERIFY1 -> `WAITING` for DYN-VERIFY2. A failed PES candidate never enters RELAX; if every RELAX candidate fails, verification fails closed.
- Update generated/example campaign configuration, README/changelog, public APIs, version metadata, canonical architecture manual/PDF, and focused specifications.

## Intentionally deferred

- `DYN-VERIFY2` short NVE/NVT structural dynamical qualification.
- Final physical completion of TARGET-DATA2D Stage C, TARGET-DATA2E materialization, and SELECT2 production publication.

## Qualification

- Primary cross-gate runtime/specification batch: 238 passed, 1 expected external-LTA skip.
- Additional checkpoint/materialization/production-integrity hardening batch: 42 passed.
- Final RELAX/current-gate specification batch after documentation/version synchronization: 31 passed.
- Python `compileall` and public import checks passed.
- Architecture PDF regenerated from canonical Markdown, expanded from 130 to 131 pages, preflighted, compared at 40 DPI, and RELAX/SELECT transition pages visually inspected at 150 DPI with no clipping, overlap, or broken glyphs.
- No DFT relaxation result is fabricated in this container. Campaign-time RELAX-VERIFY1 writes the exact request and waits for authenticated converged DFT reference relaxations.
