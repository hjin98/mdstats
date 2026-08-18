# LD8-S4 production gate

- Aggregate scientific time: `80.515 s`
- Speedup over LD7: `4.22x`
- Gate passed: `True`

| Field | Grid | Scientific | HDR | Blocks | Nodes | D/F tiles | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| Na density | 540x540x540 | 11.189 s | 0.101 s | 1322 | 1728706 | 16/99 | 0.973 GiB |
| Si density | 1038x1038x1038 | 11.172 s | 0.114 s | 1381 | 1833591 | 18/90 | 0.969 GiB |
| Al density | 1037x1037x1037 | 12.658 s | 0.120 s | 1432 | 1952525 | 19/100 | 0.987 GiB |
| O density | 646x646x646 | 45.496 s | 0.556 s | 5625 | 7274190 | 99/402 | 1.218 GiB |

## Gate checks

- `all_four_species_present`: `True`
- `aggregate_scientific_seconds_le_120`: `True`
- `aggregate_speedup_ge_3`: `True`
- `all_channel_peak_rss_le_1_5_gib`: `True`
- `all_integrals_exact`: `True`
- `all_production_backend`: `True`
- `no_fallback`: `True`
- `three_hdr_levels_each`: `True`
