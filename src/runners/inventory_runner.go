package runners

import (
	"fmt"

	"github.com/go-openapi/strfmt"
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	agentConfig "github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/inventory"
)

func NewInventoryRunner(subprocessCfg *agentConfig.SubprocessConfig, args []string) (commands.Runner, error) {
	runner := &inventoryRunner{
		subprocessCfg: subprocessCfg,
		args:          args,
	}
	if err := runner.validate(); err != nil {
		return nil, err
	}
	return runner, nil
}

type inventoryRunner struct {
	subprocessCfg *agentConfig.SubprocessConfig
	args          []string
}

func (i *inventoryRunner) Run() (stdout, stderr string, exitCode int) {
	return string(inventory.CreateInventoryInfo(i.subprocessCfg)), "", 0
}

func (i *inventoryRunner) Command() string {
	return "inventory"
}

func (i *inventoryRunner) Args() []string {
	return i.args
}

func (i *inventoryRunner) validate() error {
	err := actions.ValidateCommon("inventory", 1, i.args, nil)
	if err != nil {
		return err
	}
	if !strfmt.IsUUID(i.args[0]) {
		return fmt.Errorf("inventory cmd accepts only 1 params in args and it should be UUID, given args %v", i.args)
	}
	return nil
}
