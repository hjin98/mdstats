# mdstats 0.20.69a0 prepare restart optimization

## Problem

A plain `prepare` invocation after a successful campaign skipped DATA2-DATA5 but
still entered DATA6 finalization. Valid descriptor/prediction sidecars prevented
new MACE inference, yet the orchestration repeated substantial work:

- restored and verified the complete DATA6 sweep;
- compacted checkpoint/manifests again;
- rebuilt the finalized DATA6 feature bundle;
- rewrote sharded DATA6 state;
- reconstructed foundation energies;
- revalidated or rematerialized every DATA7/DATA8 variant.

The restart was scientifically safe but not economical.

## Correction

The campaign now writes a durable prepare restart receipt after the production
DATA9A gate passes. The receipt binds:

- the scientific prepare contract and parser versions;
- exact `campaign.toml` SHA-256;
- file-stat identities for the manifest, foundation model, replay files, and
  every source trajectory;
- persisted scientific-record digests;
- the compact DATA6 sweep checkpoint/plan identity;
- every DATA8 variant, plan, bundle, and promoted-tree digest.

An unchanged plain `prepare` validates this compact evidence and returns without
running DATA2-DATA9A. A completed 0.20.68a0 campaign can be adopted into the
receipt directly, provided the current DATA8 parser, variant identity checks,
production qualification, and complete sweep pointer all pass.

For a genuinely changed downstream protocol, restart is selective:

1. a matching completed DATA6 sweep is restored without constructing MACE,
   running inference, or eagerly scanning all sidecars;
2. finalized DATA6 is reused only when all scientific lineage and policy
   identities match exactly;
3. unchanged DATA7/DATA8 variants retain their existing content-addressed trees;
4. only changed or invalid variants are rebuilt;
5. foundation-energy reconstruction is delayed until a rebuild actually needs
   it;
6. normalized trajectory arrays are restored lazily, so DATA8-only changes do
   not load the full frame cache.

## Integrity behavior

The fast path does not weaken scientific identities. A changed configuration,
input file stat identity, record digest, sweep identity, DATA8 plan/bundle/tree
identity, missing runtime directory, or failed production qualification leaves
the fast path and resumes from the earliest affected phase. Explicit
`prepare --rebuild-catalog` still forces source/catalog reconstruction.
