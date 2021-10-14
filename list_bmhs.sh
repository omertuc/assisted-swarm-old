#!/bin/bash

set -uo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

oc get bmh -A -oname | grep swarm | cut -d'/' -f2
