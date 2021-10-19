#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

. ./make-account.sh

oc get namespace -A -oname | cut -d'/' -f2 | grep swarm | while read -r NAMESPACE ; do
    oc get baremetalhost -o name -n $NAMESPACE | cut -d'/' -f2 | while read -r BMH; do
        export NAMESPACE
        export BMH
        ./set_bmh_status.sh &
    done 
done 


