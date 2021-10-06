#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

pushd agent
git fetch -a
git reset --hard origin/master
git apply ../agent-patches/*
sudo make -o unit-test build-image
sudo podman tag quay.io/ocpmetal/assisted-installer-agent:latest quay.io/otuchfel/assisted-installer-agent:swarm
sudo podman push quay.io/otuchfel/assisted-installer-agent:swarm
git reset --hard origin/master
popd

export SERVICE_ENDPOINT=http://192.168.39.73:31442
export INFRA_ENV_ID=b7b9f297-0475-4dcb-b3ab-338b4f5ce383

export IGNITION=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)

echo $AGENT_CMD

sudo $COPY_CMD
sudo $AGENT_CMD
