"""LD9-V4 browser smoke-test acceptance contracts.

The browser runner remains external because it depends on Chromium/Playwright.
This module makes its acceptance policy and renderer classification part of the
public, serializable mdstats contract.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphStyleError

BROWSER_ACCEPTANCE_POLICY_SCHEMA = "mdstats.browser-acceptance-policy.v1"
BROWSER_ACCEPTANCE_REPORT_SCHEMA = "mdstats.browser-acceptance-report.v1"

RendererKind = Literal["physical", "software", "unavailable"]


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GraphStyleError(f"{name} must be finite and positive.")
    return result


def _optional_nonnegative_int(value: Any, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer or None.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be a nonnegative integer or None.")
    return result


def classify_webgl_renderer(vendor: Any, renderer: Any) -> RendererKind:
    text = " ".join(
        part.strip().lower()
        for part in (str(vendor or ""), str(renderer or ""))
        if part is not None
    ).strip()
    if not text:
        return "unavailable"
    software_tokens = (
        "swiftshader",
        "llvmpipe",
        "softpipe",
        "software rasterizer",
        "mesa offscreen",
    )
    if any(token in text for token in software_tokens):
        return "software"
    return "physical"


@dataclass(frozen=True, slots=True)
class BrowserAcceptancePolicy:
    max_first_complete_frame_seconds: float = 15.0
    min_camera_orbit_fps: float = 20.0
    max_trace_toggle_seconds: float = 1.0
    max_js_heap_used_bytes: int | None = 512 * 1024**2
    require_no_context_loss: bool = True
    require_physical_webgl_for_production: bool = True
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = BROWSER_ACCEPTANCE_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_ACCEPTANCE_POLICY_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-acceptance policy schema {self.schema_version!r}."
            )
        for name in (
            "max_first_complete_frame_seconds",
            "min_camera_orbit_fps",
            "max_trace_toggle_seconds",
        ):
            object.__setattr__(
                self, name, _positive_float(getattr(self, name), name=name)
            )
        object.__setattr__(
            self,
            "max_js_heap_used_bytes",
            _optional_nonnegative_int(
                self.max_js_heap_used_bytes, name="max_js_heap_used_bytes"
            ),
        )
        object.__setattr__(
            self, "require_no_context_loss", bool(self.require_no_context_loss)
        )
        object.__setattr__(
            self,
            "require_physical_webgl_for_production",
            bool(self.require_physical_webgl_for_production),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_first_complete_frame_seconds": self.max_first_complete_frame_seconds,
            "min_camera_orbit_fps": self.min_camera_orbit_fps,
            "max_trace_toggle_seconds": self.max_trace_toggle_seconds,
            "max_js_heap_used_bytes": self.max_js_heap_used_bytes,
            "require_no_context_loss": self.require_no_context_loss,
            "require_physical_webgl_for_production": (
                self.require_physical_webgl_for_production
            ),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserAcceptancePolicy":
        return cls(
            max_first_complete_frame_seconds=value.get(
                "max_first_complete_frame_seconds", 15.0
            ),
            min_camera_orbit_fps=value.get("min_camera_orbit_fps", 20.0),
            max_trace_toggle_seconds=value.get("max_trace_toggle_seconds", 1.0),
            max_js_heap_used_bytes=value.get(
                "max_js_heap_used_bytes", 512 * 1024**2
            ),
            require_no_context_loss=value.get("require_no_context_loss", True),
            require_physical_webgl_for_production=value.get(
                "require_physical_webgl_for_production", True
            ),
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", BROWSER_ACCEPTANCE_POLICY_SCHEMA
            ),
        )


@dataclass(frozen=True, slots=True)
class BrowserAcceptanceReport:
    renderer_kind: RendererKind
    functional_violations: tuple[str, ...]
    production_violations: tuple[str, ...]
    first_complete_frame_seconds: float | None
    camera_orbit_fps: float | None
    trace_toggle_seconds: float | None
    webgl_context_lost: bool | None
    js_heap_used_bytes: int | None
    webgl_vendor: str | None
    webgl_renderer: str | None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = BROWSER_ACCEPTANCE_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_ACCEPTANCE_REPORT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported browser-acceptance report schema {self.schema_version!r}."
            )
        if self.renderer_kind not in {"physical", "software", "unavailable"}:
            raise GraphAdapterError("renderer_kind is invalid.")
        object.__setattr__(
            self, "functional_violations", tuple(str(v) for v in self.functional_violations)
        )
        object.__setattr__(
            self, "production_violations", tuple(str(v) for v in self.production_violations)
        )
        for name in (
            "first_complete_frame_seconds",
            "camera_orbit_fps",
            "trace_toggle_seconds",
        ):
            value = getattr(self, name)
            if value is not None:
                number = float(value)
                if not np.isfinite(number) or number < 0.0:
                    raise GraphStyleError(f"{name} must be finite and nonnegative or None.")
                object.__setattr__(self, name, number)
        object.__setattr__(
            self,
            "js_heap_used_bytes",
            _optional_nonnegative_int(self.js_heap_used_bytes, name="js_heap_used_bytes"),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def functional_passed(self) -> bool:
        return not self.functional_violations

    @property
    def production_default_authorized(self) -> bool:
        return not self.production_violations

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "renderer_kind": self.renderer_kind,
            "functional_passed": self.functional_passed,
            "production_default_authorized": self.production_default_authorized,
            "functional_violations": list(self.functional_violations),
            "production_violations": list(self.production_violations),
            "first_complete_frame_seconds": self.first_complete_frame_seconds,
            "camera_orbit_fps": self.camera_orbit_fps,
            "trace_toggle_seconds": self.trace_toggle_seconds,
            "webgl_context_lost": self.webgl_context_lost,
            "js_heap_used_bytes": self.js_heap_used_bytes,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BrowserAcceptanceReport":
        return cls(
            renderer_kind=value["renderer_kind"],
            functional_violations=tuple(value.get("functional_violations", ())),
            production_violations=tuple(value.get("production_violations", ())),
            first_complete_frame_seconds=value.get("first_complete_frame_seconds"),
            camera_orbit_fps=value.get("camera_orbit_fps"),
            trace_toggle_seconds=value.get("trace_toggle_seconds"),
            webgl_context_lost=value.get("webgl_context_lost"),
            js_heap_used_bytes=value.get("js_heap_used_bytes"),
            webgl_vendor=value.get("webgl_vendor"),
            webgl_renderer=value.get("webgl_renderer"),
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", BROWSER_ACCEPTANCE_REPORT_SCHEMA
            ),
        )


def evaluate_browser_acceptance(
    validation: Mapping[str, Any],
    *,
    policy: BrowserAcceptancePolicy | None = None,
) -> BrowserAcceptanceReport:
    resolved = BrowserAcceptancePolicy() if policy is None else policy
    if not isinstance(resolved, BrowserAcceptancePolicy):
        raise TypeError("policy must be BrowserAcceptancePolicy or None.")
    browser = validation.get("browser", {})
    metrics = validation.get("metrics", {})
    if not isinstance(browser, Mapping) or not isinstance(metrics, Mapping):
        raise GraphAdapterError("Browser validation payload is malformed.")
    vendor = browser.get("webgl_vendor")
    renderer = browser.get("webgl_renderer")
    renderer_kind = classify_webgl_renderer(vendor, renderer)
    first = metrics.get("first_complete_frame_seconds")
    orbit = metrics.get("camera_orbit_fps")
    toggle = metrics.get("trace_toggle_seconds")
    context_lost = metrics.get("webgl_context_lost")
    heap = metrics.get("js_heap_used_bytes")
    violations: list[str] = []
    if validation.get("status") != "passed":
        violations.append("browser_runner_failed")
    if first is None or float(first) > resolved.max_first_complete_frame_seconds:
        violations.append("first_complete_frame_exceeded")
    if orbit is None or float(orbit) < resolved.min_camera_orbit_fps:
        violations.append("camera_orbit_fps_below_minimum")
    if toggle is None or float(toggle) > resolved.max_trace_toggle_seconds:
        violations.append("trace_toggle_exceeded")
    if resolved.require_no_context_loss and context_lost is not False:
        violations.append("webgl_context_lost_or_unknown")
    if (
        resolved.max_js_heap_used_bytes is not None
        and (heap is None or int(heap) > resolved.max_js_heap_used_bytes)
    ):
        violations.append("js_heap_used_exceeded_or_unknown")
    production = list(violations)
    if resolved.require_physical_webgl_for_production and renderer_kind != "physical":
        production.append(f"physical_webgl_required:{renderer_kind}")
    return BrowserAcceptanceReport(
        renderer_kind=renderer_kind,
        functional_violations=tuple(violations),
        production_violations=tuple(production),
        first_complete_frame_seconds=None if first is None else float(first),
        camera_orbit_fps=None if orbit is None else float(orbit),
        trace_toggle_seconds=None if toggle is None else float(toggle),
        webgl_context_lost=None if context_lost is None else bool(context_lost),
        js_heap_used_bytes=None if heap is None else int(heap),
        webgl_vendor=None if vendor is None else str(vendor),
        webgl_renderer=None if renderer is None else str(renderer),
        metadata={
            "policy": resolved.to_json_dict(),
            "validation_schema": validation.get("schema"),
            "navigation_mode": validation.get("navigation_mode"),
        },
    )
