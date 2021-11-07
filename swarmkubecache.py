import subprocess
import json
import time
from threading import Event


class SwarmKubeCache:
    """
    Periodically fetch swarm-related kube-api objects and store them in a cache.
    This gives swarm agents an in-memory cache of the kube-api objects, to avoid each agent
    blasting the kube-api endpoint with requests (and consuming a lot of memory, CPU, and network
    resources in the process).
    """
    def __init__(self, done: Event):
        self.cache = {
            "agentclusterinstalls": {},
            "baremetalhosts": {},
            "infraenvs": {},
        }

        self.done = done

    def get_infraenv(self, name, namespace):
        return self.cache["infraenvs"].get(f"{namespace}/{name}", None)

    def get_agent_cluster_install(self, name, namespace):
        return self.cache["agentclusterinstalls"].get(f"{namespace}/{name}", None)

    def get_baremetalhost(self, name, namespace):
        return self.cache["baremetalhosts"].get(f"{namespace}/{name}", None)

    def cache_api_type(self, api_type):
        """
        Cache all the kube-api objects of a given type.
        """
        result = json.loads(subprocess.check_output(["oc", "get", api_type, "-A", "-ojson"]).decode("utf-8"))

        for api_object in result["items"]:
            self.cache[api_type][f"{api_object['metadata']['namespace']}/{api_object['metadata']['name']}"] = api_object

    def monitor(self):
        while not self.done.is_set():
            for api_type in self.cache:
                try:
                    self.cache_api_type(api_type)
                except Exception:
                    # API is imperfect, this is okay, just try again later
                    pass

            time.sleep(5)

