#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

oc get bmh -A -ojson | jq '.items[] | .metadata.finalizers = []' | oc apply -f -
