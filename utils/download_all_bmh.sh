#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

oc get namespace -A -oname | cut -d'/' -f2 | grep swarm | while read -r NAMESPACE ; do
    oc get baremetalhost -o name -n $NAMESPACE | cut -d'/' -f2 | while read -r BMH; do
        curl -s -k $(oc get baremetalhost $BMH -n $NAMESPACE -ojson | jq .spec.image.url -r) -o /dev/null &
    done 
done 

wait


