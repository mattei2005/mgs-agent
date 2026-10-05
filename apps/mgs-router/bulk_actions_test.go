package main

import (
	"reflect"
	"testing"
)

func TestDisabledCampaignAndLandingRuntime(t *testing.T) {
	a := fixture(t)
	c := catalogFixture()
	c.ActionSchema = 1
	c.Routes[0].Disabled = true
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	for _, method := range []string{"GET", "HEAD"} {
		w := send(a, method, "/a?x=1", "go.example.com", "", nil)
		if w.Code != 404 || w.Header().Get("Location") != "" || w.Header().Get("Cache-Control") != "no-store" {
			t.Fatal("disabled route sent traffic")
		}
	}
	c.Revision = a.cfg.Revision
	c.Routes[0].Disabled = false
	c.Catalog[0].Disabled = true
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	if send(a, "GET", "/a", "go.example.com", "", nil).Code != 404 {
		t.Fatal("disabled LP used")
	}
	b, e := newApp(a.dir, a.origin, true)
	if e != nil {
		t.Fatal(e)
	}
	if !b.cfg.Catalog[0].Disabled || send(b, "GET", "/a", "go.example.com", "", nil).Code != 404 {
		t.Fatal("disabled persistence")
	}
	c.Revision = a.cfg.Revision
	c.Catalog[0].Disabled = false
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	if send(a, "GET", "/a?x=1&x=2", "go.example.com", "", nil).Header().Get("Location") != "https://example.com/a?x=1&x=2" {
		t.Fatal("reactivation query changed")
	}
}
func TestDisabledWeightedProportionsSnapshotsAndManualURL(t *testing.T) {
	a := fixture(t)
	c := catalogFixture()
	c.ActionSchema = 1
	c.Catalog = append(c.Catalog, Destination{ID: "lp-2", Name: "LP2", URL: "https://example.com/b"}, Destination{ID: "lp-3", Name: "LP3", URL: "https://example.com/c"})
	c.Catalog[0].Disabled = true
	c.Routes[0].Destination = ""
	c.Routes[0].DestinationID = ""
	c.Routes[0].Destinations = []Target{{URL: c.Catalog[0].URL, Weight: 40, DestinationID: "lp-1"}, {URL: c.Catalog[1].URL, Weight: 20, DestinationID: "lp-2"}, {URL: c.Catalog[2].URL, Weight: 40, DestinationID: "lp-3"}}
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	rt := a.index["go.example.com\n/a"]
	if len(rt.Destinations) != 2 || rt.Destinations[0].Weight != 20 || rt.Destinations[1].Weight != 40 {
		t.Fatal("effective weights")
	}
	for n := 0; n < 60; n++ {
		want := "https://example.com/c"
		if n < 20 {
			want = "https://example.com/b"
		}
		if targetAt(rt, n) != want {
			t.Fatal("proportions")
		}
	}
	if !reflect.DeepEqual(a.cfg.Routes, c.Routes) {
		t.Fatal("stored weights mutated")
	}
	c.Revision = a.cfg.Revision
	c.Catalog[1].Disabled = true
	c.Catalog[2].Disabled = true
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	if send(a, "GET", "/a", "go.example.com", "", nil).Code != 404 {
		t.Fatal("no active target must not redirect")
	}
	c.Revision = a.cfg.Revision
	c.Routes = append(c.Routes, Route{Host: "go.example.com", Path: "/manual", Destination: c.Catalog[0].URL})
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	if send(a, "GET", "/manual", "go.example.com", "", nil).Code != 302 {
		t.Fatal("ID-disabled incorrectly disabled unrelated manual URL")
	}
}
func TestBulkProtectUsedLandingDeletionAndStaleSchema(t *testing.T) {
	a := fixture(t)
	c := catalogFixture()
	c.ActionSchema = 1
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	bad := c
	bad.Revision = a.cfg.Revision
	bad.Routes = []Route{}
	bad.Catalog = []Destination{}
	if a.apply(bad) == nil {
		t.Fatal("combined used-LP deletion bypass")
	}
	bad = c
	bad.Revision = a.cfg.Revision
	bad.ActionSchema = 0
	if a.apply(bad) == nil {
		t.Fatal("old UI write allowed")
	}
	if a.apply(c) != errRevision {
		t.Fatal("stale bulk write allowed")
	}
	c.Revision = a.cfg.Revision
	c.Routes = []Route{}
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	c.Revision = a.cfg.Revision
	c.Catalog = []Destination{}
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
}
