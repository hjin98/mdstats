# MLFF parallel CuEq conversion guard and incremental evaluated-model export

Status: implemented in mdstats 0.20.94a0.

## Problem

Two independent issues were observed during real parallel checkpoint evaluation.

First, two evaluation workers could concurrently construct CuEquivariance-backed
MACE calculators. MACE 0.3.x accelerator conversion performs graph rewriting through
PyTorch FX. FX tracing uses process-global tracing hooks/state, so overlapping graph
rewrites from sibling Python threads can cross-observe modules from different model
trees and fail with `NameError: module is not installed as a submodule`.

Second, campaign-level target-head export happened only after every configured run
finished checkpoint evaluation and protocol aggregation. A run whose checkpoint
selection was already final therefore had no convenient parent-level deployment
artifact until unrelated folds/runs completed.

## Runtime contract

### Accelerator conversion

- Checkpoint file I/O, model deserialization, device transfer, and later CUDA inference
  remain eligible for the existing outer parallel executor.
- Only MACE accelerator graph-rewrite functions (`run_e3nn_to_cueq`,
  `run_e3nn_to_oeq`, and hybrid conversion) are process-serialized by one re-entrant
  lock.
- Wrapping is installed once and is idempotent.
- The lock protects third-party FX conversion only; it does not serialize ordinary
  e3nn calculator construction or model inference.

### Per-run evaluation finalization

A run becomes individually finalized when every checkpoint in its frozen evaluation
shortlist has an authenticated reusable or newly computed evaluation record.
Immediately at that point mdstats:

1. performs deterministic checkpoint admissibility/selection for that run;
2. persists `selection:<run-id>` (or the selection-failure record);
3. starts export of the selected target head to
   `models/<run-id>-target.model` without waiting for other campaign runs;
4. retains checkpoint-model reconstruction caches until export can reuse the selected
   model, then removes the run-local reconstruction cache after successful export;
5. leaves already-published run models in place if a later unrelated run fails.

The per-run export is a `VerificationModelRecord`, not yet a campaign committee/freeze
claim. Cross-validation fold exports are valid fold-specific deployment candidates;
final-development exports are the eventual production-candidate inputs if their
protocol family wins aggregation.

### Atomic publication

Target-head export always writes to a temporary file in the destination directory and
publishes with `os.replace` only after successful serialization. Interrupted export
must not truncate the public destination or destroy previously valid bytes.

### Queue conservation

When multiple futures complete in one scheduler wake-up, all completed futures are
removed from the active set and all newly empty execution slots are refilled before
potentially slower parent-side callbacks (selection, persistence, export scheduling,
progress formatting) run.

## Compatibility

- Scientific checkpoint-evaluation policy digests are unchanged.
- Existing evaluation records remain reusable when all prior identity checks pass.
- Existing campaign TOMLs require no new key.
- The accelerator guard is runtime-only and does not change model weights or
  scientific identities.
- Final protocol aggregation and committee freeze remain authoritative campaign-level
  decisions; early per-run model publication does not imply protocol selection or
  scientific acceptance.
