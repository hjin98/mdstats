---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P1
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 1
status: active
package_revision: 9
amended_date: 2026-08-28
rework_reason: Independent review after P1A7 confirmed the source/manifest/control/ensemble/energy replay repairs, shared required-label authority, typed provider restart, naming cleanup, source-map reconciliation, and same-candidate affected regression, but found one remaining scientific-integrity blocker in the current-generation neutral statistical aggregate. NeutralStatisticalBase can accept individually well-formed but mutually stale or contradictory feasibility, outer-partition, independence, and leakage state; in particular, a stale leakage report with passed=True is not required to certify the exact persisted outer partition, and coordinated rehashing can preserve structural digest validity while changing scientific meaning. Revision 9 freezes a narrow P1A8 aggregate-coherence and restart-integrity repair without reopening P1A1-P1A7 architecture.
---

# P1 — Neutral scientific substrate

## Purpose

Establish and close the current-generation **scientific identity and neutral statistical substrate** without switching the currently reachable target-size runtime.

P1A1-P1A7 already established the accepted source -> canonical-frame -> neutral-feature -> neutral-statistical architecture. P1 revision 9 preserves that implemented architecture and adds one final closure requirement: a persisted or directly constructed `NeutralStatisticalBase` must be a **single scientifically coherent aggregate**, not merely a collection of individually digest-valid component records.

The parent V7 workplan remains the generation-level authority, while durable product code and persisted schema names remain version-agnostic. The neutral substrate remains internal/unreachable from the production target-size campaign until P4.

### Revision-8 baseline retained without reinterpretation

The complete revision-8 contract and its historical P1A1-P1A7 staging remain available in the immediately preceding P1 blob `3c9f1860f64cee2faf8ecb0aad564a45c2732b66` and are incorporated as the settled baseline. Revision 9 does not reopen or weaken those obligations.

The following settled outcomes are specifically preserved:

- version-agnostic durable names under `mdstats.training_data.neutral_substrate`;
- compatibility-neutral `SourceAuthority`, `CanonicalFrameAuthority`, `NeutralFeatureEvidence`, and `NeutralStatisticalBase` ownership;
- verified originating-manifest association for authoritative DATA2 -> `SourceAuthority` conversion;
- exact companion role/locator replay;
- structurally strict `mdstats.source-record.v2` decoding;
- source-control, ensemble-certificate, reconstructed ensemble-value, and selected-energy channel/units/semantic-role verification on direct VASP rebuild;
- one shared numerical required-label evaluator used by full eligibility and authoritative direct/assembled label construction;
- correct required/optional/forbidden E/F/stress semantics;
- physical-versus-labeled frame distinction and atomic canonical-label/labeled-fingerprint coherence;
- source composition/quality/ensemble propagation into established geometry, temperature, strain, eligibility, duplicate, and partition algorithms;
- compatibility-policy invariance of scientific identity;
- generic-core/provider-owned material-profile rebinding with durable typed LTA restart;
- bounded worker-count-independent per-run canonical-frame construction;
- reconciled `P1_SOURCE_MAP.md` owner graph;
- old production runtime isolation until P4;
- no full GPU/production qualification as part of routine P1 functional closure.

P1A8 is therefore a **narrow implementation-repair package**. Do not replay or redesign settled P1A1-P1A7 mechanisms unless new executable evidence demonstrates a separate genuine defect.

## Blocking defect being repaired

`NeutralStatisticalBase` currently persists/contains:

```text
policy
unit_catalog
feasibility
outer_partition
independence
leakage
```

Each component has local structural/digest checks, but the aggregate constructor does not completely prove that these components describe the **same scientific state**.

The critical demonstrated hole is:

```text
leakage.outer_partition_digest
    is not required by NeutralStatisticalBase
    to equal outer_partition.content_digest
```

so a stale passing leakage certificate can be retained while the outer partition changes.

A mere cross-digest repair is necessary but not sufficient. Because persisted payloads are not cryptographic attestations, a malformed/replayed payload can change an outer partition, update the stored digest references, recompute ordinary content digests, and still carry stale derived findings such as `passed=True`. Therefore P1A8 must validate **semantic derivation**, not only pointer-shaped digest consistency.

## Protected concerns

P1A8 protects these outcomes simultaneously:

- restart/persistence must reproduce a scientifically usable neutral statistical state, not a digest-shaped shell;
- a leakage pass must certify the exact outer partition carried by the same `NeutralStatisticalBase`;
- feasibility, outer-role assignment, independence, and leakage must all derive from the exact same policy and unit catalog;
- changed/replayed/rehashed derived state must fail closed rather than being silently repaired or trusted;
- no unknown, omitted, duplicated, or foreign unit can enter outer-role state unnoticed;
- deterministic current P1 statistical owners remain the only derivation authority; no second validator should reimplement their algorithms;
- normal positive construction and JSON round-trip/restart remain stable;
- compatibility neutrality, provider ownership, prior source/frame scientific semantics, and old-runtime isolation remain unchanged;
- acceptance must exercise the real `NeutralStatisticalBase` construction/deserialization boundary, not only helper comparisons.

## Frozen design decisions

### 1. `NeutralStatisticalBase` owns aggregate semantic coherence

The authoritative validation boundary is `NeutralStatisticalBase` itself (or one private helper invoked unconditionally by its constructor). Any path that creates the aggregate, including `NeutralStatisticalBase.from_dict()`, must cross this validation boundary.

Individual component constructors remain responsible for their local invariants. P1A8 adds the missing **cross-object and derived-state invariants** at the aggregate owner.

### 2. Exact cross-object invariant graph

For every valid `NeutralStatisticalBase`, all of the following must hold.

#### Dataset identity

```text
base.dataset_id == unit_catalog.dataset_id
```

No separate dataset identity may drift at the aggregate level.

#### Policy identity

Let:

```text
P = base.policy.policy_digest
```

Then:

```text
unit_catalog.policy_digest     == P
feasibility.policy_digest      == P
outer_partition.policy_digest  == P
leakage.policy_digest          == P
```

`NeutralIndependenceReport` has no independent policy field and therefore binds through the unit catalog.

#### Unit-catalog identity

Let:

```text
U = unit_catalog.content_digest
```

Then:

```text
feasibility.unit_catalog_digest     == U
outer_partition.unit_catalog_digest == U
independence.unit_catalog_digest    == U
leakage.unit_catalog_digest         == U
```

#### Outer-partition/leakage identity

Let:

```text
O = outer_partition.content_digest
```

Then:

```text
leakage.outer_partition_digest == O
```

A `passed=True` leakage report for any other partition is invalid state.

#### Exact unit membership

Let:

```text
catalog_ids = {unit.unit_id for unit in unit_catalog.units}
assigned_ids = {assignment.unit_id for assignment in outer_partition.assignments}
unassigned_ids = set(outer_partition.unassigned_unit_ids)
```

Require:

```text
assigned_ids.isdisjoint(unassigned_ids)
assigned_ids | unassigned_ids == catalog_ids
```

Existing `NeutralOuterPartition` duplicate/disjoint checks remain in force. P1A8 additionally rejects foreign unit IDs and missing catalog units at the aggregate boundary.

### 3. Cross-digests are necessary but semantic re-derivation is mandatory

After cheap structural/cross-digest checks, the aggregate owner must re-derive the deterministic current P1 statistical products from the bound authoritative inputs and compare them to the persisted components.

The required semantic owners are the existing functions:

```text
assess_neutral_feasibility(unit_catalog, policy=policy)
build_neutral_outer_partition(unit_catalog, recomputed_feasibility, policy=policy)
build_independence_report(unit_catalog)
audit_neutral_leakage(unit_catalog, outer_partition, policy=policy)
```

A valid aggregate requires semantic/content equality with the stored state:

```text
stored feasibility.content_digest
    == recomputed feasibility.content_digest

stored outer_partition.content_digest
    == recomputed outer_partition.content_digest

stored independence.content_digest
    == recomputed independence.content_digest

stored leakage.content_digest
    == recomputed leakage.content_digest
```

Use the **recomputed feasibility** when deriving the expected outer partition. For leakage, audit the stored outer partition after it has been proven to equal the deterministic expected partition; auditing the equivalent expected partition is also acceptable.

This is deliberate. Current P1 exposes no alternate authoritative outer-partition constructor or manual override path. The deterministic builder is the scientific owner, so a restart object that contains a different structurally valid partition is not an equivalent P1 state.

### 4. Do not trust or independently reconstruct derived claims

P1A8 must not close by merely adding:

```python
if self.leakage.outer_partition_digest != self.outer_partition.content_digest:
    ...
```

That check is required, but by itself still permits coordinated rehashing of stale scientific claims.

Likewise, implementation must not hand-code a second approximation of feasibility, role assignment, independence, or leakage logic inside `NeutralStatisticalBase`. Reuse the existing semantic owners above.

### 5. Invalid persisted state rejects; it is not silently repaired

If a constructed or deserialized aggregate fails any invariant or re-derivation comparison:

- reject before returning a usable `NeutralStatisticalBase`;
- do not replace the stored component with a recomputed component and continue;
- do not downgrade the failure to a warning;
- do not mutate `passed`, findings, assignments, digests, or counts to make the object acceptable.

Direct construction should continue to fail with the module's established `TrainingDataInputError` family. Deserialization may surface the established serialization/input exception convention, but it must fail closed and must not bypass constructor validation.

### 6. Positive scientific behavior remains unchanged

For an aggregate built by the existing `build_neutral_statistical_base()` owner:

```text
construction succeeds
content digests remain deterministic
JSON serialization succeeds
JSON deserialization succeeds
round-trip content_digest is unchanged
scientific role/leakage/independence results are unchanged
```

P1A8 is validation/restart hardening. It must not change valid role-selection policy, leakage policy, independence grading, compatibility semantics, or production orchestration.

### 7. No P1A8 profile-dispatch redesign

The independent review noted that `profile_partition_state_changed()` still contains an LTA-specific branch. This is not a demonstrated P1 blocker for the currently supported P1 provider set and is explicitly outside this amendment.

Do not broaden P1A8 into material-profile dispatch redesign unless new evidence shows the currently supported provider contract is scientifically wrong or unusable.

## Implementation authority

### Frozen

Implementation must preserve and enforce:

- all P1A1-P1A7 settled scientific-owner behavior listed above;
- the complete dataset/policy/unit/partition cross-object invariant graph;
- exact outer-partition unit membership against the bound `NeutralUnitCatalog`;
- deterministic semantic re-derivation of feasibility, outer partition, independence, and leakage through the existing owners;
- rejection, not repair, of stale/mismatched/rehashed aggregate state;
- validation on both direct construction and `from_dict()` restart;
- unchanged valid aggregate behavior and content identity;
- old production runtime isolation and no production/GPU qualification requirement.

### Delegated

Implementation may choose:

- whether checks live directly in `NeutralStatisticalBase.__post_init__()` or in one private aggregate-validation helper called from it;
- exact check ordering, provided cheap lineage/membership failures occur before unnecessary derived recomputation;
- exact source/run/component-specific error wording;
- whether semantic equality is compared by `content_digest` or direct object equality when both are exact and deterministic;
- compact parameterization/helper structure for adversarial tests;
- local cleanup of imports/comments caused by this repair.

### Forbidden shortcuts

Implementation may not:

- stop after adding only `leakage.outer_partition_digest == outer_partition.content_digest`;
- trust `leakage.passed` without executing `audit_neutral_leakage()` during aggregate validation;
- trust stored feasibility/independence counts without re-derivation;
- accept a noncanonical but structurally valid outer partition merely because a fresh leakage audit happens to pass;
- implement duplicate feasibility/partition/independence/leakage algorithms inside the validator or tests;
- silently recompute and overwrite invalid persisted state;
- weaken component digest verification or omit top-level restart validation to make fixtures pass;
- use a helper-only test as proof that `NeutralStatisticalBase.from_dict()` rejects corrupted restart state;
- reopen source, canonical-label, profile, or runtime-cutover architecture without a new demonstrated defect.

### Reopen only on evidence

Reopen only the affected design surface if implementation proves one of the following:

- a supported P1 caller intentionally constructs a scientifically valid `NeutralOuterPartition` that differs from `build_neutral_outer_partition()` and is intended to survive restart;
- a stored derived report contains intentional non-deterministic/user-authored scientific state that cannot be exactly regenerated by its current owner;
- exact regeneration is materially infeasible at expected P1 restart scale and repository evidence shows a real resource/latency problem rather than speculation;
- the established component content digest intentionally excludes a material semantic field needed for comparison.

If such evidence appears, stop only the dependent P1A8 work and reopen the smallest affected design surface. Do not weaken validation silently.

## Entry conditions for P1A8

- Start from branch `plan/mlff-target-size-training-priority-eval-ladder-reset` at or after P1A7 implementation commit `561d56f1b5c7bb30378b6e04cade12a13cf14129`.
- Treat the revision-8 P1A7 acceptance as settled evidence unless P1A8 changes can plausibly invalidate a claim.
- Active implementation surfaces are initially bounded to:
  1. `mdstats/training_data/neutral_substrate/partition.py` — aggregate coherence owner;
  2. `tests/test_mlff_neutral_scientific_substrate.py` — focused constructor/restart adversarial cases;
  3. `workplans/active/mlff-target-size-v7-packages/P1_SOURCE_MAP.md` — add final aggregate/restart ownership description;
  4. affected DATA5/neutral-substrate regression and final assembled P1 regression evidence.
- Source authority, frame authority, required-label evaluator, DATA4/provider rebinding, and production campaign orchestration are preservation surfaces unless a new failing affected regression demonstrates otherwise.

## P1A8 implementation sequence

Implement in this order.

### Stage A — make `NeutralStatisticalBase` a complete aggregate validator

**Primary owner:** `mdstats/training_data/neutral_substrate/partition.py`

Required implementation:

1. Retain the existing local `NeutralStatisticalBase` checks; strengthen them rather than replacing valid component validation.
2. Validate `base.dataset_id == unit_catalog.dataset_id`.
3. Validate the exact policy-digest graph across unit catalog, feasibility, outer partition, and leakage.
4. Validate the exact unit-catalog-digest graph across feasibility, outer partition, independence, and leakage.
5. Validate `leakage.outer_partition_digest == outer_partition.content_digest`.
6. Validate exact outer-partition membership:
   - every assigned/unassigned ID belongs to the unit catalog;
   - every catalog unit appears exactly once as assigned or unassigned;
   - preserve existing duplicate/disjoint checks.
7. Recompute feasibility from `unit_catalog + policy`; require exact semantic/content equality to stored feasibility.
8. Recompute the canonical outer partition from `unit_catalog + recomputed feasibility + policy`; require exact semantic/content equality to stored outer partition.
9. Recompute independence from `unit_catalog`; require exact semantic/content equality to stored independence.
10. Recompute leakage through `audit_neutral_leakage(unit_catalog, stored_outer_partition, policy=policy)`; require exact semantic/content equality to stored leakage.
11. Continue to require the accepted leakage result to pass; a recomputed leakage error is a hard failure.
12. Ensure `NeutralStatisticalBase.from_dict()` necessarily executes this validation and cannot materialize a usable object through a bypass path.
13. Do not mutate any supplied component during validation.

Implementation may factor steps 2-11 into one private helper to keep `__post_init__()` readable. The helper is an orchestration validator only; the scientific calculations remain owned by the existing functions.

#### Stage-A focused acceptance

Before proceeding to Stage B, run bounded tests proving:

- an unchanged `build_neutral_statistical_base()` product still constructs;
- unchanged JSON round-trip still constructs and preserves `content_digest`;
- stale leakage bound to a different outer partition rejects;
- a changed outer partition whose digest is also copied into a stale `LeakageReport` still rejects after fresh leakage/partition re-derivation;
- an altered independence report with self-consistent local digest rejects;
- an altered feasibility report with self-consistent local digest rejects;
- foreign/missing outer-partition unit IDs reject;
- a mismatched policy digest anywhere in the aggregate rejects.

Stage A is not closed if these cases are proved only by calling the new private validator directly. At least the construction boundary must execute.

After Stage A, run the affected neutral statistical/partition/leakage regression subset before editing dependent acceptance/docs.

### Stage B — adversarial persistence/restart proof through the real deserializer

**Primary acceptance owner:** `NeutralStatisticalBase.from_dict()`.

Add explicit restart tests using real `NeutralStatisticalBase.to_dict()` / component serializers and the real deserializer.

Mandatory cases:

#### B1 — stale certificate / changed partition

1. Build a valid base through `build_neutral_statistical_base()`.
2. Serialize it.
3. Replace the serialized outer partition with another locally valid outer partition over the same unit catalog while retaining the old leakage report.
4. Ensure component-local digests are valid for the supplied component objects.
5. `NeutralStatisticalBase.from_dict()` must reject.

This proves the direct blocker.

#### B2 — coordinated rehash cannot counterfeit leakage validity

Construct a stronger adversarial payload:

1. Start from a valid base.
2. Change the outer assignments in a way that changes scientific role state.
3. Recompute/serialize the changed outer partition so its own `content_digest` is valid.
4. Construct/serialize a leakage object whose `outer_partition_digest` points at that changed partition but whose findings/pass counts remain stale or otherwise disagree with a fresh `audit_neutral_leakage()`.
5. Recompute ordinary component content digests so the payload is locally self-consistent.
6. `NeutralStatisticalBase.from_dict()` must still reject.

This case is mandatory because it distinguishes semantic validation from mere cross-digest validation.

#### B3 — noncanonical outer assignment even if leakage passes

Create an alternate locally valid partition over the same units that can pass the narrow leakage audit but differs from the deterministic result of `build_neutral_outer_partition()` (for example, where feasible, moving protected role state to a different otherwise legal unit or collapsing role state without triggering the leakage-only checks).

The restart must reject because current P1 outer-role assignment is deterministic owner state, not arbitrary persisted user input.

#### B4 — stale feasibility / independence

Independently replace feasibility and independence with locally valid/rehashed but semantically incorrect records over the same declared unit catalog. Each restart must reject after re-derivation.

#### B5 — unit membership corruption

Cover at least:

- foreign unit ID in an assignment;
- one catalog unit omitted from both assigned and unassigned sets.

Both must reject at the aggregate boundary.

#### B6 — positive restart control

The original untouched payload must continue to round-trip and preserve complete aggregate `content_digest`.

Allowed test doubles may reduce the upstream VASP/data-generation cost, but **must not replace, monkeypatch, or reimplement `NeutralStatisticalBase.from_dict()`, `assess_neutral_feasibility()`, `build_neutral_outer_partition()`, `build_independence_report()`, or `audit_neutral_leakage()` for the claims they establish.**

After Stage B, rerun affected current-owner serialization/restart and DATA5 partition/leakage tests.

### Stage C — reconcile `P1_SOURCE_MAP.md`

This is documentation/architecture reconciliation only.

Add the final current-generation statistical owner chain:

```text
NeutralFeatureEvidence
  -> build_neutral_unit_catalog(...)
  -> NeutralUnitCatalog
       + NeutralPartitionPolicy
       -> assess_neutral_feasibility(...)
       -> build_neutral_outer_partition(...)
       -> build_independence_report(...)
       -> audit_neutral_leakage(...)
  -> NeutralStatisticalBase
       validates exact dataset/policy/unit/partition lineage
       re-derives deterministic feasibility/outer/independence/leakage state
       rejects stale/replayed/rehashed restart state
```

The source map must explicitly state:

- `leakage.passed` is not trusted independently of a fresh audit;
- `leakage.outer_partition_digest` must bind the exact stored outer partition;
- restart uses the same scientific owners as initial construction rather than a deserializer-only approximation;
- current P1 outer partition is deterministic owner state, not an arbitrary persisted override;
- old production target-size runtime remains isolated until P4.

Do not rewrite settled source/frame/profile ownership sections except where necessary to connect this final aggregate boundary.

### Stage D — final same-candidate functional closure

After Stages A-C:

1. reconcile the implementation against revision 9;
2. re-derive the final affected surface from the assembled candidate;
3. execute focused P1A8 tests plus all affected neutral statistical/DATA5 regression;
4. rerun P1-D/P1-E assembled neutral-substrate integration because the aggregate construction/restart acceptance boundary changed;
5. rerun current-owner serialization/roundtrip tests;
6. rerun repository/project-required Python/package checks for the final candidate;
7. broaden to the available wider regression suite if impact cannot be confidently bounded;
8. resolve every new or plausibly affected hard failure before closure;
9. record demonstrably unrelated pre-existing failures separately;
10. do not run long GPU/full-production qualification merely to close P1A8.

A required check that did not execute is not a pass.

## Required affected regression surface

At minimum account for and execute relevant tests covering:

- `NeutralStatisticalBase` direct construction;
- `NeutralStatisticalBase.to_dict()` / `from_dict()` round-trip;
- `NeutralPartitionPolicy` / role-budget serialization;
- `NeutralUnitCatalog` construction and identity;
- feasibility outcomes and calibration deferral;
- deterministic outer-role assignment and purge semantics;
- independence report construction;
- leakage audit disjointness and temporal-purge checks;
- material-profile-dependent independence grading paths insofar as they feed the same unit catalog;
- compatibility-domain/CV absence from neutral statistical identity;
- P1-E real-owner source -> frame -> feature -> statistical integration;
- P1-E compatibility-policy invariance of final scientific identity;
- prior P1A7 direct-source/required-label regressions if final impact analysis shows the shared P1 integration harness or imports were touched;
- repository-required package/import/static checks.

Do not rerun unaffected expensive source/frame focused tests solely because P1A8 exists; final affected-surface derivation, not ceremony, decides reuse versus rerun.

## Exact P1A8 acceptance checklist

P1A8 cannot be marked complete until all of the following are true:

- [ ] `NeutralStatisticalBase` validates `dataset_id == unit_catalog.dataset_id`.
- [ ] Policy digest is identical across policy, unit catalog, feasibility, outer partition, and leakage.
- [ ] Unit-catalog digest is identical across unit catalog, feasibility, outer partition, independence, and leakage.
- [ ] `leakage.outer_partition_digest == outer_partition.content_digest` is enforced.
- [ ] Outer assigned + unassigned unit IDs exactly cover the bound unit catalog with no foreign/missing IDs.
- [ ] Stored feasibility equals a fresh `assess_neutral_feasibility()` result.
- [ ] Stored outer partition equals a fresh deterministic `build_neutral_outer_partition()` result using recomputed feasibility.
- [ ] Stored independence equals a fresh `build_independence_report()` result.
- [ ] Stored leakage equals a fresh `audit_neutral_leakage()` result for the exact stored partition.
- [ ] The aggregate still rejects if the fresh leakage audit does not pass.
- [ ] Aggregate validation runs for both direct construction and `from_dict()` restart.
- [ ] Invalid state is rejected rather than silently repaired.
- [ ] Positive direct construction remains unchanged.
- [ ] Positive JSON round-trip preserves aggregate `content_digest`.
- [ ] Stale leakage + changed partition constructor/restart negative passes.
- [ ] Coordinated changed-partition + updated leakage partition digest + stale leakage findings/pass negative passes.
- [ ] Noncanonical but leakage-clean outer partition restart negative passes.
- [ ] Rehashed stale feasibility restart negative passes.
- [ ] Rehashed stale independence restart negative passes.
- [ ] Foreign and missing unit-ID restart negatives pass.
- [ ] Policy-lineage mismatch negative passes.
- [ ] Tests exercise the real aggregate constructor/deserializer and real semantic owners rather than helper-only proxies.
- [ ] `P1_SOURCE_MAP.md` records the final aggregate/restart authority.
- [ ] Final affected neutral statistical/DATA5 regression passes on the same candidate.
- [ ] Final P1-D/P1-E assembled integration passes on the same candidate.
- [ ] Repository-required Python/package checks execute.
- [ ] No long GPU/full-production qualification is used as a substitute for functional acceptance.

## P1 exit gate

P1 is accepted only when the settled P1A1-P1A7 exit conditions remain true **and** the assembled current-generation neutral statistical state satisfies all P1A8 conditions below:

- aggregate dataset identity matches the unit catalog;
- every derived component is bound to the exact same policy and unit catalog where applicable;
- leakage certifies the exact stored outer partition;
- outer-role state covers exactly the bound units and contains no foreign/missing unit identity;
- feasibility, deterministic outer partition, independence, and leakage are freshly reproducible by their established current-generation owners;
- persisted/restarted aggregate state cannot counterfeit validity by merely updating digest references or ordinary content digests;
- direct construction and restart reject stale/contradictory semantic state rather than silently repairing it;
- valid aggregate construction/restart remains deterministic and unchanged;
- no compatibility-domain or pre-target CV authority enters neutral statistical identity;
- old production runtime remains unswitched;
- all mandatory focused, affected-regression, integration, and repository-required checks execute successfully, with only demonstrably unrelated pre-existing failures separately bounded.

## Explicitly insufficient / non-closing states

The following do **not** qualify P1A8 or P1:

- checking only `leakage.passed`;
- adding only `leakage.outer_partition_digest == outer_partition.content_digest` without semantic re-audit/re-derivation;
- accepting changed outer-role assignments after updating stored digest references;
- accepting a partition that passes the narrow leakage audit but differs from the deterministic current P1 outer-partition owner;
- trusting stored feasibility or independence counts merely because their local content digests are valid;
- accepting foreign or missing unit IDs because the outer partition object is locally well formed;
- recomputing invalid components and silently substituting the corrected values during restart;
- testing a private validator/helper while bypassing `NeutralStatisticalBase` construction or `from_dict()`;
- reimplementing feasibility/partition/independence/leakage logic in the test harness;
- weakening component or aggregate digest checks to simplify adversarial fixtures;
- treating source inspection as a substitute for affected regression/integration;
- using a production-scale/GPU run as a substitute for missing functional restart tests;
- unrelated architecture cleanup presented as required P1A8 work without evidence.

Once P1A8 satisfies this exit gate, P1 may be frozen and downstream package work may proceed without reopening the settled P1 scientific-owner design absent new evidence.
