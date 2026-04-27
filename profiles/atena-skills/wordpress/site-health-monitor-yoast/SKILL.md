---
name: site-health-monitor-yoast
description: >
  Create a standalone Linux cron monitor that checks Yoast readability health
  for all published posts on a WordPress site via SQL (wp_yoast_indexable),
  with conditional Discord posting logic and daily snapshot history.
  Reference implementation: monitor-yoast-readability-eggbev.sh
tags: [yoast, wordpress, monitoring, cron, discord, readability, eggbev, health]
related_skills: [ssh-jump-runcloud, yoast-score-architecture]
---

# Site Health Monitor — Yoast Readability

## When to use

- User asks for a Yoast readability health monitor for a site
- Extending the eggbev monitor to other sites (zuout, lyzmo, etc.)
- Replacing a Hermes internal cron with a standalone Linux cron

## Architecture pattern

**Standalone Linux cron** (NOT Hermes internal cron). Reasons:
- Discord webhook is external — works without Hermes running
- Consistent with Zeus monitor pattern (monitor-auto-push.sh)
- More reliable for infra-critical jobs

## Key design decisions (validated 2026-04-26)

### 1. Read from SQL, not yoast-scorer
The `wp_yoast_indexable` table has `readability_score` column (integer 0–100, NULL = not analyzed).
A single SQL query via SSH returns ALL posts instantly — no need to run Node.js per post.

```sql
SELECT COALESCE(i.readability_score, -1) AS score, COUNT(*) AS cnt
FROM wp_yoast_indexable i
INNER JOIN wp_posts p ON i.object_id = p.ID
WHERE i.object_type = 'post' AND p.post_status = 'publish'
GROUP BY score ORDER BY score
```

`-1` sentinel = NULL = not analyzed. Parse separately from actual scores.

### 2. Yoast standard thresholds (NOT MGS custom)
| Score | Color | Label |
|-------|-------|-------|
| ≥ 71 | 🟢 green | good |
| 41–70 | 🟡 amber | ok |
| ≤ 40 | 🔴 red | bad |
| NULL | ⚪ not_analyzed | — |

**Important:** Do NOT use ≥90 as "green" threshold — that's too strict and inflates amber count.
Align with what Yoast WP Admin shows (the same table).

### 3. Conditional posting logic
- **First run (no snapshot)**: always post baseline
- **Monday**: always post weekly summary
- **Any other day**: post alert only if degraded:
  - ≥3 percentage points more reds (vs prior total)
  - OR ≥5 new ambers (absolute count)
- **Otherwise**: silent (no Discord post)

This prevents notification fatigue.

### 4. Snapshot file
Store daily snapshot in `/root/mgs-agent/data/yoast-readability-{site}-snapshots.json`.
Max 90 entries (~3 months). Structure:
```json
{
  "_meta": {"site": "eggbev", "thresholds": {"green_min": 71, ...}},
  "snapshots": [
    {"date": "2026-04-26", "timestamp": "...", "green": 157, "amber": 36,
     "red": 39, "not_analyzed": 0, "total": 232, "post_type": "baseline"}
  ]
}
```

### 5. Discord message prefix: `[YOAST]`
Not `[ATENA]`. Identifies the data type (Yoast SEO scores).
Format: `[YOAST] eggbev (26/04 10h): ...`

## SSH execution pattern

Script runs Python inside the remote script (not bash heredoc inside heredoc — causes parsing errors).

Pattern:
1. Write remote Python script locally → `/tmp/yoast_health_query_{site}.sh`
2. SCP to S01 via expect (S03 jump)
3. SSH execute via expect, capture output
4. Parse `YOAST_DATA:{json}` sentinel from stdout

Remote script emits exactly one line: `YOAST_DATA:{json}` or `YOAST_ERROR:{msg}`.

## Pitfalls

### PITFALL 1 — set -euo pipefail + 2>/dev/null can mask failure silently
When running with `set -euo pipefail`, if a subshell command with `2>/dev/null` exits
non-zero and exits the script, the log shows the last successful message, not the error.

**Symptom:** Script logs "Buscando credenciais..." then exits with code 1 with no further output.
**Cause:** Not the credentials (they work fine). Likely a subsequent command failing silently.
**Debug:** Run `bash -x script.sh 2>&1 | head -80` to see exact trace. Credentials OK → look further.
**Fix:** Test each `op item get` individually first. Run full script without piping to `head`.

### PITFALL 2 — wp_yoast_indexable NOT wp_yoast_indexables (singular)
Table name is singular. See yoast-score-architecture skill.

### PITFALL 3 — expect script: RunCloud MOTD timing
After `expect "Made with"`, use `sleep 3` before sending command. S01 MOTD has
multi-line banner. Without sleep, command lands mid-banner and doesn't execute.

### PITFALL 4 — S01 Python needs sudo -u runcloud for WP CLI
```bash
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev db query "..." --skip-column-names
```
Plain `sudo wp` or `wp` without sudo will fail — permissions.

### PITFALL 5 — SSH sleep duration
For a simple SQL query via Python, `sleep 45` in the expect script is sufficient.
For WP-CLI commands (like in yoast-score-post.sh), use `sleep 25` per command.

### PITFALL 6 — discord webhook HTTP 204 = success
Discord webhook returns `204 No Content` on success. Use `curl -o /dev/null -w "%{http_code}"`.
Any other code = failure to investigate.

## Crontab entry pattern

```
0 10 * * * /root/mgs-agent/scripts/monitor-yoast-readability-{site}.sh >> /root/mgs-agent/logs/monitor-yoast-readability-{site}.log 2>&1
```

When replacing an old cron, **comment it out** (don't delete) with DEPRECATED marker:
```
# DEPRECATED 2026-04-26: 0 10 * * * /root/mgs-agent/scripts/monitor-rec-readability.sh ...
```

## Implementation checklist

1. Write script to `/root/mgs-agent/scripts/monitor-yoast-readability-{site}.sh`
2. `chmod +x` the script
3. Test credentials individually before running full script
4. Run manually to generate baseline → verify Discord post + snapshot JSON
5. Add to crontab via `crontab /tmp/new_crontab.txt` (safe method — dump, edit, re-install)
6. Update `/root/mgs-agent/data/infra-inventory.json`: crons, scripts, data_files
7. Commit (autocommit will handle if service running)
8. Post REPORT-INFRA to zeus-admin-agent channel

## Extending to other sites

Replace `eggbev` with site key, update:
- `WP_PATH` on remote script
- Snapshot file path
- Log path
- Script name

Same SSH jump pattern (S03 → S01 for sites on S01; adjust for S02/S03 hosted sites).
Check ssh-jump-runcloud skill for server→webapp mapping.

## Reference files

- Script: `/root/mgs-agent/scripts/monitor-yoast-readability-eggbev.sh`
- Snapshot: `/root/mgs-agent/data/yoast-readability-eggbev-snapshots.json`
- Pattern reference: `/root/mgs-agent/scripts/monitor-auto-push.sh` (Zeus pattern)
