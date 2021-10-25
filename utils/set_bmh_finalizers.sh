#!/bin/bash

# We can't set resource .status with regular tools like oc, kubectl - we must use
# the API. So this script requires you to create a service account, give it a role, 
# then set $APISERVER and $TOKEN and $CA_CERT so the API can be queried.
# You also need to set $NAMESPACE and $BMH to the values of the BMH you want to modify
set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

# Get the current CR, set its status
WITH_STATUS=$(oc get -n $NAMESPACE baremetalhost $BMH -ojson | jq '.status = {} | .spec = {} | .metadata.finalizers = []' -c)

# PUT into the status subresource. This ignores everything that's non-status
curl -X PUT $APISERVER/apis/metal3.io/v1alpha1/namespaces/${NAMESPACE}/baremetalhosts/${BMH}/finalize \
    -d $WITH_STATUS \
    --header "Authorization: Bearer $TOKEN" \
    --header "Content-Type: application/json" \
    --cacert <(cat <<< $CA_CERT)
