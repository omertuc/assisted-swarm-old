#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

./render.sh | oc delete --force --grace-period 0 -f -
