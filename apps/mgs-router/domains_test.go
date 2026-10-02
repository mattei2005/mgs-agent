package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestDomainAPIAuthenticationAndCSRF(t *testing.T) {
	a := fixture(t)
	if w := send(a, "GET", "/api/domains", a.adminHost, "", nil); w.Code != 401 {
		t.Fatal(w.Code)
	}
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "Content-Type": "application/json", "Origin": a.origin}
	payload := `{"revision":0,"domains":["card.wantabrand.com","wantabrand.com"]}`
	if w := send(a, "POST", "/api/domains", a.adminHost, payload, h); w.Code != 403 {
		t.Fatal(w.Code)
	}
	h["X-CSRF-Token"] = csrf
	h["Origin"] = "https://foreign.invalid"
	if w := send(a, "POST", "/api/domains", a.adminHost, payload, h); w.Code != 403 {
		t.Fatal(w.Code)
	}
	h["Origin"] = a.origin
	if w := send(a, "POST", "/api/domains", a.adminHost, payload, h); w.Code != 200 {
		t.Fatal(w.Code, w.Body.String())
	}
	if w := send(a, "POST", "/api/domains", a.adminHost, payload, h); w.Code != 409 {
		t.Fatal("stale accepted", w.Code)
	}
	w := send(a, "GET", "/api/domains", a.adminHost, "", h)
	if w.Code != 200 || !strings.Contains(w.Body.String(), "2.25.165.171") || !strings.Contains(w.Body.String(), "cloudflare_required") {
		t.Fatal("DNS instructions missing", w.Code, w.Body.String())
	}
	b, e := newApp(a.dir, a.origin, true)
	if e != nil {
		t.Fatal(e)
	}
	b.sessions = a.sessions
	_ = csrf
	w = send(b, "GET", "/api/domains", b.adminHost, "", map[string]string{"Cookie": cookie})
	var v struct {
		Revision int      `json:"revision"`
		Domains  []string `json:"domains"`
	}
	if json.Unmarshal(w.Body.Bytes(), &v) != nil || v.Revision != 1 || len(v.Domains) != 2 {
		t.Fatal("domain state not persisted", w.Body.String())
	}
	if w := send(a, "GET", "/api/domains", "card.wantabrand.com", "", h); w.Code != 404 {
		t.Fatal("traffic exposed admin", w.Code)
	}
}

func TestDomainValidation(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	for _, host := range []string{"https://example.com", "bad..example.com", "-bad.example.com", "bad_.example.com", "example.com:443", "localhost", "127.0.0.1", "route.mgsdigitalcorp.com", "Example.com", strings.Repeat("a", 64) + ".com"} {
		p, _ := json.Marshal(map[string]any{"revision": 0, "domains": []string{host}})
		if w := send(a, "POST", "/api/domains", a.adminHost, string(p), h); w.Code != 400 {
			t.Fatalf("invalid %q accepted %d", host, w.Code)
		}
	}
	if w := send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["example.com","example.com"]}`, h); w.Code != 400 {
		t.Fatal("duplicate accepted", w.Code)
	}
}

func TestDomainWritePreservesRoutesAndRevision(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Routes: []Route{{"card.wantabrand.com", "/existing", "https://wantabrand.com/offer"}}}); e != nil {
		t.Fatal(e)
	}
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	if w := send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["new.example.com"]}`, h); w.Code != 200 {
		t.Fatal(w.Code)
	}
	if a.cfg.Revision != 1 || len(a.cfg.Routes) != 1 {
		t.Fatal("domain write changed routes")
	}
	w := send(a, "GET", "/api/domains", a.adminHost, "", h)
	if !strings.Contains(w.Body.String(), "card.wantabrand.com") {
		t.Fatal("route domains missing")
	}
}
