# ! Warning !
Although the code in this repo tries its best to be non-destructive, it has a big potential
to mess up the machine it's running on - so you should probably run it in a disposable VM.

# What is this
This is a tool to launch a swarm of asssisted installer agents that look
to the service like actual cluster host agents, all the way from discovery to completed
installation and controller progress reports.

This repo also contains helper scripts to deploy & manage the relevant CRs for assisted
kube-api installation of the swarm, and running the agents described above to connect to said CRs
and act as the swarm itself.

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

# Non-goals / TODO
This repo, in its current state, does not deal with testing the following mechanisms -

- BMAC testing - there's no bare metal (OOBM, IPMI, RedFish, etc) emulation here. No BareMetalHost
  CRs created. Maybe we'll add it in the future.

- Image service load testing - at no point while running the swarm do we download
  the actual ISO images - we simply download the ignition file from the service
  API endpoint and copy the commands from the systemd unit. The assisted image service
  and its interaction with the real server, and the effect of ISO-downloading load on
  said services is not being tested.

# Technical, how-to-use
This repo allows you to build & run a customized no-op version of:

- The assisted installer agent
- The assisted installer 
- The assisted controller

The customization is done by applying a series of patch files that
modify the source code of the agent & installer/controller repositories,
then building them and publishing their images to quay.

The service-under-test can then be modified to use those custom images.

You can then use the provided scripts under `manifests/` to deploy n-replicas
of the assisted installation CRs. The test parameters (pull-secret, SSH keys,
and exact number of swarm replicas) can be be in the `manifests/manifests-data.example.json'.

`./launch_all.sh` will automatically discover all the infraenvs that were created,
and will launch n agents matching those infraenvs on the host where the script is ran.
I haven't ran 1000 agents yet but I imagine it's going to use up a lot of RAM to support
all these containers. It might be on the order of 100GBs of RAM.

The agents should behave just like real agents as much as possible. This is achieved
via the patches described in the patches section below.

# Service Configuration
The assisted service configmap should be modified with the following parameters -
1) AUTH_TYPE set to none
2) AGENT_DOCKER_IMAGE set to point to the agent swarm image built by `./prepare_images.sh`
2) INSTALLER_IMAGE set to point to the installer swarm image built by `./prepare_images.sh`
3) CONTROLLER_IMAGE set to point to the controller swarm image built by `./prepare_images.sh`
4) HW_VALIDATOR_REQUIREMENTS can optionally be modified if your main host has less RAM then is required by default

# Patches
The agent and installer/controller repositories had to be modified to make them fit
to be ran inside the swarm. This section describes/documents the various patches that
get applied to achieve that.

Note: ideally, we should slowly move those patches up-stream and give the real agent/installer/controller
a "simulator" mode so those patches don't have to be maintained separately in this repo. The more patches
we maintain in this repo, the easier it would be for the agent/installer to go out of sync and this repo
becoming broken as a result.

## Agent Patches
The following changes are being applied to the agent repo -
- Change image registry path from `quay.io/ocpmetal/assisted-installer-agent:latest`
  to `quay.io/otuchfel/assisted-installer-agent:swarm`. Should probably make this customizable.

- Change Makefile "docker" usage to "podman". We use podman to run the swarm, so the images
  that get built should be in the podman cache and not the docker cache.

- Read agent host-id from the usually ommitted `--host-id` flag, rather than generating
  the ID from hardware. This allows us to run many different agents with different IDs,
  rather than having them all have the same ID because they're all running on the same
  hardware. <- This can be up-streamed! If --host-id is given, use it instead of 
  getting it from the hardware, no harm done.

- Append host ID to step-containers names - The service tells the agent to launch containers
  using the next-step-runner - sometimes the service hardcodes a container name for those
  containers. This cannot work in a swarm because the different swarm agents will each try
  to create those containers, and we cannot have their names collide. We solve that by appending
  the host-id to the service container name. <- This can be up-streamed! It works great for the
  swarm use-case and doesn't interfere with the regular use-case, so there's no harm in upstreaming
  it.

- Replace `dd` with `true` - To avoid deleting the disks of the host running the swarm, we 
  intercept the `install` step and replace its `dd if=...` invocations with `true if=...` 
  invocations that don't really do anything.

- Enter CGroup namespace when the next-step-runner container launches containers on its host
  by adding the `-C` flag to `nsenter`. This fixes a bug where the next-step-runner is unable
  to launch containers using podman on some systemd based distros (this is not a problem on RHCOS,
  where the agent typically runs, which is why it was not needed on the original agent). <- This
  can be upstreamed! There's no harm in joining the cgroup namespace of the host before launching
  containers on the host.

- The FIO step has been modified to simply report that it took 1ms, rather than running the actual
  destructive FIO on the installation disk directly.

## Installer Patches
The following changes are being applied to the installer in the installer repo -
- Change image registry path from `quay.io/ocpmetal/assisted-installer:latest`
  to `quay.io/otuchfel/assisted-installer:swarm`. Should probably make this customizable.

- Comment out destructive lines in `cleanupInstallDevice`

- Call the `swarm-installer` "binary" rather than the `coreos-installer` binary. You can see what this
  "binary" does instead - it's included in this repository.

- Disable `efibootmgr` calls - don't want to mess with the host's EFI entries.

- The reboot operation has been disabled, to avoid reboot.

- `extractIgnitionToFS`, which used the unavailable `rpm-ostree` binary, has been disabled

- Disable SSH key generation, since they will destroy the host SSH keys

- Disable daemon-reload, because it'll mess with the host

- Disable `checkLocalhostName`, because it will give the host a random hostname

- Disable `NetworkManager.service` restart, because it will mess up the host's networking

- Disable `servicesToStart` because we don't need to start any actual services

- Disable `updateSingleNodeIgnition` because it tries to parse and actual ignition file generated by
  bootkube, which we don't have, because we don't actually run bootkube.

- WIP


## Controller Patches
The following changes are being applied to the controller in the installer repo -
- Change image registry path from `quay.io/ocpmetal/assisted-installer-controller:latest`
  to `quay.io/otuchfel/assisted-installer-controller:swarm`. Should probably make this customizable.

- Replace k8s_client package with a mock, configure mock to behave like a slowly initializing
  cluster as much as we reasonably can.

- Disable `HackDNSAddressConflict` - it's too complicated to mock k8s API calls for this and the
  service couldn't care less about it, so just disable it altogether.

- WIP

