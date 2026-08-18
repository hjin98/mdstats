"""LD9-V4 browser acceptance and renderer classification tests."""
from __future__ import annotations

from mdstats import (
    BrowserAcceptancePolicy,
    BrowserAcceptanceReport,
    classify_webgl_renderer,
    evaluate_browser_acceptance,
)


def _validation(renderer: str | None = "NVIDIA RTX") -> dict:
    return {
        "schema": "mdstats.density-browser-validation.v1",
        "status": "passed",
        "navigation_mode": "http-loopback",
        "browser": {
            "webgl_vendor": "Vendor" if renderer else None,
            "webgl_renderer": renderer,
        },
        "metrics": {
            "first_complete_frame_seconds": 10.0,
            "camera_orbit_fps": 30.0,
            "trace_toggle_seconds": 0.1,
            "webgl_context_lost": False,
            "js_heap_used_bytes": 200_000_000,
        },
    }


def test_renderer_classification() -> None:
    assert classify_webgl_renderer("NVIDIA", "RTX 4090") == "physical"
    assert classify_webgl_renderer("Google", "ANGLE SwiftShader") == "software"
    assert classify_webgl_renderer(None, None) == "unavailable"


def test_physical_browser_gate_authorizes_production_default() -> None:
    report = evaluate_browser_acceptance(_validation())
    assert report.functional_passed
    assert report.production_default_authorized
    assert report.renderer_kind == "physical"
    assert BrowserAcceptanceReport.from_json_dict(report.to_json_dict()) == report


def test_software_or_missing_renderer_passes_functional_but_not_production() -> None:
    software = evaluate_browser_acceptance(_validation("ANGLE SwiftShader"))
    assert software.functional_passed
    assert not software.production_default_authorized
    assert software.renderer_kind == "software"
    missing = evaluate_browser_acceptance(_validation(None))
    assert missing.functional_passed
    assert not missing.production_default_authorized
    assert "physical_webgl_required:unavailable" in missing.production_violations


def test_policy_can_authorize_software_validation_explicitly() -> None:
    policy = BrowserAcceptancePolicy(require_physical_webgl_for_production=False)
    report = evaluate_browser_acceptance(_validation("ANGLE SwiftShader"), policy=policy)
    assert report.production_default_authorized


def test_metric_failures_are_structured() -> None:
    payload = _validation()
    payload["metrics"]["first_complete_frame_seconds"] = 30.0
    payload["metrics"]["camera_orbit_fps"] = 5.0
    payload["metrics"]["webgl_context_lost"] = True
    report = evaluate_browser_acceptance(payload)
    assert not report.functional_passed
    assert "first_complete_frame_exceeded" in report.functional_violations
    assert "camera_orbit_fps_below_minimum" in report.functional_violations
    assert "webgl_context_lost_or_unknown" in report.functional_violations
