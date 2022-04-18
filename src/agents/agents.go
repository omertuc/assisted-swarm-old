package agents

import (
	"fmt"
	"time"

	"github.com/cornelk/hashmap"
	"github.com/go-openapi/strfmt"
	"github.com/omertuc/assisted-swarm/models"
)

var agentList = &hashmap.HashMap{}

func NewAgent(id int64) (*models.Agent, error) {
	_, exists := agentList.Get(id)
	if exists {
		return nil, fmt.Errorf("agent %d already exists", id)
	}
	ret := &models.Agent{
		CreatedAt: strfmt.DateTime(time.Now()),
		ID:        id,
		Status:    models.AgentStatusRunning,
	}
	agentList.Set(id, ret)
	return ret, nil
}

func GetAgent(id int64) *models.Agent {
	value, exists := agentList.Get(id)
	if !exists {
		return nil
	}
	return value.(*models.Agent)
}

func ListAgents() models.AgentList {
	ret := make(models.AgentList, 0)
	for kv := range agentList.Iter() {
		ret = append(ret, kv.Value.(*models.Agent))
	}
	return ret
}

func SetTerminated(id int64) {
	agent := GetAgent(id)
	if agent == nil {
		return
	}
	agent.Status = models.AgentStatusTerminated
	agent.TerminatedAt = strfmt.DateTime(time.Now())
}

func DeleteAgent(id int64) error {
	_, exists := agentList.Get(id)
	if !exists {
		return fmt.Errorf("id %d does not exist", id)
	}
	agentList.Del(id)
	return nil
}
