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

## How to Resume This Session

```bash
claude --resume c0ee7f2a-9489-43fd-b190-1e9a1940c0ad
```

## Next Steps

- Execute Test 4 (end-to-end): run `content-generate-rec` against a real card slug, verify the WP post is created with correct article body, featured image, and Yoast meta.
- Add minimum-dimension filter to `scripts/search-card-image.sh` tier 2 to eliminate the 48×48 false-positive.
