# P3 TRAIN2/EVAL2 realized MACE architecture identity repair — implementation evidence

Workplan: `P3_TRAIN2_EVAL2_REALIZED_MACE_ARCHITECTURE_IDENTITY_REPAIR.md`
Branch: `plan/mlff-storage-io-reset-r37-review-closure`
Environment: conda `mace`, Python 3.11, torch 2.13.0+cu126, **mace-torch 0.3.16**

---

## 1. Gate A — realized-construction census

The census was performed **empirically against the pinned dependency**, not by reading
alone: a probe drove real `mace.cli.run_train.run(...)` with the production executable
configuration, intercepted `configure_model(...)`, and diffed the canonical
`_mace_model_execution_architecture_descriptor(...)` of the real model against the
descriptor of `build_mace_model_from_configuration(...)` — every module, parameter
name/shape/dtype, buffer name/shape/dtype/value, head list, and per-interaction
`avg_num_neighbors`.

Four model-affecting divergences existed at the `configure_model` boundary. Two were the
reported ones; two more were found only by the exhaustive diff and would have caused the
next round of the same failure.

| # | Field | Real TRAIN2 (pinned MACE) | Pre-repair reconstruction | Class | Repair |
| --- | --- | --- | --- | --- | --- |
| 1 | dataset/model head | `['Default']` via `prepare_default_head(args)` because `--heads` was unset | `['target_head']` | forbidden fallback namespace | P3 projects its canonical target dataset head to `--heads` |
| 2 | `avg_num_neighbors` | recomputed per candidate by `get_avg_num_neighbors(head_configs, args, train_loader, …)` (parser default `compute_avg_num_neighbors=True`) | parser default carried in the architecture | forbidden candidate-local model refit | fitted once over P2 `P_train`; executable emits `compute_avg_num_neighbors=False` |
| 3 | `scale_shift.scale` buffer shape | `[1]` — `configure_model` rewrites `args.std` into a per-head list when `head_configs` is present | `[]` (0-dim) — `head_configs=None` | reconstruction infidelity | reconstruct through real `HeadConfig` objects |
| 4 | `atomic_energies_fn.atomic_energies` buffer shape | `[1, n_elements]` — `dict_to_array(atomic_energies_dict, heads)` | `[n_elements]` | reconstruction infidelity | pass per-head atomic energies of shape `(n_heads, n_elements)` |

Fields verified equal and requiring no change: model family/class, atomic-number
table/order, `r_max`, radial basis/cutoff basis/`radial_type`/`distance_transform`,
interaction classes and count, hidden/edge irreps and `num_channels`/`max_L`
derivation (`check_args` recomputes `hidden_irreps` from `num_channels`+`max_L` to the
same irreps), product/`correlation`/readout settings, `radial_MLP`, dtype/precision,
`scaling`/`mean`/`std` roles, embedding/readout/cutoff flags, `cueq` config
(`only_cueq` false both sides), foundation state (absent — P3 is scratch screening).

**Gate A exit:** after the repair the same probe reports **0 descriptor differences**
between the real `run_train` model and the reconstruction, with `heads == ['target_head']`
and the common `avg_num_neighbors` on both sides.

---

## 2. What changed, by owner

### `mdstats/training_data/target_size_execution/common.py`

- `fit_common_mace_neighbor_normalization(...)` — the one common fit. Membership is the
  exact P2 `P_train` (`common_membership`, already validated as such by
  `validate_against_aggregate`). Neighbourhoods come from MACE's own
  `mace.data.neighborhood.get_neighborhood` at the template's `r_max`, so cutoff and
  periodic-image semantics are the dependency's. It reproduces
  `modules.compute_avg_num_neighbors` exactly — the mean over atoms with at least one
  in-cutoff neighbour, which is batch-independent because each count is per-atom. It
  fails closed if the result is not finite and strictly positive.
- `realize_common_mace_architecture(...)` — binds the fitted scalar into the seed-neutral
  template through the existing `canonicalize_mace_candidate_architecture` owner.
- `TargetSizeCommonPreparation.realized_mace_architecture` — a **required** field (no
  permissive default). It is validated in `__post_init__`, enters `_payload()` and
  therefore `content_digest`, and is exposed as `common_avg_num_neighbors`.
- `build_target_size_common_preparation(..., mace_architecture=None)` resolves the
  template once and fits the normalization once.

No second normalization authority and no normalization database were introduced: the
scalar lives inside the realized architecture, next to the `r_max` that gives it meaning
and inside the record that already binds the membership digest.

### `mdstats/training_data/target_size_execution/candidate.py`

`_mace_config_for_candidate(...)` now takes its architecture from
`common.realized_mace_architecture`. A caller-supplied `mace_architecture` is admissible
**only** if it is exactly that one, otherwise it fails closed — candidate-local model
construction is not reachable. The config emits `compute_avg_num_neighbors: False`.

### `mdstats/training_data/campaign_target_size_runtime.py`

`mace_run_configuration(...)` projects the canonical `multi_head` mapping into MACE's
`--heads` argument through the existing `mace_heads_literal` serializer, and refuses a
configuration that is multihead, that leaves `compute_avg_num_neighbors` enabled, or that
does not carry exactly the `target_head` dataset head. The internal architecture `heads`
list is still never projected. `_execute_candidate_cell(...)` passes the common realized
architecture into materialization.

### `mdstats/training_data/model_features.py`

`build_mace_model_from_configuration(...)` reconstructs through the same
`configure_model` call shape production uses: real `HeadConfig` objects and per-head
atomic energies. `_mace_model_execution_architecture_descriptor(...)` was **not**
weakened — no field was removed or relaxed, and the census found no model-affecting value
it failed to see.

### Schema invalidation

`mdstats.target-size.common-training-policy` → `v2`,
`mdstats.target-size.common-preparation` → `v2`,
`mdstats.target-size.mace-config` → `v2`.

Old evidence is invalidated by the **existing** currentness machinery, not by new
plumbing: the changed common-preparation digest changes `TargetSizeExecutionContext`, so
`initialize_target_size_screen(...)` refuses to reuse a differing screen window and
`validate_target_size_materialization(...)` refuses a materialization whose re-derived
config no longer matches. No global protocol version was bumped and no compatibility
layer was added.

---

## 3. Gate C — real pinned-MACE owner-boundary reproducer

`tests/test_mlff_target_size_p3_realized_mace_architecture.py` (6 tests, `slow`).
These cross the boundary the existing P3A4 fixtures miss: the candidate configuration is
written by the real materialization owner, the **production**
`MaceTargetSizeBoundaryTrainer` launches the real qualified `mdstats-mace-train` wrapper,
and pinned MACE runs through its own head preparation, dataset loading and
`configure_model(...)` to a durable TRAIN2 boundary.

| Test | Proves |
| --- | --- |
| `…builds_the_canonical_target_head_and_common_normalization` | real MACE logs `Using heads: ['target_head']`, never `['Default']`; never logs `Computing average number of neighbors`; logs the common value; the reconstruction's per-interaction `avg_num_neighbors` equals the common value; **reconstructed digest == persisted real-TRAIN2 digest**; the fitted value is not MACE's parser default |
| `…two_candidate_sizes_consume_one_common_normalization` | two real TRAIN2 runs at different `N` produce the **same** architecture digest and both carry `compute_avg_num_neighbors: False` and the common value |
| `…authenticated_eval2_accepts_the_real_train2_model` | production `run_target_size_direct_boundary_inference(...)` with **no architecture or provider override** authenticates the real model and completes a real CPU forward with finite energies/forces |
| `…default_head_train2_model_cannot_authenticate` | a `Default` head is rejected by the canonical architecture owner outright; a perturbed normalization changes the digest and is rejected before state can control inference |
| `…common_normalization_is_fitted_over_p_train_only` | deterministic for fixed membership + architecture identity; changing it changes the whole common-preparation digest |
| `…pre_repair_executable_shape_reproduces_the_reported_mismatch` | running real MACE with the **superseded** projection (no `--heads`, `compute_avg_num_neighbors=True`) still yields head `Default`, discards the configured normalization, and produces a digest that differs from the canonical reconstruction — i.e. the reported failure |

The assembled-CLI boundary is additionally covered by
`tests/test_mlff_target_size_p4d_runtime_cutover.py::test_p4d_req5_assembled_boundary_one_config_passes_the_real_mace_parser`,
which now asserts against the **pinned MACE parser's own namespace** that the real screen
emitted `heads == ['target_head']`, `compute_avg_num_neighbors is False`, and
`avg_num_neighbors` equal to the campaign's common-preparation value.

---

## 4. Anti-shortcut conformance

- `authenticate_train2_checkpoint_provider(...)` untouched; no tolerance added.
- EVAL2 architecture still comes only from the canonical candidate configuration.
- `avg_num_neighbors` is no longer computed per `T_N` anywhere.
- Executable config never leaves `compute_avg_num_neighbors=True`.
- `target_head` comes from the canonical dataset mapping, never from
  `mace_architecture['heads']`.
- P5 `target_head`/`pt_head` semantics untouched; `multiheads_finetuning` is refused for
  P3 and P5's own projection path is unchanged.
- No second common-normalization authority beside `TargetSizeCommonPreparation`.
- Old-generation state fails closed through the existing currentness machinery.
- The positive evidence is a real `run_train` model, not a model this repository built
  and then authenticated against itself.

---

## 5. Fixture reconciliation

The shared P1 test corpus placed its two atoms ~6.9 Å apart in a 10 Å cell — a corpus no
accepted MACE cutoff describes, which became visible only once a real neighbor
normalization was fitted. The second atom moved to fractional `(0.35, 0.35, 0.35)`, and
the P3 fixture architecture (`tests/…_p3a.fixture_mace_architecture`) uses `r_max = 9.0`
with a small model, so the fitted value (4.0) is distinguishable from MACE's parser
default (1.0). Test digests are computed rather than hard-coded, so no assertion's
meaning changed.
