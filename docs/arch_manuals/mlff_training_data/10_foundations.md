# Part I - Foundations

## What an MLFF learns

An energy-conserving machine-learned force field represents a potential-energy function

$$
E_\theta=E_\theta(\mathbf Z,\mathbf R,\mathbf H),
$$

where \(\mathbf Z\) contains atomic numbers, \(\mathbf R\) positions, \(\mathbf H\) the periodic cell, and \(\theta\) model parameters. Forces and stress follow from derivatives of the same energy,

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial\mathbf R_i},
\qquad
\boldsymbol\sigma=-\frac{1}{V}\frac{\partial E_\theta}{\partial\boldsymbol\epsilon},
$$

under the declared stress sign and strain convention of the label source. MACE constructs symmetry-aware local atomic representations and sums atomic-energy contributions [1]. A useful training/evaluation corpus must therefore constrain both the energy surface and its derivatives throughout the intended simulation domain.

A low global force error is not sufficient. Common framework vibrations can dominate aggregate statistics while rare mobile-ion environments, strain states, migration geometries, interfaces, defects, or other declared focus physics remain poorly represented. The architecture separates broad numerical metrics, condition/group-resolved evidence, physical-observable validation, and explicit extrapolation/challenge evidence.

## Why trajectory frames need statistical roles

Molecular-dynamics frames are temporally correlated. Neighboring configurations can be near duplicates, so assigning them to nominally different roles can create leakage and overstate model quality.

For observable \(x_t\), normalized autocorrelation at lag \(k\) is

$$
\rho_x(k)=
\frac{\langle(x_t-\bar x)(x_{t+k}-\bar x)\rangle}
     {\langle(x_t-\bar x)^2\rangle}.
$$

A truncated integrated autocorrelation time is

$$
\tau_{\mathrm{int},x}=\Delta t\left[\frac12+\sum_{k=1}^{k^\star}\rho_x(k)\right],
$$

with approximate effective sample count

$$
N_{\mathrm{eff},x}\approx\frac{T}{2\tau_{\mathrm{int},x}}.
$$

mdstats therefore uses autocorrelation-aware complete-frame blocks, purge semantics, and explicit independence grades rather than treating every frame as independent [3-5]. Exact estimators, truncation, block size, purge, and role-assignment rules are specification-owned.

## Evidence-role model

The architecture distinguishes evidence by what it is allowed to control.

| Role | Supplies gradients? | May control fitted preparation/subset/size/checkpoint? | Purpose |
|---|---:|---:|---|
| development / training domain | Yes when selected | Yes, within the authorized training/model-selection contract | fitting and protocol development |
| checkpoint / common target monitor | No | Yes, only for explicitly authorized development/model-control decisions | stopping/checkpoint and target-size development evidence |
| held-out CV evaluation | No | No for the frozen protocol it evaluates | protocol validation |
| calibration | No | No training/subset/checkpoint changes | final-committee uncertainty calibration |
| locked interpolation/challenge test | No | No | sealed final evaluation |

Calibration is not test data; held-out CV is not a checkpoint monitor; and a monitor cardinality is not a target-training cardinality.

## Scope and ownership

The MLFF subsystem owns dataset certification, evidence-role construction, fitted preparation, multi-view target-subset construction, target-size study, training-artifact construction, campaign orchestration, checkpoint/evaluation lineage, deployment verification coordination, and active-learning lineage.

Its current responsibilities include:

- VASP source discovery/certification and source/label identities;
- composition, thermodynamic condition, ensemble, reference-cell, strain/stress reconstruction;
- electronic-structure compatibility and label-domain grouping;
- energy/force/stress audit and atomic-reference identifiability/fitting lineage;
- immutable frame facts, eligibility, and quality decisions;
- generic raw structural features/events plus explicit optional material/profile extensions;
- autocorrelation-aware complete-frame blocks and role feasibility;
- fixed outer roles and independent CV job families;
- fold/final-domain fitted descriptors, transforms, metrics, E0, objective/weight, and difficulty evidence;
- the target-size development split, the canonical training/evaluation orders, the common preparation, and the paired optimizer-seed screen;
- one protocol-global target-size decision with domain-local membership;
- MACE target/replay artifacts and explicit exposure realization;
- replay-retention and checkpoint admissibility;
- protocol-matched CV, final training, committee export, calibration, sealed evaluation, and deployment verification;
- active-learning candidate/DFT lineage where supported by current specifications.

The subsystem does not silently merge incompatible electronic-structure levels, infer ambiguous scientific references, use held-out/locked evidence for forbidden model-control decisions, redefine analysis-owned physical-observable algorithms, create a second target selector, generate rescue target sizes, or migrate unsupported old campaign generations.

LTA/zeolite ring, cage, site, crossing, and related semantics are optional profile extensions rather than generic defaults.

## Reference application: Li/Na/K-LTA

The principal reference application contains AIMD evidence spanning multiple cation compositions, temperatures, and strain conditions. It motivates—but does not hard-code into generic architecture—several requirements:

1. framework atoms can outnumber mobile cations, so aggregate metrics must not hide declared mobile-species environments;
2. strain conditions need not form a full Cartesian product with composition/temperature, so condition applicability may be hierarchical;
3. one trajectory per condition supplies limited independence and must not be represented as an independent-replica test;
4. fixed framework stoichiometry can make individual atomic reference-energy corrections non-identifiable without anchors;
5. short trajectories may contain few rare transitions, so absent events are explicit coverage gaps rather than evidence of irrelevance.

## Reuse of analysis and sampling capabilities

The MLFF workflow orchestrates existing mdstats capabilities instead of duplicating them.

| Capability | MLFF use |
|---|---|
| `mdstats.io.vasp.read_vasp_frames` | cells, coordinates, energies, forces, stress, temperature, provenance |
| VASP control/ensemble readers | controls, energy-channel and ensemble evidence |
| trajectory-quality / production-regime assessment | source and stationary-regime evidence |
| analysis structural/topology modules | optional profile-owned raw evidence or post-training observables under analysis contracts |
| sampling/cross-fit primitives | source-bound blocks, purge, and independence semantics |

Physical observables remain owned by `mdstats.analysis`. The MLFF layer may orchestrate matched evaluation and retain analysis-owned result identities, but it does not redefine RDF, MSD, VACF, VDOS, diffusion, topology, conductivity, or related numerical algorithms.

## Current controlling data flow

```text
source bytes / controls / trajectory collections
  -> source and label-domain certification
  -> immutable frame facts and eligibility
  -> raw features/events before ordinary thinning
  -> correlation-aware blocks and evidence-role feasibility
  -> development / monitor / CV / calibration / locked roles
  -> required fold/final training domains
  -> domain-local DATA6/DATA7 fitted preparation
  -> P_train / M3 split -> pi_train / pi_eval
  -> common target-size preparation
  -> paired optimizer-seed screen -> target-size reducer
  -> common qualified target-size population
  -> target-size study using authorized development/model-selection evidence
  -> one frozen protocol-global N_selected
  -> domain-local selected prefixes
  -> protocol-matched CV with held-out folds inaccessible to size/checkpoint choice
  -> accepted frozen protocol
  -> independent final seeds and checkpoint admission
  -> final committee + deployment artifacts
  -> final-committee calibration where supported
  -> explicit locked-test / observable-validation activation
  -> active-learning lineage where configured
```

No allowed dependency runs from held-out CV or locked-test evidence backward into fitted transforms, E0 fitting, target membership, target-size selection, checkpoint choice, or calibration-policy design.

## Responsibility separation is more durable than module layout

The implementation may reorganize Python modules while preserving the architecture. The durable separation is among:

- physical/source facts;
- evidence-role and policy decisions;
- training-domain fitted products;
- target-membership and target-size decisions;
- runtime/execution realization;
- validation/calibration/locked evidence;
- external analysis-owned results.

Current specifications control public/serialized current-generation contracts. Internal refactoring may reuse common sampling/execution primitives when externally owned scientific behavior and persisted current-generation identities remain conforming. Backward compatibility with superseded campaign generations is not an architectural requirement, except for the narrow immediately preceding fixed-fidelity restart boundary: it may reuse authenticated unchanged preparation inputs, but it must create a fresh configurable target-size authority and fails closed when compatibility is ambiguous.
