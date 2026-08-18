# Bounded Strong-Ring Classification Audit

Date: 2026-07-18  
Version: `0.19.18a0`  
Architecture: revision 25

## Scope

This gate classifies primitive rings inside an explicit finite translated-placement domain. It enumerates target-connected smaller primitive-ring placements through exact physical-edge incidence, solves exact support membership over `GF(2)`, and returns either a verifiable weak-ring witness, a bounded negative certificate, or an unresolved status.

It does not claim global strength at finite incidence depth, local strength in a tile, face embeddability, or natural-tiling membership.

## Implemented contracts

- immutable `EdgeIncidencePlacementDomain`;
- immutable `RingStrengthDomain` and separate `RingStrengthResources`;
- exact physical lifted-edge incidence expansion;
- deterministic finite candidate enumeration;
- source-completeness validation for lower-closed untruncated primitive catalogs;
- exact finite `GF(2)` span solve through the Stage-5 cancellation backend;
- independently verified weak-ring witnesses;
- bounded negative `STRONG_IN_DOMAIN` semantics;
- transactional unresolved statuses for source or resource incompleteness;
- deterministic single-result and catalog serialization; and
- source-bound canonical digests.

## Mathematical boundary

The strong-ring definition follows Goetzke and Klein (1991) and Yuan and Cormack (2002). The first placement domain is an mdstats construction on the bipartite graph of exact physical edge instances and translated primitive-ring placements.

A minimum-cardinality witness may be taken target-connected: any disconnected support component not containing the target sums to zero independently and can be removed. Therefore increasing incidence depth gives a monotone sequence of finite domains and eventually contains any fixed finite witness. No finite depth is promoted to an unbounded theorem.

## Source requirements

Certified statuses require:

```text
ring family == PRIMITIVE_NO_SHORTCUT
primitive min ring size == 2
source search untruncated
complete_for_ring_sizes_up_to >= max_component_size
```

Failure returns `UNRESOLVED_SOURCE_INCOMPLETE` without candidate enumeration.

## Resource semantics

`max_candidate_placements`, `max_search_nodes`, and `max_support_terms` limit execution only. Exceeding a limit returns `UNRESOLVED_TRUNCATED`; the partial candidate set is diagnostic and is never solved or promoted to a scientific classification.

## Na-LTA ground result

For the complete primitive catalog through size eight and incidence depth one:

```text
4R: 36 STRONG_IN_DOMAIN
6R: 24 WEAK_CERTIFIED + 16 STRONG_IN_DOMAIN
8R: 6 STRONG_IN_DOMAIN
```

Each weak 6-ring carries an exact three-component 4-ring witness. These results align with the five ring orbits discovered by Stage 6C but do not yet select natural-tiling faces.

## Validation

Focused Stage-4/5/6/7 gate:

```text
113 passed
```

Coverage includes exact weak decomposition, bounded negative classification, translation covariance, source incompleteness, transactional resource truncation, serialization/source mismatch rejection, and the full Na-LTA ring catalog.

## Gate decision

**PASS.**

The next scientific stage is the authoritative `PeriodicNetEmbedding`; symmetry-equivariant strength-orbit acceleration remains deferred until domain equivariance is specified.
