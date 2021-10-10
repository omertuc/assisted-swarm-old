#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

if [[ $(jq .pull_secret_b64 manifests-data.example.json -r) == "" ]]; then
    echo "Please set pull_secret_b64 in manifests-data.example.json" > /dev/stderr
    exit 1
fi

jinja2 manifests.yaml.j2 manifests-data.example.json 
