from containerconfig import (
    ContainerStorageConfigWithGraphrootAndAdditionalImageStores,
    ContainerConfigWithEnvAndNumLocks,
    system_container_storage_config,
    system_container_config,
)


class WithContainerConfigs:
    def __init__(self, personal_graphroot, shared_graphroot, config_dir, num_locks):
        self.personal_graphroot = personal_graphroot
        self.shared_graphroot = shared_graphroot
        self.config_dir = config_dir
        self.num_locks = num_locks

    def create_container_configs(self, next_state):
        with ContainerStorageConfigWithGraphrootAndAdditionalImageStores(
            system_container_storage_config,
            graphroot=self.personal_graphroot,
            additional_image_stores=[str(self.shared_graphroot)],
            delete=False,
            dir=str(self.config_dir),
            prefix="container_storage_config_",
        ) as container_storage_config:
            self.container_storage_conf = container_storage_config

        with ContainerConfigWithEnvAndNumLocks(
            system_container_config,
            env=[
                "CONTAINERS_CONF",
                "CONTAINERS_STORAGE_CONF",
                "DRY_ENABLE",
                "DRY_HOST_ID",
                "DRY_FORCED_MAC_ADDRESS",
                "PULL_SECRET_TOKEN",
                "DRY_FORCED_HOSTNAME",
                "DRY_FORCED_HOST_IPV4",
                "DRY_FAKE_REBOOT_MARKER_PATH",
                "DRY_CLUSTER_HOSTS_PATH",
            ],
            num_locks=self.num_locks,
            delete=False,
            dir=str(self.config_dir),
            prefix="container_config_",
        ) as container_config:
            self.container_config = container_config

        return next_state
