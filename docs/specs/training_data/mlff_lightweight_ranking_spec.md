# MLFF ADAPT-RANK1 lightweight run-champion specification

Status: implemented in mdstats 0.20.125a0 (`ADAPT-RANK1`)

## Scope

ADAPT-RANK1 converts the already-paid ADAPT-STOP1 epoch monitor history into one deterministic
run-local lightweight champion. It launches no MACE inference, does not deserialize checkpoint
models, and does not replace authoritative full evaluation. Campaign-wide top-K finalist selection
belongs to ADAPT-EVAL1.

## Inputs and lineage

A new adaptive run must provide all of the following immutable evidence:

- terminal `adaptive_training_stop.json` evidence;
- the frozen `CandidateCheckpointCatalog` already created at successful training completion;
- the ADAPT-STOP1 policy digest and score weights;
- the common ADAPT-MON1 online-monitor policy digest;
- the exact common target-online-monitor record digest; and
- the exact common true-replay-online-monitor record digest.

The stop-state epoch set and checkpoint-catalog epoch set must match exactly. Ranking is refused if
candidate eligibility recomputed from the frozen policy disagrees with the eligibility bit stored by
ADAPT-STOP1. This prevents stale or manually edited stop evidence from being silently ranked.

## Admissible region

An epoch can enter the ranking only when ADAPT-STOP1's hard candidate boundaries both pass:

$$
T_{\rm mon}\le T_{\max}
$$

and, for replay-enabled training,

$$
R_{\rm mon}\le R_{\max},\qquad
R_{\max}=\frac{w_T}{w_R}T_{\max}.
$$

The weighted score never compensates for a failed hard boundary.

## Lightweight score

For replay-enabled training,

$$
S_{\rm light}=\frac{w_TT_{\rm mon}+w_RR_{\rm mon}}{w_T+w_R}.
$$

The low-level historical policy can still represent a target-only record with `S_light = T_mon`. New adaptive production campaigns, including naive fine-tuning, supply the fixed TRUE_DFT replay monitor so cross-run screening uses the target+replay score. The default 1:1 replay policy is therefore the simple
arithmetic mean of target and replay force RMSE.

All score arithmetic uses ordinary Python/NumPy double-precision scalar semantics after MACE
inference. A sub-femtoscale canonicalization of the score is used only in the ranking key so two
mathematically identical decimal weighted averages cannot be misordered by binary representation
noise. This tolerance is many orders of magnitude below any campaign scientific threshold.

## Deterministic ranking

Eligible checkpoints are ordered by:

1. lower weighted score;
2. lower target force RMSE;
3. lower replay force RMSE when replay is enabled;
4. earlier epoch; and
5. stable checkpoint SHA-256 identity.

The rank-one eligible checkpoint is the run champion. Adjacent epochs from one training trajectory
therefore cannot occupy multiple campaign finalist slots once ADAPT-EVAL1 consumes one champion per
run.

A run with no eligible epoch receives an explicit
`no_lightweight_admissible_checkpoint` ranking record with no selected checkpoint. No fallback to
the final epoch is permitted.

## Durable artifact

Each adaptive run owns:

```text
lightweight_run_champion.json
```

The record binds:

- run-plan digest;
- training-protocol digest;
- ADAPT-STOP1 policy and state digests;
- checkpoint-catalog digest;
- common target/replay monitor identities;
- every eligible checkpoint in deterministic ranking order;
- selected checkpoint epoch/SHA and weighted score, when one exists; and
- explicit ranking outcome.

A later full-evaluation rejection never rewrites this artifact because it records a training-time
screening fact, not final scientific acceptance.

## Zero-new-inference and restart contract

`rank_lightweight_run_champion(...)` accepts frozen Python evidence objects, not checkpoint paths.
The catalog root may be unavailable and ranking must still succeed. Reconciliation regenerates the
same record from persisted STOP1 state plus the persisted catalog without opening or deserializing
model checkpoints.

If `lightweight_run_champion.json` already exists, mdstats derives the expected record again and
requires the content digest to match exactly. Mismatched or malformed ranking evidence fails closed.
This also allows a parent interrupted after training completion but before the ranking record was
committed to reconstruct the record without inference.

## Gate boundary

ADAPT-RANK1 does **not**:

- choose the campaign-wide top five;
- launch target/replay full evaluation;
- retire EVAL-MF runtime behavior; or
- select the final verified production model.

Those responsibilities remain ADAPT-EVAL1 and ADAPT-VERIFY1. In mdstats 0.20.125a0, the current
ADAPT-EVAL1 is runtime-authoritative for new generated adaptive campaigns as of 0.20.126a0; historical EVAL-MF remains readable/selectable. Each completed adaptive run has
one frozen lightweight champion.


## MLCV-RANK1 supersession (`mdstats 0.20.134a0`)

For new MLCV campaigns the historical one-champion interpretation above is superseded by a run-local top-K checkpoint-selection staging contract. Every checkpoint with complete finite lightweight target/replay metrics is rankable, regardless of whether the lightweight value lies above the future 30 meV/A full-validation criterion. No outer CV fold and no full final-validation `D` is queried here.

Checkpoints are ordered by the same deterministic score/tie-break sequence, but only the best five (or fewer when fewer exist) are retained. New schema v2 records also persist the total pre-truncation rankable checkpoint count and candidate limit. The historical rank-one fields remain temporarily populated only so ADAPT-EVAL1 can operate until MLCV-SELECT1 replaces it; they do not constitute the final representative.

The corresponding STOP1 boundaries are derived from full criteria: `T_stop=f_T*T_full_max`, `R_full_max=(w_T/w_R)*T_full_max`, and `R_stop=f_R*R_full_max`. Generated defaults remain `f_T=0.80` and `f_R=1.20`, but both factors are TOML-configurable and do not modify the full-validation acceptance ceilings.
