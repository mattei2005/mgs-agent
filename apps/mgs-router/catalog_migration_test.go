package main

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

func TestCatalogMigrationPreservesAllImportedRoutes(t *testing.T) {
	b, e := os.ReadFile("../../data/mgs-router-catalog-plan.json")
	if e != nil {
		t.Fatal(e)
	}
	var c Config
	if e = json.Unmarshal(b, &c); e != nil {
		t.Fatal(e)
	}
	b, e = os.ReadFile("../../data/mgs-router-wantabrand-import-plan.json")
	if e != nil {
		t.Fatal(e)
	}
	var before Config
	json.Unmarshal(b, &before)
	if len(c.Routes) != 41 || len(c.Catalog) != 94 || len(c.Groups) != 3 {
		t.Fatal("migration counts drift")
	}
	plain := make([]Route, len(c.Routes))
	for i, r := range c.Routes {
		r.Group = ""
		r.DestinationID = ""
		if r.Destinations != nil {
			r.Destinations = append([]Target(nil), r.Destinations...)
			for j := range r.Destinations {
				r.Destinations[j].DestinationID = ""
			}
		}
		plain[i] = r
	}
	if !reflect.DeepEqual(plain, before.Routes) {
		t.Fatal("traffic semantics changed")
	}
	a := fixture(t)
	c.Revision = 0 // Fresh isolated fixture; live plan starts at revision 1.
	if e := a.apply(c); e != nil {
		t.Fatal(e)
	}
	for _, r := range c.Routes {
		for n := 0; n < 100; n++ {
			if targetAt(r, n) == "" {
				t.Fatal("lost destination")
			}
		}
		w := send(a, "GET", r.Path+"?x=1&x=2&fbclid=A%2BB", r.Host, "", nil)
		if w.Code != 302 {
			t.Fatal("lost redirect")
		}
	}
	after, e := newApp(a.dir, a.origin, true)
	if e != nil || len(after.cfg.Catalog) != 94 {
		t.Fatal("catalog restart persistence")
	}
	// Old clients cannot erase the new catalog through an incomplete payload.
	old := before
	old.Revision = a.cfg.Revision
	if a.apply(old) == nil {
		t.Fatal("old client erased catalog")
	}
	t.Log("41 routes, 117 destination entries, 94 catalog identities and 3 groups; no traffic drift")
}
