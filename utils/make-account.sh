#!/bin/bash

# Create an admin service account so we can use its token to make API calls
oc delete serviceaccount swarm
oc delete clusterrolebinding swarm
oc create serviceaccount swarm -n default || true
oc create clusterrolebinding swarm \
    --clusterrole=cluster-admin \
    --serviceaccount=default:swarm


# Extract Token for service account
export SA_SECRET=$(oc get sa swarm -ojson | jq '.secrets[] | select(.name | test("swarm-token-[a-z0-9]{5}")).name' -r)
export TOKEN=$(oc get secret -n default ${SA_SECRET} -ojson | jq '.data.token' -r | base64 -d)

# Get API server URL
export APISERVER=$(oc whoami --show-server)

# Get CA cert because the API won't agree to talk with us without it
export CA_CERT=$(oc get secret ${SA_SECRET} -o json | jq -Mr '.data["ca.crt"]' | base64 -d)
