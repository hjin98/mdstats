# mdstats 0.20.65a0 DATA8 runtime-path correction

## Observed failure

`prepare` completed and printed the final successful DATA8 variant, but `preflight`
stopped after replay qualification. `status` then reported byte-verification
failures for `fold_00`, `fold_01`, `fold_02`, and `final` in every materialized
variant.

## Root cause

DATA8 assembly uses a temporary `.data8-staging-*` directory and then atomically
promotes the complete tree into `.data8-generations/<tree-digest>`, with `data8`
as the live pointer. The immutable `Data8PreparationBundle` records the staging
path in `output_directory`. Campaign preflight incorrectly treated that immutable
assembly locator as the runtime directory. Because the staging directory is
removed after promotion, every config lookup failed before the MACE smoke test.

The absence of visible output was a second defect: the verification loop appended
failures to the stage state but returned without printing them. The replay
qualification line was therefore the last visible message.

## Corrections

- Resolve each live DATA8 root from its existing
  `ProductionMaterializationRecord` and promoted artifact pointer.
- Reuse all completed prepare artifacts; installation alone is sufficient before
  rerunning `preflight`.
- Print variant-qualified missing-file or SHA-256 diagnostics immediately.
- Pass the promoted root into the real-MACE preflight smoke.
- Use the same promoted root for training execution.
- Rebase replay-monitor paths recorded under staging for checkpoint evaluation.
- Resolve target monitor artifacts under `jobs/<job_id>/`, fixing a latent
  post-training evaluation failure.

## Integrity behavior

The patch does not weaken byte verification. Config bytes are still authenticated
against the SHA-256 stored in each immutable `MaceJobArtifact`; only the live root
used to locate those bytes is corrected.
