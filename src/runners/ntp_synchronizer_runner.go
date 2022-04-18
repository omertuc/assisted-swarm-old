package runners

import "github.com/openshift/assisted-installer-agent/src/commands"

func NewNtpSynchronerRunner() (commands.Runner, error) {
	return &ntpSynchronizerRunner{}, nil
}

type ntpSynchronizerRunner struct{}

func (a *ntpSynchronizerRunner) Run() (stdout, stderr string, exitCode int) {
	return `{"ntp_sources": []}`, "", 0
}

func (a *ntpSynchronizerRunner) Command() string {
	return "ntp-synchronizer"
}

func (a *ntpSynchronizerRunner) Args() []string {
	return nil
}
