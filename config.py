import json
import yaml
from pathlib import Path


def validate_test_plan(test_plan):
    if "clusters" not in test_plan:
        raise Exception("Test plan must have a 'clusters' field")

    clusters = test_plan["clusters"]

    if not isinstance(clusters, list):
        raise Exception("'clusters' field must be a list")

    for cluster in clusters:
        if "num_workers" not in cluster:
            raise Exception("Each cluster must have a 'num_workers' field")

        if "single_node" not in cluster:
            raise Exception("Each cluster must have a 'single_node' field")

        if "amount" not in cluster:
            raise Exception("Each cluster must have a 'num_locks' field")

        assert (
            cluster["num_workers"] == 0 or not cluster["single_node"]
        ), "Cannot have more than one worker node in a single node cluster"


def validate_service_config(service_config):
    if "service_endpoint" not in service_config:
        raise Exception("Service config must have a 'service_endpoint' field")

    if "pull_secret_file" not in service_config:
        raise Exception("Service config must have a 'pull_secret_file' field")

    with Path(service_config["pull_secret_file"]).open("r") as f:
        pull_secret = json.load(f)
        if "auths" not in pull_secret:
            raise Exception("Pull secret must have an 'auths' field")
    
    if "release_image" not in service_config:
        raise Exception("Service config must have a 'release_image' field")


def load_config(service_config, test_plan):
    with open(service_config, "r") as f:
        service_config = yaml.safe_load(f)

    validate_service_config(service_config)

    with open(service_config["pull_secret_file"], "r") as f:
        pull_secret = f.read().strip()

        # Remove all unnecessary whitespace from JSON so it goes more smoothly
        # through HTTP headers
        pull_secret = json.dumps(json.loads(pull_secret), separators=(",", ":"))

    with open(test_plan, "r") as f:
        test_plan = yaml.safe_load(f)

    validate_test_plan(test_plan)

    return pull_secret, service_config, test_plan

