# mdstats 0.20.237a0 - MLFF progress-format consistency maintenance

- Standardize all current MLFF periodic progress and heartbeat emitters around one semicolon-delimited message grammar.
- Format `elapsed` and known `eta` as fixed-width `HH:MM:SS`; use `--:--:--` for an unavailable ETA.
- Normalize progress fractions, throughput units, phase/status vocabulary, adaptive scheduler messages, DATA6 sweep reporting, and live TRAIN heartbeat output.
- Add shared formatting helpers and regression tests that reject legacy `10s` / `27.9 min` / `estimating` ETA dialects in MLFF progress code.
- Preserve architecture revision 103, dependency schema 83, all scientific authority, MPA-0/MH-1 behavior, and the `FINAL-GPU1` next-gate decision.
