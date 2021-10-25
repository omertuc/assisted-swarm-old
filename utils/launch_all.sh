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
sudo killall next_step_runner || true
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

. $SCRIPT_DIR/make-account.sh

$SCRIPT_DIR/ready_all_bmh.sh

# Create dir for swarm storage
export STORAGE_DIR=~/.swarm/storage
mkdir -p $STORAGE_DIR

# Try to delete old tmpfs in that dir 
sudo umount $STORAGE_DIR/**/overlay || true
sudo rm -rf $STORAGE_DIR/*
sudo umount $STORAGE_DIR || true

# Create tmpfs on the storage dir
sudo mount -t tmpfs -o size=64000m tmpfs $STORAGE_DIR

# Create a shared storage directory for swarm agents to share their images/overlay
mkdir -p $STORAGE_DIR/shared
export SHARED_STORAGE=$(mktemp --dry-run --tmpdir=${STORAGE_DIR}/shared)

# Pull all known images into the shared storage directory in advance
export SHARED_STORAGE_CONF=$(mktemp --dry-run --tmpdir=${STORAGE_DIR})
< /etc/containers/storage.conf tomlq '.storage.graphroot = "'${SHARED_STORAGE}'"' --toml-output > ${SHARED_STORAGE_CONF}
curl -k ${SERVICE_ENDPOINT}/api/assisted-install/v2/component-versions | jq '
    .versions | to_entries[] | select(.key != "assisted-installer-service") | .value
' -r | xargs -L1 sudo CONTAINERS_STORAGE_CONF=${SHARED_STORAGE_CONF} podman pull 

# Run agents, 10 at a time
throttle=3
for bmh in $(./list_bmhs.sh); do 
    BMH=${bmh} ./launch_from_bmh.sh
    throttle=$((throttle - 1))
    echo $throttle
    if [[ $throttle == "0" ]]; then
        sleep 5;
        throttle=3
    fi
done
