package factories

import (
	"context"
	"sync"
	"time"

	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	agentConfig "github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/util"
	installerConfig "github.com/openshift/assisted-installer/src/config"
	"github.com/openshift/assisted-service/models"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
)

type nextStepRunnerFactory struct {
	installerCfg  *installerConfig.Config
	subprocessCfg *agentConfig.SubprocessConfig
	logSenderCfg  *agentConfig.LogsSenderConfig
	log           logrus.FieldLogger
}

func NewNextStepRunnerFactory(subprocessCfg *agentConfig.SubprocessConfig, installCfg *installerConfig.Config,
	logSenderCfg *agentConfig.LogsSenderConfig, log logrus.FieldLogger) commands.NextStepRunnerFactory {
	return &nextStepRunnerFactory{
		subprocessCfg: subprocessCfg,
		installerCfg:  installCfg,
		logSenderCfg:  logSenderCfg,
		log:           log,
	}
}

func (a *nextStepRunnerFactory) parse(args []string) (*models.NextStepCmdRequest, error) {
	ret := models.NextStepCmdRequest{}
	err := actions.ValidateCommon("next step runner", 1, args, &ret)
	if err != nil {
		return nil, err
	}
	return &ret, nil
}

func (n *nextStepRunnerFactory) Create(agentCfg *agentConfig.AgentConfig, command string, args []string) (commands.Runner, error) {
	req, err := n.parse(args)
	if err != nil {
		return nil, errors.Wrapf(err, "parse args %+v", args)
	}
	agentCfg.HostID = req.HostID.String()
	return &nextStepRunner{
		args:          args,
		agentCfg:      agentCfg,
		subprocessCfg: n.subprocessCfg,
		installerCfg:  n.installerCfg,
		logSenderCfg:  n.logSenderCfg,
		log:           n.log,
	}, nil
}

type nextStepRunner struct {
	args          []string
	agentCfg      *agentConfig.AgentConfig
	subprocessCfg *agentConfig.SubprocessConfig
	installerCfg  *installerConfig.Config
	logSenderCfg  *agentConfig.LogsSenderConfig
	log           logrus.FieldLogger
}

func (n *nextStepRunner) Run() (stdout, stderr string, exitCode int) {
	ctx, cancel := context.WithCancel(context.Background())
	running := true
	defer func() {
		running = false
	}()
	go func() {
		for running {
			if util.DryRebootHappened(&n.agentCfg.DryRunConfig) {
				n.log.Info("Dry reboot happened, exiting")
				cancel()
				break
			}

			time.Sleep(time.Second)
		}
	}()
	var wg sync.WaitGroup
	wg.Add(1)
	factory := &toolFactory{
		subprocessCfg: n.subprocessCfg,
		installerCfg:  n.installerCfg,
		logSenderCfg:  n.logSenderCfg,
		log:           n.log,
	}
	commands.ProcessSteps(ctx, n.agentCfg, factory, &wg, n.log)
	return "", "", 0
}

func (n *nextStepRunner) Command() string {
	return "next_step_runner"
}

func (n *nextStepRunner) Args() []string {
	return n.args
}
