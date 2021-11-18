#!/usr/bin/env python3

from collections import OrderedDict
from pathlib import Path
import time
import threading
import logging
import json
import subprocess
import base64
from collections import OrderedDict
import requests
import os

from statemachine import RetryingStateMachine
from swarmexecutor import SwarmExecutor
from containerconfig import (
    ContainerConfigWithEnvAndNumLocks,
    ContainerStorageConfigWithGraphroot,
    system_container_storage_config,
    system_container_config,
)
from agent import SwarmAgentConfig
from cluster import Cluster, ClusterConfig
from swarmkubecache import SwarmKubeCache


def get_user_cache_dir():
    return Path(
        os.environ["XDG_CACHE_HOME"] if "XDG_CACHE_HOME" in os.environ else os.path.join(os.environ["HOME"], ".cache")
    )


global_swarm_directory = get_user_cache_dir() / "swarm"

# The default number of locks used by podman is 2048, this is insufficient for our use case
num_locks = 9000
bad_lock_return_code = 125


class Swarm(RetryingStateMachine):
    def __init__(self, pull_secret, service_url, ssh_pub_key):
        self.ssh_pub_key = ssh_pub_key
        self.pull_secret = pull_secret
        self.service_url = service_url
        self.logging = logging.getLogger("swarm")
        self.executor = SwarmExecutor(self.logging)

        now_second = int(time.time())
        self.identifier = f"swarm-{now_second}"
        self.swarm_dir = global_swarm_directory / self.identifier

        super().__init__(
            initial_state="Initializing",
            terminal_state="Ready to create clusters",
            states=OrderedDict(
                {
                    "Initializing": self.initialize,
                    "Checking root": self.check_root,
                    "Ensuring swarm directory exists": self.ensure_swarm_directory_exists,
                    "Validating system podman lock config": self.validate_system_podman_lock_config,
                    "Killing previous swarm": self.kill_previous_swarm,
                    "Deleting previous swarm storage": self.delete_previous_swarm_storage,
                    "Creating service account": self.create_serviceaccount,
                    "Creating clusterrolebinding": self.create_cluserrolebinding,
                    "Retrieving service account credentials": self.retrieve_serviceaccount_credentials,
                    "Getting image urls from service": self.get_image_urls_from_service,
                    "Createing tmpfs": self.create_tmpfs,
                    "Creating shared container image storage": self.create_shared_container_image_storage,
                    "Pre-caching service images": self.precache_service_images,
                    "Retrieving binary": self.retrieve_agent_binary,
                    "Creating CA Cert": self.create_ca_cert,
                    "Determining hostname": self.determine_hostname,
                    "Ready to create clusters": self.ready_to_create_clusters,
                }
            ),
            logging=self.logging,
            name=f"Swarm",
        )

    def validate_system_podman_lock_config(self, next_state):
        with ContainerConfigWithEnvAndNumLocks(
            system_container_config,
            env=[],
            num_locks=num_locks,
            dir=self.swarm_dir,
            prefix="test_system_podman_config_",
        ) as container_config:
            self.logging.info(f"Validating system podman lock config")
            podman_env = {"CONTAINERS_CONF": str(container_config)}
            podman_command = self.executor.prepare_sudo_command(["podman", "run", "alpine"], env=podman_env)

            try:
                self.executor.check_call(podman_command, env={**os.environ, **podman_env})
            except subprocess.CalledProcessError as e:
                if e.returncode == bad_lock_return_code:
                    self.logging.info(
                        f'System podman lock config is not valid, please edit the "num_locks" in "{system_container_config}" to have the value {num_locks} and then run "sudo podman system renumber". If you get an error, delete "/dev/shm/libpod_lock" and try again'
                    )
                    return self.state

                raise

        return next_state

    def determine_hostname(self, next_state):
        self.logging.info("Determining hostname")

        # TODO: Which is more correct to use, with or without fqdn?
        # What does the controller care about? Usually it's the same with or without
        fully_qualified = "--fqdn"

        self.machine_hostname = self.executor.check_output(["hostname", fully_qualified]).decode("utf-8").strip()

        return next_state

    def create_ca_cert(self, next_state):
        self.ca_cert_path = self.swarm_dir / "ca.crt"
        with open(self.ca_cert_path, "w") as ca_cert_file:
            ca_cert_file.write(self.ca_cert)

        return next_state

    def ensure_swarm_directory_exists(self, next_state):
        self.swarm_dir.mkdir(parents=True, exist_ok=True)

        return next_state

    def precache_service_images(self, next_state):
        images_to_precache = {
            "discovery-agent",
            "assisted-installer",
            "assisted-installer-controller",
        }

        with ContainerStorageConfigWithGraphroot(
            system_container_storage_config,
            self.shared_graphroot,
            dir=self.swarm_dir,
            prefix="precache_container_storage_config_",
        ) as shared_graphroot_conf:
            with ContainerConfigWithEnvAndNumLocks(
                system_container_config,
                env=[],
                num_locks=num_locks,
                dir=self.swarm_dir,
                prefix="precache_container_config_",
            ) as container_config:
                for image, url in self.service_image_urls.items():
                    if image in images_to_precache:
                        self.logging.info(f"Pre-caching {image} image")

                        pull_command = ["podman", "pull", url]
                        pull_command_env = {
                            "CONTAINERS_STORAGE_CONF": str(shared_graphroot_conf),
                            "CONTAINERS_CONF": str(container_config),
                        }

                        self.executor.check_call(
                            self.executor.prepare_sudo_command(pull_command, pull_command_env),
                            env={**os.environ, **pull_command_env},
                        )

        return next_state

    def ready_to_create_clusters(self, _):
        return self.state

    def create_serviceaccount(self, next_state):
        self.logging.info("Creating service account")
        self.executor.check_call(
            [
                "oc",
                "create",
                "serviceaccount",
                self.identifier,
                "-n",
                "default",
            ]
        )

        return next_state

    def create_cluserrolebinding(self, next_state):
        self.logging.info("Creating clusterrolebinding")
        self.executor.check_call(
            [
                "oc",
                "create",
                "clusterrolebinding",
                self.identifier,
                "--clusterrole=cluster-admin",
                f"--serviceaccount=default:{self.identifier}",
            ],
        )

        return next_state

    def retrieve_serviceaccount_credentials(self, next_state):
        self.logging.info("Retrieving service account credentials")
        # Get service account secrets list
        service_accounts = self.executor.check_output(
            [
                "kubectl",
                "get",
                "sa",
                "--namespace=default",
                self.identifier,
                "-ojson",
            ]
        )

        service_accounts = json.loads(service_accounts)

        try:
            secret_name = next(
                secret["name"]
                for secret in service_accounts["secrets"]
                if secret["name"].startswith(f"{self.identifier}-token-")
            )
        except StopIteration:
            logging.info("Service account doesn't list the token secret yet")
            return self.state

        secret = self.executor.check_output(
            [
                "kubectl",
                "get",
                "secret",
                secret_name,
                "-ojson",
            ]
        )

        self.token = base64.b64decode(json.loads(secret)["data"]["token"]).decode("utf-8")
        self.ca_cert = base64.b64decode(json.loads(secret)["data"]["ca.crt"]).decode("utf-8")

        self.k8s_api_server_url = (
            self.executor.check_output(
                [
                    "oc",
                    "whoami",
                    "--show-server",
                ]
            )
            .decode("utf-8")
            .strip()
        )

        return next_state

    def create_tmpfs(self, next_state):
        self.executor.check_call(
            [
                "sudo",
                "mount",
                "-t",
                "tmpfs",
                "-o",
                "size=20G",
                "tmpfs",
                str(self.swarm_dir),
            ]
        )

        return next_state

    def retrieve_agent_binary(self, next_state):
        agent_binary_dir = self.swarm_dir / "bin"
        agent_binary_dir.mkdir(parents=True, exist_ok=True)

        with ContainerStorageConfigWithGraphroot(
            system_container_storage_config,
            self.shared_graphroot,
            prefix="agent_binary_retrieval_container_storage_config_",
        ) as shared_graphroot_conf:
            with ContainerConfigWithEnvAndNumLocks(
                system_container_config,
                env=[],
                num_locks=num_locks,
                dir=self.swarm_dir,
                prefix="precache_container_config_",
            ) as container_config:
                podman_command = [
                    "podman",
                    "run",
                    "--privileged",
                    "--rm",
                    "-v",
                    f"{agent_binary_dir}:/hostbin",
                    self.service_image_urls["discovery-agent"],
                    "cp",
                    "/usr/bin/agent",
                    "/hostbin",
                ]
                podman_command_env = {
                    "CONTAINERS_STORAGE_CONF": str(shared_graphroot_conf),
                    "CONTAINERS_CONF": str(container_config),
                }

                self.executor.check_call(
                    self.executor.prepare_sudo_command(podman_command, podman_command_env),
                    env={**os.environ, **podman_command_env},
                )

        self.agent_bin = agent_binary_dir / "agent"
        return next_state

    def kill_previous_swarm(self, next_state):
        # TODO: Find previous swarm and kill all processes

        return next_state

    def delete_previous_swarm_storage(self, next_state):
        # TODO: Find previous swarm storage and delete it

        return next_state

    def create_shared_container_image_storage(self, next_state):
        self.shared_graphroot = global_swarm_directory / "shared_graphroot"
        self.shared_graphroot.mkdir(parents=True, exist_ok=True)

        return next_state

    def get_image_urls_from_service(self, next_state):
        resp = requests.get(
            f"{self.service_url}/api/assisted-install/v2/component-versions",
            verify=False,
        )

        resp.raise_for_status()
        self.service_image_urls = resp.json()["versions"]

        return next_state

    def check_root(self, next_state):
        if os.geteuid() != 0:
            raise Exception("Must be run as root")

        return next_state

    def initialize(self, next_state):
        self.kube_cache_done = threading.Event()
        self.kube_cache = SwarmKubeCache(self.kube_cache_done)
        self.kube_cache_thread = threading.Thread(target=self.kube_cache.monitor, args=())
        self.kube_cache_thread.start()

        return next_state

    def finalize(self):
        self.kube_cache_done.set()
        self.kube_cache_thread.join()

    def launch_cluster(self, index, task_pool, single_node, num_workers):
        cluster = Cluster(
            ClusterConfig(
                logging=self.logging,
                single_node=single_node,
                num_workers=num_workers,
                storage_dir=self.swarm_dir,
                ssh_pub_key=self.ssh_pub_key,
                pull_secret=self.pull_secret,
                task_pool=task_pool,
                controller_image_path=self.service_image_urls["assisted-installer-controller"],
                index=index,
                release_image="quay.io/openshift-release-dev/ocp-release:4.9.7-x86_64",
                swarm_identifier=self.identifier,
                num_locks=num_locks,
                service_url=self.service_url,
                kube_cache=self.kube_cache,
                executor=self.executor,
                shared_graphroot=self.shared_graphroot,
            ),
            SwarmAgentConfig(
                agent_binary=self.agent_bin,
                agent_image_path=self.service_image_urls["discovery-agent"],
                ca_cert_path=self.ca_cert_path,
                pull_secret=self.pull_secret,
                service_url=self.service_url,
                shared_storage=self.shared_graphroot,
                ssh_pub_key=self.ssh_pub_key,
                executor=self.executor,
                logging=self.logging,
                token=self.token,
                shared_graphroot=self.shared_graphroot,
                k8s_api_server_url=self.k8s_api_server_url,
                kube_cache=self.kube_cache,
                num_locks=num_locks,
            ),
        )

        self.logging.info("Launching cluster")
        return cluster.start()
