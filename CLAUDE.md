# MGS Agent — Content Generation Pipeline

## Project Overview

Automated pipeline for generating and publishing credit card recommendation (REC) articles to WordPress. Built as composable Claude Code skills that fetch card data, generate featured images via Gemini, assemble articles from templates, and publish with Yoast SEO metadata.

## Architecture

- **Host**: VPS `87.99.151.107` (Linux)
- **Working dir**: `/root/mgs-agent/`
- **Credentials**: 1Password Service Account token in `/root/mgs-agent/.env` (never read or exposed). Default vault `MGS Conteúdo` via `OP_DEFAULT_VAULT`. Both shell scripts source `.env` at startup so they work under `systemd`/`cron` too.
- **Image generation**: Google Gemini 2.5 Flash Image API, Tier 1 Prepay ($300 credits, valid through Jul 2026).
- **Skills**:
  - `content-generate-rec` — fetches card data, generates composition image, assembles article from per-country/language/vertical templates.
  - `content-publish-wordpress` — reusable WordPress publishing utility (media upload, post create/update, Yoast meta, term resolution).

## Key Files

### `skills/content-generate-rec/`
- `SKILL.md` — skill definition and trigger conditions
- `scripts/generate-featured-image.sh` — Gemini 16:9 composition with card overlay; tempfile-based payload (`--rawfile` + `curl -d @file`), unified `cleanup_temps` trap
- `scripts/search-card-image.sh` — tiered image search/download for card visual
- `scripts/validate-article.sh` — pre-publish validation
- `templates/` — per-country/language/vertical article templates

### `skills/content-publish-wordpress/`
- `SKILL.md`
- `scripts/resolve-credentials.sh` — resolves WP creds from 1Password using `data/sites.json`
- `scripts/create-post.sh` — creates/updates posts via WP REST API
- `scripts/resolve-term.sh` — category/tag ID resolution
- `scripts/update-yoast.sh` — Yoast SEO meta injection
- `scripts/upload-image.sh` — media upload

### Data / config
- `data/sites.json` — WP site registry with `credentials_ref` pointing to 1P items
- `data/debug-*.png` — latest debug artifacts
- `logs/generate-rec.log`, `logs/publish-wordpress.log`

## Current State (2026-04-21)

Commits on `main` from the current session (oldest → newest):

- `15cfcd2` — `fix(gemini): use --rawfile to bypass MAX_ARG_STRLEN limit` (also: `.env` sourcing + `--vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}"` in Gemini key lookup)
- `8d5f74b` — `fix(gemini): write request payload to temp file for curl -d @` (+ unified `cleanup_temps` via `TEMP_FILES[]` array, one `trap EXIT`)
- `458d07a` — `chore(wp): source .env for systemd/cron use`
- `93547b8` — `fix(gemini): accept both camelCase and snake_case in response parsing`

### Tests passed

1. **Credentials path** — 1P Service Account token + `OP_DEFAULT_VAULT` resolve both Gemini API key and WP credentials correctly.
2. **Gemini payload transport** — base64-encoded card image (~140 KB) no longer trips the kernel `MAX_ARG_STRLEN` (128 KB / single argv entry); carried via `jq --rawfile` + `curl -d @file`.
3. **Gemini end-to-end** — request succeeds, response parsed, PNG saved. Verified with slug `aib-visa-gold` → `/tmp/featured-aib-visa-gold.png` (1248×832, 1.87 MiB, 1 attempt, scene=nighttime metropolis). See `data/debug-featured-aib.png`.

### Test pending

4. **Full publish pipeline** — end-to-end REC article generation + publication to WordPress (article assembly from templates → featured image → WP media upload → post create → Yoast meta).

## Known Issues

- `scripts/search-card-image.sh` tier 2 occasionally returns a 48×48 placeholder/icon as a false-positive card image. Needs a minimum-dimension / aspect-ratio guard before accepting the candidate at tier 2.

## Test 4 Closure — AIB Visa Gold on eggbev.com

Status: **PASS** ✓
Date: 2026-04-21
Validated by: Raquel Oliveira (Slack: "sim" at 14:41)
Post ID: 61940 (initial test, deleted by Rodolfo) → 61948 (re-POST after cleanup)
Edit link: https://eggbev.com/wp-admin/post.php?post=61948&action=edit
Slug: rec-gb-cc-aib-visa-gold-2 (was -4 with 61940 due to draft 54050; after manual cleanup of 54050 + 61940, WP re-disambiguated to -2)

End-to-end pipeline steps exercised:
- resolve-credentials (1P SA)
- upload-image (card + featured)
- Gemini 2.5 Flash Image generation
- validate-article (word count)
- LazyBlock credit-card + botao assembly (compact URL-encoded)
- Subtitle insertion (Raquel's reference from post 8151, anti-invention rule applied)
- create-post (with categories, tags, featured_media, meta)
- update-yoast + verify (content_score 60, linkdex 70)
- `_hide_from_home=1` via REST (mu-plugin reads it)

Known acceptable deltas:
- Slug auto-disambiguated to `-4` (see débito: slug pre-check)
- Yoast reports 532 words vs `validate-article.sh` 478 — both acceptable
- `_hide_from_home` visual checkbox absent (intentional: mu-plugin, not plugin-based)

Slug auto-disambiguation behavior observed: After deleting conflicting drafts (54050 at slug -2, post 61940 at slug -4) and re-POSTing the same content, WP assigned slug -2 instead of base. WP appears to maintain reservations on base + -1 slugs even when no visible posts hold them — likely due to attachments, revisions, or auto-drafts in the same namespace. Reclaim via PUT was rejected (would risk overwriting the published reference post 8151 at base slug). Final slug -2 is acceptable for test artifact.

Next: Test 5 with REAL card data (HSBC Premier or Barclaycard Platinum, both UK-CC vertical) on eggbev.com — exercises LLM-generated subtitle without mock data fallback. Same template (rec-gb-cc-en.md) since templates are vertical-scoped, not site-scoped. Other verticals (e.g., mx-cc-es, us-loans-en, br-jobs-pt, gaming-roblox-en) require dedicated templates created and refined before testing in those territories.

## Technical Debt

- `skills/content-publish-wordpress/scripts/upload-image.sh`: output JSON does not include `mime_type`. LazyBlock does not consume it, but useful for debug/auditing. Add in the next refactor.
- `skills/content-publish-wordpress/scripts/upload-image.sh`: missing HTTP status-code capture via `curl -w '%{http_code}'`. If WP returns 401/403/500 with a JSON error body, the script does not detect the failure explicitly (only checks if `.id` exists in the response). Important fix before production.
- WP credential handling: all WP-facing scripts (`upload-image.sh`, `create-post.sh`, `update-yoast.sh`, `resolve-term.sh`) pass the Application Password as `curl -u "user:pass"`. This exposes the password briefly in `ps`/argv (milliseconds during curl execution). Acceptable for now; future fix = `curl -K config-file` or `--netrc-file` (both keep the secret off argv).
- **Canonical content structure (MANDATORY — Raquel's editorial rule):**

  Post content MUST start with an editorial subtitle as the first `<p>`:

      <!-- wp:paragraph -->
      <p>{subtitle}</p>
      <!-- /wp:paragraph -->

      <!-- wp:lazyblock/credit-card ... -->
      ...
      <!-- wp:paragraph -->
      <p>{intro 1}</p>
      <!-- /wp:paragraph -->

      ...

      <!-- wp:lazyblock/botao ... -->

  Subtitle rules (auto-generated in Step 5 by writer LLM):
  - MAX 100 characters (spaces + punctuation)
  - MUST contain exact focus keyphrase
  - MUST highlight 1 specific feature or benefit of the card
  - Editorial/news-subhead tone (punchy, verb-driven)
  - Third person, no 'you should'
  - British spelling for UK cards, etc.
  - No ellipsis, clean cut
  - No `<strong>` or `<em>` (plain text)
  - Position: FIRST element of `post_content` (before LazyBlock credit-card)

  WP `excerpt` field: INTENTIONALLY LEFT EMPTY. Single source of truth = subtitle in body. WP fallback auto-generates excerpt from first ~55 words of content, which equals the subtitle. No duplication.

  Draft markers: ZERO tolerance in `post_content`. Never, not even for testing. Use git/CLAUDE.md for dev tracking.

  **Subtitle data source (anti-invention rule):** The writer LLM MUST derive the subtitle from REAL card data extracted in Step 2 (Research the card) — actual fees, benefits, APR, and target audience from the `card_official_url`. Never invent benefits, competitors, or qualifiers. If Step 2 cannot confirm a fact, that fact cannot appear in the subtitle.

  **Test 4 exception (documented):** For post 61940 (AIB Visa Gold Card), the subtitle `AIB Visa Gold Card provides existing bank customers with premium travel benefits.` was sourced from Raquel's published reference post 8151 rather than LLM-generated. The Test 4 fixture used mock data (invented competitors and benefits for pipeline validation), so an LLM-generated subtitle would have compounded the mock with invented descriptors. Reusing the real reference post's subtitle preserves editorial truth while still exercising the pipeline's subtitle-insertion mechanics.
- **Slug auto-disambiguation by WP:** when prior drafts/trashed posts/revisions share the same `post_name`, WP appends `-N` to new posts' slugs. Pipeline should either (a) pre-check slug availability via `GET /wp/v2/posts?slug=<s>&status=any,trash,auto-draft` before POST and warn, or (b) accept drift and optionally PUT the canonical slug after cleaning conflicts. Observed on eggbev with `rec-gb-cc-aib-visa-gold-4` (post 61940) due to prior draft `rec-gb-cc-aib-visa-gold-2` (id 54050, 2026-03-02).

## How to Resume This Session

```bash
claude --resume c0ee7f2a-9489-43fd-b190-1e9a1940c0ad
```

## Next Steps

- Execute Test 4 (end-to-end): run `content-generate-rec` against a real card slug, verify the WP post is created with correct article body, featured image, and Yoast meta.
- Add minimum-dimension filter to `scripts/search-card-image.sh` tier 2 to eliminate the 48×48 false-positive.
