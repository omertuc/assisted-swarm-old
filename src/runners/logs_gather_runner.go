package runners

import (
	"strings"

	"github.com/go-openapi/swag"
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/logs_sender"
	"github.com/openshift/assisted-service/models"
)

func NewLogsSenderRunner(logsSenderConfig *config.LogsSenderConfig, args []string) (commands.Runner, error) {
	ret := &logsGatherRunner{
		args:             args,
		logsSenderConfig: logsSenderConfig,
	}
	if err := ret.validate(); err != nil {
		return nil, err
	}
	ret.merge()
	return ret, nil
}

type logsGatherRunner struct {
	args             []string
	logsSenderConfig *config.LogsSenderConfig
	params           models.LogsGatherCmdRequest
}

func (a *logsGatherRunner) validate() error {
	name := "logs gather"
	return actions.ValidateCommon(name, 1, a.args, &a.params)
}

func (a *logsGatherRunner) merge() {
	a.logsSenderConfig.ClusterID = a.params.ClusterID.String()
	a.logsSenderConfig.HostID = a.params.HostID.String()
	a.logsSenderConfig.IsBootstrap = swag.BoolValue(a.params.Bootstrap)
	a.logsSenderConfig.InstallerGatherlogging = a.params.InstallerGather
	a.logsSenderConfig.MastersIPs = strings.Join(a.params.MasterIps, ",")
}

func (a *logsGatherRunner) Run() (stdout, stderr string, exitCode int) {
	err, report := logs_sender.SendLogs(a.logsSenderConfig, logs_sender.NewLogsSenderExecuter(a.logsSenderConfig, a.logsSenderConfig.TargetURL,
		a.logsSenderConfig.PullSecretToken,
		a.logsSenderConfig.AgentVersion))
	if err != nil {
		return "", err.Error(), -1
	}
	return report, "", 0
}

func (a *logsGatherRunner) Command() string {
	return "logs_sender"
}

func (a *logsGatherRunner) Args() []string {
	return a.args
}
