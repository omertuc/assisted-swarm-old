package runners

import (
	"strconv"

	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/disk_speed_check"
	"github.com/openshift/assisted-service/models"
	"github.com/sirupsen/logrus"
)

func NewDiskSpeedCheckRunner(subprocessConfig *config.SubprocessConfig, args []string) (commands.Runner, error) {
	ret := &diskSpeedCheckRunner{
		args:             args,
		subprocessConfig: subprocessConfig,
	}
	if err := ret.validate(); err != nil {
		return nil, err
	}
	return ret, nil
}

type diskSpeedCheckRunner struct {
	args             []string
	subprocessConfig *config.SubprocessConfig
}

func (a *diskSpeedCheckRunner) validate() error {
	modelToValidate := models.DiskSpeedCheckRequest{}
	err := actions.ValidateCommon("disk performance", 2, a.args, &modelToValidate)
	if err != nil {
		return err
	}
	if _, err := strconv.ParseFloat(a.args[1], 64); err != nil {
		logrus.WithError(err).Errorf("Failed to parse timeout value to float: %s", a.args[1])
		return err
	}

	return nil
}

func (a *diskSpeedCheckRunner) Command() string {
	return "disk_speed_check"
}

func (a *diskSpeedCheckRunner) Args() []string {
	return a.args
}

func (a *diskSpeedCheckRunner) Run() (stdout, stderr string, exitCode int) {
	perfCheck := disk_speed_check.NewDiskSpeedCheck(a.subprocessConfig, disk_speed_check.NewDependencies())
	return perfCheck.FioPerfCheck(a.args[0], logrus.StandardLogger())
}
