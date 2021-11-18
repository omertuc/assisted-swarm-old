import os
import base64
import jinja2
import logging
import subprocess
from pathlib import Path
from collections import OrderedDict

from agent import ClusterAgentConfig, SwarmAgentConfig, Agent
from dataclasses import dataclass
from logging import Logger
from statemachine import RetryingStateMachine
from swarmexecutor import SwarmExecutor
from swarmkubecache import SwarmKubeCache
from taskpool import TaskPool
from withcontainerconfigs import WithContainerConfigs


@dataclass
class ClusterConfig:
    controller_image_path: str
    logging: Logger
    single_node: bool
    num_workers: int
    index: int
    swarm_identifier: str
    storage_dir: Path
    service_url: str
    release_image: str
    ssh_pub_key: str
    pull_secret: str
    kube_cache: SwarmKubeCache
    task_pool: TaskPool
    num_locks: int
    executor: SwarmExecutor
    shared_graphroot: Path


class Cluster(RetryingStateMachine, WithContainerConfigs):
    def __init__(self, cluster_config: ClusterConfig, swarm_agent_config: SwarmAgentConfig):
        super().__init__(
            initial_state="Initializing",
            terminal_state="Done",
            states=OrderedDict(
                {
                    "Initializing": self.initialize,
                    "Generating manifests": self.generate_manifests,
                    "Applying manifests": self.apply_manifests,
                    "Launching agents": self.launch_agents,
                    "Waiting for AgentClusterInstall clusterMetadata infraID": self.wait_for_agentclusterinstall_cluster_metadata_infraid,
                    "Generating container configurations": self.create_container_configs,
                    "Running controller": self.run_controller,
                    "Wait for agents to complete": self.wait_for_agents,
                    "Done": self.done,
                }
            ),
            logging=logging,
            name=f"Cluster {cluster_config.index}",
        )

        self.cluster_config = cluster_config
        self.swarm_agent_config = swarm_agent_config

        self.identifier = f"{cluster_config.swarm_identifier}-{cluster_config.index}"
        self.cluster_dir = cluster_config.storage_dir / self.identifier
        self.manifest_dir = self.cluster_dir / "manifests"
        self.personal_graphroot = self.cluster_dir / "graphroot"

        WithContainerConfigs.__init__(
            self,
            self.personal_graphroot,
            self.cluster_config.shared_graphroot,
            self.cluster_dir,
            self.cluster_config.num_locks,
        )

        assert (
            cluster_config.single_node == False or cluster_config.num_workers == 0
        ), "Cannot have single node with workers"

        self.num_control_plane = 1 if cluster_config.single_node else 3
        self.num_workers = cluster_config.num_workers

        assert (
            self.total_agents <= 2 ** 16 - 4
        ), f"Too many agents in one cluster, {self.total_agents} larger than {2**16 - 4}"

        self.controller_stdout_path = self.cluster_dir / "controller.stdout.logs"
        self.controller_stderr_path = self.cluster_dir / "controller.stderr.logs"

        self.logging = logging

    @property
    def agent_ips(self):
        return [f"10.123.{i >> 8}.{i & 0xff}/16" for i in range(1, self.total_agents + 1)]

    @property
    def hostnames(self):
        return [f"{self.identifier}-{agent_index}" for agent_index in range(self.total_agents)]

    @property
    def total_agents(self):
        return self.num_control_plane + self.num_workers

    @staticmethod
    def make_mac(cluster_index, agent_index):
        assert cluster_index < 2 ** 24, "Cluster index too large"
        assert agent_index < 2 ** 24, "Agent index too large"

        octets = (
            cluster_index >> 16,
            cluster_index >> 8,
            cluster_index & 0xFF,
            agent_index >> 16,
            agent_index >> 8,
            agent_index & 0xFF,
        )
        return ":".join(f"{o:02x}" for o in octets)

    def generate_manifests(self, next_state):
        all_manifests = []

        per_cluster_manifets = (
            "namespace",
            "agentclusterinstall",
            "clusterdeployment",
            "clusterimageset",
            "infraenv",
            "secret_pull",
        )

        per_agent_manifests = (
            "baremetalhost",
            "secret_bmh",
        )

        params = {
            "release_image": self.cluster_config.release_image,
            "machine_network": "10.123.0.0/16",
            "ssh_pub_key": self.cluster_config.ssh_pub_key,
            "pull_secret_b64": base64.b64encode(self.cluster_config.pull_secret.encode("utf-8")).decode("utf-8"),
            "num_control_plane": self.num_control_plane,
            "num_workers": self.num_workers,
            "cluster_identifier": self.identifier,
            "single_node": self.cluster_config.single_node,
            "api_vip": "10.123.255.253",
            "ingress_vip": "10.123.255.254",
        }

        def render(manifest_name, **extra_params):
            with (Path("manifests") / f"{manifest_name}.yaml.j2").open() as manifest_file:
                all_manifests.append(jinja2.Template(manifest_file.read()).render(**params, **extra_params))

        for manifest_name in per_cluster_manifets:
            render(manifest_name)

        for agent_index in range(self.total_agents):
            for manifest_name in per_agent_manifests:
                render(
                    manifest_name,
                    mac_address=self.make_mac(self.cluster_config.index, agent_index),
                    agent_identifier=f"{self.identifier}-{agent_index}",
                    role="master" if agent_index < self.num_control_plane else "worker",
                )

        self.manifests = "\n---\n".join(all_manifests)

        with open(self.manifest_dir / "manifests.yaml", "w") as f:
            f.write(self.manifests)

        return next_state

    def apply_manifests(self, next_state):
        subprocess.run(["oc", "apply", "-f", "-"], input=self.manifests.encode("utf-8"), check=True)

        return next_state

    def initialize(self, next_state):
        for dir in (self.cluster_dir, self.manifest_dir):
            dir.mkdir(parents=True, exist_ok=True)

        return next_state

    def launch_agents(self, next_state):
        self.agents = [
            Agent(
                self.swarm_agent_config,
                ClusterAgentConfig(
                    index=agent_index,
                    mac_address=self.make_mac(self.cluster_config.index, agent_index),
                    machine_ip=self.agent_ips[agent_index],
                    machine_hostname=self.hostnames[agent_index],
                    cluster_identifier=self.identifier,
                    cluster_dir=self.cluster_dir,
                    identifier=f"{self.identifier}-{agent_index}",
                    cluster_hostnames=self.hostnames,
                    cluster_ips=self.agent_ips,
                ),
            )
            for agent_index in range(self.total_agents)
        ]

        self.agent_tasks = []
        for agent_index, agent in enumerate(self.agents):
            self.logging.info(f"Launching agent {agent_index}")
            self.agent_tasks.append(self.cluster_config.task_pool.submit(agent.start))

        return next_state

    def run_controller(self, next_state):
        podman_environment = {
            "CONTAINERS_CONF": str(self.container_config),
            "CONTAINERS_STORAGE_CONF": str(self.container_storage_conf),
        }

        # Arbitrarily choose the first agent's reboot marker path as a signal for the controller that it should start
        fake_reboot_marker_path = self.agents[0].fake_reboot_marker_path

        controller_environment = {
            "CLUSTER_ID": self.infra_id,
            "DRY_ENABLE": "true",
            "INVENTORY_URL": self.cluster_config.service_url,
            "PULL_SECRET_TOKEN": self.cluster_config.pull_secret,
            "OPENSHIFT_VERSION": 4.9,  # TODO: Make this configurable? Does it matter in any way?
            "DRY_FAKE_REBOOT_MARKER_PATH": str(fake_reboot_marker_path),
            "SKIP_CERT_VERIFICATION": "true",
            "HIGH_AVAILABILITY_MODE": "false",
            "CHECK_CLUSTER_VERSION": "true",
            "DRY_HOSTNAMES": ",".join(self.hostnames),
            "DRY_MCS_ACCESS_IPS": ",".join(ip.split("/")[0] for ip in self.agent_ips),
        }

        controller_mounts = {str(self.cluster_config.storage_dir): str(self.cluster_config.storage_dir)}

        podman_command = [
            "podman",
            "run",
            "--net=host",
            "-it",
            *(f"-e={var}={value}" for var, value in controller_environment.items()),
            *(f"-v={host_path}:{container_path}" for host_path, container_path in controller_mounts.items()),
            self.cluster_config.controller_image_path,
        ]

        with self.controller_stdout_path.open("ab") as controller_stdout_file:
            with self.controller_stderr_path.open("ab") as controller_stderr_file:
                controller_stdout_file.write(
                    f"Running controller with command: {podman_command} and env {podman_environment}".encode("utf-8")
                )
                controller_process = self.cluster_config.executor.Popen(
                    self.cluster_config.executor.prepare_sudo_command(podman_command, podman_environment),
                    env={**os.environ, **podman_environment},
                    stdin=subprocess.DEVNULL,
                    stdout=controller_stdout_file,
                    stderr=controller_stderr_file,
                )

        if controller_process.wait() != 0:
            self.logging.error(f"Controller exited with non-zero exit code {controller_process.returncode}")
            return self.state

        return next_state

    def wait_for_agents(self, next_state):
        for agent in self.agent_tasks:
            agent.result()

        return next_state

    def wait_for_agentclusterinstall_cluster_metadata_infraid(self, next_state):
        agent_cluster_install = self.cluster_config.kube_cache.get_agent_cluster_install(
            namespace=self.identifier, name=self.identifier
        )

        if agent_cluster_install is not None:
            infra_id = agent_cluster_install.get("spec", {}).get("clusterMetadata", {}).get("infraID", None)

            if not infra_id:
                return self.state

            self.infra_id = infra_id

            return next_state

        self.logging.info(f"Waiting for agent cluster install {self.identifier}/{self.identifier} to be created")

        return self.state

    def done(self, _):
        return self.state
