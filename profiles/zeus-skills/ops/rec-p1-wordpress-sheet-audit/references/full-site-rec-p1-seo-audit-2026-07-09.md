# Full-site REC/P1/SEO audit pattern — 2026-07-09

## Scenario

Rodolfo asked for a complete Google Sheet audit across four WordPress sites:

- `cliquet.com`
- `finanzas.cliquet.com`
- `openzed.com`
- `finanzas.openzed.com`

The output needed to include every published article, not only known REC posts. Articles that link to another same-site article are treated as REC→P1 flows. Articles without that internal flow are SEO/single articles and should show the final CTA/button link.

## Sheet columns used

```text
Data REC | Artigo REC | Tags REC | Data P1 | Artigo P1 / Link Final | Tags P1 | Tipo | Links nos botões | Alerta links
```

`Tipo` values used:

- `REC→P1` — source article links to another same-site article.
- `SEO / artigo único` — no REC→P1 flow; keep article URL in REC columns and final CTA/button URL in `Artigo P1 / Link Final`.
- `P1 sem REC listado` — article is a destination of a flow but the REC source was not clearly represented in the paired row.

## Link-audit rule

For every article, extract all CTA/button/card/lazyblock links from `content.rendered`, not just the first link. CTA detection should consider:

- anchor `href`
- anchor text
- anchor class/attributes
- nearby ancestor class/context containing button/card/lazyblock markers

If multiple distinct CTA/button URLs exist, write all of them in `Links nos botões` separated by ` | ` and set `Alerta links` to `LINKS DIFERENTES NOS BOTÕES`. This is not noise: it catches redator/gestor mistakes where one card/button points to the wrong URL.

## WordPress REST collection

1. Page through `/wp-json/wp/v2/posts?status=publish&per_page=100&page=N&_fields=id,date,link,slug,title,tags,content`.
2. Build a map from normalized post URL → post object.
3. Extract CTA/button links per post.
4. If a CTA URL maps to another post on the same site, classify the source as `REC→P1` and use the destination as P1.
5. Resolve tags through `/wp-json/wp/v2/tags?include=<ids>&per_page=100&_fields=id,name`.
6. Use `SEM TAGS NO WP` when the post has no tag IDs; do not treat it as a lookup failure.

## Google Sheets write/readback pattern used

For this session, the reliable write path was a local Playwright script using the Sheets UI and synthetic paste:

```js
const dt = new DataTransfer();
dt.setData('text/plain', tsv);
const ev = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
document.querySelector('textarea.trix-offscreen').dispatchEvent(ev);
```

This avoided hand-typing long array formulas and preserved tabular TSV structure. After writing each tab, verify by CSV export/readback.

Important readback pitfall: Google CSV export can return UTF-8 bytes while `requests` guesses `ISO-8859-1`. Decode with `r.content.decode('utf-8')` before parsing, otherwise accents in values like `botões` may look corrupted and alert counts may appear wrong.

## Completion criteria

- Every published post ID is represented either directly as an article row or as the P1 destination in a paired REC→P1 row.
- CSV export shows expected row count and the expected header.
- `Alerta links` count in the Sheet matches the local extraction summary.
- No tab is left with scratch/test data or formula parse errors.
