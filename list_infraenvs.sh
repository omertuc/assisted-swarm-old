#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

function infraenvs() {
    # Extract infra-env IDs from infraenv URLs
    oc get infraenv -A -ojson | jq '.items[].status.isoDownloadURL' -r |\
                    sed -e 's/infra-envs/#/' |\
                    sed -e 's/downloads/#/' |\
                    cut -d'#' -f2 |\
                    cut -d'/' -f2
}

function all_available() {
    while read -r infra_env_id; do
        if [[ $infra_env_id == "null" ]]; then
            return 1
        fi
    done <<< $(infraenvs)
}

while ! all_available; do
    echo "Not all infraenvs initialized"
    sleep 1
done

infraenvs
