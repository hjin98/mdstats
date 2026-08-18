#!/usr/bin/env bash
#
# watch_contcar.sh
#
# Poll CONTCAR and save each distinct, completely written version.
#
# Usage:
#   ./watch_contcar.sh [output_directory] [poll_interval]
#
# Example:
#   ./watch_contcar.sh velocity_frames 0.25
#

set -u

source_file="CONTCAR"
output_dir="${1:-velocity_frames}"
poll_interval="${2:-0.25}"

mkdir -p "$output_dir"

step=0
previous_file=""
last_observed_signature=""

echo "Watching $source_file"
echo "Output directory: $output_dir"
echo "Polling interval: ${poll_interval} s"

while true; do
    if [[ ! -s "$source_file" ]]; then
        sleep "$poll_interval"
        continue
    fi

    # GNU/Linux stat. %y includes sub-second modification time.
    signature_before=$(stat -c '%y:%s' "$source_file" 2>/dev/null) || {
        sleep "$poll_interval"
        continue
    }

    # Skip files that have not changed since the previous observation.
    if [[ "$signature_before" == "$last_observed_signature" ]]; then
        sleep "$poll_interval"
        continue
    fi

    # Wait briefly, then verify that the file is no longer changing.
    sleep "$poll_interval"

    signature_stable=$(stat -c '%y:%s' "$source_file" 2>/dev/null) || continue

    if [[ "$signature_before" != "$signature_stable" ]]; then
        # VASP is probably still writing the file.
        continue
    fi

    temporary_file="$output_dir/.CONTCAR.copy.$$"

    # Copy the candidate snapshot.
    cp "$source_file" "$temporary_file" 2>/dev/null || {
        rm -f "$temporary_file"
        continue
    }

    # Make sure the source did not change while cp was reading it.
    signature_after=$(stat -c '%y:%s' "$source_file" 2>/dev/null) || {
        rm -f "$temporary_file"
        continue
    }

    if [[ "$signature_stable" != "$signature_after" ]]; then
        rm -f "$temporary_file"
        continue
    fi

    last_observed_signature="$signature_after"

    # Avoid saving the same physical state more than once.
    if [[ -n "$previous_file" ]] &&
       cmp -s "$temporary_file" "$previous_file"; then
        rm -f "$temporary_file"
        sleep "$poll_interval"
        continue
    fi

    step=$((step + 1))
    output_file=$(printf '%s/CONTCAR.%08d' "$output_dir" "$step")

    mv "$temporary_file" "$output_file"
    previous_file="$output_file"

    echo "Saved $output_file"

    sleep "$poll_interval"
done

