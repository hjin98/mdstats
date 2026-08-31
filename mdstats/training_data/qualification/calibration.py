"""Uncertainty calibration of the exact frozen publication.

Calibration must describe the uncertainty of the product actually being
deployed.  It is therefore evaluated on the reserved
``UNCERTAINTY_CALIBRATION`` role using the exact frozen committee - never on
development evidence, and never on a committee that differs by one member from
the published one.  For a single-model publication with no accepted uncertainty
estimator the honest answer is ``not_applicable``: a point prediction has no
spread, and inventing one would be worse than admitting the gap.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .components import (
    COMPONENT_CALIBRATION,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .geometry import atoms_for_frame, labels_for_frame
from .providers import forces_of, member_provider, predict_all
from .spec import (
    CALIBRATION_METHOD_AUTO,
    CALIBRATION_METHOD_COMMITTEE_VARIANCE,
    CALIBRATION_METHOD_NONE,
)


def qualify_calibration(session: Any) -> QualificationComponentEvidence:
    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_CALIBRATION)
    method = str(policy["method"])
    members = session.publication.members
    frames = binding.evidence_roles.calibration_frame_uids

    if method == CALIBRATION_METHOD_NONE:
        return _not_applicable(
            session, "calibration_disabled_by_policy", "The frozen policy declares no calibration."
        )
    if method == CALIBRATION_METHOD_AUTO and len(members) < 2:
        return _not_applicable(
            session,
            "single_model_publication_without_uncertainty_estimator",
            "The frozen publication has one member and no accepted uncertainty "
            "estimator, so committee spread does not exist.",
        )
    if len(members) < 2:
        return build_component_evidence(
            component=COMPONENT_CALIBRATION,
            binding=binding,
            status=ComponentStatus.REJECTED,
            reason_code="committee_variance_requires_multiple_members",
            detail=(
                "The configured calibration method needs a committee, but the exact "
                "frozen publication has one member. Qualification never adds a member "
                "to make calibration possible."
            ),
            metrics={"member_count": len(members)},
            payload={},
        )
    if len(frames) < int(policy["minimum_frames"]):
        return build_component_evidence(
            component=COMPONENT_CALIBRATION,
            binding=binding,
            status=ComponentStatus.REJECTED,
            reason_code="insufficient_calibration_role_membership",
            detail=(
                "The reserved UNCERTAINTY_CALIBRATION role does not contain enough "
                "independent frames for the frozen calibration policy."
            ),
            metrics={"calibration_frame_count": len(frames)},
            payload={},
        )

    atoms_list = [atoms_for_frame(session.context, uid) for uid in frames]
    references = [labels_for_frame(session.context, uid)[1] for uid in frames]
    stacked: list[np.ndarray] = []
    for member in members:
        with member_provider(session.context, member) as provider:
            predictions = predict_all(session.context, provider, atoms_list)
        stacked.append(np.concatenate([forces_of(item).reshape(-1) for item in predictions]))
    ensemble = np.vstack(stacked)
    mean = ensemble.mean(axis=0)
    spread = ensemble.std(axis=0, ddof=1)
    truth = np.concatenate([np.asarray(item, dtype=np.float64).reshape(-1) for item in references])
    residual = np.abs(mean - truth)

    positive = spread > 0.0
    if not np.any(positive):
        return build_component_evidence(
            component=COMPONENT_CALIBRATION,
            binding=binding,
            status=ComponentStatus.REJECTED,
            reason_code="degenerate_committee_spread",
            detail="Every committee member produced identical predictions; the spread carries no information.",
            metrics={"member_count": len(members)},
            payload={},
        )
    # One global scaling factor is the accepted estimator: it is the minimal
    # correction that makes the committee spread a usable interval width without
    # introducing per-frame freedom that could be fitted to the outcome.
    scaling = float(np.sqrt(np.mean((residual[positive] / spread[positive]) ** 2)))
    # The coverage predicate is an inequality on floating-point quantities that
    # are derived from the same numbers, so an exactly-covered component can
    # otherwise fall on the wrong side of the comparison by one ulp. The guard
    # is representation tolerance, not a relaxed acceptance threshold.
    covered = float(np.mean(residual <= scaling * spread * (1.0 + 1.0e-9)))
    target = float(policy["coverage_target"])
    tolerance = float(policy["coverage_tolerance"])
    passed = bool(np.isfinite(scaling) and abs(covered - target) <= tolerance)
    return build_component_evidence(
        component=COMPONENT_CALIBRATION,
        binding=binding,
        status=ComponentStatus.PASSED if passed else ComponentStatus.REJECTED,
        reason_code=("calibration_within_policy" if passed else "calibration_coverage_out_of_tolerance"),
        detail=(
            ""
            if passed
            else "Calibrated committee coverage is outside the frozen tolerance for the exact publication."
        ),
        metrics={
            "method": CALIBRATION_METHOD_COMMITTEE_VARIANCE,
            "scaling_factor": scaling,
            "empirical_coverage": covered,
            "coverage_target": target,
            "coverage_tolerance": tolerance,
            "component_count": int(truth.size),
        },
        payload={
            "calibration_role_digest": binding.evidence_roles.calibration_digest,
            "calibration_frame_uids": list(frames),
            "member_ids": [member.member_id for member in members],
        },
    )


def _not_applicable(session: Any, reason: str, detail: str) -> QualificationComponentEvidence:
    return build_component_evidence(
        component=COMPONENT_CALIBRATION,
        binding=session.binding,
        status=ComponentStatus.NOT_APPLICABLE,
        reason_code=reason,
        detail=detail,
        metrics={"member_count": len(session.publication.members)},
        payload={},
    )


__all__ = ["qualify_calibration"]
