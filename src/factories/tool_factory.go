package factories

import (
	"fmt"

	"github.com/omertuc/assisted-swarm/src/runners"
	"github.com/openshift/assisted-installer-agent/src/commands"
	agentConfig "github.com/openshift/assisted-installer-agent/src/config"
	installerConfig "github.com/openshift/assisted-installer/src/config"
	"github.com/openshift/assisted-service/models"
	"github.com/sirupsen/logrus"
)

type toolFactory struct {
	subprocessCfg *agentConfig.SubprocessConfig
	installerCfg  *installerConfig.Config
	logSenderCfg  *agentConfig.LogsSenderConfig
	log           logrus.FieldLogger
}

func (t *toolFactory) Create(agentConfig *agentConfig.AgentConfig, stepType models.StepType, command string, args []string) (runner commands.Runner, err error) {
	switch stepType {
	case models.StepTypeInventory:
		runner, err = runners.NewInventoryRunner(t.subprocessCfg, args)
	case models.StepTypeConnectivityCheck:
		runner, err = runners.NewConnectivityCheckRunner(agentConfig, args)
	case models.StepTypeFreeNetworkAddresses:
		runner, err = runners.NewFreeAddresses(args)
	case models.StepTypeNtpSynchronizer:
		runner, err = runners.NewNtpSynchronerRunner()
	case models.StepTypeInstallationDiskSpeedCheck:
		runner, err = runners.NewDiskSpeedCheckRunner(t.subprocessCfg, args)
	case models.StepTypeDomainResolution:
		runner, err = runners.NewDomainNameResolutionRunner(args)
	case models.StepTypeContainerImageAvailability:
		runner, err = runners.NewImageAvailabilityRunner(t.subprocessCfg, args)
	case models.StepTypeInstall:
		runner, err = runners.NewInstallerRunner(t.installerCfg, args, t.log)
	case models.StepTypeStopInstallation:
		runner, err = runners.NewStopInstallationRunner()
	case models.StepTypeLogsGather:
		runner, err = runners.NewLogsSenderRunner(t.logSenderCfg, args)
	default:
		err = fmt.Errorf("unexpected step type %s", stepType)
	}
	if err != nil {
		return nil, err
	}
	return
}
