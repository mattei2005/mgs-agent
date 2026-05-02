---
name: site-health-monitor-yoast
description: >
  Create a standalone Linux cron monitor that checks Yoast SEO + Readability
  health for all published posts on a WordPress site via SQL (wp_yoast_indexable),
  with conditional Discord posting logic and daily snapshot history.
  Reference implementation: monitor-yoast-health-eggbev.sh
tags: [yoast, wordpress, monitoring, cron, discord, readability, seo, eggbev, health]
related_skills: [ssh-jump-runcloud, yoast-score-architecture]
---

# Site Health Monitor — Yoast (SEO + Readability)

## When to use

- User asks for a Yoast health monitor for a site
- Extending the eggbev monitor to other sites (zuout, lyzmo, etc.)
- Replacing a Hermes internal cron with a standalone Linux cron

## Architecture pattern

**Standalone Linux cron** (NOT Hermes internal cron). Reasons:
- Discord webhook is external — works without Hermes running
- Consistent with Zeus monitor pattern (monitor-auto-push.sh)
- More reliable for infra-critical jobs

## Two metrics, one monitor

Yoast has two independent scores per post. Both live in `wp_yoast_indexable`:

| Column | Metric | WP Admin bubble |
|--------|--------|----------------|
| `readability_score` | Readability | Left bubble |
| `primary_focus_keyword_score` | SEO | Right bubble |

**Same thresholds for both:**
| Score | Color | Label |
|-------|-------|-------|
| ≥ 71 | 🟢 green | good |
| 41–70 | 🟡 amber | ok |
| ≤ 40 | 🔴 red | bad |
| NULL | ⚪ not_analyzed | — |

**Do NOT use ≥90 as "green" threshold** — too strict, inflates amber. Use Yoast standard (≥71).

**Important:** The same post can be SEO 🟢 and Readability 🔴 simultaneously.
Always report them separately and note this in the Discord message.

## Key design decisions (validated 2026-04-26)

### 1. Read from SQL, not yoast-scorer

Two queries, one per metric. Run via Python inside the remote bash script:

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

### 2. Conditional posting logic — OR across metrics

Alert if EITHER metric degrades (not both). Rationale: they measure different things.
A SEO degradation that doesn't affect readability is still a real problem.

- **First run (no snapshot)**: always post baseline
- **Monday**: always post weekly summary  
- **Any other day**: post alert if ANY metric has:
  - ≥3 percentage points more reds (vs prior total)
  - OR ≥5 new ambers (absolute count)
- **Otherwise**: silent (no Discord post)

### 3. Snapshot format — nested SEO + Readability

```json
{
  "_meta": {"site": "eggbev", "thresholds": {"green_min": 71, "amber_min": 41, "red_max": 40}},
  "snapshots": [
    {
      "date": "2026-04-26",
      "timestamp": "2026-04-27T03:33:05Z",
      "total": 232,
      "post_type": "silent",
      "seo": {
        "green": 158, "amber": 39, "red": 0, "not_analyzed": 35
      },
      "readability": {
        "green": 157, "amber": 36, "red": 39, "not_analyzed": 0
      }
    }
  ]
}
```

Max 90 entries (~3 months).

### 4. Snapshot migration — old readability-only format

When upgrading from readability-only monitor, auto-migrate at first run:

```python
# Old format (flat keys): {"date":..., "green":157, "amber":36, "red":39, ...}
# New format (nested): {"date":..., "seo": {...} or None, "readability": {...}}

for old_snap in old_data["snapshots"]:
    new_snap = {
        "date": old_snap.get("date"),
        "timestamp": old_snap.get("timestamp"),
        "total": old_snap.get("total", 0),
        "post_type": old_snap.get("post_type", "baseline"),
        "seo": None,   # no SEO history in old snapshots — skip comparison on first new run
        "readability": {
            "green":        old_snap.get("green", 0),
            "amber":        old_snap.get("amber", 0),
            "red":          old_snap.get("red", 0),
            "not_analyzed": old_snap.get("not_analyzed", 0)
        }
    }
```

When reading prev snapshot, check `d.get('seo') is not None` before computing SEO delta.
If `seo` is None, log "Snapshot anterior sem SEO — comparação SEO ignorada nesta run" and skip SEO delta.

### 5. Discord message format

```
📊 [EGGBEV.COM] [YOAST] Baseline (26/04 10h)   ← or ⚠️ ALERTA / 📅 Relatório semanal
Total posts publicados: **232**

⚠️ *Cada post conta em ambas as métricas (mesmo post pode ser SEO 🟢 + Read 🔴):*

🎯 **SEO:**        158🟢 / 39🟡 / 0🔴 / 35⚪
📖 **Readability:** 157🟢 / 36🟡 / 39🔴 / 0⚪

Variação SEO vs ontem: +29 amarelo(s) ⬆️, -62 verde(s) ⬇️
Variação Readability vs ontem: +32 vermelho(s) ⬆️, +21 amarelo(s) ⬆️

💬 Para listar URLs por cor/métrica, peça no <#1496267571543019653>
```

**Convenção de prefixo (escalável):** `[SITE.COM] [MÉTRICA]`
- Site primeiro — identifica origem imediatamente ao escanear canal
- Métrica segundo — tipo de dado ([YOAST], [BACKUP], [UPTIME], etc.)
- Exemplo futuro: `[ZUOUT.COM] [YOAST] Relatório semanal (...)`, `[LYZMO.COM] [BACKUP] ALERTA (...)`

Prefix: `[SITE.COM] [YOAST]` (not just `[YOAST]`). Site before metric — scalable for multi-site.
Channel: `#alerts-yoast` (webhook `Discord Webhook - Alerts Yoast Channel`), NOT `#atena-content-agent`.

## SSH execution pattern

Remote script runs Python (not nested bash heredoc — causes parsing errors).

Flow:
1. Write remote Python script locally → `/tmp/yoast_health_query_{site}.sh`
2. SCP to S01 via expect (S03 jump)
3. SSH execute via expect, `sleep 55` (two SQL queries need ~10s more than one)
4. Parse `YOAST_DATA:{json}` sentinel from stdout

Remote script emits exactly one line: `YOAST_DATA:{json}` or `YOAST_ERROR:{metric}:{msg}`.

## File naming convention

| Artifact | Pattern |
|----------|---------|
| Script | `monitor-yoast-health-{site}.sh` |
| Log | `logs/monitor-yoast-health-{site}.log` |
| Snapshot | `data/yoast-health-{site}-snapshots.json` |

**NOT** `monitor-yoast-readability-*` — that was the v1 name (readability-only).
The current pattern covers both metrics, so "health" is the right term.

## Pitfalls

### PITFALL 1 — op CLI rate-limit em runs consecutivos rápidos ⚠️ CRÍTICO

**Sintoma:** Script loga "Buscando credenciais..." → exit 1 silencioso sem mais output.
**Causa:** `op` CLI retorna string vazia sem stderr em runs muito próximos.
**NÃO É problema de credenciais** — rodar `op item get ...` manualmente logo depois funciona.

**Fix obrigatório:** Retry helper com backoff 2s, 3 tentativas. Sempre usar em todos os `op` calls:

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

WEBHOOK_URL="$(op_get_retry 'Discord Webhook - MGS Alerts Channel' 'MGS Conteúdo' 'label=webhook_url')" || true
S03_PASS="$(op_get_retry 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' 'MGS Conteúdo' 'password')" || true
S01_PASS="$(op_get_retry 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' 'MGS Conteúdo' 'password')" || true
```

**Debug:** `bash -x script.sh 2>&1 | head -80` — se credenciais aparecem OK no trace mas exit 1, buscar mais adiante com `| head -120`.

### PITFALL 2 — wp_yoast_indexable NOT wp_yoast_indexables (singular)
Table name is singular. See yoast-score-architecture skill.

### PITFALL 3 — expect script: RunCloud MOTD timing
After `expect "Made with"`, use `sleep 3` before sending command.

### PITFALL 4 — S01 Python needs sudo -u runcloud for WP CLI
```bash
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev db query "..." --skip-column-names
```

### PITFALL 5 — SSH sleep com duas queries precisa de mais tempo
Readability-only monitor: `sleep 45`. Com SEO + Readability (duas queries): `sleep 55`.
Ajustar se adicionar mais métricas.

### PITFALL 6 — discord webhook HTTP 204 = success
Discord webhook returns `204 No Content` on success. Any other code = failure.
```bash
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" -d "$DISCORD_MSG" --max-time 15)
[[ "$HTTP_CODE" == "204" ]] && log "Discord: OK" || log "AVISO: HTTP ${HTTP_CODE}"
```

### PITFALL 7 — SEO score ≠ Readability score em muitos posts
Observado em eggbev (2026-04-26): SEO 🟢158/🟡39/🔴0/⚪35 vs Read 🟢157/🟡36/🔴39/⚪0.
Os 35 não-analisados do SEO são posts publicados via REST sem passar pelo editor.
Os 39 vermelhos de readability são posts com conteúdo curto/problemático.
Sempre reportar separadamente — nunca agregar as duas métricas.

## Implementation checklist

1. Write script to `/root/mgs-agent/scripts/monitor-yoast-health-{site}.sh`
2. `chmod +x` the script
3. If upgrading from readability-only: point `OLD_SNAPSHOT_FILE` to old file, script auto-migrates
4. Test credentials individually before running full script (isolate `op` calls)
5. Run manually to generate baseline → verify Discord post + snapshot JSON structure
6. Add to crontab (comment out old cron with DEPRECATED marker)
7. Update `/root/mgs-agent/data/infra-inventory.json`: crons, scripts, data_files
8. Commit
9. Post REPORT-INFRA to zeus-admin-agent channel (canal ID: `1496267442899521627`)

## Teste empírico do alerta (procedimento validado)

Para validar alerta **sem tocar em posts de produção**:

```bash
SNAP="data/yoast-health-{site}-snapshots.json"

# 1. Backup
cp "$SNAP" "${SNAP}.bak-test"

# 2. Fabricar snapshot "ontem muito bom" em AMBAS métricas
python3 -c "
import json
with open('$SNAP') as f: d = json.load(f)
d['snapshots'] = [{'date':'2026-04-25','timestamp':'2026-04-26T02:00:00Z',
    'total':232,'post_type':'baseline','_test_fabricado':True,
    'seo':      {'green':220,'amber':10,'red':2,'not_analyzed':0},
    'readability':{'green':210,'amber':15,'red':7,'not_analyzed':0}}]
with open('$SNAP','w') as f: json.dump(d,f,indent=2)
"

# 3. Run → deve disparar alerta OR (qualquer métrica que degradar)
bash scripts/monitor-yoast-health-{site}.sh

# 4. Restaurar IMEDIATAMENTE
mv "${SNAP}.bak-test" "$SNAP"

# 5. Run de validação → deve ser silencioso (delta=0)
bash scripts/monitor-yoast-health-{site}.sh
```

**Resultado esperado run com alerta:**
- Log: `ALERTA: Readability — vermelhos ≥3pp` e/ou `ALERTA: SEO — ≥5 novos amarelos`
- Log: `Degradação detectada — alerta será postado`
- Discord: `⚠️ [YOAST] ALERTA degradação` com ambas métricas lado a lado + deltas

**Resultado esperado run silencioso:**
- Log: `Estável ou melhora — silencioso (sem post)` — zero post Discord

## Reference files (eggbev)

- Script: `/root/mgs-agent/scripts/monitor-yoast-health-eggbev.sh`
- Snapshot: `/root/mgs-agent/data/yoast-health-eggbev-snapshots.json`
- Old script (deprecated): `/root/mgs-agent/scripts/deprecated/monitor-yoast-readability-eggbev.sh`
- Pattern reference: `/root/mgs-agent/scripts/monitor-auto-push.sh` (Zeus pattern)
