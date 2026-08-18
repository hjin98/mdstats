# mdstats 0.20.200a0 - TARGET-DATA2B-FEAS1

- Implement the first optimized multi-view roadmap gate, TARGET-DATA2B-FEAS1.
- Add exact self-excluded and own-correlation-unit-excluded support diagnostics for every TARGET-DATA2B family.
- Add FP64 singleton-gain cardinality lower bounds plus hard protected-stratum, extent, and correlation-interval obligation bounds.
- Treat TARGET-DATA2A development-interval count as an exact lower bound because the intervals are disjoint and current selection reserves one representative per interval.
- Add authenticated FEAS1 policy/report schemas, serialization validation, public API exports, and campaign `prepare` persistence/restart reuse.
- Keep TARGET-DATA2C revision-64 v4 selector behavior unchanged; FEAS1 is diagnostic-only in this release.
- Advance architecture to revision 67 / dependency-graph schema 49.
