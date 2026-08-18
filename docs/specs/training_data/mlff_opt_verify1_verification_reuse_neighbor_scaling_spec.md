# OPT-VERIFY1 verification reuse and nearest-pair scaling

Status: implemented in mdstats 0.20.102a0.

## Scope

OPT-VERIFY1 changes only bounded verification execution. It does not change model
weights, verification case identities, thresholds, NVE integration parameters,
checkpoint/model selection, or scientific acceptance policy.

The stage removes three repeated-work paths:

1. verification structures are parsed once into immutable ASE templates and copied
   for independent NVE cases;
2. each adaptive verification worker retains at most one private MACE calculator,
   reusing model deserialization/device transfer for adjacent cases on the same
   model while never sharing mutable calculator state between threads;
3. sampled minimum pair distance no longer constructs a full periodic `N x N`
   distance matrix.

## Private calculator ownership

A calculator cache is thread-local. Its identity contains the absolute model path,
device, dtype, and acceleration-policy digest. A cache hit therefore requires the
same deployed model and numerical runtime policy.

Only one calculator is retained per worker. Moving to another model replaces the
worker's previous calculator. Resident model multiplicity is therefore bounded by
the adaptive scheduler worker count rather than by the number of
model--structure--temperature cases.

Explicit calculators supplied to `_nve_verify` remain supported for tests and
external/internal compatibility.

## Structure template reuse

Verification structure files are still SHA-256 authenticated exactly as before.
If every verification case is already cached, structure files are not parsed at all.
Otherwise each configured structure is parsed once in the parent process and stored
as a calculator-free immutable template. Every NVE case receives an independent
`Atoms.copy()` before velocity initialization or dynamics.

## Exact nearest-pair search

The former implementation called `Atoms.get_all_distances(mic=True)`, materializing
an `N x N` matrix at every diagnostic sample.

The replacement uses ASE's periodic neighbor-list search with an adaptive radius.
The radius begins at 2 angstrom or the guaranteed search bound, whichever is
smaller. If no distinct atom pair is present, the radius grows geometrically.

As soon as a distinct pair is found, the reported minimum is globally exact: every
pair omitted by the neighbor list lies at or beyond the active radius, while at
least one returned pair lies within it.

The final guaranteed radius is slightly larger than the Cartesian bounding-box
diagonal of wrapped positions. The direct displacement of every distinct pair is
bounded by this diagonal, while the minimum-image distance cannot exceed a valid
direct displacement. Thus a result is guaranteed for any configuration containing
at least two atoms.

The common condensed-phase path therefore uses a local neighbor-list stencil and
avoids quadratic memory. Sparse pathological cells may expand to a large cutoff,
but no dense `N x N` matrix is constructed.

## Compatibility

The package runtime version advances to 0.20.102a0. The frozen MLFF scientific
compatibility token remains 0.20.99a0 and the verification runtime compatibility
token remains 0.20.85a0 because the numerical verification case definition is
unchanged.

Existing completed verification-case caches remain valid. Newly executed cases add
three diagnostic fields only:

- `calculator_reused`;
- `structure_template_reused`;
- `minimum_distance_backend = periodic_neighbor_list_adaptive_v1`.

## Acceptance gates

The implementation is accepted only if:

1. orthorhombic periodic nearest-pair values match the prior dense MIC oracle;
2. fully triclinic periodic nearest-pair values match the prior dense MIC oracle;
3. sparse-cell radius expansion remains exact;
4. the new implementation executes when `get_all_distances` is forbidden;
5. repeated NVE cases on one worker/model instantiate the calculator once;
6. structure templates eliminate repeated structure parsing;
7. existing bounded-NVE pass/fail logic is unchanged;
8. broader campaign/checkpoint/restart/evaluation tests remain green.

## Performance evidence

On the release host, a 1000-atom periodic simple lattice with 2.2 angstrom nearest
spacing required approximately 4.76 s for the former dense MIC matrix and 0.17 s
for the adaptive neighbor-list search, about 28x faster for one sampled diagnostic
frame. This is a host-specific microbenchmark, not a promised total verification
speedup. Model inference and NVE integration may still dominate total wall time.
