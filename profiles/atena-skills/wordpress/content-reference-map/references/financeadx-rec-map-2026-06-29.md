# FinanceADX REC sitemap mapping — 2026-06-29

## Pedido

Rodolfo pediu um teste de mapeamento dos RECs do domínio:

```text
https://financeadx.com/sitemap_index.xml
```

## Resultado

- Sitemaps lidos:
  - `https://financeadx.com/post-sitemap.xml`
  - `https://financeadx.com/post-sitemap2.xml`
- URLs com slug `rec-`: 485
- Classificação por título/H1:
  - REC: 484
  - P1-like: 1
- URLs abertas sem erro HTTP: 485
- Links prováveis REC → P1 extraídos: 485

## Arquivos gerados

```text
/root/mgs-agent/data/content-reference-map/financeadx/financeadx_rec_map.csv
/root/mgs-agent/data/content-reference-map/financeadx/financeadx_rec_map.json
/root/mgs-agent/data/content-reference-map/financeadx/financeadx_rec_map_summary.json
```

## Observações

- Há slugs legados fora do padrão limpo `rec-{country}-{vertical}-{produto}`, por isso aparecem países/verticais inferidos como `tarjeta/de` e `trajeta/de`.
- A extração de P1 é heurística e prioriza botões/CTAs; menus/categorias foram filtrados.
- Próxima fase recomendada: abrir cada `reference_p1_url` e extrair o CTA final/oferta externa.

## Contagem por país detectado no slug

```text
us: 251
ca: 75
za: 64
ar: 52
tarjeta: 41
mx: 1
trajeta: 1
```

## Top país/vertical

```text
us / cc: 184
ca / cc: 75
za / cc: 55
tarjeta / de: 41
us / loan: 35
ar / tarjeta: 34
us / car: 21
ar / prestamo: 10
za / loan: 9
ar / cc: 8
```
