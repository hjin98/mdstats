---
kind: D2-candidate-instance-law-binding
protocol_version: 6.4.0
status: RATIFIED_LAW_AND_ROLE_BINDING_TARGET_HOST_KEY_FREEZE_PENDING
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
candidate: db2ed47e8c999cb61507803610c72c0fa7ffaaf7
candidate_blob: 7843a41172d25c231d4c589aebc0214ddec42bd1
risk_binding: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md
accepted_parent_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
date: 2026-09-25
---

# Candidate-10 exact-instance law and role binding

## 1. Scope

This record binds the remaining prospective Candidate-10 method choices that can be resolved without observing Candidate-10 outcomes.

The already-ratified risk coordinates remain:

\[
\eta_{\rm NI}=0.09,\qquad q_{\rm cat}=0.09,\qquad n=300,
\]

with the projection evaluator using the same two ceilings and \(n_{\rm eval}=300\).

This record does not claim target-host evidence. Exact live corpus, run-plan, device/runtime and mutable-state digests are materialized in the Stage-C preflight before any governed Candidate-10 child executes.

## 2. Model-family applicability

Stage C binds two FP32 model-family realizations.

### MH-1

- family: \`mace_mh_1\`;
- selected scientific head: \`omat_pbe\`;
- locked source checkpoint SHA-256: \`ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde\`;
- current target-host selected-head qualification digest from Stage-A evidence: \`66867d6b08fc8af279c2f5e449168afa148d2f43aaa6fd745ae4524025c62244\`;
- current target-host selected-head checkpoint SHA-256 from Stage-A evidence: \`61c83c377dae92bf37c5412a263687237fbc4b9790828868ec0887cc992be928\`.

### MPA-0

- family: \`mace_mpa_0\`;
- scientific head: \`default\`;
- locked checkpoint SHA-256: \`75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638\`.

The MPA-0 Stage-C cross-family key uses the same frozen target/replay scientific corpus as the MH-1 key unless the target-host preflight shows that this corpus is not admissible for that model family, in which case Stage C remains blocked rather than substituting another corpus after Candidate output.

## 3. Dtype and backend-kernel pair

Only learned-model binary32 is in scope.

\[
d=\mathrm{float32}.
\]

The ordered kernel pair is:

\[
K_R=\mathrm{e3nn},\qquad K_C=\mathrm{cueq\_pure}.
\]

Source/DATA6 CuEq and FP64 CuEq TRAIN2 remain unsupported.

The target runtime family is the Stage-A production host family:

- NVIDIA RTX 3090 class target;
- MACE 0.3.16;
- Torch 2.13.0+cu126;
- CUDA runtime 12.6;
- CuEq 0.10.0.

The exact driver identity, GPU UUID, Torch deterministic/debug flags, TF32/matmul flags, cuDNN flags, CUBLAS workspace configuration, device capability, package build identities and any other arithmetic-relevant runtime coordinates are captured and frozen in \(\rho\) by preflight before the first governed child. A mismatch from the precommitted runtime family is a different key and does not silently reuse this instance.

## 4. Exact downstream consumer populations \(E\)

Candidate 10 is role-specific. The exact Stage-C manifest materializes the frame memberships and reduction identities, but the allowed consumer taxonomy is fixed here.

### CV role

\(E_{\rm CV}\) contains only current accepted role-effective consumers:

1. target force-component RMSE \(r_{\rm mon}(c)\) on the exact common target monitor \(M_{\rm mon}\) for every checkpoint considered by checkpoint control;
2. every continuous quantity consumed by shared checkpoint constraint \(S(c)\), including authenticated true-reference replay-retention evidence when replay is enabled;
3. the accepted target-side checkpoint ranking/tie coordinates after admissibility;
4. held-out outer metric \(r_{\rm out}\) on the exact current fold outer membership after representative freeze;
5. completed-state portable-e3nn evaluation of those same role-effective consumers after the final optimizer/EMA mutation; and
6. the exact discrete consequences derived from them: checkpoint admissibility, selected representative, replay/retention classification and outer acceptance.

### Production role

\(E_{\rm prod}\) contains only:

1. \(r_{\rm mon}(c)\) on the exact common \(M_{\rm mon}\) for every checkpoint considered;
2. every continuous quantity consumed by \(S(c)\), including true-reference replay-retention evidence when enabled;
3. accepted target-side representative/final ordering coordinates;
4. completed-state portable-e3nn evaluation of the same role-effective consumers after the final optimizer/EMA mutation; and
5. exact checkpoint-quality, representative and publication-selection decisions.

No descriptor/FPS channel is an authorizing TRAIN2 consumer. No unconsumed diagnostic metric enters \(E\).

## 5. Source-owned materiality relations \(\{\mathcal R_e\}\)

All relations resolve only from Candidate 10 plus the accepted parent.

### Checkpoint target-force RMSE

For CV:

\[
r_{\rm mon}(c)\le\tau_{\rm CV},
\qquad
\tau_{\rm CV}=0.045\ {\rm eV/\AA}
\]

under accepted D2.DEF.058 / exact parent source Section 17.1.

For production:

\[
r_{\rm mon}(c)\le\tau_{\rm prod},
\qquad
\tau_{\rm prod}=0.030\ {\rm eV/\AA}.
\]

The accepted threshold is inclusive in binary64; the next representable double above the resolved ceiling fails.

### CV outer predicate

For the accepted default target-force RMSE outer metric:

\[
r_{\rm out}\le\theta_{\rm CV},
\qquad
\theta_{\rm CV}=0.045\ {\rm eV/\AA}
\]

under accepted D2.DEF.059 / exact parent source Section 17.1.

If the exact live campaign explicitly configures another already-accepted outer metric/threshold family, that exact source-owned relation is frozen in the preflight manifest; it may not be selected from Candidate outcomes.

### Shared checkpoint/replay constraints

Every quantity consumed by \(S(c)\) uses the exact accepted relation imported by D2.DEF.057 and the current authenticated replay lineage.

For replay-enabled foundation adaptation, this exact Candidate-10 instance binds the accepted-parent replay-retention hard budget

\[
\Delta_{\rm replay}\le 0.030\ {\rm eV/\AA}
\]

(`30 meV/Å`) against authenticated true-reference/DFT replay evidence. Equality passes; no Candidate observation, newer unratified warning/hard policy, or historical D4 threshold can widen this accepted-parent relation.

The accepted-parent shared checkpoint constraint requires finite required metrics and carries no additional physical-gate tuple in the current realization (`required_physical_gates = ()`). Missing, stale or incompatible true-reference replay evidence fails closed.

### Ordering and ties

Representative/checkpoint/final ordering uses the exact accepted target-side ranking/tie owner. Candidate-10 D2.CUEQ10.DEF.018 supplies only the conservative decision-geometry qualification guard on top of that accepted relation.

Exact-tie branches remain exact.

### Non-authorizing quantities

A reported continuous value with no accepted parent relation is observation-only and cannot create \(\mathcal R_e\).

## 6. Qualification design \(\mathcal Q\)

The Stage-C design is frozen as:

1. 300 independent triplets per exact TRAIN2 key;
2. one fresh \(R1\), \(R2\), and \(C\) OS process trajectory per triplet;
3. \(\mathcal W_{\rm pre}\) completes and freezes \(\Lambda_p\) before assignment;
4. assignment is one exactly uniform choice among the six permutations of \(R1,R2,C\), drawn after \(\Lambda_p\) freeze;
5. assignment entropy comes from the host OS cryptographic random source using unbiased rejection sampling over six outcomes; the entropy-source identity and every realized draw are recorded;
6. assignment affects launch labels only and never scientific seed, data order, initialization, optimizer state, risk coordinates or production-start parameters;
7. no child/triplet redraw, replacement, reassignment or same-key retry exists after a startup/runtime/nonfinite/timeout/OOM/post-output failure;
8. every accepted child completes the full accepted TRAIN2 horizon;
9. triplets execute sequentially; triplet children do not overlap governed arithmetic;
10. restart is not claimed by the base Stage-C key. Same-backend restart is a separate optional qualification key.

## 7. Renewal contracts

### \(\mathcal W_{\rm pre}\)

Immediately before assignment:

- authenticate the exact frozen Candidate-10 candidate/risk/law records;
- authenticate exact model/head, corpus, replay lineage, objective, optimizer, scheduler, EMA, loader, horizon and source-owned consumer relations;
- verify no governed Stage-C child process from another triplet is active on the bound GPU;
- freeze the exact host/runtime key \(\rho\);
- freeze exact initial numerical state identities \(\theta_0,q_0\);
- create a new triplet-local private scratch namespace;
- record \(\Lambda_p\) before drawing assignment.

No Candidate output is available at this boundary.

### \(\mathcal W_R\) and \(\mathcal W_C\)

Immediately before each child:

- create a fresh OS process;
- reconstruct the exact same upstream scientific/training state from immutable authenticated inputs;
- use backend \(K_R\) for reference or \(K_C\) for candidate;
- create fresh child-local temporary/cache namespaces so no mutable user-space Torch/MACE/CuEq/cache/allocator/RNG/worker state is inherited from a prior child;
- use the exact frozen scientific seed and accepted loader/shuffle/sampler semantics;
- execute with one active governed training child on the GPU;
- prohibit sibling overlap and adaptive warm-up;
- use no outcome-dependent prewarm, retry or cache reuse;
- authenticate the child start record before the first governed update.

The same \(\mathcal W_C\) is the production launch contract authorized by a passing record.

## 8. Production-equivalent laws

\(P_R^{\rm prod}\) is the stochastic execution law induced by the accepted e3nn TRAIN2 production path under the exact frozen key and \(\mathcal W_R\).

\(P_C^{\rm prod}\) is the stochastic execution law induced by pure-CuEq TRAIN2 under the exact frozen key and \(\mathcal W_C\).

For this first Candidate-10 instance, the qualified law has **one active governed training process per GPU**. Existing adaptive multi-job production scheduling is not authorized by this record. D3/D4 may either preserve single-job CuEq production or separately qualify a concurrent production law before allowing a Candidate-10 record to authorize overlapping CuEq TRAIN2 jobs.

This narrowing is deliberate: concurrency cannot be assumed execution-only until it is independently shown not to alter the governed numerical law.

## 9. Corpus, objective and horizon binding

Candidate 10 forbids transport across a different corpus or run-plan key.

Therefore the target-host preflight must freeze, before Candidate execution:

- exact selected target membership and digest;
- exact replay membership/split/label-mode/true-monitor lineage and digest when enabled;
- exact replay-first / target-second pre-shuffle layout for multihead replay;
- exact loader seed, sampler, shuffle, batch size and drop-last;
- exact role/fold/optimizer seed;
- exact objective/head/property masks;
- exact optimizer, learning-rate schedule, scheduler and EMA configuration;
- exact epoch/update horizon and checkpoint/monitor schedule.

The current generated P5 method remains single-process foundation adaptation with binary32 learned arithmetic, native replay-first/target-second combined loader where replay is enabled, \`drop_last=true\`, no balancing sampler and no intentional target duplication.

The exact live campaign values are resolved from the authenticated CampaignStore/current run-plan owners and committed in the preflight manifest. A changed corpus/run plan is another Candidate-10 key.

## 10. Projection/evaluator binding

Completed CuEq state projects only through the dependency-native production converter after the independent Candidate-10 structural/coefficient oracle passes.

The evaluator uses:

\[
\eta_{\rm NI,eval}=0.09,\quad q_{\rm cat,eval}=0.09,\quad n_{\rm eval}=300
\]

with its own exact production/evaluation-equivalent child laws, fresh-process renewal and pre-assignment assignment design.

EVAL2 numerical provider identity after valid projection is e3nn.

## 11. Preflight completion criterion

The exact instance is executable only after one target-host preflight manifest records all late-bound exact key values listed in Sections 3 and 9 without any Candidate-10 output.

That manifest is pre-Stage-C identity evidence, not qualification evidence.

Any missing/ambiguous key coordinate leaves Stage C blocked.
