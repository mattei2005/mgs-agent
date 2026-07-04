# Sitemap reference map — Rodolfo site list (2026-07-02)

## Run

- Script: `/root/mgs-agent/scripts/map_content_references.py`
- Query helper: `/root/mgs-agent/scripts/query_content_references.py`
- Run ID: `20260702T050342Z`
- DB: `/root/mgs-agent/data/content-reference-map/content_reference_map.sqlite`
- CSV URLs: `/root/mgs-agent/data/content-reference-map/run-20260702T050342Z/content-reference-urls.csv`
- CSV summary: `/root/mgs-agent/data/content-reference-map/run-20260702T050342Z/content-reference-summary.csv`

## Result

- Input domains/labels: 56
- Domains with URLs: 52
- Sitemap URLs inserted/upserted in DB: 35,352 unique URLs
- Likely article URLs: 26,503
- REC URLs detected by slug: 4,317
- Rows with title or H1 fetched in this run: 3,732

All sitemap URLs were stored. Title/H1/P1 heuristic fetch was capped with `MAX_PAGE_FETCH_PER_DOMAIN=80` for runtime safety; rerun with a higher cap if deeper title extraction is needed for a specific domain.

## Domains with no usable URL rows

- `autocreditadx.com` — `/sitemap_index.xml` returned 404.
- `dicasfinancas.com` — guessed from label `DicasFinancas`; `/sitemap_index.xml` returned 404.
- `emploio.seuprimeiroempregoam.com` — DNS/name resolution failed; likely typo for `emprego` or another subdomain.
- `fincgriffin.com` — sitemap index returned 200, but no URL rows were parsed.

## Guessed domains from brand-only labels

The following labels had no dot/TLD in Rodolfo's list, so the mapper tried lowercase `.com` and marked `guessed_domain=1`:

- `Cephyric` -> `cephyric.com`
- `DicasFinancas` -> `dicasfinancas.com`
- `Escalatepower` -> `escalatepower.com`
- `Growpowerhub` -> `growpowerhub.com`
- `Jobscana` -> `jobscana.com`
- `Mavroa` -> `mavroa.com`
- `Yolokfx` -> `yolokfx.com`
- `Zyclor` -> `zyclor.com`
- `Boostingecon` -> `boostingecon.com`

## Query example validated

```bash
python3 /root/mgs-agent/scripts/query_content_references.py 'wells fargo' --limit 8
```

Returned Wells Fargo references including:

- `https://cliquet.com/rec-us-cc-wells-fargo-active-cash/`
- `https://cliquet.com/rec-us-cc-wells-fargo-autograph/`
- `https://cliquet.com/rec-us-cc-wells-fargo-reflect/`
- `https://conectageral.com/rec-us-cc-wells-fargo-active-cash/`
- `https://carcreditad.com/rec-us-car-wells-fargo-auto-loan/`

## Operational note

When Rodolfo asks for a new article and does not provide a specific reference URL, query this SQLite map by card/product + vertical/country and pick the best ready-article reference before writing. If a reference URL is supplied, use it directly and only use this DB for backup/comparison.
