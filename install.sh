#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

all_swarm_namespaces=$(oc get namespaces -ojson -A | jq '.items[] | select(.metadata.name | test("swarm.*")) | .metadata.name' -r)

echo Found the following namespaces:
echo $all_swarm_namespaces

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

    while true; do 
        oc get agentclusterinstall/$namespace -n $namespace -ojson \
        | jq '.spec.networking.machineNetwork = [{"cidr": "10.5.190.36/26"}]' \
        | oc apply -f - && break
    done

done <<< $all_swarm_namespaces

