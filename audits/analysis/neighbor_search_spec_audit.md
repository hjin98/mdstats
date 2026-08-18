# Periodic-Neighbor Specification Consistency Audit

## Normative contract

The production execution contract is defined by:

```text
docs/specs/analysis/neighbor_search_spec.md
docs/specs/analysis/neighbor_search_spec.pdf
```

The Markdown source is authoritative. The PDF is generated from the same source.

## Public API alignment

The source and specification agree on:

```python
NeighborSearchOptions(
    backend="auto",
    cache_mode="auto",
    skin=0.5,
    deformation_aware=True,
    dense_pair_threshold=32768,
    minimum_cache_frames=2,
    max_consecutive_zero_reuse_rebuilds=3,
)
```

Allowed cache modes are `"auto"`, `"none"`, and `"verlet"`.

The integrated public calls remain:

```python
compute_pair_rdf(..., neighbor_search_options=None)
compute_coordination_distribution(..., neighbor_search_options=None)
compute_bond_angle_distribution(..., neighbor_search_options=None)
compute_atomic_connectivity(
    ...,
    neighbor_search_options=None,
    verlet_cache_options=None,
)
```

The connectivity `verlet_cache_options` argument remains a backward-compatible explicit cache path. Passing both option families is rejected.

## Semantic policy alignment

The implementation and documents use the same conservative resolution:

| Selected semantics | Automatic cache result |
|---|---|
| One frame | Stateless |
| Time-ordered trajectory | Verlet when otherwise eligible |
| Independent ensemble | Stateless |

An explicit `cache_mode="verlet"` bypasses the semantic default but not geometric validity checks. Changed-cell independent ensembles do not infer continuous fractional unwrapping.

## Runtime shutoff alignment

The source and specifications define a completed cache interval as the frames between one build and the next rebuild. The initial build is not a failed interval. A zero-reuse interval increments the request-local counter; successful reuse resets it. At the configured limit, the request switches to a stateless physical-cutoff cell list and records:

```text
cache_mode_selected = verlet_then_none
cache_disable_reason = repeated_zero_reuse
fallback_event = repeated_zero_reuse_to_stateless
```

## Diagnostic alignment

The production schema is `mdstats.periodic-neighbor-search.v2`. Source and specification agree on:

- frame semantics;
- requested and selected cache modes;
- cache-resolution reasons;
- runtime cache-disable state and reason;
- consecutive zero-reuse count and configured limit;
- inherited backend, candidate, acceptance, rebuild, reuse, interval-margin, and singular-value fields.

## Revised document inventory

| Document | Markdown SHA-256 | PDF SHA-256 | PDF pages |
|---|---|---|---:|
| `docs/specs/analysis/neighbor_search_spec.md` | `bc87e34b52b941dd2d7f09e42eeeccd1652ad1c38a9b9a79d3d4d8fc89f703bb` | `796b8079c4c216d98736995e563184992eb3972f5bf01d9a44dd83657120efec` | 20 |
| `docs/specs/analysis/_neighbors_spec.md` | `c0afea5df065ae543f34e71fb9382e73cc7c091c2c511be55e0080cb8626fb1b` | `6391bcd9deefdf83777b531d2bff25a79444427e70dce28091bbe98f7758f01c` | 14 |
| `docs/specs/collection_spec.md` | `1e5485a30a9bd5051ff716132bcf84b8137b064945a4f60a6fad4e4a9ba04200` | `1b4ac435f0a33210b95f6579ebbcffefd075f376284be938b42641381024d4b2` | 13 |
| `docs/specs/analysis/_verlet_cache_deformation_spec.md` | `060eb710ec26cfed7cc8f6ff15ba99ed6df3144245d7744908cfb781ad526a20` | `d4a89d4d0ffcc9a790fca36a5abf739cf4cfc157fc42c5c41afbc4215c242dbf` | 18 |
| `docs/arch_manuals/periodic_neighbor_search_architecture.md` | `211c88d768fcdbc4d4ccef65922fb920bf289786409208f5dabe4f0479dbb054` | `349baff6c86d8c417d9653795a044a5782781f2355bb505e203894288217aea8` | 26 |
| `docs/specs/analysis/rdf_spec.md` | `4e47228d2ad1d80610e44d345fef556ad31a51f311ce241c3f495b76b5009101` | `f6f2e251f0e406f334d7a53276b5cc69af659e3e82d9c063329aea8303d0fa82` | 9 |
| `docs/specs/analysis/coordination_spec.md` | `b97fea4e5f459c3da324fdd825f312eb6256783f6f2560c71737fb1b77ac7e5a` | `bfe17afcc343900783701fe45e80a21573a0ca5b02dc969b8e3dcc26bb2c1076` | 9 |
| `docs/specs/analysis/bond_angle_spec.md` | `e136d0ab85db0f373479bed718293f66e374f94e4aa59885cd78cff97da0d612` | `6b02cee5f2627c6d3752da93d1117e961e9a5045f02b1940d48a7f45a60690e1` | 13 |
| `docs/specs/analysis/atomic_connectivity_spec.md` | `9d2ea5b64677b135a2a68b87c0a03875cd673e41821a43db23cbe2ef5a6ba59b` | `0b8b0f8b1ef0ad42789ef99184ee6cb28fdefc55734160b6ec604eee68de74ef` | 28 |

All nine PDFs, totaling 150 pages, passed structural preflight and rendered-page inspection.

## Verification

- Public policy/source comparison: passed
- Consumer delegation comparison: passed
- Obsolete multi-frame cache-default wording search: no unresolved match
- Markdown/PDF regeneration: passed
- PDF preflight: passed
- Visual layout inspection: passed
- Focused policy tests: 17 passed
- Complete regression: 289 passed

No unresolved source/specification inconsistency was found.
