#!/bin/bash

set -euxo pipefail

SCRIPT_DIR=$(dirname "$(readlink -f "$0")")

pushd agent
git fetch -a
git reset --hard origin/master
git apply ../agent-patches/*
sudo make -o unit-test build-image
sudo podman push quay.io/otuchfel/assisted-installer-agent:swarm
git reset --hard origin/master
popd

pushd installer
git fetch -a
git reset --hard origin/replace
git apply ../installer-patches/*
sudo make installer-image
sudo make controller-image
sudo podman push quay.io/otuchfel/assisted-installer:swarm
sudo podman push quay.io/otuchfel/assisted-installer-controller:swarm
git reset --hard origin/replace
popd

