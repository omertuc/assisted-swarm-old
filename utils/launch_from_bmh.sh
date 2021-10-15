#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# For now assume that the name of the namespace is the same name as the BMH
NAMESPACE=${BMH}

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
    get_uuid <<< $image_url || break;
    echo "Waiting for ${BMH} BMH to have an image URL"
    sleep 5
done

# Perform a fake download to test image service traffic
curl -s -k $(oc get baremetalhost $BMH -n $NAMESPACE -ojson | jq .spec.image.url -r) -o /dev/null

# Pretend the BMH is now provisioned
WANTED_STATE=provisioned ${SCRIPT_DIR}/set_bmh_status.sh

# Run fake agent
INFRA_ENV_ID=$(get_uuid <<< $image_url) 
export IGNITION=$(curl -k -s "${SERVICE_ENDPOINT}/api/assisted-install/v2/infra-envs/${INFRA_ENV_ID}/downloads/files?file_name=discovery.ign")
export AGENT_CMD=$(<<< $IGNITION jq '.systemd.units[].contents' -r | grep 'ExecStart=/usr/local/bin/agent' | cut -d'=' -f2-)
echo $IGNITION
echo $AGENT_CMD
sudo $(echo $AGENT_CMD | sed -e "s/--infra-env-id/--host-id $(uuid) --infra-env-id/")
