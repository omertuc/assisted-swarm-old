from adjustedtoml import AdjustedToml
from typing import List


system_container_storage_config = r"/etc/containers/storage.conf"
system_container_config = r"/usr/share/containers/containers.conf"


class ContainerStorageConfigWithGraphroot(AdjustedToml):
    def __init__(self, container_storage_config, graphroot, dir="", delete=True, prefix=None):
        self.graphroot = graphroot
        super().__init__(container_storage_config, self.adjust, dir=dir, delete=delete, prefix=prefix)

    def adjust(self, original_conf):
        adjusted_conf = original_conf
        adjusted_conf["storage"]["graphroot"] = str(self.graphroot)
        return adjusted_conf


class ContainerStorageConfigWithGraphrootAndAdditionalImageStores(AdjustedToml):
    def __init__(self, container_storage_config, graphroot, additional_image_stores: List[str], dir="", delete=True, prefix=None):
        self.graphroot = graphroot
        self.additional_image_stores = additional_image_stores
        super().__init__(container_storage_config, self.adjust, dir=dir, delete=delete, prefix=prefix)

    def adjust(self, original_conf):
        adjusted_conf = original_conf
        adjusted_conf["storage"]["options"]["additionalimagestores"].extend(self.additional_image_stores)
        adjusted_conf["storage"]["graphroot"] = str(self.graphroot)
        return adjusted_conf


class ContainerConfigWithEnvAndNumLocks(AdjustedToml):
    def __init__(self, container_config, env: List[str], num_locks, dir="", delete=True, prefix=None):
        self.env = env
        self.num_locks = num_locks
        super().__init__(container_config, self.adjust, dir=dir, delete=delete, prefix=prefix)

    def adjust(self, original_conf):
        adjusted_conf = original_conf
        if "env" not in adjusted_conf["containers"]:
            adjusted_conf["containers"]["env"] = []
        adjusted_conf["containers"]["env"].extend(self.env)
        adjusted_conf["engine"]["num_locks"] = self.num_locks
        return adjusted_conf

