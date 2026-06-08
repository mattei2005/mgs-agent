---
name: yoast-wordpress
description: >
  Class-level umbrella for all Yoast SEO + Readability work on WordPress sites
  (eggbev and multi-site). Covers: score architecture (two-layer DB system,
  mu-plugin design), fixing readability violations on existing posts, and running
  the standalone Linux cron health monitor. Load this skill for any Yoast-related
  task — scoring, repairing, monitoring, or mu-plugin changes.
tags: [yoast, wordpress, seo, readability, monitoring, mu-plugin, eggbev, cron]
related_skills: [ssh-jump-runcloud]
---

# Yoast WordPress — Umbrella Skill

Three subsystems live here. Jump to the relevant section:

| Task | Section |
|------|---------|
| Understand how Yoast stores scores (DB, mu-plugin, REST) | § Score Architecture |
| Fix a red/yellow readability post | § Repair Readability |
| Build / run the site health monitor | § Health Monitor (Cron) |

Detailed reference files are in `references/`:
- `references/yoast-score-architecture.md` — full DB schema, mu-plugin history, yoastseo Node.js scorer
- `references/content-repair-readability.md` — full repair workflow with Python diagnostic
- `references/site-health-monitor.md` — full cron monitor design, pitfalls, checklist

---

## § Score Architecture

Yoast stores scores in **two layers**:

| Layer | Table / Key | Read by |
|-------|-------------|---------|
| 1 — Post meta | `wp_postmeta`: `_yoast_wpseo_linkdex` (SEO), `_yoast_wpseo_content_score` (Readability) | REST API (`?_fields=meta`) |
| 2 — Indexables | `wp_yoast_indexable`: `primary_focus_keyword_score`, `readability_score` | WP Admin post-list bubbles |

**Score thresholds (Yoast standard):**
| Score | Color |
|-------|-------|
| ≥ 71  | 🟢 green |
| 41–70 | 🟡 amber |
| ≤ 40  | 🔴 red |
| NULL  | ⚪ notAnalyzed |

**Critical table name:** `wp_yoast_indexable` (SINGULAR). `wp_yoast_indexables` does not exist — never use the plural form.

**mu-plugin current state (v4, 2026-04-24):**
- File: `yoast-rest-meta.php` (also absorbs `hide-from-home.php`, now deleted)
- `register_post_meta` for 4 fields: `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_title`, `_hide_from_home`
- **NO** `rest_after_insert_post` hook, **NO** indexable `build()` / `save()` calls
- Yoast owns the indexable entirely — zero interference
- `pre_get_posts` hides posts with `_hide_from_home=1` from home/feed/search

**Key lesson:** Never use `rest_after_insert_post` to touch the Yoast indexable. Any interference causes score flicker. Let Yoast calculate autonomously.

Server-side scoring uses the `@yoastseo` npm library. Entry point:
```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh eggbev <post_id>
```
See `references/yoast-score-architecture.md` for full Node.js API pitfalls.

---

## § Repair Readability

**When:** Post URL has 🔴/🟡 readability score. Steps:
1. Find post ID via HTML (REST `?slug=` may return `[]` on eggbev — known bug)
2. Run Python diagnostic to identify violations (sentence length, transitions, passive voice)
3. Rewrite only the violated rules
4. Validate (word count 450–500, subtitle ≤ 100 chars)
5. Publish via REST PATCH
6. Re-score with `yoast-score-post.sh`

**Key pitfall:** Preserve `<!-- wp:lazyblock/... /-->` blocks exactly — never rewrite their JSON payloads. Only touch `<!-- wp:paragraph -->` and `<!-- wp:heading -->` blocks.

See `references/content-repair-readability.md` for full Python diagnostic code, thresholds table, and before/after rewrite examples.

---

## § Health Monitor (Cron)

**When:** Building or extending a site-wide Yoast SEO + Readability cron monitor.

**Architecture:** Standalone Linux cron (NOT Hermes internal cron). Reads `wp_yoast_indexable` via SQL through SSH ProxyJump (see `ssh-jump-runcloud` skill). Posts to Discord webhook conditionally.

**Two metrics, same thresholds:** SEO (`primary_focus_keyword_score`) and Readability (`readability_score`) are reported separately — one post can be SEO 🟢 and Readability 🔴 simultaneously.

**Alert logic (OR):** Post if EITHER metric degrades:
- ≥ 3 percentage points more reds (vs prior snapshot)
- OR ≥ 5 new ambers (absolute count)
- Monday: always post weekly summary
- First run: always post baseline

**File naming convention:**
- Script: `monitor-yoast-health-{site}.sh`
- Snapshot: `data/yoast-health-{site}-snapshots.json`
- NOT `monitor-yoast-readability-*` (v1 name, readability-only)

**Critical pitfall — `op` CLI rate-limit:** Always wrap every `op item get` call in a retry helper with 2s backoff (3 attempts). Silent empty-string return on rapid consecutive calls is the symptom — NOT a credential problem.

See `references/site-health-monitor.md` for full implementation checklist, SSH execution pattern, snapshot JSON schema, migration guide, Discord message format, and all pitfalls.
