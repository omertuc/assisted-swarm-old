#!/bin/bash


set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# For now assume that the name of the namespace is the same name as the BMH
export NAMESPACE=${BMH}

echo Running for BMH $BMH

function get_uuid() {
    pattern='[[:xdigit:]]{8}(-[[:xdigit:]]{4}){3}-[[:xdigit:]]{12}'
    input=$(cat)
    if grep --extended-regexp --quiet $pattern <<< $input; then
        grep --extended-regexp --only-matching --color=never $pattern <<< $input
    fi
}

while true; do
    image_url=$(oc get baremetalhost -n ${NAMESPACE} ${BMH} -ojson  | jq '.spec.image.url' -r)
    get_uuid <<< $image_url && break;
    echo "Waiting for ${BMH} BMH to have an image URL"
    sleep 5
done

# Perform a fake download to test image service traffic 
# curl -k $(oc get baremetalhost $BMH -n $NAMESPACE -ojson | jq .spec.image.url -r) -o /dev/null

# Pretend the BMH is now provisioned
WANTED_STATE=provisioned NAMESPACE=${NAMESPACE} ${SCRIPT_DIR}/set_bmh_status.sh

BMH_MAC=$(oc get baremetalhost -n ${NAMESPACE} ${BMH} -ojson  | jq '.spec.bootMACAddress' -r)

# Run fake agent
INFRA_ENV_ID=$(get_uuid <<< $image_url) 
export IGNITION=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | grep 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
echo $IGNITION
echo $AGENT_CMD

# Create a graphroot for this particular swarm hosthost
container_storage=$(mktemp --dry-run --tmpdir=${STORAGE_DIR})
container_storage_config=$(mktemp --dry-run --tmpdir=${STORAGE_DIR})
sudo mkdir -p $container_storage

# Generate container storage config for this host, using shared storage for all swarm agents
# and graphroot just for this host
< /etc/containers/storage.conf tomlq ' .
    | .storage.options.additionalimagestores += ["'${SHARED_STORAGE}'"] 
    | .storage.graphroot = "'$container_storage'"
' --toml-output > ${container_storage_config}

container_config=$(mktemp --dry-run --tmpdir=${STORAGE_DIR})

DRY_FAKE_REBOOT_MARKER_PATH=$(mktemp --dry-run --tmpdir=${STORAGE_DIR})

# Generate container config for this host, adjusting it to automatically propagate some environment variables from host to containers
< /usr/share/containers/containers.conf tomlq ' .
    | .containers.env += [
        "CONTAINERS_CONF",
        "CONTAINERS_STORAGE_CONF",
        "DRY_ENABLE",
        "DRY_HOST_ID",
        "DRY_MAC_ADDRESS",
        "PULL_SECRET_TOKEN"
        "DRY_FAKE_REBOOT_MARKER_PATH"
    ]
' --toml-output > ${container_config}

sudo \
    CONTAINERS_CONF=${container_config} \
    CONTAINERS_STORAGE_CONF=${container_storage_config} \
    PULL_SECRET_TOKEN=${PULL_SECRET_TOKEN} \
    DRY_ENABLE=true \
    DRY_HOST_ID=$(uuid) \
    DRY_MAC_ADDRESS=${BMH_MAC} \
    DRY_FAKE_REBOOT_MARKER_PATH=${DRY_FAKE_REBOOT_MARKER_PATH} \
    $AGENT_CMD &

function launch_controller {
    while true; do
        AGENT_CLUSTER_INSTALL=${NAMESPACE}
        INFRAENV_ID=$(oc get agentclusterinstall -n ${NAMESPACE} ${AGENT_CLUSTER_INSTALL} -ojson  | jq '.spec.clusterMetadata.infraID' -r)
        if [ -n "$INFRAENV_ID" ]; then
            break;
        fi
        echo "Waiting for infraenv ID for ${AGENT_CLUSTER_INSTALL}"
        sleep 5
    done

    sudo podman \
        CONTAINERS_CONF=${container_config} \
        CONTAINERS_STORAGE_CONF=${container_storage_config} \
        -e CLUSTER_ID=${INFRAENV_ID} \
        -e DRY_ENALBED=true \
        -e INVENTORY_URL=${SERVICE_ENDPOINT} \
        -e PULL_SECRET_TOKEN=${PULL_SECRET_TOKEN} \
        -e OPENSHIFT_VERSION=4.8 \
        -e DRY_FAKE_REBOOT_MARKER_PATH=${DRY_FAKE_REBOOT_MARKER_PATH} \
        -e SKIP_CERT_VERIFICATION=true \
        -e HIGH_AVAILABILITY_MODE=false \
        -e CHECK_CLUSTER_VERSION=true \
        -e DRY_HOSTNAME=$(hostname) \
        -e DRY_MCS_ACCESS_IP=10.5.190.36 \
        $CONTROLLER_IMAGE assisted-installer-controller
}

launch_controller &
