package main

import (
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Domains have their own revision so adding a host cannot overwrite route edits.
type DomainMetadata struct {
	ID    int    `json:"id"`
	Group string `json:"group,omitempty"`
}
type DomainConfig struct {
	Revision    int                       `json:"revision"`
	Domains     []string                  `json:"domains"`
	GroupSchema int                       `json:"group_schema,omitempty"`
	Groups      []string                  `json:"domain_groups,omitempty"`
	Metadata    map[string]DomainMetadata `json:"metadata,omitempty"`
}

func validateDomainMetadata(c DomainConfig, persisted bool) error {
	if c.GroupSchema == 0 {
		if len(c.Groups) > 0 || len(c.Metadata) > 0 {
			return errors.New("domain metadata requires schema1")
		}
		return nil
	}
	if c.GroupSchema != 1 || len(c.Groups) > 1000 {
		return errors.New("invalid domain group schema")
	}
	groups := map[string]bool{}
	for _, g := range c.Groups {
		if !validLabel(g) || groups[g] {
			return errors.New("invalid domain group")
		}
		groups[g] = true
	}
	hosts := map[string]bool{}
	for _, host := range c.Domains {
		hosts[host] = true
	}
	ids := map[int]bool{}
	for host, m := range c.Metadata {
		if !hosts[host] || m.ID < 0 || (persisted && m.ID == 0) || (m.Group != "" && !groups[m.Group]) || (m.ID > 0 && ids[m.ID]) {
			return errors.New("invalid domain metadata")
		}
		if m.ID > 0 {
			ids[m.ID] = true
		}
	}
	if persisted && len(c.Metadata) != len(c.Domains) {
		return errors.New("missing domain metadata")
	}
	return nil
}

func validDomain(host, admin string) bool {
	if host == admin || len(host) > 253 || host != strings.ToLower(host) || !strings.Contains(host, ".") || net.ParseIP(host) != nil || strings.HasSuffix(host, ".local") || strings.HasSuffix(host, ".internal") {
		return false
	}
	for _, label := range strings.Split(host, ".") {
		if len(label) == 0 || len(label) > 63 || label[0] == '-' || label[len(label)-1] == '-' {
			return false
		}
		for _, c := range label {
			if !(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '-') {
				return false
			}
		}
	}
	return true
}
func (a *App) loadDomains() error {
	b, e := os.ReadFile(filepath.Join(a.dir, "domains.json"))
	if os.IsNotExist(e) {
		a.domains = DomainConfig{Domains: []string{}}
		return nil
	}
	if e != nil {
		return e
	}
	var c DomainConfig
	if json.Unmarshal(b, &c) != nil || c.Revision < 0 {
		return errors.New("invalid domain store")
	}
	seen := map[string]bool{}
	for _, d := range c.Domains {
		if !validDomain(d, a.adminHost) || seen[d] {
			return errors.New("invalid domain store")
		}
		seen[d] = true
	}
	if e := validateDomainMetadata(c, true); e != nil {
		return e
	}
	a.domains = c
	return nil
}
func (a *App) domainReply() any {
	a.mu.RLock()
	defer a.mu.RUnlock()
	all := map[string]bool{}
	for _, d := range a.domains.Domains {
		all[d] = true
	}
	for _, r := range a.cfg.Routes {
		all[r.Host] = true
	}
	names := make([]string, 0, len(all))
	for d := range all {
		names = append(names, d)
	}
	sort.Strings(names)
	checks := make(map[string]DomainCheckResult)
	for _, host := range names {
		if check, ok := a.domainChecks[host]; ok {
			checks[host] = check
		}
	}
	return struct {
		Revision    int                          `json:"revision"`
		Domains     []string                     `json:"domains"`
		Checks      map[string]DomainCheckResult `json:"checks"`
		DNS         map[string]string            `json:"dns"`
		GroupSchema int                          `json:"group_schema,omitempty"`
		Groups      []string                     `json:"domain_groups"`
		Metadata    map[string]DomainMetadata    `json:"metadata"`
	}{a.domains.Revision, names, checks, map[string]string{"type": "A", "value": "2.25.165.171", "ttl": "Auto", "proxy": "Proxied (nuvem laranja)", "ssl": "Full", "mode": "cloudflare_required", "notice": "A origem aceita apenas conexões do proxy Cloudflare. Em outro provedor, primeiro delegue a zona ao Cloudflare; DNS direto não funcionará. Não mude DNS de domínio já ativo sem planejar a troca de tráfego."}, a.domains.GroupSchema, a.domains.Groups, a.domains.Metadata}
}
func (a *App) domainAPI(w http.ResponseWriter, r *http.Request, s Session) {
	if r.Method == "GET" {
		jsonReply(w, 200, a.domainReply())
		return
	}
	if r.Method != "POST" {
		w.WriteHeader(405)
		return
	}
	if !a.csrf(r, s) {
		jsonReply(w, 403, map[string]string{"error": "invalid request origin or csrf"})
		return
	}
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		jsonReply(w, 415, map[string]string{"error": "JSON required"})
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 128<<10)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var c DomainConfig
	if dec.Decode(&c) != nil || dec.Decode(&struct{}{}) != io.EOF || len(c.Domains) > 1000 {
		jsonReply(w, 400, map[string]string{"error": "invalid domain JSON"})
		return
	}
	seen := map[string]bool{}
	for _, d := range c.Domains {
		if !validDomain(d, a.adminHost) || seen[d] {
			jsonReply(w, 400, map[string]string{"error": "Domínio inválido ou repetido. Informe apenas dominio.com ou sub.dominio.com, sem URL ou caminho."})
			return
		}
		seen[d] = true
	}
	a.mu.Lock()
	if c.Revision != a.domains.Revision {
		a.mu.Unlock()
		jsonReply(w, 409, map[string]string{"error": "Lista de domínios alterada; recarregue antes de salvar."})
		return
	}
	// This endpoint is additive; removals require a separately approved workflow.
	for _, d := range a.domains.Domains {
		if !seen[d] {
			a.mu.Unlock()
			jsonReply(w, 400, map[string]string{"error": "Domínios existentes devem ser preservados."})
			return
		}
	}
	if a.domains.GroupSchema == 1 && c.GroupSchema != 1 {
		a.mu.Unlock()
		jsonReply(w, 400, map[string]string{"error": "Grupos de domínios devem ser preservados; recarregue o painel."})
		return
	}
	if e := validateDomainMetadata(c, false); e != nil {
		a.mu.Unlock()
		jsonReply(w, 400, map[string]string{"error": "Grupos ou metadados de domínio inválidos."})
		return
	}
	if c.GroupSchema == 1 {
		if c.Metadata == nil {
			c.Metadata = map[string]DomainMetadata{}
		}
		maxID := 0
		for _, m := range a.domains.Metadata {
			if m.ID > maxID {
				maxID = m.ID
			}
		}
		for host, m := range c.Metadata {
			old, exists := a.domains.Metadata[host]
			if (exists && m.ID != old.ID) || (!exists && m.ID != 0) {
				a.mu.Unlock()
				jsonReply(w, 400, map[string]string{"error": "ID de domínio não pode ser alterado."})
				return
			}
		}
		sort.Strings(c.Domains)
		for _, host := range c.Domains {
			m := c.Metadata[host]
			if old, exists := a.domains.Metadata[host]; exists && m.ID != old.ID {
				a.mu.Unlock()
				jsonReply(w, 400, map[string]string{"error": "Metadados existentes devem ser preservados."})
				return
			}
			if m.ID == 0 {
				maxID++
				m.ID = maxID
			}
			c.Metadata[host] = m
		}
		if e := validateDomainMetadata(c, true); e != nil {
			a.mu.Unlock()
			jsonReply(w, 400, map[string]string{"error": "Metadados inválidos."})
			return
		}
	}
	c.Revision++
	sort.Strings(c.Domains)
	if c.Domains == nil {
		c.Domains = []string{}
	}
	if e := atomicJSON(filepath.Join(a.dir, "domains.json"), c); e != nil {
		a.mu.Unlock()
		jsonReply(w, 500, map[string]string{"error": "Não foi possível persistir domínios."})
		return
	}
	a.domains = c
	a.mu.Unlock()
	jsonReply(w, 200, a.domainReply())
}
