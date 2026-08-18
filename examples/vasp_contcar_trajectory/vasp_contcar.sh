#!/usr/bin/env bash

# Prevent an old CONTCAR from being archived as frame 1.
if [[ -f CONTCAR ]]; then
    mv CONTCAR CONTCAR.before_md
fi

./watch_contcar.sh velocity_frames 0.25 > contcar_watcher.log 2>&1 &
watcher_pid=$!

cleanup() {
    kill "$watcher_pid" 2>/dev/null || true
    wait "$watcher_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

srun /path/to/vasp_std

# Give the watcher time to capture the final write.
sleep 1
cleanup
trap - EXIT INT TERM
