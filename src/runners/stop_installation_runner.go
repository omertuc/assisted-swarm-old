package runners

import "github.com/openshift/assisted-installer-agent/src/commands"

func NewStopInstallationRunner() (commands.Runner, error) {
	return &stopInstallationRunner{}, nil
}

type stopInstallationRunner struct{}

func (a *stopInstallationRunner) Run() (stdout, stderr string, exitCode int) {
	return "", "", 0
}

func (a *stopInstallationRunner) Command() string {
	return "stop_installation"
}

func (a *stopInstallationRunner) Args() []string {
	return []string{}
}
