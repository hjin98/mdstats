# mdstats 0.20.104a0 patch notes

## Source-tool restoration and packaging integrity

- Restore the user-facing `tools/` tree last present in the 0.20.99a0 complete
  source package.
- Keep `tools/mdstats-mlff-campaign.py` as a thin source-checkout launcher over
  the current `mdstats.training_data.campaign_cli.main`, so OPT-EVAL1 through
  OPT-CTRL1 execution remains fully active and no optimized MLFF logic is
  duplicated or bypassed by the wrapper.
- Port `tools/finalize_lta_data9a3_qualification.py` to the current immutable
  `ProductionCorpusPlan` qualification API. The old 0.20.99a0 utility still
  passed the removed `expected_source_count=` keyword and was already stale.
- Make the MACE runtime qualification and DATA9A3 finalization tools bootstrap
  the source-checkout root explicitly, so they work outside the repository CWD.
- Regenerate `campaign.toml.example` from the current campaign backend and retain
  CUDA as the example target. This restores the 0.20.103a0 optimized evaluation
  controls, including 5% calibration peak trimming, 30 s post-calibration GPU
  telemetry, and bounded OPT-EVAL4 CPU prepare/finalize pipeline controls.
- Restore the normative MLFF and Stage-11 machine-readable dependency graphs
  that were omitted by the same source-distribution manifest regression.
- Update `MANIFEST.in` so future sdists include `tools/`,
  `campaign.toml.example`, and architecture JSON files.
- Add packaging/front-end regression tests so the restored source files and
  current optimized campaign defaults cannot silently disappear again.

## Compatibility

The frozen MLFF scientific campaign identity remains 0.20.99a0. This release
changes source-package/front-end integrity and does not invalidate existing
campaign state, DATA artifacts, prediction caches, checkpoint-selection records,
or bounded-verification cache identities.
