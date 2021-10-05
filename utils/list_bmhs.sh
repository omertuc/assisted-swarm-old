#!/bin/bash

set -uo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

function check_bmh() {
    # Extract infra-env IDs from infraenv URLs
    oc get baremetalhost -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | .spec.image.url' -r \
	    | grep --invert-match --extended-regexp --only-matching --color=never '[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}'
}

while check_bmh; do
    echo "Not all baremetalhosts have URL:" > /dev/stderr
    oc get baremetalhost -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | {"url": .spec.image.url, "name": .metadata.name}' -c | grep -v --extended-regexp '[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}' | jq -C -c '.name + " has no URL"' | sort -V > /dev/stderr
    sleep 1
done

oc get bmh -A -oname | grep swarm | cut -d'/' -f2
