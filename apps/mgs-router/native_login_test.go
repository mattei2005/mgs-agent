package main

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"net/url"
	"os/exec"
	"testing"
)

func TestNativeBrowserLoginFormPreservesOrigin(t *testing.T) {
	a := fixture(t)
	srv := httptest.NewServer(a)
	defer srv.Close()
	u, _ := url.Parse(srv.URL)
	a.origin = srv.URL
	a.adminHost = u.Host
	a.secure = false
	input, _ := json.Marshal(map[string]string{"url": srv.URL})
	cmd := exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python", "tests/native_login_smoke.py")
	cmd.Stdin = bytes.NewReader(input)
	out, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatalf("native browser harness failed: %v", e)
	}
	var result struct {
		Origin   string `json:"native_form_origin"`
		Status   int    `json:"post_status"`
		Location string `json:"location"`
	}
	if e = json.Unmarshal(out, &result); e != nil {
		t.Fatal(e)
	}
	if result.Origin != srv.URL || result.Status != 303 || result.Location != "/login?error=1" {
		t.Fatalf("native browser login origin rejected: origin=%q status=%d", result.Origin, result.Status)
	}
}
func TestOpaqueAndForeignLoginOriginsStillRejected(t *testing.T) {
	a := fixture(t)
	for _, origin := range []string{"null", "", "https://attacker.invalid"} {
		w := send(a, "POST", "/login", "route.mgsdigitalcorp.com", "", map[string]string{"Origin": origin, "Content-Type": "application/x-www-form-urlencoded"})
		if w.Code != 403 {
			t.Fatalf("unsafe origin accepted: %q", origin)
		}
	}
}
func TestTrafficRedirectKeepsNoReferrerPolicy(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Routes: []Route{{"tarjeta.wantabrand.com", "/m0", "https://wantabrand.com/offer"}}}); e != nil {
		t.Fatal(e)
	}
	w := send(a, "GET", "/m0?utm_content=x", "tarjeta.wantabrand.com", "", nil)
	if w.Code != 302 || w.Header().Get("Referrer-Policy") != "no-referrer" {
		t.Fatal("traffic privacy changed")
	}
}
