# MLFF OPT-EVAL1 fast checkpoint reconstruction specification

Status: implemented in mdstats 0.20.97a0.

## Objective

Remove the dominant post-selection cost of launching a new MACE training process just
to convert an already-trained epoch checkpoint into a deployable model.  No scientific
evaluation identity or checkpoint metric changes in this stage.

## Reconstruction order

1. Authenticate the raw checkpoint and immutable DATA8 MACE config.
2. Reuse a valid reconstructable checkpoint-model cache entry when available.
3. Locate the completed training whole model under ``runs/<run>/models/<name>.model``.
4. Restore the checkpoint directly:
   - memory-map PyTorch storage when supported;
   - require exact state keys, tensor shapes, and dtypes;
   - for CuEq/OEq training, convert the deployable e3nn template back to the training
     backend under the shared FX lock;
   - compare the training-backend template state with ``checkpoint["model"]``;
   - if already identical, reuse the completed whole model directly;
   - otherwise ``load_state_dict(..., strict=True)`` and convert back to deployable e3nn;
   - write an authenticated reconstructable cache receipt.
5. Fall back to the legacy sandboxed ``mdstats-mace-train`` restart/export only when
   the direct path is unsupported or fails its strict compatibility checks.

LoRA is fallback-only in this version.

## Target-head export

Single-head models serialize directly.  Multi-head MACE models use MACE 0.3.16's own
``remove_pt_head`` implementation in-process with temporary default-dtype scoping.
The qualified ``mdstats-mace-select-head`` wrapper remains fallback-only.  Publication
is staged beside the parent output and committed with ``os.replace``.

## Cache compatibility

The cache schema is v2 and records ``reconstruction_method`` plus
``materialization_elapsed_seconds``.  v1 cache receipts produced by the legacy restart
export remain valid and reusable when checkpoint/config/model hashes match.

## Correctness gates

Focused tests must cover: direct restoration without wrapper execution; exact reuse of
a matching completed training model; rejection of silent dtype casts; fallback to the
legacy path; guarded CuEq conversion; exact energy/force/stress equality for a real MACE
0.3.16 model fixture; in-process multi-head target extraction and reload; source SHA
immutability; atomic export and restart reconciliation.
