# FinanceADX Google Sheet publish — 2026-06-29

## Resultado

OAuth de usuário foi autorizado por Rodolfo e salvo sem imprimir tokens.

Google Sheet criado dentro de:

```text
MGS-AGENTS / Atena - Content Reference Maps
```

Arquivo:

```text
FinanceADX REC Reference Map - 2026-06-29
```

URL:

```text
https://docs.google.com/spreadsheets/d/1ujiUCCSizcQjKnUAgEa7eXzSPdGPCHaJKJrm9Pbhg1A/edit?usp=drivesdk
```

## Dados publicados

- Linhas de dados: 485
- Colunas: 17
- Fonte local: `/root/mgs-agent/data/content-reference-map/financeadx/financeadx_rec_map.csv`
- Pasta Drive: `1Ac2-b6PQKOO46tQI7kAgmg2_mdegC-OF`

## Observações técnicas

- Service account conseguia ler a pasta, mas não criar arquivo em `My Drive` por falta de quota própria.
- Solução usada: OAuth de usuário com escopo Drive.
- Upload/conversão CSV -> Google Sheet funcionou.
- Formatação via Sheets API falhou em tentativa ad-hoc (`HTTPError`), mas a planilha foi criada e preenchida corretamente.
- Nunca imprimir `client_secret`, `refresh_token` ou `access_token`.
