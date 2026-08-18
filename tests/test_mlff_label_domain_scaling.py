from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import mdstats
from tests.test_mlff_data5_partition_roles import _build


def _legacy_groups(source_fingerprints, policy):
    compatible = {
        mdstats.LabelCompatibilityOutcome.COMPATIBLE,
        mdstats.LabelCompatibilityOutcome.COMPATIBLE_WITH_QUALITY_FLAG,
    }
    groups = []
    unresolved = []
    for source_id, fingerprint in sorted(source_fingerprints.items()):
        unresolved_identity = (
            policy.require_resolved_theory
            and fingerprint.theory.resolution_status != "resolved"
        ) or (
            policy.require_resolved_energy_reference
            and fingerprint.energy_reference.resolution_status != "resolved"
        )
        if unresolved_identity:
            unresolved.append(source_id)
            continue
        for group in groups:
            if all(
                mdstats.compare_label_fingerprints(
                    fingerprint, existing, policy=policy
                ).outcome
                in compatible
                for _, existing in group
            ):
                group.append((source_id, fingerprint))
                break
        else:
            groups.append([(source_id, fingerprint)])
    return tuple(tuple(source_id for source_id, _ in group) for group in groups), tuple(unresolved)


def test_indexed_label_domains_match_legacy_first_fit(tmp_path: Path) -> None:
    sources, _, _, _ = _build(tmp_path)
    base = sources.sources[0].electronic_structure
    paw_variants = (
        (("Li", "Li-A"),),
        (("O", "O-A"),),
        (("Li", "Li-A"), ("O", "O-A")),
        (("Li", "Li-B"),),
        (("O", "O-B"),),
        (("Li", "Li-B"), ("O", "O-B")),
        (("Li", "Li-A"), ("O", "O-B")),
        (("Li", "Li-B"), ("O", "O-A")),
    )
    fingerprints = {}
    for index in range(64):
        theory = replace(base.theory, paw_datasets=paw_variants[index % len(paw_variants)])
        numerical = replace(
            base.numerical_quality,
            settings=(("ENCUT", 500 + 10 * (index % 3)),),
        )
        software = replace(
            base.software_provenance,
            source_program_version=f"test-{index % 2}",
        )
        fingerprints[f"source-{index:03d}"] = replace(
            base,
            theory=theory,
            numerical_quality=numerical,
            software_provenance=software,
        )

    for policy in (
        mdstats.LabelCompatibilityPolicy(),
        mdstats.LabelCompatibilityPolicy(
            numerical_differences_are_quality_flags=False,
            software_differences_are_quality_flags=False,
        ),
    ):
        expected_groups, expected_unresolved = _legacy_groups(fingerprints, policy)
        catalog = mdstats.build_label_domain_catalog(fingerprints, policy=policy)
        actual_groups = tuple(domain.source_ids for domain in catalog.domains)
        # Domain IDs sort by scientific digest, while first-fit groups are in
        # encounter order. Compare the partition, not presentation order.
        assert {frozenset(group) for group in actual_groups} == {
            frozenset(group) for group in expected_groups
        }
        assert catalog.unresolved_source_ids == expected_unresolved
        for domain in catalog.domains:
            assert all(catalog.domain_for_source(uid) == domain.domain_id for uid in domain.source_ids)
