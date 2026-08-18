# mdstats 0.20.76a0 patch notes

This release fixes a process-supervision leak in long-running production MACE training. It does not change prepared scientific artifacts, optimizer settings, checkpoints, or completed-run identities.

## Root cause

The campaign process launched `mdstats-mace-train` in a dedicated process group. The precision wrapper then launched the real MACE Python process in a second detached process group so it could terminate MACE safely after validating a completed model artifact. When the campaign interrupted the wrapper, only the outer wrapper group received the signal; the detached MACE process and its CUDA context could continue running.

## Corrected supervision

- The precision wrapper installs forwarding handlers for SIGINT, SIGTERM, SIGHUP, and SIGQUIT.
- The first signal terminates the complete nested MACE process group, waits through a bounded grace period, and escalates to SIGKILL if required.
- A repeated signal forces immediate nested-group termination.
- Linux `PR_SET_PDEATHSIG` protection requests SIGTERM if either supervising parent disappears unexpectedly.
- The campaign interruption guard now maps SIGTERM and SIGHUP to the same durable cancellation event used for Ctrl-C.
- The campaign does not return until active worker futures have finished writing interrupted execution records.

## Restart behavior

An interrupted run retains its current-policy checkpoints. The next `train` invocation uses `--restart_latest`; completed runs remain checksum-verified and are not recalculated. No `prepare` or `preflight` rerun is required.
