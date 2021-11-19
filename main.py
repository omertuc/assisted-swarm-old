#!/usr/bin/env python3

import plac
from swarm import Swarm
from pathlib import Path
import logging
from config import load_config
from taskpool import TaskPool
from random import shuffle

from threading import Event
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

    with TaskPool(max_workers=max_concurrent) as agents_taskpool:
        with TaskPool(max_workers=max_concurrent) as clusters_taskpool:
            swarm = Swarm(
                pull_secret=pull_secret,
                service_url=service_config["service_endpoint"],
                ssh_pub_key=service_config["ssh_pub_key"],
            )

            swarm.start()

            execute_plan(agents_taskpool, clusters_taskpool, test_plan, swarm)

    swarm.logging.info(f"All clusters finished, exiting")
    swarm.finalize()


def execute_plan(agents_taskpool, clusters_taskpool, test_plan, swarm: Swarm):
    clusters = [(c["single_node"], c["num_workers"]) for c in test_plan["clusters"] for _ in range(c["amount"])]

    if test_plan.get("shuffle", False):
        shuffle(clusters)

    # We use a couple of events to allow cluster X to signal to cluster Y that
    # cluster X has launched all of its agents, and only then cluster Y will
    # launch its own agents. This allows us to launch clusters in parallel
    # while still giving a cluster that launched early a priority to launch all
    # of its agents before any of the clusters that were launched after it.
    # This prevents a situation where all clusters race to create agent
    # threads, saturating the thread pool, and as a result the clusters are in
    # a dead lock because non of them have enough agents to finish the
    # installation (a finished installation is necessary for agents to die and
    # make space in the thread pool). This synchronization of events events
    # makes it so that only a single cluster can have a partial amount of
    # agents launched. One cluster's "I've launched all of my agents" event is
    # another cluster's "can start all agents" event.

    # The reason we don't simply launch clusters one after the other is because
    # before launching agents, a cluster has a lot of work it needs to do, and
    # there's no reason for that work to be delayed. That mostly includes
    # creating CR's and waiting for the service to reconcile them.

    # Create an initial "dummy" event that is immediately set for the first cluster
    # since it doesn't have any cluster it needs to wait for.
    previous_cluster_started_all_agents = Event()
    previous_cluster_started_all_agents.set()

    for cluster_index, (single_node, num_workers) in enumerate(clusters):
        current_cluster_all_agents_started = Event()

        clusters_taskpool.submit(
            swarm.launch_cluster,
            cluster_index,
            agents_taskpool,
            single_node,
            num_workers,
            can_start_agents=previous_cluster_started_all_agents,
            all_agents_started=current_cluster_all_agents_started,
        )

        previous_cluster_started_all_agents = current_cluster_all_agents_started

    clusters_taskpool.wait()
    agents_taskpool.wait()


if __name__ == "__main__":
    try:
        plac.call(main)
    except Exception as e:
        logging.exception(e)
