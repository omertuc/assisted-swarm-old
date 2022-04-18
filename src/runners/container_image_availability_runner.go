package runners

import (
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/container_image_availability"
	"github.com/openshift/assisted-service/models"
	"github.com/sirupsen/logrus"
)

func NewImageAvailabilityRunner(subprocessConfig *config.SubprocessConfig, args []string) (commands.Runner, error) {
	ret := &imageAvailabilityRunner{
		args:             args,
		subprocessConfig: subprocessConfig,
	}
	if err := ret.validate(); err != nil {
		return nil, err
	}
	return ret, nil
}

type imageAvailabilityRunner struct {
	args             []string
	subprocessConfig *config.SubprocessConfig
}

func (a *imageAvailabilityRunner) validate() error {
	modelToValidate := models.ContainerImageAvailabilityRequest{}
	err := actions.ValidateCommon("image availability", 1, a.args, &modelToValidate)
	if err != nil {
		return err
	}
	return nil
}

func (a *imageAvailabilityRunner) Run() (stdout, stderr string, exitCode int) {
	return container_image_availability.Run(a.subprocessConfig, a.args[0], &container_image_availability.ProcessExecuter{}, logrus.StandardLogger())
}

func (a *imageAvailabilityRunner) Command() string {
	return "sh"
}

func (a *imageAvailabilityRunner) Args() []string {
	return a.args
}
