package main

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"net/url"
	"os/exec"
	"testing"
)

func TestKeitaroBrowserRoundtrip(t *testing.T) {
	a := fixture(t)
	var c Config
	json.Unmarshal([]byte(`{"routes":[{"host":"card.wantabrand.com","path":"/relative","relative_weights":true,"keitaro_query":true,"destinations":[{"url":"https://wantabrand.com/a","weight":14},{"url":"https://wantabrand.com/b","weight":14},{"url":"https://wantabrand.com/c","weight":14}]},{"host":"card.wantabrand.com","path":"/empty","response_status":500,"keitaro_query":true},{"host":"card.wantabrand.com","path":"/fragment","keitaro_query":true,"destination":"https://wantabrand.com/p?utm_campaign=pg_#PAGE_ID#&utm_content=drip_m0-1"}]}`), &c)
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
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
	cmd := exec.Command("/root/.local/share/mgs-router-toolchain/qa-venv/bin/python", "tests/keitaro_browser_smoke.py")
	cmd.Stdin = bytes.NewReader(input)
	output, e := cmd.CombinedOutput()
	if e != nil {
		t.Fatalf("Keitaro browser failed: %v\n%s", e, output)
	}
	t.Log(string(output))
}
