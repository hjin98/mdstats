# REPLAY-PERF1 cloud CPU benchmark - mdstats 0.20.234a0

Date: 2026-08-17  
Architecture revision: 101  
Active foundation: MACE-MPA-0 medium (`75428afe...fb638`); execution contract is MACE-MH-1 compatible.

## Authority

Supplied replay source: 12,000 frames, SHA-256 `187eed42fb2d6cf5e7e745ffed0ce34541e92c6a35ec9e654520cd3c7198403c`. The source artifact digest is `9f43677d6100cea85f6de287fe1dd739322609fd82cbeb320e46f9434ce90688`; the REPLAY-PERF1 byte index digest is `ce6c678ad556cff63be8ee75754d87cba2b3d08e80f544c5983fe4498dc0c5e1`.

## Results

| Workload | Untouched 0.20.233a0 | 0.20.234a0 | Speedup |
|---|---:|---:|---:|
| Monitor-only true-label view (2,000/12,000 frames) | 9.139 s | 3.012 s | 3.03x |
| Full-source parse + geometry identity bookkeeping | 7.642 s | 6.423 s | 1.19x |
| Full train+monitor true-label views | 15.676 s | 14.348 s | 1.09x |

The one-time index build measured 0.451 s and an authenticated persisted index hit 0.071 s.

Monitor output is byte-identical between control/current (`cc0f9b308becd5c027a2adc64fc251808323e19c217412d82ea3d50b3deab2cf`) and preserves logical digest `633aae8a6deb1a3d857880f3eecd9bb40dbaedba8357a13944184c1bafbf1114`. Full train materialization is likewise byte-identical (`e6977082593a5b5610292e13ae49df7afbdbb7744ea9fe496952952474636f8c`) with logical digest `8d7a29c35443cd8a8e7b2142157dce7c9804c8137d4a42e824edef9e42240901`.

## Parser decision

Direct tests of Python-threaded ASE ExtXYZ chunk parsing were slower than a single parser lane on this CPU. REPLAY-PERF1 therefore uses deterministic serial chunk parsing and obtains its gain from direct indexed seeks and reuse of authenticated source-order geometry identities rather than from executor overhead.

## Acceptance

PASS. Source, split, true-label, pseudo-label, prediction-cache, and view scientific authority are unchanged. Cache corruption/source mutation rebuild safely. Next gate: `CAMPAIGN-PERF-QUAL1`.
