// Code generated by go-swagger; DO NOT EDIT.

package restapi

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/go-openapi/errors"
	"github.com/go-openapi/loads"
	"github.com/go-openapi/runtime"
	"github.com/go-openapi/runtime/middleware"
	"github.com/go-openapi/runtime/security"

	"github.com/omertuc/assisted-swarm/restapi/operations"
	"github.com/omertuc/assisted-swarm/restapi/operations/swarm"
)

type contextKey string

const AuthKey contextKey = "Auth"

//go:generate mockery -name SwarmAPI -inpkg

/* SwarmAPI  */
type SwarmAPI interface {
	/* CreateNewAgent Create new agent. */
	CreateNewAgent(ctx context.Context, params swarm.CreateNewAgentParams) middleware.Responder

	/* DeleteAgent Delete agent. */
	DeleteAgent(ctx context.Context, params swarm.DeleteAgentParams) middleware.Responder

	/* Exit Exit the process. */
	Exit(ctx context.Context, params swarm.ExitParams) middleware.Responder

	/* GetAgent Get specific agent. */
	GetAgent(ctx context.Context, params swarm.GetAgentParams) middleware.Responder

	/* Health Health check. */
	Health(ctx context.Context, params swarm.HealthParams) middleware.Responder

	/* ListAgents List all running agents. */
	ListAgents(ctx context.Context, params swarm.ListAgentsParams) middleware.Responder
}

// Config is configuration for Handler
type Config struct {
	SwarmAPI
	Logger func(string, ...interface{})
	// InnerMiddleware is for the handler executors. These do not apply to the swagger.json document.
	// The middleware executes after routing but before authentication, binding and validation
	InnerMiddleware func(http.Handler) http.Handler

	// Authorizer is used to authorize a request after the Auth function was called using the "Auth*" functions
	// and the principal was stored in the context in the "AuthKey" context value.
	Authorizer func(*http.Request) error

	// Authenticator to use for all APIKey authentication
	APIKeyAuthenticator func(string, string, security.TokenAuthentication) runtime.Authenticator
	// Authenticator to use for all Bearer authentication
	BasicAuthenticator func(security.UserPassAuthentication) runtime.Authenticator
	// Authenticator to use for all Basic authentication
	BearerAuthenticator func(string, security.ScopedTokenAuthentication) runtime.Authenticator
}

// Handler returns an http.Handler given the handler configuration
// It mounts all the business logic implementers in the right routing.
func Handler(c Config) (http.Handler, error) {
	h, _, err := HandlerAPI(c)
	return h, err
}

// HandlerAPI returns an http.Handler given the handler configuration
// and the corresponding *AssistedSwarm instance.
// It mounts all the business logic implementers in the right routing.
func HandlerAPI(c Config) (http.Handler, *operations.AssistedSwarmAPI, error) {
	spec, err := loads.Analyzed(swaggerCopy(SwaggerJSON), "")
	if err != nil {
		return nil, nil, fmt.Errorf("analyze swagger: %v", err)
	}
	api := operations.NewAssistedSwarmAPI(spec)
	api.ServeError = errors.ServeError
	api.Logger = c.Logger

	if c.APIKeyAuthenticator != nil {
		api.APIKeyAuthenticator = c.APIKeyAuthenticator
	}
	if c.BasicAuthenticator != nil {
		api.BasicAuthenticator = c.BasicAuthenticator
	}
	if c.BearerAuthenticator != nil {
		api.BearerAuthenticator = c.BearerAuthenticator
	}

	api.JSONConsumer = runtime.JSONConsumer()
	api.JSONProducer = runtime.JSONProducer()
	api.SwarmCreateNewAgentHandler = swarm.CreateNewAgentHandlerFunc(func(params swarm.CreateNewAgentParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.CreateNewAgent(ctx, params)
	})
	api.SwarmDeleteAgentHandler = swarm.DeleteAgentHandlerFunc(func(params swarm.DeleteAgentParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.DeleteAgent(ctx, params)
	})
	api.SwarmExitHandler = swarm.ExitHandlerFunc(func(params swarm.ExitParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.Exit(ctx, params)
	})
	api.SwarmGetAgentHandler = swarm.GetAgentHandlerFunc(func(params swarm.GetAgentParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.GetAgent(ctx, params)
	})
	api.SwarmHealthHandler = swarm.HealthHandlerFunc(func(params swarm.HealthParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.Health(ctx, params)
	})
	api.SwarmListAgentsHandler = swarm.ListAgentsHandlerFunc(func(params swarm.ListAgentsParams) middleware.Responder {
		ctx := params.HTTPRequest.Context()
		return c.SwarmAPI.ListAgents(ctx, params)
	})
	api.ServerShutdown = func() {}
	return api.Serve(c.InnerMiddleware), api, nil
}

// swaggerCopy copies the swagger json to prevent data races in runtime
func swaggerCopy(orig json.RawMessage) json.RawMessage {
	c := make(json.RawMessage, len(orig))
	copy(c, orig)
	return c
}

// authorizer is a helper function to implement the runtime.Authorizer interface.
type authorizer func(*http.Request) error

func (a authorizer) Authorize(req *http.Request, principal interface{}) error {
	if a == nil {
		return nil
	}
	ctx := storeAuth(req.Context(), principal)
	return a(req.WithContext(ctx))
}

func storeAuth(ctx context.Context, principal interface{}) context.Context {
	return context.WithValue(ctx, AuthKey, principal)
}
