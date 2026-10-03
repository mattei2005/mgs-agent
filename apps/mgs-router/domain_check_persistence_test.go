package main

import (
	"encoding/json"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"testing"
)

func persistenceLogin(t *testing.T, a *App) (string, string) {
	t.Helper()
	user := "persistence-" + randomHex(3)
	password := randomHex(24)
	if err := a.addTestUser(user, password); err != nil {
		t.Fatal(err)
	}
	w := send(a, "POST", "/login", a.adminHost, url.Values{"username": {user}, "password": {password}}.Encode(), map[string]string{"Content-Type": "application/x-www-form-urlencoded", "Origin": a.origin})
	if w.Code != 303 {
		t.Fatal(w.Code)
	}
	cookies := w.Result().Cookies()
	cookie := cookies[0].Name + "=" + cookies[0].Value
	me := send(a, "GET", "/api/me", a.adminHost, "", map[string]string{"Cookie": cookie})
	var data struct {
		CSRF string `json:"csrf"`
	}
	json.Unmarshal(me.Body.Bytes(), &data)
	return cookie, data.CSRF
}
func readCheckMap(t *testing.T, a *App, cookie string) map[string]map[string]any {
	t.Helper()
	w := send(a, "GET", "/api/domains", a.adminHost, "", map[string]string{"Cookie": cookie})
	if w.Code != http.StatusOK {
		t.Fatal(w.Code)
	}
	var body struct {
		Checks map[string]map[string]any `json:"checks"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatal(err)
	}
	return body.Checks
}
func TestDomainCheckNegativePersistsAfterReload(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	if w := send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["check.invalid"]}`, h); w.Code != 200 {
		t.Fatal(w.Code)
	}
	w := send(a, "POST", "/api/domains/check", a.adminHost, `{"host":"check.invalid"}`, h)
	if w.Code != 200 {
		t.Fatal(w.Code)
	}
	var result map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	check := readCheckMap(t, a, cookie)["check.invalid"]
	if check == nil || check["verified"] != false || check["checked_at"] != result["checked_at"] {
		t.Fatal("verification result lost on API reload", check)
	}
	restarted, err := newApp(a.dir, a.origin, a.secure)
	if err != nil {
		t.Fatal(err)
	}
	cookie2, _ := persistenceLogin(t, restarted)
	again := readCheckMap(t, restarted, cookie2)["check.invalid"]
	if again == nil || again["verified"] != false || again["checked_at"] != result["checked_at"] {
		t.Fatal("verification result lost on restart", again)
	}
	st, err := os.Stat(filepath.Join(a.dir, "domain-checks.json"))
	if err != nil || st.Mode().Perm() != 0600 {
		t.Fatal("private persistence missing")
	}
}
func TestSavedPositiveDomainCheckLoadsWithoutNewOnlineClaim(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	if w := send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["check.invalid"]}`, h); w.Code != 200 {
		t.Fatal(w.Code)
	}
	data := map[string]any{"check.invalid": map[string]any{"host": "check.invalid", "verified": true, "message": "Synthetic local stored positive proof", "checked_at": "2026-01-01T00:00:00Z"}}
	if err := atomicJSON(filepath.Join(a.dir, "domain-checks.json"), data); err != nil {
		t.Fatal(err)
	}
	restarted, err := newApp(a.dir, a.origin, a.secure)
	if err != nil {
		t.Fatal(err)
	}
	cookie2, csrf2 := persistenceLogin(t, restarted)
	check := readCheckMap(t, restarted, cookie2)["check.invalid"]
	if check == nil || check["verified"] != true || check["checked_at"] != "2026-01-01T00:00:00Z" {
		t.Fatal("stored green state lost", check)
	}
	// Manual verification performs a fresh network check and replaces the prior saved success.
	h2 := map[string]string{"Cookie": cookie2, "X-CSRF-Token": csrf2, "Content-Type": "application/json", "Origin": a.origin}
	w := send(restarted, "POST", "/api/domains/check", restarted.adminHost, `{"host":"check.invalid"}`, h2)
	if w.Code != 200 {
		t.Fatal(w.Code)
	}
	if got := readCheckMap(t, restarted, cookie2)["check.invalid"]; got["verified"] != false {
		t.Fatal("old saved positive hid new online failure", got)
	}
}
func TestDomainCheckDoesNotClaimSuccessWhenPersistenceFails(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	h := map[string]string{"Cookie": cookie, "X-CSRF-Token": csrf, "Content-Type": "application/json", "Origin": a.origin}
	send(a, "POST", "/api/domains", a.adminHost, `{"revision":0,"domains":["check.invalid"]}`, h)
	if err := os.Mkdir(filepath.Join(a.dir, "domain-checks.json"), 0700); err != nil {
		t.Fatal(err)
	}
	w := send(a, "POST", "/api/domains/check", a.adminHost, `{"host":"check.invalid"}`, h)
	if w.Code != 500 {
		t.Fatal("verification claimed saved with failed storage", w.Code)
	}
}
func TestDomainCheckMalformedStoreFailsClosed(t *testing.T) {
	a := fixture(t)
	if err := os.WriteFile(filepath.Join(a.dir, "domain-checks.json"), []byte(`{"bad":{"verified":true}}`), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := newApp(a.dir, a.origin, a.secure); err == nil {
		t.Fatal("malformed stored verification accepted")
	}
}
