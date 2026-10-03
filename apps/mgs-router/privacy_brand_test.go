package main

import (
	"bytes"
	"strings"
	"testing"
)

const panelRobots = "noindex, nofollow, noarchive, nosnippet, noimageindex"

func TestPanelFaviconAndPrivateIndexing(t *testing.T) {
	a := fixture(t)
	cookie, _ := login(t, a)
	for _, path := range []string{"/", "/login", "/admin", "/api/routes", "/missing", "/robots.txt", "/favicon.ico", "/assets/style.css"} {
		w := send(a, "GET", path, a.adminHost, "", map[string]string{"Cookie": cookie})
		if w.Header().Get("X-Robots-Tag") != panelRobots {
			t.Fatalf("%s: missing private robots header", path)
		}
	}
	for _, path := range []string{"/login", "/admin"} {
		w := send(a, "GET", path, a.adminHost, "", map[string]string{"Cookie": cookie})
		if !strings.Contains(w.Body.String(), `<meta name="robots" content="`+panelRobots+`">`) || !strings.Contains(w.Body.String(), `rel="icon" href="/favicon.ico?v=1555940342707257524"`) {
			t.Fatalf("%s: favicon or robots meta missing", path)
		}
	}
	w := send(a, "GET", "/favicon.ico", a.adminHost, "", nil)
	if w.Code != 200 || w.Header().Get("Content-Type") != "image/vnd.microsoft.icon" || !bytes.HasPrefix(w.Body.Bytes(), []byte{0, 0, 1, 0}) {
		t.Fatal("invalid or inaccessible favicon")
	}
	w = send(a, "GET", "/robots.txt", a.adminHost, "", nil)
	if w.Code != 200 || w.Body.String() != "User-agent: *\nDisallow: /\n" {
		t.Fatal("robots must disallow all without sitemap")
	}
	w = send(a, "GET", "/sitemap.xml", a.adminHost, "", nil)
	if w.Code != 404 {
		t.Fatal("sitemap enabled")
	}
}

func TestPanelIndexingPolicyDoesNotChangeTraffic(t *testing.T) {
	a := fixture(t)
	if err := a.apply(Config{Routes: []Route{{Host: "tarjeta.wantabrand.com", Path: "/m0", Destination: "https://wantabrand.com/offer"}}}); err != nil {
		t.Fatal(err)
	}
	w := send(a, "GET", "/m0?utm_content=A%2BB&x=1&x=2", "tarjeta.wantabrand.com", "", nil)
	if w.Code != 302 || w.Header().Get("X-Robots-Tag") != "" || w.Header().Get("Location") != "https://wantabrand.com/offer?utm_content=A%2BB&x=1&x=2" || w.Header().Get("Referrer-Policy") != "no-referrer" {
		t.Fatal("traffic behavior changed by panel privacy policy")
	}
}
