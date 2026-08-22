# Historical narrative: campaign compatibility and migration evolution

**Status:** non-normative history  
**Current authority:** current architecture and the specifications indexed by `docs/specs/training_data/README.md`

## Why compatibility layers existed

During rapid MLFF development, persisted campaign schemas changed alongside selection, evaluation, precision, monitor, profile, and runtime behavior. Migration records and compatibility readers were introduced so an in-progress campaign could sometimes cross one change without full re-preparation.

That was useful during transition but accumulated a second problem: documentation had to explain both the current scientific path and how older generations were interpreted. Eventually migration/readability machinery became part of the apparent architecture rather than temporary transition support.

## What migration could and could not prove

A schema converter can translate field representation. It cannot automatically prove that two generations have the same scientific meaning when any of the following changed:

- statistical evidence roles or blinding;
- fitted-domain boundaries;
- target-membership policy;
- hard-coverage/repair semantics;
- target-size population or screening policy;
- replay/monitor semantics;
- stopping/LR/checkpoint policy;
- precision/backend behavior;
- physical/deployment admissibility.

When those meanings change, preserving old bytes or aliases is not sufficient to establish protocol equivalence.

## Architecture-reset decision

The current MLFF architecture has one semantic generation. A persisted artifact is either valid under the current schema/identity contract or unsupported.

Unsupported old campaigns are re-prepared from their authoritative source evidence. Current product behavior does not include MVMIGRATE, ADAPT-MIGRATE, ML-CV migration, profile-extension migration, or legacy selector/repair construction modes.

Low-level forensic readers may exist in code when useful for diagnosing old evidence, but they are not product-semantic authorities and cannot create current campaign state.

## Why re-preparation is safer

Re-preparation is preferred when scientific identities changed because it:

- rebuilds fitted products from the correct current training domains;
- rebuilds target membership under the sole current selector/repair policy;
- recomputes independent qualification under current predicates;
- recreates monitor/protocol identity without ambiguous aliases;
- avoids silently treating old evaluation roles as current ones;
- reduces permanent code and documentation branching.

The cost is bounded recomputation; the benefit is a single interpretable dependency graph.

## Durable historical evidence

Exact old schemas remain recoverable from Git history and release/audit artifacts when required for forensic interpretation. They need not remain in the current specification directory merely to preserve provenance.

A historical snapshot should be retained as a dedicated artifact only when a durable audit or benchmark cannot be interpreted without its exact schema. Otherwise this conceptual narrative plus repository history is sufficient.

## Durable lessons

1. Backward readability and scientific equivalence are different claims.
2. Migration is a temporary product feature, not a default architectural virtue.
3. Compatibility state machines should have an explicit retirement boundary.
4. Current permanent documentation should explain one current model; history should explain why it changed.
5. Re-preparation from authoritative evidence is often safer than converting derived state whose scientific semantics changed.
