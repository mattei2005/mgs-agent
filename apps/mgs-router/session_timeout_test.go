package main

import (
    "crypto/sha256"
    "encoding/hex"
    "net/http"
    "net/url"
    "strings"
    "testing"
)

func TestSessionCookieHasNoAutomaticDeadline(t *testing.T) {
    a := fixture(t)
    if err := a.addTestUser("timeout-test", "synthetic-password-for-local-test"); err != nil { t.Fatal(err) }
    form := url.Values{"username":{"timeout-test"}, "password":{"synthetic-password-for-local-test"}}
    w := send(a, "POST", "/login", a.adminHost, form.Encode(), map[string]string{"Origin":a.origin,"Content-Type":"application/x-www-form-urlencoded"})
    if w.Code != 303 { t.Fatalf("login status=%d",w.Code) }
    cookies := w.Result().Cookies()
    if len(cookies)!=1 { t.Fatal("missing session cookie") }
    c:=cookies[0]
    if c.MaxAge!=0 || !c.Expires.IsZero() { t.Fatal("session cookie still expires automatically") }
    if !c.Secure || !c.HttpOnly || c.SameSite!=http.SameSiteStrictMode { t.Fatal("session cookie security changed") }
}

func TestRecordedSessionRequiresNoClockDeadline(t *testing.T) {
    a:=fixture(t)
    token:=strings.Repeat("a",64)
    hash:=sha256.Sum256([]byte(token)); key:=hex.EncodeToString(hash[:])
    a.sessions[key]=Session{Username:"recorded-local-test",CSRF:strings.Repeat("b",64)}
    headers:=map[string]string{"Cookie":"mgs_session="+token}
    for _,path:=range []string{"/admin","/api/me","/api/routes"} {
        w:=send(a,"GET",path,a.adminHost,"",headers)
        if w.Code!=200 { t.Fatalf("recorded session rejected by a time deadline: path=%s status=%d",path,w.Code) }
    }
    // A later valid sign-in must not purge another already authenticated session.
    login(t,a)
    if w:=send(a,"GET","/api/me",a.adminHost,"",headers);w.Code!=200 { t.Fatal("another login invalidated the recorded session") }
}

func TestNoTimeoutKeepsManualLogoutAndCSRF(t *testing.T) {
    a:=fixture(t);cookie,csrf:=login(t,a)
    bad:=map[string]string{"Cookie":cookie,"Origin":a.origin}
    if w:=send(a,"POST","/logout",a.adminHost,"{}",bad);w.Code!=403 { t.Fatal("logout missing CSRF accepted") }
    if w:=send(a,"GET","/api/me",a.adminHost,"",bad);w.Code!=200 { t.Fatal("invalid logout ended session") }
    good:=map[string]string{"Cookie":cookie,"Origin":a.origin,"X-CSRF-Token":csrf}
    if w:=send(a,"POST","/logout",a.adminHost,"{}",good);w.Code!=200 || w.Result().Cookies()[0].MaxAge>=0 { t.Fatal("manual logout did not clear session cookie") }
    if w:=send(a,"GET","/api/me",a.adminHost,"",good);w.Code!=401 { t.Fatal("logged-out cookie still authenticates") }
    if w:=send(a,"GET","/api/me",a.adminHost,"",map[string]string{"Cookie":"mgs_session="+strings.Repeat("f",64)});w.Code!=401 { t.Fatal("unregistered token accepted") }
}
