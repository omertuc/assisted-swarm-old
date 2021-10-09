#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

for infra_env in $(./list_infraenvs.sh); do 
    INFRA_ENV_ID=${infra_env} ./launch.sh
done
