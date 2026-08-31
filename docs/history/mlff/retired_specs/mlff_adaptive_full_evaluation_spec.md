# MLFF ADAPT-EVAL1 adaptive top-K full-evaluation specification

Status: implemented in mdstats 0.20.126a0.

## Purpose

ADAPT-EVAL1 replaces the generated production EVAL-MF successive-halving workflow after
ADAPT-MON1/STOP1/RANK1 have already paid for fixed epoch-wise target/replay monitor metrics.
Production evaluation performs no 10% or 33% checkpoint rounds. It consumes exactly one
immutable lightweight champion from each independent run, purchases authoritative full
inference for a small campaign-wide finalist set, rejects hard failures before weighted
ranking, and expands the purchased set only when the current batch contains no admissible
model.

Historical `bounded`, `exhaustive`, and `multi_fidelity` evaluation strategies remain readable
and executable for pre-adaptive campaign evidence. New generated campaigns use
`checkpoint_strategy = "adaptive_topk"`.

## Inputs and immutable lineage

ADAPT-EVAL1 requires:

- a completed training-campaign plan;
- terminal ADAPT-STOP1 state for every considered run;
- reconciled ADAPT-RANK1 `lightweight_run_champion.json` evidence;
- the frozen checkpoint catalog for each champion;
- one identical common full target artifact across all adaptive DATA8 bundles;
- one independent full TRUE_DFT replay artifact;
- the binary learned-model precision identity (`single` or `double`); and
- the retained full-evaluation safety policy.

The finalist queue is content-addressed to the campaign, the run-local champion evidence, and
the scoring policy. Full candidate decisions are content-addressed to the corresponding
checkpoint evaluation record.

## Common full target domain

The 256-frame ADAPT-MON1 target monitor is a lightweight training/screening domain and must
not be relabeled as full evidence. DATA8 v3 therefore materializes the complete DATA5
`outer_monitor` domain once as:

```text
shared/target/full_target_evaluation.xyz
```

with role `common_full_target_evaluation`. The 256-frame online monitor must be a subset of
this domain. All adaptive bundles competing in one campaign must expose identical full-target
membership and content identity.

## Common full replay domain

Authoritative replay evaluation uses the complete configured independent TRUE_DFT replay monitor
domain resolved from `[paths].replay_true_labels` and the frozen replay-monitor lineage. The
512-frame online replay monitor remains a lightweight fixed trend monitor; it is not substituted for
full replay evidence. This domain is the authoritative true-label replay validation/monitor split, not
the replay-training corpus.

Both naive fine-tuning and multi-head replay candidates are evaluated on the same true-replay
domain. A multi-head model uses its replay head. A naive model has no replay head, so its target
head is evaluated on the replay structures. This gives one physically comparable replay force
RMSE across training methods.

## Lightweight cross-method comparability

The campaign finalist queue is meaningful only if ADAPT-RANK1 scores have the same target/replay
semantics for every training method. Multi-head replay obtains its replay validation row from the
normal `pt_head` loader. Naive fine-tuning receives the same fixed 512-frame TRUE_DFT replay
monitor as an auxiliary validation-only loader evaluated through its target head.

The auxiliary loader:

- contributes no gradients;
- does not add a trainable head;
- is inserted before the ordinary target loader, preserving MACE 0.3.16's historical
  last-validation-loader checkpoint/patience scalar as target-driven; and
- supplies the replay metric consumed by ADAPT-STOP1 and ADAPT-RANK1.

Thus all new adaptive runs rank by the same weighted target/true-replay force objective.

## Finalist queue

For one champion per independent run, order candidates by the frozen lightweight score and its
existing deterministic tie-breakers. Initially purchase full evaluation for at most:

```toml
[evaluation]
finalist_count = 5
```

If fewer than five champions exist, evaluate all of them.

The queue is fixed before authoritative inference begins; full-evaluation results do not reorder
or mutate the queue.

## Authoritative full score

For target force RMSE `T_full` and true-replay force RMSE `R_full`, define:

$$
S_{\rm full}
=
\frac{w_T T_{\rm full}+w_R R_{\rm full}}{w_T+w_R}.
$$

The default score weights are 1:1.

The replay hard ceiling remains coupled to the target threshold and score weights:

$$
R_{\max}=\frac{w_T}{w_R}T_{\max}.
$$

With the default `T_max = 0.030 eV/A` and 1:1 weights, both target and replay hard ceilings are
30 meV/A.

## Hard acceptance before ranking

A candidate is fully admissible only after it satisfies:

1. `T_full <= T_max`;
2. `R_full <= R_max`;
3. retained target energy-MAE safety limits;
4. retained focus/mobile-ion force-RMSE safety limits;
5. retained stress-RMSE safety limits;
6. retained worst-condition force-RMSE safety limits; and
7. required finite/complete metric evidence.

The weighted score is never allowed to compensate for a hard failure.

The historical foundation-relative replay degradation remains recorded as:

- foundation true-replay force RMSE;
- candidate minus foundation absolute degradation; and
- fractional degradation when the foundation baseline is positive.

It is diagnostic under the new default selector and is not the hard replay acceptance gate.

## Rescue batching

If no candidate in the first purchased batch is admissible, purchase the next unevaluated
champions in deterministic batches of:

```toml
[evaluation]
finalist_rescue_batch_size = 5
```

Continue only until:

- at least one purchased candidate is fully admissible; or
- the champion pool is exhausted.

Once a purchased batch produces an admissible candidate, production full evaluation stops. An
exhaustive historical/reference evaluator may still be used explicitly for research, but it is
not the generated adaptive production strategy.

## Precision contract

The learned-model dtype is never normalized across finalists:

```text
single -> FP32 model inference
double -> FP64 model inference
```

An FP32 checkpoint is not promoted to FP64 for evaluation, reconstruction, or export. mdstats
converts model outputs to FP64 for SSE/RMSE accumulation, retained safety metrics, replay
diagnostics, and weighted score calculation.

## Restart and cache semantics

Full predictions are reusable only when all relevant identities match, including:

- run and checkpoint identity;
- evaluation policy identity;
- binary model dtype;
- common full target artifact identity and SHA-256;
- common full replay artifact identity and SHA-256; and
- reconstructed model/checkpoint lineage.

Interrupted evaluation resumes from authenticated completed predictions. It never repeats a
completed finalist merely to rebuild aggregate evidence, and it never changes the frozen queue.

## Outputs

ADAPT-EVAL1 persists:

- `CampaignFinalistQueueRecord`;
- one authoritative `CheckpointEvaluationRecord` per purchased finalist;
- one `FullEvaluationCandidateRecord` per purchased finalist;
- one aggregate `AdaptiveFullEvaluationRecord`; and
- `results/adaptive-full-evaluation.json` for a complete campaign.

The aggregate result orders the fully admissible candidates by full score, but ADAPT-EVAL1 does
not perform deployment verification, fallback after verification failure, or final export. Those
responsibilities remain ADAPT-VERIFY1.

## Acceptance tests

ADAPT-EVAL1 is complete only when tests prove:

1. generated campaigns default to `adaptive_topk` and purchase no EVAL-MF partial rounds;
2. the initial queue contains at most five one-per-run champions;
3. rescue proceeds in batches of five only when no purchased candidate is admissible;
4. the 256-frame target online monitor is a subset of a separately materialized common full target domain;
5. the full true-replay domain is independent of the 512-frame online replay monitor;
6. naive and replay-trained runs expose comparable target+true-replay lightweight scores;
7. hard target/replay and retained safety gates execute before full-score ranking;
8. the old foundation-relative replay degradation is diagnostic rather than the default hard selector;
9. `single` and `double` preserve their own model inference dtype with FP64 scientific reductions;
10. interruption/restart reuses authenticated completed predictions; and
11. historical EVAL-MF policies remain readable and directly testable without remaining the generated default.
