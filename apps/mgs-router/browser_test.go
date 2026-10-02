package main

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"net/url"
	"os/exec"
	"testing"
)

func TestBrowserWorkflow(t *testing.T) {
	a := fixture(t)
	srv := httptest.NewServer(a)
	defer srv.Close()
	u, _ := url.Parse(srv.URL)
	a.origin = srv.URL
	a.adminHost = u.Host
	a.secure = false
	password := randomHex(24)
	if e := a.addTestUser("synthetic-browser-user", password); e != nil {
		t.Fatal(e)
	}
	form := url.Values{"username": {"synthetic-browser-user"}, "password": {password}}
	w := send(a, "POST", "/login", a.adminHost, form.Encode(), map[string]string{"Origin": a.origin, "Content-Type": "application/x-www-form-urlencoded"})
	if w.Code != 303 || len(w.Result().Cookies()) != 1 {
		t.Fatal("fixture login failed")
	}
	input, _ := json.Marshal(map[string]string{"url": srv.URL, "session": w.Result().Cookies()[0].Value})
	cmd := exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python", "tests/browser_smoke.py")
	cmd.Stdin = bytes.NewReader(input)
	output, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatalf("browser smoke failed: %v\n%s", e, output)
	}
	t.Log(string(output))
	redirect := send(a, "GET", "/qa-route?utm_content=A%2BB&x=1&x=2", "test.wantabrand.invalid", "", nil)
	if redirect.Code != 302 || redirect.Header().Get("Location") != "https://wantabrand.com/qa-two?utm_content=A%2BB&x=1&x=2" {
		t.Fatal("browser change not applied to redirect")
	}
}
