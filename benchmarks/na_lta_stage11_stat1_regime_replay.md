# Na-LTA Stage 11E-STAT1 real-source replay

- source: supplied 1,500-step `vasprun.xml`
- STAT0 outcome: `degraded_quality`
- NVE drift: `-0.00121757378 eV/(atom ps)`
- STAT1 catalog status: `accepted`
- selected scientific regimes: `['regime_000']`
- change-point status: `none`
- thermalization evidence: `no_detected_transient`
- stationarity evidence: `supported`
- production interval status: `scientific_candidate`
- quality signature: `63c1e2ffadd31452d75cf8df9560c0e88a0c16bc712529996f8c5ef2fa5de9d5`
- catalog signature: `5b8e086ccb9b22d2fc695ed5cae8720e2f77db98930e1ce3d54dcbe04aeaaf31`

The full source shows no detected heating transient. Temperature, kinetic-energy, and potential-energy block trends do not jointly exceed the revision-50 stationarity significance and effect-size gates, so the full source is retained as a scientific production candidate. The independently recorded total-energy drift remains nonstationary and keeps STAT0 at `degraded_quality`; STAT1 does not repair or hide it.
