package runners

import (
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	agentConfig "github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/connectivity_check"
	"github.com/openshift/assisted-service/models"
)

func NewConnectivityCheckRunner(agentCfg *agentConfig.AgentConfig, args []string) (commands.Runner, error) {
	runner := &connectivityCheckRunner{agentConfig: agentCfg, args: args}
	if err := runner.validate(); err != nil {
		return nil, err
	}
	return runner, nil
}

type connectivityCheckRunner struct {
	agentConfig *agentConfig.AgentConfig
	args        []string
}

func (a *connectivityCheckRunner) validate() error {
	modelToValidate := models.ConnectivityCheckParams{}
	err := actions.ValidateCommon("connectivity check", 1, a.args, &modelToValidate)
	if err != nil {
		return err
	}

	return nil
}

func (a *connectivityCheckRunner) Command() string {
	return "connectivity_check"
}

func (a *connectivityCheckRunner) Args() []string {
	return a.args
}

func (a *connectivityCheckRunner) Run() (stdout, stderr string, exitCode int) {
	return connectivity_check.ConnectivityCheck(&a.agentConfig.DryRunConfig, "", a.args...)
}
