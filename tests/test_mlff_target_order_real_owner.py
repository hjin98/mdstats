"""Real-owner D4 tests for the restored ``pi_train`` preparation chain.

These fixtures are intentionally small but execute the current owners.  The
downstream P2/P3 tests use a below-claim substitute because their claims do not
concern target-order construction; this module is the opposite boundary and
therefore opts out of that substitute.
"""

from __future__ import annotations

import errno
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import numpy as np
import pytest

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.target_order.artifact_store import (
    TargetOrderArtifactStoreError,
    close_memmap,
    publish_artifact_directory,
)
from mdstats.training_data.target_order.coverage_reference import (
    TargetCoveragePolicy,
    build_target_coverage_reference,
    score_target_subset_coverage,
)
from mdstats.training_data.target_order.engine import run_selection
from mdstats.training_data.target_order.feasibility import (
    build_target_coverage_feasibility_report,
    build_target_coverage_geometry,
)
from mdstats.training_data.target_order.kernels import preflight_native_workers
from mdstats.training_data.target_order.native import qualify_mvsel2_native_backend
from mdstats.training_data.target_order.obligations import (
    build_canonical_obligation_authority,
)
from mdstats.training_data.target_order.preparation import (
    prepare_target_training_order,
)
from mdstats.training_data.target_order.qualification import (
    build_membership_qualification,
)
from mdstats.training_data.target_order.repair import build_repair_plan
from mdstats.training_data.target_order.selector import (
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionPlan,
    TargetMultiViewSelectorPolicy,
    build_forward_state,
    materialized_rung,
    prefix_digest,
    reconstruct_forward_state,
    score_candidate,
    select_candidate,
)
from mdstats.training_data.target_order.sparse_index import (
    build_target_coverage_sparse_index,
    indexed_family_covered_mass,
    read_target_coverage_sparse_forward_view,
    sparse_forward_view,
    write_target_coverage_sparse_index,
)
from mdstats.training_data.target_order.state import (
    restore_latest_checkpoint,
    restore_selection_checkpoint,
    selection_identity,
    write_selection_checkpoint,
)
from tests.support.target_order_fixtures import build_selector_fixture


pytestmark = pytest.mark.real_target_order

_POLICY_NAME = "multi_view_mvsel2_repair2.v1"
_SIZES = (8, 16, 24)


def _file_bytes(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def _rss_peak_kib() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value // 1024 if sys.platform == "darwin" else value


def _open_fd_count() -> int:
    try:
        return len(tuple(Path("/proc/self/fd").iterdir()))
    except OSError:
        return -1


def _timed_stage(metrics: dict, root: Path, name: str, operation):
    started = time.perf_counter()
    value = operation()
    metrics[name] = {
        "wall_seconds": time.perf_counter() - started,
        "rss_peak_kib": _rss_peak_kib(),
        "artifact_bytes_after": _file_bytes(root),
    }
    return value


def _close_forward_view(forward) -> None:
    for array in (
        forward.candidate_obligation_offsets,
        forward.candidate_obligations,
        forward.candidate_correlation_unit_codes,
        *(item.candidate_offsets for item in forward.families),
        *(item.candidate_witnesses for item in forward.families),
    ):
        close_memmap(array)


def _build_assembled_campaign_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build a real CLI campaign whose structural substrate is feasible.

    The ordinary P4 fixture intentionally contains a changing structural
    trajectory and its small default ladder is not a feasible target-order
    ceiling.  This fixture keeps the real P1/P2/P3/store owners but supplies a
    controlled source trajectory with repeated structural frames, so the
    restored membership method can qualify three configured prefixes while
    leaving enough independent outer-monitor units for the existing P5 flow.
    """

    from tests import test_mlff_neutral_scientific_substrate as neutral
    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
    import tests._mlff_post_selection_fixture as p5
    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore

    training_root = tmp_path / "sources"
    source_directory = training_root / "run"
    source_directory.mkdir(parents=True)
    source_path = source_directory / "vasprun.xml"
    source_path.write_text(
        neutral._vasprun(
            ("Li", "O", "O"), n_frames=332, force_event_frame=None, tebeg=700
        ),
        encoding="utf-8",
    )
    tree = ET.parse(source_path)
    calculations = tree.getroot().findall("calculation")
    first_positions = calculations[0].find(
        "./structure/varray[@name='positions']"
    )
    assert first_positions is not None
    # Each frame is a rigid fractional translation of the first frame.  This
    # changes P1's exact geometry fingerprint (so correlation/duplicate split
    # constraints remain separable) while preserving the local structural
    # features consumed by the target-order provider.  Keep the label payload
    # fixed as well, so the small fixture exercises the structural and
    # canonical-unit obligations without requiring a large label ladder.
    # A compact 3.8 A cubic cell gives Li two distinct O neighbors at 1.9 A
    # (minimum image), so every frozen universal structural family (including
    # the neighbor-dependent pair-distance, chemical, angular and orientational
    # families) has valid reference elements; a dilute cell would correctly
    # fail closed on the required family catalog.
    for basis in tree.getroot().iter("varray"):
        if basis.get("name") == "basis":
            for axis, vector in enumerate(basis):
                vector.text = " ".join("3.8" if column == axis else "0" for column in range(3))
    base_positions = ((0.125, 0.125, 0.125), (0.625, 0.125, 0.125), (0.125, 0.625, 0.125))
    for frame_index, calculation in enumerate(calculations):
        positions = calculation.find("./structure/varray[@name='positions']")
        assert positions is not None
        for atom_index, target in enumerate(positions):
            coordinates = [
                value + (1.0 / 1000.0) * frame_index
                for value in base_positions[atom_index]
            ]
            target.text = " ".join(f"{value:.12g}" for value in coordinates)
        forces = calculation.find("./varray[@name='forces']")
        assert forces is not None
        fixed_forces = ((0.1, 0.0, 0.0), (-0.05, 0.0, 0.0), (-0.05, 0.0, 0.0))
        for atom_index, target in enumerate(forces):
            target.text = " ".join(f"{value:.12g}" for value in fixed_forces[atom_index])
        for energy in calculation.findall("./energy/i"):
            fixed_values = {
                "e_fr_energy": -10.0,
                "e_0_energy": -9.9,
                "e_wo_entrp": -9.95,
                "total": -9.5,
            }
            if energy.get("name") in fixed_values:
                energy.text = str(fixed_values[energy.get("name")])
        for energy in calculation.findall("./scstep/energy/i"):
            if energy.get("name") == "e_fr_energy":
                energy.text = "-10.0"
            elif energy.get("name") == "e_0_energy":
                energy.text = "-9.9"
    tree.write(source_path, encoding="utf-8", xml_declaration=True)

    manifest = mdstats.TrainingDataManifest(
        dataset_id="real-target-order-assembled",
        system_profile="generic",
        runs=(
            mdstats.TrainingDataRunSpec(
                run_id="run",
                vasprun="run/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            ),
        ),
    )
    sources = mdstats.build_training_data_source_catalog(
        manifest, base_directory=training_root
    )
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=training_root,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=neutral._data4_role_budget(),
    )

    workspace = tmp_path / "campaign"
    config = tmp_path / "campaign.toml"
    config.write_text(
        p4d._CONFIG.format(
            workspace=str(workspace), training_root=str(training_root)
        ).replace(
            "target_size_power_min = 1", "target_size_power_min = 2"
        ).replace(
            "target_size_power_max = 3", "target_size_power_max = 5"
        ).replace(
            "outer_monitor_minimum_independent_units = 1",
            "outer_monitor_minimum_independent_units = 72",
        )
        + p5.POST_SELECTION_CONFIG,
        encoding="utf-8",
    )
    cfg, paths = cli._load_config(config)
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.write_text(
        json.dumps(manifest.to_dict(), sort_keys=True), encoding="utf-8"
    )
    store = CampaignStore(paths.state_db)
    store.set_meta("approved_manifest_digest", manifest.content_digest)
    store.put_record(
        "acceleration_realization",
        mdstats.AccelerationRealizationRecord(
            requested_backend="e3nn",
            resolved_kernel_mode="e3nn",
            training_kernel_mode="e3nn",
            device="cpu",
            dtype="float32",
            foundation_inference_identity_digest=digest(
                {"fixture": "foundation"}
            ),
            mace_version="0.3.16",
            qualified=True,
        ),
    )
    store.put_record("source_catalog", sources)
    store.put_record("frame_catalog", frames)
    store.put_record("data4", data4)
    store.put_record("data5", {"schema": "data5-placeholder"})
    # The fixture has already run the lower-level owner checks; this stage
    # marker is refreshed after the target-order-only ladder edit above.
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    store.close()
    return config, workspace


def _all_duplicate_pairs(frames: int) -> tuple[tuple[int, int], ...]:
    return tuple((0, index) for index in range(1, frames))


def _products(
    root: Path,
    *,
    frames: int = 32,
    units: int = 4,
    conditions: int = 2,
    event_frames: tuple[int, ...] = (),
    duplicate_pairs: tuple[tuple[int, int], ...] | None = None,
    pair_rules: int = 1,
    performance_metrics: dict | None = None,
) -> SimpleNamespace:
    fixture = build_selector_fixture(
        frames=frames,
        units=units,
        conditions=conditions,
        event_frames=event_frames,
        duplicate_pairs=(
            _all_duplicate_pairs(frames)
            if duplicate_pairs is None
            else duplicate_pairs
        ),
        pair_rules=pair_rules,
    )
    metrics = {} if performance_metrics is None else performance_metrics

    def stage(name: str, operation):
        if performance_metrics is None:
            return operation()
        return _timed_stage(metrics, root, name, operation)

    reference = stage(
        "coverage_reference",
        lambda: build_target_coverage_reference(
            dataset_id=fixture.population.dataset_id,
            population=fixture.population,
            split=fixture.split,
            raw_feature_catalog=fixture.raw_features,
            structural_catalog=fixture.structural_catalog,
            policy=TargetCoveragePolicy(),
            query_workers=1,
            radius_block_size=8,
        ),
    )
    authority = stage(
        "canonical_obligations",
        lambda: build_canonical_obligation_authority(
            reference,
            fixture.population,
            training_order_policy=_POLICY_NAME,
            hard_support_obligations=(),
        ),
    )
    geometry = stage(
        "shared_feas1_neighbor1",
        lambda: build_target_coverage_geometry(
            reference,
            build_directory=root / "geometry-build",
            global_workers=1,
            query_workers=1,
            query_block_size=8,
        ),
    )
    feasibility = stage(
        "feasibility",
        lambda: build_target_coverage_feasibility_report(
            reference,
            geometry,
            authority,
            configured_ceiling=frames,
        ),
    )
    index = stage(
        "mvidx_inversion",
        lambda: build_target_coverage_sparse_index(
            reference,
            geometry.neighborhoods,
            authority,
            workers=1,
            out_of_core_directory=root / "mvidx-build",
        ),
    )
    return SimpleNamespace(
        fixture=fixture,
        reference=reference,
        authority=authority,
        geometry=geometry,
        feasibility=feasibility,
        index=index,
        forward=sparse_forward_view(index),
        performance_metrics=metrics,
    )


@pytest.fixture(scope="module")
def feasible_products(tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    return _products(tmp_path_factory.mktemp("target-order-products"))


@pytest.fixture(scope="module")
def repair_products(tmp_path_factory: pytest.TempPathFactory) -> SimpleNamespace:
    # The first and second halves are separate duplicate clusters.  The
    # hand-built selector order fills the first cluster first so REPAIR2 has a
    # genuine positive-coverage replacement frontier.
    duplicates = tuple((0, index) for index in range(1, 16)) + tuple(
        (16, index) for index in range(17, 32)
    )
    return _products(
        tmp_path_factory.mktemp("target-order-repair"),
        units=1,
        conditions=1,
        duplicate_pairs=duplicates,
    )


def _run_bounded_selection(products: SimpleNamespace, *, workers: int):
    return run_selection(
        products.reference,
        products.forward,
        TargetMultiViewSelectorPolicy(),
        stop=_SIZES[-1],
        rung_sizes=_SIZES,
        record_entries_through=_SIZES[-1],
        workers=workers,
    )


def test_real_owner_native_and_serial_ranks_match_on_wide_csr_rows(
    feasible_products: SimpleNamespace,
) -> None:
    products = feasible_products
    assert qualify_mvsel2_native_backend().qualified
    assert max(
        len(family.candidate_witness_indices(candidate))
        for family in products.forward.families
        for candidate in range(products.forward.candidate_count)
    ) >= 8

    serial = _run_bounded_selection(products, workers=1)
    native = _run_bounded_selection(products, workers=2)

    assert [item.frame_uid for item in serial.entries] == [
        item.frame_uid for item in native.entries
    ]
    assert [item.to_dict() for item in serial.entries] == [
        item.to_dict() for item in native.entries
    ]
    assert [item.to_dict() for item in serial.rungs] == [
        item.to_dict() for item in native.rungs
    ]
    assert serial.state.selected_order == native.state.selected_order


def test_real_owner_shared_geometry_and_mvidx_match_direct_coverage(
    feasible_products: SimpleNamespace,
) -> None:
    products = feasible_products
    assert (
        products.index.neighborhood_digest
        == products.geometry.neighborhoods.content_digest
    )
    assert products.feasibility.geometry_digest == products.geometry.content_digest
    selected = _run_bounded_selection(products, workers=1)
    uids = [item.frame_uid for item in selected.entries]

    for size in _SIZES:
        direct = score_target_subset_coverage(
            products.reference, uids[:size], query_workers=1
        )
        by_family = {item.family_id: item for item in direct.family_reports}
        selected_indices = [products.reference.frame_index(uid) for uid in uids[:size]]
        for family in products.forward.families:
            indexed = indexed_family_covered_mass(
                family,
                products.reference.family(family.family_id).weights,
                selected_indices,
            )
            assert indexed == pytest.approx(
                by_family[family.family_id].covered_reference_mass,
                rel=0.0,
                abs=5.0e-12,
            )


def test_real_owner_mvqual_is_independent_and_canonical(
    feasible_products: SimpleNamespace,
) -> None:
    products = feasible_products
    selected = _run_bounded_selection(products, workers=1)
    prefixes = {
        size: tuple(item.frame_uid for item in selected.entries[:size])
        for size in _SIZES
    }
    serial = build_membership_qualification(
        products.reference,
        products.authority,
        products.forward,
        prefixes,
        workers=1,
    )
    parallel = build_membership_qualification(
        products.reference,
        products.authority,
        products.forward,
        prefixes,
        workers=2,
    )
    assert serial.to_dict() == parallel.to_dict()
    assert serial.qualified_sizes == _SIZES
    for rung in serial.rungs:
        assert rung.minimum_family_coverage == min(
            item.covered_reference_mass for item in rung.family_reports
        )
        assert rung.coverage_passed == all(
            item.coverage_passed for item in rung.family_reports
        )
        assert rung.extent_passed == all(
            item.extent_passed for item in rung.family_reports
        )
        assert rung.qualified == (
            rung.coverage_passed
            and rung.extent_passed
            and not rung.unsatisfied_obligation_ids
        )


def _manual_selection_plan(
    products: SimpleNamespace,
    order: tuple[int, ...] | None = None,
    sizes: tuple[int, ...] = (4, 8),
) -> TargetMultiViewSelectionPlan:
    reference = products.reference
    forward = products.forward
    if order is None:
        # The first cluster is deliberately redundant at the first shell; the
        # second cluster remains in the future as a positive-coverage replacement.
        order = tuple(range(forward.candidate_count))
    state = build_forward_state(reference, forward, validate=False)
    entries: list[TargetMultiViewSelectionEntry] = []
    rungs = []
    for rank, candidate in enumerate(order[: sizes[-1]]):
        score = score_candidate(candidate, forward, state)
        entries.append(
            TargetMultiViewSelectionEntry(
                rank=rank,
                frame_uid=reference.frame_uids[candidate],
                phase="hard_coverage",
                primary_reason="repair-fixture-order",
                bottleneck_family_id=forward.families[0].family_id,
                hard_obligation_gain=score.hard_obligation_gain,
                bottleneck_coverage_gain=score.family_coverage_gains[0],
                total_coverage_gain=score.total_coverage_gain,
                representative_gain=score.representative_gain,
                normalized_diversity=score.sparse_diversity,
                correlation_unit_code=int(
                    forward.candidate_correlation_unit_codes[candidate]
                ),
            )
        )
        select_candidate(candidate, forward, state, score=score)
        if rank + 1 in sizes:
            rungs.append(
                materialized_rung(
                    reference,
                    forward,
                    state,
                    entries,
                    target_size=rank + 1,
                    previous_size=0 if rank + 1 == sizes[0] else sizes[sizes.index(rank + 1) - 1],
                )
            )
    return TargetMultiViewSelectionPlan(
        target_coverage_reference_digest=reference.content_digest,
        mvidx_content_digest=forward.mvidx_content_digest,
        policy=TargetMultiViewSelectorPolicy(),
        configured_sizes=sizes,
        entries=tuple(entries[: sizes[-1]]),
        rungs=tuple(rungs),
        phase_a_completed_at=None,
    )


def test_real_owner_repair_swaps_and_reconstructs_cold_continuation(
    repair_products: SimpleNamespace,
) -> None:
    products = repair_products
    selection = _manual_selection_plan(products)
    serial = build_repair_plan(
        products.reference, products.forward, selection, workers=1
    )
    parallel = build_repair_plan(
        products.reference, products.forward, selection, workers=2
    )
    assert serial.total_swaps > 0
    assert serial.to_dict() == parallel.to_dict()

    for position, (base, repaired) in enumerate(
        zip(selection.rungs, serial.rungs, strict=True)
    ):
        assert repaired.frame_uids_digest == prefix_digest(
            serial.repaired_prefix[: repaired.target_size]
        )
        base_coverage = dict(base.family_coverage)
        assert all(
            value + 1.0e-14 >= base_coverage[family]
            for family, value in repaired.family_coverage
        )
        for swap in repaired.swaps:
            assert repaired.active_shell_start <= swap.rank < repaired.target_size
            assert swap.objective_after[0] <= swap.objective_before[0]
        if position:
            previous_size = selection.rungs[position - 1].target_size
            assert serial.rungs[position - 1].frame_uids_digest == prefix_digest(
                serial.repaired_prefix[:previous_size]
            )

    repaired_indices = [
        products.reference.frame_index(uid)
        for uid in serial.repaired_prefix[: selection.configured_sizes[-1]]
    ]
    cold = mdstats.training_data.target_order.selector.reconstruct_forward_state(
        products.reference,
        products.forward,
        repaired_indices,
    )
    assert cold.selected_order == repaired_indices
    final_rung = serial.rungs[-1]
    cold_masses = {
        item.family_id: item.coverage_mass for item in cold.family_states
    }
    for family, value in final_rung.family_coverage:
        assert cold_masses[family] == pytest.approx(value, abs=5.0e-13)


def test_real_owner_suffix_and_checkpoint_resume_beyond_nmax(
    feasible_products: SimpleNamespace, tmp_path: Path
) -> None:
    products = feasible_products
    selector_policy = TargetMultiViewSelectorPolicy()
    identity = selection_identity(
        reference_digest=products.reference.content_digest,
        mvidx_digest=products.forward.mvidx_content_digest,
        selector_policy_digest=selector_policy.policy_digest,
        configured_sizes=_SIZES,
    )
    checkpoint_root = tmp_path / "checkpoints"
    prefix_run = run_selection(
        products.reference,
        products.forward,
        selector_policy,
        stop=_SIZES[-1],
        rung_sizes=_SIZES,
        record_entries_through=_SIZES[-1],
        workers=1,
        checkpoint=lambda state, entries, rungs, phase: write_selection_checkpoint(
            checkpoint_root,
            identity=identity,
            state=state,
            entries=entries,
            rungs=rungs,
            phase_a_completed_at=phase,
        ),
    )
    restored = restore_latest_checkpoint(
        checkpoint_root,
        products.reference,
        products.forward,
        expected_identity=identity,
        maximum_selected=_SIZES[-1],
    )
    assert restored is not None
    assert restored.state.selected_count == _SIZES[-1]
    resumed = run_selection(
        products.reference,
        products.forward,
        selector_policy,
        stop=products.forward.candidate_count,
        state=restored.state,
        entries=restored.entries,
        rungs=restored.rungs,
        phase_a_completed_at=restored.phase_a_completed_at,
        record_entries_through=_SIZES[-1],
        workers=1,
    )
    cold = run_selection(
        products.reference,
        products.forward,
        selector_policy,
        stop=products.forward.candidate_count,
        rung_sizes=_SIZES,
        record_entries_through=_SIZES[-1],
        workers=1,
    )
    assert prefix_run.state.selected_count == _SIZES[-1]
    assert resumed.state.selected_order == cold.state.selected_order
    assert [item.to_dict() for item in resumed.entries] == [
        item.to_dict() for item in cold.entries
    ]
    assert [item.to_dict() for item in resumed.rungs] == [
        item.to_dict() for item in cold.rungs
    ]


def test_real_owner_stale_and_corrupt_checkpoints_are_rejected(
    feasible_products: SimpleNamespace, tmp_path: Path
) -> None:
    products = feasible_products
    policy = TargetMultiViewSelectorPolicy()
    identity = selection_identity(
        reference_digest=products.reference.content_digest,
        mvidx_digest=products.forward.mvidx_content_digest,
        selector_policy_digest=policy.policy_digest,
        configured_sizes=_SIZES,
    )
    run = run_selection(
        products.reference,
        products.forward,
        policy,
        stop=8,
        rung_sizes=(8,),
        record_entries_through=8,
        workers=1,
    )

    stale_root = tmp_path / "stale"
    stale = write_selection_checkpoint(
        stale_root,
        identity=digest({"foreign": identity}),
        state=run.state,
        entries=run.entries,
        rungs=run.rungs,
        phase_a_completed_at=run.phase_a_completed_at,
    )
    with pytest.raises(TargetOrderArtifactStoreError, match="identity"):
        restore_selection_checkpoint(
            stale.directory,
            products.reference,
            products.forward,
            expected_identity=identity,
        )
    assert restore_latest_checkpoint(
        stale_root,
        products.reference,
        products.forward,
        expected_identity=identity,
    ) is None
    assert not stale.directory.exists()

    corrupt_root = tmp_path / "corrupt"
    corrupt = write_selection_checkpoint(
        corrupt_root,
        identity=identity,
        state=run.state,
        entries=run.entries,
        rungs=run.rungs,
        phase_a_completed_at=run.phase_a_completed_at,
    )
    manifest_path = corrupt.directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["identity"] = digest({"corrupt": identity})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert restore_latest_checkpoint(
        corrupt_root,
        products.reference,
        products.forward,
        expected_identity=identity,
    ) is None
    assert not corrupt.directory.exists()


def test_real_owner_many_family_forward_restore_maps_constant_fds(
    tmp_path: Path,
) -> None:
    products = _products(
        tmp_path / "many-families",
        pair_rules=40,
    )
    destination = tmp_path / "many-families" / "published-mvidx"
    write_target_coverage_sparse_index(destination, products.index)
    assert len(products.index.families) >= 64

    def mapped_fds() -> set[str]:
        result: set[str] = set()
        for descriptor in Path("/proc/self/fd").iterdir():
            try:
                target = os.path.realpath(os.readlink(descriptor))
            except OSError:
                continue
            if str(destination.resolve()) in target:
                result.add(target)
        return result

    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard < 32:
        pytest.fail("RLIMIT_NOFILE hard limit is too small for the bounded restore test")
    bounded = min(64, hard)
    changed = soft > bounded
    if changed:
        resource.setrlimit(resource.RLIMIT_NOFILE, (bounded, hard))
    forward = None
    try:
        before = len(mapped_fds())
        forward = read_target_coverage_sparse_forward_view(destination)
        after = len(mapped_fds())
        assert len(forward.families) == len(products.index.families)
        assert after - before <= 8
    finally:
        if changed:
            resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
        if forward is not None:
            for array in (
                forward.candidate_obligation_offsets,
                forward.candidate_obligations,
                forward.candidate_correlation_unit_codes,
                *(item.candidate_offsets for item in forward.families),
                *(item.candidate_witnesses for item in forward.families),
            ):
                close_memmap(array)
            del forward
        gc.collect()


def test_real_owner_write_failure_leaves_no_partial_accepted_artifact(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "selector-artifact"

    def fail(directory: Path):
        (directory / "partial.bin").write_bytes(b"partial")
        raise OSError(errno.ENOSPC, "forced target-order ENOSPC")

    with pytest.raises(OSError, match="ENOSPC"):
        publish_artifact_directory(
            destination,
            schema="test.target-order-artifact.v1",
            write=fail,
            verify_existing=lambda _path, _manifest: None,
        )
    assert not destination.exists()
    assert not tuple(destination.parent.glob(f".{destination.name}-attempt-*"))


def test_real_owner_native_preflight_reports_real_mvidx_rows(
    feasible_products: SimpleNamespace,
) -> None:
    state = build_forward_state(
        feasible_products.reference,
        feasible_products.forward,
    )
    preflight = preflight_native_workers(
        feasible_products.forward,
        state,
        max_workers=2,
        sample_size=16,
    )
    assert preflight.forward_edges > 0 or preflight.reason is not None


def test_real_owner_performance_checkpoint(tmp_path: Path) -> None:
    """Record bounded D4 stage, restart, and native execution evidence."""

    root = tmp_path / "performance"
    metrics: dict = {}
    products = _products(root, performance_metrics=metrics)
    assert products.index.neighborhood_digest == products.geometry.neighborhoods.content_digest

    preflight_started = time.perf_counter()
    preflight = preflight_native_workers(
        products.forward,
        build_forward_state(products.reference, products.forward),
        max_workers=2,
        sample_size=16,
    )
    metrics["native_preflight"] = {
        "wall_seconds": time.perf_counter() - preflight_started,
        "requested_workers": preflight.requested_workers,
        "effective_workers": preflight.effective_workers,
        "sample_candidates": preflight.sample_candidates,
        "forward_edges": preflight.forward_edges,
        "scaling_passed": preflight.scaling_passed,
        "reason": preflight.reason,
        "meters": [
            {
                "workers": meter.workers,
                "elapsed_seconds": meter.elapsed_seconds,
                "forward_edges": meter.forward_edges,
                "speedup_vs_one": meter.speedup_vs_one,
            }
            for meter in preflight.meters
        ],
    }

    published_root = root / "published-mvidx"
    adoption_started = time.perf_counter()
    published = write_target_coverage_sparse_index(published_root, products.index)
    metrics["mvidx_adoption"] = {
        "wall_seconds": time.perf_counter() - adoption_started,
        "artifact_bytes": _file_bytes(published.directory),
    }
    before_fds = _open_fd_count()
    restore_started = time.perf_counter()
    restored_forward = read_target_coverage_sparse_forward_view(published_root)
    restore_elapsed = time.perf_counter() - restore_started
    after_fds = _open_fd_count()
    try:
        assert restored_forward.mvidx_content_digest == products.index.content_digest
        assert len(restored_forward.families) == len(products.forward.families)
    finally:
        _close_forward_view(restored_forward)
        del restored_forward
        gc.collect()
    metrics["mvidx_forward_reload"] = {
        "wall_seconds": restore_elapsed,
        "mapped_fd_delta": after_fds - before_fds if before_fds >= 0 and after_fds >= 0 else None,
        "artifact_bytes": _file_bytes(published_root),
    }

    policy = TargetMultiViewSelectorPolicy()
    identity = selection_identity(
        reference_digest=products.reference.content_digest,
        mvidx_digest=products.forward.mvidx_content_digest,
        selector_policy_digest=policy.policy_digest,
        configured_sizes=_SIZES,
    )
    configured = _timed_stage(
        metrics,
        root,
        "mvsel2_configured_prefix",
        lambda: run_selection(
            products.reference,
            products.forward,
            policy,
            stop=_SIZES[-1],
            rung_sizes=_SIZES,
            record_entries_through=_SIZES[-1],
            workers=1,
        ),
    )
    checkpoint_root = root / "checkpoints"
    checkpoint_stats = {"writes": 0, "write_seconds": 0.0, "bytes": 0}

    def checkpoint(state, entries, rungs, phase):
        started = time.perf_counter()
        artifact = write_selection_checkpoint(
            checkpoint_root,
            identity=identity,
            state=state,
            entries=entries,
            rungs=rungs,
            phase_a_completed_at=phase,
        )
        checkpoint_stats["writes"] += 1
        checkpoint_stats["write_seconds"] += time.perf_counter() - started
        checkpoint_stats["bytes"] += _file_bytes(artifact.directory)

    checkpointed = _timed_stage(
        metrics,
        root,
        "mvsel2_checkpointed_prefix",
        lambda: run_selection(
            products.reference,
            products.forward,
            policy,
            stop=_SIZES[-1],
            rung_sizes=_SIZES,
            record_entries_through=_SIZES[-1],
            workers=1,
            checkpoint=checkpoint,
        ),
    )
    assert configured.state.selected_order == checkpointed.state.selected_order
    restore_started = time.perf_counter()
    restored = restore_latest_checkpoint(
        checkpoint_root,
        products.reference,
        products.forward,
        expected_identity=identity,
        maximum_selected=_SIZES[-1],
    )
    checkpoint_read_seconds = time.perf_counter() - restore_started
    assert restored is not None
    metrics["checkpoint_restore"] = {
        "wall_seconds": checkpoint_read_seconds,
        "selected_count": restored.state.selected_count,
    }
    resumed = _timed_stage(
        metrics,
        root,
        "mvsel2_suffix_resume",
        lambda: run_selection(
            products.reference,
            products.forward,
            policy,
            stop=products.forward.candidate_count,
            state=restored.state,
            entries=restored.entries,
            rungs=restored.rungs,
            phase_a_completed_at=restored.phase_a_completed_at,
            record_entries_through=_SIZES[-1],
            workers=1,
        ),
    )
    cold = _timed_stage(
        metrics,
        root,
        "mvsel2_complete_order_cold",
        lambda: run_selection(
            products.reference,
            products.forward,
            policy,
            stop=products.forward.candidate_count,
            rung_sizes=_SIZES,
            record_entries_through=_SIZES[-1],
            workers=1,
        ),
    )
    assert resumed.state.selected_order == cold.state.selected_order
    assert [item.to_dict() for item in resumed.entries] == [item.to_dict() for item in cold.entries]
    assert [item.to_dict() for item in resumed.rungs] == [item.to_dict() for item in cold.rungs]

    repair_duplicates = tuple((0, index) for index in range(1, 16)) + tuple(
        (16, index) for index in range(17, 32)
    )
    repair_products = _products(
        root / "repair",
        units=1,
        conditions=1,
        duplicate_pairs=repair_duplicates,
    )
    repair_selection = _manual_selection_plan(repair_products)
    repair_started = time.perf_counter()
    repair = build_repair_plan(
        repair_products.reference,
        repair_products.forward,
        repair_selection,
        workers=1,
    )
    metrics["repair2"] = {
        "wall_seconds": time.perf_counter() - repair_started,
        "total_swaps": repair.total_swaps,
        "configured_sizes": list(repair_selection.configured_sizes),
    }
    assert repair.total_swaps > 0
    repaired_indices = [
        repair_products.reference.frame_index(uid)
        for uid in repair.repaired_prefix[: repair_selection.configured_sizes[-1]]
    ]
    reconstruction = _timed_stage(
        metrics,
        root,
        "post_final_repair_reconstruction",
        lambda: reconstruct_forward_state(
            repair_products.reference,
            repair_products.forward,
            repaired_indices,
        ),
    )
    assert reconstruction.selected_order == repaired_indices

    phase_b_ranks = cold.telemetry.ranks - cold.telemetry.phase_a_ranks
    report = {
        "p_train_frames": products.reference.candidate_count,
        "family_count": len(products.index.families),
        "witness_counts": [item.witness_count for item in products.index.families],
        "edge_counts": [item.edge_count for item in products.index.families],
        "configured_sizes": list(_SIZES),
        "mvidx_scratch_bytes": _file_bytes(root / "mvidx-build"),
        "published_mvidx_bytes": _file_bytes(published_root),
        "checkpoint": checkpoint_stats,
        "checkpoint_bytes": _file_bytes(checkpoint_root),
        "peak_process_rss_kib": _rss_peak_kib(),
        "open_fd_final": _open_fd_count(),
        "selection": {
            "configured_prefix": configured.telemetry.to_dict(),
            "checkpointed_prefix": checkpointed.telemetry.to_dict(),
            "suffix_resume": resumed.telemetry.to_dict(),
            "complete_order_cold": cold.telemetry.to_dict(),
            "phase_a_to_b_rank": cold.phase_a_completed_at,
            "phase_b_refreshes_per_rank": (
                cold.telemetry.rescoring_count / phase_b_ranks if phase_b_ranks else 0.0
            ),
        },
        "stages": metrics,
    }
    print("PERF_CHECKPOINT " + json.dumps(report, sort_keys=True))


def test_real_owner_assembled_campaign_uses_prepared_order_through_production(
    tmp_path: Path,
) -> None:
    """Exercise the current prepared generation and the downstream lifecycle."""

    import tests._mlff_post_selection_fixture as p5
    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

    from mdstats.training_data import _campaign_cli_core as cli
    from mdstats.training_data._campaign_cli_core import CampaignStore
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        resolve_current_cv_acceptance,
        resolve_current_cv_plan,
        resolve_current_final_production_completion,
        resolve_current_final_production_plan,
    )
    from mdstats.training_data.campaign_prepared_generation import (
        PREPARED_GENERATION_SCHEMA,
        PreparedGenerationMissingError,
        load_prepared_generation_components,
        prepared_generation_root,
        read_prepared_generation_manifest,
    )
    from mdstats.training_data.campaign_target_size_runtime import (
        load_prepared_target_size_definition,
        load_prepared_target_size_generation,
    )
    from mdstats.training_data.campaign_target_size_selection import (
        SELECTION_SOURCE_MANUAL,
    )
    from mdstats.training_data.campaign_target_size_state import (
        TargetSizeLifecycle,
        TargetSizeRegime,
        load_target_size_campaign_revision,
    )

    config, workspace = _build_assembled_campaign_fixture(tmp_path)
    state_db = workspace / ".mdstats" / "campaign.sqlite3"
    assert cli.main(["--config", str(config), "prepare"]) == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        assert revision.state.lifecycle is TargetSizeLifecycle.AUTHORITIES_BOUND
        assert revision.state.generation == 1
        manifest = read_prepared_generation_manifest(
            paths, revision.state.prepared_manifest_digest
        )
        assert manifest.to_dict()["schema"] == PREPARED_GENERATION_SCHEMA
        assert manifest.component_digests["target_order"]
        components = load_prepared_generation_components(paths, manifest)
        target_order = components["target_order"]
        aggregate = components["aggregate"]
        assert target_order.configured_sizes == (4, 8, 16, 32)
        assert aggregate.definition.qualified_candidate_sizes == (8, 16, 32)
        assert (
            aggregate.definition.training_order.selection_evidence_digest
            == target_order.content_digest
        )
        loaded = load_prepared_target_size_generation(cfg, paths, store, revision)
        assert loaded.target_order.content_digest == target_order.content_digest

        # A v1 manifest is stale content, not a second currentness path.  It is
        # intentionally unreachable from CampaignStore and must be rejected by
        # the prepared-generation owner before any component is interpreted.
        stale_bytes = (
            json.dumps(
                {"schema": "mdstats.mlff-prepared-generation.v1"},
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        stale_digest = hashlib.sha256(stale_bytes).hexdigest()
        stale_path = (
            prepared_generation_root(paths)
            / "generations"
            / f"{stale_digest}.json"
        )
        stale_path.parent.mkdir(parents=True, exist_ok=True)
        stale_path.write_bytes(stale_bytes)
        with pytest.raises(PreparedGenerationMissingError, match="stale"):
            read_prepared_generation_manifest(paths, stale_digest)
    finally:
        store.close()

    repository = Path(__file__).resolve().parents[1]
    child_environment = os.environ.copy()
    child_environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(repository), child_environment.get("PYTHONPATH", "")) if item
    )

    reload_probe = r'''
import sys
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_runtime import load_prepared_target_size_generation
from mdstats.training_data.campaign_target_size_state import load_target_size_campaign_revision

cfg, paths = cli._load_config(sys.argv[1], ensure=False)
store = CampaignStore(paths.state_db, create=False)
try:
    revision = load_target_size_campaign_revision(store)
    authorities = load_prepared_target_size_generation(cfg, paths, store, revision)
    assert authorities.target_order.content_digest
    assert authorities.aggregate.definition.qualified_candidate_sizes == (8, 16, 32)
finally:
    store.close()
print("fresh prepared-generation reload passed")
'''
    reloaded = subprocess.run(
        [sys.executable, "-c", reload_probe, str(config)],
        check=False,
        cwd=tmp_path,
        env=child_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert reloaded.returncode == 0, reloaded.stdout

    manual_probe = r'''
import sys
from mdstats.training_data import _campaign_cli_core as cli

assert cli.main(["--config", sys.argv[1], "select-target-size", "8"]) == 0
assert "mdstats.training_data.target_order.selector" not in sys.modules
assert "mdstats._mvsel2_native" not in sys.modules
print("manual selection definition path passed")
'''
    manual = subprocess.run(
        [sys.executable, "-c", manual_probe, str(config)],
        check=False,
        cwd=tmp_path,
        env=child_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert manual.returncode == 0, manual.stdout

    store = CampaignStore(state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        assert len(revision.state.provisional_entries) == 1
        assert revision.state.provisional_entries[0].n_provisional == 8
        assert revision.state.provisional_entries[0].selection_source == SELECTION_SOURCE_MANUAL
        assert revision.state.frozen_entries is None
        # The same owner is used by the explicit CLI, and the returned object
        # is definition-only: no target-order rebuild occurred.
        definition = load_prepared_target_size_definition(cfg, paths, store, revision)
        assert definition.training_order.content_digest == revision.state.provisional_entries[0].training_order_digest
    finally:
        store.close()

    screen = p5._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            "--auto",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    assert screen.rungs and screen.inferences

    cv = p5.PostSelectionHarness()
    assert p5.run_cross_validate(config, cv) == 0
    production = p5.PostSelectionHarness()
    assert p5.run_train_production(config, production) == 0
    assert cv.runs and cv.evaluations
    assert production.runs and production.evaluations

    store = CampaignStore(state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.generation == 1
        assert revision.state.provisional_entries == ()
        assert len(revision.state.frozen_entries) == 1
        contexts = build_post_selection_contexts(cfg, paths, store)
        assert len(contexts) == 1
        context = contexts[0]
        cv_plan = resolve_current_cv_plan(context)
        cv_acceptance = resolve_current_cv_acceptance(context)
        final_plan = resolve_current_final_production_plan(context)
        completion = resolve_current_final_production_completion(context)
        assert cv_plan is not None
        assert cv_acceptance is not None and cv_acceptance.accepted
        assert final_plan is not None and final_plan.n_selected == 8
        assert completion is not None
        assert completion.plan.content_digest == final_plan.content_digest
    finally:
        store.close()


def test_installed_package_native_equivalence(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(repository),
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheelhouse),
        ],
        check=True,
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    wheel = next(wheelhouse.glob("mdstats-*.whl"))
    site = tmp_path / "installed"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(site),
            str(wheel),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    probe = """
import numpy as np
from mdstats.training_data.target_order.native import qualify_mvsel2_native_backend, score_family_candidate_batch
status = qualify_mvsel2_native_backend()
assert status.available and status.qualified and status.openmp, status
offsets = np.asarray([0, 8, 17], dtype=np.uint64)
witnesses = np.asarray(list(range(8)) + list(range(3, 12)), dtype=np.uint32)
terms = np.linspace(0.125, 1.75, 17, dtype=np.float64)
candidates = np.asarray([0, 1], dtype=np.uint32)
actual, edges = score_family_candidate_batch(offsets, witnesses, terms, candidates, workers=2)
expected = np.asarray([np.sum(terms[witnesses[int(offsets[i]):int(offsets[i + 1])]], dtype=np.float64) for i in candidates], dtype=np.float64)
assert edges == len(witnesses)
assert np.array_equal(actual.view(np.uint64), expected.view(np.uint64))
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONPATH"] = str(site)
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        check=False,
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout


def test_real_owner_prepare_build_reuse_crash_resume_and_scratch_cleanup(
    tmp_path: Path,
) -> None:
    fixture = build_selector_fixture(
        frames=32,
        units=4,
        conditions=2,
        event_frames=(),
        duplicate_pairs=_all_duplicate_pairs(32),
    )
    prepared_root = tmp_path / "prepared"
    progress: list[str] = []
    calls = {"structural": 0}

    def structural_catalog():
        calls["structural"] += 1
        return fixture.structural_catalog

    def crash(message: str) -> None:
        progress.append(message)
        if message.startswith("status=selecting; progress=8/24"):
            raise RuntimeError("forced prepare interruption after checkpoint")

    with pytest.raises(RuntimeError, match="forced prepare interruption"):
        prepare_target_training_order(
            prepared_root=prepared_root,
            population=fixture.population,
            split=fixture.split,
            training_order_policy=_POLICY_NAME,
            hard_support_obligations=(),
            configured_sizes=_SIZES,
            raw_feature_catalog=fixture.raw_features,
            structural_input_identity="real-owner-prepare-fixture.v1",
            structural_catalog_factory=structural_catalog,
            workers=1,
            progress_callback=crash,
        )
    attempts = prepared_root / "target-order" / "attempts"
    assert attempts.is_dir()
    assert not tuple(attempts.iterdir())
    assert calls["structural"] == 1
    assert any(
        item.startswith("status=selecting; progress=8/24") for item in progress
    )

    resumed_progress: list[str] = []
    build = prepare_target_training_order(
        prepared_root=prepared_root,
        population=fixture.population,
        split=fixture.split,
        training_order_policy=_POLICY_NAME,
        hard_support_obligations=(),
        configured_sizes=_SIZES,
        raw_feature_catalog=fixture.raw_features,
        structural_input_identity="real-owner-prepare-fixture.v1",
        structural_catalog_factory=structural_catalog,
        workers=1,
        progress_callback=resumed_progress.append,
    )
    assert len(build.frame_uids) == 32
    assert build.qualification.qualified_sizes == _SIZES
    assert calls["structural"] == 1
    assert any("resume=8" in item for item in resumed_progress)
    assert not tuple(attempts.iterdir())

    reused = prepare_target_training_order(
        prepared_root=prepared_root,
        population=fixture.population,
        split=fixture.split,
        training_order_policy=_POLICY_NAME,
        hard_support_obligations=(),
        configured_sizes=_SIZES,
        raw_feature_catalog=fixture.raw_features,
        structural_input_identity="real-owner-prepare-fixture.v1",
        structural_catalog_factory=structural_catalog,
        workers=1,
    )
    assert reused.reused
    assert reused.preparation.content_digest == build.preparation.content_digest
    assert calls["structural"] == 1


# --- Revision 11 falsification ------------------------------------------------


def _prepare(prepared_root: Path, fixture, *, sizes=_SIZES, **kwargs):
    kwargs.setdefault("structural_catalog_factory", lambda: fixture.structural_catalog)
    return prepare_target_training_order(
        prepared_root=prepared_root,
        population=fixture.population,
        split=fixture.split,
        training_order_policy=_POLICY_NAME,
        hard_support_obligations=(),
        configured_sizes=sizes,
        raw_feature_catalog=fixture.raw_features,
        structural_input_identity="real-owner-prepare-fixture.v1",
        workers=1,
        **kwargs,
    )


def _prepare_fixture():
    return build_selector_fixture(
        frames=32,
        units=4,
        conditions=2,
        event_frames=(),
        duplicate_pairs=_all_duplicate_pairs(32),
    )


def _tree_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_real_owner_repair2_zero_new_coverage_swap_strictly_improves_representative_utility(
    repair_products: SimpleNamespace,
) -> None:
    """D2 9.2/9.3: a zero-new-coverage replacement is admitted by strict J alone."""

    products = repair_products
    # Shell 1 = one member of each duplicate cluster -> complete coverage.  Shell
    # 2 piles four more members onto cluster A, so no available frame adds new
    # coverage while moving a member to cluster B strictly raises U_rep.
    uneven = _manual_selection_plan(products, order=(0, 16, 1, 2, 3, 4), sizes=(2, 6))
    plans = [
        build_repair_plan(products.reference, products.forward, uneven, workers=workers)
        for workers in (1, 2, 4, 16)
    ]
    # Execution width and native batch boundaries never move the repair trace.
    assert all(plan.to_dict() == plans[0].to_dict() for plan in plans[1:])
    plan = plans[0]
    assert plan.total_swaps > 0
    cluster_b = {products.reference.frame_uids[index] for index in range(16, 32)}
    for rung in plan.rungs:
        for swap in rung.swaps:
            before, after = swap.objective_before, swap.objective_after
            assert before[0] == after[0] == 0
            assert after[1] == pytest.approx(before[1], rel=0.0, abs=1.0e-14)
            assert after[2] == pytest.approx(before[2], rel=0.0, abs=1.0e-14)
            assert after[3] > before[3]
            assert swap.removed_unique_coverage == 0.0
            assert swap.replacement_frame_uid in cluster_b
    base = dict(uneven.rungs[-1].family_coverage)
    assert all(
        value == pytest.approx(base[family], rel=0.0, abs=1.0e-14)
        for family, value in plan.rungs[-1].family_coverage
    )

    # Control: the shell is already balanced across clusters, so no replacement
    # strictly improves J and REPAIR2 must make no swap.
    even = _manual_selection_plan(products, order=(0, 16, 1, 17), sizes=(2, 4))
    control = build_repair_plan(products.reference, products.forward, even, workers=2)
    assert control.total_swaps == 0
    assert control.to_dict() == build_repair_plan(
        products.reference, products.forward, even, workers=1
    ).to_dict()


def test_real_owner_repair2_v1_build_identity_is_not_current(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from mdstats.training_data.target_order import preparation
    from mdstats.training_data.target_order.repair import (
        REPAIR2_VERSION,
        TargetMultiViewRepairPolicy,
    )
    from mdstats.training_data._common import TrainingDataInputError

    assert REPAIR2_VERSION == "mdstats.target-order.repair2.configured-shell.v2"
    current_policy = TargetMultiViewRepairPolicy().to_dict()
    v1_payload = {
        key: value for key, value in current_policy.items() if key != "policy_digest"
    }
    v1_payload["authority_version"] = "mdstats.target-order.repair2.configured-shell.v1"
    v1_policy = {**v1_payload, "policy_digest": digest(v1_payload)}
    with pytest.raises(TrainingDataInputError, match="REPAIR2 policy version"):
        TargetMultiViewRepairPolicy.from_dict(v1_policy)

    fixture = _prepare_fixture()
    build = _prepare(tmp_path / "prepared", fixture)
    identity_arguments = {
        "population_digest": fixture.population.content_digest,
        "split_digest": fixture.split.content_digest,
        "raw_feature_catalog_digest": fixture.raw_features.content_digest,
        "structural_input_identity": "real-owner-prepare-fixture.v1",
        "training_order_policy": _POLICY_NAME,
        "hard_support_obligations": (),
        "configured_sizes": _SIZES,
    }
    assert preparation.target_order_build_identity(**identity_arguments) == build.preparation.build_identity
    current_method = preparation.target_order_method_identity()
    monkeypatch.setattr(
        preparation,
        "target_order_method_identity",
        lambda: {**current_method, "repair_policy": v1_policy},
    )
    v1_identity = preparation.target_order_build_identity(**identity_arguments)
    assert v1_identity != build.preparation.build_identity

    # A completed build whose repair plan names the v1 policy cannot authenticate.
    root = tmp_path / "prepared" / "target-order"
    manifest = json.loads((root / "builds" / build.preparation.build_identity / "manifest.json").read_text())
    manifest["repair_plan"]["policy"] = v1_policy
    manifest.pop("manifest_digest")
    manifest["manifest_digest"] = digest(manifest)
    forged = tmp_path / "forged"
    forged.mkdir()
    (forged / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TargetOrderArtifactStoreError, match="REPAIR2 policy version"):
        preparation._read_build(forged, root)


def _fence_lock_path(prepared_root: Path) -> Path:
    locks = tuple((prepared_root / "target-order" / "builds").glob(".*.prepare.lock"))
    assert len(locks) == 1, locks
    return locks[0]


def _fence_is_held(lock_path: Path) -> bool:
    import fcntl

    descriptor = os.open(lock_path, os.O_RDWR)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return False
    finally:
        os.close(descriptor)


def test_real_owner_same_build_prepare_is_single_flight(tmp_path: Path) -> None:
    import threading

    fixture = _prepare_fixture()
    prepared_root = tmp_path / "prepared"
    root = prepared_root / "target-order"
    holder_inside = threading.Event()
    release = threading.Event()
    results: dict[str, object] = {}
    failures: list[BaseException] = []
    holder_progress: list[str] = []
    waiter_progress: list[str] = []
    waiter_structural = {"calls": 0}

    def holder_callback(message: str) -> None:
        holder_progress.append(message)
        if message.startswith("status=selecting; progress=8/24"):
            holder_inside.set()
            assert release.wait(300.0)

    def run(name: str, **kwargs) -> None:
        try:
            results[name] = _prepare(prepared_root, fixture, **kwargs)
        except BaseException as exc:  # pragma: no cover - surfaced below
            failures.append(exc)

    def waiter_structural_factory():
        waiter_structural["calls"] += 1
        return fixture.structural_catalog

    holder = threading.Thread(
        target=run, args=("holder",), kwargs={"progress_callback": holder_callback}, daemon=True
    )
    holder.start()
    try:
        assert holder_inside.wait(300.0), failures
        lock_path = _fence_lock_path(prepared_root)
        assert _fence_is_held(lock_path)
        checkpoints_before = _tree_digest(root / "checkpoints")
        assert checkpoints_before
        assert len(tuple((root / "attempts").iterdir())) == 1

        waiter = threading.Thread(
            target=run,
            args=("waiter",),
            kwargs={
                "progress_callback": waiter_progress.append,
                "structural_catalog_factory": waiter_structural_factory,
            },
            daemon=True,
        )
        waiter.start()

        # A different prospective build identity is not serialized behind the
        # held same-build fence: it completes while the holder is still paused.
        other = _prepare(prepared_root, fixture, sizes=(8, 16))
        assert other.preparation.build_identity not in lock_path.name
        assert _fence_is_held(lock_path)
        assert "waiter" not in results and "holder" not in results
        assert not any(item.startswith("stage=") for item in waiter_progress)
        assert waiter_structural["calls"] == 0
        # The waiter created no attempt scratch and touched no checkpoint.
        assert len(tuple((root / "attempts").iterdir())) == 1
        assert _tree_digest(root / "checkpoints").items() >= checkpoints_before.items()
    finally:
        release.set()
        holder.join(300.0)
    waiter.join(300.0)
    assert not failures, failures
    assert not holder.is_alive() and not waiter.is_alive()

    holder_build, waiter_build = results["holder"], results["waiter"]
    assert not holder_build.reused
    assert waiter_build.reused
    assert waiter_structural["calls"] == 0
    assert not any(item.startswith("stage=") for item in waiter_progress)
    assert waiter_build.preparation.content_digest == holder_build.preparation.content_digest
    assert waiter_build.frame_uids == holder_build.frame_uids
    assert waiter_build.repair_plan.to_dict() == holder_build.repair_plan.to_dict()
    assert waiter_build.qualification.to_dict() == holder_build.qualification.to_dict()
    assert not tuple((root / "attempts").iterdir())
    assert not _fence_is_held(lock_path)

    # Serial reference: an independent root yields the identical build.
    serial = _prepare(tmp_path / "serial", fixture)
    assert serial.preparation.content_digest == holder_build.preparation.content_digest


def test_real_owner_interrupted_fence_holder_releases_and_successor_resumes(
    tmp_path: Path,
) -> None:
    import signal
    import threading

    prepared_root = tmp_path / "prepared"
    marker = tmp_path / "holder-inside"
    repository = Path(__file__).resolve().parents[1]
    child_script = r'''
import sys, time
from pathlib import Path
from tests.test_mlff_target_order_real_owner import _prepare, _prepare_fixture

marker = Path(sys.argv[2])

def callback(message):
    if message.startswith("status=selecting; progress=8/24"):
        marker.write_text("inside")
        while True:
            time.sleep(60)

_prepare(Path(sys.argv[1]), _prepare_fixture(), progress_callback=callback)
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(repository), environment.get("PYTHONPATH", "")) if item
    )
    child = subprocess.Popen(
        [sys.executable, "-c", child_script, str(prepared_root), str(marker)],
        cwd=repository,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 300.0
        while not marker.exists():
            assert child.poll() is None, child.stdout.read()
            assert time.monotonic() < deadline, "fence holder never reached its checkpoint"
            time.sleep(0.05)
        lock_path = _fence_lock_path(prepared_root)
        assert _fence_is_held(lock_path)

        fixture = _prepare_fixture()
        progress: list[str] = []
        results: dict[str, object] = {}
        failures: list[BaseException] = []

        def successor() -> None:
            try:
                results["build"] = _prepare(prepared_root, fixture, progress_callback=progress.append)
            except BaseException as exc:  # pragma: no cover - surfaced below
                failures.append(exc)

        waiter = threading.Thread(target=successor, daemon=True)
        waiter.start()
        assert "build" not in results and not progress
        child.send_signal(signal.SIGKILL)
        child.wait(60.0)
        waiter.join(300.0)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(60.0)
    assert not failures, failures
    build = results["build"]
    # The successor acquired the released fence, rechecked the absent build,
    # removed nothing it did not own, and resumed from the authenticated
    # checkpoint the killed holder published.
    assert not build.reused
    assert any("resume=8" in item for item in progress), progress
    # Only the killed holder's own scratch remains; the successor removed its
    # own scratch and did not adopt or delete the dead attempt's directory.
    attempts = prepared_root / "target-order" / "attempts"
    assert len(tuple(attempts.iterdir())) == 1
    fresh = _prepare(tmp_path / "fresh", fixture)
    assert build.preparation.content_digest == fresh.preparation.content_digest
    assert build.repair_plan.to_dict() == fresh.repair_plan.to_dict()
    assert build.qualification.to_dict() == fresh.qualification.to_dict()


def test_real_owner_required_structural_families_are_complete_or_fail_closed(
    tmp_path: Path,
) -> None:
    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.target_order.coverage_reference import (
        REQUIRED_STRUCTURAL_FEATURE_FAMILIES,
    )

    def reference(fixture, **kwargs):
        return build_target_coverage_reference(
            dataset_id=fixture.population.dataset_id,
            population=fixture.population,
            split=fixture.split,
            raw_feature_catalog=fixture.raw_features,
            structural_catalog=fixture.structural_catalog,
            policy=TargetCoveragePolicy(),
            radius_block_size=8,
            **kwargs,
        )

    from mdstats.training_data.resources import StageResourceScope

    complete = build_selector_fixture(frames=32, units=4, event_frames=())
    serial = reference(complete, query_workers=1)
    parallel = reference(complete, query_workers=2)
    # COVREF-PAR1 block parallelism, the execution path ``prepare`` uses.
    blocked = reference(
        complete,
        query_workers=1,
        execution_scope=StageResourceScope(
            stage_name="TARGET-ORDER-COVREF",
            cpu_threads_available=4,
            cpu_threads_budget=4,
            python_workers=4,
            tree_workers=1,
            blas_threads=1,
        ),
    )
    assert serial.content_digest == parallel.content_digest == blocked.content_digest
    assert {
        family.semantic_family for family in serial.families if family.family_kind == "structural"
    } == set(REQUIRED_STRUCTURAL_FEATURE_FAMILIES)

    omitted = build_selector_fixture(
        frames=32, units=4, event_frames=(), omit_structural_families=("orientational_order",)
    )
    with pytest.raises(TrainingDataInputError, match="orientational_order"):
        reference(omitted, query_workers=1)

    # A family whose only group projection has fewer than the D2 minimum
    # reference elements is invalid and must fail rather than disappear.
    sparse = build_selector_fixture(
        frames=32, units=4, event_frames=(), sparse_structural_families=("connectivity",)
    )
    with pytest.raises(TrainingDataInputError, match="connectivity") as caught:
        reference(sparse, query_workers=1)
    assert "orientational_order" not in str(caught.value)

    # Preparation fails before FEAS/MVIDX/MVSEL products exist.
    prepared_root = tmp_path / "prepared"
    with pytest.raises(TrainingDataInputError, match="orientational_order"):
        _prepare(prepared_root, omitted)
    target_root = prepared_root / "target-order"
    for stage in ("reference", "geometry", "mvidx", "checkpoints", "builds"):
        assert not tuple((target_root / stage).glob("[!.]*")), stage


def test_real_owner_molecular_phase_plan_cannot_thin_target_order_families(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from mdstats.training_data import campaign_target_size_runtime as runtime
    from mdstats.training_data.phase_geometry_profiles import (
        derive_phase_geometry_selection_plan,
    )
    from mdstats.training_data.structural_selection import (
        UniversalStructuralSelectionProvider,
    )
    from mdstats.training_data.target_order import preparation
    from mdstats.training_data.target_order.coverage_reference import (
        REQUIRED_STRUCTURAL_FEATURE_FAMILIES,
    )

    profile = mdstats.build_single_phase_material_profile(
        profile_id="molecular-bulk",
        phase_kind=mdstats.MaterialPhaseKind.MOLECULAR_OR_GAS,
        geometry=mdstats.MaterialGeometryKind.BULK,
    )
    contracts = mdstats.build_material_profile_contracts(profile)
    plan = derive_phase_geometry_selection_plan(contracts)
    assert "orientational_order" not in plan.feature_families

    captured: dict[str, object] = {}

    def capture_prepare(**kwargs):
        captured["prepare"] = kwargs
        kwargs["structural_catalog_factory"]()
        return "prepared"

    def capture_catalog(self, frame_catalog, frame_data_by_run, data4, **kwargs):
        captured["policy"] = kwargs["policy"]

    monkeypatch.setattr(preparation, "prepare_target_training_order", capture_prepare)
    monkeypatch.setattr(UniversalStructuralSelectionProvider, "build_catalog", capture_catalog)
    fixture = _prepare_fixture()

    def call(material_contracts):
        return runtime._build_current_target_training_order(
            {"model": {"device": "cpu"}},
            SimpleNamespace(internal=tmp_path / "internal"),
            population=fixture.population,
            split=fixture.split,
            policy=SimpleNamespace(
                training_order_policy=_POLICY_NAME,
                hard_support_obligations=(),
                candidate_sizes=_SIZES,
            ),
            raw_feature_catalog=fixture.raw_features,
            frame_catalog=SimpleNamespace(content_digest=digest({"frame-catalog": 1})),
            frame_data_by_run={},
            data4=SimpleNamespace(
                material_profile_contracts=material_contracts,
                content_digest=digest({"data4": 1}),
            ),
        )

    assert call(contracts) == "prepared"
    policy = captured["policy"]
    assert set(policy.enabled_feature_families) == set(REQUIRED_STRUCTURAL_FEATURE_FAMILIES)
    assert policy.materialize_atomic_environments is False
    # Accepted phase/geometry semantics other than the family catalog survive.
    assert policy.phase_geometry_plan_digest == plan.content_digest
    assert tuple(policy.enabled_event_types) == tuple(sorted(plan.event_types))
    molecular_identity = captured["prepare"]["structural_input_identity"]

    call(None)
    default_policy = captured["policy"]
    assert set(default_policy.enabled_feature_families) == set(REQUIRED_STRUCTURAL_FEATURE_FAMILIES)
    assert captured["prepare"]["structural_input_identity"] != molecular_identity


def test_real_owner_corrupt_published_target_order_artifacts_are_not_replaced(
    tmp_path: Path,
) -> None:
    # Direct owner: identical content converges, corrupt or conflicting content
    # fails closed and stays byte-for-byte untouched.
    destination = tmp_path / "store" / "artifact"

    def writer(content: bytes):
        def write(directory: Path):
            (directory / "member.bin").write_bytes(content)
            return {
                "schema": "test.target-order-artifact.v1",
                "content_digest": hashlib.sha256(content).hexdigest(),
            }

        return write

    def verify(path: Path, manifest) -> None:
        if hashlib.sha256((path / "member.bin").read_bytes()).hexdigest() != manifest["content_digest"]:
            raise TargetOrderArtifactStoreError("member checksum mismatch")

    first = publish_artifact_directory(
        destination, schema="test.target-order-artifact.v1", write=writer(b"same"), verify_existing=verify
    )
    again = publish_artifact_directory(
        destination, schema="test.target-order-artifact.v1", write=writer(b"same"), verify_existing=verify
    )
    assert again.manifest == first.manifest
    with pytest.raises(TargetOrderArtifactStoreError, match="not replaced"):
        publish_artifact_directory(
            destination, schema="test.target-order-artifact.v1", write=writer(b"other"), verify_existing=verify
        )
    (destination / "member.bin").write_bytes(b"corrupt")
    corrupt = _tree_digest(destination)
    with pytest.raises(TargetOrderArtifactStoreError, match="not replaced"):
        publish_artifact_directory(
            destination, schema="test.target-order-artifact.v1", write=writer(b"same"), verify_existing=verify
        )
    assert _tree_digest(destination) == corrupt
    assert sorted(path.name for path in destination.parent.iterdir()) == [".artifact.lock", "artifact"]

    # Real prepare: a corrupt completed build and a corrupt completed reference
    # both fail closed without deletion, replacement, or an alternative build.
    fixture = _prepare_fixture()
    prepared_root = tmp_path / "prepared"
    build = _prepare(prepared_root, fixture)
    root = prepared_root / "target-order"
    paths = dict(build.preparation.artifact_paths)
    build_directory = root / paths["build"]
    manifest_path = build_directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["frame_uids"] = list(reversed(manifest["frame_uids"]))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    corrupt_build = _tree_digest(build_directory)
    with pytest.raises(TargetOrderArtifactStoreError, match="does not replace"):
        _prepare(prepared_root, fixture)
    assert _tree_digest(build_directory) == corrupt_build

    reference_directory = root / paths["reference"]
    member = next(path for path in sorted(reference_directory.iterdir()) if path.suffix == ".npy")
    raw = bytearray(member.read_bytes())
    raw[-1] ^= 0xFF
    member.write_bytes(bytes(raw))
    corrupt_reference = _tree_digest(reference_directory)
    builds_before = sorted(path.name for path in (root / "builds").glob("[!.]*"))
    with pytest.raises(TargetOrderArtifactStoreError, match="does not replace"):
        _prepare(prepared_root, fixture, sizes=(8, 16))
    assert _tree_digest(reference_directory) == corrupt_reference
    assert sorted(path.name for path in (root / "builds").glob("[!.]*")) == builds_before
    assert not tuple((root / "attempts").iterdir())


# --- R12 B12-1: batched REPAIR2 execution versus the scalar D2 oracle ---------


def _bits(values) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float64).view(np.uint64)


def _oracle_after_removal(
    candidates: np.ndarray, removed: int, forward, state
) -> tuple[np.ndarray, np.ndarray]:
    """Scalar D2 formula owner for the removal-dependent frontier terms."""

    from mdstats.training_data.target_order import repair as repair_module

    marks = repair_module._RemovalMarks(forward)
    marks.mark(forward, int(removed))
    representative = np.asarray(
        [
            repair_module._representative_after_removal(
                int(candidate), forward, state, marks
            )
            for candidate in candidates
        ],
        dtype=np.float64,
    )
    diversity = np.asarray(
        [
            repair_module._diversity_after_removal(
                int(candidate), forward, state, marks
            )
            for candidate in candidates
        ],
        dtype=np.float64,
    )
    return representative, diversity


def _repair_states(products: SimpleNamespace) -> list[tuple[str, object, np.ndarray]]:
    """Bounded adversarial states: hard deficit pending, then satisfied."""

    from mdstats.training_data.target_order.repair import hard_deficit

    reference = products.reference
    forward = products.forward
    state = build_forward_state(reference, forward, validate=False)
    states: list[tuple[str, object, np.ndarray]] = []
    deficit_seen = False
    satisfied_seen = False
    for rank in range(int(forward.candidate_count)):
        candidate = rank
        select_candidate(
            candidate, forward, state, score=score_candidate(candidate, forward, state)
        )
        pending = hard_deficit(forward, state) > 0
        if pending and not deficit_seen and rank >= 1:
            deficit_seen = True
            states.append(("hard-deficit-pending", state, np.arange(rank + 1)))
        if not pending and not satisfied_seen and rank >= 3:
            satisfied_seen = True
            states.append(("hard-deficit-satisfied", state, np.arange(rank + 1)))
        if deficit_seen and satisfied_seen and rank >= int(forward.candidate_count) // 2:
            states.append(("saturated-frontier", state, np.arange(rank + 1)))
            break
    assert states, "fixture produced no bounded repair state"
    return states


@pytest.mark.parametrize("workers", (1, 2, 4, 16))
def test_real_owner_repair2_batch_quantities_are_bitwise_equal_to_the_scalar_oracle(
    repair_products: SimpleNamespace, workers: int
) -> None:
    """R12 B12-1: the batched proposal path reproduces D2 9.2/9.3 bitwise.

    Every candidate-indexed quantity the optimized REPAIR2 path evaluates is
    compared, bit for bit, against the scalar formula owner it replaced: the
    removal metrics, the coverage-gain frontier filters and the
    removal-dependent representative/diversity terms, at removal shortlists of
    size 1 and of the frozen limit 64, over states with the hard deficit both
    pending and satisfied.
    """

    from mdstats.training_data.target_order.repair import (
        TargetMultiViewRepairPolicy,
        _StateBatch,
        hard_safe,
        removal_metrics,
    )
    from mdstats.training_data.target_order.selector import (
        family_coverage_gain,
        total_coverage_gain,
    )

    if workers > 1 and not qualify_mvsel2_native_backend().qualified:
        pytest.skip("native backend is required for width > 1")
    products = repair_products
    forward = products.forward
    limit = TargetMultiViewRepairPolicy().removal_shortlist_limit
    assert limit == 64
    compared = {"removal": 0, "coverage": 0, "after_removal": 0, "shortlists": []}

    for label, state, selected in _repair_states(products):
        batch = _StateBatch(forward, state, workers=workers)
        assert batch.native == (workers > 1)

        # removal metrics over every selected row
        unique, loss = batch.removal_metrics_many(selected)
        oracle = [removal_metrics(int(c), forward, state) for c in selected]
        assert np.array_equal(_bits(unique), _bits([v[0] for v in oracle])), label
        assert np.array_equal(_bits(loss), _bits([v[1] for v in oracle])), label
        compared["removal"] += int(selected.size)

        # coverage-gain frontier filters over every available candidate
        available = np.flatnonzero(state.available).astype(np.uint32)
        if available.size:
            for index in range(len(forward.families)):
                gains = batch.family_coverage_gain_many(available, index)
                expected = [
                    family_coverage_gain(int(c), index, forward, state)[0]
                    for c in available
                ]
                assert np.array_equal(_bits(gains), _bits(expected)), (label, index)
            totals = batch.total_coverage_gain_many(available)
            expected_totals = [
                total_coverage_gain(int(c), forward, state)[1] for c in available
            ]
            assert np.array_equal(_bits(totals), _bits(expected_totals)), label
            compared["coverage"] += int(available.size)

            # removal-dependent terms at shortlist sizes 1 and 64 (the frozen limit).
            # Only zero-unique, hard-safe members are legal removals; anything
            # else must fail closed and is covered by the negative test below.
            removable = np.asarray(
                [
                    int(candidate)
                    for position, candidate in enumerate(selected)
                    if float(unique[position]) <= 1.0e-14
                    and hard_safe(int(candidate), forward, state)
                ],
                dtype=np.uint32,
            )
            if removable.size == 0:
                continue
            for size in (1, min(limit, int(removable.size))):
                shortlist = removable[:size]
                compared["shortlists"].append(int(shortlist.size))
                for removed in shortlist:
                    representative = batch.representative_after_removal_many(
                        available, int(removed)
                    )
                    diversity = batch.diversity_after_removal_many(
                        available, int(removed)
                    )
                    expected_rep, expected_div = _oracle_after_removal(
                        available, int(removed), forward, state
                    )
                    assert np.array_equal(
                        _bits(representative), _bits(expected_rep)
                    ), (label, int(removed))
                    assert np.array_equal(_bits(diversity), _bits(expected_div)), (
                        label,
                        int(removed),
                    )
                    compared["after_removal"] += int(available.size)

    assert compared["removal"] > 0 and compared["coverage"] > 0
    assert compared["after_removal"] > 0
    assert 1 in compared["shortlists"] and max(compared["shortlists"]) > 1


@pytest.mark.parametrize("workers", (1, 2))
def test_real_owner_repair2_batch_fails_closed_on_an_illegal_removal(
    repair_products: SimpleNamespace, workers: int
) -> None:
    """R12 B12-1: the batched path keeps the zero-unique removal invariant.

    A candidate that uniquely covers a witness shared with an evaluated
    replacement is not a legal removal.  The batch must raise exactly where the
    scalar oracle raises instead of quietly summing a patched term.
    """

    from mdstats.training_data.target_order.repair import _StateBatch
    from mdstats.training_data._common import TrainingDataInputError

    if workers > 1 and not qualify_mvsel2_native_backend().qualified:
        pytest.skip("native backend is required for width > 1")
    products = repair_products
    forward = products.forward
    state = build_forward_state(products.reference, forward, validate=False)
    # One member of each duplicate cluster: every witness it covers is unique.
    for candidate in (0, 16):
        select_candidate(
            candidate, forward, state, score=score_candidate(candidate, forward, state)
        )
    available = np.flatnonzero(state.available).astype(np.uint32)
    batch = _StateBatch(forward, state, workers=workers)
    with pytest.raises(TrainingDataInputError, match="zero-unique removal invariant"):
        batch.representative_after_removal_many(available, 16)
    with pytest.raises(TrainingDataInputError, match="zero-unique removal invariant"):
        _oracle_after_removal(available, 16, forward, state)


def test_real_owner_repair2_batch_state_arrays_are_invalidated_by_an_accepted_swap(
    repair_products: SimpleNamespace,
) -> None:
    """R12 B12-1: a swap must discard every state-dependent batch quantity.

    The batch caches removal-independent per-witness term vectors.  This drives
    a real accepted swap and shows both that a freshly built batch matches the
    scalar oracle on the new state and that reusing the stale batch would have
    produced different numbers -- so the per-state construction is load-bearing
    rather than vacuous.
    """

    from mdstats.training_data.target_order.repair import (
        _StateBatch,
        _best_proposal,
        _build_frontier,
        removal_metrics,
    )
    from mdstats.training_data.target_order.selector import deselect_candidate
    from mdstats.training_data._common import TrainingDataInputError

    products = repair_products
    reference, forward = products.reference, products.forward
    selection = _manual_selection_plan(products, order=(0, 16, 1, 2, 3, 4), sizes=(2, 6))
    state = build_forward_state(reference, forward, validate=False)
    order = [reference.frame_index(uid) for uid in selection.master_order]
    for candidate in order:
        select_candidate(
            candidate, forward, state, score=score_candidate(candidate, forward, state)
        )

    stale = _StateBatch(forward, state, workers=1)
    shortlist = [
        (rank, order[rank], *removal_metrics(order[rank], forward, state))
        for rank in range(len(order))
    ]
    shortlist = [row for row in shortlist if row[2] <= 1.0e-14]
    assert shortlist, "fixture produced no removable shell member"
    frontier = _build_frontier(forward, state, selection.policy, 1.0e-14, stale)
    assert frontier is not None
    best = _best_proposal(
        reference, forward, state, shortlist, frontier, stale, 1.0e-14
    )
    assert best is not None

    removed, replacement = int(best["removed"]), int(best["replacement"])
    deselect_candidate(removed, forward, state)
    select_candidate(
        replacement,
        forward,
        state,
        score=score_candidate(replacement, forward, state),
    )

    # A batch built on the new state answers the scalar oracle exactly.
    fresh = _StateBatch(forward, state, workers=1)
    row = np.asarray([replacement], dtype=np.uint32)
    oracle_unique, oracle_loss = removal_metrics(replacement, forward, state)
    fresh_unique, fresh_loss = fresh.removal_metrics_many(row)
    assert np.array_equal(_bits(fresh_unique), _bits([oracle_unique]))
    assert np.array_equal(_bits(fresh_loss), _bits([oracle_loss]))
    expected, _ = _oracle_after_removal(
        frontier.candidates, replacement, forward, state
    )
    assert np.array_equal(
        _bits(fresh.representative_after_removal_many(frontier.candidates, replacement)),
        _bits(expected),
    )

    # The pre-swap batch would answer the same question from the old state, so
    # per-state construction is what keeps the arrays correct.
    try:
        stale_unique, stale_loss = stale.removal_metrics_many(row)
    except TrainingDataInputError:
        stale_differs = True
    else:
        stale_differs = not (
            np.array_equal(_bits(stale_unique), _bits([oracle_unique]))
            and np.array_equal(_bits(stale_loss), _bits([oracle_loss]))
        )
    assert stale_differs, "stale batch arrays were indistinguishable from the new state"


def test_real_owner_repair2_best_relative_mask_matches_the_selector_filter() -> None:
    """R12 B12-1: the array contender filter is the MVSEL2 rule, not a new one."""

    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st

    from mdstats.training_data.target_order.repair import _best_relative_mask
    from mdstats.training_data.target_order.selector import filter_best_relative

    @settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(
            st.floats(min_value=-1.0e6, max_value=1.0e6, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=24,
        )
    )
    def property_holds(values: list[float]) -> None:
        candidates = tuple(range(len(values)))
        mapping = {index: value for index, value in enumerate(values)}
        expected = filter_best_relative(candidates, mapping, 1.0e-14)
        mask = _best_relative_mask(np.asarray(values, dtype=np.float64), 1.0e-14)
        assert tuple(index for index in candidates if mask[index]) == expected

    property_holds()


def test_real_owner_repair2_has_no_python_worker_queue_left_in_the_proposal_path() -> None:
    """R12 B12-1: the GIL-bound candidate-at-a-time mechanism is gone, not wrapped."""

    import inspect

    from mdstats.training_data.target_order import repair as repair_module

    source = inspect.getsource(repair_module)
    assert "DeterministicWorkQueue" not in source
    assert "threading" not in source and "from threading import" not in source
    assert "ThreadPool" not in source
    # Exactly one execution primitive, reused from the qualified MVSEL2 backend.
    assert source.count("score_family_candidate_batch(") == 1
    assert "_best_proposal" in source and "def _proposal(" in source
