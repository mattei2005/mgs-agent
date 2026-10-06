package main

import (
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestFractionalEqualWeightsNoDrift(t *testing.T) {
	a := fixture(t)
	for _, n := range []int{3, 20, 23, 100} {
		r := Route{Host: "go.example.com", Path: "/equal", RelativeWeights: true}
		w := math.Round(100/float64(n)*1e12) / 1e12
		for i := 0; i < n; i++ {
			r.Destinations = append(r.Destinations, Target{URL: "https://example.com/a", Weight: w})
		}
		idx, e := a.validate(Config{Routes: []Route{r}})
		if e != nil {
			t.Fatal(e)
		}
		for i, weight := range idx["go.example.com\n/equal"].Destinations {
			if weight.Weight != w {
				t.Fatal("ratio drift", i)
			}
		}
	}
	for _, w := range []float64{math.NaN(), math.Inf(1), math.Inf(-1), 0, -1, 1e-15, 1000001} {
		if _, e := a.validate(Config{Routes: []Route{{Host: "go.example.com", Path: "/bad", RelativeWeights: true, Destinations: []Target{{URL: "https://example.com/a", Weight: w}}}}}); e == nil {
			t.Fatal("invalid weight accepted")
		}
	}
	if _, e := a.validate(Config{Routes: []Route{{Host: "go.example.com", Path: "/ok", Destinations: []Target{{URL: "https://example.com/a", Weight: 33.333333333333}, {URL: "https://example.com/b", Weight: 66.666666666667}}}}}); e != nil {
		t.Fatal(e)
	}
}
func TestStateCheckDoesNotCreateClickStore(t *testing.T) {
	dir := t.TempDir()
	a, e := newAppMode(dir, "https://route.mgsdigitalcorp.com", true, false)
	if e != nil || a.clicks != nil {
		t.Fatal(e)
	}
	if _, e := os.Stat(filepath.Join(dir, "clicks.sqlite")); !os.IsNotExist(e) {
		t.Fatal("read-only check created database")
	}
}
