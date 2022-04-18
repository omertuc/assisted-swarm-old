package runners

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/openshift/assisted-installer-agent/src/commands"
	"github.com/openshift/assisted-installer-agent/src/commands/actions"
	"github.com/openshift/assisted-installer/src/config"
	"github.com/openshift/assisted-installer/src/installer"

	"github.com/go-openapi/swag"
	"github.com/hashicorp/go-version"
	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"github.com/spf13/afero"
	"github.com/thoas/go-funk"

	"github.com/openshift/assisted-service/models"
	"github.com/openshift/assisted-service/pkg/validations"
)

type installRunner struct {
	args          []string
	installParams models.InstallCmdRequest
	filesystem    afero.Fs
	installConfig *config.Config
	log           logrus.FieldLogger
}

func NewInstallerRunner(installConfig *config.Config, args []string, log logrus.FieldLogger) (commands.Runner, error) {
	ret := &installRunner{
		args:          args,
		installConfig: installConfig,
		filesystem:    afero.NewOsFs(),
		log:           log,
	}
	if err := ret.validate(); err != nil {
		return nil, err
	}
	if err := ret.merge(); err != nil {
		return nil, err
	}
	return ret, nil
}

func (a *installRunner) validate() error {
	err := actions.ValidateCommon("installRunner", 1, a.args, &a.installParams)
	if err != nil {
		return err
	}

	if a.installParams.MustGatherImage != "" {
		err = validateMustGatherImages(a.installParams.MustGatherImage)
		if err != nil {
			return err
		}
	}

	if a.installParams.Proxy != nil {
		err = validateProxy(a.installParams.Proxy)
		if err != nil {
			return err
		}
	}

	if a.installParams.InstallerArgs != "" {
		var installAgs []string
		err := json.Unmarshal([]byte(a.installParams.InstallerArgs), &installAgs)
		if err != nil {
			a.log.WithError(err).Errorf("Failed to unmarshal installer args: json.Unmarshal, %s", a.installParams.InstallerArgs)
			return err
		}
		err = validations.ValidateInstallerArgs(installAgs)
		if err != nil {
			return err
		}
	}

	if a.installParams.OpenshiftVersion != "" {
		_, err := version.NewVersion(a.installParams.OpenshiftVersion)
		if err != nil {

			return errors.Wrapf(err, "Failed to parse OCP version %s", a.installParams.OpenshiftVersion)
		}
	}

	return a.validateDisks()
}

func (a *installRunner) merge() error {
	a.installConfig.Role = string(*a.installParams.Role)
	a.installConfig.ClusterID = a.installParams.ClusterID.String()
	a.installConfig.HostID = a.installParams.HostID.String()
	a.installConfig.Device = swag.StringValue(a.installParams.BootDevice)
	a.installConfig.HighAvailabilityMode = swag.StringValue(a.installParams.HighAvailabilityMode)
	a.installConfig.ControllerImage = swag.StringValue(a.installParams.ControllerImage)
	a.installConfig.MCOImage = a.installParams.McoImage
	a.installConfig.MustGatherImage = a.installParams.MustGatherImage
	a.installConfig.OpenshiftVersion = a.installParams.OpenshiftVersion

	a.installConfig.DisksToFormat = nil
	for _, diskToFormat := range a.installParams.DisksToFormat {
		a.installConfig.DisksToFormat = append(a.installConfig.DisksToFormat, diskToFormat)
	}

	/*
		boolean flag must be used either without value (flag present means True) or in the format of <flag>=True|False.
		format <boolean flag> <value> is not supported by golang flag package and will cause the flags processing to finish
		before processing the rest of the input flags
	*/
	a.installConfig.CheckClusterVersion = swag.BoolValue(a.installParams.CheckCvo)

	if a.installParams.InstallerArgs != "" {
		if err := json.Unmarshal([]byte(a.installParams.InstallerArgs), &a.installConfig.InstallerArgs); err != nil {
			return err
		}
	}

	if a.installParams.Proxy != nil {
		a.installConfig.HTTPProxy = swag.StringValue(a.installParams.Proxy.HTTPProxy)
		a.installConfig.HTTPSProxy = swag.StringValue(a.installParams.Proxy.HTTPSProxy)
		a.installConfig.NoProxy = swag.StringValue(a.installParams.Proxy.NoProxy)
	}
	a.installConfig.ServiceIPs = strings.Join(a.installParams.ServiceIps, ",")
	return nil
}

func validateProxy(proxy *models.Proxy) error {
	httpProxy := swag.StringValue(proxy.HTTPProxy)
	httpsProxy := swag.StringValue(proxy.HTTPSProxy)
	noProxy := swag.StringValue(proxy.NoProxy)

	if httpProxy != "" {
		err := validations.ValidateHTTPProxyFormat(httpProxy)
		if err != nil {
			return err
		}
	}

	if httpsProxy != "" {
		err := validations.ValidateHTTPProxyFormat(httpsProxy)
		if err != nil {
			return err
		}
	}

	if noProxy != "" {
		err := validations.ValidateNoProxyFormat(noProxy)
		if err != nil {
			return err
		}
	}

	return nil
}

func validateMustGatherImages(mustGatherImage string) error {
	var imageMap map[string]string
	err := json.Unmarshal([]byte(mustGatherImage), &imageMap)
	if err != nil {
		// must gather image can be a string and not json
		imageMap = map[string]string{"ocp": mustGatherImage}
	}
	r, errCompile := regexp.Compile(`^(([a-zA-Z0-9\-\.]+)(:[0-9]+)?\/)?[a-z0-9\._\-\/@]+[?::a-zA-Z0-9_\-.]+$`)
	if errCompile != nil {
		return errCompile
	}

	for op, image := range imageMap {
		if !r.MatchString(image) {
			return fmt.Errorf("must gather image %s validation failed %v", image, imageMap)
		}
		// TODO: adding check for supported operators
		if !funk.Contains([]string{"cnv", "lso", "ocs", "odf", "ocp"}, op) {
			return fmt.Errorf("operator name %s validation failed", op)
		}
	}
	return nil
}

func (a *installRunner) validateDisks() error {
	disksToValidate := append(a.installParams.DisksToFormat, swag.StringValue(a.installParams.BootDevice))
	for _, disk := range disksToValidate {
		if !strings.HasPrefix(disk, "/dev/") {
			return fmt.Errorf("disk %s should start of with /dev/", disk)
		}
		if !a.pathExists(disk) {
			return fmt.Errorf("disk %s was not found on the host", disk)
		}
	}
	return nil
}

func (a *installRunner) pathExists(path string) bool {
	if _, err := a.filesystem.Stat(path); os.IsNotExist(err) {
		return false
	} else if err != nil {
		a.log.WithError(err).Errorf("failed to verify path %s", path)
		return false
	}
	return true
}

func (a *installRunner) Run() (stdout, stderr string, exitCode int) {
	if err := installer.RunInstaller(a.installConfig, a.log); err != nil {
		return "", err.Error(), -1
	}
	return "", "", 0
}

func (a *installRunner) Command() string {
	return "installer"
}

func (a *installRunner) Args() []string {
	return a.args
}
