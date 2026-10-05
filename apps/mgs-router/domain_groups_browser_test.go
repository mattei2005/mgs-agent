package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http/httptest"
	"net/url"
	"os/exec"
	"testing"
)

func TestDomainGroupsBrowserWorkflow(t *testing.T) {
	a := fixture(t)
	c := Config{ActionSchema: 1, GroupSchema: 2, RouteGroups: []string{"Main", "Other"}, DestinationGroups: []string{"Main", "Other"}, Routes: []Route{}, Catalog: []Destination{}}
	for i := 0; i < 65; i++ {
		g := "Main"
		if i >= 40 {
			g = "Other"
		}
		c.Routes = append(c.Routes, Route{Host: "go.example.com", Path: fmt.Sprintf("/p%03d", i), Name: fmt.Sprintf("Campaign %03d", i), Group: g, Destination: "https://example.com/landing"})
	}
	for i := 0; i < 61; i++ {
		g := "Main"
		if i >= 35 {
			g = "Other"
		}
		c.Catalog = append(c.Catalog, Destination{ID: fmt.Sprintf("lp-%03d", i), Name: fmt.Sprintf("Landing %03d", i), Group: g, URL: fmt.Sprintf("https://example.com/landing-%03d", i)})
	}
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	dc := DomainConfig{GroupSchema: 1, Groups: []string{"MGS"}, Domains: []string{}, Metadata: map[string]DomainMetadata{}}
	for i := 0; i < 65; i++ {
		host := fmt.Sprintf("d%03d.example.com", i)
		dc.Domains = append(dc.Domains, host)
		dc.Metadata[host] = DomainMetadata{ID: i + 1, Group: "MGS"}
	}
	dc.Domains = append(dc.Domains, "go.example.com")
	dc.Metadata["go.example.com"] = DomainMetadata{ID: 66, Group: "MGS"}
	a.domains = dc
	if e := atomicJSON(a.dir+"/domains.json", dc); e != nil {
		t.Fatal(e)
	}
	srv := httptest.NewServer(a)
	defer srv.Close()
	u, _ := url.Parse(srv.URL)
	a.origin = srv.URL
	a.adminHost = u.Host
	a.secure = false
	password := randomHex(24)
	if e := a.addTestUser("pagination-test", password); e != nil {
		t.Fatal(e)
	}
	form := url.Values{"username": {"pagination-test"}, "password": {password}}
	w := send(a, "POST", "/login", a.adminHost, form.Encode(), map[string]string{"Origin": a.origin, "Content-Type": "application/x-www-form-urlencoded"})
	if w.Code != 303 {
		t.Fatal("login failed")
	}
	input, _ := json.Marshal(map[string]string{"url": srv.URL, "session": w.Result().Cookies()[0].Value})
	cmd := exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python", "tests/domain_groups_browser_smoke.py")
	cmd.Stdin = bytes.NewReader(input)
	out, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatalf("pagination failed: %v\n%s", e, out)
	}
	t.Log(string(out))
	if a.cfg.Revision != 1 || len(a.cfg.Routes) != 65 || len(a.cfg.Catalog) != 61 {
		t.Fatal("pagination mutated data")
	}
}
