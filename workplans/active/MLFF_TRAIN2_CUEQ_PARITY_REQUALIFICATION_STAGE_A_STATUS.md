---
kind: stage-status
protocol_version: 6.4.0
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
stage: A
status: passed-ready-for-stage-b
date: 2026-09-24
branch: design/mlff-train2-cueq-parity-requalification
repository_review_head: 872d35d0f905ae5adf16a6ecf5c82fdd5f28375b
workplan_semantic_review_candidate: 293bc8e3fcdb0cdda6a22608d2a280fdd7a97ab4
accepted_d1_d2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_d1_d2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
---

# MLFF TRAIN2 CuEq parity requalification — Stage A status

## Disposition

**PARTIAL / NOT YET THROUGH GATE A.**

The repository-side authority, currentness, implementation, and historical-evidence reconstruction required by Stage A is now sufficiently closed to identify the exact remaining evidence dependency. Gate A has now received and authenticated the durable target-host CampaignStore snapshot from the observed MACE-MH-1 / `omat_pbe` RTX 3090 failure. The bounded fresh-process/order diagnostic has now been executed and analyzed for both MH-1 and MPA-0 under the same frozen 20-process 2x2 design. The cross-family evidence confirms a common stochastic structure with strongly family-dependent absolute scale, so the current single-process all-pairs reducer and fixed stable-channel floor are not adequate generic D2 semantics. The Stage-A evidence obligations are complete. Gate A is PASS and Stage B may now freeze a bounded D2 candidate before any fresh Stage-C acceptance realization.

The console transcript is discovery evidence only. It is not promoted into durable numerical qualification evidence.

## A1. Accepted authority result

The accepted Protocol-6.4 parent remains:

- accepted D1/D2 kernel commit: `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`;
- exact imported stakeholder-ratified source target: `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

Direct source inspection performed during workplan review established that the accepted D2 source contains no CuEq-specific FP32/FP64 acceleration-equivalence relation. The historical Rev83-86 parity specifications and current D4 implementation are therefore executable guards/evidence, not accepted D2 numerical authority.

No D1 change is presently indicated. The accepted D2 equivalence registry is broad enough to host a bounded acceleration-equivalence family once its definitions, applicability and evidence are supplied.

## A2. Current executable TRAIN2 FP32 relation

Current D4 implements `TrainingAccelerationNoiseNormalizedParityPolicy` with:

- one discarded warm-up per backend;
- ten post-warm-up evaluations per backend;
- all-pairs comparison: 45 e3nn-self, 45 CuEq-self, 100 cross;
- fixed `stable_channel_abs_ceiling = 1e-6` for energy, stress and descriptor maxima;
- force statistics `Frmse`, `Fp99`, `Fp99.9` reduced with NumPy percentile q=99 and compared as cross/self-envelope ratios;
- `force_distribution_ratio_ceiling = 1.25`;
- catastrophic `Fmax` limit `min(1e-4, 1.5 * self_Fmax_envelope)`;
- exact selection identity across all self and cross comparisons.

The implementation uses all-pairs observations derived from ten backend evaluations. The 45/45/100 pair values are therefore dependent contrasts, not independent experimental units. The D2 replacement must define whether these are merely a deterministic finite-sample functional or support a population/noise inference, and it must not use pair cardinality as IID sample size.

## A3. Currentness graph — confirmed D3/D4 defects

### Source-side realization

`AccelerationRealizationRecord` binds:

- source backend / resolved inference and training kernel modes;
- device and dtype;
- foundation inference identity;
- MACE/CuEq/OEq versions;
- inference/training parity **record digests**;
- historical `qualified` state.

Its parity records bind their own policy digests. However, `_stored_acceleration_realization(..., require_qualified=True)` loads the realization and checks only requested backend, device/dtype and historical `qualified` state. It does not fetch/authenticate the bound parity record against the **current** accepted parity method/policy.

Consequential source-side consumers can therefore reuse a historical realization after a parity-method change unless another incidental stage fence happens to block the path. Currentness must be enforced at the realization-use owner rather than relying on call ordering.

### TRAIN2 realization

`TrainingAccelerationRealizationRecord` binds:

- requested TRAIN2 backend and kernel mode;
- device/dtype;
- exact selected training checkpoint SHA;
- selected-head qualification digest;
- dependency versions;
- training parity record digest;
- historical `qualified` state.

`_stored_training_acceleration_realization(..., require_qualified=True)` checks backend, device/dtype, checkpoint bytes and historical qualification, but not current parity-method ancestry.

This is consequential: `_optimizer_policy(...)` directly embeds the loaded realization's `content_digest` as `MaceOptimizerPolicy.acceleration_realization_digest` and its kernel mode as `resolved_acceleration_kernel_mode`. A stale qualified realization can therefore enter current TRAIN2 method identity rather than remaining harmless archived evidence.

No second realization registry is needed. The existing parity-policy -> parity-record -> realization chain is already sufficient to enforce currentness once the accepted D2/D3 policy identity is explicit.

## A4. TRAIN2 -> EVAL2 model-state / representation result

Current checkpoint authentication intentionally uses two representations:

```text
TRAIN2 checkpoint
 -> reconstruct transient training realization
 -> authenticate/load exact live or EMA state in that realization
 -> dependency-native CuEq -> e3nn state transfer
 -> canonical portable e3nn provider
 -> EVAL2 forward
```

The accepted prior recurrence repair supplies strong D3/D4 evidence for architecture reconstruction, native state transfer, arbitrary perturbed trained-state transfer, and bounded portable-vs-CuEq forward parity.

It does **not** supply accepted D2 authority for transporting a starting-checkpoint doctor relation across every optimizer-reachable model state.

A separate current D4 provenance defect is confirmed: `campaign_post_selection_runtime._checkpoint_provider_realization()` records the TRAIN2 backend (normally `cueq`) in EVAL2 `EvaluationMeasurementIdentity`, while the actual native EVAL2 provider returned after authenticated projection is portable `e3nn`. Repair belongs at the existing measurement-identity owner; transient CuEq checkpoint authentication remains unchanged.

The current content-addressed measurement identity is sufficient for cutover: corrected EVAL2 measurements/assessments become stale and are recomputed. Otherwise-authenticated TRAIN2 roots do not need retraining solely because the old assessment identity mislabeled the forward representation.

## A5. Historical evidence classification

### MPA-0

Repository search found:

- Rev84/85/86 prose summaries;
- historical parity specification prose;
- release source patches repeating those summaries;
- unit-test constants constructed from the published MPA-0 values.

No raw MPA-0 CampaignStore DIAG3/repeatability/parity realization artifact was found.

Therefore the historically quoted MPA-0 values — including approximately `1.08/1.02/0.90` p99 force ratios and `Fmax 2.261e-5 / 2.337e-5` — are **secondary evidence**. They may motivate hypotheses and regression fixtures but cannot serve as the sole raw numerical basis of a newly generic D2 relation.

If the new relation claims generic MPA-0/MH-1 scope, obtain a fresh raw MPA-0 target-host realization under the frozen candidate method/runtime.

### MH-1 target-host failure

The supplied console log is consistent with a current Rev86-style failed doctor and is adequate to trigger the Serious Challenge. It is not yet durable Stage-A evidence because this review environment has no access to the campaign workspace / CampaignStore that produced it.

## A6. Exact target-host evidence snapshot — no new product machinery

The existing `CampaignStore` already provides read-only record enumeration, digest retrieval and payload decoding. Do not add an export subsystem.

On the **same failed campaign workspace, before rerunning doctor**, run from the mdstats source/runtime that produced the failure:

```bash
python - <<'PY'
from pathlib import Path
import hashlib
import json

from mdstats.training_data import _campaign_cli_core as cli

config = Path("campaign.toml").resolve()
cfg, paths = cli._load_config(config)
store = cli.CampaignStore(paths.state_db, create=False)

wanted = (
    "doctor",
    "mace_runtime_freeze",
    "selected_head_qualification",
    "acceleration_policy",
    "acceleration_probe",
    "acceleration_parity",
    "acceleration_training_parity",
    "acceleration_realization",
    "training_acceleration_policy",
    "training_acceleration_parity_policy",
    "training_acceleration_noise_normalized_parity_policy",
    "training_acceleration_repeatability_diagnostic",
    "training_acceleration_noise_normalized_parity",
    "training_acceleration_parity",
    "training_acceleration_realization",
)

try:
    records = {}
    for key in wanted:
        if store.has_record(key):
            records[key] = {
                "record_digest": store.record_digest(key),
                "payload": store.get_payload(key),
            }

    doctor_state, doctor_message = store.stage("doctor")
    payload = {
        "schema": "mdstats.stage-a-cueq-parity-evidence-snapshot.v1",
        "config_path": str(config),
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "state_db_path": str(paths.state_db.resolve()),
        "doctor_stage": {
            "state": doctor_state.value,
            "message": doctor_message,
        },
        "doctor_stage_config_digest": store.get_meta(cli._stage_config_key("doctor")),
        "record_keys": list(store.record_keys()),
        "records": records,
    }
finally:
    store.close()

out = Path("mlff_train2_cueq_parity_stage_a_snapshot.json").resolve()
out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(out)
PY
```

This command is observational: `CampaignStore(create=False)` uses SQLite read-only mode and no campaign record is mutated.

The snapshot should be preserved before any rerun because a later doctor invocation may replace current aliases with a new realization.

## A7. Imported MH-1 evidence authentication

The user-supplied snapshot has SHA-256:

`ef0e4d8c2d0b867294a97b86769a1e1fd709c1af9e35d1a1c7730bb936a6dd83`.

All content-addressed records and policy digests checked from the snapshot recompute exactly under mdstats canonical JSON hashing. In particular:

- repeatability diagnostic: `66be5bdcc4e660067d6c7801a1fb3083ff634f21a48e919a6fb1199c2d9dedfa`;
- authorizing noise-normalized parity record: `7dc24d6f0201d34258cfbbfe15c507fb648a2c00b07aff57a6ed202f456c810f`;
- selected-head qualification: `66867d6b08fc8af279c2f5e449168afa148d2f43aaa6fd745ae4524025c62244`;
- failed TRAIN2 realization: `9767ce3f3816deb1e19bfed330877401735380c3051db7324529f1e33ab7430b`;
- TRAIN2 noise-normalized policy: `1faf33e781142ff0656cc6a49235294858dfe5dc7639c08e7a5e0f1fc73ed0d5`.

The selected-head checkpoint is bound to SHA-256 `61c83c377dae92bf37c5412a263687237fbc4b9790828868ec0887cc992be928`, the requested TRAIN2 realization is `cueq_pure` / FP32 / CUDA, and the runtime evidence binds MACE 0.3.16, Torch 2.13.0+cu126, CUDA 12.6, CuEq 0.10.0 and the RTX 3090. The MACE calculator source-byte mismatch is explicitly covered by the stored semantic source-compatibility pass.

The snapshot therefore satisfies the Stage-A provenance/authentication obligation. Its console-derived failure is reproduced exactly by the stored authorizing record.

## A8. Evidence-derived numerical findings

Detailed calculations are recorded in:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_STAGE_A_EVIDENCE_ANALYSIS.md`.

The decisive results are:

1. the `1e-6` absolute descriptor ceiling is below ordinary same-backend descriptor variability in both backends;
2. the force-tail ratio classification is unstable under bounded leave-one/leave-two realization sensitivity at only ten retained runs;
3. per-pair `Fp99.9` on only 45 force components is effectively an extreme/max statistic and is almost redundant with `Fmax`;
4. same-index cross pairs and all-pairs cross comparisons lead to materially different tail ratios under the current fixed e3nn->CuEq evaluation order, so process/order covariance is not negligible;
5. complete force-RMSE distance geometry shows similar e3nn/CuEq within-backend spread plus a small systematic backend-centroid separation, which the current tail-ratio rule does not distinguish from stochastic spread;
6. energy, stress, selection identity and the `1e-5` force-component catastrophic guard do not show a material failure in this realization.

These findings strengthen the Serious Challenge but do not yet select a replacement criterion.

## A9. Fresh-process/order diagnostic result

The user-supplied diagnostic artifact

`mlff_train2_cueq_stage_a_order_process_diagnostic.json`

has raw-file SHA-256

`8f9df123b2ca5b055a7f1a82b3c819263021da52b005904af2f3f5df21acc056`

and self-declared canonical content digest

`880261c2eabd33beeadcefe54eefea01e6acdc3d94e574c657dd3bee78cf570a`.

The aggregate canonical digest and all 20 per-process content digests recompute exactly. The artifact binds:

- repository head `5d2df62f82c70615cbe16aaa4600b4140e80f1c2` with no dirty paths;
- one campaign/config identity;
- one selected-head checkpoint SHA;
- one deterministic three-structure corpus SHA;
- 20 fresh processes in a balanced 2x2 design;
- five processes per construction/evaluation-order cell;
- one discarded warm-up pair and three retained paired evaluations per process;
- ordinary nondeterministic production settings on the RTX 3090.

Detailed analysis is recorded in:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_STAGE_A_ORDER_PROCESS_DIAGNOSTIC_ANALYSIS.md`.

The decisive force result is:

- e3nn fresh-process radius: `1.5945e-7`;
- CuEq fresh-process radius: `1.6520e-7`;
- backend centroid separation: `9.5935e-8`;
- centroid separation / pooled process radius: `0.591`.

Thus the backend-centered component is real but smaller than ordinary fresh-process variation.

For the signed process-level force-difference field, centered variation partitions approximately as:

- construction order: 5.41%;
- evaluation order: 4.96%;
- construction/evaluation interaction: 5.23%;
- replicate-block/time state: 20.63%;
- remaining process variation: 63.77%.

The four cell-mean force-difference directions have pairwise cosines only about `0.29-0.44`. The backend offset therefore is not a single stable direction independent of execution conditions.

The scalar paired force RMSE remains microscopic (grand mean `4.002e-7`). Its strongest designed effect is the construction/evaluation interaction: cells where construction-first and evaluation-first backend agree have mean RMSE about `4.09-4.13e-7`, while crossed-order cells are about `3.87-3.92e-7`. There is no comparable standalone evaluation-order main effect.

Descriptor evidence differs from force: the descriptor centroid separation is `4.481e-8` versus process radii `3.944e-8` (e3nn) and `3.851e-8` (CuEq), so a systematic descriptor representation shift exists. Nevertheless the three-structure inter-descriptor distance ordering is identical across all 20 process-mean realizations for both backends. This reinforces that the current raw absolute descriptor maximum is the wrong semantic object, while downstream decision robustness remains the relevant question.

No decisive monotonic drift across the three retained pair positions was found. The diagnostic therefore does not justify increasing warm-up count merely to make the result pass.

## A10. MPA-0 cross-family evidence result

The user-supplied MPA-0 artifact

`mlff_train2_cueq_stage_a_mpa0_order_process_diagnostic.json`

has raw-file SHA-256

`b3f08aeab0118d03364e1c33c3a9665c4a93c78a11d01c540a333bc50782f3be`

and canonical content digest

`f2bca742e8215bffb7299eef6f13e6d1378de3298e2c40760a4e70e66e7bea5d`.

The aggregate canonical digest and all 20 child-process digests recompute exactly. The artifact binds the locked MACE-MPA-0-medium checkpoint SHA-256

`75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`

and repeats the same frozen three-structure corpus, GPU, FP32 dtype, 2x2 construction/evaluation-order design, 5 processes/cell, one warm-up, three retained pairs, no early stopping, and clean mdstats source head used for the MH-1 diagnostic.

Detailed analysis is recorded in:

`workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_STAGE_A_MPA0_DIAGNOSTIC_ANALYSIS.md`.

Cross-family force comparison:

| quantity | MH-1 | MPA-0 | MPA-0 / MH-1 |
| --- | ---: | ---: | ---: |
| e3nn fresh-process radius | 1.5945e-7 | 9.0134e-7 | 5.65 |
| CuEq fresh-process radius | 1.6520e-7 | 9.1972e-7 | 5.57 |
| backend centroid separation | 9.5935e-8 | 3.8643e-7 | 4.03 |
| paired force RMS discrepancy | 4.0393e-7 | 2.2614e-6 | 5.60 |
| centroid separation / pooled process radius | 0.591 | 0.424 | — |

The absolute force scale is therefore strongly model-family dependent, while the normalized systematic backend component is sub-unity in both families.

The hierarchical squared-discrepancy decomposition is also similar:

- MH-1 force paired discrepancy variance: 5.64% stable backend centroid, 34.40% process-level differential state, 59.96% within-process differential state;
- MPA-0: 2.92% stable backend centroid, 35.28% process-level differential state, 61.80% within-process differential state.

The paired-force RMS divided by pooled fresh-process radius is about 2.46 for MH-1 and 2.44 for MPA-0. With three retained observations per process this is close to `sqrt(6)`, consistent with the dominant paired discrepancy arising from realization-level stochastic arithmetic rather than a family-specific deterministic CuEq offset.

The factorial force decomposition is likewise cross-family consistent:

| source | MH-1 | MPA-0 |
| --- | ---: | ---: |
| construction order | 5.41% | 6.88% |
| evaluation order | 4.96% | 5.53% |
| interaction | 5.23% | 8.25% |
| replicate/time block | 20.63% | 16.86% |
| residual process variation | 63.77% | 62.48% |

This supports one family-generic stochastic **structure**, not one family-independent absolute error scale.

MPA-0 also falsifies the generic fixed `1e-6` stable-channel interpretation beyond descriptors:

- CuEq-self energy pair maxima exceed `1e-6` in 5/60 within-process self pairs;
- cross-backend energy maxima exceed `1e-6` in 25/180 within-process cross pairs;
- the cross and CuEq-self energy extrema share the same FP32-scale quantized levels, so the absolute ceiling does not distinguish backend disagreement from ordinary realization variability.

Stress remains below `1e-6` in all observed self/cross pairs.

MPA-0 force components above `1e-5` occur in e3nn-self (2/2700), CuEq-self (2/2700), cross (5/8100), and paired cross (3/2700) comparisons. Therefore `1e-5` component exceedance is not a valid standalone backend-failure predicate; it may remain diagnostic or participate only in a repeatability-aware catastrophic guard.

Descriptor behavior is again semantically different from physical outputs. MPA-0 descriptor backend-centroid separation is `4.1138e-8`, with process radii about `1.70e-8`, so the latent-coordinate shift is more systematic than in MH-1. Nevertheless the complete three-structure inter-descriptor distance ordering is identical between e3nn and CuEq in all 20 same-process comparisons. This reinforces that descriptor **geometry/decision preservation** is the governed quantity, not an arbitrary raw coordinate maximum.

### Gate-A disposition

**PASS.**

The required raw MH-1 and MPA-0 target-host realizations now exist under one frozen diagnostic design. They establish enough evidence to formulate a generic D2 candidate without inventing family-specific thresholds:

1. absolute FP32 discrepancy scales are model-family dependent;
2. stochastic decomposition structure is reproducibly similar across families;
3. fixed stable-channel absolute floors are not generic repeatability semantics;
4. single-process all-pairs tail ratios confound process/order state, stochastic spread, systematic backend shift and extreme-order statistics;
5. descriptor latent coordinates require downstream geometry/decision semantics rather than raw-coordinate tolerance;
6. fresh Stage-C realizations remain required after the Stage-B candidate is frozen.

No current CuEq realization is authorized by this Gate-A pass; the existing doctor remains fail-closed until Gate C and downstream D3/D4 closure.

## A11. Repository-side Stage-A result

Repository-side Stage A plus fresh MH-1 and MPA-0 target-host diagnostics are complete. No additional architecture search or new runtime subsystem is justified before Stage B. The next owner is D2: freeze a source-closed candidate relation, then subject that immutable candidate to fresh independent Stage-C falsification.

The likely next numerical-design focus, once raw arrays are available, is:

- descriptor equivalence relative to measured same-backend variability rather than the current unjustified shared absolute floor;
- force-tail estimation under dependent all-pairs contrasts and unequal self/cross pair cardinalities;
- exact finite-sample/quantile semantics;
- model-state applicability of the accepted relation.

Those are hypotheses for Stage B/C, not accepted fixes.
