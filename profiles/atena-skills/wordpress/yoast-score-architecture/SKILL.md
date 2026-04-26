---
name: yoast-score-architecture
description: >
  Architectural knowledge about how Yoast SEO stores and displays scores in WordPress,
  including the two-layer system (post meta vs. yoast_indexables table), REST endpoint map,
  and how scores are calculated. Reference before modifying yoast-rest-meta.php or any
  score-related logic in the MGS pipeline.
tags: [yoast, wordpress, seo, scores, mu-plugin, eggbev]
---

## Yoast Score Architecture — Two-Layer System

Yoast stores SEO and readability scores in **two separate layers**:

### Layer 1 — Post Meta (wp_postmeta)
Keys:
- `_yoast_wpseo_linkdex` — SEO score (0–100)
- `_yoast_wpseo_content_score` — Readability score (0–100)
- `_yoast_wpseo_title` — Custom SEO title
- `_yoast_wpseo_metadesc` — Meta description
- `_yoast_wpseo_focuskw` — Focus keyword

Readable via: `GET /wp-json/wp/v2/posts/{id}?_fields=meta`

These are the "legacy" storage keys. The Yoast editor reads/writes both layers on save.

### Layer 2 — Indexables Table (wp_yoast_indexables)
Columns:
- `primary_focus_keyword_score` — SEO score (integer, 0–100)
- `readability_score` — Readability score (integer, 0–100)
- `title`, `description`, `primary_focus_keyword`

**This is what the WP Admin post list reads.** The colored bubbles in `edit.php` come from this table, not from post meta.

### Score thresholds (Yoast standard)
| Score | Color | Label |
|-------|-------|-------|
| ≥ 71 | 🟢 green | good |
| 41–70 | 🟡 orange | ok |
| ≤ 40 | 🔴 red | bad |
| null / 0 | ⚪ gray | notAnalyzed |

**Note:** 70 is orange (ok), NOT green. Green starts at 71.

---

## yoast-rest-meta.php — MGS mu-plugin Analysis

File location: `/root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php`
Deployed to: `wp-content/mu-plugins/yoast-rest-meta.php` on each WP site.

### What it does (at `rest_after_insert_post`, priority 20):

1. **Registers post meta** as REST-visible (init hook) — needed so the pipeline can read/write Yoast meta via REST.
2. **Builds the indexable** via `Indexable_Builder::build()` — reconstructs the indexable row (canonical, robots, etc.) from current post data.
3. **Copies meta fields** to indexable (title, description, focus keyword).
4. **Layer 1 fallback (CONDITIONAL)** — lines 46–55: sets `_yoast_wpseo_linkdex=70` and `_yoast_wpseo_content_score=60` only if empty.
5. **Layer 2 override (UNCONDITIONAL)** — lines 57–61: always sets `readability_score=60` and `primary_focus_keyword_score=70` on the indexable.

### The masking problem (identified 2026-04-24)

The unconditional Layer 2 block (lines 57–61):
```php
$indexable = $indexable_repo->find_by_id_and_type($post->ID, 'post');
if ($indexable) {
    $indexable->readability_score           = 60;  // ALWAYS overwritten
    $indexable->primary_focus_keyword_score = 70;  // ALWAYS overwritten
    $indexable->save();
}
```
This runs AFTER `build()`, discarding any real score the builder may have calculated.
Result: every post published via REST shows 🟡 orange (ok) in the admin list regardless of actual content quality.

### Fix applied (2026-04-24)
**A1** (commit 26ba678 first pass): removed lines 57–61 (unconditional Layer 2 overwrite).
**A2** (corrective pass): removed lines 46–55 (conditional Layer 1 fallback).

**v3 (commit 8d9951b) — partial fix, flicker persisted:**
Root cause found: even after A1+A2, the `rest_after_insert_post` hook still called `build()` on EVERY REST update (not just on post creation). This still caused a 3-frame flicker on F5. Rodolfo validated visually — behavior unchanged vs. v2.

**v4 — TRUE FINAL FIX (consolidation, 2026-04-24):**
Diagnosis confirmed by comparing with external reference code (Felipe / Empire Ads plugin): ANY interference with the Yoast indexable — even `build()` on CREATE only — introduces an intermediate DB state that causes flicker. The correct pattern: **zero indexable interference, zero hooks on REST save**.

v4 also consolidates `yoast-rest-meta.php` and `hide-from-home.php` into a single mu-plugin. The `hide-from-home.php` was deleted from both locations.

**v4 architecture (current, 2026-04-24):**
- **No `rest_after_insert_post` hook at all**
- **No `build()`, no `save()`, no indexable interaction whatsoever**
- **Section 1:** `add_action('init')` → `register_post_meta` for 4 fields only: `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_title`, `_hide_from_home`
- **Section 2:** `add_action('pre_get_posts')` → hides posts with `_hide_from_home=1` from home/feed/category/tag/search/archive (was previously in separate `hide-from-home.php`)
- `linkdex` and `content_score` are NOT registered (they're OUTPUTS, not INPUTS)
- Yoast is 100% autonomous — builds/recalculates the indexable on its own timing

After v4:
- REST meta returns exactly 4 fields + WP `footnotes` (default)
- `_yoast_wpseo_linkdex` and `_yoast_wpseo_content_score` are absent from REST response
- `_hide_from_home` is present (empty string when not set, `'1'` when hidden)
- New posts show ⚪ gray (notAnalyzed) until editor opened once — honest, expected
- No flicker on F5 — Yoast JS runs uninterrupted, scores stable

Deployed to eggbev: MD5 `069270de4c07a9d15838ff45df65f539`. Files:
- `/root/mgs-agent/scripts/mu-plugins/yoast-rest-meta.php` (repo)
- `/home/runcloud/webapps/eggbev/wp-content/mu-plugins/yoast-rest-meta.php` (server)
- `hide-from-home.php` deleted from both locations

**Key lesson:** Do NOT use `rest_after_insert_post` to interact with the Yoast indexable. The pattern is: `register_post_meta` (show_in_rest=true) + `pre_get_posts` filter. Nothing else. Let Yoast own the indexable entirely.

Expected outcomes after v4:
- Posts published via REST have `_yoast_wpseo_linkdex` and `_yoast_wpseo_content_score` entirely absent from REST response
- List shows ⚪ gray (notAnalyzed) until editor is opened once — honest and acceptable
- No 3-frame flicker on F5 in the editor — stable score display
- Raquel's visual review pass is sufficient to trigger real score calculation
- `_hide_from_home` works correctly (hides posts from frontend when set to `'1'`) — logic consolidated into `yoast-rest-meta.php`

---

## Yoast REST Endpoint Map (eggbev, verified 2026-04-24)

All endpoints under `/wp-json/yoast/v1/`. Requires `administrator` role.

### Score inspection (GET, authenticated)
```
GET /yoast/v1/seo_scores?contentType=post
GET /yoast/v1/readability_scores?contentType=post
```
Returns distribution: `{scores: [{name:"good",amount:N,...}]}`
Does NOT return per-post scores. Aggregate only.

**Current distribution (2026-04-24, eggbev):**
- SEO: good=151, ok=39, bad=0, notAnalyzed=32
- Readability: good=150, ok=35, bad=16, notAnalyzed=21

### Indexing (POST, authenticated) — rebuilds indexable structure, NOT scores
```
POST /yoast/v1/indexing/posts     → rebuilds post indexables (structural, not scores)
POST /yoast/v1/indexing/general   → rebuilds general indexables
POST /yoast/v1/indexing/prepare   → prepares indexing queue
POST /yoast/v1/indexing/complete  → marks indexing as complete
```
`/yoast/v1/indexing/posts` returns `{"objects":[],"next_url":false}` when all posts already indexed.

### Other notable endpoints
```
GET  /yoast/v1/get_head           → renders Yoast <head> for a URL
POST /yoast/v1/link-indexing/posts → indexes internal links for posts
```

### Endpoints that do NOT exist
- No per-post score recalculation endpoint
- No `wpseo_indexable_content_score_calculate` or equivalent REST route

---

## Score Calculation — Node.js Server-Side Solution (IMPLEMENTED 2026-04-24)

Yoast's full SEO and readability analysis (keyword density, Flesch-Kincaid, passive voice, sentence length, etc.) runs **in the browser via JavaScript**. There is no PHP-callable equivalent.

**HOWEVER:** The same `@yoastseo` npm library that powers the Gutenberg editor is available on npm and can be run server-side via Node.js. The MGS pipeline uses this to compute real scores and write them to the DB after every REST publish.

### Implementation (content-generate-rec Step 12)

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh eggbev <post_id>
```

Output:
```json
{"status":"ok","post_id":62008,"seo_score":84,"readability_score":90,
 "indexable_seo":"84","indexable_read":"90","wpcli_ok":true}
```

**Flow:** Node fetches post via REST → runs `yoastseo` analysis → shell script writes scores via WP-CLI postmeta update + SQL UPDATE on `wp_yoast_indexable` → result confirmed via SSH/DB query.

### PITFALLS — yoastseo v3.6 API (learned 2026-04-24, trial & error)

**1. Correct module imports:**
```js
const { Paper, assessors } = require('yoastseo');
const { SEOAssessor, ContentAssessor } = assessors; // NOT SeoAssessor/ContentAssessor from top-level
const EnResearcher = require('./node_modules/yoastseo/build/languageProcessing/languages/en/Researcher.js').default;
// Note: .default is required — the module exports { default: Researcher }
```

**2. Constructor order — researcher is FIRST arg:**
```js
// CORRECT:
const researcher = new EnResearcher(paper);
const seoAssessor = new SEOAssessor(researcher);    // researcher first, options second
const readAssessor = new ContentAssessor(researcher);

// WRONG (causes "researcher.setPaper is not a function"):
new SEOAssessor({}, { researcher })
```

**3. AbstractResearcher lacks `getHelper()` — use language-specific Researcher:**
Using `AbstractResearcher` instead of `EnResearcher` causes `getHelper(...) is not a function`
errors during morphology analysis. Always use the language-specific Researcher:
- English: `languages/en/Researcher.js`
- No helpers needed explicitly — the `EnResearcher` includes them automatically.

**4. `require()` path — always `cd` to scorer dir first:**
```bash
# CORRECT — node_modules resolved relative to CWD:
cd /root/mgs-agent/scripts/yoast-scorer && node yoast-scorer.js ...

# WRONG — node_modules not found:
node /root/mgs-agent/scripts/yoast-scorer/yoast-scorer.js ...
```

**5. `wp yoast index --object-id` does NOT exist in Yoast v27.x:**
The WP-CLI Yoast command does not support per-post reindexing. Use SQL UPDATE directly:
```sql
UPDATE wp_yoast_indexable
  SET primary_focus_keyword_score=84, readability_score=90
  WHERE object_id=62008 AND object_type='post'
```

**6. `resolve-credentials.sh` returns JSON, not KEY=VALUE:**
```bash
# CORRECT:
WP_URL=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['wp_url'])")
WP_USER=$(echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['username'])")

# WRONG:
WP_URL=$(echo "$CREDS" | grep '^WP_URL=' | cut -d= -f2-)  # returns empty
```

**7. RunCloud ASCII art banner interferes with grep on SSH output:**
The RunCloud MOTD contains multi-digit ASCII art (e.g. `8888888b...888`). Grep with
`^[0-9]+` patterns will match banner digits and return wrong values.
Solution: use Python with `PARSE_ID` env var to match the exact post_id in the SQL result row.
See `yoast-score-post.sh` for the reference implementation.

### Validated results (2026-04-24, post 62008, Santander Edge)
- SEO score: **84** 🟢 | Readability: **90** 🟢
- Both written to `wp_yoast_indexable` and confirmed via SSH/DB query
- Admin post list shows green bubbles immediately after script runs
- No manual editor open required

---

## User Capabilities (eggbev, raqueloliveira, user ID 11)
- Role: `administrator`
- Has: `manage_options`, `wpseo_manage_options`, `rank_math_role_manager`
- The `seo_scores` and `readability_scores` endpoints return 401 without auth but work with the app password used by the pipeline.

---

## Validation Steps After mu-plugin Change (v4+)

1. Deploy mu-plugin to both locations, verify MD5 identical
2. Check Layer 1 via REST (PRIMARY validation):
   ```bash
   curl -s "https://eggbev.com/wp-json/wp/v2/posts/{id}?_fields=meta" \
     -u "$WP_USER:$WP_PASS" | jq .meta
   ```
   Must return exactly these 4 fields (+ WP `footnotes`):
   - `_yoast_wpseo_focuskw` — filled
   - `_yoast_wpseo_metadesc` — filled
   - `_yoast_wpseo_title` — filled
   - `_hide_from_home` — present (empty or `'1'`)
   - `_yoast_wpseo_linkdex` — **must NOT exist**
   - `_yoast_wpseo_content_score` — **must NOT exist**
3. Visually verify post list after running `yoast-score-post.sh`: post should show 🟢🟢 green bubbles (or appropriate color based on content quality). If scorer hasn't run yet, ⚪⚪ gray is expected.
4. **FLICKER TEST (manual):** Open post editor, press F5 — bubbles must NOT flash red or orange. They should appear stable.
5. Run scorer: `bash skills/content-generate-rec/scripts/yoast-score-post.sh eggbev <post_id>` → confirm JSON output shows `wpcli_ok:true` and `indexable_seo`/`indexable_read` match expected scores.

    ### PITFALL — wp_yoast_indexables vs wp_yoast_indexable (table name is SINGULAR)
The correct table name is **`wp_yoast_indexable`** (singular), NOT `wp_yoast_indexables` (plural).
Running `wp db tables '*yoast*'` may return empty even if Yoast is active — pattern matching via WP CLI can miss it.

Verified on eggbev (2026-04-24): querying `SELECT COUNT(*) FROM eggbevbd.wp_yoast_indexable` works correctly;
`wp_yoast_indexables` (with S) returns "Table doesn't exist".

**Consequence:** Always use singular `wp_yoast_indexable` in raw SQL queries. Do NOT rely on `wp db tables` output alone to confirm existence.

### PITFALL — wp_yoast_indexables may not exist on some installs
On eggbev (verified 2026-04-24), `wp_yoast_indexables` does NOT appear in `wp db tables` output, even though Yoast SEO v27.2 is active. The site also has Rank Math tables (`wp_rank_math_*`). This suggests:
- The site may have migrated from Rank Math and Yoast's indexables table was never created
- Or `wp db tables` pattern matching filtered it out

**Consequence:** Do NOT rely on a DB query to validate score changes on eggbev. Use REST meta comparison (Layer 1 only) as the primary evidence. Layer 1 comparison is sufficient because the conditional fallback (lines 46–55) was the mechanism writing 70/60 to postmeta — absence of those values confirms A2 removal worked.
