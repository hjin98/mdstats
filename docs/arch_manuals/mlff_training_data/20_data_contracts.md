# Data contracts and integration boundaries

## Canonical evidence plane

The data plane is architected as a one-way normalization path:

`raw/source occurrence -> source adapter -> canonical frame/evidence record -> role/sampling products -> model-ready projection`.

Source adapters own parsing and source-specific representation. Canonical records expose stable identities, geometry, label availability, provenance, condition evidence, and relation evidence required by downstream owners. The scientific meaning of those fields is D1; numerical construction is D2; exact serialized fields and adapter rules are D4.

## Identity and provenance

Downstream artifacts bind immutable upstream identities rather than reconstructing ancestry from paths or display metadata. Membership-bearing products bind exact member identities and parent identities. Fitted products additionally bind their fit domain and policy/method identity. A cache key is not evidence unless the owning contract explicitly promotes it to an authoritative identity.

## Adapter boundary

External-source conventions are translated once at the adapter boundary. Central MLFF code consumes canonical evidence and must not branch on VASP-, ASE-, MACE-, or filesystem-specific incidental details unless an explicit D4 adapter interface requires it. Source-specific contracts are indexed by `../../specs/training_data/README.md`.

## Availability and failure propagation

Missing labels, malformed source state, incompatible evidence, failed fitting, numerical failure, and unavailable runtime capability are distinct outcomes. D3 routes these typed outcomes between owners; it does not collapse them into fabricated values or silently substitute another scientific role.

## Artifact classes

The architecture distinguishes:

- authoritative evidence and memberships that must survive restart;
- fitted method products whose identity binds the authorized fit domain;
- execution progress required for exact continuation/recovery;
- generated reports/publications derived from canonical sources; and
- disposable caches/scratch that can be reconstructed without changing authority.

Persistence and cleanup decisions must preserve this distinction.
