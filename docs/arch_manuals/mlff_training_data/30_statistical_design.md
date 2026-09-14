# Part III - Evidence flow and fitted-product integration

## Purpose and boundary

This chapter owns the D3 integration structure that carries accepted D1 evidence semantics and D2 constructions into executable MLFF products. Scientific meanings such as independence, leakage, target-size interpretation, objective semantics, and validity are owned by D1. Numerical definitions such as correlation units, deterministic orders, common fitting, weighting algorithms, and fold construction are owned by D2.

D3 therefore answers a narrower question: which software owner may create, persist, consume, or invalidate each product, and in what dependency direction?

## Evidence-role pipeline

The architectural flow is:

```text
canonical frame/evidence authority
  -> neutral statistical substrate and protected-relation authority
  -> pre-order fitted selection evidence
  -> target-size split/order owner
  -> common target-size training preparation
  -> target-size execution/reducer evidence
  -> operator-owned provisional design
  -> cross-validate admission / frozen target bindings
  -> post-selection fold-local products
  -> final-production products
```

Each arrow is one-way. A downstream consumer may challenge an upstream product with evidence, but it cannot mutate or reinterpret the upstream product in place.

The canonical D1 role semantics and D2 relation/allocation algorithms are not repeated here. Their D3 consequence is that role-bearing and membership-bearing artifacts must bind exact parent identities, and consumers must reject stale, foreign, or incomplete ancestry rather than reconstructing a convenient substitute.

## Pre-order evidence versus common training preparation

Two fitted stages exist on opposite sides of the target-order boundary and are separate architectural owners.

### Pre-order selection evidence

DATA6/DATA7-style providers may publish candidate-independent descriptors, fitted feature transforms or metrics, foundation predictions, difficulty evidence, condition/event/environment evidence, and other authorized ordering inputs. Every fitted product binds its fit domain and recipe identity. The target-order owner consumes these products through their canonical interfaces; it does not refit them inside candidate execution.

These providers do not own target membership, candidate qualification, target size, or cross-validation.

### Common target-size training preparation

After the target-size split and canonical orders exist, the P3 preparation owner publishes one `TargetSizeCommonPreparation` for the accepted training pool. Candidate execution consumes projections of that product. It does not create one independent fitted preparation per target size or optimizer seed.

Exact fitted quantities and projection semantics are D2. Exact schema, serialization, policy fields, and resolver code are D4. D3 requires only one authenticated common owner and one dependency direction.

## Post-selection fold-local products

After `cross-validate` freezes the target binding, the post-selection owner may create fold-local products whose fit domain is the fold-authorized training partition. Such products are descendants of the frozen binding and fold plan. They cannot change the frozen target membership, create another target-size order, or become reusable outside the lineage they name.

A fold checkpoint monitor, held-out evaluation partition, replay monitor, and training partition remain separate interfaces even when one runtime process materializes more than one of them.

## Objective, weighting, and exposure integration

D1/D2 distinguish the global training objective, per-configuration weighting, local property-availability masks, and runtime exposure. D3 preserves that separation by routing each value from its single resolver/owner into the executable training plan without introducing a second policy surface.

The current integration uses the shared training-data configuration resolvers and the MACE execution adapter. Exact defaults, validation ranges, serialized fields, and dependency-facing arguments belong to D4 specifications. A CLI, materializer, or executor may carry resolved values but must not independently default, reinterpret, or renormalize them.

## Identity and invalidation

A fitted product identity binds, as applicable:

- the exact parent evidence or membership;
- the fitting/method policy identity;
- the fit domain;
- the required foundation/head or external model identity; and
- the representation version needed for authenticated reuse.

Invalidation follows semantic dependency rather than pathname proximity. A change that affects only a fold-local product does not invalidate target-size evidence. A change to a common P3 input invalidates descendants that consume that preparation. A presentation/report change does not invalidate scientific or numerical products.

## Failure routing

D3 routes typed failure rather than converting it into another evidence role. Typical examples include unavailable labels, incompatible ancestry, infeasible protected-relation allocation, failed fitted preparation, missing fold-local authority, stale lineage, and unavailable execution capability.

If the failure exposes a contradiction in scientific meaning, route to D1. If it exposes a numerical-method contradiction, route to D2. If the accepted D1/D2 method is coherent but component ownership or dependency flow is defective, it is a D3 issue. Schema/parser/implementation defects under a coherent architecture remain D4.
