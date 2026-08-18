# Part I - Foundations and ownership

## Reader orientation

### What an MLFF learns

An energy-conserving machine-learned force field represents a potential-energy
function

$$
E_\theta = E_\theta(\mathbf Z, \mathbf R, \mathbf H),
$$

where $\mathbf Z$ contains atomic numbers, $\mathbf R$ contains positions,
$\mathbf H$ is the periodic cell, and $\theta$ denotes model parameters.
Forces and stress follow from derivatives of the same energy:

$$
\mathbf F_i = -\frac{\partial E_\theta}{\partial \mathbf R_i},
\qquad
\boldsymbol\sigma = -\frac{1}{V}
\frac{\partial E_\theta}{\partial \boldsymbol\epsilon},
$$

up to the exact stress sign and strain convention declared by the label source.
MACE builds symmetry-aware local atomic features and sums atomic energy
contributions [1]. A useful dataset therefore has to constrain both the energy
surface and its derivatives throughout the intended simulation domain.

A low average force error is not sufficient. A model can fit common framework
vibrations while failing on rare mobile-ion environments, strained cells, or
migration geometries. Validation must include both numerical errors and
physically relevant observables [6].

### Why adjacent MD frames are not independent

A molecular-dynamics trajectory contains temporally correlated configurations.
At a 1 fs output interval, neighboring frames are often nearly duplicates.
Using them in different statistical roles creates leakage and overstates model
accuracy.

For an observable $x_t$, the normalized autocorrelation at lag $k$ is

$$
\rho_x(k) =
\frac{
\langle (x_t-\bar x)(x_{t+k}-\bar x)\rangle
}{
\langle (x_t-\bar x)^2\rangle
}.
$$

A truncated integrated autocorrelation time is

$$
\tau_{\mathrm{int},x}
=
\Delta t
\left[
\frac{1}{2}+
\sum_{k=1}^{k^\star}\rho_x(k)
\right].
$$

The effective number of independent observations is approximately

$$
N_{\mathrm{eff},x}
\approx
\frac{T}{2\tau_{\mathrm{int},x}}.
$$

Block averaging and hv-block cross-validation provide established foundations
for handling correlated data [3-5]. The branch uses these ideas but records the
mdstats-specific estimator, truncation rule, minimum block size, and purge rule
as explicit policies.

### The three ordinary dataset roles

| Role | Function | May affect parameters? | May affect model choice? |
|---|---|---:|---:|
| Training | Supplies gradient updates | Yes | Yes |
| Validation | Early stopping and hyperparameter choice | No | Yes |
| Test | Final locked evaluation | No | No |

MACE documents the same distinction: validation controls early stopping, while
the test set is independent and evaluated at the end [8].

The architecture adds two more evidence roles:

| Role | Function |
|---|---|
| Calibration | Calibrates committee disagreement or acquisition thresholds |
| Challenge test | Evaluates a named extrapolation or physical mechanism |

Calibration is not test data. Challenge tests are not ordinary validation data.

## Scope

### Included

The branch will provide:

- VASP trajectory discovery and source certification;
- composition, temperature, ensemble, and strain reconstruction;
- electronic-structure compatibility and label-domain classification;
- energy, force, and stress label auditing;
- atomic-reference-energy identifiability diagnostics;
- frame-level eligibility and quality decisions;
- generic physical feature providers plus optional material-profile extensions;

LTA is an optional profile extension; it is not the generic feature or selection default.

- optional MPA-0 descriptors and zero-shot residuals;
- event detection before ordinary thinning;
- autocorrelation-aware complete-frame blocks;
- fixed outer validation, calibration, and locked test domains;
- independent cross-validation job families;
- fold-local transformations and training selection;
- deterministic nested training-size ladders;
- MACE target/replay artifact generation;
- replay-retention monitoring;
- training-only epoch resampling and exposure accounting;
- active-learning candidate screening, acquisition, and immutable lineage.

### Excluded from the first runtime release

The first runtime sequence will not:

- patch the internal MACE optimizer or data loader;
- claim that coverage metrics prove final MLFF accuracy;
- infer an unstrained reference cell when more than one reference is defensible;
- merge incompatible DFT levels into one target head;
- use locked test labels for uncertainty calibration;
- treat replay-head disagreement as an uncertainty committee;
- silently download replay data from the mdstats core;
- promise efficient random access to XML before a streaming/indexed reader exists.

## Reference application: bulk Li/Na/K-LTA

The first scientific target contains 27 AIMD runs:

- seven cation compositions: Li, Na, K, LiNa, NaK, LiK, and LiNaK;
- three temperatures: 300, 700, and 800 K;
- six additional LiNaK strain runs: hydrostatic $\pm5\%$ volume,
  constant-volume orthorhombic $\pm2\%$ linear strain, and engineering shear
  $\pm2\%$;
- 1.4 ps per run at 1 fs time step;
- a Langevin NVT protocol, with approximately 0.2 ps initial relaxation.

This dataset motivates several domain-specific requirements:

1. Framework atoms greatly outnumber mobile cations. Global descriptor averages
   must not hide Li, Na, or K environments.
2. Strain combinations do not form a full Cartesian product with composition
   and temperature. Stratification must be hierarchical.
3. One trajectory per condition provides temporal interpolation evidence, not a
   fully independent replica test.
4. Fixed framework stoichiometry makes individual atomic reference-energy
   corrections non-identifiable without additional anchors.
5. Short trajectories may contain few cation hops. Absence of a transition is a
   documented coverage gap, not evidence that the transition is unimportant.

## Relationship to existing mdstats capabilities

The training-data branch is an orchestrator over existing mdstats scientific
capabilities.

| Existing capability | Reused evidence |
|---|---|
| `mdstats.io.vasp.read_vasp_frames` | cells, coordinates, energies, forces, stress, temperature, provenance |
| `mdstats.io.vasp_controls.read_vasp_run_controls` | source controls, named energy channels, SCF iterations |
| VASP ensemble-control certification | NVE/NVT/NpT/NpH and driven-control classification |
| trajectory-quality assessment | source and trajectory integrity verdicts |
| production-regime assessment | transient and stationary regime evidence |
| Stage 11 structural modules | LTA rings, sites, coordination, topology, transitions |
| `mdstats.io.sampling_crossfit` | design precedent for source-bound blocks and purge semantics |

The new branch owns dataset-level comparison, partition, selection, export, and
active-learning lineage. It does not redefine the underlying physical analyses.

## Controlling data flow

The controlling flow is:

```text
source bytes
  -> source occurrence identity
  -> VASP controls + trajectory collection
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
  -> fixed outer partition + PartitionIndependenceReport
       development pool
       outer monitor validation
       dedicated final-committee calibration cohort
       locked interpolation test
       named locked challenge tests
  -> independent cross-validation job family
       fold-training domain
       nested fold checkpoint monitor
       held-out evaluation fold
       fold-local feature metric + transform
       fold-local atomic-reference fit
       fold-local selection
       fresh model and frozen checkpoint per fold
       out-of-fold predictions
  -> final target-training transform + E0 fit + deterministic master order
  -> nested training-size ladder
  -> development MACE target/replay bundle
       no locked-test path
       replay-retention checkpoint constraint
  -> selected final checkpoints + independent-seed committee
  -> final-committee predictions on dedicated calibration cohort
  -> committee-bound uncertainty calibration
  -> post-freeze locked evaluation bundle
  -> active-learning candidate trajectories
  -> candidate admissibility + novelty + calibrated or rank-only uncertainty
  -> DFT query manifest
  -> labeled-round eligibility
  -> append-only child dataset generation with inherited roles
```

No arrow runs from a locked test into a fitted transform, E0 fit,
hyperparameter or checkpoint choice, uncertainty calibration, or acquisition
rule.

## Package and ownership structure

```text
mdstats/
  sampling/
    autocorrelation.py
    blocks.py
    assignment.py

  training_data/
    __init__.py
    policies.py
    records.py
    sources.py
    label_domains.py
    reference_energies.py
    conditions.py
    strain.py
    identity.py
    eligibility.py
    frame_catalog.py
    events.py
    independence.py
    partition_feasibility.py
    feature_metric.py
    blinding.py
    features/
      base.py
      thermodynamic.py
      geometry.py
      coordination.py
      lta.py
      mace.py
    partition.py
    cross_validation.py
    training_protocol.py
    objectives.py
    checkpoint_selection.py
    selection.py
    exposure.py
    replay.py
    replay_retention.py
    calibration.py
    active_learning.py
    role_inheritance.py
    export/
      extxyz.py
      mace.py
      manifest.py
    workflow.py
```

The proposed `mdstats.sampling` package contains source-independent primitives.
Existing Stage 11 public records remain unchanged and may be reimplemented
internally over these primitives only after exact replay tests pass.
