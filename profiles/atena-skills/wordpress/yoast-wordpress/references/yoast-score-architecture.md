# Yoast Score Architecture — Deep Reference

> Absorbed from: `yoast-score-architecture` skill (archived 2026-04-29)

## Two-Layer System

### Layer 1 — Post Meta (wp_postmeta)
Keys:
- `_yoast_wpseo_linkdex` — SEO score (0–100)
- `_yoast_wpseo_content_score` — Readability score (0–100)
- `_yoast_wpseo_title` — Custom SEO title
- `_yoast_wpseo_metadesc` — Meta description
- `_yoast_wpseo_focuskw` — Focus keyword

Readable via: `GET /wp-json/wp/v2/posts/{id}?_fields=meta`

### Layer 2 — Indexables Table (wp_yoast_indexable)
Columns:
- `primary_focus_keyword_score` — SEO score (integer, 0–100)
- `readability_score` — Readability score (integer, 0–100)

**This is what the WP Admin post list reads.** Colored bubbles in `edit.php` come from this table.

**CRITICAL: Table name is SINGULAR — `wp_yoast_indexable`, NOT `wp_yoast_indexables`.**
Running `wp db tables '*yoast*'` may return empty even if Yoast is installed.

---

## yoast-rest-meta.php — mu-plugin History

File: `/root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php`
Deployed: `wp-content/mu-plugins/yoast-rest-meta.php` on each WP site.

### The masking problem (identified 2026-04-24)
Old versions unconditionally set `readability_score=60` and `primary_focus_keyword_score=70`
on every REST publish — discarding real scores and showing every post as 🟡 orange.

### v4 — TRUE FINAL FIX (2026-04-24)
- **No `rest_after_insert_post` hook**
- **No `build()`, `save()`, or indexable interaction whatsoever**
- Section 1: `add_action('init')` → `register_post_meta` for 4 fields:
  `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_title`, `_hide_from_home`
- Section 2: `add_action('pre_get_posts')` → hides posts with `_hide_from_home=1`
- `linkdex` and `content_score` NOT registered (they are OUTPUTS, not INPUTS)
- Consolidates former `hide-from-home.php` (that file deleted from both locations)

Deployed MD5 on eggbev: `069270de4c07a9d15838ff45df65f539`

After v4: new posts show ⚪ notAnalyzed until editor opened — honest, expected. No flicker on F5.

**Key lesson:** Do NOT use `rest_after_insert_post` to interact with the Yoast indexable.
Pattern: `register_post_meta` (show_in_rest=true) + `pre_get_posts` filter. Nothing else.

---

## Yoast REST Endpoint Map (eggbev, verified 2026-04-24)

All under `/wp-json/yoast/v1/`. Requires `administrator` role.

### Score inspection (GET, authenticated)
```
GET /yoast/v1/seo_scores?contentType=post
GET /yoast/v1/readability_scores?contentType=post
```
Returns aggregate distribution only — NOT per-post scores.

**Current distribution (2026-04-24, eggbev):**
- SEO: good=151, ok=39, bad=0, notAnalyzed=32
- Readability: good=150, ok=35, bad=16, notAnalyzed=21

### Indexing (POST) — rebuilds indexable STRUCTURE, not scores
```
POST /yoast/v1/indexing/posts
POST /yoast/v1/indexing/general
POST /yoast/v1/indexing/prepare
POST /yoast/v1/indexing/complete
```

### Does NOT exist
- No per-post score recalculation endpoint
- No `wpseo_indexable_content_score_calculate` REST route

---

## Node.js Server-Side Scorer (yoastseo npm library)

Yoast analysis runs in the browser via JS. Server-side equivalent uses `@yoastseo` npm package.

Entry point:
```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh eggbev <post_id>
```

Output:
```json
{"status":"ok","post_id":62008,"seo_score":84,"readability_score":90,
 "indexable_seo":"84","indexable_read":"90","wpcli_ok":true}
```

Flow: Node fetches post via REST → runs `yoastseo` analysis → shell writes scores via
WP-CLI postmeta update + SQL UPDATE on `wp_yoast_indexable` → confirmed via SSH/DB query.

### PITFALLS — yoastseo v3.6 API (trial & error, 2026-04-24)

**1. Correct imports:**
```js
const { Paper, assessors } = require('yoastseo');
const { SEOAssessor, ContentAssessor } = assessors;
const EnResearcher = require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher.js').default;
// .default is required — module exports { default: Researcher }
```

**2. Constructor order — researcher is FIRST arg:**
```js
// CORRECT:
const researcher = new EnResearcher(paper);
const seoAssessor = new SEOAssessor(researcher);
const readAssessor = new ContentAssessor(researcher);

// WRONG (causes "researcher.setPaper is not a function"):
new SEOAssessor({}, { researcher })
```

**3. Use language-specific Researcher (`EnResearcher`), not `AbstractResearcher`.**
`AbstractResearcher` causes `getHelper(...) is not a function` during morphology analysis.

**4. Always `cd` to scorer dir before running Node:**
```bash
# CORRECT:
cd /root/mgs-agent/scripts/yoast-scorer && node yoast-scorer.js ...

# WRONG (node_modules not found):
node /root/mgs-agent/scripts/yoast-scorer/yoast-scorer.js ...
```

**5. `wp yoast index --object-id` does NOT exist in Yoast v27.x.**
Use SQL UPDATE directly:
```sql
UPDATE wp_yoast_indexable
  SET primary_focus_keyword_score=84, readability_score=90
  WHERE object_id=62008 AND object_type='post'
```

**6. `resolve-credentials.sh` returns JSON, not KEY=VALUE:**
```bash
WP_URL=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
# NOT: grep '^WP_URL=' | cut -d= -f2-  (returns empty)
```

**7. RunCloud ASCII art MOTD interferes with grep on SSH output.**
Use Python with `PARSE_ID` env var to match exact post_id in SQL result row.

### Validated (2026-04-24, post 62008, Santander Edge)
- SEO: 84 🟢 | Readability: 90 🟢
- Both written to `wp_yoast_indexable`, confirmed via SSH/DB query
- Admin list shows green immediately after script runs

---

## Validation Steps After mu-plugin Change (v4+)

1. Deploy mu-plugin to both locations, verify MD5 identical
2. Check Layer 1 via REST:
   ```bash
   curl -s "https://eggbev.com/wp-json/wp/v2/posts/{id}?_fields=meta" \
     -u "$WP_USER:$WP_PASS" | jq .meta
   ```
   Must return exactly 4 fields: `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`,
   `_yoast_wpseo_title`, `_hide_from_home`. `_yoast_wpseo_linkdex` and
   `_yoast_wpseo_content_score` **must NOT exist**.
3. Run scorer, confirm 🟢🟢 green bubbles in admin list.
4. **FLICKER TEST (manual):** Open post editor, press F5 — bubbles must NOT flash.

---

## User Capabilities (eggbev, raqueloliveira, user ID 11)
- Role: `administrator`
- Has: `manage_options`, `wpseo_manage_options`, `rank_math_role_manager`
