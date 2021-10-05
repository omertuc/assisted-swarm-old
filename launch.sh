#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

pushd agent
git reset --hard origin/master
git pull
git apply ../agent-patches/*
skipper make -o unit-test build-image
git reset --hard origin/master
popd

export SERVICE_ENDPOINT=http://192.168.39.73:31442
export INFRA_ENV_ID=5daa967c-aa76-43db-ad10-607098dee4ae

export IGNITION=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)

echo $AGENT_CMD

sudo $COPY_CMD
sudo $AGENT_CMD
