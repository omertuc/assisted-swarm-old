# Agent Patches
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
