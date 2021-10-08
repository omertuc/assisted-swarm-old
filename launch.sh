#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

pushd agent
git fetch -a
git reset --hard origin/master
git apply ../agent-patches/*
sudo make -o unit-test build-image
sudo podman push quay.io/otuchfel/assisted-installer-agent:swarm
git reset --hard origin/master
popd

export SERVICE_ENDPOINT=http://192.168.39.73:31442
export INFRA_ENV_ID=4f5b713a-d897-41a1-b5ee-d0a8579b22a2

export IGNITION=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)

set -x 
sudo $COPY_CMD

echo $AGENT_CMD
echo sudo $(echo $AGENT_CMD | sed -e "s/--infra-env-id/--host-id $(uuid) --infra-env-id/")
