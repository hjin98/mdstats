# mdstats 0.20.105a0 patch notes

## Scope

This maintenance release corrects misleading wall-clock throughput and ETA reporting in the MLFF preparation/campaign path. No scientific record schema, selection policy, model-training protocol, checkpoint identity, or verification identity is changed.

## Root cause

DATA6 performs foundation-model work in numerical batches and persists results in artifact shards. The old implementation emitted one logical progress callback per frame only after a completed batch was being journaled. A reporter sampling the time between those callbacks measured how quickly Python drained already-computed bookkeeping events, not how quickly MACE computed frames. Thus a real cumulative rate near 20 frame/s could be paired with a spurious "recent" rate above 1,000 frame/s and an ETA of only seconds.

The threaded universal-structural-feature path had the same producer/consumer timing risk: completed futures can be consumed in bursts after workers have already performed the numerical work.

A related restart/cache issue existed in the generic campaign reporter: multiple already-complete items emitted immediately at startup could be counted as current throughput and make the ETA for the remaining expensive work unrealistically small.

## Changes

1. `production_model_sweep.py` coalesces DATA6 progress callbacks to one notification per persistence drain instead of one notification per journaled frame.
2. New internal `ProgressRateTracker` separates cumulative wall-clock throughput from recent diagnostics. Recent-rate samples require a real minimum wall-clock window, so sub-second callback bursts are ignored.
3. DATA6 ETA uses cumulative throughput since the current run/restart baseline. A restored verified checkpoint resets the baseline so previously completed frames do not inflate the rate.
4. Universal structural selection uses the same stable tracker and cumulative ETA policy.
5. `_ProgressReporter` treats immediate startup cache/restart completions as baseline work and displays `eta=estimating` until actual timed work has been observed.
6. Progress interval tests use completed-count deltas rather than exact modulo hits, so coalesced/batched callbacks cannot skip reporting merely because a batch jumped across an interval boundary.

## Example

For

```text
[DATA6   3100/36759] ... recent=1708.24 frame/s avg=20.07 frame/s eta=20s
```

the cumulative rate implies

```text
remaining = 36759 - 3100 = 33659 frames
ETA = 33659 / 20.07 s = 1677 s ≈ 28 min
```

The corrected reporter therefore stays near that cumulative estimate rather than using the callback-drain burst rate.

## Compatibility

All frozen MLFF scientific/materialization identities remain unchanged. Existing 0.20.99a0+ campaigns, DATA6/DATA8 artifacts, checkpoints, prediction caches, and verification records remain reusable.
