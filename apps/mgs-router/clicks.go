package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	_ "modernc.org/sqlite"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sync/atomic"
	"time"
	_ "time/tzdata"
)

// Only day, immutable public route identity and total are retained. No visitor
// identifiers, IPs, cookies, user-agents, queries, referrers or destination URLs.
type ClickStore struct {
	db       *sql.DB
	zone     *time.Location
	since    string
	failures atomic.Uint64
}

func openClicks(dir string) (*ClickStore, error) {
	zone, e := time.LoadLocation("America/New_York")
	if e != nil {
		return nil, e
	}
	path := filepath.Join(dir, "clicks.sqlite")
	f, e := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	f.Close()
	db, e := sql.Open("sqlite", "file:"+url.PathEscape(path)+"?_pragma=busy_timeout(250)&_pragma=journal_mode(WAL)&_pragma=synchronous(FULL)")
	if e != nil {
		return nil, e
	}
	db.SetMaxOpenConns(1)
	failed := true
	defer func() {
		if failed {
			db.Close()
		}
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if _, e = db.ExecContext(ctx, `CREATE TABLE IF NOT EXISTS click_totals(day TEXT NOT NULL,route_key TEXT NOT NULL,total INTEGER NOT NULL CHECK(total>=0),PRIMARY KEY(day,route_key)) WITHOUT ROWID; CREATE TABLE IF NOT EXISTS click_meta(name TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;`); e != nil {
		return nil, e
	}
	if _, e = db.ExecContext(ctx, `INSERT OR IGNORE INTO click_meta(name,value) VALUES('since',?)`, time.Now().UTC().Format(time.RFC3339)); e != nil {
		return nil, e
	}
	var since string
	if e = db.QueryRowContext(ctx, `SELECT value FROM click_meta WHERE name='since'`).Scan(&since); e != nil {
		return nil, e
	}
	failed = false
	return &ClickStore{db: db, zone: zone, since: since}, nil
}
func (s *ClickStore) record(key string, now time.Time) error {
	ctx, cancel := context.WithTimeout(context.Background(), 350*time.Millisecond)
	defer cancel()
	_, e := s.db.ExecContext(ctx, `INSERT INTO click_totals(day,route_key,total) VALUES(?,?,1) ON CONFLICT(day,route_key) DO UPDATE SET total=total+1`, now.In(s.zone).Format("2006-01-02"), key)
	if e != nil {
		s.failures.Add(1)
	}
	return e
}
func validClickDates(from, to string) bool {
	if from == "" || to == "" {
		return from == "" && to == ""
	}
	f, e := time.Parse("2006-01-02", from)
	if e != nil || f.Format("2006-01-02") != from {
		return false
	}
	t, e := time.Parse("2006-01-02", to)
	return e == nil && t.Format("2006-01-02") == to && !f.After(t)
}
func (s *ClickStore) counts(from, to string) (map[string]int64, error) {
	if !validClickDates(from, to) {
		return nil, errors.New("invalid date interval")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	q := `SELECT route_key,SUM(total) FROM click_totals`
	args := []any{}
	if from != "" {
		q += ` WHERE day>=? AND day<=?`
		args = append(args, from, to)
	}
	q += ` GROUP BY route_key`
	rows, e := s.db.QueryContext(ctx, q, args...)
	if e != nil {
		return nil, e
	}
	defer rows.Close()
	counts := map[string]int64{}
	for rows.Next() {
		var key string
		var n int64
		if e = rows.Scan(&key, &n); e != nil {
			return nil, e
		}
		counts[key] = n
	}
	return counts, rows.Err()
}

type ClickHistoryInfo struct {
	Source               string `json:"source"`
	From                 string `json:"from"`
	To                   string `json:"to"`
	Timezone             string `json:"timezone"`
	ImportedClicks       int64  `json:"imported_clicks"`
	DailyRows            int    `json:"daily_rows"`
	CampaignsWithHistory int    `json:"campaigns_with_history"`
	RoutesMatched        int    `json:"routes_matched"`
}

func (s *ClickStore) history() (*ClickHistoryInfo, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	var raw string
	e := s.db.QueryRowContext(ctx, `SELECT value FROM click_meta WHERE name='history_keitaro'`).Scan(&raw)
	if errors.Is(e, sql.ErrNoRows) {
		return nil, nil
	}
	if e != nil {
		return nil, e
	}
	var h ClickHistoryInfo
	if e = json.Unmarshal([]byte(raw), &h); e != nil {
		return nil, e
	}
	if h.Source != "Keitaro" || h.Timezone != "America/New_York" || !validClickDates(h.From, h.To) || h.From == "" || h.ImportedClicks < 0 || h.DailyRows < 0 || h.CampaignsWithHistory < 0 || h.RoutesMatched < h.CampaignsWithHistory {
		return nil, errors.New("invalid historical provenance")
	}
	return &h, nil
}
func (a *App) clicksAPI(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		w.WriteHeader(405)
		return
	}
	q := r.URL.Query()
	from, to := q.Get("from"), q.Get("to")
	if !validClickDates(from, to) || len(q["from"]) > 1 || len(q["to"]) > 1 {
		jsonReply(w, 400, map[string]string{"error": "Período inválido: informe as duas datas; a data inicial não pode ser posterior à final."})
		return
	}
	counts, e := a.clicks.counts(from, to)
	if e != nil {
		jsonReply(w, 503, map[string]string{"error": "Contagem de cliques indisponível; redirecionamentos continuam ativos."})
		return
	}
	history, e := a.clicks.history()
	if e != nil {
		jsonReply(w, 503, map[string]string{"error": "Metadados do histórico indisponíveis; redirecionamentos continuam ativos."})
		return
	}
	jsonReply(w, 200, map[string]any{"history": history, "counts": counts, "timezone": "America/New_York", "since": a.clicks.since, "from": from, "to": to, "failed_writes": a.clicks.failures.Load(), "definition": "GET com redirecionamento; inclui acessos repetidos e robôs; não conta HEAD"})
}
