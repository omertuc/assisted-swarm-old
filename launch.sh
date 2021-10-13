#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
echo Running for infraenv $INFRA_ENV_ID

export IGNITION=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | grep 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)

echo $IGNITION
echo $AGENT_CMD

sudo $(echo $AGENT_CMD | sed -e "s/--infra-env-id/--host-id $(uuid) --infra-env-id/")
