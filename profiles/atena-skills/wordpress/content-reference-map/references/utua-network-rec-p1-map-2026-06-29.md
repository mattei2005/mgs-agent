# UTUA network sitemap mapping — 2026-06-29

## Pedido

Rodolfo listou 19 domínios UTUA adicionais para mapear por sitemap:

```text
utua.fr, utua.de, utua.es, utua.it, utua.uk, utua.at, utua.pl, utua.gr, utua.fi, utua.lv, utua.us, utua.ar, utua.co, utua.pe, utua.id, utua.ph, utua.in, utua.pk, utua.ae
```

## Regra operacional

Para a rede UTUA, usar a mesma correção identificada no `utua.com.br`:

```text
*-p1 = REC de referência
*-p2 = P1 de referência
```

Ou seja:

```text
UTUA_P1 -> REC
UTUA_P2 -> P1
```

## Resultado agregado

```text
Domínios solicitados: 19
Post URLs lidas: 3.647
Artigos fonte P1/P2: 3.639
REC rows corrigidas: 1.871
REC com P1 pareada: 1.763
REC sem P1 pareada: 108
P2 órfãs sem REC correspondente: 5
```

## Resultado por domínio

```text
utua.fr  post URLs 178   REC 89   pareados 87   REC-only 2
utua.de  post URLs 321   REC 163  pareados 158  REC-only 5
utua.es  post URLs 366   REC 185  pareados 180  REC-only 5
utua.it  post URLs 204   REC 107  pareados 97   REC-only 10
utua.uk  post URLs 159   REC 80   pareados 78   REC-only 2
utua.at  post URLs 2     REC 2    pareados 0    REC-only 2
utua.pl  post URLs 243   REC 147  pareados 94   REC-only 53
utua.gr  post URLs 14    REC 7    pareados 7    REC-only 0
utua.fi  post URLs 0     REC 0    erro: sitemap 404
utua.lv  post URLs 1347  REC 675  pareados 668  REC-only 7
utua.us  post URLs 0     REC 0    sitemap retorna HTML/lander, sem XML de sitemap
utua.ar  post URLs 108   REC 54   pareados 54   REC-only 0
utua.co  post URLs 60    REC 30   pareados 30   REC-only 0
utua.pe  post URLs 112   REC 56   pareados 56   REC-only 0
utua.id  post URLs 214   REC 112  pareados 102  REC-only 10
utua.ph  post URLs 0     REC 0    erro SSL/remote disconnected
utua.in  post URLs 16    REC 11   pareados 5    REC-only 6
utua.pk  post URLs 73    REC 38   pareados 35   REC-only 3
utua.ae  post URLs 230   REC 115  pareados 112  REC-only 3
```

## Google Sheet

Planilha criada na pasta `MGS-AGENTS/Atena - Content Reference Maps`:

```text
https://docs.google.com/spreadsheets/d/1gfLVgIgFU4q8y_wkjSZPwJqO6ZG-zlYyWpf1jO9KZ-I/edit
```

Abas criadas:

```text
summary
all_rec_p1
fr, de, es, it, uk, at, pl, gr, fi, lv, us, ar, co, pe, id, ph, in, pk, ae
```

## Arquivos locais

Agregado:

```text
/root/mgs-agent/data/content-reference-map/utua-network/utua_network_rec_p1_map.csv
/root/mgs-agent/data/content-reference-map/utua-network/utua_network_rec_p1_map.json
/root/mgs-agent/data/content-reference-map/utua-network/utua_network_rec_p1_map.xlsx
/root/mgs-agent/data/content-reference-map/utua-network/utua_network_rec_p1_map_summary.json
```

Também há subpastas por domínio em:

```text
/root/mgs-agent/data/content-reference-map/utua-network/<dominio>/
```

## Observações

- `utua.fi`: `https://utua.fi/sitemap_index.xml` retornou 404.
- `utua.ph`: HTTPS falhou por certificado e, com contexto sem verificação/HTTP, o servidor encerrou a conexão sem resposta.
- `utua.us`: `https://utua.us/sitemap_index.xml` respondeu HTML com redirecionamento para `/lander`, não XML de sitemap.
- O XLSX foi gerado em OOXML mínimo porque `openpyxl` não está instalado no ambiente global; CSV/JSON e Google Sheet são as fontes principais para leitura operacional.
