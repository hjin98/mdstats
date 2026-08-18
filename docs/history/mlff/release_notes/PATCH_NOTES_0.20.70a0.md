# mdstats 0.20.70a0 production replay-gate fix

## Symptom

A mixed campaign containing both `naive_fine_tuning` and `multihead_replay`
variants failed at the final DATA9A production gate with:

```text
production_replay_corpus_not_bound
```

even though replay qualification and replay DATA8 materialization had passed.

## Cause

Production qualification records one representative DATA8 materialization. The
CLI always selected the first variant as that representative. After 0.20.68a0
correctly made naïve variants replay-free, a configuration ordered as naïve then
replay caused the representative bundle to report `ReplayMode.NONE`. The gate
therefore interpreted a variant-local property as a campaign-wide absence of
replay.

## Correction

- Mixed campaigns select the first genuine `multihead_replay` materialization
  as the production-gate representative.
- `require_replay_corpus` is derived from the configured training-mode matrix.
- Naïve-only campaigns no longer require replay.
- Mode/bundle mismatches fail with the exact offending variant ID.
- Existing DATA3-DATA8 artifacts remain valid; plain `prepare` reuses them and
  only recomputes the inexpensive final qualification record and restart
  receipt.
