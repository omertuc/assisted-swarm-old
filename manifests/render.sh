#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

jinja2 manifests.yaml.j2 manifests-data.example.json 
