#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

all_swarm_namespaces=$(oc get namespaces -ojson -A | jq '.items[] | select(.metadata.name | test("swarm.*")) | .metadata.name' -r)
while read -r namespace; do 
    echo Preparing $namespace for installation
    agent_name=$(oc get agent -n $namespace -ojson | jq '.items[].metadata.name' -r)

    oc patch agent/$agent_name -n $namespace --type='json' --patch '[{
            "op": "add",
            "path": "/spec/approved",
            "value": true
        }]'

    oc patch agent/$agent_name -n $namespace --type='json' --patch '[{
            "op": "add",
            "path": "/spec/role",
            "value": master
        }]'

    oc patch agent/$agent_name -n $namespace --type='json' --patch '[{
            "op": "add",
            "path": "/spec/clusterDeploymentName",
            "value": {
              "name": "'$namespace'",
              "namespace": "'$namespace'"
            }
        }]
    '

    oc get agentclusterinstall/$namespace -n $namespace -ojson \
        | jq '.spec.networking.machineNetwork = [{"cidr": "192.168.39.0/24"}]' \
        | oc apply -f -
done <<< $all_swarm_namespaces

