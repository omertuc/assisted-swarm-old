#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

echo "Pushing to quay user ${QUAY_ACCOUNT}"

pushd agent
git fetch -a
git reset --hard origin/release-ocm-2.4
git apply ../agent-patches/*.patch
make -o unit-test build-image
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer-agent:swarm
git reset --hard origin/release-ocm-2.4
popd

pushd installer
git fetch -a
git reset --hard origin/release-ocm-2.4
git apply ../installer-patches/*.patch
make installer-image
make controller-image
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer:swarm
podman push quay.io/${QUAY_ACCOUNT}/assisted-installer-controller:swarm
git reset --hard origin/release-ocm-2.4
popd

