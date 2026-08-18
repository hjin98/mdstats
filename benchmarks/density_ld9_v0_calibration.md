# LD9-V0 rendering calibration

- Raw density faces: 3,184,902
- Raw density vertices: 1,599,109
- Complete Plotly traces: 173
- Self-contained HTML: 177.70 MiB
- Hard face limit: 300,000
- Hard vertex limit: 200,000
- Hard trace limit: 64
- Hard HTML limit: 40.00 MiB
- Existing artifact passes browser budget: **False**

## Required reduction

- Face reduction factor: 10.616x
- Vertex reduction factor: 7.996x
- HTML reduction factor: 4.443x

## Browser evidence

- Status: **failed**
- First complete frame: None s
- Camera orbit: None frames/s
- Trace toggle: None s
- WebGL context loss: None

## Violations

- `final_density_faces=3184902>300000`
- `final_density_vertices=1599109>200000`
- `plotly_traces=173>64`
- `final_html_bytes=186335598>41943040`
