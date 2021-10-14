# ! Warning !
Although the code in this repo tries its best to be non-destructive, it has a big potential
to mess up the machine it's running on - so you should probably run it in a disposable VM.

# What is this
This is a tool to launch a swarm of asssisted installer agents that look
to the service like actual cluster host agents, all the way from discovery/bmh to completed
installation and controller progress reports, for the purpose of load-testing the service.

This repo also contains helper scripts to deploy & manage the relevant CRs for assisted
kube-api installation of the swarm, and running the agents described above to act as the swarm.

# Background
Originally, the assisted installer service has been load-tested by installing actual clusters
on thousands of VMs. That approach has the advantage of testing the real thing - complete e2e OCP
assisted installation - it gave a perfectly accurate representation of the load on the service and also
helped find rare installation bugs. However, using this method is very costly and requires a
lot of machines to host all these VMs. Since this amount of hardware is not always immediately
available, a need arose to find a cheaper, less hardware-intensive way to load test
the service, by faking agent traffic rather then performing actual installations. This has the 
obvious downside that it doesn't find actual rare installation bugs, but at-least it allows us
to check how the service handles a lot of seemingly real agent traffic.

I considered two approaches to fake agent traffic:

1. Complete emulation - using tools such as JMeter or Locust, or writing custom fake agents that
 behave like real one, then running a lot of those on a single machine. 

2. No-op agent - use the existing agent, as is, let it do everything it usually does - but replace
 destructive actions such as installation, disk wiping, etc. with no-ops. The assisted controller that runs
 on the cluster (the cluster which doesn't really exist in this case) will simply run locally, and will
 also be modified to use mocked kube-api calls that cause it to feel like it's running on an 
 actual cluster.

Option (1) is definitely possible, but I felt it would be hard to maintain it and keep it up to date
with all the API changes / agent behavior changes that will be added in the future. 

Option (2) is what this repo is.

# TODO
At its current state, the repo is able to deploy all the relevant CRs, "fake" download the discovery ISO from the
image service, start a lot of agents, update the BMH status accordingly to make BMAC approve the agents, modify the
agent CRs with cluster binding, and run the assisted installer / controller all the way to the "Joined" stage.
The controller is yet to be fully implemented and it currently doesn't run, so the hosts only actually reach "Rebooting".

- [x] Manifests jinja2 templates
- [x] Working patched agent
    - [x] Fix weird `stateInfo: Failed - config is not valid` bug that happens 1/25 fake agents
- [x] Working patched installer
- [ ]  Working patched controller
    - [ ] Finish controller kube-api mock implementation
- [x] Launch script
- [x] Install script (set hostnames/roles/machine network/approve/etc)
- [ ] Upstream all the patches - get rid of as many patches as possible (see patch docs for more info)
- [ ] Split `**/mega.patch` files into several separate patch files - to ease failed patch application 
- [x] Add BMH support
- [x] Add image service load test support
- [ ] Run with auth enabled (load testing without auth is a bit unfair - I presume it adds a lot of CPU usage)
- [x] Run with https enabled (load testing without https is a bit unfair - I presume it adds a lot of CPU usage)
- [ ] Automate service configuration
- [ ] Query prometheus, extract interesting metrics (graphana dashboards? matplotlib?)

# Technical, how-to-use
## Overview
This repo allows you to build & run a customized no-op version of:

- The assisted installer agent
- The assisted installer 
- The assisted controller

The customization is done by applying a series of patch files that
modify the source code of the agent & installer/controller repositories,
then building them and publishing their images to quay.

The service-under-test can then be modified to use those custom images.

You can then use the provided scripts under `manifests/` to deploy n-replicas
of the assisted installation CRs. 
`./launch_all.sh` will automatically discover all the infraenvs that were created,
and will launch n agents matching those infraenvs on the host where the script is ran.
My current estimate for resource usage is - negligible amount of RAM per agent, but about
250m cores per agent, which is a lot - you'd need about 256 cores to run 2000 agents concurrently
without freezing your host.

The agents/installer/controller are supposed to behave just like the real thing as much as possible. This is achieved
via the patches described in the "Patches" section below.

## 1. Build images
From any machine (doesn't have to be the same machine running the swarm), run
`QUAY_ACCOUNT=<your quay.io account> ./prepare_images.sh`

This will build the patched images and publish them to:

- quay.io/${QUAY_ACCOUNT}/assisted-installer-agent:swarm
- quay.io/${QUAY_ACCOUNT}/assisted-installer:swarm
- quay.io/${QUAY_ACCOUNT}/assisted-installer-controller:swarm

So please make sure to `podman login quay.io` into the specified quay account, and 
also create public repositories with the above names.

## 2. Deploy the service-under-test
This part is up to you. Make sure the service is accessible from the swarm machines.

### Service Configuration
The assisted service configmap should be modified with the following parameters -
1) `AUTH_TYPE` set to `none`
2) `AGENT_DOCKER_IMAGE` set to point to the agent swarm image built by `./prepare_images.sh`
2) `INSTALLER_IMAGE` set to point to the installer swarm image built by `./prepare_images.sh`
3) `CONTROLLER_IMAGE` set to point to the controller swarm image built by `./prepare_images.sh`
4) `HW_VALIDATOR_REQUIREMENTS` can optionally be modified if your main host has less RAM then is required by default

## 3. Create manifests
This step requires `jq`, `jinja2-cli` (Python package, see `requirements.txt`) and `kubectl` & `oc` binaries.
You also need to point your kube binaries to the cluster the assisted service is running on.

Test parameters such as pull-secret, SSH keys, and exact number of swarm replicas should be set
in the `manifests/manifests-data.example.json` file. A default SSH key is provided and since we're
not actually installing anything, there's no point in modifying it to your own SSH key.

After configuration `manifests/manifests-data.example.json` you may run `./render.sh` to make sure
everything is working as expected, then you can use `./apply.sh` and `./delete.sh` to create/delete
the swarm CRs respectively.

These scripts too can be ran from a machine that is not the swarm machine, as long as they both point
to the same service

## 4. Launch the agents
There are two modes to launch the agents - 

- `infraenv` - This mode launches the agents directly from infraenvs without messing around with BMHs
- `bmh` - This mode simulates BMH state changes and downloads ISO images from the BMH image URL stanza

The mode can be changed inside the `./launch_all.sh` script

To be continued

# Patches
The agent and installer/controller repositories had to be modified to make them fit
to be ran inside the swarm. This section describes/documents the various patches that
get applied to achieve that.

Note: ideally, we should slowly move those patches up-stream and give the real agent/installer/controller
a "simulator" mode so those patches don't have to be maintained separately in this repo. The more patches
we maintain in this repo, the easier it would be for the agent/installer to go out of sync and this repo
becoming broken as a result.

## Agent Patches
See [Agent Patches documentation](agent-patches/doc.md)

## Installer Patches
See [Installer / Controller Patches documentation](installer-patches/doc.md)
