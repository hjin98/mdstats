# MLFF progress reporting format specification

Implemented in mdstats 0.20.237a0 as presentation-only maintenance on MLFF architecture revision 103. Dependency-graph schema 83 and the `FINAL-GPU1` next-gate decision are unchanged.

## Canonical grammar

All user-facing MLFF periodic progress and heartbeat messages use semicolon-delimited fields in this order when applicable:

`status; progress; elapsed; eta; recent/current rate; average rate; stage-specific telemetry`

- `elapsed=HH:MM:SS`
- `eta=HH:MM:SS` when known
- `eta=--:--:--` when not yet estimable
- `progress=completed/total (percent%)` for counted work
- explicit rate units such as `frame/s`, `witness/s`, `task/s`, or `edge/s`
- phase-only events use `status=phase; phase=...`

Humanized ETA/elapsed variants (`39m44s`, `27.9 min`, `10s`, `estimating`) are not permitted in MLFF progress output.

## Scope

The normalization covers generic campaign reporters, DATA2/DATA3/DATA4/DATA6 preparation callbacks, structural selection, target-size preparation and screen execution, production model sweep, inference scheduler heartbeats, and live training heartbeats.

## Authority

Formatting is presentation state only. It does not enter scientific content digests, selection/repair/evaluation authority, checkpoint identity, replay identity, scheduler admission authority, model-family behavior, or cache identity. MACE-MPA-0 and MACE-MH-1 use the same progress grammar.

## Qualification

Release qualification SHALL include source-level checks against legacy ETA dialects, formatter unit tests, representative progress-callback tests, the unchanged TARGET-DATA2 scientific authority, and package-version/document synchronization.
