#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

export SERVICE_ENDPOINT=http://192.168.39.239:30478

arbitrary_infraenv=$(./list_infraenvs.sh | head -1)

PULL_SECRET=$(oc get secret -n swarm-1 swarm-1 -ojson | jq '.data.".dockerconfigjson"' -r | base64 -d)
sudo mkdir -p /root/.docker
sudo tee /root/.docker/config.json >/dev/null <<< $PULL_SECRET

sudo killall agent || true
sudo podman ps -q | xargs sudo podman kill || true

export PULL_SECRET=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${arbitrary_infraenv}/downloads/files?file_name=discovery.ign")
export IGNITION=$(curl -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${arbitrary_infraenv}/downloads/files?file_name=discovery.ign")
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)
sudo $COPY_CMD

for infra_env in $(./list_infraenvs.sh); do 
    INFRA_ENV_ID=${infra_env} ./launch.sh &
done
