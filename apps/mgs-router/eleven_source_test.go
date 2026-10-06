package main

import (
	"encoding/json"
	"net/url"
	"os"
	"testing"
)

func TestAllElevenDomainsSourceExact(t *testing.T) {
	b, e := os.ReadFile("../../data/mgs-router-eleven-domains-import-plan.json")
	if e != nil {
		t.Fatal(e)
	}
	var plan struct {
		Configuration Config `json:"configuration"`
	}
	if e = json.Unmarshal(b, &plan); e != nil {
		t.Fatal(e)
	}
	c := plan.Configuration
	c.Revision = 0 // Isolated synthetic state starts at revision zero.
	if len(c.Routes) != 469 {
		t.Fatal("missing routes", len(c.Routes))
	}
	b, e = os.ReadFile("../../data/mgs-router-eleven-domains-keitaro-source.json")
	if e != nil {
		t.Fatal(e)
	}
	type Landing struct {
		ID          int    `json:"id"`
		Destination string `json:"destination"`
		Share       int    `json:"share"`
	}
	var source struct {
		Campaigns []struct {
			ID      int    `json:"id"`
			Name    string `json:"name"`
			Alias   string `json:"alias"`
			Domain  string `json:"domain"`
			Streams []struct {
				Landings []Landing `json:"landings"`
			} `json:"streams"`
		} `json:"campaigns"`
	}
	json.Unmarshal(b, &source)
	a := fixture(t)
	if e = a.apply(c); e != nil {
		t.Fatal(e)
	}
	idx := map[string]Route{}
	for _, r := range c.Routes {
		idx[r.Host+r.Path] = r
	}
	entries := 0
	empty := 0
	for _, sc := range source.Campaigns {
		u, _ := url.Parse(sc.Domain)
		r, ok := idx[u.Host+"/"+sc.Alias]
		if !ok || r.Name != sc.Name || !r.KeitaroQuery {
			t.Fatal("source identity lost", sc.ID)
		}
		ls := sc.Streams[0].Landings
		entries += len(ls)
		if len(ls) == 0 {
			empty++
			if r.ResponseStatus != 500 {
				t.Fatal("empty state lost")
			}
		} else if len(ls) == 1 {
			if r.Destination != ls[0].Destination {
				t.Fatal("single URL changed", sc.ID)
			}
		} else {
			if !r.RelativeWeights || len(r.Destinations) != len(ls) {
				t.Fatal("weighted membership lost")
			}
			counts := map[string]int{}
			wanted := map[string]int{}
			total := 0
			for i, l := range ls {
				if r.Destinations[i].URL != l.Destination || r.Destinations[i].Weight != float64(l.Share) {
					t.Fatal("raw share URL/order drift", sc.ID)
				}
				wanted[l.Destination] += l.Share
				total += l.Share
			}
			for i := 0; i < total; i++ {
				counts[targetAt(r, i)]++
			}
			for k, v := range wanted {
				if counts[k] != v {
					t.Fatal("selection ratio drift", sc.ID)
				}
			}
		}
		for _, raw := range []string{"", "utm_source=face%62ook&utm_medium=A+B&utm_campaign=x%26y%3Dz&utm_term=~&utm_content=A%2BB&fbclid=a%2Fb&x=1&x=2"} {
			allowed := map[string]bool{}
			for _, l := range ls {
				allowed[resolveKeitaroQuery(l.Destination, raw)] = true
			}
			for _, method := range []string{"GET", "HEAD"} {
				w := send(a, method, r.Path+"?"+raw, r.Host, "", nil)
				if len(ls) == 0 {
					if w.Code != 500 || w.Header().Get("Location") != "" {
						t.Fatal(sc.ID, w.Code)
					}
				} else if w.Code != 302 || !allowed[w.Header().Get("Location")] {
					t.Fatal("HTTP fidelity mismatch", sc.ID, w.Code)
				}
			}
		}
	}
	if len(source.Campaigns) != 428 || entries != 1247 || empty != 1 {
		t.Fatal("source count drift", len(source.Campaigns), entries, empty)
	}
	bapp, e := newApp(a.dir, a.origin, true)
	if e != nil || len(bapp.cfg.Routes) != 469 {
		t.Fatal("reload failed", e)
	}
	t.Logf("428 campaigns / 1247 destination entries / 1 source HTTP500; every alias GET+HEAD twice, every weighted bucket, all 469 persisted")
}

func TestKeitaroPHPEncodingAndDuplicates(t *testing.T) {
	got := resolveKeitaroQuery("https://wantabrand.com/?utm_source={utm_source}&utm_content={utm_content}", "utm_source=one&utm_source=two+~&utm_content=%0D%0AX-Test%3A%20yes")
	want := "https://wantabrand.com/?utm_source=two+%7E&utm_content=%0D%0AX-Test%3A+yes"
	if got != want {
		t.Fatal(got)
	}
}
