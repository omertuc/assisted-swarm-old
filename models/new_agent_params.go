// Code generated by go-swagger; DO NOT EDIT.

package models

// This file was generated by the swagger tool.
// Editing this file might prove futile when you re-run the swagger generate command

import (
	"context"

	"github.com/go-openapi/errors"
	"github.com/go-openapi/strfmt"
	"github.com/go-openapi/swag"
	"github.com/go-openapi/validate"
)

// NewAgentParams new agent params
//
// swagger:model new-agent-params
type NewAgentParams struct {

	// agent version
	AgentVersion string `json:"agent_version,omitempty"`

	// cacert
	Cacert string `json:"cacert,omitempty"`

	// containers conf
	ContainersConf string `json:"containers_conf,omitempty"`

	// containers storage conf
	ContainersStorageConf string `json:"containers_storage_conf,omitempty"`

	// dry cluster hosts path
	DryClusterHostsPath string `json:"dry_cluster_hosts_path,omitempty"`

	// dry fake reboot marker path
	DryFakeRebootMarkerPath string `json:"dry_fake_reboot_marker_path,omitempty"`

	// dry forced host id
	// Format: uuid
	DryForcedHostID strfmt.UUID `json:"dry_forced_host_id,omitempty"`

	// dry forced host ipv4
	// Pattern: ^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)[\/]([1-9]|[1-2][0-9]|3[0-2]?)$
	DryForcedHostIPV4 string `json:"dry_forced_host_ipv4,omitempty"`

	// dry forced hostname
	DryForcedHostname string `json:"dry_forced_hostname,omitempty"`

	// dry forced mac address
	// Format: mac
	DryForcedMacAddress strfmt.MAC `json:"dry_forced_mac_address,omitempty"`

	// infra env id
	// Format: uuid
	InfraEnvID strfmt.UUID `json:"infra_env_id,omitempty"`

	// pull secret
	PullSecret string `json:"pull_secret,omitempty"`

	// service url
	ServiceURL string `json:"service_url,omitempty"`
}

// Validate validates this new agent params
func (m *NewAgentParams) Validate(formats strfmt.Registry) error {
	var res []error

	if err := m.validateDryForcedHostID(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateDryForcedHostIPV4(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateDryForcedMacAddress(formats); err != nil {
		res = append(res, err)
	}

	if err := m.validateInfraEnvID(formats); err != nil {
		res = append(res, err)
	}

	if len(res) > 0 {
		return errors.CompositeValidationError(res...)
	}
	return nil
}

func (m *NewAgentParams) validateDryForcedHostID(formats strfmt.Registry) error {
	if swag.IsZero(m.DryForcedHostID) { // not required
		return nil
	}

	if err := validate.FormatOf("dry_forced_host_id", "body", "uuid", m.DryForcedHostID.String(), formats); err != nil {
		return err
	}

	return nil
}

func (m *NewAgentParams) validateDryForcedHostIPV4(formats strfmt.Registry) error {
	if swag.IsZero(m.DryForcedHostIPV4) { // not required
		return nil
	}

	if err := validate.Pattern("dry_forced_host_ipv4", "body", m.DryForcedHostIPV4, `^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)[\/]([1-9]|[1-2][0-9]|3[0-2]?)$`); err != nil {
		return err
	}

	return nil
}

func (m *NewAgentParams) validateDryForcedMacAddress(formats strfmt.Registry) error {
	if swag.IsZero(m.DryForcedMacAddress) { // not required
		return nil
	}

	if err := validate.FormatOf("dry_forced_mac_address", "body", "mac", m.DryForcedMacAddress.String(), formats); err != nil {
		return err
	}

	return nil
}

func (m *NewAgentParams) validateInfraEnvID(formats strfmt.Registry) error {
	if swag.IsZero(m.InfraEnvID) { // not required
		return nil
	}

	if err := validate.FormatOf("infra_env_id", "body", "uuid", m.InfraEnvID.String(), formats); err != nil {
		return err
	}

	return nil
}

// ContextValidate validates this new agent params based on context it is used
func (m *NewAgentParams) ContextValidate(ctx context.Context, formats strfmt.Registry) error {
	return nil
}

// MarshalBinary interface implementation
func (m *NewAgentParams) MarshalBinary() ([]byte, error) {
	if m == nil {
		return nil, nil
	}
	return swag.WriteJSON(m)
}

// UnmarshalBinary interface implementation
func (m *NewAgentParams) UnmarshalBinary(b []byte) error {
	var res NewAgentParams
	if err := swag.ReadJSON(b, &res); err != nil {
		return err
	}
	*m = res
	return nil
}
