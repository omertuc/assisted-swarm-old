#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Service endpoint should look something like http://192.168.39.239:30478/
echo Speaking to service at $SERVICE_ENDPOINT

# Install utilities this machine might be missing
sudo dnf install -y $(cat $SCRIPT_DIR/../dnf-dependencies.txt)

# Make sure the pull secret is configured for podman
PULL_SECRET=$(oc get secret -n swarm-1 swarm-1-pull -ojson | jq '.data.".dockerconfigjson"' -r | base64 -d)
sudo mkdir -p /root/.docker
sudo tee /root/.docker/config.json >/dev/null <<< $PULL_SECRET

# Kill previously running agents / step containers / next_step_runners
sudo killall agent || true
sudo podman ps -q | xargs sudo podman kill || true

# Fetch the ignition file of some arbitrary infraenv
set +e
arbitrary_infraenv=$(./list_infraenvs.sh | head -1)
export IGNITION=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${arbitrary_infraenv}/downloads/files?file_name=discovery.ign")
if [[ "$IGNITION" == "" ]]; then
  echo "Failed to fetch ignition file"
  exit 1
fi
set -e

# Create some files the agent expects to exist
sudo cp $SCRIPT_DIR/swarm-installer /usr/local/bin/swarm-installer
sudo mkdir -p /opt/openshift/
sudo touch /opt/openshift/.bootkube.done
sudo touch /opt/openshift/master.ign

# Copy service ca file from ignition, because the agent expects it to be there
CA_CERT_PATH="/etc/assisted-service/service-ca-cert.crt"
sudo mkdir -p $(dirname ${CA_CERT_PATH})
jq '.storage.files[] | select(.path == "'$CA_CERT_PATH'").contents.source' -r <<< $IGNITION | cut -d',' -f2- | base64 -d | sudo tee $CA_CERT_PATH > /dev/null

# Extract the agent binary copy command from the ignition file, and run it to
# place the agent binary on this host
export COPY_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | grep "podman run" | cut -d'=' -f2-)
sudo $COPY_CMD

# Run agents, 10 at a time
if [[ $MODE == "infraenv" ]]; then
    throttle=10
    for infra_env in $(./list_infraenvs.sh); do 
        INFRA_ENV_ID=${infra_env} ./launch_from_infraenv.sh &
        throttle=$((throttle - 1))
        echo $throttle
        if [[ $throttle == "0" ]]; then
            sleep 10;
            throttle=10
        fi
    done
elif [[ $MODE == "bmh" ]]; then
    throttle=10
    for bmh in $(./list_bmhs.sh); do 
        BMH=${bmh} ./launch_from_bmh.sh &
        throttle=$((throttle - 1))
        echo $throttle
        if [[ $throttle == "0" ]]; then
            sleep 10;
            throttle=10
        fi
    done
else
    echo "Unsupported mode MODE=$MODE"
    exit 1
fi
