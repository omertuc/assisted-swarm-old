#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

export SERVICE_ENDPOINT=http://192.168.39.73:31442

echo Running for infraenv $INFRA_ENV_ID

export IGNITION=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)

set -x 
sudo $COPY_CMD

echo $AGENT_CMD
sudo $(echo $AGENT_CMD | sed -e "s/--infra-env-id/--host-id $(uuid) --infra-env-id/")
