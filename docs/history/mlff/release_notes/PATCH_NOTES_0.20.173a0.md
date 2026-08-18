# mdstats 0.20.173a0 patch notes

## Gate

`PES-VERIFY1` - candidate-independent finite-displacement restoring-force and local-curvature qualification against matched fixed-geometry DFT.

## Implemented

- Added immutable PES-VERIFY1 policy, mode, probe-geometry, probe-set, request, DFT-reference, per-mode metric, model-qualification, per-run, and campaign authority records.
- Inherit base membership from the authenticated DEPLOY-VERIFY1 correlation-block round-robin probe set. The generated default uses at most four correlation-balanced target bases and up to four generic semantic modes per base, with no LTA- or Al-O-specific branch in the PES core.
- Discover generic bond-stretch, exact angle-gradient, coordination-shell breathing, and periodic strain modes. Atomistic directions are unit-normalized and use symmetric +/-0.04 A perturbations; strain uses a 1% default amplitude and rotates hydrostatic/orthorhombic/shear modes across bases.
- Include one q=0 request per base so force/stress comparisons use centered increments and do not assume an AIMD/thermal base is a zero-force stationary point.
- Materialize a common `results/pes-verify1` DFT request as ExtXYZ, manifest, and per-probe VASP POSCAR directories. TRAIN2 `verify` returns WAITING until matched reference labels exist rather than fabricating a physical pass.
- Auto-collect VASP references only when every probe has `INCAR`, `KPOINTS`, `POTCAR`, and `vasprun.xml`; require identical electronic-input bytes across probes and reject any changed requested geometry. External labeled ExtXYZ references require an explicit protocol digest.
- Compare centered projected-force increments, resolved restoring-force direction, symmetric force-derived stiffness, and energy curvature. Periodic strain modes additionally compare centered stress increments/slope and energy curvature per atom.
- Freeze explicit mixed absolute/relative first-release tolerances and resolution floors. PES-VERIFY1 v1 is an all-generated-modes hard gate: a failed mode rejects that candidate from later physical gates.
- Evaluate the untouched FOUNDATION-AUDIT1 checkpoint on the exact same DFT probes as a diagnostic matched baseline. Candidate qualification remains absolute against DFT and does not require beating the foundation on every mode.
- Bind cached evidence to DEPLOY campaign/run identities, target-only model bytes, foundation checkpoint/head identity, common probe/request/reference bytes and DFT protocol, policy, and prediction/qualification digests. Stale deployment policy/model/LAMMPS authority forces DEPLOY regeneration before PES reuse.
- Update generated and example campaign configuration, guide/README/changelog, public API, version metadata, architecture manual/PDF, and focused specifications.

## Intentionally deferred

- RELAX-VERIFY1 zero-K topology preservation and quantitative geometry fidelity.
- DYN-VERIFY2 short structural dynamical qualification.
- Physical completion of TARGET-DATA2D Stage C, TARGET-DATA2E final corpus materialization, and SELECT2 production publication.

## Qualification

- Cross-gate authority/runtime batch: 142 passed across TARGET-DATA2A-E, FOUNDATION-AUDIT1, TRAIN2A/B, EVAL2, DEPLOY-VERIFY1, PES-VERIFY1, and DATA5 lineage.
- Campaign/DATA6/DATA8/cache batch: 103 passed, 1 expected external-LTA skip. Checkpoint-model/production-materialization hardening: 32 additional passes. Total qualified regression evidence: 277 passed, 1 expected skip. Two separate historical specification tests still hard-code package version `0.20.140a0` and are retained as known test debt rather than modified by PES-VERIFY1.
- Python `compileall` and public import checks passed.
- Architecture PDF regenerated from the canonical Markdown, expanded from 128 to 130 pages, fully compared at 30 DPI, and the new DEPLOY/PES/RELAX transition pages were visually inspected at 120 DPI with no clipping, overlap, or broken equations/glyphs.
- No real DFT probe calculation is fabricated in this container. Campaign-time `verify` emits the exact request, waits for fixed-geometry DFT evidence, and resumes only after authenticated labels are available.
