package main

import (
	"encoding/json"
	"testing"
)

func TestClickHistoricalMetadataVisibleAndNativeSincePreserved(t *testing.T) {
	a := fixture(t)
	before := a.clicks.since
	_, e := a.clicks.db.Exec(`INSERT INTO click_meta(name,value) VALUES('history_keitaro',?)`, `{"source":"Keitaro","from":"2026-01-22","to":"2026-10-04","timezone":"America/New_York","imported_clicks":99,"daily_rows":2,"campaigns_with_history":1,"routes_matched":2}`)
	if e != nil {
		t.Fatal(e)
	}
	cookie, _ := login(t, a)
	w := send(a, "GET", "/api/clicks", a.adminHost, "", map[string]string{"Cookie": cookie})
	if w.Code != 200 {
		t.Fatal(w.Code)
	}
	var v struct {
		Since   string `json:"since"`
		History struct {
			Source string `json:"source"`
			From   string `json:"from"`
			To     string `json:"to"`
			Clicks int64  `json:"imported_clicks"`
		} `json:"history"`
	}
	if e := json.Unmarshal(w.Body.Bytes(), &v); e != nil {
		t.Fatal(e)
	}
	if v.Since != before || v.History.Source != "Keitaro" || v.History.From != "2026-01-22" || v.History.To != "2026-10-04" || v.History.Clicks != 99 {
		t.Fatal("historical provenance missing or native date overwritten")
	}
}
func TestMalformedHistoricalMetadataFailsStatsNotRedirects(t *testing.T) {
	a := fixture(t)
	_, e := a.clicks.db.Exec(`INSERT INTO click_meta(name,value) VALUES('history_keitaro','bad')`)
	if e != nil {
		t.Fatal(e)
	}
	cookie, _ := login(t, a)
	w := send(a, "GET", "/api/clicks", a.adminHost, "", map[string]string{"Cookie": cookie})
	if w.Code != 503 {
		t.Fatal(w.Code)
	}
}
