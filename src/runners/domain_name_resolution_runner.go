package runners

import (
	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer-agent/src/domain_resolution"
	"github.com/openshift/assisted-service/models"
	log "github.com/sirupsen/logrus"
)

func NewDomainNameResolutionRunner(args []string) (commands.Runner, error) {
	ret := &domainResolution{
		args: args,
	}
	if err := ret.validate(); err != nil {
		return nil, err
	}
	return ret, nil
}

type domainResolution struct {
	args []string
}

func (a *domainResolution) validate() error {
	modelToValidate := models.DomainResolutionRequest{}
	err := actions.ValidateCommon("domain resolution", 1, a.args, &modelToValidate)
	if err != nil {
		return err
	}

	return nil
}

func (a *domainResolution) Run() (stdout, stderr string, exitCode int) {
	return domain_resolution.Run(a.args[0],
		&domain_resolution.DomainResolver{}, log.StandardLogger())
}

func (a *domainResolution) Command() string {
	return "domain_resolution"
}

func (a *domainResolution) Args() []string {
	return a.args
}
