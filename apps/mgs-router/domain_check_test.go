package main

import (
	"encoding/json"
	"net/http"
	"strings"
	"testing"
)

func TestDomainCheckAPIAndProbe(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	if w := send(a, "POST", "/api/domains/check", a.adminHost, `{"host":"card.wantabrand.com"}`, nil); w.Code != 401 {
		t.Fatal(w.Code)
	}
	if w := send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["check.invalid"]}`, h); w.Code != 200 {
		t.Fatal(w.Code)
	}
	if w := send(a, "POST", "/api/domains/check", a.adminHost, `{"host":"notregistered.invalid"}`, h); w.Code != 400 {
		t.Fatal("unregistered check allowed", w.Code)
	}
	h["Origin"] = "null"
	if w := send(a, "POST", "/api/domains/check", a.adminHost, `{"host":"check.invalid"}`, h); w.Code != 403 {
		t.Fatal("CSRF missing", w.Code)
	}
	nonce := strings.Repeat("a", 32)
	w := send(a, "GET", "/__mgs-router-check?challenge="+nonce, "check.invalid", "", nil)
	if w.Code != http.StatusOK {
		t.Fatal("probe absent", w.Code)
	}
	var p probeResponse
	if json.Unmarshal(w.Body.Bytes(), &p) != nil || !a.validProbe(p, "check.invalid", nonce) {
		t.Fatal("probe invalid")
	}
	if a.validProbe(p, "another.invalid", nonce) || a.validProbe(p, "check.invalid", strings.Repeat("b", 32)) {
		t.Fatal("probe not bound")
	}
	p.Signature = ""
	if a.validProbe(p, "check.invalid", nonce) {
		t.Fatal("unsigned origin trusted")
	}
	w = send(a, "GET", "/__mgs-router-check?challenge="+nonce, "notregistered.invalid", "", nil)
	if w.Code != 404 {
		t.Fatal("unknown domain exposed probe", w.Code)
	}
}
func TestProbeRejectsPrivateAddresses(t *testing.T) {
	for _, s := range []string{"127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "0.0.0.0"} {
		if publicIP(s) {
			t.Fatal("private probe IP accepted", s)
		}
	}
	if !publicIP("1.1.1.1") {
		t.Fatal("public IP rejected")
	}
}
func TestWeightBoundariesDeterministic(t *testing.T) {
	r := Route{Destinations: []Target{{URL: "https://wantabrand.com/a", Weight: 25}, {URL: "https://wantabrand.com/b", Weight: 75}}}
	count := map[string]int{}
	for i := 0; i < 100; i++ {
		count[targetAt(r, i)]++
	}
	if count["https://wantabrand.com/a"] != 25 || count["https://wantabrand.com/b"] != 75 {
		t.Fatal(count)
	}
}
