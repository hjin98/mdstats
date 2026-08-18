# LD9-V0 browser validation

- Status: **passed**
- Input: `/mnt/data/na_lta_300K_all_species_density_framework_trajectories.html`
- Input bytes: 34,758,038
- Chromium: `144.0.7559.96`
- User agent: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/144.0.0.0 Safari/537.36`
- WebGL renderer: `None`
- Plotly trace count: 28
- First complete frame: 15.32253629600018 s
- Scripted camera orbit: 17.46724890829694 frames/s
- Representative trace toggle: 0.16709999999962746 s
- WebGL context loss: False
- JavaScript heap used: 91700000

## Notes

The browser environment is part of the benchmark evidence. Headless Chromium may use SwiftShader rather than the workstation GPU; the reported WebGL renderer must therefore be retained with every result.

## Acceptance

- Renderer kind: **unavailable**
- Functional gate: **False**
- Production-default authorization: **False**
- Production violations: `['first_complete_frame_exceeded', 'camera_orbit_fps_below_minimum', 'physical_webgl_required:unavailable']`
