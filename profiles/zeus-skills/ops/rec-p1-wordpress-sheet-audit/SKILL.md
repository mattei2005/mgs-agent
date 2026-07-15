---
name: rec-p1-wordpress-sheet-audit
description: Use when Rodolfo asks to audit WordPress REC/P1 article pairs into a Google Sheet, including dates, links, and WordPress tags for both REC and linked P1 posts.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, wordpress, rec, p1, google-sheets, audit]
    related_skills: [content-publish-wordpress, productivity-workspace-apis]
---

# REC/P1 WordPress Sheet Audit

## Overview

Use this workflow to build a spreadsheet mapping REC articles to their linked P1 articles across MGS WordPress sites. The key relationship is not inferred from title alone: open the REC content and identify the card/button/final CTA link that points to the P1.

## Required Columns

Always use exactly these columns unless Rodolfo changes the format:

1. `Data REC`
2. `Artigo REC`
3. `Tags REC`
4. `Data P1`
5. `Artigo P1`
6. `Tags P1`

Do not collapse the P1 into the REC date. REC and P1 each need their own date, link, and WordPress tag list.

## Workflow

1. Identify the target sheet tabs/sites from the Sheet itself or the screenshot.
2. For each site, discover **all published posts** via WordPress REST. Use `/wp-json/wp/v2/search` as a fallback because some older REC/P1 posts may be reachable by direct ID/search but absent from ordinary `/posts` listing.
3. Fetch each post body and extract CTA/button/card/lazyblock links from `content.rendered`; prefer links inside `<a>` elements whose class/text/ancestor indicates button, card, LazyBlock, apply, solicitar, veja, continue, etc.
4. For every article, check whether all CTA/button/card/lazyblock links resolve to the same destination. If not, report the different links in the sheet; this catches redator/gestor mistakes where one button points to the wrong URL.
5. Classify flow:
   - REC→P1: article links to another same-site article and that destination is the P1/apply article.
   - P1 destination: if a URL is already the P1 destination of a REC row, **do not create a separate row with that same P1 in `Artigo REC` / column B**. It belongs only in `Artigo P1 / Link Final` / column E of the REC row. This prevents duplicate P1 rows.
   - SEO: article does not participate in REC→P1 flow; keep the article URL and record its final CTA/button link.
6. Fetch REC/P1 dates/tags through the correct WordPress REST route:
   - First extract the post ID from the public HTML (`postid-123`, `/wp-json/wp/v2/posts/123`, or `?p=123`).
   - Then call `/wp-json/wp/v2/posts/{id}?_fields=id,date,link,slug,tags,title,status`.
   - Do **not** rely only on `/wp-json/wp/v2/posts?slug=...`; on these sites it can return `[]` for published posts that still resolve correctly by ID, causing false `SEM TAGS NO WP`.
   - Resolve tag IDs through `/wp-json/wp/v2/tags?include=...`.
7. Fill the Google Sheet tab using the required REC/P1 columns plus operational audit columns when needed (`Tipo`, `Links de botão`, `Alerta links`). Coverage means all source URLs except P1 destination duplicates that are already represented in column E.
8. Verify by CSV export/readback for every edited tab: header contains the required REC/P1 columns, no duplicate P1 destination appears in column B, no blank spacer rows exist, and divergent links are present in the alert column.

## Pitfalls

- Some sites use `apply-now-*`, others use `aplicar-ahora-*`, others use `p1-*`; do not assume a single P1 slug pattern. The source of truth is the links in buttons/cards/LazyBlocks inside the article.
- Public `/wp/v2/posts` listings and public sitemaps can undercount vs the YYDevelopment Show Pages plugin. Canonical inventory validation is authenticated WordPress UI: log into that site's WP Admin, open `https://dominio.com/wp-admin/admin.php?page=yydev-show-pages`, and read the section `There are xxx published posts`. Use that plugin count/list as the 100% URL source. Use sitemap only as fallback/proxy when no logged-in WP session is available, and explicitly report the limitation.
- Never leave blank spacer rows for P1-only detections. If a URL must be represented, keep a row with the URL in the article/link column and a clear `Tipo`; blank REC rows look like sheet corruption.
- Extract CTA/card/LazyBlock links only from the real post body, never from related-post widgets, sidebar, footer, menu, category lists or homepage/blog listing blocks. On Cliquet theme use `jd-post-content`; on OpenZed theme use `article.main-content` and cut before `related-posts`/navigation/comments. LazyBlock markup may be inside HTML comments; unwrap comments inside the post body and extract only explicit `<a href>`/`href` values. **Do not regex every URL inside a LazyBlock comment**: image `src` and `blob:https://dominio/UUID` values can be misclassified as broken internal article links.
- After redirects, canonicalization, or legacy-IP-to-domain mapping, compare every destination against the source URL again and remove self-links. A legacy IP link can map back to the current article and otherwise create a false `MÚLTIPLOS DESTINOS` result.
- If many unrelated REC rows all point to the same P1, stop immediately: that almost always means the scraper captured `related posts`, not the actual CTA card/button.
- Canonicalize CTA URLs before final classification: follow redirects for same-site/internal CTA links, replace typo/legacy paths with the final canonical URL, fill Data/Tags P1 from that final post, and remove the canonical P1 row from column B if it is represented in column E. Keep the original URL in the button-links/audit column when useful.
- Canonicalize legacy/internal IP URLs found in buttons (e.g. `http://18.x.x.x/slug/` or `http://3.x.x.x/slug/`) to the current domain when the same slug exists on that site, and keep the original IP only in the button-links/audit column if needed.
- Tag columns C/F must be populated for every internal WordPress article URL represented in the sheet. Lookup order: post ID from HTML → `/wp-json/wp/v2/posts/{id}` → WordPress `tags`; if `tags: []`, confirm via the same post-ID route and only then write `SEM TAGS NO WP`. Do not leave internal article tag cells blank. Re-run a live taxonomy audit across all 4 sites before final delivery; if the public route later returns real tags for a URL that previously fell back to category/blank, update the sheet to the live tags.
- Cloudflare can intermittently return HTTP `526` only on a Basic-authenticated read while the same published direct post-ID endpoint is healthy without Authorization. For **read-only published-post audits**, retry the exact `/wp-json/wp/v2/posts/{id}` request unauthenticated after `403/526`, require HTTP 200 and the expected post ID, and record the fallback. Never use this fallback for drafts, private data, or writes.
- Missing-tag audit column: when Rodolfo asks to identify missing standard tags, add a new column (e.g. `Tags faltando`) and audit by tag classes, not exact expected values. For each REC article, verify presence of: vertical tag class, country tag class, language tag class (`lang_*`), and `rec`. For each internal P1 article, verify presence of: vertical tag class, country tag class, language tag class (`lang_*`), and `p1`. If a class is missing, write generic labels like `REC faltando: vertical, país` or `P1 faltando: língua, p1`; do not guess the exact country/vertical when it cannot be inferred. If all required classes exist, write `OK`.
- For Google Sheets browser fallback, an array literal formula in `A1` can populate a small test table quickly, but always validate via CSV export/readback.

## Country-tag integrity audits from article inventory Sheets

Use this branch when a Sheet lists WordPress articles by `Page ID`/URL and Rodolfo wants only the country taxonomy checked because country tags select the advertising blocks.

1. Treat the Sheet's `Page ID` as the primary lookup key; the edit-link column is a convenience, not a requirement to open every post manually.
2. Fetch each post by direct ID and resolve tag IDs to live term slugs through the approved authenticated REST/admin-session path when needed. Do not downgrade to manual article-by-article review merely because an anonymous route is unavailable.
3. Two-letter slugs are country candidates, not proof. Maintain a verified non-country exclusion list: MGS uses `cc` for the credit-card vertical, so `cc` must never be reported as a country merely because it has two letters.
4. Unless Rodolfo requests more, append exactly two operator-facing columns and do not duplicate the complete WordPress tag list or add a redundant status column:
   - `Tags de país`
   - `País sugerido (revisar)`
5. Populate `Tags de país` as follows:
   - one country tag: normalized slug, e.g. `us`;
   - multiple country tags: all normalized slugs, e.g. `es, us`;
   - none: exactly `sem tag de país`.
6. Populate `País sugerido (revisar)` conservatively:
   - one country tag: repeat that country;
   - multiple/no country tag: first prefer an explicit country code in a structured article URL such as `rec-es-*`, `aplicar-ahora-es-*`, or `apply-now-gb-*`;
   - otherwise use strong title/body evidence such as an explicit country, currency, regulator, or country-specific institution;
   - if evidence remains ambiguous, write `revisar` rather than silently choosing the site's majority country.
7. Highlight only actionable exceptions: missing country tag in red and multiple country tags in amber/yellow. The goal is to reduce Rodolfo/Raquel's manual review to those exceptions.
8. Before writing, confirm the destination columns are empty and save an exact CSV backup of every affected tab. After writing, validate the new cells and prove all pre-existing columns remain value-for-value unchanged.
9. Required readback: authenticated Sheets API when available plus independent CSV export. Report article count, fetch errors, missing-country count, multi-country count, mismatches, and backup path.
10. Taxonomy correction in WordPress is a separate authorized write phase. This audit writes only to the Sheet unless Rodolfo explicitly asks to alter post tags.

Country-tag audit and REC→P1 mapping are separate dimensions. If both are requested, keep country results on the existing article rows while deriving REC→P1 only from real CTA/card/LazyBlock links inside the post body. Never infer a REC→P1 relationship from `rec`, `apply`, or country text in a slug alone; inspect every real CTA/card/LazyBlock link, flag divergent destinations, and do not duplicate a linked P1 as a separate REC row.

## Graph-aware consolidation for human review

Use this branch when Rodolfo wants to prevent Raquel from checking the same article twice because a destination URL appears both in `Links internos encontrados` and as its own `Page URL` row.

1. Model the inventory as a directed graph before removing or hiding anything:
   - node = one unique canonical article URL;
   - edge = source article → internal destination found in the real post body;
   - compute target-only nodes, targets that are also sources, multi-incoming targets, and cycles.
2. Never delete/clear every target row blindly. A target may also point to a third article, may be referenced by several sources, or may participate in a cycle. Blind deletion loses chains and can recreate duplicate review work elsewhere.
3. Preserve the complete inventory and add destination-side review columns next to the internal-link column:
   - `Tags de país do destino`;
   - `País sugerido do destino`;
   - `Conferência Raquel`.
4. Assign each destination a single canonical review owner:
   - first/selected source row: `REVISAR DESTINO AQUI`, with destination country tags and suggestion populated;
   - additional source rows pointing to the same target: `JÁ CONSOLIDADO NA LINHA X`;
   - destination's own `Page URL` row: `NÃO CONFERIR TAG — MIGRADA PARA A LINHA X`.
5. Target-only rows may be hidden from Raquel's operational view after readback, but not deleted. Keep them available for traceability, rollback, future audits, and URL inventory completeness.
6. Targets that are also sources must remain visible so their outgoing relationship is not lost. Their own tags can be marked already handled while the row continues to represent the next edge in the chain.
7. For cycles, choose one stable canonical owner per node and preserve every edge; never resolve a cycle by deleting one of its article rows.
8. The optimization target is **one tag review per unique article**, not the smallest possible number of stored rows. Denormalizing destination tags beside links is allowed, but repeated destinations must point back to one canonical review row.
9. Before writing, save an exact backup and calculate the graph statistics. After writing, verify:
   - every original `Page URL` still exists;
   - each unique target has exactly one `REVISAR DESTINO AQUI` owner;
   - every skip/reference points to a valid line;
   - chains and cycles preserve all edges;
   - pre-existing columns remain value-for-value unchanged.
10. If Rodolfo explicitly requests physical deletion after seeing the graph-aware plan, treat that as a separate destructive phase with backup, explicit target set, and rollback/readback validation.

## References

- `references/full-site-rec-p1-seo-audit-2026-07-09.md` — complete-site audit pattern for REC→P1 plus SEO/single articles, CTA/button link divergence reporting, and Google Sheets paste/readback details.

## Verification Checklist

- [ ] Each tab has the required REC/P1 columns in order; when doing complete-site audits, include `Tipo`, `Links nos botões`, and `Alerta links`.
- [ ] Each target site has the requested coverage: sample size or all published posts, depending on Rodolfo's scope.
- [ ] Each P1 URL was found inside the REC content, not guessed from slug similarity alone.
- [ ] Every CTA/button/card/lazyblock link in the article was checked for consistency; divergent links are reported in the sheet.
- [ ] WordPress tags for REC and P1 were resolved from tag IDs.
- [ ] Google Sheet readback confirms the data is present remotely and alert counts match local extraction.
