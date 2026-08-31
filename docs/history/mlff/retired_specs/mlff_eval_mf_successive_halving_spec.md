# MLFF EVAL-MF1/MF2 multi-fidelity checkpoint-evaluation specification

Status: EVAL-MF1 implemented in mdstats 0.20.106a0; EVAL-MF2 implemented in mdstats 0.20.107a0. PREC1 is implemented in mdstats 0.20.108a0; PREC2 is the next MLFF implementation gate.

## Purpose

This specification defines the production replacement for the historical
four-checkpoint screening default. The evaluator spends a small, equal fraction
of target and replay monitor labels on every saved epoch, progressively increases
fidelity for survivors, and performs final scientific selection only on complete
authoritative monitor data.

The implementation is split into two gates:

1. **EVAL-MF1** - deterministic nested monitor ladders, incremental prediction
   reuse, multi-round execution, full-fidelity finalist evaluation, and durable
   restart records.
2. **EVAL-MF2** - conservative statistical guard bands, ambiguity-driven expansion,
   comprehensive epoch reporting, exhaustive-comparison qualification, and
   migration to the production default.

## EVAL-MF1 implementation record

mdstats 0.20.106a0 implements the first gate as an opt-in campaign strategy. The
runtime uses the original authenticated complete monitor artifacts plus immutable
configuration-index ladders; it does not manufacture alternate mini-monitor source
files. Candidate predictions are persisted as immutable coverage shards keyed by
model/checkpoint identity, head, numerical contract, and ordered geometry identities.
A later cumulative round composes valid earlier shards and evaluates only missing
geometry identities. Dedicated partial-round records carry explicit fidelity/evidence
class and survivor records persist deterministic rank/outcome/reason data. Only the
100% round publishes the ordinary authoritative checkpoint-evaluation record.

The 0.20.106a0 EVAL-MF1 survivor rule was deliberately deterministic and simple.
EVAL-MF2 in 0.20.107a0 implements the statistical ambiguity/guard-band behavior below
and advances newly generated campaign TOML to `checkpoint_strategy = "multi_fidelity"`.
Legacy configs that omit the strategy continue to resolve to `bounded` for restart
compatibility.

## EVAL-MF2 implementation record

mdstats 0.20.107a0 implements conservative source/temporal-block survivor evidence and
comprehensive epoch reporting on top of EVAL-MF1. The default guard retains a candidate
when the paired mean primary-metric difference from the nominal cutoff is no larger than
a 2% relative allowance plus 2 standard errors over at least 4 common blocks. If fewer
blocks are available, only the deterministic 2% relative allowance is used. True-label
replay campaigns reserve provisionally replay-compatible candidates up to the minimum-
finalist floor, and a pairwise rank-inversion fraction >=25% expands the subsequent round
to at least 50% of current candidates. These numbers are explicit policy fields, not
hidden constants.

Every run receives normative JSON plus CSV/Markdown epoch-evaluation reports that combine
MACE training history with partial/full independent metrics, survivor reasons, final
admissibility, and selected status. A representative deterministic 30-checkpoint
qualification selects the same true-replay-admissible winner as exhaustive evaluation
while purchasing 10.89 rather than 30 full-checkpoint-equivalent candidate inference,
a 63.7% reduction for that case. Supplied MACE 0.3.16 restoration and monitor-graph cache
regressions separately qualify the real-model inference substrate.

## Binding invariants

1. Every saved candidate checkpoint enters round 1 unless it is already invalid
   by immutable checkpoint/catalog evidence (for example corrupt bytes).
2. A round fraction `f` applies to the same nominal fraction of the complete
   target monitor and the complete true-label replay monitor. Neither domain is
   intentionally assigned a higher evaluation fidelity.
3. Target and replay metrics remain separate; the implementation shall not pool
   them into a single RMSE merely for screening.
4. Subsets are deterministic, label-independent, stratified, and nested.
5. Later rounds infer only the delta not already authenticated in earlier rounds.
6. Partial-round metrics are screening evidence only.
7. Final checkpoint admissibility and selection require complete target data and,
   for replay-backed protocols, complete true-label replay data.
8. The existing frozen checkpoint metric/admissibility/selection policy remains
   authoritative in the full-fidelity round.
9. An incomplete or partially evaluated checkpoint is never represented as a
   scientifically rejected checkpoint.
10. Evaluation artifacts are campaign-owned; source monitor files remain read-only.

## Default ladder

The initial policy to qualify is:

| Round | Target fraction | Replay fraction | Nominal survivor action |
|---|---:|---:|---|
| 1 | 0.10 | 0.10 | EVAL-MF1: retain the nominal best one third subject to the minimum-finalist floor; EVAL-MF2 adds guard bands |
| 2 | 0.33 | 0.33 | EVAL-MF1: retain at least the configured finalist floor; EVAL-MF2 adds guard bands |
| 3 | 1.00 | 1.00 | full admissibility and deterministic selection |

Fractions and survivor controls are configurable execution policy. Integer and
stratum-minimum rounding may produce slightly different realized counts while
preserving the same nominal fraction on both monitor domains.

## Nested subset construction

For each monitor domain, build one immutable ordered configuration catalog before
candidate results are inspected. The order shall balance all frozen monitor strata
available to the evaluator, including condition axes and source/trajectory grouping.
Within a trajectory/source, temporally nearby frames shall not be treated as iid
samples when a decorrelated or block-aware ordering can be constructed from existing
partition evidence.

Round subsets are prefixes of the immutable order. Their identities bind the complete
monitor digest, ordered configuration identities, stratum policy, round fractions,
and realized sizes.

## Prediction persistence

Candidate prediction storage shall support authenticated incremental coverage. A
surviving checkpoint evaluated on round `r+1` predicts only configurations absent
from round `r`. Metric reduction reads the union of authenticated prediction shards.
A direct one-shot evaluation on the same complete subset must be numerically identical
within the existing precision tolerance.

Existing OPT-EVAL2 foundation prediction reuse and OPT-EVAL3 monitor graph/view caches
remain authoritative when identities match.

## Survivor ranking

EVAL-MF1 may use deterministic provisional ranking derived from the existing frozen
checkpoint policy, but partial threshold outcomes are not final admissibility records.
A nominal one-third survivor fraction is a resource target, not a hard scientific cap.

EVAL-MF2 implements paired, block-aware ambiguity handling. Because checkpoints are evaluated
on the same configurations, comparisons should use paired loss/error differences where
possible. Uncertainty estimation shall operate on trajectory/source or decorrelated
blocks rather than treating individual adjacent MD frames as independent samples.
Candidates statistically indistinguishable from a cutoff are retained. A detected
boundary-ranking inversion triggers deterministic expansion rather than forced pruning.

The production policy shall not claim a global-minimum guarantee over all saved epochs
unless all epochs receive full-monitor evaluation. It guarantees exact application of
the frozen selection policy among the full-fidelity finalists retained by the declared
screening policy.

## Restart records

Every round persists:

- round plan and subset identities;
- per-checkpoint authenticated prediction coverage;
- partial metrics with explicit fidelity tags;
- survivor/elimination ranking inputs and reasons;
- remaining inference deltas;
- final full-fidelity metric/admissibility records for finalists.

Restart shall reuse every valid prediction shard and recompute only missing/corrupt
deltas.

## Comprehensive epoch report

EVAL-MF2 produces a machine-readable and human-readable summary for every epoch,
including when available:

- MACE training-history target/replay metrics;
- independent target energy and force errors by round;
- focus-group and worst-condition metrics;
- replay candidate/baseline metrics and degradation;
- round fraction and realized monitor counts;
- survivor/elimination reason;
- final admissibility reason; and
- selected/nonselected status.

JSON is normative. CSV and plotting-ready outputs are convenience derivatives.

## Qualification

The production-default qualification completed in 0.20.107a0 demonstrates:

1. deterministic nested equal-fraction target/replay subsets;
2. label-independent subset construction;
3. all saved epochs in round 1;
4. exact incremental prediction reuse;
5. restart/corruption recovery;
6. no final scientific decision from partial metrics;
7. full target/replay evaluation of every finalist;
8. numerical identity against one-shot full evaluation of the same finalist;
9. conservative behavior under synthetic ranking inversions/noisy early subsets; and
10. representative comparison with exhaustive 30-checkpoint evaluation, recording both
    winner agreement and inference-cost reduction.

The current fixed `max_checkpoints_per_run` mode remains available as an explicit fast
or compatibility strategy. Exhaustive full-monitor evaluation remains available as an
audit/reference strategy.


### 0.20.107a0 qualification evidence

- representative exhaustive comparison: 30 saved checkpoints, exhaustive winner epoch 16,
  multi-fidelity winner epoch 16;
- nested candidate counts in that case: 30 -> 11 -> 8;
- incremental candidate-inference cost: 10.89 full-checkpoint equivalents versus 30
  exhaustive, or 63.7% less candidate inference;
- real-MACE qualification: supplied MACE 0.3.16 direct checkpoint restoration and
  persistent monitor-graph/cache regressions pass; and
- partial screening remains non-authoritative and acquires no checkpoint-deletion
  authority.

The measured reduction is case-specific and is not a universal performance guarantee.
