from statemachine import RetryingStateMachine
import jinja2
import subprocess
import os
import requests
import json
from swarmexecutor import SwarmExecutor
from collections import OrderedDict
from containerconfig import (
    ContainerStorageConfigWithGraphrootAndAdditionalImageStores,
    ContainerConfigWithEnvAndNumLocks,
    system_container_storage_config,
    system_container_config,
)
from swarmkubecache import SwarmKubeCache
import re
import base64
import uuid

from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


class Agent(RetryingStateMachine):
    """
    A state machine to execute the commands for a single swarm agent
    """

    def __init__(
        self,
        agent_binary,
        agent_image_path,
        controller_image_path,
        ca_cert_path,
        token,
        index,
        machine_network,
        machine_ip,
        pull_secret,
        release_image,
        service_url,
        shared_storage,
        ssh_pub_key,
        storage_dir,
        executor: SwarmExecutor,
        logging,
        swarm_identifier,
        shared_graphroot,
        k8s_api_server_url,
        machine_hostname,
        kube_cache: SwarmKubeCache,
        num_locks: int,
    ):
        super().__init__(
            initial_state="Initializing",
            terminal_state="Done",
            states=OrderedDict(
                {
                    "Initializing": self.initialize,
                    "Generating manifests": self.generate_manifests,
                    "Applying manifests": self.apply_manifests,
                    "Waiting for ISO URL on InfraEnv": self.wait_iso_url_infraenv,
                    'Seting BMH provisioning state to "ready"': self.ready_bmh,
                    "Waiting for ISO URL on BMH": self.wait_iso_url_bmh,
                    # "Download ISO": self.download_iso,
                    'Seting BMH provisioning state to "provisioned"': self.provisioned_bmh,
                    "Generating container configurations": self.create_container_configs,
                    "Running agent": self.run_agent,
                    "Waiting for AgentClusterInstall clusterMetadata infraID": self.wait_for_agentclusterinstall_cluster_metadata_infraid,
                    "Running controller": self.run_controller,
                    "Done": self.done,
                }
            ),
            logging=logging,
            name=f"Agent {index}",
        )

        # Identifiers
        self.host_id = str(uuid.uuid4())
        self.swarm_identifier = swarm_identifier
        self.identifier = f"{self.swarm_identifier}-{index}"
        self.index = index

        # Utils
        self.logging = logging
        self.executor = executor
        self.kube_cache = kube_cache

        # Directories
        self.storage_dir = storage_dir
        self.agent_dir = self.storage_dir / self.identifier
        self.manifest_dir = self.agent_dir / "manifests"

        # General paths
        self.agent_binary = agent_binary
        self.agent_image_path = agent_image_path
        self.controller_image_path = controller_image_path
        self.fake_reboot_marker_path = self.agent_dir / "fake_reboot_marker"

        # Service account credentials
        self.token = token
        self.ca_cert_path = ca_cert_path

        # Networking 
        self.mac_address = f"00:00:00:00:{self.index >> 8:02x}:{self.index & 0xff:02x}"
        self.machine_network = machine_network
        self.machine_ip = machine_ip
        self.machine_hostname = machine_hostname

        # Secrets
        self.pull_secret = pull_secret
        self.ssh_pub_key = ssh_pub_key

        # Container config
        self.personal_graphroot = self.agent_dir / "graphroot"
        self.shared_graphroot = shared_graphroot
        self.shared_storage = shared_storage
        self.num_locks = num_locks

        # Endpoints
        self.service_url = service_url
        self.k8s_api_server_url = k8s_api_server_url

        # misc.
        self.release_image = release_image

        # Logging paths
        self.log_dir = self.agent_dir / "logs"
        self.agent_stdout_path = self.agent_dir / "agent.stdout.logs"
        self.agent_stderr_path = self.agent_dir / "agent.stderr.logs"
        self.controller_stdout_path = self.agent_dir / "controller.stdout.logs"
        self.controller_stderr_path = self.agent_dir / "controller.stderr.logs"

    def wait_for_agentclusterinstall_cluster_metadata_infraid(self, next_state):
        agent_cluster_install = self.kube_cache.get_agent_cluster_install(
            namespace=self.identifier,
            name=self.identifier
        )

        if agent_cluster_install is not None:
            infra_id = agent_cluster_install.get("spec", {}).get("clusterMetadata", {}).get("infraID", None)

            if not infra_id:
                return self.state

            self.infra_id = infra_id

            return next_state

        self.logging.info(f"Waiting for agent cluster install {self.identifier}/{self.identifier} to be created")

        return self.state

    def initialize(self, next_state):
        for dir in (self.agent_dir, self.log_dir, self.manifest_dir, self.personal_graphroot):
            dir.mkdir(parents=True, exist_ok=True)

        return next_state

    def download_iso(self, next_state):
        self.executor.check_call(
            ["curl", "-s", "-o", "/dev/null", self.bmh_iso_url],
            check=True,
        )

        return next_state

    def generate_manifests(self, next_state):
        with (SCRIPT_DIR / "manifests.yaml.j2").open("r") as f:
            template = jinja2.Template(f.read())
            self.manifests = template.render(
                agent_identifier=self.identifier,
                release_image=self.release_image,
                machine_network=self.machine_network,
                ssh_pub_key=self.ssh_pub_key,
                pull_secret_b64=base64.b64encode(self.pull_secret.encode("utf-8")).decode("utf-8"),
                mac_address=self.mac_address,
            )

        with open(self.manifest_dir / "manifests.yaml", "w") as f:
            f.write(self.manifests)

        return next_state

    def apply_manifests(self, next_state):
        subprocess.run(["oc", "apply", "-f", "-"], input=self.manifests.encode("utf-8"), check=True)

        return next_state

    @staticmethod
    def get_infraenv_id_from_url(url):
        uuid_regex = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

        search = re.search(uuid_regex, url)
        if search:
            return search.group(0)

        raise RuntimeError("Could not find infraenv ID from url")

    def wait_iso_url_infraenv(self, next_state):
        infraenv = self.kube_cache.get_infraenv(
            namespace=self.identifier,
            name=self.identifier
        )

        if infraenv is not None:
            iso_url = infraenv.get("status", {}).get("isoDownloadURL", "")

            if iso_url == "":
                self.logging.info("Infraenv .status.isoDownloadURL is empty")
                return self.state

            self.logging.info(f"Infraenv .status.isoDownloadURL found {iso_url}")
            self.infraenv_iso_url = iso_url

            self.infraenv_id = self.get_infraenv_id_from_url(self.infraenv_iso_url)

            return next_state

        self.logging.info(f"Infraenv {self.identifier}/{self.identifier} not found")

        return self.state

    def wait_iso_url_bmh(self, next_state):
        baremetalhost = self.kube_cache.get_baremetalhost(
            namespace=self.identifier,
            name=self.identifier
        )

        if baremetalhost is not None:
            iso_url = baremetalhost.get("spec", {}).get("image", {}).get("url", "")

            if iso_url == "":
                self.logging.info("BMH .spec.image.url is empty")
                return self.state

            self.logging.info(f"BMH .spec.image.url found {iso_url}")
            self.bmh_iso_url = iso_url

            self.infraenv_id = self.get_infraenv_id_from_url(self.infraenv_iso_url)

            return next_state

        self.logging.info(f"BMH {self.identifier}/{self.identifier} not found")

        return self.state

    def set_bmh_provisioning_state(self, provisioning_state):
        baremetalhost = self.kube_cache.get_baremetalhost(
            namespace=self.identifier,
            name=self.identifier
        )

        if baremetalhost is not None:
            baremetalhost["status"] = {
                "errorCount": 0,
                "errorMessage": "",
                "goodCredentials": {},
                "hardwareProfile": "",
                "operationalStatus": "discovered",
                "poweredOn": True,
                "provisioning": {"state": provisioning_state, "ID": "", "image": {"url": ""}},
            }

            response = requests.put(
                f"{self.k8s_api_server_url}/apis/metal3.io/v1alpha1/namespaces/{self.identifier}/baremetalhosts/{self.identifier}/status",
                json=baremetalhost,
                headers={"Authorization": f"Bearer {self.token}"},
                verify=str(self.ca_cert_path),
            )
            response.raise_for_status()

            return True

        self.logging.info(f"BMH {self.identifier}/{self.identifier} not found")

        return False

    def ready_bmh(self, next_state):
        if self.set_bmh_provisioning_state("ready"):
            return next_state

        return self.state

    def provisioned_bmh(self, next_state):
        if self.set_bmh_provisioning_state("provisioned"):
            return next_state

        return self.state

    def create_container_configs(self, next_state):
        with ContainerStorageConfigWithGraphrootAndAdditionalImageStores(
            system_container_storage_config,
            graphroot=self.personal_graphroot,
            additional_image_stores=[self.shared_graphroot],
            delete=False,
            dir=str(self.agent_dir),
            prefix="agent_and_controller_container_storage_config_",
        ) as container_storage_config:
            self.container_storage_conf = container_storage_config

        with ContainerConfigWithEnvAndNumLocks(
            system_container_config,
            env=[
                "CONTAINERS_CONF",
                "CONTAINERS_STORAGE_CONF",
                "DRY_ENABLE",
                "DRY_HOST_ID",
                "DRY_MAC_ADDRESS",
                "PULL_SECRET_TOKEN",
                "DRY_FAKE_REBOOT_MARKER_PATH",
            ],
            num_locks=self.num_locks,
            delete=False,
            dir=str(self.agent_dir),
            prefix="agent_and_controller_container_config_",
        ) as container_config:
            self.container_config = container_config

        return next_state

    def run_agent(self, next_state):
        agent_environment = {
            "CONTAINERS_CONF": str(self.container_config),
            "CONTAINERS_STORAGE_CONF": str(self.container_storage_conf),
            "PULL_SECRET_TOKEN": self.pull_secret,
            "DRY_ENABLE": "true",
            "DRY_HOST_ID": self.host_id,
            "DRY_MAC_ADDRESS": self.mac_address,
            "DRY_FAKE_REBOOT_MARKER_PATH": str(self.fake_reboot_marker_path),
        }

        agent_command = [
            str(self.agent_binary),
            "--url",
            self.service_url,
            "--infra-env-id",
            self.infraenv_id,
            "--agent-version",
            self.agent_image_path,
            "--insecure=true",
            "--cacert",
            str(self.ca_cert_path),
        ]

        with self.agent_stdout_path.open("ab") as agent_stdout_file:
            with self.agent_stderr_path.open("ab") as agent_stderr_file:
                agent_stdout_file.write(f"Running agent with command: {agent_command} and env {agent_environment}".encode('utf-8'))
                agent_process = self.executor.Popen(
                    self.executor.prepare_sudo_command(agent_command, agent_environment),
                    env={**os.environ, **agent_environment},
                    stdin=subprocess.DEVNULL,
                    stdout=agent_stdout_file,
                    stderr=agent_stderr_file,
                )

        if agent_process.wait() != 0:
            self.logging.error(f"Agent exited with non-zero exit code {agent_process.returncode}")
            return self.state

        return next_state

    def run_controller(self, next_state):
        podman_environment = {
            "CONTAINERS_CONF": str(self.container_config),
            "CONTAINERS_STORAGE_CONF": str(self.container_storage_conf),
        }

        controller_environment = {
            "CLUSTER_ID": self.infra_id,
            "DRY_ENABLE": "true",
            "INVENTORY_URL": self.service_url,
            "PULL_SECRET_TOKEN": self.pull_secret,
            "OPENSHIFT_VERSION": 4.9,  # TODO: Make this configurable? Does it matter in any way?
            "DRY_FAKE_REBOOT_MARKER_PATH": str(self.fake_reboot_marker_path),
            "SKIP_CERT_VERIFICATION": "true",
            "HIGH_AVAILABILITY_MODE": "false",
            "CHECK_CLUSTER_VERSION": "true",
            "DRY_HOSTNAMES": self.machine_hostname,
            "DRY_MCS_ACCESS_IPS": self.machine_ip,
        }

        controller_mounts = {str(self.storage_dir): str(self.storage_dir)}

        podman_command = [
            "podman",
            "run",
            "--net=host",
            "-it",
            *(f"-e={var}={value}" for var, value in controller_environment.items()),
            *(f"-v={host_path}:{container_path}" for host_path, container_path in controller_mounts.items()),
            self.controller_image_path,
        ]

        with self.controller_stdout_path.open("ab") as controller_stdout_file:
            with self.controller_stderr_path.open("ab") as controller_stderr_file:
                controller_stdout_file.write(f"Running controller with command: {podman_command} and env {podman_environment}".encode('utf-8'))
                controller_process = self.executor.Popen(
                    self.executor.prepare_sudo_command(podman_command, podman_environment),
                    env={**os.environ, **podman_environment},
                    stdin=subprocess.DEVNULL,
                    stdout=controller_stdout_file,
                    stderr=controller_stderr_file,
                )

        if controller_process.wait() != 0:
            self.logging.error(f"Controller exited with non-zero exit code {controller_process.returncode}")
            return self.state

        return next_state

    def done(self, _):
        return self.state
