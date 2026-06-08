# Site Health Monitor — Yoast SEO + Readability

> Absorbed from: `site-health-monitor-yoast` skill (archived 2026-04-29)
> Related: `ssh-jump-runcloud` skill (SSH execution pattern)

Standalone Linux cron monitor that checks Yoast SEO + Readability health for all
published posts via SQL (`wp_yoast_indexable`), with conditional Discord posting
and daily snapshot history.

---

## Architecture: Standalone Linux cron (NOT Hermes internal cron)

Reasons: Discord webhook is external, consistent with Zeus monitor pattern (`monitor-auto-push.sh`), more reliable for infra-critical jobs.

---

## Two metrics — always report separately

| Column | Metric |
|--------|--------|
| `readability_score` | Readability (left bubble in WP admin) |
| `primary_focus_keyword_score` | SEO (right bubble) |

Same thresholds for both: ≥71 🟢, 41–70 🟡, ≤40 🔴, NULL ⚪ notAnalyzed.

**Do NOT use ≥90 as green — too strict, inflates amber. Use Yoast standard (≥71).**

One post can be SEO 🟢 and Readability 🔴 simultaneously. Never aggregate the two.

---

## SQL queries (run via Python inside remote bash script)

```python
def run_query(metric_col):
    sql = (
        f"SELECT COALESCE(i.{metric_col}, -1) AS score, COUNT(*) AS cnt "
        f"FROM wp_yoast_indexable i "
        f"INNER JOIN wp_posts p ON i.object_id = p.ID "
        f"WHERE i.object_type = 'post' AND p.post_status = 'publish' "
        f"GROUP BY score ORDER BY score"
    )
    result = subprocess.run(
        ["sudo", "-u", "runcloud", "wp", f"--path={WP_PATH}",
         "db", "query", sql, "--skip-column-names"],
        capture_output=True, text=True, timeout=60
    )
    ...

seo_raw  = run_query("primary_focus_keyword_score")
read_raw = run_query("readability_score")
```

`-1` sentinel = NULL = not analyzed. Classified separately from real scores.

---

## Conditional posting logic (OR across metrics)

- **First run (no snapshot):** always post baseline
- **Monday:** always post weekly summary
- **Any other day:** post alert if EITHER metric has:
  - ≥ 3 percentage points more reds (vs prior total), OR
  - ≥ 5 new ambers (absolute count)
- **Otherwise:** silent — no Discord post

---

## Snapshot JSON format

```json
{
  "_meta": {"site": "eggbev", "thresholds": {"green_min": 71, "amber_min": 41, "red_max": 40}},
  "snapshots": [
    {
      "date": "2026-04-26",
      "timestamp": "2026-04-27T03:33:05Z",
      "total": 232,
      "post_type": "silent",
      "seo":         {"green": 158, "amber": 39, "red": 0, "not_analyzed": 35},
      "readability": {"green": 157, "amber": 36, "red": 39, "not_analyzed": 0}
    }
  ]
}
```

Max 90 entries (~3 months). Old readability-only format (flat keys) is auto-migrated
on first new-format run — set `seo: null` on old entries, skip SEO delta for that run.

---

## SSH execution pattern

Remote script runs Python inside bash — NOT nested bash heredoc (causes parsing errors).

Flow:
1. Write remote Python script locally → `/tmp/yoast_health_query_{site}.sh`
2. SCP to S01 via expect (S03 jump) — see `ssh-jump-runcloud` skill
3. SSH execute via expect, `sleep 55` (two SQL queries need ~10s more than one query)
4. Parse `YOAST_DATA:{json}` sentinel from stdout

Remote script emits exactly: `YOAST_DATA:{json}` or `YOAST_ERROR:{metric}:{msg}`.

---

## Discord message format

```
📊 [EGGBEV.COM] [YOAST] Baseline (26/04 10h)
Total posts publicados: **232**

⚠️ *Cada post conta em ambas as métricas (mesmo post pode ser SEO 🟢 + Read 🔴):*

🎯 **SEO:**        158🟢 / 39🟡 / 0🔴 / 35⚪
📖 **Readability:** 157🟢 / 36🟡 / 39🔴 / 0⚪
```

**Prefix convention:** `[SITE.COM] [MÉTRICA]` — site first, metric second.
Channel: `#alerts-yoast` webhook (NOT `#atena-content-agent`).
Discord `204 No Content` = success.

---

## File naming convention

| Artifact | Pattern |
|----------|---------|
| Script | `monitor-yoast-health-{site}.sh` |
| Log | `logs/monitor-yoast-health-{site}.log` |
| Snapshot | `data/yoast-health-{site}-snapshots.json` |

NOT `monitor-yoast-readability-*` (v1 name, readability-only).

---

## Implementation checklist

1. Write script to `/root/mgs-agent/scripts/monitor-yoast-health-{site}.sh`
2. `chmod +x` the script
3. If upgrading from readability-only: point `OLD_SNAPSHOT_FILE` to old file (auto-migrates)
4. Test credentials individually before full run (isolate `op` calls)
5. Run manually → baseline → verify Discord post + snapshot JSON
6. Add to crontab (DEPRECATED-comment the old cron)
7. Update `/root/mgs-agent/data/infra-inventory.json`
8. Commit
9. Post REPORT-INFRA to #alerts-infra channel (ID: `1498132022634483894`)

---

## Alert test procedure (validated, no production impact)

```bash
SNAP="data/yoast-health-{site}-snapshots.json"
cp "$SNAP" "${SNAP}.bak-test"

# Fabricate "great yesterday" snapshot
python3 -c "
import json
with open('$SNAP') as f: d = json.load(f)
d['snapshots'] = [{'date':'2026-04-25','timestamp':'2026-04-26T02:00:00Z',
    'total':232,'post_type':'baseline','_test_fabricado':True,
    'seo':       {'green':220,'amber':10,'red':2,'not_analyzed':0},
    'readability':{'green':210,'amber':15,'red':7,'not_analyzed':0}}]
with open('$SNAP','w') as f: json.dump(d,f,indent=2)
"

bash scripts/monitor-yoast-health-{site}.sh   # should fire alert

mv "${SNAP}.bak-test" "$SNAP"  # restore IMMEDIATELY

bash scripts/monitor-yoast-health-{site}.sh   # should be silent
```

---

## Pitfalls

### PITFALL 1 — op CLI rate-limit on rapid consecutive runs ⚠️ CRITICAL

**Symptom:** Script logs "Buscando credenciais..." → silent exit 1 with no further output.
**Cause:** `op` CLI returns empty string without stderr on rapid consecutive calls.
**NOT a credential problem** — running `op item get ...` manually right after works.

**Mandatory fix — retry wrapper:**
```bash
op_get_retry() {
    local item="$1" vault="$2" field="$3"
    local val="" attempt=0
    while [[ $attempt -lt 3 ]]; do
        val="$(op item get "$item" --vault "$vault" --fields "$field" --reveal 2>/dev/null)" || true
        [[ -n "$val" ]] && echo "$val" && return 0
        attempt=$(( attempt + 1 ))
        [[ $attempt -lt 3 ]] && sleep 2
    done
    return 1
}
```
Use `op_get_retry` for every `op item get` call in the script.

**Debug:** `bash -x script.sh 2>&1 | head -120`

### PITFALL 2 — Table name is SINGULAR
`wp_yoast_indexable` (singular), NOT `wp_yoast_indexables`.

### PITFALL 3 — expect script: RunCloud MOTD timing
After `expect "Made with"`, use `sleep 3` before sending command.

### PITFALL 4 — S01 Python needs sudo -u runcloud for WP CLI
```bash
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev db query "..." --skip-column-names
```

### PITFALL 5 — SSH sleep with two queries needs more time
Readability-only: `sleep 45`. SEO + Readability (two queries): `sleep 55`.

### PITFALL 6 — Discord webhook HTTP 204 = success
```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" -d "$DISCORD_MSG" --max-time 15)
[[ "$HTTP_CODE" == "204" ]] && log "Discord: OK" || log "AVISO: HTTP ${HTTP_CODE}"
```

### PITFALL 7 — SEO ≠ Readability on many posts
Observed eggbev (2026-04-26): SEO 🟢158/🟡39/🔴0/⚪35 vs Read 🟢157/🟡36/🔴39/⚪0.
The 35 SEO not-analyzed = posts published via REST without opening editor.
The 39 readability reds = posts with short/problematic content.
Always report separately — never aggregate.

---

## Reference files (eggbev)

- Script: `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`
- Snapshot: `/root/mgs-agent/data/yoast-health-eggbev-snapshots.json`
- Deprecated: `/root/mgs-agent/scripts/deprecated/monitor-yoast-readability-eggbev.sh`
- Pattern reference: `/root/mgs-agent/scripts/monitor-auto-push.sh` (Zeus pattern)
