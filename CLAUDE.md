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

## Current State (2026-04-27)

Foundation complete (Phase 1 ✅). Pipeline operational in production.

**Active agents:** Zeus (admin) + Atena (content), both online with auto-thread, anti-loop, output discipline.

**Production stats:**
- eggbev.com: 232 posts published
- Yoast scores: 158 SEO 🟢 / 157 Readability 🟢 (latest weekly snapshot)
- Crontab: 7 active monitors (sync-souls, auto-push, yoast-health, pending-reports, service-restarts, anthropic-cost, tool-loops)
- Auto-push to GitHub on every commit (post-commit hook)

**Recent foundational commits (oldest → newest):**

- `15cfcd2` — `fix(gemini): use --rawfile to bypass MAX_ARG_STRLEN limit` (also: `.env` sourcing + `--vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}"` in Gemini key lookup)
- `8d5f74b` — `fix(gemini): write request payload to temp file for curl -d @` (+ unified `cleanup_temps` via `TEMP_FILES[]` array, one `trap EXIT`)
- `458d07a` — `chore(wp): source .env for systemd/cron use`
- `93547b8` — `fix(gemini): accept both camelCase and snake_case in response parsing`

### Tests passed

1. **Credentials path** — 1P Service Account token + `OP_DEFAULT_VAULT` resolve both Gemini API key and WP credentials correctly.
2. **Gemini payload transport** — base64-encoded card image (~140 KB) no longer trips the kernel `MAX_ARG_STRLEN` (128 KB / single argv entry); carried via `jq --rawfile` + `curl -d @file`.
3. **Gemini end-to-end** — request succeeds, response parsed, PNG saved. Verified with slug `aib-visa-gold` → `/tmp/featured-aib-visa-gold.png` (1248×832, 1.87 MiB, 1 attempt, scene=nighttime metropolis). See `data/debug-featured-aib.png`.

### Test pending

~~4. **Full publish pipeline**~~ **PASSED 2026-04-23** — End-to-end REC pipeline validated in production. AIB Visa Gold (post 62008): SEO 84 🟢 / Readability 90 🟢. Multiple RECs published since then (Barclaycard Platinum, Virgin Atlantic Reward, etc.).

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

## Known Issue: WP REST /posts?slug= filter broken on eggbev

Symptom: GET /wp-json/wp/v2/posts?slug=<existing-slug>&status=any returns []
even when the slug exists (verified via direct GET /posts/<id>). Affects
both auth and unauth requests, and all status filters tested (publish, draft,
trash, auto-draft, any). Other endpoints unaffected: /media?slug= works,
/posts?per_page=N (no filter) works, GET /posts/<id> direct works.

Suspected cause: Plugin interference in `rest_post_query` filter hook.
Likely culprits on eggbev: Rank Math SEO, Wordfence, custom theme functions.

Workaround: check-slug-conflict.sh detects attachments correctly (via /media)
but cannot detect post conflicts. create-post.sh still calls the check
fail-closed but coverage is partial on eggbev. Other WP sites in portfolio
may not be affected.

Investigation TODO (low priority, requires Raquel + downtime risk):
1. Disable Rank Math REST integration → re-test
2. Disable Wordfence REST API protection → re-test
3. If both clean → check theme/mu-plugins for rest_post_query hooks
4. Once culprit identified, configure exception or accept native behavior

Detection: check-slug-conflict.sh now logs WARN when /posts query returns
0 results (likely false negative due to filter interference). In production,
look for these WARN entries to identify affected sites.

## Agent Roadmap

### Philosophy

Each agent is a specialized "employee" of MGS Digital Corp's content operation.
Zeus is the General Manager — sees everything, authorizes users, monitors agents.
Specialized agents report to Zeus and execute their domain autonomously.

### Phase 1 — Foundation (2026-04-21 → 2026-04-23, ✅ COMPLETE)

**Zeus** — Admin Agent / General Manager
- Discord channel: zeus-admin-agent
- Whitelist: Rodolfo (Super Admin)
- Receives: all events from other agents (started, paused, completed, errors, auth requests)
- Proactive: alerts when agents go offline, auto-summaries
- Commands: status, list users, aprova/nega, pending, last N, pipeline <agent>

**Atena** — Content Agent
- Discord channel: atena-content-agent
- Whitelist: Raquel
- Combines skills: content-generate-rec + content-publish-wordpress
- Full pipeline: WebFetch research → generate article → create images → publish WordPress
- Reports to Zeus at each lifecycle event
- 4 mandatory human-review pauses (after Step 2, 5, 11.1, 11.5)

### Phase 2 — Quality Assurance (planned)

**Hermes** — Site Auditor / Quality Manager
- Function: keep all sites "100% redondos" at all times
- Audit categories:
  - Links: broken links, redirect chains, dead external links
  - SEO: keyword stuffing, meta descriptions, alt text, schema markup
  - Content: plagiarism, readability, keyword density
  - Product/Card: card existence check, benefit updates, fee changes
  - Legal/Compliance: privacy policy, terms, cookie banner, disclaimers
  - AdSense/AdX: Google guidelines enforcement (YMYL, clickbait, prohibited categories)
  - Performance: Lighthouse scores, Core Web Vitals, page speed
  - Mobile: responsiveness
  - Accessibility: WCAG compliance, contrast, ARIA
  - Duplication: canonical tags, duplicate content
  - Images: alt text, optimization, WebP
  - Structure: sitemap.xml, robots.txt, internal linking
- Country-specific regulatory audits:
  - UK: FCA financial product disclaimers
  - US: TILA/Reg Z disclosures
  - EU: GDPR + cookie compliance
  - BR: BACEN credit card regulations
  - MX: CNBV compliance
- Additional checks (Claude suggestions to Rodolfo):
  - Schema.org markup for financial products (Review schema, FAQPage)
  - HTTPS mixed content detection
  - Meta robots conflicts (noindex where shouldn't be)
  - Abandoned drafts (>X days)
  - Outdated posts (>6 months in competitive keywords)
- Output: prioritized checklist → assigned to Raquel with tracking
- Reports to Zeus

### Phase 3 — Marketing (future)

**Ares** — Ads Manager
- Platforms: Facebook Ads Manager + Google Ads
- Functions: campaign creation, monitoring, optimization, A/B testing
- Budget allocation between campaigns
- Automation: pause underperforming, scale high-ROI
- Reports to Zeus with ROI dashboards

### Phase N — Beyond

Additional agents to be added as business grows. Examples for later consideration:
- Analytics agent (extraction + reporting)
- Email campaign agent
- SEO research agent
- Competitor intelligence agent

### Communication pattern

All agents → Zeus via Discord webhook (posts to #zeus-admin-agent channel).
Zeus → agents via direct messages in their respective channels (future:
inter-agent orchestration).

Event types sent to Zeus:
- pipeline_started (agent, user, request_summary)
- pipeline_paused (agent, step, awaiting_from)
- pipeline_completed (agent, duration, output_url)
- error (agent, step, error_message)
- auth_request (agent, user, request)
- unauthorized_attempt (agent, user, request)
- health_heartbeat (agent, uptime) — periodic

## Technical Debt

- `skills/content-publish-wordpress/scripts/upload-image.sh`: output JSON does not include `mime_type`. LazyBlock does not consume it, but useful for debug/auditing. Add in the next refactor.
- ~~`upload-image.sh`: missing HTTP status-code capture~~ **RESOLVED 2026-04-27** — All WP-facing scripts now capture `%{http_code}` via `wp_curl_auth` helper.
- ~~WP credential handling: scripts pass password via `curl -u "user:pass"` (briefly exposed in argv)~~ **RESOLVED 2026-04-27** — All 6 WP-facing scripts (`upload-image.sh`, `create-post.sh`, `update-yoast.sh`, `resolve-term.sh`, `check-slug-conflict.sh`, `test-connection.sh`) migrated to `wp_curl_auth` helper that uses `curl -K tempfile` (chmod 600). Password never appears in `ps aux` or `/proc/*/cmdline`. See `docs/security/migration-curl-auth-20260427.md`.
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

This document is consulted by Claude Code (CLI) and Claude.ai (web) sessions
working on this repository. State is reconstructed from:

1. Current `git log` and `git diff`
2. `data/infra-inventory.json` (run `bash scripts/infra-discovery.sh` to refresh)
3. `data/auto-push-monitor.json`, `service-restart-state.json`, etc. (state files)
4. SOULs in `profiles/zeus-soul.md` and `profiles/atena-soul.md` (agent identity + Case Studies)
5. Active session journal in `/mnt/transcripts/` (if Claude.ai web with code interpreter)

## Next Steps

- Execute Test 4 (end-to-end): run `content-generate-rec` against a real card slug, verify the WP post is created with correct article body, featured image, and Yoast meta.
- Add minimum-dimension filter to `scripts/search-card-image.sh` tier 2 to eliminate the 48×48 false-positive.
