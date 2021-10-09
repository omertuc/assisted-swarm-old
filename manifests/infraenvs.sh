#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Extract infra-env IDs from infraenv URLs
oc get infraenv -A -ojson | jq '.items[].status.isoDownloadURL' -r |\
    sed -e 's/infra-envs/#/' |\
    sed -e 's/downloads/#/' |\
    cut -d'#' -f2 |\
    cut -d'/' -f2
