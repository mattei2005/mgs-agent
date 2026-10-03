package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type DomainCheckResult struct {
	Host      string `json:"host"`
	Verified  bool   `json:"verified"`
	Message   string `json:"message"`
	CheckedAt string `json:"checked_at"`
}

// A saved check is the last observed result, not an always-online health claim.
func (a *App) loadDomainChecks() error {
	a.domainChecks = map[string]DomainCheckResult{}
	b, err := os.ReadFile(filepath.Join(a.dir, "domain-checks.json"))
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	dec := json.NewDecoder(strings.NewReader(string(b)))
	dec.DisallowUnknownFields()
	var checks map[string]DomainCheckResult
	if dec.Decode(&checks) != nil || len(checks) > 1001 {
		return errors.New("invalid domain verification store")
	}
	// Unmarshal also rejects trailing JSON values without exposing any content.
	if json.Unmarshal(b, &checks) != nil {
		return errors.New("invalid domain verification store")
	}
	for host, c := range checks {
		if host != c.Host || (!validDomain(host, a.adminHost) && host != a.adminHost) || !a.registered(host) || len(c.Message) == 0 || len(c.Message) > 2048 {
			return errors.New("invalid domain verification record")
		}
		if _, err := time.Parse(time.RFC3339, c.CheckedAt); err != nil {
			return errors.New("invalid domain verification timestamp")
		}
	}
	if checks != nil {
		a.domainChecks = checks
	}
	return nil
}
func (a *App) saveDomainCheck(result DomainCheckResult) error {
	a.mu.Lock()
	defer a.mu.Unlock()
	next := make(map[string]DomainCheckResult, len(a.domainChecks)+1)
	for host, check := range a.domainChecks {
		next[host] = check
	}
	next[result.Host] = result
	if err := atomicJSON(filepath.Join(a.dir, "domain-checks.json"), next); err != nil {
		return err
	}
	a.domainChecks = next
	return nil
}
