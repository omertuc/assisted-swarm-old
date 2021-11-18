#!/usr/bin/env python3

import plac
from swarm import Swarm
from pathlib import Path
import logging
from config import load_config
from taskpool import TaskPool

from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

log = logging.getLogger("rich")


@plac.pos("max_concurrent", "Max concurrent threads - recommended around 6 per core", type=int)
@plac.pos("test_plan", "A test plan file. See testplan.example.yaml", type=Path)
@plac.pos(
    "service_config", "A file containing details about the target service. See service_config.example.yaml", type=Path
)
def main(max_concurrent, test_plan, service_config):
    assert max_concurrent > 5, "Surely you can spare more than 5 concurrent threads?"

    logging.basicConfig(level=logging.INFO)

    pull_secret, service_config, test_plan = load_config(service_config, test_plan)

    with TaskPool(max_workers=max_concurrent) as taskpool:
        swarm = Swarm(
            pull_secret=pull_secret,
            service_url=service_config["service_endpoint"],
            ssh_pub_key=service_config["ssh_pub_key"],
        )

        swarm.start()

        execute_plan(taskpool, test_plan, swarm)

    swarm.logging.info(f"All clusters finished, exiting")
    swarm.finalize()


def execute_plan(taskpool, test_plan, swarm):
    clusters = [(c["single_node"], c["num_workers"]) for c in test_plan["clusters"] for _ in range(c["amount"])]

    for cluster_index, (single_node, num_workers) in enumerate(clusters):
        taskpool.submit(swarm.launch_cluster, cluster_index, taskpool, single_node, num_workers)

    taskpool.wait()


if __name__ == "__main__":
    try:
        plac.call(main)
    except Exception as e:
        logging.exception(e)
