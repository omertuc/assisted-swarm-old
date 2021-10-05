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

Option (2) is what this repo is. Originally this repo contained the patches to make the agent/installer/controller no-op,
but today the patches have been upstreamed and now the agent/installer/controller have a "dry run" mode that 
does exactly that, and this repo makes use of that

# TODO
At its current state, the repo is able to deploy all the relevant CRs, "fake" download the discovery ISO from the
image service, start a lot of agents, update the BMH status accordingly to make BMAC approve the agents, modify the
agent CRs with cluster binding, and run the assisted installer / controller all the way to the "Joined" stage.
The controller is yet to be fully implemented and it currently doesn't run, so the hosts only actually reach "Rebooting".

- [x] Manifests jinja2 templates
- [x] Working patched agent
    - [x] Fix weird `stateInfo: Failed - config is not valid` bug that happens 1/25 fake agents
- [x] Working patched installer
- [x]  Working patched controller
    - [x] Finish controller kube-api mock implementation
- [x] Launch script
- [x] Install script (set hostnames/roles/machine network/approve/etc)
- [x] Upstream all the patches - get rid of as many patches as possible (see patch docs for more info)
- [x] Add BMH support
- [x] Add image service load test support
- [ ] Run with auth enabled (load testing without auth is a bit unfair - I presume it adds a lot of CPU usage)
- [x] Run with https enabled (load testing without https is a bit unfair - I presume it adds a lot of CPU usage)
- [ ] Automate service configuration
- [ ] Query prometheus, extract interesting metrics (graphana dashboards? matplotlib?)

# Technical, how-to-use
## Overview
You can then use the provided scripts under `manifests/` to deploy n-replicas
of the assisted installation CRs. 
`utils/launch_all.sh` will automatically discover all the infraenvs that were created,
and will launch n agents matching those infraenvs on the host where the script is ran.
My current estimate for resource usage is - negligible amount of RAM per agent, but about
250m cores per agent, which is a lot - you'd need about 256 cores to run 2000 agents concurrently
without freezing your host.

The agents/installer/controller are launched using their dry-run mode.

## 1. Deploy the service-under-test
This part is up to you. Make sure the service is accessible from the swarm machines.

### Service Configuration
The assisted service configmap should be modified with the following parameters -
1) `AUTH_TYPE` set to `none`
2) `HW_VALIDATOR_REQUIREMENTS` can optionally be modified if your main host has less RAM then is required by default

## 2. Create manifests
This step requires `jq`, `jinja2-cli`, `yq` (Python packages, see `requirements.txt`) and `kubectl` & `oc` binaries.
You also need to point your kubectl/oc to the cluster the assisted service is running on.

Test parameters such as pull-secret, SSH keys, and exact number of swarm replicas should be set
in the `manifests/manifests-data.example.json` file. A default SSH key is provided and since we're
not actually installing anything, there's no point in modifying it to your own SSH key.

After configuration `manifests/manifests-data.example.json` you may run `manifests/render.sh` to make sure
everything is working as expected, then you can use `manifests/apply.sh` and `manifests/delete.sh` to create/delete
the swarm CRs respectively.

These scripts too can be ran from a machine that is not the swarm machine, as long as they both point
to the same service

## 3. Launch the agents
The agents are launched using the `utils/launch_all.sh` script. Make sure to set the SERVICE_ENDPOINT to point
at the service's API endpoint.

