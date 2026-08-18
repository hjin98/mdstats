# Part I - Foundations and ownership

## Reader orientation

### What an MLFF learns

An energy-conserving machine-learned force field represents a potential-energy function

$$
E_\theta = E_\theta(\mathbf Z, \mathbf R, \mathbf H),
$$

where $\mathbf Z$ contains atomic numbers, $\mathbf R$ contains positions, $\mathbf H$ is the periodic cell, and $\theta$ denotes model parameters. Forces and stress follow from derivatives of the same energy,

$$
\mathbf F_i = -\frac{\partial E_\theta}{\partial \mathbf R_i},
\qquad
\boldsymbol\sigma = -\frac{1}{V}\frac{\partial E_\theta}{\partial \boldsymbol\epsilon},
$$

under the declared stress sign and strain convention of the label source. MACE constructs symmetry-aware local atomic features and sums atomic-energy contributions [1]. A useful training/evaluation corpus therefore constrains both the energy surface and its derivatives throughout the intended simulation domain.

A low average force error is not sufficient. Common framework vibrations can dominate aggregate statistics while rare mobile-ion environments, strain states, migration geometries, or other declared focus physics remain poorly represented. The architecture therefore separates broad numerical metrics, condition/group-resolved evidence, physical observable validation, and explicit extrapolation/challenge evidence.

### Why adjacent MD frames are not independent

A molecular-dynamics trajectory contains temporally correlated configurations. Neighboring frames can be near duplicates, so placing them in different statistical roles can create leakage and overstate model accuracy.

For an observable $x_t$, the normalized autocorrelation at lag $k$ is

$$
\rho_x(k) =
\frac{\langle (x_t-\bar x)(x_{t+k}-\bar x)\rangle}
{\langle (x_t-\bar x)^2\rangle}.
$$

A truncated integrated autocorrelation time is

$$
\tau_{\mathrm{int},x}
=
\Delta t\left[\frac{1}{2}+\sum_{k=1}^{k^\star}\rho_x(k)\right],
$$

with an effective sample count approximately

$$
N_{\mathrm{eff},x}\approx\frac{T}{2\tau_{\mathrm{int},x}}.
$$

mdstats uses autocorrelation-aware complete-frame blocks, purge semantics, and explicit independence grades rather than treating every frame as an independent observation [3-5]. The precise estimator, truncation, block-size, purge, and role-assignment behavior belongs to the current sampling/partition specifications.

### Statistical evidence roles

The architecture distinguishes gradient-training evidence from model-control and final-evaluation evidence.

| Role | Function | May affect parameters? | May affect model/checkpoint choice? |
|---|---|---:|---:|
| Training/development | Supplies gradient updates and fitted training-domain products | Yes | Yes |
| Checkpoint monitor / validation | Controls declared stopping/checkpoint policy | No | Yes |
| Outer validation | Estimates protocol performance without fitting that protocol | No | No for the already-frozen job |
| Calibration | Calibrates final-committee uncertainty/acquisition behavior | No | No training/checkpoint change |
| Locked test / challenge | Final sealed evaluation of interpolation or named mechanisms | No | No |

Calibration is not test data, and locked/challenge evidence is not ordinary validation data.

## Scope and ownership

The MLFF training-data subsystem owns dataset-level certification, comparison, partition, selection, training-artifact construction, campaign orchestration, checkpoint/evaluation lineage, deployment verification coordination, and active-learning lineage.

Its current responsibilities include:

- VASP source discovery/certification and source/label identities;
- composition, thermodynamic condition, ensemble, reference-cell, and strain reconstruction;
- electronic-structure compatibility and label-domain grouping;
- energy/force/stress auditing and atomic-reference identifiability/fitting lineage;
- immutable frame facts, eligibility, and quality decisions;
- generic structural feature providers plus explicit optional material-profile extensions;
- event detection before ordinary thinning;
- autocorrelation-aware complete-frame blocks and role feasibility;
- fixed outer evidence roles and independent cross-validation job families;
- fold-local transforms, metrics, E0 fits, difficulty evidence, and selection;
- deterministic nested target-data construction and exact multi-view coverage/selection;
- MACE target/replay artifacts and explicit exposure realization;
- replay-retention monitoring and checkpoint admissibility;
- training/evaluation execution, protocol freeze, and committee export;
- final-committee-bound calibration and sealed evaluation activation;
- candidate admissibility/acquisition records and append-only active-learning lineage where supported by the current runtime/specification set.

LTA/zeolite ring, cage, site, crossing, and related semantics are optional profile extensions; they are not generic defaults.

The subsystem does not silently merge incompatible electronic-structure levels, infer ambiguous scientific references, use locked-test evidence for fitting/calibration/acquisition, treat replay-head disagreement as an uncertainty committee, redefine physical-analysis algorithms, or silently obtain external replay data.

## Reference application: bulk Li/Na/K-LTA

The principal reference corpus contains 27 AIMD runs spanning seven cation compositions, three temperatures, and six additional LiNaK strain conditions. This application motivates, but does not hard-code into generic behavior, several design requirements:

1. framework atoms can outnumber mobile cations, so global descriptor averages must not hide declared mobile-species environments;
2. strain conditions need not form a full Cartesian product with composition and temperature, so condition schemas are hierarchical;
3. one trajectory per condition supplies limited independence and must not be represented as an independent-replica test;
4. fixed framework stoichiometry can make individual atomic reference-energy corrections non-identifiable without anchors;
5. short trajectories may contain few rare transitions, so absent events are explicit coverage gaps rather than evidence of irrelevance.

## Relationship to existing mdstats capabilities

The training-data subsystem orchestrates existing mdstats scientific capabilities rather than duplicating them.

| Existing capability | Reused evidence |
|---|---|
| `mdstats.io.vasp.read_vasp_frames` | cells, coordinates, energies, forces, stress, temperature, provenance |
| `mdstats.io.vasp_controls.read_vasp_run_controls` | source controls, named energy channels, SCF behavior |
| VASP ensemble-control certification | ensemble/control classification |
| trajectory-quality assessment | source and trajectory integrity verdicts |
| production-regime assessment | transient/stationary regime evidence |
| analysis structural/topology modules | optional profile-owned structural evidence |
| `mdstats.io.sampling_crossfit` and sampling primitives | source-bound block and purge semantics |

Physical observables remain owned by `mdstats.analysis`; the MLFF layer may invoke and compare their results only through the declared analysis-owned contracts.

## Controlling data flow

The current controlling flow is:

```text
source bytes
  -> source occurrence identity
  -> controls + trajectory collection
  -> ensemble, quality, and production-regime evidence
  -> source catalog + decomposed label-domain audit
  -> structural atomic-reference identifiability
  -> immutable frame facts
       occurrence UID
       geometry fingerprint
       label payload digest
       labeled-configuration fingerprint
  -> labeled-frame eligibility
  -> full-resolution generic + partition-critical profile features
  -> event detection before ordinary thinning
  -> complete-frame temporal blocks
  -> fixed outer partition + independence evidence
       development pool
       outer monitor/validation
       calibration cohort when supported
       sealed interpolation/challenge tests when supported
  -> independent cross-validation job family
       fold-training domain
       disjoint checkpoint monitor
       held-out evaluation fold
       fold-local fitted products and selection
       fresh model/checkpoint per fold
       out-of-fold predictions
  -> final target-training fitted products + deterministic target-data order/rungs
  -> development MACE target/replay bundle
       no locked-test path
       replay-retention constraints
  -> candidate checkpoint evaluation and admissibility
  -> selected final checkpoints + independent-seed committee
  -> protocol freeze
  -> final-committee calibration where configured
  -> explicit sealed-evaluation activation
  -> deployment verification
  -> active-learning candidate/DFT lineage where configured
```

No allowed dependency runs from locked-test evidence into fitted transforms, E0 fitting, training selection, protocol/checkpoint choice, uncertainty calibration, or acquisition policy.

## Package and responsibility structure

Current implementation is organized under source-independent sampling primitives, `mdstats.training_data` record/policy/workflow modules, optional feature/profile providers, MACE export/runtime adapters, campaign orchestration, and analysis-owned observable bridges. The architectural requirement is responsibility separation rather than a frozen file listing: source facts, workflow decisions, fitted products, runtime realizations, and external-analysis results remain distinct owners even when modules are reorganized internally.

Public/serialized compatibility promises are controlled by current specifications and schema readers. Internal refactoring may reuse common sampling or execution primitives only when the externally owned scientific behavior and persisted identities remain compatible.
