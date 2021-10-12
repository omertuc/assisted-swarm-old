#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Service endpoint should look something like http://192.168.39.239:30478
echo Speaking to service at $SERVICE_ENDPOINT

arbitrary_infraenv=$(./list_infraenvs.sh | head -1)

PULL_SECRET=$(oc get secret -n swarm-1 swarm-1 -ojson | jq '.data.".dockerconfigjson"' -r | base64 -d)
sudo mkdir -p /root/.docker
sudo tee /root/.docker/config.json >/dev/null <<< $PULL_SECRET

sudo killall agent || true
sudo podman ps -q | xargs sudo podman kill || true

sudo cp $SCRIPT_DIR/swarm-installer /usr/local/bin/swarm-installer
sudo touch /opt/openshift/.bootkube.done

export PULL_SECRET=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${arbitrary_infraenv}/downloads/files?file_name=discovery.ign")
export IGNITION=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${arbitrary_infraenv}/downloads/files?file_name=discovery.ign")

CA_CERT_PATH="/etc/assisted-service/service-ca-cert.crt"
sudo mkdir -p $(dirname ${CA_CERT_PATH})
jq '.storage.files[] | select(.path == "'$CA_CERT_PATH'").contents.source' -r <<< $IGNITION | cut -d',' -f2- | base64 -d | sudo tee $CA_CERT_PATH > /dev/null

if [[ "$IGNITION" == "" ]]; then
  echo "Failed to fetch ignition file"
  exit 1
fi

export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | rg "podman run" | cut -d'=' -f2-)
sudo $COPY_CMD

for infra_env in $(./list_infraenvs.sh); do 
    INFRA_ENV_ID=${infra_env} ./launch.sh &
done
