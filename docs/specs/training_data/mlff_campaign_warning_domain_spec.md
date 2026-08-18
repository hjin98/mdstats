# MLFF WARN-DOMAIN1 campaign-wide warning capture specification

- Release: `mdstats 0.20.220a0`
- Architecture revision: `87`
- Dependency-graph schema: `69`
- Gate: `WARN-DOMAIN1`

## Purpose

The MLFF campaign SHALL own one warning domain from CLI command dispatch through command completion/failure. The domain is an observability/compatibility control and SHALL NOT alter scientific results, parity thresholds, data membership, or cache identity.

## Python warnings

The outer domain SHALL capture MACE/PyTorch warnings across the full command lifetime. Existing operation-local `mace_runtime_warning_scope` calls SHALL nest into the campaign owner and SHALL NOT independently emit compatibility warnings while the campaign owner is active. Known TorchScript deprecations SHALL be condensed rather than printed with their raw source locations.

## Logging warnings

MACE/PyTorch logging records at `WARNING` or higher SHALL enter the same grouped record. Classification SHALL use the emitting source pathname and package logger name, because MACE 0.3.16 emits some calculator warnings through the root logger. Matching records SHALL be intercepted before logger handlers emit raw output.

The observed MACE 0.3.16 message `Default dtype float32 does not match model dtype float64, converting models to float32.` is an explicit regression case. It SHALL appear only inside the normalized grouped campaign summary, never as `WARNING:root:`.

## Threads

The active campaign owner SHALL be visible process-wide for the lifetime of one command. A local MACE warning scope entered by a worker thread SHALL merge into the campaign owner even if the worker did not inherit the main-thread `ContextVar`. Operation registration SHALL be thread-safe.

## Presentation

At command exit mdstats SHALL emit at most one `[WARN]` compatibility summary when grouped MACE/PyTorch warnings were observed. The summary SHALL include total count, unique group count, compact source/message signatures, operations, and runtime versions.

Unrelated warning/logging records SHALL preserve their historical behavior. Standalone mdstats calls outside campaign execution SHALL retain local consolidated `MaceRuntimeCompatibilityWarning` behavior.

## Acceptance cases

1. A TorchScript `torch.jit.script` warning emitted before a local provider scope is captured.
2. A nested `torch.jit.load` warning is merged into the same command record.
3. The MACE root-logger dtype conversion warning is captured and does not print as `WARNING:root:`.
4. A local scope entered from a worker thread merges into the active campaign domain.
5. The command emits exactly one normalized `[WARN]` line for the combined synthetic leak case.
6. Unrelated vendor logging is not classified or suppressed by the MACE/PyTorch policy.
