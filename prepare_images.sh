#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "Pushing to quay user ${QUAY_ACCOUNT}"

pushd agent
git fetch -a
git reset --hard origin/master
git apply ../agent-patches/*
make -o unit-test build-image
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer-agent:swarm
git reset --hard origin/master
popd

pushd installer
git fetch -a
git reset --hard origin/replace
git apply ../installer-patches/*
make installer-image
make controller-image
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer:swarm
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer-controller:swarm
git reset --hard origin/replace
popd

