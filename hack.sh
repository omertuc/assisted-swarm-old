# You're not supposed to run this as a script

exit 0

# A collection of utility functions for working with the swarm

# Launch
pushd assisted-swarm
sudo KUBECONFIG=/root/kubeconfig ./main.py 200 testplan.example.yaml service_config.example.yaml

# Download agent logs
export KUBECONFIG=/root/kubeconfig
oc get agents -A -ojson | jq '.items[].metadata | select(.namespace | test("swarm-")).name' -r | xargs -I@ sh -c "sudo journalctl DRY_AGENT_ID=@ > @.logs"

# Show all installer logs
export KUBECONFIG=/root/kubeconfig
oc get agents -A -ojson | jq '.items[].metadata | select(.namespace | test("swarm-")).name' -r | xargs -I@ sh -c "echo @ && cat /var/log/assisted-installer-@.log | tail -1"

# Delete all namespaces
export KUBECONFIG=/root/kubeconfig
oc get namespace -A -ojson | jq '.items[] | select(.metadata.name | test("swarm"))' | oc delete -f -

# Kill all processes
killall agent
pgrep assisted-installer-controller -f | xargs kill -9
pgrep next_step_runner -f | xargs kill -9

# Delete mounts
findmnt --json --list | jq '.filesystems[].target | select(test("/root/.cache/swarm"))' -r | xargs -L1 umount
findmnt --json --list | jq '.filesystems[].target | select(test("/root/.cache/swarm"))' -r | xargs -L1 umount
findmnt --json --list | jq '.filesystems[].target | select(test("/root/.cache/swarm"))' -r | xargs -L1 umount
findmnt --json --list | jq '.filesystems[].target | select(test("/root/.cache/swarm"))' -r | xargs -L1 umount

# Cleanup
rm -rf /var/log/assisted-installer-*.log
rm -rf /root/mtab-*
rm -rf /root/.cache/swarm/swarm-*

# Prometheus instance
docker run \
    --net host \
    -p 9090:9090 \
    -v $PWD/prometheus.yml:/etc/prometheus/prometheus.yml \
    prom/prometheus

# Prometheus prometheus.yml
"
global:
  scrape_interval: 5s 

scrape_configs:
  - job_name: 'swarm'
    static_configs:
      - targets: ['localhost:9100']
  - job_name: 'ai'
    scheme: https
    static_configs:
      - targets: ['assisted-service-open-cluster-management.apps.jetlag-ibm0.performance-scale.cloud:443']
    tls_config:
      insecure_skip_verify: true
"
