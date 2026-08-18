---
title: "MLFF-DATA9A7e Cross-System Qualification"
author: "mdstats project"
date: "2026-07-30"
version: "0.20.51a0"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# 1. Purpose

MLFF-DATA9A7e qualifies the generalization completed in DATA9A7a--DATA9A7d.
The stage does not add a new physical descriptor or declare that a fitted model
is scientifically valid. It proves that the same DATA4--DATA7 preparation path
can be exercised for materially different profile classes while preserving
profile lineage, generic feature ownership, optional-extension isolation, and
selection evidence.

The required bounded cases are:

1. a generic crystalline solid;
2. an amorphous solid;
3. a homogeneous liquid;
4. a multiphase interface;
5. a crystalline material with the optional LTA extension.

The first four cases must neither import the MLFF LTA implementation modules nor
serialize legacy LTA top-level fields. The fifth case must activate the explicit
`porous_network -> zeolite -> lta` chain and carry LTA results only through the
generic optional-extension envelopes.

# 2. Scope and non-goals

DATA9A7e owns software-path qualification. It verifies:

- explicit material-profile contracts;
- DATA4--DATA7 digest lineage;
- phase/geometry plan realization;
- universal structural-feature and event activation;
- optional-extension activation or absence;
- nonempty deterministic DATA7 selection evidence;
- generic import isolation;
- canonical serialization without legacy LTA fields;
- immutable qualification records and suite evidence.

DATA9A7e does **not** establish:

- physical realism of the synthetic bounded fixtures;
- transferability of a trained potential;
- convergence of RDF, coordination, VDOS, diffusion, or other observables;
- production corpus sufficiency;
- final feature weights, acceptance thresholds, or checkpoint choice;
- performance or scaling for large systems.

Those responsibilities remain with the owning analysis manuals, DATA9A8
observable-comparison policy, and later DATA9B execution.

# 3. Qualification records

## 3.1 Clean-import evidence

`ImportIsolationEvidence` binds a clean-interpreter probe:

- probe identity;
- whether the interpreter started clean;
- material-specific modules present before generic import;
- material-specific modules present after generic MLFF import;
- forbidden module prefixes;
- digest of the probe script;
- a derived pass/fail result.

For DATA9A7e the forbidden generic prefixes are:

```text
mdstats.training_data.lta_profile
mdstats.training_data.lta_selection
```

Importing `mdstats`, constructing generic profiles, and using generic
DATA4--DATA7 APIs must not load either module. Accessing a public LTA symbol may
load the requested module lazily.

## 3.2 Per-case qualification evidence

`CrossSystemQualificationCaseRecord` binds:

- case ID and case kind;
- qualification-policy digest;
- material-profile and contract digests;
- declared phase kinds and geometry;
- exact DATA4, DATA5, DATA6, and DATA7 bundle digests;
- phase/geometry plan digest;
- enabled universal feature and event families;
- active optional-extension IDs;
- selected-frame count;
- clean-import evidence digest;
- forbidden imported modules;
- forbidden serialized field paths;
- profile, lineage, and selection gates;
- final derived pass/fail state.

The record cannot be marked passed unless every required component passes.

## 3.3 Suite evidence

`CrossSystemQualificationSuiteRecord` requires one record for every policy-
required case kind. All cases must share the same policy digest. The suite pass
state is the conjunction of its case pass states. JSON write/read operations
are canonical and digest-verified.

# 4. Case-specific requirements

## 4.1 Generic crystalline solid

Required:

- exactly one `crystalline_solid` phase;
- a realized phase/geometry plan;
- universal structural features in DATA6;
- nonempty DATA7 selection;
- no `lta` extension;
- no forbidden MLFF LTA imports;
- no legacy LTA serialization fields.

## 4.2 Amorphous solid

Required:

- exactly one `amorphous_solid` phase;
- disordered-phase radial and local-density defaults;
- universal structural features and generic events;
- the same generic isolation requirements as the crystal case.

## 4.3 Liquid

Required:

- exactly one `liquid` phase;
- liquid phase defaults and generic structural selection;
- no assumption of rings, sites, or cations;
- the same generic isolation requirements.

## 4.4 Multiphase interface

Required:

- `interface` geometry;
- at least two declared phases;
- explicit phase and interface atom groups;
- phase-composed feature and event defaults;
- geometry-aware group priorities;
- no implicit surface or interface inference;
- the same generic isolation requirements.

## 4.5 LTA extension

Required:

- a crystalline phase;
- explicit `porous_network`, `zeolite`, and `lta` extensions;
- canonical `lta` partition and selection catalogs inside generic
  `ProfileFeatureCatalog` envelopes;
- no legacy LTA top-level fields in new serialization;
- nonempty DATA7 selection combining universal and extension feature blocks.

# 5. Import architecture

The generic package import path must not import MLFF LTA implementations merely
because the public API exposes optional LTA symbols. DATA9A7e therefore changes
LTA exports to lazy resolution:

```text
import mdstats
    -> generic training-data modules loaded
    -> lta_profile and lta_selection absent

mdstats.LtaSelectionPolicy
    -> lta_selection loaded on demand
```

`data4_bundle.py` and `data6_bundle.py` use type-checking imports plus local
runtime imports only when legacy LTA payloads are decoded or an active LTA
policy is requested.

# 6. Bounded end-to-end workflow

Each qualification case executes:

```text
explicit profile contracts
        -> DATA4 raw/profile evidence
        -> DATA5 partition and leakage audit
        -> DATA6 profile-aware structural evidence
        -> DATA7 fitted metric and deterministic selection
        -> qualification case record
```

The fixture may be small, but the same public builders and lineage checks used
by production workflows must be exercised. Test-only bypasses of bundle
validation are forbidden.

# 7. Serialization audit

Generic cases recursively scan canonical DATA4, DATA6, and DATA7 payloads for
legacy keys:

```text
lta_partition_features
lta_selection_features
```

The current canonical schemas must not emit these fields. Generic cases must
also contain no active extension whose ID is `lta`. Historical schema readers
remain supported and are tested separately; compatibility does not permit new
canonical evidence to regress to legacy fields.

# 8. Failure semantics

Qualification fails closed for:

- missing explicit material-profile contracts;
- missing phase/geometry plan;
- DATA4--DATA7 digest mismatch;
- wrong phase or geometry for the declared case;
- LTA extension in a generic case;
- missing LTA hierarchy or catalog in the LTA case;
- missing DATA7 selection;
- absent clean-interpreter import evidence;
- forbidden generic imports;
- legacy LTA fields in new generic serialization;
- incomplete suite case coverage;
- tampered qualification records.

# 9. Regression requirements

The focused release gate must include:

- all five DATA4--DATA7 bounded workflows;
- clean top-level import without MLFF LTA modules;
- lazy LTA-symbol loading;
- generic rejection of forbidden import evidence;
- universal-plus-extension DATA7 metric fitting;
- suite completeness and round-trip serialization;
- DATA4/DATA6 historical compatibility tests;
- DATA9A7a--DATA9A7d regression tests;
- dependency-graph acyclicity and documentation assertions;
- source/wheel public API parity.

# 10. Acceptance criteria

DATA9A7e is complete when:

1. all five cases pass the immutable suite policy;
2. generic cases import and serialize no MLFF LTA implementation evidence;
3. the LTA case uses only generic extension envelopes in canonical bundles;
4. DATA4--DATA7 lineage and nonempty selection are proven for every case;
5. the clean source tree and installed wheel expose equivalent qualification
   APIs;
6. the MLFF architecture and dependency graph identify DATA9A7e as implemented;
7. no physical-observable algorithm has moved into the MLFF branch.

# 11. Next stage

DATA9A8 introduces profile-aware observable comparison policies. It consumes
analysis-owned physical results through the standardized observable bridge,
freezes comparison rules before evaluation, aggregates by condition and atom
group, and supports checkpoint decisions without reimplementing the analyses.
