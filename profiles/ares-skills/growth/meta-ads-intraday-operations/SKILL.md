---
name: meta-ads-intraday-operations
description: "Operação intraday e governança Meta Ads do Ares: R1-R4 v2, persistência, HOA, reativação segura, read-only/dry-run/controlled-write, logs e auditoria."
version: 2.0.4
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, intraday, campaigns, messenger, growth, mgs]
---

# Meta Ads Intraday Operations — Ares/MGS

Use esta skill quando Rodolfo pedir estrutura, execução, revisão ou manutenção dos crons Meta Ads intraday do Ares.

## Disclosure progressivo e anti-loop

1. Classifique o pedido em apenas um ramo: núcleo intraday, piloto/defaults, relatórios/Discord/HOA, recuperação auth/cron, `controlled_write` ou histórico.
2. Carregue **uma referência primária por vez**. Leia uma segunda somente quando a primeira exigir ou a evidência viva mudar o ramo.
3. Não releia este `SKILL.md` no mesmo turno, salvo mudança externa comprovada por hash.
4. Acumule correções candidatas e, quando autorizado, aplique **no máximo um patch consolidado ao final**.
5. Valide somente o hunk alterado, links, hash e paridade live/mirror. É proibido o ciclo `patch → reload completo → patch`.
6. Todo retry/backoff deve ter limite explícito de tentativas e tempo. Pare antes se houver loop ou ausência de progresso.

## Roteamento do contrato atual

- Escopo do piloto, estrutura, scripts, defaults, métricas e avanço de fase → `references/current-pilot-contract.md`
- Formato atual de relatórios, Discord e HOA → `references/current-reporting-contract.md`
- Localização de referências históricas por assunto → `references/reference-catalog.md`
- Armadilhas operacionais atuais → `references/current-operational-pitfalls.md`

Os arquivos datados no catálogo são evidência histórica. Em conflito, as regras always-on abaixo e os contratos `current-*` vencem.

## Governança Meta consolidada

Esta é a fonte procedural canônica para operação **e guardrails** Meta do Ares. A skill histórica `meta-ads-governance-guardrails` é somente um redirect de compatibilidade e não deve ser carregada como fluxo separado.

```text
Modo                Comportamento
------------------  ------------------------------------------------------------
read_only           Lê API/config e produz relatório; zero write.
dry_run             Calcula ações sem alterar a Meta.
recommend           Recomenda e aguarda a autorização aplicável.
controlled_write    Executa somente o escopo pontual e pré-aprovado.
autonomous_guarded  Futuro; exige política, limites e aprovação formal próprios.
```

- Rodolfo, Geizian, Icaro, Isliago, Joe, Kelly e Nicolas podem operar Campaign Ops e Creative Ops; Kelly também é gestora de campanhas e Geizian atua nos dois módulos.
- Autorização para operar o Ares não libera automaticamente budget, billing, token/app/permissão Meta, pixel/CAPI, credencial ou produção fora do playbook.
- Token Meta vem da fonte 1Password/config da conta e nunca é impresso. Scripts usam `ares-meta-common.py` para token, cache, lock, throttling e backoff.
- Espaçamento base entre chamadas: `ARES_META_MIN_INTERVAL_SECONDS=0.75`. Toda resposta GET/POST/batch deve alimentar o estado cross-process de `X-Business-Use-Case-Usage`; usar o máximo entre `call_count`, `total_cputime` e `total_time`.
- A partir de `80%`, aplicar soft limit antes da próxima chamada. Em `code 17/613` ou rate limit, usar `estimated_time_to_regain_access` do header em minutos; sem estimativa, usar backoff exponencial limitado. Retry fixo de 10 segundos é exclusivo para HTTP `5xx`.
- Readbacks relacionados devem usar Graph batch quando possível. Se o readback for adiado por quota, não classificar a operação como falha nem executar cleanup prematuro; persistir state tipado (`active_campaign_ids`, `deferred_target_ids`, `deferred_stage`, `async_session_ids`) e retomar por estágio.
- Somente IDs de campanhas criadas são elegíveis a cleanup. IDs de source adset/campaign e async session nunca podem ser tratados como campaign IDs.
- Async sem session ID ou ainda não terminal permanece PAUSED; não executar hierarchy readback/cleanup até estado terminal comprovado. Um outer `AresRateLimitDeferred` encerra a tentativa atual sem um segundo ciclo de backoff no runner.
- Erro de parâmetro/compliance/validação não recebe retry. Preservar no audit `error_user_title`, `error_user_msg`, `error_data` e `blame_field_specs`.
- Toda ação real salva decisão, regra, métrica, status anterior/posterior e timestamp; sucesso exige write confirmado + GET/readback do alvo completo.
- `exit code 0` de job em background não prova sucesso operacional: abrir o audit e validar campanhas, budgets, status/effective_status, start time, adsets/ads e campos críticos.
- Pausar/reativar exige `controlled_write` aplicável; budget exige autorização explícita vigente; billing exige confirmação crítica; token/permissão/app e tracking crítico não mudam sem autorização explícita.
- Referência de budget nunca vira autorização global: histórico de outra conta/moeda não substitui a configuração viva da operação atual.

## Regras operacionais

1. Intraday v2 e reativação segura 00:30 são determinísticos e devem rodar como cron/script na VPS; skill é documentação/contexto operacional, não runtime.
2. R1-R4 são slots plugáveis por operação, não hardcoded por conta; para conta/Business Manager em USD, thresholds ficam em USD.
3. Em operações Europa/GDPR, usar `MO = actions.complete_registration` e `CPMO = spend / MO` como norte intraday, porque a Meta pode não expor subscribe de forma confiável. Não usar `subs/CPS` como métrica primária dessas operações.
4. Cortes e reativações ocorrem somente em nível de campanha.
5. Campanhas com `TEST` no nome têm carência de 3 dias usando `created_time` da Meta; fallback é `first_seen_at` local; durante essa carência ficam imunes às regras R1-R4 e não acumulam persistência.
6. COST_CAP não pausa por regra de custo (`CPS`/`CPMO`); o bid cap controla custo. Regra de custo aplica pausa só quando a condição/bid strategy permitir, especialmente LOWEST_COST.
7. A reativação das 00:30 exige proveniência `paused_by_ares_rule`; a lista de exclusão e os holds continuam fail-closed e nunca são ignorados por silêncio.
8. Teto diário de USD 300 é referência/log/base para orçamento; 20% (USD 60) fica reservado para testes de criativos novos quando houver espaço de budget.
- Guardrail adicional de primeiro gasto atrasado: quando a operação o definir como padrão, toda nova campanha de produção é auto-armada depois do readback final, sem novo pedido humano. O watcher script-only consulta a cada 15 minutos. Primeiro `spend > 0` observado na data operacional entre 00:30 e 02:00 inclusive libera sem pause; fora da janela, pausa no nível campanha com readback e cria uma única reativação 00:30 com proveniência `first_delivery_guardrail`. Liberação saudável ou reativação validada encerram o watcher da campanha. A rota 00:30 aceita apenas proveniências explicitamente allowlisted e continua fail-closed para origem ausente/desconhecida.
9. Log intraday no Discord deve ser resumido e enviado quando houver ação/erro. Para OpenzedFinanzas, Rodolfo aprovou heartbeat enxuto: quando o cron roda limpo sem candidatos, o wrapper habilita `ARES_META_INTRADAY_HEARTBEAT_HOURS=3` e o runner emite no máximo 1 sinal de vida a cada 3h, usando state local em `/root/mgs-agent/data/ares/meta-ads/state/intraday-heartbeat-<op>-<account>.json`. Chamadas manuais do runner continuam silenciosas por padrão, salvo se a env var for definida explicitamente.
10. Logs dos crons Meta em `logs-aquisicao` devem usar título com `nome da conta — dia — horário no timezone da conta — tipo do cron` e tabela alinhada com estas colunas base: `ID REC`, `Nome da campanha`, `PG ID`, `Início`, métricas aplicáveis, `Ação`, `Motivo`, `Status`. `ID REC` é identificador da recomendação, não da campanha, e deve usar sequência de 3 dígitos (`REC-YYYYMMDD-HHMM-001`). `Nome da campanha` deve ser legível no mobile e pode normalizar apenas a exibição para 3 dígitos (`... - 009`) sem renomear a campanha na Meta; o nome bruto fica no audit. `Início` deve ser data real em formato `dd/mm/yyyy`, nunca idade decimal tipo `1.17d`. Não incluir colunas redundantes `Nome da página`, `Página`, `Campaign ID` ou `Meta ID` no relatório normal; IDs técnicos ficam no audit/API. Extrair `PG ID` do padrão `(pg_12345)` no nome da campanha. Em `Regra usada`/`Motivo`, intraday v2 deve mostrar o identificador e a descrição curta (`R1 — ...`, `R2 — ...`, `R3 — ...`, `R4 — ...`). O cron diário separado deve mostrar `reativar-00:30-paused_by_ares_rule`, porque não existe mais R5 nem reativação ampla.
11. Intraday R1-R4 e HOA são camadas separadas e devem coexistir inicialmente. HOA roda como camada de gestor/tráfego nos checkpoints 08:00, 12:00, 15:00, 18:00 e 22:00 no timezone da conta, usando MO/CPMO em operações Europa/GDPR. O relatório HOA deve abrir com cabeçalho humano: `HOA — relatório das HH:MM (Europe/Madrid) da página em foco`, declarar que é análise sem alteração na Meta e só depois mostrar a tabela. Deve listar todas as campanhas da página em foco (`management_scope.active_focus`) — ativas, pausadas e histórico visível por insights — não só watchlist, ordenadas pela numeração da campanha (`001`, `002`, `003`... até a última). Quando a página deixar de rodar, atualizar `active_focus`; o HOA passa a reportar a próxima página em foco.
12. Durante a fase de calibração de 4 dias, operar em `read_only/dry_run`: Ares deve reportar a ação que tomaria, regra e motivo; Rodolfo executa/declina manualmente e corrige a lógica. Não recomendar liberar write/autonomia antes dessa calibração. Campanhas com menos de 3 dias de campanha ficam em learning/aquecimento: o intraday pode mostrar métricas e regras que teriam acionado, mas a ação sugerida deve ser informativa (`eu observaria`), sem recomendar pausa/reativação até completar a janela de learning.
13. O cron lê a conta/operação como fonte de dados, mas a gestão deve respeitar `active_scope` e estado local: campanhas pausadas por humano/saturação entram em hold/exclusão; campanhas pausadas por regra do Ares continuam monitoradas para simular reativação.
14. Para recomendações que exigem ação humana, criar/usar thread do checkpoint em `logs-aquisicao` e incluir `ID recomendação`, `Ação que eu tomaria`, `Motivo` e `Estado local`. Respostas curtas de Rodolfo (`feito`, `ignorar`, `segurar`, `pausei`, `reativei`, `não mexer nessa campanha`) devem ser registradas em state/audit e validadas por GET na próxima leitura.
15. Para crons script-only, não confiar que o scheduler abrirá thread automaticamente. O wrapper deve postar a mensagem no Discord e deixar stdout vazio para evitar duplicidade. Para a operação Openzed/Elena atual, usar threads operacionais fixas/diárias no `logs-aquisicao`, separando fluxos por cadência: intraday em uma thread própria de alta frequência e HOA em outra thread própria de gestor. Criar thread separada adicional só para incidente técnico, anomalia grande, mudança estrutural/budget ou investigação de criativo/replacement. Referências operacionais: `references/logs-aquisicao-permissions-and-cron-threads-2026-06-19.md` e `references/hoa-thread-routing-historical-reports-and-mobile-layout-2026-06-22.md`.
16. Para crons script-only Hermes, manter o tempo total do wrapper abaixo do timeout do scheduler (120s). Rate-limit/backoff da Meta deve ser bounded no wrapper/ambiente, e timeout local deve virar mensagem sanitizada + audit local, não erro bruto `Cronjob Response ... Script timed out`. Referência operacional: `references/hermes-script-only-timeout-and-sanitized-errors-2026-06-19.md`.
17. Quando Rodolfo der autorização explícita para uma manutenção pontual em Meta Ads (ex.: virada da conta, budget/adset/rules), tratar como `controlled_write` limitado ao escopo nomeado — não como liberação geral de autonomia. Antes de escrever: validar estado vivo, clarificar divergência de escopo/contagem, rodar dry-run, salvar audit, agendar one-shot se for na virada e validar por GET depois.
17. Mudanças de acesso ao Discord/logs-aquisicao não devem ser assumidas pelo Ares se não houver token/capacidade admin disponível. Se Ares tiver `MANAGE_ROLES`/`MANAGE_CHANNELS`, pode aplicar permission overwrites e validar por GET. Caso contrário, enviar handoff explícito ao Zeus/admin com canal, IDs e motivo; só reportar como concluído após confirmação/API bem-sucedida.


## Relatórios e Discord

Carregue `references/current-reporting-contract.md` somente para formato de log, threads, recomendações humanas ou HOA.

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


## Referências e pitfalls sob demanda

- Catálogo histórico: `references/reference-catalog.md`
- Pitfalls atuais: `references/current-operational-pitfalls.md`
