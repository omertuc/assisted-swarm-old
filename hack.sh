# You're not supposed to run this as a script
exit 0

# A collection of utility functions for working with the swarm

# Launch
pushd assisted-swarm
sudo KUBECONFIG=/root/kubeconfig ./main.py 200 testplan.example.yaml service_config.example.yaml

# Delete all namespaces
export KUBECONFIG=/root/kubeconfig
oc get namespace -A -ojson | jq '.items[] | select(.metadata.name | test("swarm"))' | oc delete -f -

# Download agent logs
oc get agents -A -ojson | jq '.items[].metadata | select(.namespace | test("swarm-")).name' -r | xargs -I@ sh -c "sudo journalctl DRY_AGENT_ID=@ > @.logs"

# Show all installer logs
oc get agents -A -ojson | jq '.items[].metadata | select(.namespace | test("swarm-")).name' -r | xargs -I@ sh -c "echo @ && cat /var/log/assisted-installer-@.log | tail -1"

# Kill all processes
killall agent
pgrep assisted-installer-controller -f | xargs kill -9
pgrep next_step_runner -f | xargs kill -9

# Delete mounts
findmnt --json --list | jq '.filesystems[].target | select(test("/root/.cache/swarm"))' -r | xargs -L1 umount
