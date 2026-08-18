# MLFF architecture revision 25 — ADAPT-PREC1 implementation

mdstats 0.20.122a0 implements the first gate of the adaptive-training revision recorded
in REV24.

## Closed gate

`ADAPT-PREC1` is complete for new campaigns:

- learned-model precision is binary: `single` (FP32) or `double` (FP64);
- staged `refine` and a user-facing `mixed` model mode are retired;
- generated campaign TOML has no executable staged precision schedule;
- new optimizer/DATA8 protocols are schedule-free, making staged optimizer/EMA promotion
  unreachable from new production configuration;
- model dtype follows training, evaluation inference, verification inference, committee
  inference, and export without silent promotion;
- mdstats-owned critical/scientific arithmetic is invariant FP64 under either learned-
  model dtype; and
- historical staged/refine evidence remains readable but production execution fails
  closed rather than silently rewriting its identity.

Historical PREC1-PREC3 implementation records remain part of the architecture as evidence
for old campaigns. They are not production semantics for newly initialized campaigns.

## Gates still open

`ADAPT-MON1`, `ADAPT-STOP1`, `ADAPT-RANK1`, `ADAPT-EVAL1`, `ADAPT-VERIFY1`, and
`ADAPT-MIGRATE1` remain unimplemented. In particular, 0.20.122a0 does **not** yet enable
the planned 256/512 fixed monitors, criterion-driven epoch stopping, lightweight weighted
ranking, or top-five full evaluation. Existing fixed-epoch monitor/EVAL-MF behavior
remains authoritative until those later gates close.
