#!/bin/bash

set -uo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

function infraenvs() {
    # Extract infra-env IDs from infraenv URLs
    oc get infraenv -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | .status.isoDownloadURL' -r \
	    | grep $@ --extended-regexp --only-matching --color=never '[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}'
}

while infraenvs -v; do
    echo "Not all infraenvs initialized:" > /dev/stderr
    oc get infraenv -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | {"url": .status.isoDownloadURL, "name": .metadata.name}' -c | grep -v --extended-regexp '[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}' | jq -C > /dev/stderr
    sleep 1
done

infraenvs
