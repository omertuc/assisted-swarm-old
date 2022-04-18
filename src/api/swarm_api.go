package api

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"sync/atomic"
	"time"

	"github.com/go-openapi/runtime/middleware"
	"github.com/go-openapi/swag"
	"github.com/omertuc/assisted-swarm/models"
	"github.com/omertuc/assisted-swarm/restapi/operations/swarm"
	"github.com/omertuc/assisted-swarm/src/agents"
	"github.com/omertuc/assisted-swarm/src/factories"
	"github.com/openshift/assisted-installer-agent/src/agent"
	agentConfig "github.com/openshift/assisted-installer-agent/src/config"
	"github.com/openshift/assisted-installer-agent/src/util"
	installerConfig "github.com/openshift/assisted-installer/src/config"
)

type SwarmAPI struct {
	nextId int64
}

func newError(code int32, err error) *models.Error {
	return &models.Error{
		Code:   swag.String(fmt.Sprintf("%d", code)),
		Href:   swag.String(""),
		ID:     &code,
		Kind:   swag.String("Error"),
		Reason: swag.String(err.Error()),
	}
}

func (s *SwarmAPI) CreateNewAgent(ctx context.Context, params swarm.CreateNewAgentParams) middleware.Responder {
	id := atomic.AddInt64(&s.nextId, 1)
	agentCfg := &agentConfig.AgentConfig{
		DryRunConfig: agentConfig.DryRunConfig{
			DryRunEnabled:        true,
			ForcedHostID:         params.NewAgentParams.DryForcedHostID.String(),
			ForcedHostIPv4:       params.NewAgentParams.DryForcedHostIPV4,
			ForcedMacAddress:     params.NewAgentParams.DryForcedMacAddress.String(),
			ForcedHostname:       params.NewAgentParams.DryForcedHostname,
			FakeRebootMarkerPath: params.NewAgentParams.DryFakeRebootMarkerPath,
		},
		ConnectivityConfig: agentConfig.ConnectivityConfig{
			TargetURL:          params.NewAgentParams.ServiceURL,
			InfraEnvID:         params.NewAgentParams.InfraEnvID.String(),
			AgentVersion:       params.NewAgentParams.AgentVersion,
			PullSecretToken:    params.NewAgentParams.PullSecret,
			InsecureConnection: true,
			CACertificatePath:  params.NewAgentParams.Cacert,
		},
		LoggingConfig: agentConfig.LoggingConfig{
			JournalLogging: true,
		},
		IntervalSecs: 60,
	}
	subprocessCfg := &agentConfig.SubprocessConfig{
		LoggingConfig: agentConfig.LoggingConfig{
			TextLogging:    false,
			JournalLogging: true,
		},
		DryRunConfig: agentCfg.DryRunConfig,
	}
	installerCfg := &installerConfig.Config{
		DryRunConfig: installerConfig.DryRunConfig{
			DryRunEnabled:          true,
			FakeRebootMarkerPath:   params.NewAgentParams.DryFakeRebootMarkerPath,
			ForcedHostID:           params.NewAgentParams.DryForcedHostID.String(),
			DryRunClusterHostsPath: params.NewAgentParams.DryClusterHostsPath,
		},
		InfraEnvID:           params.NewAgentParams.InfraEnvID.String(),
		URL:                  params.NewAgentParams.ServiceURL,
		AgentImage:           params.NewAgentParams.AgentVersion,
		PullSecretToken:      params.NewAgentParams.PullSecret,
		SkipCertVerification: true,
		CACertPath:           params.NewAgentParams.Cacert,
	}
	logSenderCfg := &agentConfig.LogsSenderConfig{
		AgentConfig:     *agentCfg,
		InfraEnvID:      params.NewAgentParams.InfraEnvID.String(),
		TargetURL:       params.NewAgentParams.ServiceURL,
		PullSecretToken: params.NewAgentParams.PullSecret,
	}
	log := util.NewJournalLogger("combined-agent", params.NewAgentParams.DryForcedHostID.String())
	if err := installerConfig.DryParseClusterHosts(params.NewAgentParams.DryClusterHostsPath, &installerCfg.ParsedClusterHosts); err != nil {
		log.WithError(err).Error("DryParseClusterHosts")
		return swarm.NewCreateNewAgentBadRequest().WithPayload(newError(http.StatusBadRequest, err))
	}
	newAgent, err := agents.NewAgent(id)
	if err != nil {
		log.WithError(err).Warnf("Cannot allocate agent %d id %s", id, params.NewAgentParams.DryForcedHostID.String())
		return swarm.NewDeleteAgentInternalServerError().WithPayload(newError(http.StatusInternalServerError, err))
	}
	go func() {
		defer agents.SetTerminated(id)

		factory := factories.NewNextStepRunnerFactory(subprocessCfg, installerCfg, logSenderCfg, log)
		agent.RunAgent(agentCfg, factory, log)
	}()
	return swarm.NewCreateNewAgentCreated().WithPayload(newAgent)
}

func (s *SwarmAPI) DeleteAgent(ctx context.Context, params swarm.DeleteAgentParams) middleware.Responder {
	err := agents.DeleteAgent(params.AgentID)
	if err != nil {
		return swarm.NewDeleteAgentNotFound().WithPayload(newError(http.StatusNotFound, err))
	}
	return swarm.NewDeleteAgentNoContent()
}

func (s *SwarmAPI) GetAgent(ctx context.Context, params swarm.GetAgentParams) middleware.Responder {
	agent := agents.GetAgent(params.AgentID)
	if agent == nil {
		return swarm.NewGetAgentNotFound().WithPayload(newError(http.StatusNotFound, fmt.Errorf("id %d was not found", params.AgentID)))
	}
	return swarm.NewGetAgentOK().WithPayload(agent)
}

func (s *SwarmAPI) ListAgents(ctx context.Context, params swarm.ListAgentsParams) middleware.Responder {
	return swarm.NewListAgentsOK().WithPayload(agents.ListAgents())
}

func (s *SwarmAPI) Exit(ctx context.Context, params swarm.ExitParams) middleware.Responder {
	go func() {
		time.Sleep(500 * time.Millisecond)
		os.Exit(0)
	}()
	return swarm.NewExitNoContent()
}

func (s *SwarmAPI) Health(ctx context.Context, params swarm.HealthParams) middleware.Responder {
	return swarm.NewHealthNoContent()
}
