#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

function infraenvs() {
    # Extract infra-env IDs from infraenv URLs
    oc get infraenv -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | .status.isoDownloadURL' -r \
	    | grep --extended-regexp --only-matching --color=never '[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}' || true 
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
