## 0.20.215a0 - CUEQ-DEFAULT1-HF2

TRAIN2 FP32 e3nn/pure-CuEq numerical parity now uses the fixed backend-equivalence envelope `rtol=1e-5, atol=1e-5`. The generic source/DATA6 FP32 authority remains `rtol=1e-5, atol=1e-6`, FP64 remains unchanged, and no scientific convergence/model-quality tolerance is modified. FINAL-GPU1 remains v3/18 items; preflight v9 binds the exact TRAIN2 parity-policy digest.

## 0.20.214a0 - REPLAY-UNIFY1E

The single-source replay migration is complete. The executable invalidation planner freezes minimal cache invalidation, identical-byte relocation avoids source reparse, and FINAL-GPU1 v3 adds a release-blocking replay pseudo-label GPU execution gate. Positive GPU qualification remains pending the regenerated workstation bundle.

# mdstats

## MLFF replay-evaluation semantics

Checkpoint accuracy is judged against independent DFT labels. Foundation-generated replay pseudolabels remain the default replay training targets and an absolute behavioral-drift diagnostic. Set `[paths].replay_true_labels` to the original true-label replay directory so mdstats can evaluate both the foundation and fine-tuned checkpoint on the same target and replay geometries without changing training inputs.

Current development release: **0.20.242a0**. New MLFF campaigns use one fixed target-size authority: `FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2/MVSTATE2 -> MVQUAL2 -> Q -> 3/10/30 TargetSizeStudyPolicy -> selected REPAIR2 prefix -> held-out CV/EVAL/VERIFY`. The only candidate sizes are `128, 256, 512, 1024, 2048, 4096, 8192, 16384`; MVQUAL2 is the sole hard size-eligibility authority; `q < 3` terminates without rescue; and the selected size is immutable before held-out validation. Legacy target ladders, SIZE-HALVE2, SIZE-FIDELITY2, MVMIGRATE1, migration activation, generated rescue sizes, and downstream Stage-B/Stage-C size advancement are historical only and are not current campaign prerequisites. GPU qualification remains deferred to the final release package and does not gate this architecture.

## Target-size v5 redesign

Target-size candidate membership is always the exact REPAIR2 prefix `R[:N]`. Qualified candidates continue along the same authenticated TRAIN2 trajectory at epochs 3, 10, and 30, preserving checkpoint, optimizer, RNG, schedule, and candidate-data lineage. The funnel is `q -> min(q,4) -> 2 -> 1`, including the required `q=3 -> 3 -> 2 -> 1` case. If 16384 remains materially superior at the final boundary, the study terminates as `nonconverged_at_fixed_ceiling`; it never synthesizes a larger or intermediate rescue size. Production target-corpus materialization promotes only the selected prefix.


## Historical MLFF release notes

The sections below describe earlier releases and are retained for change lineage; they do not override the current target-size-v5 architecture above.

## REPLAY-UNIFY1C in 0.20.212a0

`mdstats 0.20.212a0` adds the reusable foundation-prediction layer for the single replay source. Scientific prediction identity binds the exact foundation checkpoint/head and frozen inference/runtime identity but excludes batch and shard tuning. Bounded ragged prediction shards are paired with a compact authenticated scalar audit sidecar, so replay qualification and threshold-only reclassification require zero model calls and avoid loading force payloads. Pseudo-label train/monitor ExtXYZ views are generated lazily from the immutable qualification/split authority; authenticated views restart without source parsing, while deleted views reconstruct from cached predictions without reinference. Real MACE/CUDA/CuEq replay inference remains deferred to the regenerated FINAL-GPU1 bundle after REPLAY-UNIFY1E.

## REPLAY-UNIFY1B in 0.20.211a0

`mdstats 0.20.211a0` adds an order-independent source-true-label cache and lazy true-label train/monitor materialization over the single replay source. Source truth remains a separate logical namespace and is projected to MACE `REF_*` fields only at the transport boundary. Missing views reconstruct deterministically, dual-role cold generation uses one bounded source pass, and same-geometry/different-label cache masquerading fails closed.

## REPLAY-UNIFY1A in 0.20.210a0

`mdstats 0.20.210a0` freezes the single-source replay migration before positive FINAL-GPU1 execution and implements its additive authority/schema gate. New replay-source records use a versioned 1e-8 Angstrom canonical geometry identity, one streamed selected replay corpus, and deterministic seeded split manifests with default 5:1 membership (12,000 -> 10,000/2,000). Source true labels and future foundation pseudo-labels are separate namespaces. Historical split-file campaigns remain live and readable until the later campaign-integration gate. Because the replay interface will change before release qualification, the 0.20.209a0 workstation bundle is archival and will be regenerated after REPLAY-UNIFY1E.

## FINAL-GPU1 v2 in 0.20.209a0

`mdstats 0.20.209a0` completes the release-side control plane for the one-shot GPU qualification. FINAL-GPU1 v2 requires typed, content-addressed SIZE-FIDELITY2 and legacy-vs-MV learning-control evidence in addition to the existing accelerator/scientific matrix, and supplies dedicated assemblers for both. A pass can then be consumed by an explicit dry-run/`--apply` MVMIGRATE1 transaction that atomically preserves v4 and promotes the fixed-eight v5 ladder plus v3 convergence authority. No GPU pass is embedded in the release; v4/v2/v2 remains live until the final workstation evidence passes.

## TARGET-DATA2C-MVMIGRATE1 in 0.20.208a0

`mdstats 0.20.208a0` implements the atomic migration latch from the historical dynamic-rescue target ladder to the exact sparse multi-view fixed-eight generation. The candidate TARGET-DATA2C v5 ladder uses only REPAIR1 master-order prefixes at 128, 256, 512, 1024, 2048, 4096, 8192, and 16384, independently reconstructs TARGET-DATA2B coverage/DATA2A hard obligations, requires four hard-qualified sizes, and forbids dynamic rescue. TARGET-DATA2D v3 and TARGET-DATA2E v3 are generation-separated from v2 so historical records cannot masquerade as migrated authorities. Campaign preparation persists the migration latch and authenticated v5 candidate while leaving the live v4/v2/v2 path untouched. Atomic activation is authorized only by passed FINAL-GPU1 paired legacy-vs-MV learning controls and a passed SIZE-FIDELITY2 report with final GPU status.

## FINAL-GPU1 handoff in 0.20.192a0

`mdstats 0.20.192a0` converts FINAL-GPU1 from a readiness-only preflight into the final release-handoff authority. Preflight v6 binds the exact source archive, locked MH-1/MPA-0 model bytes, CUDA/CuEq runtime, and the existing PHASE1/PHASE2/PERF-CERT1 schemas. The handoff root registers every GPU result content-addressably, makes registrations immutable, requires explicit runtime binding for CuEq-dependent evidence, re-hashes release/models/evidence before reduction, rejects cross-release and cross-runtime evidence, and reduces the complete matrix fail-closed. Release-blocking scientific/safety gates must pass; negative measure-only optimizations are admissible only when they remain disabled or are superseded by the qualified phase-separated path. CUEQ-PHASE2 and ML-IAP/LAMMPS deployment remain optional. FINAL-GPU1 still cannot rewrite generated defaults; a positive PERF-CERT1 recommendation requires a later explicit policy revision. Positive GPU evidence is intentionally produced only when this complete package is run on the final workstation.

## PERF-CERT1 in 0.20.191a0

`mdstats 0.20.191a0` implements the end-to-end certification/recommendation authority above CUEQ-PHASE1 and optional CUEQ-PHASE2. Complete execution profiles are compared against the optimized MH-1/`omat_pbe` e3nn baseline on one frozen scientific protocol and workload. Faster execution is insufficient: target/DATA6/DATA7 selections, replay retention, EVAL2 and other hard decisions must remain identical, while final checkpoint bytes may differ. PHASE2 remains optional and cannot block a valid e3nn-source + CuEq-training recommendation. The v1 policy requires a strict positive end-to-end speedup, rejects locked-test tuning, and can recommend but never directly change generated defaults. Positive GPU profile evidence remains deferred to FINAL-GPU1 preflight v5.


## CUEQ-PHASE2 in 0.20.190a0

`mdstats 0.20.190a0` implements the optional selected-head CuEq source/DATA6 qualification authority. The original six-head MH-1/`omat_pbe` checkpoint remains the scientific source; the EXTRACT1 single-head checkpoint plus a release-matched CUEQ-DEP1 runtime is execution provenance only. The gate reuses the existing energy/force/stress/descriptor numerical-parity authority, requires deterministic stratified development coverage, foundation-difficulty and frozen-transform PCA/FPS parity, exact DATA6/DATA7 selection fingerprints, and explicit realization lineage. Pseudolabel/E0 execution is authorized only when separately evidenced. Direct six-head CuEq execution and generated-default changes remain forbidden. Positive GPU evidence is deferred to FINAL-GPU1; PERF-CERT1 is next.

## CUEQ-PHASE1 in 0.20.189a0

`mdstats 0.20.189a0` implements the phase-separated training qualification authority: source-foundation inference, DATA6, pseudolabel generation, and source evaluation remain e3nn, while only training from the EXTRACT1-qualified selected-head checkpoint may vary to pure CuEq. The gate requires exact paired protocol identity, a 5-10 epoch short pair (default 8), and at least one representative full pair on one positive CUEQ-DEP1 runtime. Final checkpoint bytes need not match, but replay retention, finiteness, checkpoint admissibility, target-head extraction, EVAL2, and available physical verification must preserve the existing hard scientific decisions. Performance telemetry is diagnostic only. The control plane is complete; positive GPU evidence remains deferred to `FINAL-GPU1`, and a pass still cannot authorize CuEq source/DATA6 execution or a generated-default change.

## CUEQ-DEP1 in 0.20.188a0

`mdstats 0.20.188a0` implements the content-addressed accelerator-runtime freeze that will be used by the final consolidated GPU qualification. `CueqDep1RuntimeRecord.v1` requires CuEq core, Torch frontend, and CUDA-ops layers; records CUDA device/runtime, cuDNN, determinism/TF32/matmul state, and selected environment variables; and binds installed distribution metadata/RECORD plus imported module bytes. CUDA-13, CUDA-12, CUDA-11, and generic CuEq ops distributions are discovered explicitly. OpenEquivariance remains optional for the first pure-CuEq training phase. The current CPU-only development host correctly produces negative CUEQ-DEP1 evidence; no e3nn fallback is inferred as a pass. Actual accelerator qualification remains deferred to `FINAL-GPU1`.

## PERF-P5 in 0.20.187a0

`mdstats 0.20.187a0` hardens late TRAIN2/EVAL2 persistence and reuse without changing checkpoint, continuation, or evaluation authority. TRAIN2 and STOR2 tensor-state SHA-256 paths now feed canonical contiguous CPU buffers to the hasher in bounded chunks rather than materializing a second full-size `bytes` copy; execution-only persistence telemetry separates clone, hash, write, and summary costs. EVAL2 also exposes a fail-closed optional compatible-model state reload path for one validated unaccelerated shell. On the CPU development host the shell path is exact but slower than reconstruction, so it remains opt-in and is not a generated default. HDF5/LMDB remain dataset formats rather than being relabeled as authenticated graph caches. All accelerator-side persistence/reuse performance qualification remains deferred to `FINAL-GPU1`; the remaining accelerator/certification gates are not exercised during intermediate development.


## VRAM1 + PERF-P4 in 0.20.186a0

`mdstats 0.20.186a0` implements workload-correct DATA6 batch-capacity evidence and bounded CPU/GPU/I/O orchestration without promoting any accelerator claim. `MaceBatchCapacityCalibration.v2` binds the actual descriptor/prediction/combined workload, stress-oriented calibration-frame identities, allocator/driver memory telemetry, absolute and fractional headroom, throughput-aware batch choice, and post-cleanup live-memory re-clamping. DATA6 persists identity-bound OOM-safe caps and may overlap native CPU graph preparation with current inference plus bounded shard persistence; synchronous execution remains the exact fallback. Real supplied MH-1 and MPA-0 CPU/e3nn prepared/direct paths match exactly. CUDA/VRAM throughput acceptance is deferred to `FINAL-GPU1`; **PERF-P5** is the next CPU/control-plane implementation gate.


## PERF-P3 in 0.20.185a0

`mdstats 0.20.185a0` implements CPU structural/reduction hardening without changing scientific authority. DATA6 uses an exact direct local-structure array kernel with immutable topology reuse; FOUNDATION-AUDIT1 fills exact preallocated force-tail arrays with an execution-only mmap fallback; and stage resource scopes fail closed on nested CPU oversubscription. Bounded CPU evidence shows 7.42% lower median wall time for the controlled 168-atom structural fixture and 8.02% lower peak RSS for the 900,000-atom audit reduction fixture. GPU qualification remains deferred to `FINAL-GPU1`; **VRAM1 + PERF-P4** is the next implementation gate.


## SELECT2 in 0.20.176a0

After production-size DYN qualification, TRAIN2 `verify` now freezes the final-development seed order from the same EVAL2 target-only practical-equivalence/bootstrap policy used for checkpoint selection. Physical pass/fail is then applied only as an eligibility filter over that already-frozen order: the first complete DEPLOY->PES->RELAX->DYN passer wins, while failed higher-ranked seeds remain immutable fallback evidence. Replay and rollout metrics have zero positive ranking or tie-break authority. The selected target-only MACE and exact ML-IAP artifacts are copied byte-for-byte into `models/select2-frozen/` and authenticated by a pre-locked-test freeze record. The subsequent one-shot locked test is intentionally not implemented by SELECT2 and cannot select another seed or checkpoint.


## DYN-VERIFY2 in 0.20.175a0

After RELAX qualification, TRAIN2 `verify` now runs the exact DEPLOY-authenticated ML-IAP artifact through the same LAMMPS executable on a common grid of up to two DFT-relaxed bases at 300 K and 800 K. Each case uses 0.2 ps Langevin NVT followed by 1.0 ps NVE at a 0.5 fs timestep and records a `run 0` frame before velocity initialization. Numerical NVE/NVT diagnostics are hard but insufficient: preserved-group bond loss/new bonds plus displacement, bond-RMSE, and angle-RMSE damage must persist for 50 fs before becoming a structural failure. During target-size Stage C, the complete DEPLOY->PES->RELAX->DYN physical chain is bound back to TARGET-DATA2D so the final `N_target` can resolve. Production-size candidates wait for SELECT2 after DYN.

## RELAX-VERIFY1 in 0.20.174a0

After PES qualification, TRAIN2 `verify` now freezes up to four common correlation-balanced relaxation bases, writes matched fixed-cell zero-K DFT relaxation requests, and waits for converged DFT references. Every surviving target-only candidate is relaxed from those exact bases with ASE FIRE (`fmax = 0.03 eV/A`, at most 500 steps). Preserved profile groups are hard topology authorities: the generated LTA campaign protects the `framework` graph while allowing Li/Na/K guests to relocate. Passing topology is not enough; candidate relaxed structures must also reproduce the matched DFT geometry within frozen displacement, bond-length, bond-angle, cell, and force tolerances on every base. Completion advances only to DYN-VERIFY2.

## PES-VERIFY1 in 0.20.173a0

TRAIN2 `verify` now proceeds from deployment parity to one common finite-displacement local-PES request. Up to four correlation-balanced target bases receive up to four generic bond/angle/coordination/strain modes with symmetric +/- perturbations and an explicit q=0 reference. The campaign writes fixed-geometry DFT request directories and waits until matched labels are available; VASP auto-collection requires identical INCAR/KPOINTS/POTCAR bytes across all probes, while external ExtXYZ references require an explicit protocol digest. Candidate and foundation predictions are compared against the same DFT evidence using centered restoring-force increments, force-derived stiffness, energy curvature, and strain stress/curvature. Wrong restoring direction or local curvature is a hard candidate failure even when static RMSE is favorable.


## DEPLOY-VERIFY1 in 0.20.172a0

TRAIN2 `verify` now freezes a deterministic correlation-block-balanced probe set, reconstructs the exact EVAL2-selected checkpoint, verifies its explicit target head against the exported target-only MACE model, converts that target-only model to ML-IAP, and runs the configured LAMMPS executable at `run 0` on the same probes. Energy and forces, plus stress when supported, must match within the frozen dtype-specific tolerance. The record binds exact model/export bytes, target-head export identity, probe identity, LAMMPS executable bytes and launch arguments. Completion advances only to PES-VERIFY1; it does not claim physical stability.


## MLCV-MIGRATE1 in 0.20.139a0

MIGRATE1 closes lifecycle migration and storage authority. New preparations are bound to `checkpoint_strategy = "mlcv_nested_cv"` through an immutable lifecycle record tied to the campaign plus ROLE1/MON1 catalog digests. Editing TOML cannot redirect the same campaign into ADAPT-EVAL1, bounded/multi-fidelity evaluation, fold-winner deployment, or historical lightweight hard-gating. Transitional 0.20.131-0.20.138 MLCV campaigns that were created while the TOML spelling was `adaptive_topk` are recognized from their MLCV DATA8 authority and migrated in place without reranking or scientific reevaluation. After verified publication, the complete top-five/SELECT1/CV/FINAL1/VERIFY1/locked-E evidence graph is frozen; top-five checkpoints, representatives, qualified committee models, and production bytes remain protected.

## MLCV-VERIFY1 in 0.20.138a0

VERIFY1 visits only qualified FINAL1 full-development representatives. With `fallback_to_next_qualified_final_seed = true` (default), a bounded-NVE failure advances to the next qualified final seed; the first complete physical passer is frozen and fallback then ends permanently. Sealed target test `E` is materialized only after that freeze and evaluated target-only on the exact frozen target-head bytes. Locked-E failure is terminal review/failure evidence under the current campaign identity and cannot select another seed or checkpoint. Production publication is atomic and requires both physical verification and locked-E success.


## MLCV-FINAL1 in 0.20.137a0

FINAL1 consumes AGG1 conventional-CV evidence and SELECT1 final-development representatives only. A configured-CV failure blocks production selection at the recipe level. Otherwise, qualified final seeds are ranked deterministically by authoritative full `D_full + R_full` score, target error, replay error, seed, epoch, and checkpoint identity. The best seed becomes the single production **verification candidate**; FINAL1 does not publish the verified production model before physical verification. Every qualified final seed is exported as a target-head committee member, while failed final seeds are omitted rather than padding committee cardinality. Generated campaigns now expose `seed_mode = "optimizer_only"`; optional `optimizer_and_cv_partition` changes deterministic CV partitions per seed for broader robustness sampling without changing the final full-development training domain.


## MLCV-AGG1 in 0.20.136a0

Each frozen fold representative is evaluated exactly once on its untouched outer CV target fold. The outer result can pass or fail that fold but cannot choose another epoch. Per seed, every configured fold must have a SELECT1 representative and pass the configured target force-RMSE ceiling. Target, representative TRUE_DFT `R_full` replay, and combined score statistics are reported separately as mean, sample standard deviation, minimum, maximum, range, and worst fold. Cross-fold dispersion is diagnostic-only in this revision. Fold representatives are permanently production-ineligible; only final-development representatives will enter MLCV-FINAL1.

## MLCV-SELECT1 in 0.20.135a0

Every retained RANK1 checkpoint is fully evaluated within its own run. Fold runs use nested `V_i_full + R_full`; final-development runs use `D_full + R_full`. The standard target threshold and weight-derived replay threshold are component-wise hard gates, together with configured energy/focus/stress/worst-condition limits. Only surviving checkpoints are ranked by full weighted score, producing exactly one representative or an explicit no-representative outcome per run. New MLCV campaigns therefore no longer pool fold/final champions through the historical ADAPT-EVAL1 queue.

`target_stop_fraction` and `replay_stop_multiplier` remain derived-control factors rather than absolute errors. Their defaults are 0.80 and 1.20, but users may configure them in TOML; the full-validation acceptance criteria do not move with these factors.




## MLCV-RANK1 in 0.20.134a0

Every finite lightweight checkpoint is ranked within its own training run by the target/replay weighted score. Up to five are retained deterministically; no full validation or checkpoint deserialization is purchased at this gate. The rank-one compatibility fields remain only as a temporary bridge to the historical evaluator until MLCV-SELECT1.

The STOP1 control boundaries remain derived, not absolute: `target_stop = 0.80 * target_full_threshold` and `replay_stop = 1.20 * replay_full_threshold`, where `replay_full_threshold = (target_weight / replay_weight) * target_full_threshold`.

## MLCV-STOP1 in 0.20.133a0

New adaptive-stop policy schema v2 removes the 30 meV/A target/replay full-validation ceilings from per-epoch lightweight disqualification. At default 1:1 score weighting, 24 meV/A target success and 36 meV/A replay exhaustion remain training-control signals only and cannot stop training before three completed epochs; the 30-epoch maximum remains hard. Foundation replay feasibility is now frozen from one-time full TRUE_DFT `R_full` evidence before epoch 0, authenticated by replay-artifact SHA-256 and not reevaluated on exact restart. Historical v1 stop policies preserve their original digest and behavior.

## MLCV-MON1 in 0.20.132a0

New preparations materialize `V_i_light ⊂ V_i_full` for CV folds, `D_light ⊂ D_full` for final runs, and `R_light ⊂ R_full` with TRUE_DFT replay labels. Defaults cap target-light and target-training diagnostic monitors at 256 configurations and replay-light at 512. The training diagnostic is evaluated each validation epoch through the target head but is selection-inert; per-run JSON/CSV/PNG histories are reconstructed from persisted MACE metrics without reporting-time inference. Outer CV folds remain untouched by checkpoint selection.

## MLCV-ROLE1 and three-seed default in 0.20.131a0

MLCV-ROLE1 freezes conventional-CV statistical authority before later gates change
monitoring or selection behavior. New DATA8 preparations carry typed lineage for
fold training, nested checkpoint selection, outer CV evaluation, final validation
`D`, locked test `E`, replay-gradient training, and TRUE_DFT replay validation.
Outer-CV and locked-test roles fail closed if presented to checkpoint stop/rank/top-K
selection APIs.

New `init` configurations now spend a 12-job default training budget entirely on the
production-preferred multi-head replay path: three optimizer seeds, three common
cross-validation folds, and one final-development fit per seed. Naive/native
target-only fine-tuning remains configurable as an explicit baseline but is disabled
by default. Existing TOML files and historical campaign identities remain unchanged.

## Multi-head-only default campaign in 0.20.129a0

The 0.20.129a0 generated default first switched to multi-head replay only and used
four optimizer seeds with three common cross-validation folds plus one final fit per
seed, for 16 jobs. That historical default remains part of old campaign identity;
0.20.131a0 reduces only newly initialized campaigns to three seeds.


## Adaptive migration and compatibility closure in 0.20.128a0

ADAPT-MIGRATE1 closes the seven-gate adaptive revision. New adaptive campaign identity now prevents
TOML edits from switching back to historical bounded/exhaustive/EVAL-MF evaluators, while historical
campaigns cannot be silently reinterpreted as `adaptive_topk`. Generic storage/restart code consumes
a schema-neutral protocol-freeze authority record that points to the original historical committee
freeze or adaptive deployment freeze without rewriting it. Completed 0.20.127 adaptive campaigns can
be reconciled by rerunning `verify`; completed inference/evaluation/NVE evidence is reused and only the
generic authority alias plus immutable migration receipt are added. Consequential STOR operations now
require a schema-valid freeze authority, and `storage report` reads migration/freeze summary through a
read-only SQLite connection. Historical EVAL-MF/refine/committee evidence remains readable and is not
deleted by migration.

## Adaptive top-K full evaluation in 0.20.126a0

New generated campaigns use `checkpoint_strategy = "adaptive_topk"`. Training already pays for the
common 256-target / 512-true-replay online monitor metrics; ADAPT-RANK1 freezes exactly one champion
per independent run from those metrics. ADAPT-EVAL1 orders those champions by their frozen
lightweight score, purchases authoritative full evaluation for at most five initially, and evaluates
the next five only when no already-purchased candidate is fully admissible. Production adaptive
evaluation launches no 10%/33% EVAL-MF rounds.

Authoritative target evaluation uses the complete common DATA5 outer-monitor domain, separately
materialized from the 256-frame online subset. Authoritative replay evaluation uses the complete
configured independent TRUE_DFT replay validation/monitor domain resolved from
`[paths].replay_true_labels`, not the 512-frame online subset and not the replay-training corpus.
Target/replay hard ceilings and retained safety gates are applied before weighted scoring. Naive
fine-tuning remains target-only for gradients but receives the same fixed true-replay online monitor
as validation-only evidence through its target head, making lightweight scores comparable with
multi-head replay runs. Historical `bounded`, `exhaustive`, and `multi_fidelity` evaluators remain
available for compatible old campaigns. ADAPT-VERIFY1 in 0.20.127a0 performs score-ordered
bounded verification fallback and publishes only the first passing target-head model.

## Adaptive stopping and run-local ranking in 0.20.124a0-0.20.125a0

ADAPT-STOP1 terminates a run when its common target monitor reaches 80% of the configured target
ceiling, its common true-replay monitor exceeds 120% of the weight-derived replay ceiling, or the
hard epoch limit is reached. With the default 30 meV/A target ceiling and 1:1 score weights this is a
24 meV/A target-success stop and a 36 meV/A replay-exhaustion stop. ADAPT-RANK1 then uses only the
already-persisted epoch metrics to freeze one admissible weighted-score champion per run with zero
new model inference.

## Read-only campaign storage accounting in 0.20.111a0

Run `mdstats-mlff-campaign --config campaign.toml storage report` to inventory the campaign workspace without reclaiming anything (bare `storage` is the same report). All storage management now lives under this one command: `storage cleanup`, `storage deduplicate [--apply]`, and `storage archive create|verify|restore`. `storage cleanup --tier archive --apply` deletes consequential hot representations only after a verified reversible archive exists. STOR1 reports logical bytes, inode-deduplicated allocated physical bytes, unique-inode logical bytes, ownership/retention families, protected external inputs, symlink escapes, future reclamation eligibility, capability loss, and the largest files/directories. The JSON report is written to `results/storage-report.json` only when that destination is itself inside the verified ownership boundary.

Configured training, foundation, replay, true-label, and campaign-config paths remain protected user/reference inputs even when physically located inside the workspace. Existing cleanup and checkpoint-pruning code now consumes the same real-path/symlink containment boundary, so a path found in TOML/SQLite/JSON never grants deletion authority over external data. STOR1 adds no new deletion mode; STOR2 is the next gate.


## Fixed common online monitors in 0.20.123a0

New campaign preparation freezes one common 256-configuration target online monitor and one
independent 512-configuration TRUE_DFT replay online monitor. The target monitor is selected
deterministically from DATA5 outer-monitor evidence with condition/run/time coverage and reused
by every competing run. Multi-head replay validation uses the true-label monitor while replay
gradient training remains independently configured. ADAPT-STOP1 and the later adaptive ranking/evaluation gates now consume these fixed monitor identities.

## Binary learned-model precision in 0.20.122a0

`mdstats-mlff-campaign init` now accepts only `--precision single|double`; plain init is canonical `single`. `single` means an FP32 learned model for training and every MACE inference path, while `double` means an FP64 learned model throughout training, evaluation, verification, committee inference, and export. New campaigns no longer generate a staged `[training.precision]` schedule: the former `refine` profile and any user-facing `mixed` model mode are retired. Historical staged/refine records remain readable for audit/archive, but production commands fail closed and require an explicit migration to `single` or `double`.

Model dtype does not control mdstats-owned scientific arithmetic. Reference fitting, SVD/PCA, geometric linear algebra, SSE/RMSE/statistical reductions, observable analysis, and persistent mdstats-owned MD bookkeeping remain FP64 invariants for both model modes. Evaluation explicitly forbids checkpoint/template dtype promotion, so an FP32 checkpoint is never presented as an FP64 model merely for evaluation or export.

The earlier PREC1-PREC3 staged-precision implementation remains documented as historical compatibility evidence; ADAPT-PREC1 supersedes its production precision semantics for newly initialized campaigns.

## Historical guarded multi-fidelity checkpoint evaluation in 0.20.107a0

Release 0.20.107a0 introduced deterministic nested target/true-replay screening (10% -> 33% -> 100%), prediction-coverage reuse, statistical guard bands, and replay-plausible rescue. A representative 30-checkpoint qualification matched exhaustive selection while purchasing about 10.9 full-checkpoint equivalents. ADAPT-EVAL1 in 0.20.126a0 supersedes this as the generated production strategy; `multi_fidelity` remains available only for compatible historical campaigns alongside `bounded` and `exhaustive`.

## Adaptive parallel evaluation and verification in 0.20.86a0

Checkpoint evaluation now uses one campaign-wide adaptive queue across runs and shortlisted checkpoints, while bounded NVE verification runs independent cases concurrently with private calculators. CUDA starts with one job and admits more only when projected aggregate VRAM and GPU utilization both remain below 90%; CPU admission uses affinity/cgroup-aware projected utilization below 90%. Package CPU and GPU/VRAM defaults are now 90%, while RAM remains 80%. Existing TOMLs and compatible verification caches remain reusable. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.86a0.md` and `docs/specs/training_data/mlff_parallel_evaluation_verification_spec.md`.

## Independent true-label replay evaluation in 0.20.85a0

The campaign configuration now separates replay training labels from replay evaluation labels. A directory containing `mp_replay_selected.extxyz` can reconstruct the exact true-label train/monitor split from `replay_source_index`, or users may supply already split true-label files. Evaluation persists the complete foundation/candidate × target/replay metric matrix, invalidates stale pseudo-label results by artifact/model/policy identity, and refreshes retained checkpoints safely after prior checkpoint pruning. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.85a0.md` and `docs/specs/mlff_true_label_replay_evaluation.md`.

## Constraint-aware evaluation in 0.20.83a0

A completed training run whose evaluated checkpoint shortlist contains no candidate satisfying every frozen acceptance constraint no longer aborts the whole campaign. mdstats records the exact per-epoch rejection reasons, excludes that run from export and verification, continues evaluating other completed runs, and automatically downgrades the available fold evidence. A full production freeze is withheld whenever any required run lacks an admissible checkpoint. Bounded shortlisting is reported honestly: failure of four shortlisted epochs is not presented as proof that all saved epochs fail. Set `[evaluation].max_checkpoints_per_run = 0` only when exhaustive checkpoint rescue is scientifically worth the cost. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.83a0.md`.


## Lower-cost evaluation and verification in 0.20.82a0

Evaluation no longer reconstructs and runs full monitor inference on every epoch by default. It first shortlists at most four checkpoints per run from existing training-time validation history, then applies the authoritative mdstats target/replay metrics only to those candidates. Verification gives full structure-temperature NVE coverage to deployment/final models, uses a bounded stability smoke for fold-only comparison models, caches completed cases, keeps one calculator resident per model, and samples expensive MD diagnostics every ten steps by default. Set `[evaluation].max_checkpoints_per_run = 0` for exhaustive checkpoint evaluation. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.82a0.md`.

## MACE checkpoint reconstruction in 0.20.81a0

MACE 0.3.16 epoch `*.pt` files are optimizer restart dictionaries, not deployable model modules. Evaluation now verifies the selected checkpoint, reconstructs a whole model through the immutable DATA8 job configuration in an isolated copy, verifies the original checkpoint remains byte-identical, and uses the reconstructed model for `MACECalculator` and target-head export. Multi-head replay models are reduced to the requested target head; unambiguous single-head naïve models are serialized directly. Install this release and rerun `evaluate`; do not repeat `prepare`, preflight, or training. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.81a0.md` and `docs/arch_manuals/mlff_checkpoint_model_reconstruction.md`.


## Complete persisted-schema compatibility in 0.20.80a0

`evaluate` can now read digest-valid campaign state produced by 0.20.63a0–0.20.79a0, including feature-metric policies created before `randomized_projection_seed`, DATA5 partition policies created before `cross_validation_seed`, training-execution policy v1, production-materialization plan v2, and historical DATA7/DATA8 parser identities.  Legacy runtime defaults are supplied without changing the original serialized child identity, so parent plan/checkpoint/record digests remain valid.

Every nested digest is still verified independently; altered historical payloads fail closed.  Actual 0.20.76a0 DATA5 and production-plan fixtures are part of the regression suite.  Install the new code and rerun `evaluate`; do not repeat `prepare`, preflight, or completed training.  See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.80a0.md` and `docs/arch_manuals/mlff_schema_compatibility.md`.

## Verification from completed models in 0.20.78a0

A campaign may now be evaluated and bounded-NVE verified before every configured training job finishes. Completed runs are grouped by exact training method, selection size, and optimizer seed. A group with all configured folds plus its final-development job receives **complete-variant interim evidence**; two or more completed folds receive **partial cross-validation evidence** with an explicit reduced-confidence warning; one completed model receives **single-model evidence** based on checkpoint-monitor metrics and bounded stability tests, with an explicit warning that no cross-fold estimate is available.

Use `evaluate --training-mode multihead_replay --seed 1` to select a particular completed group, then run `verify`. Without filters, evaluation chooses the strongest available evidence level before comparing its admissible checkpoint metrics. Interim evidence never freezes a production protocol, never deletes restartable checkpoints, and leaves unfinished jobs resumable. If more runs complete afterward, verification asks for a fresh `evaluate` rather than silently using a stale subset. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.78a0.md`.


## Deterministic training matrices and restart accounting in 0.20.77a0

The generated campaign TOML now exposes separate seed arrays, fold counts, and fold-partition seeds for naïve fine-tuning and multi-head replay. The default is three cross-validation folds plus one final-development model for each of two seeds and two methods (16 jobs). Set `cross_validation_folds = 0` for final-only training, disable a method, or shorten its seed array. Replay sampling, randomized feature projection, Python hash randomization, and verification velocities also use explicit seeds. Downstream evaluation, committee export, and verification follow only the configured/trained matrix.

Restart progress is checkpoint-aware: the epoch display cannot regress, abandoned or duplicated optimizer rows do not inflate the percentage, and qualified MACE 0.3.16 resumes after the committed checkpoint epoch. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.77a0.md`.


## Complete child-process teardown in 0.20.76a0

Production training has two subprocess layers: the campaign launches the mdstats precision wrapper, and that wrapper launches the real MACE/PyTorch process in a detached process group. The wrapper now forwards Ctrl-C, SIGTERM, terminal hangup, and quit signals to the nested MACE group, waits for it to exit, and escalates if necessary. Linux parent-death protection covers abrupt loss of either supervising parent. The campaign itself handles SIGTERM and SIGHUP through the same checkpoint-safe interruption path used by Ctrl-C. Existing checkpoints and completed runs remain restartable; no DATA8, `prepare`, or preflight identity changes are required. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.76a0.md`.

## Fixed-window scheduler averaging and bounded failed-runtime cleanup in 0.20.75a0

Production training now separates the one-second internal cancellation poll from visible progress output, which defaults to one update every 10 seconds. The adaptive CUDA scheduler no longer waits for fluctuating GPU utilization or VRAM to become low-variance: after every active job enters true optimizer work, it averages the complete 180-second calibration window and projects one additional job. Both projected mean VRAM and projected mean GPU utilization must remain below the configured 90% ceilings.

Obsolete execution-layout failures are no longer archived as complete model/checkpoint/results trees. mdstats retains a bounded compact diagnostic with execution metadata, a capped inventory, and log tails, then deletes the obsolete heavy bytes immediately. Current-policy restart checkpoints and completed-run artifacts remain protected. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.75a0.md`.

## Automatic storage cleanup and durable training restart in 0.20.74a0

Campaign lifecycle cleanup now removes only provably stale or reconstructable artifacts: orphaned external records, obsolete DATA8 generations, stale promotion trees, duplicated frame/DATA7 caches after preflight, heavy completed preflight-smoke outputs, and obsolete runtime-policy trees after preserving compact diagnostics. A manual `storage cleanup --dry-run` previews every deletion and reclaimed byte count. Before evaluation, all training checkpoints are retained; after every checkpoint is evaluated and one is selected, only evaluated unselected optimizer snapshots are removed while the selected checkpoint, full metrics, selection evidence, logs, and original catalog identities remain.

Production `train` now handles `Ctrl-C` and low-disk stops as durable interruptions: active MACE process groups are terminated gracefully, checkpoint bytes remain, interrupted attempts do not consume retry allowance, and the next invocation resumes with `--restart_latest`. Run-local records and valid final model/checkpoint artifacts recover parent-process commit gaps. Completed runs are SHA-256 re-inventoried and skipped; changed/missing checkpoint bytes fail closed rather than triggering silent recalculation. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.74a0.md`.


## True-epoch adaptive GPU training concurrency in 0.20.73a0

Production `train` now begins with exactly one CUDA job and adds at most one job per calibration step. Initialization, graph construction, initial validation, and checkpoint export cannot authorize expansion: every active job must first produce fresh optimizer records and remain in sustained epoch work for a fixed-duration averaging window. Natural utilization fluctuations are averaged rather than waited out. The projected mean aggregate VRAM **and** GPU utilization after adding the next job must both remain strictly below their admission ceilings (90% defaults). After each promotion, calibration resets. If stable post-add utilization reaches a ceiling, current jobs continue but the future replacement target is reduced. Runtime scheduling does not change DATA8 scientific identity, so no `prepare` or preflight rerun is required. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.73a0.md`.

## Production training runtime-path correction in 0.20.71a0

Production `train` now executes MACE from each immutable DATA8 job directory, exactly like preflight, so job-relative foundation, target, and replay paths resolve correctly. Models, checkpoints, logs, and results are redirected to the mutable `runs/<run-id>` directory with explicit absolute output arguments. Failed attempts from the obsolete run-directory working layout are archived and reset automatically; no `prepare` or preflight rerun is required. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.71a0.md`.


## Production replay-gate correction in 0.20.70a0

Mixed `naive_fine_tuning` + `multihead_replay` campaigns now qualify replay from an actual replay-bound DATA8 variant rather than whichever variant appears first. A plain `prepare` reuses completed DATA6-DATA8 artifacts and repairs only the final gate record. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.70a0.md`.

## Stage-aware prepare restart in 0.20.69a0

Plain `prepare` is now a true no-op when the completed campaign, configuration,
input file identities, scientific record digests, DATA6 sweep pointer, and DATA8
variant matrix are unchanged. Existing 0.20.68a0 campaigns are adopted into a
checksummed restart receipt without rebuilding DATA6 or rematerializing DATA8.

When a downstream protocol really changes, restart is selective: the completed
DATA6 checkpoint is restored without loading MACE or scanning every sidecar,
the finalized DATA6 bundle is reused by exact lineage/policy identity, and each
unchanged DATA7/DATA8 variant keeps its promoted content-addressed tree. Only
invalid or changed variants are rebuilt. Normalized frame arrays are also loaded lazily, so a DATA8-only repair does not reread the complete trajectory cache. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.69a0.md`.


## Naïve/replay campaign identity correction in 0.20.68a0

`naive_fine_tuning` variants now bind an explicit replay-free DATA8 plan. Earlier
releases carried the already-resolved replay corpus into every materialization;
DATA8 therefore inferred `multihead_replay` even for nominally naïve variants.
With the standard two-mode/two-seed campaign this produced paired fold/final jobs
with identical run IDs and stopped `train` at campaign-plan construction.

The runtime now verifies that each `data8:<variant>` pointer agrees with the
training mode, selection size, and optimizer seed frozen inside every DATA8 job.
Install this release and run ordinary `prepare` once. The corrected naïve DATA8
job trees are regenerated while DATA3-DATA7 and the completed foundation sweep
are reused. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.68a0.md`.


## Bounded preflight and live GPU progress in 0.20.67a0

The required one-epoch real-MACE smoke no longer traverses the complete replay
corpus. It writes deterministic temporary target/replay subsets under
`.mdstats/preflight-smoke`, extends the target subset only when necessary to
cover all target-head elements, and leaves the authenticated DATA8 generation
untouched. The launch line prints the exact MACE device, GPU model/memory, dtype,
and e3nn/cuEquivariance backend. Heartbeats report the current MACE phase plus
completed gradient updates as an exact percentage, with live GPU utilization and
VRAM use when `nvidia-smi` is available. Production training uses the same
progress counter. See `docs/history/mlff/release_notes/PATCH_NOTES_0.20.67a0.md`.


## Production-gate correction in 0.20.64a0

The final DATA9A gate now correctly distinguishes ordinary unstrained fixed-cell
runs from unresolved strain. Runs without an explicit strain reference group use
their own selected fixed cell as an exact zero-strain baseline; ungrouped
variable-cell runs remain fail-closed. LTA extension coverage is reconstructed
from retained compact DATA6 aggregate features when memory-optimized production
omits per-atom environment objects.

After installing this release, rebuild DATA2-DATA5 once with
`prepare --rebuild-catalog`. The DATA6 restart path verifies frame-record, model,
policy, and sidecar digests and rebinds compatible completed descriptor/prediction
artifacts to the rebuilt lineage without repeating MACE inference. See
`docs/history/mlff/release_notes/PATCH_NOTES_0.20.64a0.md`.


## DATA6-finalize and post-DATA6 scaling

The production universal structural stage now streams frame results into a
columnar NumPy table instead of expanding roughly 1,400 aggregate values per
frame into Python objects. Exact triclinic pair geometry is evaluated once for
`i < j` when all atoms are centers, angular invariants are batched by repeated
neighbor count, static aggregation plans are reused per run, and a short
autotune chooses an economical outer thread count. Production does not
materialize unused per-atom environment descriptors. Long-running progress
reports include recent and average frame rates, ETA, event count, and peak RSS.

For fixed atom count and feature policy, the stage scales linearly with frame
count. DATA7 uses bounded `O(N K d)` maximin selection, deterministic bounded
PCA, implicit missing-indicator products, and shared content-addressed results
across training variants. DATA6 and DATA7 large artifacts use native arrays plus
streamed JSONL rather than giant nested JSON payloads. Frames that need both
MACE descriptors and predictions share one native graph evaluation when the
qualified MACE 0.3.16 path is available. See
`audits/MLFF_PERFORMANCE_AUDIT_2026-08-05.md` for the complete complexity and
residual-cost analysis.


## Resource-aware campaign acceleration in 0.20.63a0

The MLFF campaign detects the CPU affinity/cgroup quota, currently available
system RAM, CUDA device, and free VRAM at runtime. Current automatic execution
targets 90% of CPU and GPU/VRAM capacity while retaining an 80% RAM ceiling. Independent trajectories are processed through
fresh, one-shot worker processes so Python GIL contention is avoided and native
parser/NumPy memory is released after every run. Worker counts are bounded by
the number of independent trajectories and by conservative per-worker plus
parent-output memory estimates; low-core systems may remain serial when process
startup would be slower.

DATA3 frame construction, raw DATA4 features, and LTA compact-column construction
all support trajectory-level process parallelism. The LTA workers return compact
NumPy columns rather than hundreds of thousands of Python records. Event scanning
reuses the catalog's immutable frame-to-state index instead of reconstructing a
second million-record hierarchy.

DATA6 uses native MACE graph batches when the locked MACE 0.3.16 calculator path
supports them. The initial batch is selected from 90% of free VRAM and is halved
automatically after a CUDA out-of-memory exception. MACE training and preflight
receive a CPU/RAM-bounded DataLoader worker count, while cuEquivariance remains
the qualified GPU kernel backend when available. CPU-only feature stages are not
blindly moved to the GPU because the 168-atom trajectory batches are dominated by
object construction and host-side provenance rather than sufficiently large dense
GPU kernels.

The defaults are:

```toml
[performance]
cpu_fraction = 0.90
ram_fraction = 0.80
gpu_memory_fraction = 0.90
source_workers = 0
feature_workers = 0
lta_workers = 0

[model]
artifact_shard_size = 128
inference_batch_size = 0
maximum_inference_batch_size = 16

[evaluation]
batch_size = 8
cache_monitor_datasets = true
cache_replay_baseline = true

[training]
num_workers = 0
```

Zero means automatic resource-bounded selection. Positive overrides remain clipped
by the detected CPU and memory envelopes.


## MLFF large-campaign storage and evaluation optimization

Production DATA6 writes immutable descriptor and prediction shards rather than one
file per frame. With the default `artifact_shard_size = 128`, an all-descriptor and
all-prediction 36,759-frame sweep uses 576 scientific shard files instead of up to
73,518 sidecars. Each descriptor shard also contains global and per-species summary
arrays, so DATA7 reads about one summary block per shard rather than reopening and
reducing every atomic descriptor tensor. Energy-only residual-reference fitting does
not materialize force or stress arrays. Legacy per-frame sidecars remain readable.

The normalized frame cache and large DATA7 numerical members are native `.npy`
arrays with independent authentication. Restored frame arrays and the fitted DATA7
matrix remain read-only memory maps where possible. Centers, scales, and PCA
projections are native arrays rather than nested JSON floats. Raw and transformed
feature matrices are preallocated, and standard scaling uses masked reductions
without temporary NaN matrices.

Checkpoint evaluation parses authenticated target/replay monitor files once, reuses
one candidate MACE provider across heads, evaluates adaptive batches with CUDA-OOM
backoff, streams sufficient error statistics, and caches the unchanged foundation
replay baseline. Set `[evaluation].batch_size`, `cache_monitor_datasets`, or
`cache_replay_baseline` explicitly to override these defaults.

## MLFF runtime and memory optimization revision 4

The MLFF worker transport now preserves read-only frame-cache arrays as path/offset
references instead of embedding complete NumPy payloads in task pickles. Authenticated
DATA6/DATA7 arrays use fast restoration and direct stored-member memory mapping, VASP
controls and metadata are parsed once per source, MACE descriptor summaries are gathered
by shard, and DATA7 training weights are columnar. Parsed monitor datasets and CPU MACE
graph batches use byte-budgeted caches controlled by
`MDSTATS_MLFF_MONITOR_CACHE_BYTES` and `MDSTATS_MACE_GRAPH_CACHE_BYTES` (both default
to 512 MiB; set either to `0` to disable). Scientific feature and selection semantics are
unchanged.

## MLFF campaign performance in 0.20.62a0

The campaign preparation path now decodes each VASP source once, writes a
checksummed normalized frame cache, and reuses the same arrays for DATA3--DATA8.
Independent source files are processed by a bounded worker pool with per-run
frame counts, quality status, elapsed time, and ETA. DATA4 reports progress for
raw features, LTA partition features, and event scanning.

Large DATA4 state is persisted as checksummed JSONL shards rather than a giant
SQLite JSON value. This avoids duplicate multi-gigabyte payloads and restores
only when a later stage actually consumes DATA4. Foundation sweeps skip DATA4
restoration entirely. Catalog frame lookups are indexed, mobile/framework
coordination uses vectorized minimum-image batches, quantiles are computed in
one NumPy call, and canonical digest serialization avoids redundant sorting.

On the supplied 27-run production LTA corpus (37,633 retained frames), the
optimized DATA2 source-ingestion stage completed in 125.9 s with four workers.
From the normalized cache, DATA3 completed in 35.4 s, DATA4 in 111.2 s, and
DATA5 in 1.6 s, with a 2.70 GiB peak resident set. Sharded DATA4 persistence
took 17.2 s and checksum-verified restoration in a fresh process took 21.0 s
with about 1.0 GiB peak RSS. Exact timings depend on storage and CPU. GPU-bound
DATA6 and MACE training remain controlled by the selected MACE/cuEq backend.


The `prepare` stage now pre-populates its review manifest from source evidence.
It reads target temperature, thermostat, ensemble, timestep, and fixed-cell status
from each `vasprun.xml`; parses LTA strain intent from filenames; and promotes a
strain family only when the actual fixed-cell matrices reproduce the exact LTA
hydrostatic, volume-preserving orthorhombic, or symmetric right-polar shear
definition. Values such as `hydro+5` are interpreted as +5%, while `hydro+0.05`
retains fractional notation. Failed or ambiguous geometry checks remain visible
as warnings but cannot influence downstream partitioning until reviewed.

The MLFF preparation and fine-tuning path is now exposed through one source-
checkout command rather than fragmented stage scripts:

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml guide
```

The CLI owns one documented TOML configuration, one reviewed manifest, one
SQLite orchestration database, and compact `data/`, `runs/`, `models/`, and
`results/` directories. Its `doctor`, `prepare`, `preflight`, `train`,
`evaluate`, and `verify` stages wrap the implemented DATA2-DATA9B2 contracts
without weakening their leakage, provenance, replay, precision, checkpoint, or
protocol-freeze gates. `status` always reports the next safe action, while
`advance` never skips an incomplete gate.

The campaign treats MACE acceleration as a frozen protocol input. New MH-1
campaigns now default explicitly to `[acceleration].backend = "e3nn"`, the
qualified numerical reference path. CuEq remains an explicit opt-in backend and
`doctor` must prove energy/force/stress/descriptor/selection parity before it is
authorized. The same frozen setting is propagated through DATA6, DATA8,
preflight, training, checkpoint evaluation, and bounded verification. No stage
silently changes backend.

For multi-head replay, `doctor` now treats replay as a first-class production
input rather than merely checking that two extended-XYZ files parse. It binds
pseudo-labels to the exact foundation checkpoint SHA-256, verifies train/monitor
geometry separation, target-element coverage, explicit label provenance, and
minimum corpus sizes. The bundled small replay fixture therefore remains useful
for software smoke work but is rejected by the default production policy.

A real one-epoch MACE 0.3.16 preflight passes the exact production wrappers,
target-head extraction, and finite evaluation round trip. Bounded committee-
wide NVE verification rejects non-finite predictions, atomic collapse, extreme
forces, and total-energy drift above the configured hard limit. Passing bounded
verification authorizes longer scientific validation; it does not replace
analysis-owned RDF, coordination, site-occupancy, VDOS/VACF, strain-response, or
diffusion checks.

Long production fine-tuning remains intentionally gated on completion of the
real DATA9A realization and qualified production replay-train/replay-monitor
corpora. The code path is implemented; those campaign-specific inputs and the
RTX 3090 CUDA preflight must pass before the expensive local run begins.

## Stage 11E-ENS0 through GR3 and MLFF-DATA9A4 selectable precision

Version `0.20.41a0` adds an auditable selectable-precision contract for MACE foundation-model fine-tuning. A user may set `MaceOptimizerPolicy(default_dtype="float32")` or `default_dtype="float64"`; that choice is bound into the training-protocol digest, realized in the generated MACE configuration, enforced during execution, and verified from the serialized trained and extracted model tensors. The supplied float64 MPA-0 medium checkpoint has been tested as the starting point for both float32 and float64 one-epoch transfer jobs. A real three-frame 300 K Na-LTA smoke also produced a finite, uniformly float32 model.

The complete 27-trajectory, 37,632-frame target corpus remains qualified through DATA5. The surviving production candidate plan contains 2,734 expensive frames, but the checkpoint-bound production DATA6--DATA8 sweep must be restarted because its partial descriptor outputs did not survive the prior execution restart. DATA9B remains gated on completion of that production realization.

The Stage 11E-GR3 fixed-kernel grid-refinement runtime from `0.20.26a0` is unchanged. Stage 11E-GR4 cross-fitted numerical-hypothesis selection and freeze is the next implementation stage in the Stage 11 branch.

## Stage 11 revision-43 implementation contract

Architecture revision 43 retains the corrected ENS/STAT/E0b dependency graph and
adds the missing trajectory-temperature and numerical-quality contracts. Ionic
temperature is reconstructed from ionic kinetic energy by equipartition with a signed
active degree-of-freedom definition. The VASP adapter must parse explicit/effective
`vasprun.xml` controls and per-step SCF traces. Trajectories are classified as
`strictly_qualified`, `degraded_quality`, or `unqualified`: degraded data proceed with
warnings and signed metadata, while only catastrophic integrity failure is rejected by
default. Execution quality remains separate from method-specific thermodynamic
admissibility. No runtime S0--S4 scientific result is promoted by this planning revision.

## Architecture ownership and maintainability refactor

Version `0.20.16a0` resolves the immediately fixable architecture/codebase audit
items without changing scientific behavior. The framework/ring manual is now
Part I and ends at species-independent Stage 11D structural semantics; the
registered site/kinetics manual is Part II and owns Stage C0 onward. Obsolete
duplicated Stage 11 plans are removed, stale Stage 11 and density-specification
PDFs are regenerated, and duplicated S0-S4 serialization/signing/resource
helpers are centralized in a private module while preserving every public schema
and signature. The Na-LTA pilot remains `scientifically_partial`.

## Stage 11E8a implementation and regression closeout

Version `0.20.15a0` closes the engineering boundary after the completed
Stage 11E8a-S0 through S4 real-source pilot. LD6 multilevel research sweeps now
use their documented deterministic phase budget rather than host-dependent
throughput calibration; Phase-A planning uses exact logical-node counts for
explicit atomic and framework density grids; hard-limit tests isolate the limit
under test without relaxing runtime-derived production guardrails; and
`fast-simplification` tests skip cleanly when the optional interactive extra is
absent. A file-complete bounded regression sweep passes 1,493 tests with one
optional-dependency skip. The scientific conclusion is unchanged: the Na-LTA
pilot remains `scientifically_partial`, with persistent occupied basin identities
but unresolved saddle topology, PMF-force provenance, and observed transition
paths. Stage 11E8a implementation is complete; a kinetic Stage 11E8b remains
closed until those scientific prerequisites are addressed.

## Stage 11E8a-S4 force-density and transition-path readiness

Version `0.20.14a0` executes the source-bound Stage 11E3 force-refinement gate and prepares the Stage 11E6/11E6b path boundary without weakening either contract. The historical S4 baseline predates ENS/STAT reconstruction: it has complete physical forces but retains equilibrium, stationarity, and PMF admissibility as unresolved legacy evidence, so all 24 central local refinements remain `pmf_provenance_rejected` rather than being converted into a density-gradient comparison. Revision 42 now specifies how the NVE controls and trajectory-quality evidence must be reconstructed before that decision can be revisited. The trajectory contains five provisional return excursions, three right-censored exits, and no inter-attractor jumps. Because the S2 saddle topology remains non-authoritative, final segmentation and observed path reconstruction stay closed. All required evidence records now exist, so the dossier is `scientifically_partial` with explicit blockers rather than `blocked_missing_required_evidence`. Stage 11E8b remains prohibited pending closure review.

## Stage 11E8a-S3 structural mapping and temporal-support preparation

Version `0.20.13a0` maps the source-bound central Na attractors onto the
packaged 82-ring primitive Na-LTA catalog using the actual locally unwrapped,
serrated oxygen polygons rather than circular or elliptical surrogates. It then
transfers the signed S2 spatial partition to the coordinate-identical full
36,000-sample Na catalog and executes provisional Stage 11E4 temporal support
over all 1,500 frames. All 24 central attractors have unique ring candidates and
the temporal pattern is persistent, but both records remain partial because the
S2 bandwidth/grid saddle topology is not authoritative. Force-density agreement
and observed transition paths remain missing; Stage 11E8a-S4 is next and Stage
11E8b remains closed.

## Stage 11E8a-S2 density refinement and attractor-lineage certification

Version `0.20.12a0` executes a source-bound Cartesian bandwidth ladder,
deterministic attractor lineage, central-bandwidth 12³→16³ grid refinement,
and a signed reference-cell sensitivity certificate on the Na-LTA NVE continuation
trajectory. The fixed-cell comparison is an exact identity certificate. The
24 basin identities persist across 0.40, 0.50, and 0.60 Å, but numerical density-boundary
adjacency changes with bandwidth and grid, so scale selection and topology remain
explicitly unresolved. Stage 11E8a-S3 structural mapping and temporal-support
preparation is next; Stage 11E8b remains closed.

## Stage 11E8a-S1 framework-registered density and attractor pilot

Version `0.20.11a0` selects and validates the all-framework center-of-geometry
translation gauge for the Na-LTA NVE continuation trajectory, compares it against an
independent center-of-mass gauge, preserves the complete represented-time
measure with deterministic pilot quadrature, and executes one Stage 11E1 Na
density plus one Stage 11E2 attractor realization. The result remains
fail-closed: density convergence, reference-cell sensitivity, attractor lineage,
temporal support, force-density agreement, transition paths, and rates are not
inferred from the coarse single-scale pilot. Stage 11E8a-S2 is next; Stage
11E8b remains closed.

## Stage 11E8a-S0 real-trajectory source bootstrap

Version `0.20.10a0` consumes an externally supplied, normalized nominal-300-K Na-LTA continuation
trajectory and binds the exact raw bytes to a physical fixed-cell C0 registration,
a compact E0b Na position/force sample catalog, and the immutable E8a dossier.
The bootstrap validates the required 168-atom composition and leaves equilibrium,
stationarity, density, attractor, temporal, path, and network evidence unresolved.
Its expected status is therefore `blocked_missing_required_evidence`, not
`blocked_missing_trajectory`. Stage 11E8a-S1 now consumes this source-bound bootstrap; Stage 11E8a-S2 is the next implementation boundary and Stage 11E8b remains closed.

## Stage 11E8a pilot dossier and real-data preflight

Version `0.20.9a0` adds a source-bound nominal-300-K Na-LTA continuation pilot dossier and execution
preflight. The package certifies the bundled real reference structure,
2,000-frame topology summary, primitive-ring catalog, 1,300-frame density
benchmark, and plotting summary, but it does not promote those legacy artifacts
to current E0b--E7 site evidence. Because the raw trajectory is not bundled, the
pilot status is explicitly `blocked_missing_trajectory`; Stage 11E8b is not
opened. Real ASE 3.29.0 is used for the reference-structure audit.

## Stage 11E7 observed periodic network and transfer validation

Version `0.20.8a0` composes frozen validated state instances with exact E6b
path ensembles. Observed periodic edges are created only from trajectory
evidence and are compared explicitly with declared structural candidates;
unobserved structural edges and observed off-structural edges remain visible.
Site complexes, validated symmetry orbits, semantic classes, and compact
transferred state models remain distinct from state instances. Held-out or
external application uses certified periodic distances to retained source
anchors, declared domain metadata, radius and ambiguity rejection, and explicit
reproduction, off-network, failed, or domain-mismatch outcomes. No rates,
state merging, symmetry augmentation, or refitting are introduced. Stage 11E8a
Na-LTA NVE continuation pilot analysis is next; the global-PMF branch remains optional.

## Stage 11E6b observed transition-path ensembles and collective-event diagnostics

Version `0.20.7a0` reconstructs exact registered paths from Stage-11E6 passage
brackets, preserves physical cadence and integer periodic translations, retains
optional ring-sector coordination, harmonic, density, PMF, and transformed-force
evidence, and certifies compatible pooling across independent registrations.
Single observations, undersampled path collections, and resolved ensembles remain
distinct; concurrent exchange and concerted-event candidates are diagnostic and
do not create rates or a many-body kinetic model. Stage 11E7 observed-network
and transfer validation is the next mandatory implementation boundary; the
support-limited global PMF branch remains optional.

## Stage 11E6 final hysteretic segmentation and residence statistics

Version `0.20.6a0` converts immutable E4 spatial labels and optional E5b moving
regions into final core-entry/basin-retention state histories. It retains
unsupported gaps, assignment conflicts, moving-boundary evidence, censoring,
static-versus-dynamic membership provenance, represented-time residence and
occupancy statistics, and a threshold/stride stability certificate. Full
transition paths remain Stage 11E6b.

## Stage 11E5b geometry-conditioned site refinement

Version `0.20.5a0` adds optional one-pass framework-only affine center models
for frozen E5 statistical states. Discovery assignments remain fixed, model
selection uses separate blocks, and the dynamic model is retained only when
untouched final validation does not contradict the gain. Frozen and moving
cores/basins, static/dynamic memberships, comoving and boundary motion,
assignment conflicts, and occupancy bounds remain jointly reportable. Stage
11E6 final hysteretic segmentation is the next implementation boundary.

## Interpreter-hotpath policy

Dense numerical work in mdstats is delegated to NumPy, SciPy, FFT, marching-cubes, or other compiled kernels. Python is retained for bounded orchestration over fields, tiles, chunks, and irregular graph states. The 0.19.72a0 Stage-2 pass vectorizes cell-list candidate expansion, metric-stencil minimization, ragged bond-angle accumulation, sparse support-atlas merging, tiled-mesh reconciliation, and fragmented direct density scheduling. See `docs/specs/performance/interpreter_hotpath_policy.md`.

The consolidated maintenance workflow and deferred optimization roadmap are in `docs/arch_manuals/mdstats_interpreter_hotpath_patching_manual.md`.

## Stage 11E5a species-dependent coordination fingerprints and classification

Version `0.20.4a0` converts frozen Stage-11E5 statistical states and their
retained registered ring associations into exact, state-conditioned physical
M--O and M--T sample records. Direct ion coordinates in persistent ring frames
remain authoritative. Equal-index cyclic spectra, boundary-measure angular
moments, rank-safe actual-angle fits, centered-reference residuals,
geometry-forward residuals, phase-locking evidence, and occupancy-conditioned
mixtures are retained as inspectable diagnostics. Conservative point, bilateral,
discrete off-center, smooth/corrugated annular, cage, general, and ambiguous
classes do not move E5 centers or redefine basins. Multiple plausible structural
associations remain separate. Stage 11E5b optional geometry-conditioned site
refinement is next.

## Stage 11E5 joint evidence validation and structural association

Version `0.20.3a0` freezes one selected E2 statistical-state catalog and
combines spatial, temporal, force, force-score, stationarity, geometry,
curvature, and transfer evidence without collapsing disagreement into one
optimistic score. Statistical states are associated with persistent registered
ring, window, or tile/cage objects under an explicit distance radius; ambiguous
associations remain ambiguous and no nearest-object fallback is performed.
Discovery, selection, final-validation, and optional-refit blocks retain their
independence status, while nominal symmetry orbits require conservative
exchangeability checks and never augment samples by default. Force-free data may
produce spatial/temporal validation but cannot claim force validation. Stage
11E5a species-dependent coordination fingerprints and classification is next.

## Stage 11E4 provisional assignment and temporal-persistence diagnostics

Version `0.20.2a0` projects registered E0b species samples onto the exact E2
supported periodic cell complex without nearest-center filling. It retains raw
core, basin, transition, background, unknown, unresolved, and overlap classes;
constructs segment-aware core visits, preliminary residences, jumps, return
excursions, unresolved gaps, and censored exits; and reports local decorrelation,
stride, dwell, excursion, and recrossing diagnostics. Independent ensembles keep
spatial memberships but acquire no invented temporal continuity. These records
remain provisional and do not replace final Stage-11E6 hysteretic segmentation.
Stage 11E5 joint evidence validation and structural association is next.

## Stage 11E3 local mean-force and harmonic/manifold refinement

Version `0.20.1a0` adds PMF-admissible matched-kernel conditional mean-force
fields and source-bound local force refinements for every Stage-11E2 attractor.
Registered Cartesian forces are transformed to the E1 fractional covector
measure before density-score comparison. Point and extended candidates receive
represented-time weighted symmetric force fits, explicit curvature classes,
force-defined centers where identifiable, chart-containment checks, residence
covariance diagnostics, and block uncertainty. Missing or inadmissible force
evidence lowers an independent status and never deletes a spatial candidate.
Stage 11E4 provisional assignment and temporal-persistence diagnostics is next.

## Stage 11E2 deterministic density attractors and supported basins

Version `0.20.0a0` adds source-bound point modes, derivative-supported extended
ridges, unresolved flat components, support-restricted periodic basin ownership,
supported inter-basin saddles, isolated-mode and annular local charts, and
point- or manifold-specific provisional cores. Ordered bandwidth ladders now
produce attractor lineage, split/merge ambiguity, and an explicit scale-consensus
decision. Unsupported or omitted sparse nodes remain unknown and cannot create
background, connectivity, saddles, or relative free-energy offsets. Separate
topology-refinement certificates and optional periodic k-means/HDBSCAN comparison
adapters are included. Stage 11E3 local mean-force and harmonic/manifold
refinement is the next implementation boundary.

## Stage 11E1 periodic species-density estimation

Version `0.19.99a0` adds the source-bound nonparametric density layer downstream
of the Stage-11E0b species catalog. It evaluates a normalized triclinic Gaussian
lattice sum on one explicit physical or reference-material periodic domain, with
separate kernel covariance and analysis geometry metric. Number density,
probability density, score covectors, metric-raised gradient vectors, density
Hessians, local effective sample size, support masks, image-tail certificates,
bandwidth ladders, dense/block-packed realizations, and complete-system block
uncertainty are retained independently. No modes, basins, site labels, free-energy
surfaces, or kinetic objects are inferred. Architecture revision 23 identifies
Stage 11E2 attractor and basin discovery as the next implementation boundary.

## Stage 11E0b registered position-force sample catalog

Version `0.19.98a0` adds the compact, source-bound evidence catalog between
C0 registration and statistical site discovery. One species at a time is stored
in frame-major form with registered positions, transformed force covectors,
represented-time weights, topology-regime identifiers, exact position/force/joint
evidence masks, and conservative PMF admissibility. Independent trajectories may
be pooled only through an explicit fixed-domain registration group. Structural
annotations remain lazy, and no site labels, basins, free-energy surfaces, or
kinetics are inferred. Architecture revision 22 identifies Stage 11E1 as the next
implementation boundary.

## Stage 11E0a scientific density facade

Version `0.19.97a0` establishes the analysis-owned scientific density surface without
changing the established numerical estimators. Dense and block-sparse atomic and
framework fields are exposed through backend-neutral protocols and zero-copy adapters,
while numerical field-construction limits are separated from plotting-owned browser and
mesh admission. Architecture revision 21 identifies Stage 11E0b, the registered
position-force sample catalog, as the next implementation stage.

## Interactive density fitting and partitioned topology

Version `0.19.91a0` completes Stage 11E2 trajectory site assignment and
observed site statistics. It evaluates explicit species-profile basins in the
instantaneous Stage-11C2 ring and Stage-11B tile frames, distinguishes accepted,
annular, ambiguous, transition-region, unassigned, and unresolved outcomes,
tracks periodic site images, and compares accepted transitions against the
Stage-11E1 structural multigraph. Assignment remains descriptive geometric
evidence: no energetic certification, smoothing, or nearest-site fallback is
inferred.

Version `0.19.90a0` completes Stage 11E1 explicit species-dependent site-state
topology. It preserves two oriented ring-side anchors per natural-tiling window,
creates physical-state hypotheses only from an explicit species profile, and
builds a periodic directed multigraph of structural candidate pathways. The
release supports one-sided, bilateral, centered, discrete off-center, annular,
general-multiwell, no-bound, and unresolved regimes plus optional cage
candidates. It does not infer energetic stability, barriers, rates, or
trajectory assignments.

Version `0.19.89a0` completes Stage 11D framework semantics. It derives
generic natural-tile face signatures and ring-order-plus-adjacent-tile interface
identities directly from certified geometry, preserves oriented sides and
periodic translations, and adds an explicit validated LTA profile for D4R,
alpha-cage, beta-cage, and the four 4R/6R/8R interface families. Expected
multiplicities validate classifications only after local signature rules have
been applied; they never force labels.

Version `0.19.88a0` completes Stage 11C2 compatible-frame oxygen-ring
geometry. It reuses the Stage-11B periodic gauge to map fixed Stage-11C1 T/O
identities over compatible frames, retains reference-aligned centers, normals,
side frames, aperture and deformation descriptors, and preserves topology,
gauge, bridge, and degenerate-ring failures as explicit immutable states.

Version `0.19.87a0` completes Stage 11C1 reference oxygen-ring geometry. It
binds every certified natural-tiling window to persistent lifted T and bridging-O
polygons, defines the oxygen projected-area centroid as the geometric ring center,
constructs opposite side-local frames, retains shape and aperture descriptors,
and records explicit unresolved bridge/path states. Framework-path compatibility
is independent of spectator-only connectivity, with an optional strict full-state
source check.

Version `0.19.86a0` completes C2 ionic transport. It integrates fixed-cell,
fully periodic collective current correlations into SI Green-Kubo conductivity,
retains ordered group-pair contributions, adds explicit interval-based plateau
estimation, and compares compatible three-dimensional species diffusion against
the Nernst-Einstein independent-particle estimate with fail-closed provenance
checks and explicit zero-denominator ratio flags.

Version `0.19.85a0` adds collective charge-current construction and ordered
positive-lag current correlations. It resolves per-atom or exact-symbol charges,
requires neutrality, validates exact current-carrying species partitions, retains
fixed/variable-cell and drift provenance, and provides direct and zero-padded FFT
correlation backends with immutable total and ordered group-pair results. The
correlator preserves the raw resolved current and performs no implicit mean-current
subtraction, detrending, smoothing, or symmetrization.

Version `0.19.84a0` adds the D3 self-intermediate scattering function. It
computes direct isotropic angular averages with dimension-correct kernels or
complex directional characteristic functions, rejects q-vector components
outside the selected subspace, preserves q ordering and duplicates, and reuses
the D0 atom/origin block iterator with bounded transient q chunks.

Version `0.19.83a0` adds the D2 non-Gaussian displacement parameter. It
accumulates projected second and fourth moments from the D0 atom/origin block
iterator, applies the rank-correct cumulant prefactor, marks every exact-zero
second-moment lag as undefined, and cross-checks its second moment against D1
and direct MSD.

Version `0.19.82a0` adds the D1 radial self van Hove function. It reuses the
D0 prepared displacement layer, applies an explicit one-, two-, or
three-dimensional physical subspace, retains finite-support overflow instead of
renormalizing it away, and reports an unbinned direct second moment for MSD
cross-checks.

Version `0.19.81a0` adds the D0 shared displacement layer. Measured selection,
coordinate convention, reference cell, drift removal, projection, and complete
input signature are prepared once; direct MSD displacement work is blocked in
both origin and atom dimensions under a deterministic memory target.

Version `0.19.80a0` hardened the VACF/dynamics boundary with explicit physical
analysis subspaces, complete trajectory/selection signatures, deeply immutable
results, strict option validation, and fail-closed MSD/VACF comparison.

Version `0.19.76a0` separates raw contour-extraction safety from visual mesh
targets and final browser budgets. Version `0.19.79a0` also makes the LTA topology example explicitly hysteretic; `0.19.78a0` closed two remaining
robustness gaps. Sparse tiled contours are validated before simplification; an
invalid tile-local reduction is retried without local pre-simplification and, if
needed, repaired by bounded coarse recontouring or the declared cloud fallback.
A failed global simplification restores the last validated mesh instead of
propagating an open surface.

`prepare_framework_dynamics_scene()` accepts a complete `TopologyCatalog`. Global
trajectories and density fields remain shared, while each topology class receives
its own averaged framework and atomic mean-connectivity graph. Partitioned scenes
now use a compact adapter with at most four Plotly traces per category (framework
edges, framework nodes, atomic edges, atomic nodes), all in one-click legend
groups. This keeps a seven-category scene below the balanced 96-trace browser
profile without weakening the browser budget. The LTA example uses hysteretic
framework connectivity and caches the complete topology catalog.

## Exact minimum-image cutoff

Version `0.19.73a0` validates RDF, coordination, connectivity, and neighbor-list
cutoffs against one half of the shortest nonzero periodic lattice translation.
The shortest translation is obtained from a validated ASE Minkowski-reduced
basis.  This replaces the older perpendicular-face-height bound, which was
unnecessarily restrictive for skewed primitive cells such as LTA.

`mdstats` converts VASP, LAMMPS, and ASE-supported structures into one normalized
`AtomisticFrameCollection` and provides transparent structural and dynamical
statistics.

The central object can represent:

- a time-ordered molecular-dynamics trajectory;
- an independent statistical ensemble of structures;
- an arbitrary selected set of frames for clustering or rare-event analysis;
- a single static structure.

The frame relationship is explicit through `FrameSemantics`.

## Repository layout

```text
mdstats/              Python package
docs/specs/           module specifications mirroring mdstats/
docs/arch_manuals/    cross-module architecture manuals
audits/               validation and integration audits
benchmarks/            benchmark scripts, raw data, and summaries
examples/              rendering examples and generation scripts
release/               manifests and checksums
dist/                  wheel and source distribution
tests/                 regression tests and fixtures
```

Naming rules are documented in `docs/README.md`, `audits/README.md`, and
`benchmarks/README.md`.

## Installation

```bash
python -m pip install .
```

Dependencies are NumPy, SciPy, ASE, Matplotlib, and NetworkX. Interactive 3-D
graph rendering is optional:

```bash
python -m pip install ".[interactive]"
```

The base package imports and all noninteractive analyses remain usable when Plotly
is absent.


## Production periodic-neighbor subsystem

Version `0.17.0a3` retains the completed stages S0-S4 of the exact triclinic cell-list and
Verlet-cache acceleration program. RDF, coordination, bond-angle, and every
distance-based atomic-connectivity mode now use one backend-neutral policy.

```python
from mdstats import NeighborSearchOptions

options = NeighborSearchOptions(
    backend="auto",     # auto | dense | cell_list
    cache_mode="auto", # auto | none | verlet
    skin=0.5,
)
```

The production default is conservative and exact:

- estimate dense pair work for each normalized request;
- use dense below `32768` pair evaluations;
- use the exact triclinic cell list at or above that threshold;
- activate deformation-aware Verlet reuse automatically only for eligible
  multi-frame trajectories;
- keep independent ensembles and single-frame selections stateless by default;
- retain explicit `cache_mode="verlet"` as an expert override;
- disable an unproductive cache after three consecutive completed intervals
  with no successful reuse;
- fall back only to another exact path and record the event;
- store deterministic backend, request, candidate, rebuild, safety-margin, and
  singular-value diagnostics in result metadata.

Users may always force the dense oracle or a stateless cell list:

```python
dense = NeighborSearchOptions(backend="dense")
cell = NeighborSearchOptions(backend="cell_list", cache_mode="none")
cached = NeighborSearchOptions(
    backend="cell_list",
    cache_mode="verlet",
    deformation_aware=True,
    skin=0.5,
)
```

Low-level `NeighborSearchSession` and `VerletCacheOptions` remain available for
direct request-keyed workflows. The fixed-cell low-level default is preserved;
the high-level S4 policy enables the proven variable-cell bound explicitly.

Normative documents and reports:

```text
docs/specs/analysis/neighbor_search_spec.md
docs/specs/analysis/neighbor_search_spec.pdf
docs/specs/analysis/_verlet_cache_deformation_spec.md
docs/specs/analysis/_verlet_cache_spec.md
docs/specs/analysis/_cell_list_spec.md
docs/arch_manuals/periodic_neighbor_search_architecture.md
audits/analysis/neighbor_search_integration_audit.md
audits/analysis/neighbor_search_spec_audit.md
benchmarks/neighbor_search_benchmark.md
```

Specification convention: every new module or staged implementation
specification is maintained in both Markdown and PDF from one Markdown source.
A specification defines data structures and function calls, input and output
types, input constraints, motivation, theory, algorithm, and edge cases. The
writing remains compact, explicit, and suitable for human review and AI
contextualization.

## Orientation-aware framework topology

Version `0.15.0` repairs Stage 2 projected-edge identity for asymmetric linker
paths. Framework adjacency remains undirected, but one edge retains an ordered
canonical atomic path and an exact reverse traversal.

```python
from mdstats import FrameworkPathRule

rule = FrameworkPathRule.from_symbols(
    "Si-O-S-Al",
    ("O", "S"),
    endpoint_symbols=("Si", "Al"),
    edge_kind="asymmetric_bridge",
)
```

The rule accepts `Si-O-S-Al` and its complete reverse `Al-S-O-Si`. It does not
accept `Si-S-O-Al`. Endpoint species and linker order are canonicalized together
as one complete path signature.

Canonical edges provide `edge.oriented(+1)`, `edge.oriented(-1)`, and
`edge.oriented_from(source_vertex)` for ring traversal and diagnostics. These
views reverse atom order, linker order, and periodic shifts together without
creating a directed authoritative graph.

Normative documents:

```text
docs/arch_manuals/framework_ring_architecture.md
docs/specs/analysis/framework_topology_spec.md
docs/specs/plotting/framework_topology_graph_spec.md
docs/specs/analysis/topology_catalog_spec.md
```

## Exact multi-frame topology catalogs

Version `0.16.0` implements Stage 3 of the framework/ring architecture. The
module projects each referenced atomic-connectivity state once, reconciles exact
Stage 2 framework-topology classes, and records semantics-appropriate frame
organization.

```python
from mdstats import (
    TopologyCatalogOptions,
    build_topology_catalog,
)

catalog = build_topology_catalog(
    collection,
    connectivity_result,
    framework_mapping,
    catalog_options=TopologyCatalogOptions(
        mode="catalog",
        minimum_persistent_frames=2,
    ),
)

print(catalog.consistency)
print(catalog.topology_counts)
```

Catalog mode stores one `FrameworkTopology` per exact class, together with:

- `frame_topology_ids` and one `TopologyFrameGroup` per class;
- maximal `TopologySegment` runs and exact `TopologyTransition` records for
  trajectories;
- no invented temporal segmentation for ensembles;
- source connectivity-state provenance and deterministic serialization.

Class identity uses canonical `FrameworkEdgeKey` records. Complete path reversal
reconciles, while asymmetric linker order remains distinct. Short trajectory
segments may be labeled transient, but are never smoothed, deleted, or merged.

Normative documents:

```text
docs/specs/analysis/topology_catalog_spec.md
docs/specs/analysis/atomic_connectivity_spec.md
docs/specs/analysis/framework_topology_spec.md
docs/arch_manuals/framework_ring_architecture.md
```

## VACF-derived spectra, VDOS, and diffusion consistency

Version `0.19.9a0` includes the VS1 VACF-derived velocity spectrum, VS3
explicit VDOS normalization, GK1 running Green-Kubo self diffusion, VP1
plotting, G2 explicit diffusion estimation and MSD/VACF comparison, and G3/GK4
VACF-to-MSD reconstruction.

```python
from mdstats import (
    compare_msd_vacf_diffusion,
    compute_msd,
    compute_vacf,
    compute_vacf_spectrum,
    compute_vdos,
    estimate_diffusion_plateau,
    integrate_vacf_to_diffusion,
    plot_vacf_diffusion,
    plot_velocity_spectrum,
    reconstruct_msd_from_vacf,
)

vacf = compute_vacf(collection, species="Na", weights="uniform")
spectrum = compute_vacf_spectrum(vacf)
vdos = compute_vdos(spectrum, normalization="unit_area")
running = integrate_vacf_to_diffusion(vacf, dimensions=3)
reconstructed_msd = reconstruct_msd_from_vacf(vacf)
estimate = estimate_diffusion_plateau(
    running,
    time_range_ps=(4.0, 8.0),
    slope_tolerance=1.0e-3,
)
msd = compute_msd(collection, species="Na")
comparison = compare_msd_vacf_diffusion(
    msd,
    estimate,
    msd_fit_range_ps=(4.0, 8.0),
    dimensions=3,
)
fig, ax = plot_velocity_spectrum(vdos, x_axis="cm^-1")
fig_d, ax_d = plot_vacf_diffusion(running, diffusion_unit="cm2/s")
```
A complete native-velocity workflow for watcher-generated VASP `TRAJECTORY` files is provided at:

```text
examples/vacf_dynamics/vasp_contcar_trajectory_vdos_diffusion.py
```

It writes separate VDOS and running Green-Kubo diffusion figures and CSV tables.


`compute_vdos()` uses the discrete one-sided FFT-bin measure and never applies
trapezoidal endpoint weights. Degrees-of-freedom normalization requires an
explicit target, and material negative spectral weight is rejected.

`integrate_vacf_to_diffusion()` returns the full sampled running curve and
does not silently choose a plateau or fit a tail.
`estimate_diffusion_plateau()` requires an explicit interval in G2, reports
the interval mean and diagnostics, and does not treat adjacent running values
as independent uncertainty samples. Automatic `stable_window` selection
remains deferred.

`compare_msd_vacf_diffusion()` fits an explicit time-averaged laboratory-frame
MSD interval and compares it with the VACF estimate without declaring either
estimator authoritative. Atom selection, drift convention, source identity
when available, component, and dimensions must agree.

`reconstruct_msd_from_vacf()` uses two cumulative trapezoidal moments to
reconstruct the displacement curve implied by the physical self VACF. It is an
optional consistency diagnostic; direct position-based MSD remains primary and
finite-record agreement is not forced.

`plot_velocity_spectrum()` accepts either a velocity spectrum or VDOS and can
show total, Cartesian, or selected per-atom curves. Alternate spectral x axes
reuse stored coordinates; the ordinate remains the stored THz-based density.

The default atomic-density backend is selected automatically. Production local-sparse admission uses the exact mixed direct/FFT execution plan: nominal source-stencil contributions remain diagnostic, while actual direct pairs, FFT work, memory, and calibrated wall time control feasibility.

As of `0.20.144a0`, PAR-DENS5 adds an optional FP64 CUDA execution backend for selected density kernels. GPU use is subordinate to the same scientific operators: `MDSTATS_DENSITY_GPU=auto` (default) selects CUDA only when device/VRAM availability and a transfer-aware cost estimate justify it, `off` forces the qualified CPU reference path, and `force` requests CUDA subject to the hard VRAM/host-memory safeguards. CUDA is optional; no GPU package is a hard mdstats dependency, at most one major density field owns a GPU at a time, usable VRAM is capped at 80% of the currently free device memory, and any unavailable/failed GPU path falls back to FP64 CPU execution.

As of `0.20.145a0`, PAR-DENS6 closes the long-trajectory density program. The production auto-tuner is execution-only: it may select bounded field concurrency, chunk depth, FFT workers, and optional CPU/GPU execution, but it cannot change grid resolution, Gaussian/operator identity, normalization, support, HDR semantics, or scientific content identities. Scene-level Phase-B now freezes each sparse field's direct/FFT tile partition before worker admission, eliminating worker-count-dependent summation-path changes. On the supplied 10,001-frame Na-LTA trajectory with a fixed Na/Si/O 64^3 local-sparse, 0.5 Angstrom operator, two isolated auto repeats and two one-worker references gave a median total-wall speedup of about 1.114x with max |Delta rho| = 0 for all species, identical content identities/integrals/HDR thresholds, and CPU/RAM safeguards satisfied. The authenticated qualification is `release/par_dens6_na_lta_qualification.json`; CUDA performance remains conditional on a CUDA-capable host.


Normative documents:

```text
docs/specs/analysis/_quadrature_spec.{md,pdf}
docs/specs/analysis/vacf_transport_spec.{md,pdf}
docs/specs/analysis/diffusion_estimation_spec.{md,pdf}
docs/specs/analysis/velocity_spectrum_spec.{md,pdf}
docs/specs/analysis/vdos_spec.{md,pdf}
docs/specs/plotting/velocity_spectrum_spec.{md,pdf}
docs/arch_manuals/vacf_dynamics_architecture.{md,pdf}
```

## Periodic primitive-ring enumeration

The corrected Stage-4 primitive-ring foundation remains available unchanged.
The default method builds a bounded lifted shortest-path index, constructs even
and odd cycles from tied shortest half-paths, and applies the primitive
no-shortcut criterion.

```python
from mdstats import (
    PrimitiveRingOptions,
    PrimitiveRingSearchMethod,
    enumerate_primitive_rings,
    expand_primitive_ring_atomic_walk,
)

rings = enumerate_primitive_rings(
    framework_topology,
    options=PrimitiveRingOptions(max_ring_size=8),
)

# The earlier fast subset remains available explicitly.
edge_shortest = enumerate_primitive_rings(
    framework_topology,
    options=PrimitiveRingOptions(
        method=PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST,
        max_ring_size=8,
    ),
)

print(rings.ring_size_counts)
walk = expand_primitive_ring_atomic_walk(framework_topology, rings.rings[0])
```

The periodic search state is `(atom_index, image_shift)`. Even candidates join
two internally disjoint shortest paths between exact lifted antipodes. Odd
candidates join two shortest root paths with one exact lifted closing edge.
Candidate construction retains all tied paths within explicit limits; the
remaining maximal half-cycle pairs are checked through the shared distance
index.

The two methods have different semantics:

```text
SHORTEST_PATH_PAIRS   -> PRIMITIVE_NO_SHORTCUT
REMOVED_EDGE_SHORTEST -> EDGE_SHORTEST_SUBSET
```

For the uniform 300 K Na-LTA topology through ring size eight, the corrected
default returns 36 four-rings, 40 six-rings, and 6 eight-rings. The edge-shortest
subset returns the earlier 36 four-rings and 16 six-rings. These are topological
cycle counts; conventional ring sites and pore windows still require downstream
geometry and cage/portal classification.

The implementation cites the shortest-path candidate constructions of Horton
and Vismara and the primitive-ring work of Goetzke-Klein and Yuan-Cormack. The
periodic lifted-state, decorated multigraph, resource, and serialization layers
are mdstats-specific adaptations.

Normative documents and example:

```text
docs/specs/analysis/primitive_ring_spec.md
docs/arch_manuals/framework_ring_architecture.md
examples/primitive_ring/na_lta_300K/
```

## Topology-statistics TS0-TS5 pipeline

Version `0.17.0a5` contains the graph-independent TS0 common foundation, TS1
atomic-connectivity statistics, TS2 framework-topology statistics, TS3 shared
trajectory-only temporal statistics, TS4 exact atomic/framework cross-layer
alignment, and TS5 standard plotting plus JSON/CSV export. Together they provide exact integer
probability mass functions, scalar population summaries, catalog occupancy and
Shannon diversity, graph-specific descriptors, exact residence intervals,
changed-state timelines, return lags, and entity-presence episodes.

```python
from mdstats import (
    AtomicStatisticsOptions,
    compute_atomic_connectivity_statistics,
)

options = AtomicStatisticsOptions.from_species_pairs(
    [("Si", "O"), ("Al", "O"), ("Na", "O")]
)
stats = compute_atomic_connectivity_statistics(
    atomic_result,
    times=times_ps,
    time_unit="ps",
    options=options,
)
na_o_distribution = stats.pair("Na", "O").contact_count_distribution
atomic_timeline = stats.temporal_statistics.state_statistics

from mdstats import compute_topology_statistics
combined = compute_topology_statistics(atomic_result, topology_catalog)
print(combined.summary.interpretation)

from mdstats import plot_pair_count_distribution, export_topology_statistics
fig, ax = plot_pair_count_distribution(combined, "Na", "O")
fig.savefig("na_o_contact_distribution.pdf")
export_topology_statistics(combined, "topology_tables", prefix="na_lta")
```

The common layer remains graph-independent. TS1 consumes completed
`AtomicConnectivityResult` objects; TS2 consumes completed `TopologyCatalog`
objects. TS3 standardizes temporal organization only for trajectories and rejects
ensemble storage order as time. Atomic contact episodes use gauge-invariant atom
pairs, while framework episodes use canonical decorated `FrameworkEdgeKey`
identity. TS4 validates exact catalog derivation, builds atomic-state/framework-
class contingency tables, and classifies reconciled trajectory boundaries.
TS5 consumes completed result objects only. Plotting returns Matplotlib figure/axes
objects, while the I/O layer writes the authoritative JSON payload and deterministic
long-form CSV tables.

Normative documents:

```text
docs/arch_manuals/topology_statistics_architecture.md
docs/specs/analysis/topology_statistics/combined_spec.md
docs/specs/analysis/topology_statistics/_common_spec.md
docs/specs/analysis/topology_statistics/atomic_spec.md
docs/specs/analysis/topology_statistics/framework_spec.md
docs/specs/analysis/topology_statistics/temporal_spec.md
docs/specs/plotting/topology_statistics_spec.md
docs/specs/io/topology_statistics_spec.md
```

## Core data model

```python
from mdstats import AtomisticFrameCollection, FrameSemantics
```

Two semantics are supported:

```python
FrameSemantics.TRAJECTORY
FrameSemantics.ENSEMBLE
```

A trajectory asserts that frame order and physical time are meaningful. Its
fractional coordinates are continuous across periodic boundaries, and missing
velocities are reconstructed when possible.

An ensemble treats every frame independently. No temporal continuity is
assumed; periodic coordinates are wrapped separately in each frame, and
velocities are deliberately absent. The word *ensemble* here includes any
independent frame set, not only a rigorously weighted thermodynamic ensemble.

The collection stores a fixed atom population:

```text
atomic_numbers       (N,)
masses               (N,)
pbc                   (3,)
frame_ids             (T,)
steps                 (T,) or None
times                 (T,) or None
cells                 (T, 3, 3)
origins               (T, 3)
fractional_positions  (T, N, 3)
velocities            (T, N, 3) or None
forces                (T, N, 3) or None
```

Cells use ASE's row-vector convention:

```text
cartesian = fractional @ cell
```

For trajectories, `fractional_positions` are time-unwrapped. For ensembles,
they are independently wrapped in periodic directions.

## Reading time-ordered trajectories

### VASP

```python
from mdstats import read_vasp_frames

trajectory = read_vasp_frames("vasprun.xml")
trajectory = read_vasp_frames("XDATCAR", timestep_fs=1.0)

# Custom stream of complete per-step MD CONTCAR restart records.
trajectory = read_vasp_frames(
    "TRAJECTORY",
    format="vasp-contcar-trajectory",
    timestep_fs=1.0,
)
```

The custom `TRAJECTORY` format preserves VASP-written Cartesian ionic
velocities. It is created by archiving each complete `CONTCAR` as a zero-padded
`CONTCAR.n` snapshot and concatenating the ordered files. Reproducible scripts
and the exact recipe are in `examples/vasp_contcar_trajectory/`; the normative
format is `docs/specs/io/vasp_contcar_trajectory_spec.md`. Missing native
velocities are a hard error and are never reconstructed from positions.

### LAMMPS

```python
from mdstats import read_lammps_frames

trajectory = read_lammps_frames(
    "trajectory.dump",
    log_file="log.lammps",
    type_map={1: "Si", 2: "O", 3: "Na"},
)
```

LAMMPS atoms are sorted by persistent atom ID in every frame. The IDs are then
discarded after identity and species consistency are verified.

## Reading independent frame ensembles

Random or sparsely selected MD frames can be read directly as independent
samples:

```python
ensemble = read_lammps_frames(
    "trajectory.dump",
    units="metal",
    start=0,
    stop=10000,
    stride=100,
    frame_semantics="ensemble",
)
```

```python
ensemble = read_vasp_frames(
    "XDATCAR",
    start=0,
    stop=1000,
    stride=20,
    frame_semantics="ensemble",
)
```

No physical timestep is needed for an ensemble. Native velocities, when
present, are discarded to prevent accidental temporal analysis.

Read several independent static structure files with:

```python
from mdstats import read_structure_collection

ensemble = read_structure_collection(
    ["POSCAR.001", "POSCAR.014", "POSCAR.093"],
    format="vasp",
)
```

All frames must have the same atom count, species order, masses, and PBC flags.
Cells and atomic coordinates may differ.

## Reading one static structure

```python
from mdstats import read_structure

structure = read_structure("POSCAR")
structure = read_structure("CONTCAR")
structure = read_structure("framework.cif")
structure = read_structure(
    "system.data",
    format="lammps-data",
    type_map={1: "Si", 2: "O", 3: "Na"},
)
```

A static structure is represented as a one-frame ensemble.

## Extracting independent samples from a trajectory

```python
sampled = trajectory.select_frames(
    [10, 87, 205, 901],
    frame_semantics="ensemble",
)
```

or:

```python
sampled = trajectory.as_ensemble()
```

Conversion to an ensemble wraps every frame independently and drops velocity
data. An ensemble cannot later be reinterpreted as a trajectory because time
continuity has been discarded.

`frame_ids` provide stable identifiers inside the current collection. Selected
subsets record parent frame IDs in metadata, which is useful for clustering,
active-learning selection, and rare-event traceability.

## Structural analyses

RDF, coordination, and bond-angle analysis accept trajectories, ensembles,
and single-frame structures. Pair geometry is generated by one shared
minimum-image CSR neighbor kernel using the strict convention
`distance < cutoff`.

```python
from mdstats import compute_pair_rdf

rdf_na_o = compute_pair_rdf(
    ensemble,
    species_a="Na",
    species_b="O",
    r_max=5.0,
)
```

Convert a robust RDF first minimum into a reusable cutoff:

```python
from mdstats import PairCutoff, PairCutoffRegistry

na_o = PairCutoff.from_rdf_minimum(rdf_na_o)
cutoffs = PairCutoffRegistry.from_cutoffs([na_o])
```

The same cutoff object can drive coordination analysis:

```python
from mdstats import compute_coordination_distribution

coordination = compute_coordination_distribution(
    ensemble,
    species_a="Na",
    species_b="O",
    cutoff=na_o,
)
```

and species-resolved bond-angle statistics:

```python
from mdstats import CoordinationCondition, compute_bond_angle_distribution

angles = compute_bond_angle_distribution(
    ensemble,
    triplet=("O", "Na", "O"),
    cutoffs=cutoffs,
    coordination_filters=[
        CoordinationCondition.exact("O", 6),
    ],
    per_frame=True,
)
```

Combined-species coordination filters use a set union. For example,
`CoordinationCondition.exact(("Si", "Al"), 2)` selects bridging oxygen with
two total framework-cation neighbors while allowing different Si-O and Al-O
cutoffs in the registry.

For an ensemble, structural functions average over independent frames. For a
single structure, the result contains one structural sample. Per-frame angle
histograms can be retained as descriptors for later clustering and rare-event
selection.

## Atomic connectivity

`mdstats` provides explicit periodic atomic graph construction. Connectivity
is a scientific model distinct from RDF, radial coordination, and neighbor-angle
statistics. A persistent `ConnectivityScope` selects atom identities, while a
connectivity definition determines which atomic edges exist.

```python
from mdstats import (
    ConnectivityScope,
    DistanceConnectivity,
    PairCutoffRegistry,
    compute_atomic_connectivity,
)

framework_scope = ConnectivityScope.from_selection(
    included_atom_indices=initial_framework_atom_indices,
)

definition = DistanceConnectivity(
    cutoffs=PairCutoffRegistry.from_cutoffs([si_o, al_o]),
    scope=framework_scope,
)

connectivity = compute_atomic_connectivity(
    collection,
    definition,
)
```

Available definitions include instantaneous distance connectivity, trajectory-only
two-cutoff hysteresis, order-independent reference connectivity for trajectories
or ensembles, and explicit user-supplied edge sets. Repeated canonical graphs are
compressed into uniform or partitioned state catalogs; trajectories additionally
record contiguous state segments and exact added/removed atom-pair transitions.

Connectivity scope is fixed by atom identity. It does not remove an atom because
the atom leaves a slab or enters a liquid. Dynamic region membership and framework
roles are separate future layers.


## Graph visualization

`mdstats` provides a renderer-independent decorated-graph view, a static
Matplotlib 2-D backend, renderer-independent periodic materialization, and an
optional interactive Plotly 3-D backend.

A publication-oriented 2-D view can be rendered directly from an atomic
connectivity result:

```python
from mdstats import (
    Graph2DRenderOptions,
    GraphLayoutOptions,
    LocalUnwrappedDisplay,
    plot_atomic_connectivity_2d,
)

rendered_2d = plot_atomic_connectivity_2d(
    collection,
    connectivity,
    frame_index=0,
    layout=GraphLayoutOptions(method="physical", projection="pca"),
    periodic=LocalUnwrappedDisplay(center_node_key=0, hop_radius=4),
    options=Graph2DRenderOptions(show_axes=False),
)
rendered_2d.figure.savefig("connectivity.svg", bbox_inches="tight")
```

The same scientific graph and periodic-display contract drive interactive 3-D
inspection:

```python
from mdstats import (
    Graph3DRenderOptions,
    LocalUnwrappedDisplay,
    plot_atomic_connectivity_3d,
)

rendered_3d = plot_atomic_connectivity_3d(
    collection,
    connectivity,
    frame_index=0,
    periodic=LocalUnwrappedDisplay(center_node_key=0, hop_radius=4),
    options=Graph3DRenderOptions(
        title="Local atomic connectivity",
        camera_projection="orthographic",
        cell_mode="reference",
    ),
)
rendered_3d.write_html("connectivity.html")
```

Three periodic display modes are available:

```python
CanonicalCellDisplay()
LocalUnwrappedDisplay(center_node_key=0, hop_radius=4)
ExpandedCellDisplay(image_ranges=((0, 1), (0, 1), (0, 0)))
```

`DecoratedGraphView` separates scientific graph identity from presentation. G4
materializes explicit display nodes and edges while preserving source mappings:
replicas and ghosts never become new scientific atoms. Focus, filters, styles,
periodic expansion, and complexity limits are recorded in render results; no graph
object is silently sampled or coarsened.

For dense graphs, interactive 3-D views are intended for diagnosis and exploration,
while carefully selected 2-D projections remain preferable for publication. Future
framework, ring, site, and cage adapters will reuse the same graph-view, periodic,
and renderer contracts.

## Temporal analyses

MSD requires explicit trajectory semantics, at least two frames, and a physical
uniform time grid:

```python
from mdstats import compute_msd

msd = compute_msd(
    trajectory,
    species="Na",
    mode="time_averaged",
)
```

Passing an ensemble raises `TrajectoryRequiredError`. VACF and future
autocorrelation modules use the same guards:

```python
collection.require_trajectory("VACF")
collection.require_minimum_frames(2, "VACF")
times = collection.require_time_axis("VACF")
velocities = collection.require_velocities("VACF")
```

## Velocity autocorrelation

VACF requires a uniformly sampled time-ordered trajectory with velocities:

```python
from mdstats import compute_vacf

vacf = compute_vacf(
    trajectory,
    species="Na",
    weights="uniform",
    backend="auto",
)
```

The canonical result stores the raw weighted self-correlation. Derived views
include `scalar_mean`, `normalized_scalar()`, and arbitrary directional
projection through `project_direction()`. Mass weighting is available for later
vibrational-density-of-states analysis. Spectral transformation and
Green-Kubo integration remain separate explicit modules.

## Capability properties

```python
collection.is_trajectory
collection.is_ensemble
collection.is_single_frame
collection.has_time_axis
collection.has_velocities
collection.has_forces
collection.coordinates_are_time_unwrapped
```

## Fixed-population constraint

`AtomisticFrameCollection` intentionally assumes one atom mapping across all
frames. It rejects changes in:

- atom count;
- persistent source IDs;
- species at a canonical atom index;
- mass at a canonical atom index;
- PBC flags.

Bonding and coordination may change freely. Collections with different
compositions or atom counts require a future ragged dataset abstraction rather
than this dense fixed-shape object.

## Internal units

| Quantity | Unit |
|---|---|
| Position and cell | Å |
| Time | ps |
| Velocity | Å/ps |
| Force | eV/Å |
| Energy | eV |
| Stress and pressure | eV/Å³ |
| Mass | atomic mass unit |
| Temperature | K |

Stress is stored in the tensile-positive continuum convention. Pressure is

\[
P = -\frac{1}{3}\operatorname{tr}\boldsymbol{\sigma}.
\]

## Design specifications

The source distribution includes implementation specifications for the core
frame collection and analysis modules:

- `docs/specs/collection_spec.md`
- `docs/specs/analysis/msd_spec.md`
- `docs/specs/analysis/_displacement_common_spec.md`
- `docs/specs/analysis/vacf_spec.md`
- `docs/specs/analysis/_fft_spec.md`
- `docs/specs/analysis/rdf_spec.md`
- `docs/specs/analysis/coordination_spec.md`
- `docs/specs/analysis/atomic_connectivity_spec.md`
- `docs/specs/analysis/primitive_ring_spec.md`
- `docs/specs/plotting/index.md`
- `docs/specs/plotting/graph_view_spec.md`
- `docs/specs/plotting/graph_styles_spec.md`
- `docs/specs/plotting/graph_2d_spec.md`
- `docs/specs/plotting/periodic_graph_spec.md`
- `docs/specs/plotting/graph_3d_spec.md`
- `docs/specs/plotting/atomic_connectivity_graph_spec.md`

`docs/specs/analysis/_fft_spec.md` documents the private shared padding,
positive-lag correlation, pair-count, and memory-planning conventions used by
MSD and VACF. It is an internal maintenance contract, not a public API.

## Validation

Run the test suite with:

```bash
python -m pytest -q
```

## FFT-accelerated MSD

```python
from mdstats import compute_msd

result = compute_msd(
    collection,
    species="Na",
    mode="time_averaged",
    backend="auto",
)
```

`backend="fft"` is available for all-origin time-averaged MSD. Fixed-origin MSD
and non-unit `origin_stride` use the direct estimator. The direct estimator now
consumes the D0 displacement iterator, which bounds both origin and atom work
under a 256 MiB default target and records the resolved block plan in result
metadata.

## Compact framework visualization

Framework-topology views can reduce vertex clutter without changing scientific
graph identity:

```python
from mdstats import GraphStyle, NodeDisplayMode

dot_style = GraphStyle.framework_default(
    node_display_mode=NodeDisplayMode.DOTS,
    node_dot_size=16.0,
)

edge_only_style = GraphStyle.framework_default(
    node_display_mode=NodeDisplayMode.HIDDEN,
)
```

`DOTS` preserves species colors using small circular points. `HIDDEN` creates an
edge-only view while keeping all node keys, endpoint indices, and periodic geometry
in the returned render result.



Version `0.19.6a0` also centralizes velocity-input preparation and adds memory-aware atom-spectrum planning for the forthcoming direct Welch estimator.


## VS2 direct Welch velocity spectra

Version `0.19.7a0` adds `compute_velocity_spectrum()`, a direct atom-blocked
Welch estimator for uniformly sampled trajectory velocities. It shares the
VACF atom-selection, weight, drift, and per-atom semantics; returns the common
`VelocitySpectrumResult`; and forms only equal-atom self periodograms. The
implementation supports component and Hermitian tensor spectra, explicit
segment overlap and windowing, optional segment-mean detrending, and bounded
memory. The method is attributed to Welch (1967); mdstats-specific aggregation
and validation choices are documented in
`docs/specs/analysis/velocity_spectrum_spec.md`.

## Certified natural-face search from a master refinement

Version `0.19.25a0` implements Stage 10B. The backend searches every
symmetry-closed subset of bounded locally strong ring interfaces represented in
one exact Stage-9 master tetrahedral refinement.

```python
from mdstats.analysis import search_natural_tilings_from_master_refinement

result = search_natural_tilings_from_master_refinement(
    view=view,
    embedding=embedding,
    symmetry_discovery=symmetry_discovery,
    ring_index=ring_index,
    strength_catalog=strength_catalog,
    master_complex=master_complex,
    master_partition=master_partition,
    compatibility=compatibility,
)

print(result.status)
print(result.catalog.outcome)
```

Omitted scientific interfaces merge tetrahedra. Exact translation-labelled
connectivity rejects lifted slabs or channels with nonzero translation cycles;
finite components are rebuilt as tile orbits, re-certified by the Stage-9
partition checker, and passed through Stage-10A properness certification. Every
inclusion-maximal viable splitting is retained. The result is complete only
relative to the supplied master refinement, fixed witness assignment, bounded
ring-strength domain, and declared resources.

Normative documents:

```text
docs/specs/analysis/natural_tiling_search_spec.md
docs/specs/analysis/natural_tiling_search_spec.pdf
docs/arch_manuals/framework_ring_architecture.md
audits/analysis/natural_tiling_search_audit.md
```


## Primitive-ring-bound full rebuild and refinement comparison

Version `0.19.26a0` implements Stage 10C. Increasing the primitive-ring bound is
a hard invalidation boundary: every ring-derived symmetry, strength, face,
compatibility, complex, partition, search, and natural-tiling result is rebuilt
from the new primitive-ring catalog.

```python
from mdstats.analysis import (
    PrimitiveBoundBuild,
    run_primitive_bound_refinement,
)

def rebuild_for_bound(K: int) -> PrimitiveBoundBuild:
    # Reconstruct the complete source-bound Stage 4-10B stack for K.
    ...

report = run_primitive_bound_refinement(
    bounds=(8, 10, 12),
    rebuild=rebuild_for_bound,
)

print(report.status)
print(report.stable_tested_suffix_start)
for transition in report.transitions:
    print(transition.lower_bound, transition.upper_bound, transition.status)
    print(transition.changes)
```

Cross-bound comparison uses stable scientific keys rather than dense IDs or
catalog-bound digests. A primitive ring that disappears under two complete
increasing bounds is an invalid monotonicity violation. An incomplete rebuild
remains `UNRESOLVED`; an unchanged tested suffix is not presented as a proof for
all larger untested bounds.

Normative documents:

```text
docs/specs/analysis/natural_tiling_refinement_spec.md
docs/specs/analysis/natural_tiling_refinement_spec.pdf
docs/arch_manuals/framework_ring_architecture.md
audits/analysis/natural_tiling_refinement_audit.md
```

## LTA end-to-end natural-tiling ground gate

Version `0.19.27a0` implements Stage 10D for the exact unlabeled LTA net.

```python
import json
from pathlib import Path

from mdstats.analysis import (
    FrameworkTopology,
    certify_lta_natural_tiling,
)

topology = FrameworkTopology.from_dict(
    json.loads(Path("na_lta_framework_topology.json").read_text())
)
gate = certify_lta_natural_tiling(topology)

print(gate.status)
for observation in gate.observations:
    print(observation.primitive_ring_bound)
    print(observation.tile_multiplicities)
    print(observation.reduced_multiplicity_ratio)
```

The gate independently rebuilds primitive rings, depth-one bounded strength, and
exact ring-polygon geometry at `K = 8, 10, 12`. It certifies 36 four-ring, 16
six-ring, and 6 eight-ring faces, records the 32 new strong twelve-rings at
`K = 12` as nonplanar exclusions, reconstructs ten translation-labelled tile
shells, proves properness under the complete order-96 group, and certifies an
exact convex periodic partition. The recovered tile multiplicities are
`6:2:2`, or `3:1:1`.

Normative documents:

```text
docs/specs/analysis/lta_natural_tiling_gate_spec.md
docs/specs/analysis/lta_natural_tiling_gate_spec.pdf
docs/arch_manuals/framework_ring_architecture.md
audits/analysis/lta_natural_tiling_gate_audit.md
```

## Registered framework dynamics and atomic trajectories

Version `0.19.30a0` adds a prepared mean-framework scene and selected atomic
trajectory overlays to the existing Plotly 3-D graph viewer.

```python
from mdstats import (
    FrameworkDynamicsOptions,
    TrajectoryAtomSelection,
    prepare_framework_dynamics_scene,
    plot_framework_dynamics_3d,
)

scene = prepare_framework_dynamics_scene(
    collection,
    framework_topology,
    trajectory_selection=TrajectoryAtomSelection(species=("Na",)),
    options=FrameworkDynamicsOptions(
        registration_mode="framework_registered",
        trajectory_display_mode="continuous",
    ),
)

rendered = plot_framework_dynamics_3d(scene)
rendered.write_html("na_framework_trajectory.html")
```

Material coordinates remove homogeneous cell deformation, laboratory coordinates
retain it, and framework registration additionally removes the mean framework
translation. Folded paths are split at cell crossings instead of drawing false
diagonals. Independent ensembles may produce a mean framework but cannot produce
trajectory lines.

Normative document:

```text
docs/specs/plotting/framework_dynamics_spec.md
docs/specs/plotting/framework_dynamics_spec.pdf
```

## Periodic atomic-density clouds

Version `0.19.31a0` adds normalized time- or ensemble-averaged atomic occupancy
fields to the same registered 3-D framework scene.

```python
from mdstats import (
    AtomicDensity3DRenderOptions,
    AtomicDensityOptions,
    AtomicDensitySelection,
    FrameworkDynamicsOptions,
    prepare_framework_dynamics_scene,
    plot_framework_dynamics_3d,
)

scene = prepare_framework_dynamics_scene(
    collection,
    framework_topology,
    atomic_density_selections=(
        AtomicDensitySelection(species=("Na",), label="Na occupancy"),
        AtomicDensitySelection(species=("O",), label="O occupancy"),
    ),
    atomic_density_options=AtomicDensityOptions(
        grid_shape=(64, 64, 64),
        gaussian_bandwidth=0.30,
    ),
    options=FrameworkDynamicsOptions(
        registration_mode="framework_registered",
    ),
)

rendered = plot_framework_dynamics_3d(
    scene,
    density_options=AtomicDensity3DRenderOptions(
        mass_fractions=(0.50, 0.80, 0.95),
    ),
)
rendered.write_html("framework_atomic_density.html")
```

Each individual-atom field integrates to one; a species field integrates to the
number of selected atoms. Nested isosurfaces enclose requested fractions of that
measure rather than arbitrary fractions of the peak voxel value.

Normative document:

```text
docs/specs/plotting/atomic_density_spec.md
docs/specs/plotting/atomic_density_spec.pdf
```

## 0.19.65a0 automatic density defaults

Atomic and framework density preparation now uses the canonical periodized Gaussian
and transactional dense-versus-local-sparse selection by default. Users do not need
to choose a storage backend or smoothing implementation. The physical grid and
Gaussian width are resolved first; dense and sparse costs are then compared at that
identical resolution under the runtime budget.

```python
options = AtomicDensityOptions()
assert options.kernel_options.smoothing_operator == "discrete_periodized_v1"
assert options.storage_options.grid_backend == "auto"
```

Localized fields normally select local-sparse storage, while broad fields may select
dense storage. If neither backend can realize the requested resolution, preparation
fails with both reasons rather than silently increasing the Gaussian bandwidth.
Explicit backend and legacy-spectral dense overrides remain available for controlled
reproduction.

Normative document:

```text
docs/specs/plotting/density_default_auto_policy_ld11_spec.md
docs/specs/plotting/density_default_auto_policy_ld11_spec.pdf
```

## 0.19.64a0 runtime-derived density resource policy

Density preparation and mesh extraction no longer use scene-fitted compute caps. A
single runtime budget is resolved from the current process allocation, then inherited
by every planner, kernel, cache, and isolated mesh worker. Defaults use 80% of
detected available memory, 90% of available CPUs, and a 20-minute complete-scene
wall-time objective.

```python
from mdstats import FrameworkDynamicsResources

resources = FrameworkDynamicsResources(
    # Omit these values to use the runtime-derived defaults.
    max_memory_bytes="12GiB",
    max_threads=16,
    max_wall_time_seconds=1800,
)
```

Equivalent process-level overrides are
`MDSTATS_MAX_MEMORY_BYTES`, `MDSTATS_MAX_THREADS`, and
`MDSTATS_MAX_WALL_TIME_SECONDS`. Explicit memory and thread requests are clamped to
the detected process/job ceiling. Legacy per-kernel count limits are tightening-only;
they cannot expand the authoritative scene budget.

Browser faces, vertices, traces, and HTML bytes remain separate client-output
profiles. They are not inferred from host RAM and do not authorize additional compute.
The all-species example exposes both domains explicitly:

```text
--max-memory --max-threads --max-wall-time --max-browser-faces
```

Normative document:

```text
docs/specs/plotting/density_runtime_resource_policy_ld10_spec.md
docs/specs/plotting/density_runtime_resource_policy_ld10_spec.pdf
```

## 0.19.63a0 trajectory endpoint legend update

Trajectory start and end markers are enabled by default and now appear as separately
labeled legend entries whenever trajectory legends are enabled. The two endpoint
classes use independent legend groups. The complete 300 K Na-LTA example now accepts
command-line paths, uses every frame by default, and overlays all-species trajectories
with the mean framework, mean atomic net, and three HDR density shells for Na, Si, Al,
and O.

## Density optimization evidence, exact support planning, and browser budgets

Version `0.19.62a0` retains the completed LD8-S4 scientific backend and the
LD9-V1/V2/V3 hard-budget browser pipeline, then adds LD9-V4 bounded shell execution
and browser acceptance records. Normal local-sparse density preparation uses the exact
finite-support atlas and hybrid direct/overlap-add FFT executor. Browser scenes provide:

- deterministic post-replication allocation across every requested density shell;
- periodic-quotient reconstruction and fidelity-constrained simplification;
- bounded parallel fresh-process shell preparation with one native numerical thread per worker;
- compact `float32` coordinates and `int32` face indices;
- one trajectory line trace per species without dropping frames;
- hard limits of 300,000 density faces, 200,000 density vertices, 64 Plotly traces, and 40 MiB self-contained HTML;
- structured failure before writing an oversized artifact; and
- separate functional-browser and physical-WebGL production-authorization reports.

The complete V3 reference scene contains 286,008 faces, 147,477 vertices, 28 traces,
and a 26.2 MB self-contained HTML payload. Under managed headless Chromium, the V4
functional gate passes at 13.392 s to first frame, 27.698 FPS scripted orbit, 0.119 s
trace toggle, approximately 199 MiB JavaScript heap, and no context loss. The environment
did not expose renderer identity, so physical-WebGL production-default authorization
remains pending rather than being inferred.

A bounded real-mesh three-shell benchmark reduced wall time from 9.997 s serial to
3.701 s with three workers (2.701x speedup and 96.9% parallel efficiency), with
identical per-shell face and vertex counts.

```python
from mdstats import (
    BrowserAcceptancePolicy,
    BrowserMeshBudget,
    DensityMeshExecutionOptions,
    evaluate_browser_acceptance,
)

execution = DensityMeshExecutionOptions(
    max_parallel_shell_workers=3,
    worker_native_threads=1,
)

budget = BrowserMeshBudget(
    max_final_density_faces=300_000,
    max_final_density_vertices=200_000,
    max_plotly_traces=64,
    max_final_html_bytes=40 * 1024**2,
)

acceptance = evaluate_browser_acceptance(
    validation_payload,
    policy=BrowserAcceptancePolicy(
        require_physical_webgl_for_production=True,
    ),
)
```

Normative documents:

```text
docs/specs/plotting/density_evidence_benchmark_ld8_p0_spec.md
docs/specs/plotting/density_block_routing_ld8_s0_spec.md
docs/specs/plotting/density_support_atlas_ld8_s1_spec.md
docs/specs/plotting/density_packed_field_ld8_s0_spec.md
docs/specs/plotting/density_block_direct_ld8_s2_spec.md
docs/specs/plotting/density_tiled_fft_ld8_s3_spec.md
docs/specs/plotting/density_downstream_reuse_ld8_s4_spec.md
docs/specs/plotting/density_render_budget_spec.md
docs/specs/plotting/density_mesh_validation_ld9_v0_spec.md
docs/specs/plotting/density_tiled_contour_ld9_v1_spec.md
docs/specs/plotting/density_mesh_simplify_spec.md
docs/specs/plotting/density_scene_fit_spec.md
docs/specs/plotting/density_browser_acceptance_spec.md
```

## Framework vertex and edge-density clouds

Version `0.19.32a0` adds two dimensionally distinct framework-density channels:
projected-vertex occupancy and retained-edge arc length.

```python
from mdstats import (
    FrameworkDensity3DRenderOptions,
    FrameworkDensityOptions,
    prepare_framework_dynamics_scene,
    plot_framework_dynamics_3d,
)

scene = prepare_framework_dynamics_scene(
    collection,
    framework_topology,
    framework_density_options=FrameworkDensityOptions(
        grid_shape=(64, 64, 64),
        gaussian_bandwidth=0.30,
        edge_source="atomic_paths",
        edge_sample_spacing=0.20,
    ),
)

rendered = plot_framework_dynamics_3d(
    scene,
    framework_density_options=FrameworkDensity3DRenderOptions(
        mass_fractions=(0.50, 0.80, 0.95),
    ),
)
rendered.write_html("framework_density.html")
```

The vertex field integrates to the number of projected framework vertices. The
edge field integrates to the time- or ensemble-averaged total retained arc
length. They remain separate because their units are `angstrom^-3` and
`angstrom^-2`.

Normative document:

```text
docs/specs/plotting/framework_density_spec.md
docs/specs/plotting/framework_density_spec.pdf
```

## Natural-tile geometry on compatible frames

Version `0.19.29a0` implements Stage 11B. It maps a fixed, certified natural
tiling onto selected trajectory or ensemble frames after rebuilding and matching
the exact projected framework graph.

```python
from mdstats.analysis import map_tiling_geometry_to_frames

frame_geometry = map_tiling_geometry_to_frames(
    reference_geometry,
    periodic_cell_complex,
    periodic_net_embedding,
    primitive_ring_index,
    collection,
    atomic_connectivity,
    topology_catalog,
)

print(frame_geometry.mapped_frame_indices)
print(frame_geometry.tile_metric(0, "volume"))
```

The mapper replays the same periodic integer gauges used by atomic connectivity
and framework projection. Scientific faces, windows, tile identities, and
translation-labelled adjacency remain fixed. Thermally nonplanar faces are
retained as deterministic boundary-center fan surfaces with explicit planarity
diagnostics. Topology changes or unreplayable geometry remain explicit per-frame
outcomes; they are not silently forced into the reference tiling.

Normative documents:

```text
docs/specs/analysis/tiling_geometry_frames_spec.md
docs/specs/analysis/tiling_geometry_frames_spec.pdf
docs/arch_manuals/framework_ring_architecture.md
audits/analysis/tiling_geometry_frames_audit.md
```

## Structured progress reporting

Long-running APIs accept a shared structured progress port and remain silent by
default:

```python
import sys
from mdstats import TextProgressPort, prepare_framework_dynamics_scene

progress = TextProgressPort(label="mdstats", stream=sys.stdout)
scene = prepare_framework_dynamics_scene(
    collection,
    topology,
    progress=progress,
)
```

Applications may instead use `LoggingProgressPort`, `CallbackProgressPort`, or a
custom object implementing `emit(ProgressEvent)`. The former string
`progress_callback=` argument remains temporarily available but is deprecated. See
`docs/specs/progress_spec.md` for the event schema and module adoption standard.


### Closed-loop interactive density fitting and topology categories

Interactive framework-density scenes use the `balanced` browser profile by
default and automatically refit periodic shell geometry before export. Choose a
profile explicitly with `mesh_profile="compact"`, `"balanced"`, or `"quality"`,
or pass `BrowserMeshProfile.custom(...)`.

`prepare_framework_dynamics_scene` accepts a complete `TopologyCatalog`. For a
partitioned high-temperature trajectory, mdstats prepares one category-local
averaged framework and atomic mean-connectivity graph per exact topology class.
The dominant category is visible initially; one grouped legend click toggles all
framework and atomic-connectivity traces for another category. Atomic density
fields and trajectories remain global rather than being recomputed per class.

## LTA topology hysteresis

The LTA density/framework example classifies framework topology with a
framework-only two-cutoff Si/Al--O definition.  Bonds form below the calibrated
formation cutoff and remain present until they exceed the larger breaking
cutoff.  Calibration uses the four-nearest-oxygen tetrahedral shell, and the
resolved cutoffs are printed and stored in the topology-resolution audit.
Optional `--framework-formation-cutoff` and `--framework-breaking-cutoff`
overrides are available for controlled studies.

## MLFF training-data branch

The canonical MLFF architecture and implementation history are documented in
`docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`. The production
branch now covers source/label identity, leakage-safe partitioning, checkpoint-
bound DATA6 features, exact target/replay selection, restartable MACE training,
target-first evaluation, deployment/PES/relaxation/dynamics verification, final
selection, locked-test activation, generalized multi-head MACE foundations, and
reference-backend certification through MH1-CERT1. MACE-MH-1 / `omat_pbe` /
e3nn remains the current generated/reference authority; accelerated CuEq work
remains explicit and phase separated after failed six-head parity qualification.

`mdstats 0.20.178a0` freezes bounded **PERF-BASE0** as the exact
post-MH1 numerical/performance oracle. `mdstats 0.20.179a0` completes bounded
**PERF-P0** for TARGET-DATA2B: numerical families are canonical little-endian
read-only arrays; campaign persistence uses authenticated content-addressed NPY
shards with shared weight profiles and threshold-controlled mmap restore; and
historical inline v1 records migrate only after exact elementwise comparison.
The coverage mathematics, FP64 authority, source membership, and scientific
digests are unchanged.

On the complete supplied 37,633-frame / 6,322,344-atom LTA target corpus, five
matched isolated runs reduced median exact-family construction wall time from
7.541 s to 6.236 s (17.30%). Native v2 persistence measured 0.184 s write,
0.180 s authenticated read, and 17,912,666 bytes, versus 10.366 s, 14.382 s,
and 42,749,676 bytes for nested JSON v1. All 48 numerical-array fingerprints
match PERF-BASE0 exactly.

`mdstats 0.20.180a0` completes bounded **PERF-P1**. TARGET-DATA2C and DATA7
share one exact reusable FPS workspace, fused selector construction is
preallocated, nested coverage carries one exact family state, and DATA7
nearest-selected coverage uses O(K) persistent state rather than KxK. Full
reference selection/coverage digests remain unchanged.

`mdstats 0.20.181a0` completed historical **PERF-P2**, whose lazy v2 ladder
truncated materialization after the former four-smallest coverage shortlist was
provably fixed. `mdstats 0.20.182a0` supersedes that generated-campaign science
with **SIZE-HALVE1**: coverage is hard admission only, every coverage-qualified
size is retained, and target size is reduced by exact 3/10/30 successive-fidelity
training. Epoch 3 is a common target-only coarse screen (default 256 target
configurations) to at most four candidates; epoch 10 retains two; epoch 30 applies
final target/replay/physical qualification. Both continuation boundaries
authenticate checkpoint, optimizer/scheduler, and RNG ancestry. Early practical
equivalence preserves the largest ladder boundary within its equivalence band so
a tie cannot hide bounded-ladder nonconvergence.

Historical PERF-P2 timing remains archival evidence for the algorithm that was
measured, not a current campaign speed claim. `mdstats 0.20.183a0` implements the
**SIZE-FIDELITY1** calibration authority and execution plan. The calibration itself disables
halving: every hard-coverage-qualified size is trained to 30 epochs for at least three frozen
optimizer seeds, and candidate 3/4/5-epoch screens are replayed retrospectively. A candidate
coarse rule is certifiable only when both eventual 30-epoch target finalists survive the coarse
and epoch-10 screens for every seed and the coarse monitor produces the same promotion set as
the full development role. Monitor-size calibration reuses one authenticated full-role prediction
pass per checkpoint and derives all monitor views from those predictions.

The supplied MACE-MH-1 and MACE-MPA-0-medium foundation files are now available and match the
previously locked SHA-256 identities. `mdstats 0.20.184a0` introduces **FINAL-GPU1**: accelerator-dependent
qualification is deferred to one final release-matched CUDA/CuEquivariance run on the user's workstation.
SIZE-FIDELITY1 remains a hard final-release scientific blocker, but it no longer interrupts implementation
development. PERF-P2R CPU/control-plane execution is implemented against the complete parameter grid, with authenticated DATA8 fixed-file reuse and parameterized stage dispatch; PERF-P3 CPU structural/reduction hardening is implemented in 0.20.185a0; VRAM1 + PERF-P4 CPU/control-plane execution is implemented in 0.20.186a0, and PERF-P5 TRAIN2/EVAL2 persistence hardening is CPU-qualified in 0.20.187a0; CUEQ-DEP1 runtime-freeze implementation is complete in 0.20.188a0 and CUEQ-PHASE1 training-only qualification control-plane implementation is complete in 0.20.189a0; positive accelerator evidence remains deferred to FINAL-GPU1. No GPU-derived default or performance claim becomes authoritative before FINAL-GPU1 passes. The one-shot readiness entry point is
`tools/run_mlff_final_gpu_qualification.py`.

```python
from pathlib import Path

from mdstats import (
    compare_target_coverage_references_exact,
    read_target_coverage_native_record,
    write_target_coverage_native_record,
)

root = Path("campaign-state")
pointer = write_target_coverage_native_record(reference, root / "records")
restored = read_target_coverage_native_record(
    pointer,
    root,
    mmap_threshold_bytes=8 * 1024 * 1024,
)
assert compare_target_coverage_references_exact(reference, restored).exact_match
```

The normative contract is
`docs/specs/training_data/mlff_perf_p0_native_target_coverage_spec.{md,pdf}`;
matched CPU evidence is
`audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.{json,md,pdf}`.

## Selecting MACE fine-tuning precision

The foundation checkpoint may remain in its original float64 representation.
Choose the precision of every generated fine-tuning job in the optimizer policy:

```python
from mdstats import MaceOptimizerPolicy

# Faster/lower-memory training on consumer GPUs such as an RTX 3090.
fp32 = MaceOptimizerPolicy(default_dtype="float32", device="cuda")

# Numerically conservative control protocol.
fp64 = MaceOptimizerPolicy(default_dtype="float64", device="cuda")
```

Pass the selected policy to `build_data8_preparation_bundle(...)`. The choice is
part of the immutable training-protocol digest. `realize_mace_job_config(...)`
verifies the generated MACE parser value, and `run_mace_job_execution_smoke(...)`
loads the saved final and target-head models and rejects mixed or unexpected
floating-point state. The foundation file is never modified.


### Universal 3-D graphics architecture (GFX3D-1)

As of `0.20.146a0`, `mdstats.graphics3d` provides the renderer-independent contract foundation for composable 3-D scientific scenes: named layer requests, universal selections, scientific dependency keys, separate scientific/render/execution identities, canonical scene manifests, an internal layer registry, renderer-neutral primitives, and compatibility adapters for the existing `FrameworkDynamicsScene` path. The current framework/connectivity/trajectory/density science remains unchanged; independent built-in layer adapters are the GFX3D-2 gate, and the universal `mdstats-3d` CLI remains deferred to GFX3D-3.
