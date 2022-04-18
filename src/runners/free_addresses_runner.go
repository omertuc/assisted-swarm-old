package runners

import (
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer-agent/src/free_addresses"
	"github.com/openshift/assisted-service/models"
	"github.com/sirupsen/logrus"
)

func NewFreeAddresses(args []string) (commands.Runner, error) {
	runner := &freeAddressesRunner{
		args: args,
	}
	if err := runner.validate(); err != nil {
		return nil, err
	}
	return runner, nil
}

type freeAddressesRunner struct {
	args []string
}

func (a *freeAddressesRunner) validate() error {
	modelToValidate := models.FreeAddressesRequest{}
	err := actions.ValidateCommon("free addresses", 1, a.args, &modelToValidate)
	return err
}

func (a *freeAddressesRunner) Run() (stdout, stderr string, exitCode int) {
	return free_addresses.GetFreeAddresses(a.args[0], &free_addresses.ProcessExecuter{}, logrus.StandardLogger())
}

func (a *freeAddressesRunner) Command() string {
	return "free_addresses"
}

func (a *freeAddressesRunner) Args() []string {
	return a.args
}
