---
name: meta-ads-intraday-operations
description: "Operação intraday Meta Ads do Ares: reativar-todas, cortes determinísticos R1-R5, carência TEST, logs e auditoria para campanhas Messenger/chatbot."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, intraday, campaigns, messenger, growth, mgs]
---

# Meta Ads Intraday Operations — Ares/MGS

Use esta skill quando Rodolfo pedir estrutura, execução, revisão ou manutenção dos crons Meta Ads intraday do Ares.

## Escopo atual do piloto

```text
Campo                         | Valor
------------------------------|------------------------------------------------------------
Operação                      | OpenzedFinanzas-CC-ES
Conta piloto                  | 1356770869843984
Canal                         | Messenger
Nível de ação                 | Campaign somente
Cortes intraday               | A cada 30 minutos via cron determinístico na VPS
Reativar-todas                | 00:30 no timezone da conta Meta via cron determinístico
Budget referência             | USD 300/dia; 20% (USD 60/dia) reservado para teste de criativos
Carência TEST                 | Nome contém TEST => não pausar/excluir por 3 dias
Log intraday                  | Só quando houver ação/erro; resumido no canal dedicado
Write                         | Desabilitado até aprovação explícita de Rodolfo
```

## Estrutura canônica

```text
/root/mgs-agent/data/ares/meta-ads/accounts/      # configs por conta
/root/mgs-agent/data/ares/meta-ads/operations/    # configs por operação país+vertical
/root/mgs-agent/data/ares/meta-ads/rules/         # rulesets R1-R5 + reativar-todas
/root/mgs-agent/data/ares/meta-ads/state/         # carência TEST, exclusões, estado local
/root/mgs-agent/data/ares/meta-ads/cache/         # cache para reduzir chamadas Meta API
/root/mgs-agent/data/ares/meta-ads/audit/         # logs auditáveis
/root/mgs-agent/data/ares/meta-ads/reports/       # relatórios
/root/mgs-agent/data/ares/meta-ads/permissions/   # permissionamento/guardrails
```

Scripts iniciais / cron:

```text
/root/mgs-agent/scripts/ares-meta-common.py
/root/mgs-agent/scripts/ares-meta-auth-check.py
/root/mgs-agent/scripts/ares-meta-intraday-runner.py
/root/mgs-agent/scripts/ares-meta-cron-runner.py                 # intraday + reativar-todas dry-run/no-write
/root/mgs-agent/scripts/ares-meta-token-expiry-alert.py          # watchdog de expiração do Token Meta API
/root/.hermes/profiles/ares/scripts/ares-meta-intraday-cron.sh   # wrapper Hermes script-only
/root/.hermes/profiles/ares/scripts/ares-meta-reactivate-all-cron.sh
/root/.hermes/profiles/ares/scripts/ares-meta-token-expiry-alert.sh
```

## Regras operacionais

1. Intraday e reativar-todas são determinísticos e devem rodar como cron/script na VPS; skill é documentação/contexto operacional, não runtime.
2. R1-R5 são slots plugáveis por operação, não hardcoded por conta; para conta/Business Manager em USD, thresholds ficam em USD.
3. Em operações Europa/GDPR, usar `MO = actions.complete_registration` e `CPMO = spend / MO` como norte intraday, porque a Meta pode não expor subscribe de forma confiável. Não usar `subs/CPS` como métrica primária dessas operações.
4. Cortes e reativações ocorrem somente em nível de campanha.
5. Campanhas com `TEST` no nome têm carência de 3 dias usando `created_time` da Meta; fallback é `first_seen_at` local; durante essa carência ficam imunes a todas as regras R1-R5.
6. COST_CAP não pausa por regra de custo (`CPS`/`CPMO`); o bid cap controla custo. Regra de custo aplica pausa só quando a condição/bid strategy permitir, especialmente LOWEST_COST.
7. Reativar-todas pode ter lista de exclusão, mas ela começa vazia e Ares deve perguntar antes de adicionar algo.
8. Teto diário de USD 300 é referência/log/base para orçamento; 20% (USD 60) fica reservado para testes de criativos novos quando houver espaço de budget.
9. Log intraday no Discord deve ser resumido e enviado só quando houver ação/erro, salvo Rodolfo mudar a política.
10. Logs dos crons Meta em `logs-aquisicao` devem usar título com `nome da conta — dia — horário no timezone da conta — tipo do cron` e tabela alinhada com estas colunas base: `ID REC`, `Nome da campanha`, `PG ID`, `Início`, métricas aplicáveis, `Ação`, `Motivo`, `Status`. `ID REC` é identificador da recomendação, não da campanha, e deve usar sequência de 3 dígitos (`REC-YYYYMMDD-HHMM-001`). `Nome da campanha` deve ser legível no mobile e pode normalizar apenas a exibição para 3 dígitos (`... - 009`) sem renomear a campanha na Meta; o nome bruto fica no audit. `Início` deve ser data real em formato `dd/mm/yyyy`, nunca idade decimal tipo `1.17d`. Não incluir colunas redundantes `Nome da página`, `Página`, `Campaign ID` ou `Meta ID` no relatório normal; IDs técnicos ficam no audit/API. Extrair `PG ID` do padrão `(pg_12345)` no nome da campanha. Em `Regra usada`/`Motivo`, intraday deve mostrar o identificador e a descrição curta (`R1 — ...`, `R2 — ...`, `R3 — ...`, `R4 — ...`, `R5 — ...`). O cron diário separado deve mostrar só `reativar-todas` — não rotular como `fora R1-R5`, porque a distinção já está no tipo do cron/título.
11. Intraday R1-R5 e HOA são camadas separadas e devem coexistir inicialmente. HOA roda como camada de gestor/tráfego nos checkpoints 08:00, 12:00, 15:00, 18:00 e 22:00 no timezone da conta, usando MO/CPMO em operações Europa/GDPR.
12. Durante a fase de calibração de 4 dias, operar em `read_only/dry_run`: Ares deve reportar a ação que tomaria, regra e motivo; Rodolfo executa/declina manualmente e corrige a lógica. Não recomendar liberar write/autonomia antes dessa calibração. Campanhas com menos de 3 dias de campanha ficam em learning/aquecimento: o intraday pode mostrar métricas e regras que teriam acionado, mas a ação sugerida deve ser informativa (`eu observaria`), sem recomendar pausa/reativação até completar a janela de learning.
13. O cron lê a conta/operação como fonte de dados, mas a gestão deve respeitar `active_scope` e estado local: campanhas pausadas por humano/saturação entram em hold/exclusão; campanhas pausadas por regra do Ares continuam monitoradas para simular reativação.
14. Para recomendações que exigem ação humana, criar/usar thread do checkpoint em `logs-aquisicao` e incluir `ID recomendação`, `Ação que eu tomaria`, `Motivo` e `Estado local`. Respostas curtas de Rodolfo (`feito`, `ignorar`, `segurar`, `pausei`, `reativei`, `não mexer nessa campanha`) devem ser registradas em state/audit e validadas por GET na próxima leitura.
14. Para recomendações que exigem ação humana, criar/usar thread do checkpoint em `logs-aquisicao` e incluir `ID recomendação`, `Ação que eu tomaria`, `Motivo` e `Estado local`. Respostas curtas de Rodolfo (`feito`, `ignorar`, `segurar`, `pausei`, `reativei`, `não mexer`) devem ser registradas em state/audit e validadas por GET na próxima leitura.
15. Para crons script-only, não confiar que o scheduler abrirá thread automaticamente. O wrapper deve postar a mensagem no Discord e deixar stdout vazio para evitar duplicidade. Para a operação Openzed/Elena atual, usar uma thread operacional fixa/diária no `logs-aquisicao` para checkpoints normais, em vez de criar uma thread por alerta; criar thread separada só para incidente técnico, anomalia grande, mudança estrutural/budget ou investigação de criativo/replacement. Referência operacional: `references/logs-aquisicao-permissions-and-cron-threads-2026-06-19.md`.
16. Para crons script-only Hermes, manter o tempo total do wrapper abaixo do timeout do scheduler (120s). Rate-limit/backoff da Meta deve ser bounded no wrapper/ambiente, e timeout local deve virar mensagem sanitizada + audit local, não erro bruto `Cronjob Response ... Script timed out`. Referência operacional: `references/hermes-script-only-timeout-and-sanitized-errors-2026-06-19.md`.
17. Quando Rodolfo der autorização explícita para uma manutenção pontual em Meta Ads (ex.: virada da conta, budget/adset/rules), tratar como `controlled_write` limitado ao escopo nomeado — não como liberação geral de autonomia. Antes de escrever: validar estado vivo, clarificar divergência de escopo/contagem, rodar dry-run, salvar audit, agendar one-shot se for na virada e validar por GET depois.
17. Mudanças de acesso ao Discord/logs-aquisicao não devem ser assumidas pelo Ares se não houver token/capacidade admin disponível. Se Ares tiver `MANAGE_ROLES`/`MANAGE_CHANNELS`, pode aplicar permission overwrites e validar por GET. Caso contrário, enviar handoff explícito ao Zeus/admin com canal, IDs e motivo; só reportar como concluído após confirmação/API bem-sucedida.

## Defaults R1-R5 atuais — OpenzedFinanzas-CC-ES / Europa / USD

```text
Regra | Condição                                                   | Ação
------|------------------------------------------------------------|--------------------
R1    | MO = 0 e spend > USD 5.00                                  | pausar campanha
R2    | MO > 0 e CPMO > USD 3.25                                   | pausar campanha
R3    | MO = 1 e spend > USD 5.00                                  | pausar campanha
R4    | LOWEST_COST + MO >= 2 + CPMO > USD 2.00 + spend >= USD 8.00| pausar campanha
R5    | campanha pausada + MO >= 2 + CPMO < USD 2.50               | reativar campanha
```

Exceções: campanha `TEST` com menos de 3 dias ativos é imune a todas as regras; `COST_CAP` não pausa por regra de custo.

## Métricas Meta atuais

```text
Métrica | Definição
--------|------------------------------------------------------------
MO      | actions.complete_registration
CPMO    | spend / MO
```

Em operações Europa/GDPR, `MO/CPMO` são a métrica primária do intraday porque a informação de subscribe pode não aparecer de forma confiável na Meta. Se `MO = 0`, `CPMO` fica nulo/não comparável.

Para operações fora da Europa onde subscribe é confiável, usar mapping separado de `subs/CPS` conforme operação específica, sem misturar com o ruleset Europa.

## Formato de log dos crons

Quando configurar ou ajustar crons Meta Ads do Ares (`intraday` e `reativar-todas`), o log operacional deve ir para o canal `logs-aquisicao` quando configurado para a operação. O formato preferido por Rodolfo é uma tabela curta, com título contendo conta, dia e horário da conta.

Durante `read_only/dry_run`, relatórios de gestão devem ser tratados como recomendações auditáveis: cada checkpoint/recomendação relevante deve ter thread própria no `logs-aquisicao` para Rodolfo responder a ação manual tomada. Depois que write/autonomia for explicitamente liberado, não abrir thread para cada ação por padrão; executar, validar e postar log consolidado.

```text
<Nome da conta> — <YYYY-MM-DD> — <HH:MM TZ> — <Tipo do cron>

ID REC                 | Nome da campanha              | PG ID    | Início     | Spend | MO | CPMO | Ação que eu tomaria | Motivo
-----------------------|-------------------------------|----------|------------|-------|----|------|---------------------|-------
REC-20260621-0124-001  | Elena Santana - ES - ESP - 009| pg_22091 | 20/06/2026 | 6.21  | 0  |      | OBSERVAR            | Learning < 3d; R1 acionou
```

Regras de formatação:
- Extrair `PG ID` do nome da campanha quando houver padrão `(pg_12345)`.
- `País/Vertical`: país do nome da campanha quando disponível + vertical da operação.
- `Regra usada`: `R1`–`R5` no intraday; `reativar-todas` no cron diário; `HOA`/razão no gestor HOA.
- `Status atual`: `effective_status` atual da campanha.
- `Ação que eu tomaria`: no dry-run, usar verbos simulados (`pausaria`, `reativaria`, `manteria`, `clonaria/substituiria`, `ignoraria`). Nunca executar write nessa fase.
- Se não houver ação candidata nem erro, o cron fica silencioso e salva apenas audit JSON local, salvo HOA configurado para `always_output_each_checkpoint`.
- Sempre declarar `dry_run_no_write` no audit enquanto controlled-write não estiver aprovado; não precisa poluir a tabela principal com essa coluna.
- Respostas curtas de Rodolfo na thread devem mapear para state/audit: `feito`, `ignorar`, `segurar 1 checkpoint`, `pausei`, `reativei`, `não mexer nessa campanha`.

## Segurança e autorização

- Nunca expor token Meta no chat.
- Token atual esperado no 1Password: item `Token Meta API`.
- Começar com leitura/dry-run; `ads_management`/write só depois de aprovação explícita.
- No piloto, só Rodolfo autoriza alteração de campanha.
- Budget/billing continuam fora de automação e exigem confirmação/double-confirm conforme política MGS.
- Antes de reportar sucesso de pausa/reativação, validar com GET na Meta API.

## Reativação de crons pausados por token/app inválido

Quando Rodolfo pedir para “arrumar” crons Meta pausados por `OAuthException code 190`, não reative às cegas. Primeiro rodar o auth check read-only da conta piloto:

```bash
python3 /root/mgs-agent/scripts/ares-meta-auth-check.py --account-id 1356770869843984
```

Só retomar crons se o check retornar `ok=true` e `http_status=200`. Ao reportar, nunca exibir token; mostrar apenas item/campo/len/status, conta, moeda e timezone. Depois de `cronjob resume`, validar com `cronjob list` que os jobs estão `enabled=true` e `state=scheduled`. Reportar via `[REPORT-INFRA]` no `#alerts-infra` porque alteração de cron é mudança persistente.

## Checklist para avanço de fase

```text
Fase | Critério
-----|-----------------------------------------------------------------
0    | Estrutura local criada e validada
1    | Token lido do 1Password sem exposição e conta lida read-only
2    | Métrica CPS mapeada nos insights Meta
3    | R1-R5 definidas por Rodolfo e rodando dry-run
4    | Canal Discord de log configurado
5    | Controlled-write aprovado explicitamente
```

## Referências

- `references/openzedfinanzas-cc-es-pilot.md` — decisões, estrutura criada, validações read-only e lições reutilizáveis do primeiro piloto Meta Messenger.
- `references/threshold-calibration.md` — método read-only de baixa carga para analisar mês da conta e sugerir thresholds R1-R5 sem pedir payload pesado da Meta API.
- `references/openzedfinanzas-cron-logging-2026-06-17.md` — detalhe da configuração dos crons intraday/reativar-todas e formato de tabela corrigido por Rodolfo para `logs-aquisicao`.
- `references/cron-log-format-logs-aquisicao.md` — formato validado por Rodolfo para logs dos crons Meta em `logs-aquisicao`: título conta/dia/horário e colunas `PG ID`, `País/Vertical`, `Regra usada`, `Status`.
- `references/meta-crons-dry-run-and-logging-2026-06-17.md` — configuração e validações dos crons dry-run/logging.
- `references/read-only-calibration-and-human-feedback-loop-2026-06-19.md` — correção operacional de Rodolfo: fase atual é calibração read-only com recomendações em thread, decisão humana, state local para pausas e write só depois de aprovação.
- `references/controlled-write-elena-bulk-and-readonly-calibration-2026-06-19.md` — ponte entre calibração read-only e controlled-write explícito: IDs de recomendação, escopo Elena/hold Patricia, desligar regras Meta de pause, normalização USD25/1 adset/3 ads e duplicação controlada para chegar a 20 campanhas.
- `references/elena-controlled-write-midnight-structure-2026-06-19.md` — padrão para controlled-write explicitamente aprovado: validar estado vivo, clarificar escopo quando contagem solicitada não bate com a conta, desativar regras Meta de PAUSE com GET, agendar one-shot na virada da conta e reportar permissões Discord via Zeus quando Ares não tiver admin token.
- `references/logs-aquisicao-threaded-cron-and-permissions.md` — padrão para postar relatórios Meta no `logs-aquisicao` abrindo thread própria via wrapper/script-only cron, evitar duplicidade de scheduler e aplicar/validar permission overwrites quando Ares tiver permissão.
- `references/hermes-script-only-timeout-and-sanitized-errors-2026-06-19.md` — padrão para impedir que crons script-only Hermes estourem o timeout de 120s do scheduler durante backoff/rate-limit Meta; wrapper deve limitar tempo total e converter falha em alerta sanitizado + audit local.

## Pitfalls

- Quando Rodolfo pedir ação no canal do Zeus, mencionar explicitamente o bot Zeus (`<@1496296175014252634>`); mensagem sem mention pode não ser lida/acionada pelo Zeus.
- Não confundir controlled-write explícito de setup com autorização geral para write/autonomia; registrar escopo exato aprovado, rodar dry-run, validar por GET e manter os crons de gestão em read-only até nova aprovação.
- Antes de executar pedidos como “deixar 20 campanhas”, validar quantas campanhas existem no escopo ativo e esclarecer se deve duplicar, reativar pausadas ou limitar ao escopo atual; não assumir.
- Não inferir CPS sem validar qual campo da Meta corresponde ao subscriber real.
- Não confundir timezone do VPS com timezone da conta; crons finais devem respeitar a conta.
- Não pausar campanha TEST dentro dos 3 dias mesmo se regra disparar.
- Não usar teto de R$1.500 como kill switch; por decisão atual ele é referência para planejamento e deve ser convertido usando USD/BRL do dia porque a conta está em USD.
- Não enviar log a cada 30 minutos se nada aconteceu.
- Não transformar guardrails em fluxo separado: eles devem ser validações dentro dos scripts que leem/executam ações na conta.
