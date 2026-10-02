package main

import (
	"bytes"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func (a *App) addTestUser(username, password string) error { return a.addUser(username, password) }
func fixture(t *testing.T) *App {
	t.Helper()
	a, e := newApp(t.TempDir(), "https://route.mgsdigitalcorp.com", true)
	if e != nil {
		t.Fatal(e)
	}
	return a
}
func send(a *App, method, path, host, body string, headers map[string]string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	r.Host = host
	for k, v := range headers {
		r.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	a.ServeHTTP(w, r)
	return w
}
func TestRedirectPreservesRawParameters(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Revision: 0, Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/offer?fixed=1"}}}); e != nil {
		t.Fatal(e)
	}
	w := send(a, "GET", "/m0?utm_content=A%2BB&x=1&x=2&blank=&fbclid=a%2Fb", "tarjeta.wantabrand.com", "", nil)
	want := "https://wantabrand.com/offer?fixed=1&utm_content=A%2BB&x=1&x=2&blank=&fbclid=a%2Fb"
	if w.Code != 302 || w.Header().Get("Location") != want {
		t.Fatalf("status=%d redirect mismatch", w.Code)
	}
	if !strings.Contains(w.Header().Get("Cache-Control"), "no-store") {
		t.Fatal("redirect cached")
	}
}
func TestUnknownRouteDoesNotOpenRedirect(t *testing.T) {
	a := fixture(t)
	w := send(a, "GET", "/missing?url=https://attacker.invalid", "tarjeta.wantabrand.com", "", nil)
	if w.Code != 404 {
		t.Fatal(w.Code)
	}
}
func TestDestinationsCannotInjectOrUseCredentials(t *testing.T) {
	for _, d := range []string{"javascript:alert(1)", "https://user:secret@example.com", "https://example.com/\r\nX: bad", "https://127.0.0.1/", "https://localhost/", "https://route.mgsdigitalcorp.com/admin"} {
		a := fixture(t)
		if a.apply(Config{Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: d}}}) == nil {
			t.Fatalf("invalid destination accepted: %q", d)
		}
	}
}
func TestDuplicateAndReservedRoutesRejected(t *testing.T) {
	a := fixture(t)
	r := Route{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/offer"}
	if a.apply(Config{Routes: []Route{r, r}}) == nil {
		t.Fatal("duplicate accepted")
	}
	if a.apply(Config{Routes: []Route{{Host: "route.mgsdigitalcorp.com", Path: "/api/routes", Destination: r.Destination}}}) == nil {
		t.Fatal("reserved accepted")
	}
}
func TestConfigurationPersistsAndKeepsPreviousOnInvalid(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/offer"}}}); e != nil {
		t.Fatal(e)
	}
	if a.apply(Config{Revision: 1, Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "bad"}}}) == nil {
		t.Fatal("invalid accepted")
	}
	b, e := newApp(a.dir, a.origin, true)
	if e != nil {
		t.Fatal(e)
	}
	w := send(b, "GET", "/m0", "tarjeta.wantabrand.com", "", nil)
	if w.Code != 302 {
		t.Fatal(w.Code)
	}
}
func TestStaleRevisionRejected(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Routes: []Route{}}); e != nil {
		t.Fatal(e)
	}
	if a.apply(Config{Revision: 0, Routes: []Route{}}) == nil {
		t.Fatal("stale write accepted")
	}
}
func TestUnauthenticatedCannotReadOrWrite(t *testing.T) {
	a := fixture(t)
	for _, method := range []string{"GET", "POST"} {
		w := send(a, method, "/api/routes", "route.mgsdigitalcorp.com", "{}", nil)
		if w.Code != 401 {
			t.Fatal(method, w.Code)
		}
	}
}
func login(t *testing.T, a *App) (string, string) {
	t.Helper()
	p := make([]byte, 24)
	rand.Read(p)
	password := hex.EncodeToString(p)
	if e := a.addTestUser("synthetic-test-user", password); e != nil {
		t.Fatal(e)
	}
	form := url.Values{"username": {"synthetic-test-user"}, "password": {password}}
	w := send(a, "POST", "/login", "route.mgsdigitalcorp.com", form.Encode(), map[string]string{"Content-Type": "application/x-www-form-urlencoded", "Origin": a.origin})
	if w.Code != 303 {
		t.Fatalf("login status %d", w.Code)
	}
	cs := w.Result().Cookies()
	if len(cs) != 1 || !cs[0].Secure || !cs[0].HttpOnly || cs[0].SameSite != http.SameSiteStrictMode {
		t.Fatal("unsafe cookie")
	}
	cookie := cs[0].Name + "=" + cs[0].Value
	me := send(a, "GET", "/api/me", "route.mgsdigitalcorp.com", "", map[string]string{"Cookie": cookie})
	var v struct {
		CSRF string `json:"csrf"`
	}
	if e := json.Unmarshal(me.Body.Bytes(), &v); e != nil || v.CSRF == "" {
		t.Fatal("no csrf")
	}
	return cookie, v.CSRF
}
func TestAuthenticatedEditRequiresCSRFAndOrigin(t *testing.T) {
	a := fixture(t)
	cookie, csrf := login(t, a)
	payload, _ := json.Marshal(Config{Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/offer"}}})
	h := map[string]string{"Cookie": cookie, "Content-Type": "application/json", "Origin": a.origin}
	if w := send(a, "POST", "/api/routes", "route.mgsdigitalcorp.com", string(payload), h); w.Code != 403 {
		t.Fatal("csrf not enforced", w.Code)
	}
	h["X-CSRF-Token"] = csrf
	h["Origin"] = "https://attacker.invalid"
	if w := send(a, "POST", "/api/routes", "route.mgsdigitalcorp.com", string(payload), h); w.Code != 403 {
		t.Fatal("origin not enforced", w.Code)
	}
	h["Origin"] = a.origin
	if w := send(a, "POST", "/api/routes", "route.mgsdigitalcorp.com", string(payload), h); w.Code != 200 {
		t.Fatal("edit failed", w.Code)
	}
	if w := send(a, "GET", "/m0", "tarjeta.wantabrand.com", "", nil); w.Code != 302 {
		t.Fatal(w.Code)
	}
}
func TestAdminNotAvailableOnTrafficDomain(t *testing.T) {
	a := fixture(t)
	for _, p := range []string{Host: "/admin", Path: "/login", Destination: "/api/routes"} {
		if w := send(a, "GET", p, "tarjeta.wantabrand.com", "", nil); w.Code != 404 {
			t.Fatal(p, w.Code)
		}
	}
}
func TestSecurityHeadersAndUI(t *testing.T) {
	a := fixture(t)
	w := send(a, "GET", "/login", "route.mgsdigitalcorp.com", "", nil)
	if w.Code != 200 || !bytes.Contains(w.Body.Bytes(), []byte("MGS Router")) {
		t.Fatal("login UI missing")
	}
	for _, h := range []string{Host: "Content-Security-Policy", Path: "X-Content-Type-Options", Destination: "Referrer-Policy"} {
		if w.Header().Get(h) == "" {
			t.Fatal("missing header", h)
		}
	}
}
func TestLoginRateLimited(t *testing.T) {
	a := fixture(t)
	last := 0
	for i := 0; i < 8; i++ {
		w := send(a, "POST", "/login", "route.mgsdigitalcorp.com", "username=missing&password=bad", map[string]string{"Origin": a.origin, "Content-Type": "application/x-www-form-urlencoded"})
		last = w.Code
	}
	if last != 429 {
		t.Fatal("rate limit absent", last)
	}
}
func TestConcurrentRedirectAndEdit(t *testing.T) {
	a := fixture(t)
	if e := a.apply(Config{Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/a"}}}); e != nil {
		t.Fatal(e)
	}
	done := make(chan bool)
	go func() {
		for i := 0; i < 1000; i++ {
			send(a, "GET", "/m0?x=1", "tarjeta.wantabrand.com", "", nil)
		}
		done <- true
	}()
	for i := 1; i < 20; i++ {
		if e := a.apply(Config{Revision: i, Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/b"}}}); e != nil {
			t.Fatal(e)
		}
	}
	<-done
}
