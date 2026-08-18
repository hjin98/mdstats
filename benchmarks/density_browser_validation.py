#!/usr/bin/env python3
"""LD9-V0 Chromium/WebGL smoke validation for a self-contained Plotly HTML.

This benchmark is intentionally external to the plotting API.  It records the
browser, WebGL renderer, first-frame latency, scripted camera-orbit throughput,
trace-toggle latency, trace count, context-loss state, and optional JavaScript heap
statistics.  The test does not change or rewrite the input artifact.
"""

from __future__ import annotations

import argparse
import json
import platform
import threading
import time
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import quote

from mdstats import BrowserAcceptancePolicy, evaluate_browser_acceptance

SCHEMA = "mdstats.density-browser-validation.v1"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def _loopback_server(path: Path) -> Iterator[str]:
    """Serve one artifact directory over loopback for Chromium validation."""

    handler = partial(_QuietHandler, directory=str(path.parent))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}/{quote(path.name)}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


def _markdown(result: dict[str, Any]) -> str:
    browser = result.get("browser", {})
    metrics = result.get("metrics", {})
    lines = [
        "# LD9-V0 browser validation",
        "",
        f"- Status: **{result['status']}**",
        f"- Input: `{result['input_html']}`",
        f"- Input bytes: {result['input_html_bytes']:,}",
        f"- Chromium: `{browser.get('version', 'unavailable')}`",
        f"- User agent: `{browser.get('user_agent', 'unavailable')}`",
        f"- WebGL renderer: `{browser.get('webgl_renderer', 'unavailable')}`",
        f"- Plotly trace count: {metrics.get('trace_count')}",
        f"- First complete frame: {metrics.get('first_complete_frame_seconds')} s",
        f"- Scripted camera orbit: {metrics.get('camera_orbit_fps')} frames/s",
        f"- Representative trace toggle: {metrics.get('trace_toggle_seconds')} s",
        f"- WebGL context loss: {metrics.get('webgl_context_lost')}",
        f"- JavaScript heap used: {metrics.get('js_heap_used_bytes')}",
        "",
        "## Notes",
        "",
        "The browser environment is part of the benchmark evidence. Headless Chromium may use SwiftShader rather than the workstation GPU; the reported WebGL renderer must therefore be retained with every result.",
    ]
    acceptance = result.get("acceptance", {})
    if acceptance:
        lines.extend((
            "",
            "## Acceptance",
            "",
            f"- Renderer kind: **{acceptance.get('renderer_kind')}**",
            f"- Functional gate: **{acceptance.get('functional_passed')}**",
            f"- Production-default authorization: **{acceptance.get('production_default_authorized')}**",
            f"- Production violations: `{acceptance.get('production_violations')}`",
        ))
    if result.get("error"):
        lines.extend(("", "## Error", "", f"```text\n{result['error']}\n```"))
    return "\n".join(lines) + "\n"


def validate_html(
    html_path: Path,
    *,
    chromium_executable: str | None = None,
    timeout_seconds: float = 180.0,
    orbit_frames: int = 24,
    max_direct_injection_bytes: int = 64 * 1024**2,
) -> dict[str, Any]:
    """Run one bounded loopback-served browser smoke test."""

    from playwright.sync_api import sync_playwright

    resolved = html_path.resolve()
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "failed",
        "input_html": str(resolved),
        "input_html_bytes": resolved.stat().st_size,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "browser": {},
        "metrics": {},
    }
    timeout_ms = int(timeout_seconds * 1000.0)
    start = time.perf_counter()
    try:
        with sync_playwright() as playwright:
            launch_args = [
                "--allow-file-access-from-files",
                "--disable-dev-shm-usage",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--no-proxy-server",
                "--proxy-bypass-list=<-loopback>",
            ]
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=chromium_executable,
                args=launch_args,
            )
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            page.add_init_script(
                """
                window.__mdstatsWebGLContextLost = false;
                document.addEventListener('webglcontextlost', function(event) {
                    window.__mdstatsWebGLContextLost = true;
                    event.preventDefault();
                }, true);
                """
            )
            with _loopback_server(resolved) as artifact_url:
                result["artifact_url_scheme"] = "http-loopback"
                try:
                    page.goto(artifact_url, wait_until="load", timeout=timeout_ms)
                    result["navigation_mode"] = "http-loopback"
                except Exception as navigation_error:
                    result["loopback_navigation_error"] = (
                        f"{type(navigation_error).__name__}: {navigation_error}"
                    )
                    if resolved.stat().st_size > int(max_direct_injection_bytes):
                        raise RuntimeError(
                            "Loopback navigation was blocked and the artifact exceeds "
                            "the bounded direct-injection limit: "
                            f"{resolved.stat().st_size}>{int(max_direct_injection_bytes)} bytes."
                        ) from navigation_error
                    page.close()
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)
                    page.add_init_script(
                        """
                        window.__mdstatsWebGLContextLost = false;
                        document.addEventListener('webglcontextlost', function(event) {
                            window.__mdstatsWebGLContextLost = true;
                            event.preventDefault();
                        }, true);
                        """
                    )
                    html_text = resolved.read_text(encoding="utf-8")
                    page.set_content(html_text, wait_until="load", timeout=timeout_ms)
                    del html_text
                    result["navigation_mode"] = "set-content-fallback"
            page.wait_for_function(
                """
                () => {
                  const gd = document.querySelector('.plotly-graph-div');
                  return Boolean(gd && gd.data && gd._fullLayout);
                }
                """,
                timeout=timeout_ms,
            )
            page.evaluate(
                """async () => {
                  await new Promise(resolve => requestAnimationFrame(
                    () => requestAnimationFrame(resolve)
                  ));
                }"""
            )
            first_frame = time.perf_counter() - start
            browser_info = page.evaluate(
                """() => {
                  const canvas = document.createElement('canvas');
                  const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                  let vendor = null;
                  let renderer = null;
                  if (gl) {
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    vendor = ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
                    renderer = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
                  }
                  return {
                    user_agent: navigator.userAgent,
                    webgl_vendor: vendor,
                    webgl_renderer: renderer,
                    device_memory_gib: navigator.deviceMemory || null,
                    hardware_concurrency: navigator.hardwareConcurrency || null,
                  };
                }"""
            )
            browser_info["version"] = browser.version
            result["browser"] = browser_info

            metrics = page.evaluate(
                """async ({orbitFrames}) => {
                  const gd = document.querySelector('.plotly-graph-div');
                  const traceCount = gd.data.length;
                  const meshTraceCount = gd.data.filter(t => t.type === 'mesh3d').length;
                  const scatter3dTraceCount = gd.data.filter(t => t.type === 'scatter3d').length;
                  const started = performance.now();
                  for (let i = 0; i < orbitFrames; ++i) {
                    const theta = 2 * Math.PI * i / orbitFrames;
                    const eye = {x: 1.8 * Math.cos(theta), y: 1.8 * Math.sin(theta), z: 1.15};
                    await Plotly.relayout(gd, {'scene.camera.eye': eye});
                    await new Promise(resolve => requestAnimationFrame(resolve));
                  }
                  const orbitSeconds = (performance.now() - started) / 1000.0;
                  let toggleSeconds = null;
                  if (traceCount > 0) {
                    const target = Math.max(0, gd.data.findIndex(t => t.type === 'mesh3d'));
                    const toggleStart = performance.now();
                    await Plotly.restyle(gd, {visible: 'legendonly'}, [target]);
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    await Plotly.restyle(gd, {visible: true}, [target]);
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    toggleSeconds = (performance.now() - toggleStart) / 1000.0;
                  }
                  return {
                    trace_count: traceCount,
                    mesh_trace_count: meshTraceCount,
                    scatter3d_trace_count: scatter3dTraceCount,
                    camera_orbit_seconds: orbitSeconds,
                    camera_orbit_fps: orbitFrames / Math.max(orbitSeconds, 1e-12),
                    trace_toggle_seconds: toggleSeconds,
                    webgl_context_lost: Boolean(window.__mdstatsWebGLContextLost),
                    js_heap_used_bytes: performance.memory ? performance.memory.usedJSHeapSize : null,
                    js_heap_total_bytes: performance.memory ? performance.memory.totalJSHeapSize : null,
                  };
                }""",
                {"orbitFrames": int(orbit_frames)},
            )
            metrics["first_complete_frame_seconds"] = first_frame
            result["metrics"] = metrics
            result["status"] = "passed" if not metrics["webgl_context_lost"] else "failed"
            context.close()
            browser.close()
    except Exception as error:  # benchmark must preserve diagnostics
        result["error"] = f"{type(error).__name__}: {error}"
        result["metrics"]["elapsed_before_failure_seconds"] = time.perf_counter() - start
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--chromium-executable", default="/usr/bin/chromium")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--orbit-frames", type=int, default=24)
    parser.add_argument(
        "--max-direct-injection-bytes",
        type=int,
        default=64 * 1024**2,
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(__file__).with_name("density_browser_validation.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(__file__).with_name("density_browser_validation.md"),
    )
    args = parser.parse_args()
    result = validate_html(
        args.html,
        chromium_executable=args.chromium_executable,
        timeout_seconds=args.timeout_seconds,
        orbit_frames=args.orbit_frames,
        max_direct_injection_bytes=args.max_direct_injection_bytes,
    )
    result["acceptance"] = evaluate_browser_acceptance(
        result, policy=BrowserAcceptancePolicy()
    ).to_json_dict()
    args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.markdown_output.write_text(_markdown(result))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
