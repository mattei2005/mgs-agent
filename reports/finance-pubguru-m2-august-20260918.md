# PubGuru/M2 — reconciliação Wantabrand · agosto/2026

Autoridade: Rodolfo `1550520908517478583`, período `1550520995335503945`, regra de campanha `1550521965805043746`.  
Execução: leitura autenticada, sem qualquer alteração no PubGuru ou na dashboard financeira.

## Regra aplicada

- `utm_campaign` normalizada iniciando com `b01` → tráfego direto.
- Qualquer outro valor, inclusive `/empty/` → BOT/ChatPion.
- Domínios auditados separadamente: `wantabrand.com` e `finance.wantabrand.com`.

## Método

- Profit Attribution aceita no máximo três dias.
- Agosto foi dividido em 11 janelas contíguas e sem sobreposição por domínio.
- Foram obtidos 22 registros únicos após deduplicação por domínio + início + fim.
- Analytics Report foi lido para 01–31/08, `Revenue Source = NETWORK`, em USD, por domínio.
- Dashboard financeira foi relida diretamente no workspace de agosto, cutoff 31/08.

## Profit Attribution

### wantabrand.com

- Direto: **US$ 519,89**
  - `b01fb01c01`: US$ 519,89
- BOT/ChatPion: **US$ 4.621,03**
  - `pg-22104`: US$ 2.945,78
  - `pg-22103`: US$ 919,80
  - `pg-22302`: US$ 669,86
  - `/empty/`: US$ 64,97
  - demais campanhas: US$ 20,62
- Total: **US$ 5.140,92**

### finance.wantabrand.com

- Direto: **US$ 0,00**
- BOT/ChatPion: **US$ 7,83**
  - `pg-19326`: US$ 7,83
- Total: **US$ 7,83**

### Consolidado Profit Attribution

- Direto: **US$ 519,89** — 10,10%
- BOT/ChatPion: **US$ 4.628,86** — 89,90%
- Total: **US$ 5.148,75**

## Analytics Report — NETWORK gross

- `wantabrand.com`: **US$ 4.604,04**
- `finance.wantabrand.com`: **US$ 7,83**
- Total: **US$ 4.611,87**

## Dashboard financeira — M2 gross

- `wantabrand.com`: **US$ 5.150,28**
- `finance.wantabrand.com`: **US$ 7,40**
- Total: **US$ 5.157,68**

## Reconciliacão

- Profit Attribution − Analytics: **+US$ 536,88**.
- Dashboard − Profit Attribution: **+US$ 8,93**.
- Dashboard − Analytics: **+US$ 545,81**.
- A divergência Profit Attribution × Analytics está integralmente em `wantabrand.com`; o subdomínio fecha a frações de centavo.
- No domínio principal, a diferença está concentrada em 01–06 e 13–21/08. As demais janelas de até três dias fecham com o Analytics dentro de arredondamento.

## Conclusão

A separação Direto/BOT é reproduzível pela regra aprovada, mas os dois relatórios internos do PubGuru não fecham entre si para `wantabrand.com`. Portanto, não existe base segura para alterar agosto na dashboard até a origem da diferença de US$ 536,88 ser identificada pelo PubGuru/MonetizeMore ou por uma fonte adicional aprovada. Nenhuma escrita foi realizada.
