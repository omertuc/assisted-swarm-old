#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

oc get bmh -A -ojson | jq '.items[] | select(.metadata.namespace | test("swarm-")) | .metadata.finalizers = []' | oc apply -f -
