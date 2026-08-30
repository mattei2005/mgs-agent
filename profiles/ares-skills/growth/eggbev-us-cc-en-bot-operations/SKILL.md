---
name: eggbev-us-cc-en-bot-operations
description: "Use em Campaign Ops BOT/Messenger da Eggbev US-CC-EN."
version: 0.18.0-draft
author: Ares
license: internal
metadata:
  hermes:
    tags: [eggbev, usa, credit-cards, english, meta-ads, messenger, bot, campaign-ops]
---

# Eggbev US-CC-EN BOT Operations

Skill específica da operação Meta Ads Eggbev USA, vertical Credit Cards, idioma inglês, estratégia BOT/Messenger.

## When to Use

Use quando Rodolfo ou Nicolas pedir revisão de regras, análise, relatório, campanha, criativo, cron ou mudança Meta Ads da operação Eggbev US-CC-EN BOT. Não usar para tráfego direto nem para configurar internamente ChatPion/DigitalTrChat sem escopo explícito.

## Estado atual

```text
Status do contrato       Corte/reativação e postagem ROAS autorizados em modo fail-closed; budget write segue gated
Operation ID             Eggbev-US-CC-EN-BOT
Conta Meta               act_1034081997659047; alias Eggbev-US-CC-EN-01-G006
Gestão                    Rodolfo Mattei + Nicolas
Write Meta                status de ad/campanha no ciclo ROAS habilitado; budget write bloqueado; guardrail de leads habilitado
Crons Eggbev              Corte/ROAS e guardrail de leads ativos; tick LEADS 20:00 ET confirmado. Flag cron gateway_running=false é falso negativo do observador; execução real vence.
Regra nativa              ADS ZERO RESULTS está DISABLED por readback; ADS ON 1.1 ausente
Herança tráfego direto    proibida sem revisão explícita
Herança operação anterior proibida
```

O estado vivo está nos arquivos canônicos de operação e conta em `data/ares/meta-ads/`. IDs técnicos completos e referência de credencial ficam nesses arquivos/audits, nunca no relatório humano.

## Threads fixas

```text
Tipo              Thread ID
----------------  -------------------
Regras             1543280854024060999
Intraday           1541578606076231750
Diário             1541578596253175858
Criar campanhas    1541578556037927053
Clonar campanhas   1543333373945053184
Limite de Leads    1543312825890381865
```

Nunca criar uma thread substituta quando uma dessas rotas se aplicar. Toda thread nova do canal deve incluir Zeus e Nicolas conforme a política Discord vigente. A identidade das seis rotas vive em `thread_id + prompt_file + registry`; não publicar nem recriar mensagens operacionais de banner/pin em cada thread.

Por instrução explícita de Nicolas em 29/08/2026, a rota canônica de **Regras** passou a ser a thread atual `1543280854024060999`. A antiga `Eggbev-US-CC-EN Regras` (`1541578622106865815`) fica supersedida e não recebe novas regras ativas.

### Roteamento obrigatório — Criar Campanhas

Na thread `1541578556037927053`, pedidos genéricos como “sua configuração”, “como está configurada” ou “relatório da configuração” significam **a configuração operacional da criação Eggbev**, não a configuração global de Hermes/Ares. Só mostrar modelo, provider, OAuth, ferramentas ou flags globais quando o usuário disser explicitamente que quer a configuração global.

Antes de responder naquela thread:

1. ler o contrato e a conta canônicos;
2. executar `python3 scripts/ares-eggbev-creation-config-report.py --check` ou usar exatamente os mesmos campos;
3. separar criação do zero dos três modos de clone;
4. informar readiness real e bloqueios, sem tratar contrato aprovado como runner pronto;
5. não misturar ROAS, Diário ou Limite de Leads na configuração de criação, salvo nota curta de pós-lançamento.

A correção de 29/08/2026 supersede o relatório que respondeu com configuração global do agente na rota de criação. O prompt exato da thread vive em `data/ares/discord/thread-prompts/1541578556037927053.txt` e em `discord.channel_prompts.1541578556037927053`.

### Roteamento obrigatório — Diário

Na thread `1541578596253175858`, pedidos como “suas regras”, “suas automações”, “como está configurado” ou “mostre tudo” significam **somente a configuração do Diário**: horários, períodos, fontes, métricas, runtime, limitações e modo read-only. Não responder com toda a operação Eggbev, configuração global do agente, criação, clones, cortes ROAS, limite de leads ou inventário de Automated Rules.

- Configuração da rota: `python3 scripts/ares-eggbev-daily-config-report.py --check`.
- Relatório vivo hoje/agora: `python3 scripts/ares-eggbev-daily-report.py --period today`.
- Ontem: `--period yesterday`; data específica: `--period YYYY-MM-DD`.
- Nunca reutilizar números de mensagens antigas como estado atual.
- Horários aprovados: 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 e 22:00 em `America/New_York`; aprovação do plano não significa cron aprovado.
- Renderer v3: inclui toda campanha efetivamente `ACTIVE` mesmo sem insight e toda campanha com insight no período; histórico sem nenhuma dessas condições fica fora.
- Não há limite silencioso de linhas nem truncamento do nome. Cards verticais mostram o nome integral e todos os campos; a tabela desktop única preserva todas as campanhas com paginação Discord fence-safe.
- A tabela única combina Meta Ads + Smart Bidding + Pricing/monetização por campanha. O join exige `utm_campaign` do creative Meta = `UTM_CAMPAIGN` Smart Bidding e `object_story_spec.page_id` Meta = `FB_PAGE_ID` Smart Bidding.
- Campos Meta por campanha: status, `start_time` ET, Budget, spend, `messaging_conversation_started_7d`, custo por mensagem iniciada, Purchase ROAS, CPM e CTR.
- Campos Smart Bidding/Pricing por campanha: investimento, receita, LEADS, `AVG_PRICE`, RPS, CPM, EPC e ROI quando expostos pela rota direta compatível. Fórmula local é apenas fallback rotulado.
- Freshness Smart Bidding aparece com timestamp/idade/campo ou `N/D`; sem timestamp ou acima de 2h, todas as métricas externas por campanha permanecem `N/D`, nunca zero.
- UTM ausente/múltipla, página ausente/duplicada, Page ID divergente ou fonte stale falha fechado e expõe o motivo no campo `Join`.
- As métricas de Pricing/monetização podem ser extraídas diretamente da Smart Bidding pela rota compatível de **vertical, Messenger Pages ou domain**. Selecionar pela granularidade da métrica e exigir mapping explícito de operação/UTM/página/domain, mesmo período, moeda e freshness.
- RPS, CPM, EPC, `AVG_PRICE`, receita, ROI e demais campos devem preferir o valor direto da Smart Bidding. Cálculo local de RPS/EPC é apenas fallback explícito e rotulado quando a rota selecionada não expuser o campo direto.
- O payload global `/pricing` não é a única fonte e sua ausência de UTM não significa indisponibilidade da métrica; consultar vertical, Messenger Pages ou domain antes de concluir `N/D`.
- ROI real e ROI estimado do **Corte e ROAS** podem ser exibidos como cálculos locais explicitamente rotulados e somente informativos após join econômico exato: `ROI real* = (NET_REVENUE−INVESTIMENT) / INVESTIMENT`; `ROI est.* = (estimatedRevenue−INVESTIMENT) / INVESTIMENT`. O denominador zero/ausente ou estimate ambíguo permanece `N/D`.
- RPS* e CPM bloco* do **Corte e ROAS** usam, respectivamente, `NET_REVENUE×1.000/SESSIONS` e `NET_REVENUE×1.000/GAM_IMPRESSIONS`, sempre rotulados como cálculo report-only. Esses campos não alteram corte, reativação ou budget; Meta Purchase ROAS continua sendo a métrica de decisão.
- A rota econômica materializada é `/report/performance_per_campaigns`, filtrada por `CUSTOMER_ID + DOMAIN + DATE + CAMPAIGN_ID + UTM_ADGROUP`, com estimativa em `/estimated/revenue/utm_adgroup` e freshness em `/estimated/delay` (`currentFillTime` presente e `totalMinutes <= 120`). O join da estimativa falha fechado quando a UTM não é única na conta-alvo.
- Runtime: runner read-only construído; sob demanda disponível; post automático, cron e writes desabilitados.

O relatório histórico que misturou todas as regras/automação da operação dentro do Diário foi supersedido em 29/08/2026. O prompt exato vive em `data/ares/discord/thread-prompts/1541578596253175858.txt` e em `discord.channel_prompts.1541578596253175858`.

### Roteamento obrigatório — Limite de Leads

Na thread `1543312825890381865`, pedidos como “sua configuração”, “como está configurado”, “mostre tudo” ou “relatório” significam **somente a rota de limite de LEADS por página**: fonte, métrica, threshold, reconciliação, freshness, horários, runtime, alertas, readbacks e limitações. Nunca responder com configuração global do Hermes/Ares ou misturar ROAS, criação, clones, Diário e Intraday.

- Prompt canônico: `data/ares/discord/thread-prompts/1543312825890381865.txt` e `discord.channel_prompts.1543312825890381865`.
- A configuração está persistida; a ativação em novas sessões depende do próximo restart seguro do gateway. Nunca reiniciar o gateway dentro da sessão ativa.
- Smart Bidding exige timestamp verificável com idade máxima de 2h. Ausente, inválido, futuro ou stale bloqueia somente o item afetado e gera alerta; `BROADCAST_TIME` e `DATE_START` não provam atualização.
- O wrapper automático usa `--scheduled` e aceita apenas 08:00/20:00 `America/New_York`; execução manual autorizada é separada.
- Mapping/freshness inválidos geram mensagem na thread; toda postagem exige GET/readback exato. Falha primária tenta uma vez a thread Regras `1543280854024060999`; falha total termina o run com erro.
- O tick agendado de 20:00 ET em 29/08/2026 foi confirmado `ok`. A flag `gateway_running=false` do cron tool é falso negativo do observador e não prevalece sobre o histórico real de execução.

## Escopo Ares

Ares gerencia a camada de aquisição e Campaign Ops ao redor do BOT:

- arquitetura de campanha Meta;
- contas, campanhas, adsets, ads e criativos;
- naming, inventário e reconciliação Drive × Meta;
- relatórios Intraday e Diário;
- recomendações, guardrails, custo, performance e ROI quando as fontes forem definidas;
- crons determinísticos somente após contrato e aprovação.

Configuração interna de ChatPion, DigitalTrChat, quiz, SMS Funnel, WordPress ou pixel/CAPI crítico não entra automaticamente neste escopo. Qualquer uma dessas camadas exige pedido explícito de Rodolfo e a rota técnica correspondente.

## Separação obrigatória de tráfego direto

Não copiar automaticamente para BOT/Messenger:

- objetivo e optimization goal;
- destination/conversion location;
- estrutura CBO/ABO;
- bid strategy e cost cap;
- público, placements e attribution;
- evento de conversão;
- fórmula de resultado/custo;
- thresholds de pausa/reativação;
- horários Intraday/Diário;
- regras de criação, ativação, replacement e escala;
- naming e UTMs.

Somente guardrails genéricos de segurança, idempotência, autorização e readback podem ser compartilhados após revisão de compatibilidade.

## Pendências residuais antes do canário

O contrato de estrutura, horários, threshold, guardrail, publicação e reporting já foi consolidado nas seções seguintes. Permanecem pendentes somente as camadas dependentes de evidência ou decisão ainda ausente:

1. Smart Bidding: no Corte e ROAS, a rota econômica read-only foi materializada com match exato `CUSTOMER_ID + DOMAIN + DATE + CAMPAIGN_ID + UTM_ADGROUP`, estimativa por UTM única e freshness `/estimated/delay`. Permanece pendente o timestamp verificável da rota Messenger para LEADS e a seleção multi-rota específica do Diário.
2. Engine v3: conta Eggbev cadastrada na release 3.4.0; `from_zero_prestaged`, `pure_clone`, `clone_prestaged` de 1–5 ads e `clone_page_switch` passam schema/prevalidation/plan. Mídia nova continua pre-stageada sob demanda antes de selar o manifest.
3. Criação do zero: runner `scripts/ares-eggbev-creation.py`, policy por modo, naming, copy, tracking, Messenger JSON, placements e pós-processamento estão materializados. Os quatro payloads diretos campaign/adset/adcreative/ad passaram Meta `validate_only` com GET antes/depois e zero objeto criado. Reconciliação read-only encontrou 63 linhagens aptas à liberação scoped; nenhuma foi reservada ou pre-stageada antes do pedido real. O call mínimo exige somente budget; nomes dos ads são automáticos. OK final de Nicolas e autoridade financeira Rodolfo/Geizian continuam gates distintos do execute.
4. `clone_page_switch`: schema, planner, prevalidation e recovery implementados; antes do primeiro write real, validar em canário aprovado os campos exatos do JSON Messenger, Page/UTM, delivery e readbacks Meta.
5. ROAS: comando aprovado de alteração intraday e eventual fórmula de recomendação de threshold.
6. Diário: renderer híbrido v3 e tabela única Pricing + Meta Ads + Smart Bidding validados com fixture de 25 campanhas e live read-only; permanecem seleção direta vertical/Messenger Pages/domain, timestamp Smart Bidding e aprovação de automação.
7. Canário live: validar payload, serving, métricas e readbacks com uma campanha aprovada.
8. Escala: Nicolas aprovou `+10%` em todo ciclo ROAS para cada campanha com Meta Purchase ROAS estritamente acima de `0,50`; de `0,40` até `0,50` mantém o budget. Planner está pronto, mas budget write exige Rodolfo/Geizian e um teto/envelope aprovado.

Cada pendência bloqueia somente a ação dependente; não reabre regras já aprovadas.

## Contrato confirmado em blocos — criação, ciclos e reporting

Fonte canônica: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json` v0.2-draft. Este resumo não substitui o JSON vivo.

### Criação de campanha

```text
Campaign  Auction | Sales | CBO | Highest volume | Standard | Financial products/services US
Status    produção normal = ACTIVE com start_time futuro após resumo final aprovado; canário técnico = PAUSED até aprovação separada
Ad set   AdG1 | Messenger | next day 00:00 America/New_York | ongoing | US 18+ All
Ads      1x1x3 ou 1x1x5 | manual upload | Instagram usa Facebook Page
Pixel    Eggbev-US-CC-EN; mesmo pixel para toda a operação
Payer    DIGITAL TRUST; sempre nesta operação
Budget   variável; gestor autorizado escolhe e confirma por campanha; write financeiro mantém gate Rodolfo/Geizian
```

Placements são `MANUAL_ONLY` e estão materializados no contrato: Facebook `feed`, `story`, `search`, `marketplace`, `video_feeds`, `instream_video`, `facebook_reels`, `facebook_reels_overlay`, `profile_feed`; Instagram `stream`, `story`, `reels`, `explore`, `explore_home`, `profile_feed`; Messenger `story`; devices `mobile` e `desktop`. `explore` é dependência obrigatória da API quando `explore_home` está ativo. Audience Network é proibida e nunca se converte o payload para Advantage+ Placements. Criativo sempre novo de `CC_US_EN`, após reserva e conciliação Meta × Drive.

Interpretação determinística de pedido mínimo:

- `cc en us` normaliza para `CC_US_EN`;
- `criar N campanha(s) pagina X` aplica por padrão `1×1×3`, pasta `CC_US_EN`, três criativos inéditos por campanha e nomes `AD NN - {canonical_stem}`; a resposta confirma os defaults e pergunta somente o budget diário;
- “3 campanhas com 3 criativos” = três campanhas, cada uma `1×1×3`, total de nove criativos únicos no lote; nunca reutilizar os mesmos três entre campanhas sem instrução explícita;
- sem override, aplicar o início no dia seguinte às `00:00 America/New_York` e status de produção `ACTIVE` após o resumo final aprovado, sem perguntar novamente pelo horário;
- `pg_XXXXX` deve resolver para uma única linha Messenger da Smart Bidding e a Page precisa passar GET Meta;
- pedir para “puxar da pasta” autoriza a revisão/liberação scoped dos candidatos daquele request, não elegibilidade global nem seleção por ordem de filename.

Copy significa exclusivamente os campos Meta `Primary text`, `Headline`, `Description` e `CTA`; imagens e vídeos são criativos. A referência canônica de copy/estrutura permanece `155 - Jolie Caruthers - ENG - US - (pg_5083) C001 para Jolie - Copy`: Primary text vazio, headlines `APPLY NOW ✅`, `CARD APPROVED`, `✔️ APPLY CARD`, Description `⭐⭐⭐⭐⭐` e CTA `APPLY_NOW`. Por compatibilidade API validada, cada ad usa uma headline aprovada em rotação determinística. Naming from-zero é `[page_sequence] - [Page] - ENG - US - (pg_XXXXX) C0XX`, com avanço C001, C002, C003... na ordem do lote e sem o sufixo `para [Primeiro nome] - Copy`; `DUPnn` permanece exclusivo de clone. `url_tags` usa `utm_campaign=pg_XXXXX`. A instrução atual do gestor vence a referência. Budget não tem default e continua obrigatório; nomes dos ads são derivados automaticamente do slot e do nome canônico do criativo.

O simulador read-only canônico é `python3 scripts/ares-eggbev-creation-intake-simulate.py`. O runner real é `python3 scripts/ares-eggbev-creation.py`: reserva assets somente após pedido scoped, faz pre-stage resumível registry-first, sela manifest, mostra resumo+digest e delega writes ao Engine v3. Depois do readback completo, verifica por GET cada creative criado: Page, `url_tags` e o JSON parseado em `asset_feed_spec.additional_data.page_welcome_message` devem corresponder ao manifest aprovado. Só então move o tratado `01_READY → 02_TESTING` e registra IDs/linhagem; divergência fica `POSTPROCESS_PENDING`, preserva IDs e nunca repete a criação. Falha geral fica `RECOVERY_PENDING` ou `POSTPROCESS_PENDING`, nunca repete POST cegamente.

O início padrão continua no dia seguinte às 00:00 `America/New_York`. Exceção única aprovada para o primeiro request `eggbev-pg-5024-20260830-nicolas-01`: no execute, atualizar o `start_time` para o horário corrente ET com buffer técnico mínimo da Meta. Não propagar essa exceção para campanhas futuras sem novo override explícito.

O template Messenger é obrigatório. Qualquer mudança de texto, botão, payload ou flags exige versão integral + aprovação de Nicolas. Antes de qualquer publicação, apresentar o resumo final e esperar OK explícito; a instrução atual da campanha vence o print de referência.

### Ciclos ROAS

```text
00:00               reset diário do threshold para 0,40
00:00–06:00         formação de dados; sem corte/reativação
Fase 1              06:00, 08:00, 10:00, 12:00
Corte Fase 1        Spend > USD 2 E Purchase ROAS < threshold
Fase 2              13:00, 14:00, 16:00, 18:00, 20:00, 22:00, 23:00
Corte Fase 2        Purchase ROAS < threshold; sem gate de gasto
Reativação          ad pausado pelo Ares com Purchase ROAS > mesmo threshold
23:00–00:00         sem novo corte/reativação
```

Threshold é simétrico; valor exatamente igual não muda estado. Mudança intraday depende do OK de Nicolas. Purchase ROAS vazio com fonte válida é elegível a corte e aparece `N/D`: na Fase 1 o gate `Spend > USD 2` continua; na Fase 2 não há gate de gasto. Por decisão explícita de Nicolas, ausência completa da linha de insight do anúncio na Fase 2 também é `N/D` e corta. Fonte indisponível, com freshness superior a 2h, sem timestamp verificável ou irreconciliável gera `no_write + alerta`, não deve ser confundida com métrica individual vazia.

A ação padrão de ROAS é no ad. Se o ciclo deixar zero ads ativos, cortar todos os elegíveis e pausar a campanha; não pausar o ad set. Essa decisão supersede a invariante anterior de nunca pausar campanha. Se um ad pausado pelo Ares recuperar Purchase ROAS acima do threshold, reativar automaticamente o ad e a campanha no mesmo ciclo, sempre com pré-leitura e readback pós-write.

Escala de budget é uma camada separada: em cada ciclo ROAS aprovado, agregar Meta Purchase ROAS no nível da campanha. `ROAS > 0,50` recomenda aumentar o budget CBO atual em `10%`; `0,40 < ROAS <= 0,50` mantém; `ROAS = 0,50` mantém. A regra é composta ciclo a ciclo. O planner é dry-run; write real depende de Rodolfo/Geizian e de teto/envelope aprovado.

### Reporting

- Intraday: um relatório por ciclo e qualquer atualização sob demanda.
- Núcleo Meta: CPM, Purchase ROAS, `messaging_conversation_started_7d`, custo por mensagem iniciada, Budget, Amount spent e CTR.
- Tabela unificada por campanha: Meta + Smart Bidding + Pricing/monetização, usando UTM exata e confirmação de Page ID.
- Núcleo Smart Bidding solicitado: investimento, receita, Leads/UTM, `AVG_PRICE`, RPS, CPM, EPC, ROI drip, receita líquida/estimada e ROI real/estimado.
- Fonte aprovada por Nicolas: extrair diretamente da rota Smart Bidding compatível — vertical, Messenger Pages ou domain — com readback do endpoint, campo, moeda, período, freshness e identidade. Não existe precedência implícita; usar a granularidade que reconcilia corretamente a linha.
- `Custo/msg iniciada` = spend Meta ÷ `messaging_conversation_started_7d`. Para RPS/EPC, campo direto Smart Bidding vence cálculo local; fórmulas locais são fallback-only, rotuladas e não substituem um campo direto disponível.
- Não inventar denominador, atribuição ou moeda. A ausência de UTM no `/pricing` global não prova indisponibilidade: tentar vertical, Messenger Pages ou domain antes de publicar `N/D`.
- Diário aprovado em múltiplos horários, inspirado na distribuição do Crédito para Veículo e adaptado ao BOT: 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 e 22:00 ET. Não automatizar antes de apresentar o plano final e obter OK explícito de Nicolas.
- Thread Intraday fixa: `Eggbev-US-CC-EN Corte e ROAS` (`1541578606076231750`), nome confirmado por readback.
- Padrão das rotas funcionais: prefixo `Eggbev-US-CC-EN` antes da função. Exceção aprovada por Nicolas: Regras usa a thread atual `1543280854024060999`; a antiga thread de Regras foi supersedida.

## Guardrail aprovado — limite de leads por página

Nicolas aprovou o guardrail específico da conta `Eggbev-US-CC-EN-01-G006`:

```text
Fonte                 Smart Bidding /campaigns/Messenger, publisher Eggbev
Métrica de ação        LEADS (não LEADS_TOTAL)
Operador               estritamente > 5000
Chave primária         UTM_CAMPAIGN exato no padrão pg_XXXXX
Confirmação identidade FB_PAGE_ID da SB = page_id do creative Meta
Escopo Meta            campanha efetivamente ACTIVE com ad efetivamente ACTIVE
Ação                   pausar a campanha inteira; sem budget/delete
Reativação             nunca automática
Frequência aprovada    08:00 e 20:00, America/New_York
Relatório automático   silencioso sem ação; publicar quando houver pausa ou erro
Relatório sob pedido   todas as páginas ativas reconciliadas, com LEADS e proximidade por emoji
```

Este guardrail é exceção explícita à regra de cortes por ROAS: ROAS atua em anúncios; limite de leads atua na campanha inteira. Mapeamento ausente, duplicado ou divergente é `fail_closed_no_write`. Antes do POST, ler o estado real; depois do POST, fazer GET/readback. POST falho é reconciliado por GET e nunca repetido às cegas.

O alerta obrigatório inclui página, UTM, LEADS, estado `RESTRICTED_UNTIL` da Smart Bidding, campanhas pausadas, horário ET, snapshot Meta de hoje e contagem de readbacks. `RESTRICTED_UNTIL` é estado da Smart Bidding e não deve ser descrito como prova independente de uma restrição DTR `#2022`.

Runtime:

```text
Thread fixa           Eggbev-US-CC-EN Limite de Leads (`1543312825890381865`)
Runner                 /root/mgs-agent/scripts/ares-eggbev-page-lead-guardrail.py
Wrapper                /root/.hermes/profiles/ares/scripts/eggbev-page-lead-guardrail.sh
Modo                   dry-run e controlled-write com preflight/readback
Cron                   `0 8,20 * * *`, no_agent=true, deliver=local, enabled/scheduled
Estado do scheduler    ativo; tick 20:00 ET confirmado ok em 29/08/2026; gateway_running=false é falso negativo do observador
Freshness              timestamp Smart Bidding verificável, máximo 2h; ausente/stale = no_write + alerta
Discord                GET/readback exato; fallback único para Regras; falha total torna o run erro
Horário interno        wrapper agendado exige `--scheduled` e permite apenas 08:00/20:00 ET
```

Quando Nicolas pedir relatório, executar leitura real e mostrar todas as páginas exatamente reconciliadas com campanhas e anúncios ativos. Usar **proximidade ao limite**, sem chamar de previsão estatística:

```text
🟢 0–3.999 LEADS      abaixo de 4k
🟡 4.000–4.499 LEADS  atenção
🟠 4.500–5.000 LEADS  muito próxima
🔴 >5.000 LEADS       pausar campanha e reportar com readback
```

A proximidade percentual é `LEADS / 5000`. O check automático permanece silencioso quando não há ação; relatório de status completo é enviado sob pedido do gestor.

## Thread dedicada — Clonar campanhas

Thread fixa: `Eggbev-US-CC-EN Clonar Campanhas` (`1543333373945053184`). Criada por pedido explícito de Nicolas, com Nicolas, Zeus e Rodolfo confirmados por readback e três mensagens de contrato confirmadas.

Escopo exclusivo de clonagem; criação do zero permanece em `Eggbev-US-CC-EN Criar Campanhas`. Executor obrigatório: `meta-campaign-engine-v3`. Modos não intercambiáveis:

- `pure_clone` (**duplicação exata**): preserva estrutura, público, placements, estratégia, Page, JSON Messenger, mídia, copy, links e UTMs; mudam apenas IDs técnicos inevitáveis, budget escolhido pelo gestor, nome `DUPnn` e início/status;
- `clone_prestaged`: preserva lineage/estrutura e usa de 1 a 5 criativos novos aprovados, reconciliados e pre-stageados;
- `clone_page_switch`: preserva estrutura, público, placements, estratégia, copy e mídia, mas troca Facebook Page, `pg_XXXXX`, links/UTMs e o JSON Messenger. A página é indicada por Nicolas; quando ele delegar a escolha, usar a página elegível em entrega com menor `LEADS` após match único `UTM_CAMPAIGN + FB_PAGE_ID`. Empate, fonte stale ou mapping inválido bloqueia a escolha automática.

Naming obrigatório: preservar o nome-base integral e adicionar o próximo número livre `DUP01`, `DUP02`, `DUP03`… Se a fonte já terminar em `DUPnn`, remover apenas esse sufixo para recuperar o mesmo nome-base e usar o próximo número livre após scan das campanhas não deletadas.

Gestores autorizados escolhem e confirmam o budget diário de cada duplicação; essa seleção é input obrigatório, mas não amplia autoridade financeira. O write de budget permanece sujeito ao gate vigente Rodolfo/Geizian. Default de produção: campanha, ad set e todos os ads `ACTIVE`, com início no dia seguinte às 00:00 `America/New_York`; `PAUSED` somente para canário técnico explicitamente pedido.

A conta `1034081997659047` está cadastrada no Engine v3 release 3.4.0. `pure_clone` e `clone_page_switch` não exigem mídia nova no registry; `clone_prestaged` continua exigindo pre-stage dos assets do pedido. Pedidos genéricos de “dup” iniciam perguntas curtas apenas para campos ausentes: modo, quantidade de duplicações e budget; depois, assets/copy ou Page/UTM/JSON conforme o modo. Prompt canônico: `data/ares/discord/thread-prompts/1543333373945053184.txt`. Relatório determinístico: `python3 scripts/ares-eggbev-clone-config-report.py --check`.

Antes de cada plan/write, fazer preflight da fonte e da conta, scan de colisão `DUPnn`, materializar e prevalidar o manifest, mostrar resumo final e aguardar OK explícito. Write real usa somente v3 com `--confirm-execute` e o gate financeiro vigente. Sucesso exige readback consolidado de nome, budget, `ACTIVE`, início aprovado, Page/tracking/mídia/copy e IDs. Não existe cron de clonagem.

Fail-closed para troca de Page/placements: o preflight deve comparar `promoted_object.page_id`, targeting e placements do ad set fonte com o alvo. Se o pedido trocar Page ou exigir normalização de placements, o plan só é válido quando o executor materializar essas mudanças no ad set copiado e o readback confirmar a Page e os placements exatos. `creative_parameters` no anúncio não corrige sozinho o `promoted_object` do ad set. Enquanto o runtime não representar essa atualização, não executar `clone_page_switch` nem `clone_prestaged` combinado com troca de Page; usar outra rota somente após o gestor aprovar explicitamente a mudança de método.

## Apêndice histórico não autoritativo — auditoria pré-simulação de 2026-08-29

> **NÃO USAR COMO REGRA OU READINESS ATUAL.** Este apêndice é preservado somente para rastrear o diagnóstico daquele momento. Todas as afirmações de status, naming, budget, Engine, Smart Bidding, layout e bloqueios abaixo foram supersedidas pelas seções ativas anteriores e pelos arquivos canônicos vivos.

Todas as seis rotas fixas foram atualizadas com regras, riscos e testes; a thread de status também foi atualizada e duas threads históricas receberam aviso de supersessão mantendo o estado arquivado. Readback confirmou 16/16 mensagens e Nicolas, Zeus e Rodolfo em todos os nove alvos da API. Um HTTP 429 ocorreu após efeito parcial: o recovery fez GET de todas as threads, pulou membros/posts já confirmados e publicou apenas as camadas ausentes; zero duplicatas no readback final.

Bloqueios reais antes do canário:

1. observadores do scheduler discordam: processo Ares ativo, cron tool com `gateway_running=false`; confirmar um tick programado antes de confiar na automação de LEADS;
2. Smart Bidding sem conta 01 no report;
3. `ADS ZERO RESULTS` ainda ENABLED; desativar somente no gate futuro já autorizado;
4. `ADS ON 1.1` em `HAS_ISSUES`, sem decisão de remoção/desativação;
5. conta Eggbev ausente do Engine v3 e do media registry;
6. zero campanhas/ads ativos impede validação live de métricas/serving/readback;
7. ROI/RPS/receita líquida e recomendação de threshold sem fórmula aprovada;
8. comando de mudança intraday do threshold ainda não implementado.

Decisões de clonagem atualizadas:

- `pure_clone` e `clone_page_switch` são exceções aprovadas que preservam mídia/copy; campanhas novas e `clone_prestaged` continuam exigindo criativos novos;
- `pure_clone` usa o sufixo `COPY C{fonte}`; `clone_page_switch` usa o naming canônico com próximo sequencial, página-alvo e novo `pg_XXXXX`;
- `clone_page_switch` usa USD 45, próximo dia 00:00 ET e campanha/ad set/ads `ACTIVE` para o início aprovado;
- permanecem pendentes somente o suporte do v3, os campos exatos de JSON/Page no payload e o canário live;
- layout Diário com volume continua pendente: card único ou card + tabela por campanha.

Ordem de testes: fixtures ROAS → fixtures LEADS → fórmulas/layout Diário → onboarding v3 → validate/plan criação → validate/plan clone → campanha canário aprovada → API×Ads Manager×Smart Bidding → dry-run apresentado → controlled-write/readback → crons.

## Runtime ROAS e reporting construído

A autorização inicial de Nicolas para somente runner/testes foi supersedida em 29/08/2026: status writes de anúncio/campanha e postagem dos ciclos ROAS estão autorizados em modo fail-closed; budget write permanece sujeito ao gate Rodolfo/Geizian. Readback atual:

```text
Módulo comum            /root/mgs-agent/scripts/ares-eggbev-roas-common.py
Corte e ROAS            /root/mgs-agent/scripts/ares-eggbev-roas-cycle.py
Diário/sob demanda      /root/mgs-agent/scripts/ares-eggbev-daily-report.py
Testes                  tests/test_eggbev_roas_automation.py
Testes aprovados        63 no módulo ROAS atual; suíte ampliada cobre guardrail, rollover, Fase 2 sem linha, freshness 2h, intervenção manual, escala +10%, layout híbrido, paginação de 25 campanhas e rotas econômicas report-only
Write ROAS              status de ad/campanha habilitado sob gates fail-closed e readback
Budget write            false; exige Rodolfo/Geizian + teto/envelope
Post ciclo ROAS         habilitado na thread fixa
Cron ROAS               00:00, 06:00, 08:00, 10:00, 12:00, 13:00, 14:00, 16:00, 18:00, 20:00, 22:00 e 23:00 ET; scheduler ativo e tick 20:00 alcançou o runner; o ciclo terminou fail-closed por freshness Smart Bidding, não por falha do scheduler
Post/Cron Diário         false
```

### Renderer Corte e ROAS v5 — painel único

Nicolas Holanda solicitou em `2026-08-30`, na thread `1541578606076231750`, substituir os cards e as duas tabelas do v4 por uma leitura curta, visual e inspirada no Intraday CPV. O v5 é a baseline ativa de apresentação; não altera corte, reativação, escala, budget, cron ou autoridade.

A hierarquia da única tabela é: sinais `R/E` → `On` → `Camp/Pg` → `Delivery` → `Ação` → eficiência Meta → identidade/economia Smart Bidding. As colunas, nesta ordem, são:

```text
R/E | On | # | Camp/Pg | Delivery | Ação | C/msg | ROAS | C/res | Res |
Budget | Spend | CPM | CTR | CPC | Page ID | Page | C/Sub | Rev | Profit |
ROI% | Leads | ROI Drip | Rev BC
```

- `Camp/Pg` usa o prefixo operacional real do nome e a UTM `pg_XXXXX`; nunca inventa campanha.
- `C/msg` = spend ÷ `messaging_conversation_started_7d`; `C/res` = spend ÷ resultado Messenger; `CPC` = spend ÷ `inline_link_clicks`.
- `C/Sub*` = `INVESTIMENT ÷ SUBSCRIBED`; `Profit*` = `REVENUE − INVESTIMENT`; `ROI%*` e `ROI Drip*` usam o mesmo investimento como denominador.
- Page ID/Name podem permanecer visíveis por identidade reconciliada mesmo quando as métricas externas ficam `N/D`; valores Smart Bidding exigem UTM + Page ID + freshness válidos.
- `R/E` conserva os sinais dos ROIs real/estimado da rota econômica report-only. Meta Purchase ROAS continua sendo a única métrica de decisão do ciclo.

O renderer mantém também campanhas com insight Meta no dia mesmo quando não entram no plano de write: faz GET exato da campanha, mostra o estado Off/On real e usa `OBSERVAR`, sem criar decisão. A lista por anúncio aparece somente quando há corte/reativação. Não há limite silencioso; a tabela repete o cabeçalho a cada 6 linhas, e mensagens multipart continuam fence-safe com `⚔️ Corte & ROAS • Parte N/T`.

O runner controla proveniência de ads/campanhas pausados pelo Ares, nunca reativa pausa manual ou do guardrail de leads, não altera ad set e exige pré-leitura + readback. Às 00:00 o reset local para `0,40` independe das fontes e não faz write Meta. Smart Bidding ausente/irreconciliável ou `ADS ZERO RESULTS` ativa mantém writes fail-closed; métrica indisponível aparece `N/D`, nunca zero inventado.

### Refinamento visual v6 — 2026-08-30

Por correção de Nicolas na thread `1541578606076231750`, a tabela humana não mostra mais Page ID; esse ID permanece somente no join técnico e no audit. A ordem visual ativa é:

```text
Ligada | Campanha | Entrega | Ação | Página ║ Meta Ads ║ Smart Bidding
```

`Página` fica imediatamente após `Ação` e antes de `Custo por conversa`. Os cabeçalhos usam palavras completas em português, divididas em duas linhas quando necessário; não voltar para `Camp/Pg`, `C/msg`, `C/res`, `C/Sub`, `Rev BC` ou `Page ID`. Valores USD usam cifrão e vírgula decimal, por exemplo `$1,86`. Os grupos **Decisão e Identidade**, **Meta Ads — ROAS em destaque** e **Smart Bidding** usam títulos Markdown em negrito, `║` entre grupos e `│` entre colunas.

ROAS é a única coluna com sinal visual dependente do threshold do ciclo: `🔴` abaixo, `🟡` exatamente igual, `🟢` acima e `⚪` indisponível. O sinal é apresentação; não altera a fórmula nem a lógica de corte/reativação. A largura ampliada usa até 3 campanhas por bloco e repete o cabeçalho completo de duas linhas sem limite silencioso.

### Refinamento visual v7 — ROI e nova posição da Página

Por instrução de Nicolas em `2026-08-30`, a ordem inicial fica `Ligada | Campanha | Página | Entrega | Ação`. Esta regra supersede a posição da Página descrita no v6.

No final do grupo Smart Bidding, exibir duas colunas numéricas distintas:

- `ROI atual`: valor de `roi_real`, calculado por `(NET_REVENUE − INVESTIMENT) / INVESTIMENT × 100` após join econômico exato;
- `ROI estimado`: valor de `roi_estimated`, calculado por `(estimatedRevenue − INVESTIMENT) / INVESTIMENT × 100` após join exato e estimativa não ambígua.

Ambas mostram percentual com sinal: `🟢` positivo, `🟡` zero, `🔴` negativo e `⚪ N/D` quando indisponível. São informativas e nunca substituem Meta Purchase ROAS na decisão de corte/reativação.

### Refinamento visual v8 — ROAS não é ROI negativo

Por correção explícita de Nicolas em `2026-08-30`, Purchase ROAS abaixo de `0,40` significa somente que está abaixo do threshold operacional; não significa resultado econômico negativo. A apresentação de ROAS usa marcadores de posição: `⬇️` abaixo, `🎯` igual, `⬆️` acima e `⚪ N/D` indisponível. Não usar vermelho/verde no ROAS como semântica de prejuízo/lucro.

A classificação `negativo` pertence somente ao ROI: `ROI atual < 0%` ou `ROI estimado < 0%` aparece `🔴`; ROI positivo aparece `🟢`, zero `🟡` e indisponível `⚪ N/D`. Esta distinção visual não altera o threshold nem a lógica de corte/reativação por Meta Purchase ROAS.

### Refinamento visual v9 — abertura mobile e sem legenda recorrente

Por instrução de Nicolas em `2026-08-30`, o relatório Corte e ROAS começa com uma abertura curta para mobile: título com estado e horário ET; uma linha com fase, modo e threshold; uma linha com contagens de campanhas, anúncios, cortes, reativações, escalas e manutenções. A legenda explicativa longa foi removida integralmente do fim do relatório. A tabela e a semântica do v8 permanecem inalteradas; fontes inválidas continuam aparecendo como bloqueio curto no início.

### Refinamento visual v10 — alinhamento Unicode e espaços

Por correção de Nicolas em `2026-08-30`, o painel unificado preserva todos os espaços de padding ao calcular a largura visual e trata sequências emoji com VS16, como `⬇️` e `⬆️`, como duas colunas no Discord. Cabeçalho superior, cabeçalho inferior, separador e todas as linhas devem terminar na mesma coluna visual. A regressão cobre ROAS abaixo, igual, acima e indisponível. Esta revisão é somente de apresentação e não altera fontes, seleção de campanhas, threshold, corte, reativação, budget, cron ou autoridade.

### Refinamento visual v11 — cartões simples sem colunas fixas

Após evidência visual enviada por Nicolas em `2026-08-30`, o renderer deixou de usar a tabela horizontal de 283 colunas, porque o Discord quebrava os cabeçalhos, separadores e valores em linhas diferentes mesmo com a largura Unicode calculada corretamente. O formato ativo usa um cartão Markdown vertical por campanha, com uma métrica completa por linha e seções separadas de decisão, Meta Ads e Smart Bidding. Não há bloco de código, barras verticais, padding manual, coluna fixa nem truncamento de rótulo. Todas as campanhas continuam presentes sem limite silencioso e os chunks Discord são divididos apenas em linhas Markdown normais. Esta revisão é somente visual e não altera fontes, fórmulas, threshold, corte, reativação, budget, cron ou autoridade.

### Refinamento visual v12 — tabelas compactas no padrão CPV 13

Por correção de Nicolas em `2026-08-30`, os cartões v11 foram substituídos por três tabelas compactas alinhadas no mesmo padrão técnico do Intraday Creditoparaveiculo 13: largura dinâmica pelas células reais, duas colunas de espaço entre campos, cabeçalhos curtos em uma linha, divisor Unicode e bloco `text` monoespaçado. As tabelas separam Decisão/Identidade, Meta Ads e Smart Bidding para preservar todas as métricas sem recriar a linha única de 283 colunas. O maior bloco validado tem 96 colunas visuais; a paginação usa o tamanho renderizado real, repete o cabeçalho e mantém fences balanceadas. Esta revisão é somente visual e não altera fontes, fórmulas, threshold, corte, reativação, budget, cron ou autoridade.

### Refinamento visual v13 — tudo em uma tabela única

Por instrução direta de Nicolas em `2026-08-30`, Decisão/Identidade, Meta Ads e Smart Bidding passam a compartilhar uma única tabela compacta no padrão CPV 13. Cada campanha ocupa um grupo indivisível de oito linhas, com colunas `Camp`, `Bloco` e três pares `Métrica/Valor`; a chave da campanha aparece uma vez. A paginação usa o tamanho renderizado real, repete o mesmo cabeçalho e nunca divide o grupo da campanha. A amostra live ficou com 87 colunas visuais e todos os rótulos completos. Esta revisão é somente visual e não altera fontes, fórmulas, threshold, corte, reativação, budget, cron ou autoridade.

### Refinamento visual v14 — hierarquia exata do print CPV 13 Intraday

Após Nicolas enviar o print canônico em `2026-08-30`, o renderer abandonou os cabeçalhos genéricos `Bloco/Métrica/Valor` e passou a usar uma campanha por linha, com a ordem direta `R/E | Camp | Página | Status | Budget | Spend | Custo | ROAS | ROI real | ROI est. | Leads | RPS | CPM | Ação`. As larguras são dinâmicas, há dois espaços entre colunas, um único divisor e paginação somente por overflow real, como no Intraday CPV 13. A amostra live ficou alinhada em 122 colunas visuais. ROAS permanece numérico; os sinais de ROI ficam em `R/E`. Esta revisão é somente visual e não altera fontes, fórmulas, threshold, corte, reativação, budget, cron ou autoridade.

## Apêndice histórico não autoritativo — auditoria ponta a ponta de 2026-08-29 15:37 ET

> **NÃO USAR COMO ESTADO ATUAL.** Os policy updates e hardenings subsequentes deste apêndice explicam a evolução, mas as seções ativas anteriores e os arquivos canônicos vivos são a única regra/readiness aplicável.

Estado comprovado: conta Meta ativa em USD/ET, zero campanhas/ads ativos, zero spend; Fase 1 e Fase 2 executadas em dry-run; Diário live read-only e relatório de LEADS executados; 47 testes aprovados. Smart Bidding continua sem a conta 01 e `ADS ZERO RESULTS` continua ativa, então ROAS write permanece fail-closed.

Furo corrigido: o reset de 00:00 apagava `paused_ads`/`paused_campaigns` e impossibilitava recuperação em outro dia. O rollover agora reseta threshold/campos diários e preserva a proveniência Ares até reativação ou reconciliação explícita.

Gaps que bloqueiam produção:

1. conta/operação Eggbev ausente do Engine v3;
2. criação e os três clones sem manifest/runner Eggbev;
3. `clone_page_switch` ausente do schema/executor, sem seletor de página nem transformer JSON/Page;
4. Smart Bidding sem conta 01;
5. sem watcher de primeira impressão/gasto;
6. conflito nativo `ADS ZERO RESULTS`;
7. scheduler com observadores divergentes;
8. sem reconciliação durável de intervenção manual versus proveniência Ares;
9. sem política de escala para alta performance;
10. sem precedência/freshness aprovada entre Meta ROAS e Smart Bidding ROI;
11. janela Smart Bidding enviada com limites `Z` precisa ser validada contra o dia ET;
12. runner de LEADS não possui gate de freshness da linha;
13. Phase 2 trata ausência total de insight do ad como `N/D` válido e corta; confirmar esse comportamento para zero-delivery;
14. criação do zero sem política final Eggbev de `PAUSED` técnico versus `ACTIVE` futuro;
15. `ADS ON 1.1` segue `HAS_ISSUES` sem decisão.

O comportamento implementado para performance é: abaixo do threshold corta conforme a fase; igual mantém; acima mantém ou reativa somente objetos pausados pelo Ares; todos os ads cortados pausam a campanha; `LEADS > 5000` pausa a campanha terminalmente. Alta performance não escala budget automaticamente.

## Policy update — 2026-08-29 17:08 ET (histórico; supersedido abaixo)

Decisões aprovadas por Nicolas e persistidas no contrato:

- ausência completa de linha de insight na Fase 2 é `N/D` e corta;
- quando Meta Purchase ROAS e Smart Bidding ROI discordarem, Meta Purchase ROAS vence;
- Smart Bidding aceita atraso máximo de 2h e exige timestamp verificável; ausência/stale continua fail-closed;
- alteração manual não apaga permanentemente a proveniência Ares: comparar o conjunto campanha/adset/ad, bloquear a automação afetada e pedir orientação a Nicolas;
- `ADS ON 1.1` deve ser removida; readback encontrou a regra já ausente, então Ares não executou DELETE;
- `ADS ZERO RESULTS` está `DISABLED` por readback e não foi alterada pelo Ares neste update;
- escala aprovada em princípio: todas as campanhas elegíveis com Meta Purchase ROAS estritamente acima do threshold recebem recomendação de budget `+30%`. O planner existe em dry-run, mas budget write segue bloqueado até fechar frequência, cooldown, máximo de execuções/dia e teto/envelope.

Readback vivo antes do guardrail:

```text
Campanha ativa          123 - Lauren Tucker - ENG - US - (pg_13829) 666666
Ads ativos              3
Budget diário           USD 70
Spend do dia            USD 76
Meta Purchase ROAS      0,00
Resultados Messenger    0
Página / UTM            Lauren Tucker / pg_13829
LEADS                    5.239
Smart Bidding report    conta 01 ausente; ROAS write permanece bloqueado
```

O guardrail autorizado foi executado em controlled-write porque `LEADS > 5.000` e o scheduler não era confiável: 1 campanha planejada, 1 pausa confirmada por GET, 1 alerta entregue e 0 mapping issues. Readback independente final: campanha `PAUSED`, effective status `PAUSED`, 0 ads efetivamente ativos. Nunca reativar automaticamente essa campanha pelo runner ROAS.

Validação: 56 testes, `py_compile`, dry-run Fase 2 e `git diff --check` aprovados. O dry-run classificou os três ads sem insight como `PAUSE_AD` e a campanha como `PAUSE_CAMPAIGN`, mas executou zero writes devido ao gate Smart Bidding. O gate de intervenção manual compara `updated_time` de campanha, ad set e anúncio e nunca apaga proveniência automaticamente.

## Policy update — 2026-08-29 17:27 ET

Nicolas fechou os dois pontos pendentes:

- criação normal: após o resumo final aprovado, campanha/ad set/ads nascem `ACTIVE` com `start_time` futuro; canário técnico separado permanece `PAUSED` até aprovação de ativação;
- escala: em cada ciclo ROAS, toda campanha CBO efetivamente ativa com Meta Purchase ROAS agregado `> 0,50` recebe recomendação de `+10%` no budget atual. `ROAS = 0,50` mantém; entre o threshold de corte e `0,50` mantém. O aumento é composto a cada ciclo elegível.

Limite de autoridade: Nicolas aprovou a política, mas a matriz MGS exige Rodolfo ou Geizian para budget write. Portanto o planner e o relatório foram atualizados, enquanto execução de budget permanece `false` até aprovação e teto/envelope.

Validação: 58 testes PASS. Fixture de limite confirmou `0,50 → KEEP`; `0,51 → +10%`; exemplo `USD 100 → USD 110`. Dry-run vivo mostrou o rótulo `Escalas +10% recomendadas` e zero writes/crons.

Smart Bidding avançou parcialmente: a conta `Eggbev-US-CC-EN-01` agora aparece com 1 linha, mas o schema não expõe timestamp de atualização. Como freshness máxima é 2h, o gate retorna `smart_bidding_freshness_unverifiable` e mantém economic writes fail-closed.

## Hardening do Limite de Leads — 2026-08-29 20:00 ET

Os gaps históricos de scheduler e freshness da rota Limite de Leads foram supersedidos:

- tick `c3d2499d8c33` de 20:00 ET confirmado `ok`; próximo 08:00 ET;
- source gate por timestamp com máximo 2h implementado; schema vivo atual não expõe campo aceito, então qualquer campanha ativa reconciliada fica `no_write` e gera alerta até a Smart Bidding fornecer timestamp verificável;
- erros de mapping/freshness são publicados, não ficam apenas no audit;
- posts usam GET/readback exato e falha total termina o run com erro;
- fallback único de erro vai para Regras `1543280854024060999`;
- wrapper automático tem gate interno `--scheduled` para 08:00/20:00 ET;
- auditoria lê `auto_reactivate=false` do escopo correto;
- prompt canônico da thread foi persistido; ativação no gateway depende do próximo restart seguro externo à sessão.

## Sequência de implementação

1. Fechar o contrato em conversa com Rodolfo/Nicolas.
2. Atualizar o JSON da operação e versionar regras próprias Eggbev.
3. Fazer análise inicial read-only da conta e calibrar com conferência manual do gestor.
4. Implementar runner específico com manifest, audit e testes.
5. Criar crons em `no_agent=true`, `deliver=local`, primeiro read-only/dry-run.
6. Validar entrega nas threads fixas e reconciliar contagens.
7. Liberar controlled-write ou autonomia somente por decisão explícita e readback.

## Conclusão mínima

Nenhuma ação Meta é considerada concluída sem readback do alvo. Nenhum cron Eggbev é considerado ativo sem readback de `enabled`, `schedule`, `script`, `no_agent` e `deliver`.
