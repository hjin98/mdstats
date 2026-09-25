# TRAIN2 FP32 CuEq doctor sanity pre-check

## Status

This is a **D4 engineering sanity pre-check** used by routine campaign `doctor`.
It is not a scientific-equivalence relation, a model-quality criterion, or a
training-acceptance theorem. Its purpose is only to reject obviously broken or
grossly inconsistent CuEq realizations before expensive work begins.

The historical Revision-86 noise-normalized implementation is retained because
it already exists and is inexpensive on the small doctor corpus. Its statistics
are implementation diagnostics; they are not promoted to D2 scientific
authority.

## Current coarse guard

For FP32 TRAIN2 CuEq doctor checks:

- one warm-up evaluation is discarded;
- ten small post-warm-up evaluations per backend are retained;
- energy, stress, and descriptor cross differences use a coarse absolute ceiling
  of `1e-5`;
- the existing force self-noise ratio guard uses ceiling `1.5`;
- the existing catastrophic force guard remains
  `min(1.5 * Fmax_self, 1e-4 eV/A)`;
- selection fingerprints must remain identical;
- non-finite output, unavailable CuEq, incompatible runtime/model state, or
  failed construction remains a hard failure.

These values are deliberately broad sanity bounds. They are not propagated into
CV, EVAL2, replay, physical validation, convergence, checkpoint selection, or
scientific uncertainty.

## Scope

Changing this pre-check does not change the training objective, optimizer,
dataset, target-size method, CV method, production method, or accepted scientific
interpretation. A doctor pass means only that the requested CuEq realization
looks numerically sane enough to attempt TRAIN2.
