# SB Messenger Page Broadcast Times — bulk update pattern

Sessão: 2026-07-01. Use quando Rodolfo pedir para mapear, converter ou alterar horários de envio de broadcast na Smart Bidding.

## Conceito crítico

Na SB, os horários da aba `Accounts > Messenger > Page > Broadcast` ficam no registro da **Page**, campo `BROADCAST_TIME`, não no Broadcast Template em si.

A dash salva/exibe horário em `America/Sao_Paulo` (Brasil). Para entender o horário real no país do template/page, converter de Brasil para o timezone local do país.

Exemplo validado:

```text
SB/Brasil 01:00 em julho/2026 -> Espanha/Madrid 06:00 CEST
SB/Brasil 07:00 em Argentina -> Argentina 07:00
```

## Escopo correto MGS

Para Messenger Page na operação atual, o escopo correto é:

```text
Digital trust      45 sites
Digital trust 2    11 sites
Total              56 sites
Páginas            3.237
```

Pitfall real: capturar a API antes de selecionar/atualizar `Digital trust 2` retorna apenas `2.443` páginas / `45 sites`. Isso é incompleto.

## Fluxo UI validado

1. Abrir `https://app.smartbiddingdigital.com/accounts` com Playwright headed/Xvfb.
2. Selecionar fonte/contexto `Messenger`.
3. Abrir aba `Page`.
4. Abrir seletor de sites.
5. Garantir todos os sites de `Digital trust` e `Digital trust 2` selecionados.
6. Confirmar label `56 sites`.
7. Clicar no botão azul de refresh/update ao lado do seletor.
8. Validar paginação/response com `3.237` páginas.
9. Só então mapear ou alterar horários.

## API observada

A tabela usa:

```text
GET /campaigns/Messenger?companies[]=...&source=Messenger
PUT /campaigns/Messenger/update-many
GET /campaigns/Messenger/{ID}
```

Campos relevantes retornados:

```text
ID
PAGE_ID
PAGE_NAME
COUNTRY
VERTICAL
STATUS
BROADCAST_TEMPLATE_ID
BROADCAST_TEMPLATE_NAME
BROADCAST_TIME
BROADCAST_CURRENT_MESSAGE_ID
BROADCAST_MESSAGE_ID
BROADCAST_LAST_SCHEDULE
RESTRICTED_UNTIL
```

## Bulk update por template/page

Procedimento seguro:

1. Capturar a base completa com `56 sites` e `3.237 páginas`.
2. Filtrar pelo `BROADCAST_TEMPLATE_NAME` exato.
3. Conferir quantidade de páginas e horários atuais.
4. Salvar backup JSON dos rows completos antes da alteração em:

```text
/root/mgs-agent/backups/sb-page-schedules/
```

5. Enviar `PUT /campaigns/Messenger/update-many` com payload:

```json
{
  "BROADCAST_TIME": ["07:00", "09:00", "11:00", "13:00", "15:00", "18:00", "20:00", "23:00"],
  "ids": ["PAGE_ROW_ID_1", "PAGE_ROW_ID_2"]
}
```

6. Validar por `GET /campaigns/Messenger/{ID}` para cada ID.
7. Recapturar a tabela com `56 sites` + refresh e validar:
   - target row count bate;
   - `BROADCAST_TIME` bate exatamente;
   - `rows_with_new_pattern` só contém o template alvo quando for teste isolado;
   - nenhum outro template mudou.

## Teste validado

Template alterado em produção com aprovação do Rodolfo:

```text
Financeadx - AR-CC-ES/ES-ZW-SR - g006-d Nicolas
Antes:  09,11,14,18,20
Depois: 07,09,11,13,15,18,20,23
Escopo: 2 páginas
Pages:  Teresa Camacho (19337), Leticia Anzaldo (5439)
Validação: all_target_times_ok=true; rows_with_new_pattern=2; outros templates=0
```

Backup criado:

```text
/root/mgs-agent/backups/sb-page-schedules/financeadx-ar-g006-before-times-20260701-001052.json
```

## Sheet de análise de timezone

Quando Rodolfo pedir tabela visual, escrever na planilha operacional:

```text
Sheet ID: 1ieSjYbhl34T0tWOvvol3F2lhvCoVTWHm9_YnUkoVhtM
Aba: SB Horários Local
```

Conteúdo recomendado:

- título e metadata;
- escopo `Digital trust + Digital trust 2 / 56 sites / 3.237 páginas`;
- referência de conversão `America/Sao_Paulo` -> país local;
- resumo por padrão de horário;
- detalhe por template;
- readback via Sheets API.

## Conversão de timezone

Use `zoneinfo` em Python. Base:

```python
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
base = ZoneInfo('America/Sao_Paulo')
local = ZoneInfo('Europe/Paris')
dt = datetime.combine(date(2026, 7, 1), time(1, 0), base).astimezone(local)
```

Mapa canônico de Rodolfo para converter horários locais desejados para SB/Brasil:

```text
US -> America/New_York
CA -> America/Toronto
MX -> America/Mexico_City
AR -> America/Sao_Paulo + America/Santiago
DE -> Europe/Berlin
ES -> Europe/Paris + Europe/Rome
GB -> Europe/London
ZA -> Africa/Johannesburg
FR -> Europe/Paris
```

Para updates por template, derive o país do `BROADCAST_TEMPLATE_NAME` / vertical antes de usar `COUNTRY` da Page row. Exemplo: uma Page row pode estar com `COUNTRY=US`, mas usar template `DE-CC-DE`; o horário correto é o do template/vertical (`Europe/Berlin`), não US Eastern.

## Pitfalls

- Não confiar em `45 sites`: está incompleto.
- Não capturar a primeira response de `/campaigns/Messenger` antes do refresh como base final.
- Não alterar sem backup JSON dos rows completos.
- Não assumir que template name = país real; validar `COUNTRY` dos rows.
- Argentina atualmente não exige conversão prática: Brasil = Argentina no horário observado.
- Europa muda com DST; sempre declarar a data de referência da conversão.
- Não expor cookies, bearer tokens ou storage state em logs/chat.
