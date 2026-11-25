#!/usr/bin/env bash
set -euo pipefail

docker_bin=${DOCKER_BIN:-docker}

if ! command -v "$docker_bin" >/dev/null 2>&1; then
    printf 'capture-runtime-logs: Docker executable not found: %s\n' "$docker_bin" >&2
    exit 1
fi

capture_container_logs() {
    local container_id=$1
    local short_id=${container_id:0:12}

    "$docker_bin" logs --timestamps --follow "$container_id" 2>&1 |
        while IFS= read -r line; do
            printf '[%s] %s\n' "$short_id" "$line"
        done
}

printf 'Monitoring OpenHands conversation container logs.\n'
"$docker_bin" events \
    --filter type=container \
    --filter event=start \
    --filter label=ai.openhands.runtime-owner \
    --format '{{.Actor.ID}}' |
    while IFS= read -r container_id; do
        [[ -n "$container_id" ]] || continue
        capture_container_logs "$container_id" &
    done
