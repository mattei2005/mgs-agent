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
- Public `/wp/v2/posts` listings can undercount vs the YYDevelopment Show Pages plugin. When available, use `/wp-admin/admin.php?page=yydev-show-pages` / `yydev-show-pages` as the URL inventory source and reconcile counts before writing the sheet.
- Never leave blank spacer rows for P1-only detections. If a URL must be represented, keep a row with the URL in the article/link column and a clear `Tipo`; blank REC rows look like sheet corruption.
- Extract CTA/card/LazyBlock links only from the real post body, never from related-post widgets, sidebar, footer, menu, category lists or homepage/blog listing blocks. On Cliquet theme use `jd-post-content`; on OpenZed theme use `article.main-content` and cut before `related-posts`/navigation/comments. LazyBlock markup may be inside HTML comments; unwrap comments inside the post body before extracting `<a href>`.
- If many unrelated REC rows all point to the same P1, stop immediately: that almost always means the scraper captured `related posts`, not the actual CTA card/button.
- Canonicalize legacy/internal IP URLs found in buttons (e.g. `http://18.x.x.x/slug/` or `http://3.x.x.x/slug/`) to the current domain when the same slug exists on that site, and keep the original IP only in the button-links/audit column if needed.
- A P1 may have no WordPress tags. Record that explicitly as blank or `SEM TAGS NO WP`, not as a failed lookup.
- For Google Sheets browser fallback, an array literal formula in `A1` can populate a small test table quickly, but always validate via CSV export/readback.

## References

- `references/full-site-rec-p1-seo-audit-2026-07-09.md` — complete-site audit pattern for REC→P1 plus SEO/single articles, CTA/button link divergence reporting, and Google Sheets paste/readback details.

## Verification Checklist

- [ ] Each tab has the required REC/P1 columns in order; when doing complete-site audits, include `Tipo`, `Links nos botões`, and `Alerta links`.
- [ ] Each target site has the requested coverage: sample size or all published posts, depending on Rodolfo's scope.
- [ ] Each P1 URL was found inside the REC content, not guessed from slug similarity alone.
- [ ] Every CTA/button/card/lazyblock link in the article was checked for consistency; divergent links are reported in the sheet.
- [ ] WordPress tags for REC and P1 were resolved from tag IDs.
- [ ] Google Sheet readback confirms the data is present remotely and alert counts match local extraction.
