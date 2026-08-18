# LD9-V0 browser validation

- Status: **passed**
- Input: `/mnt/data/mdstats_0_19_61a0_ld9_v3_browser_scene_self_contained.html`
- Input bytes: 26,233,233
- Chromium: `144.0.7559.96`
- User agent: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/144.0.0.0 Safari/537.36`
- WebGL renderer: `None`
- Plotly trace count: 28
- First complete frame: 13.39214830100002 s
- Scripted camera orbit: 27.69763416041546 frames/s
- Representative trace toggle: 0.11920000000006985 s
- WebGL context loss: False
- JavaScript heap used: 199000000

## Notes

The browser environment is part of the benchmark evidence. Headless Chromium may use SwiftShader rather than the workstation GPU; the reported WebGL renderer must therefore be retained with every result.

## Acceptance

- Renderer kind: **unavailable**
- Functional gate: **True**
- Production-default authorization: **False**
- Production violations: `['physical_webgl_required:unavailable']`
