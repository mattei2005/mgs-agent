---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 1.0.45
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, growth, meta-ads, direct-traffic, vehicle-finance, cbo, roi]
    related_skills: [direct-traffic-cbo-operations, creative-operations-mgs, creative-taxonomy-mgs]
---

# Tráfego Direto para Financiamento Veicular — MGS/Ares

Esta skill especializa o procedimento genérico de tráfego direto CBO para operações de financiamento de veículos, começando por `creditoparaveiculo.com` / `BR-CAR-BR`. Ela governa criação diária, janela de aprendizagem, leitura de ROI, escala, cortes e renovação de campanhas. Estrutura Meta, UTMs, evento, reconciliação e credenciais continuam subordinados à skill `direct-traffic-cbo-operations` e ao runtime real.

## When to use

Use quando o pedido envolver:

- tráfego direto para financiamento de carro/veículo;
- rotina diária do gestor da operação `BR-CAR-BR`;
- campanha CBO 1×1×3;
- leitura de ROI por campanha/adgroup;
- escala de budget nos dias 1–3;
- corte de campanhas após aprendizagem;
- criação diária com criativos do Shared Drive.

Não use para configurar quiz, SMS Funnel, ChatPion, WordPress, pixel crítico, billing ou credenciais. Esses itens exigem rota e autorização próprias.

## Executor de campanhas

Toda criação/clone desta vertical materializa o contrato operacional em `meta-campaign-engine-v3`. Esta skill governa a estratégia Vehicle Finance; não cria outro runner. O hot path recebe mídia Meta pre-stageada, bundle de duas campanhas e um readback consolidado. V3 é a rota ativa sob guards de `development_access`; v2 permanece rollback explícito.

## Fontes de verdade

```text
Fonte                                Uso
------------------------------------ ---------------------------------------------
Meta Ads API/runtime                 status, entrega, spend e budget real
Smart Bidding > Reports > Adgroup    ROI decisório da campanha/adgroup
Shared Drive MGS-AGENTS              criativos elegíveis e suas linhagens
Inventário Ares                      reserva, uso, teste e reconciliação Meta×Drive
Autorização vigente da operação      permissão de criar, escalar, cortar ou ativar
```

Toda leitura de ROI deve informar período, moeda, timezone, fonte e horário de atualização. Nunca substituir a dashboard Smart Bidding por estimativa.

Para `Creditoparaveiculo-BR-CAR-BR-13-G006`, a regra operacional é fixa: selecionar `USD` no rodapé da Smart Bidding, manter `Discount revenue share` ativado e calcular ROI com `NET_REVENUE` pela fórmula `(NET_REVENUE − INVESTIMENT) × 100 ÷ INVESTIMENT`. Não relatar ROI dessa operação com o toggle desligado ou em BRL.

### Experiência, captura e SMS

A experiência é **quiz com rewards após o preenchimento**, com captura de telefone para envio de SMS.

```text
Experiência Meta/Site   quiz com rewards
Captura                 telefone
Evento                  event_Subscribe / SUBSCRIBE
Relatório de aquisição  Smart Bidding > Reports > AdGroup
Relatório de SMS        Smart Bidding > Reports > SMS
```

O endpoint SMS atual usa `UTM_CAMPAIGN=s01c01g006` para o bucket de Nicolas/G006 e não expõe `CAMPAIGN_ID`, `b01fb13cNN` ou `UTM_ADGROUP`. Portanto, até existir ponte confiável, o relatório mostra um bloco separado `Receita SMS G006 — não atribuída por campanha`; nunca repetir o mesmo total em cada linha de campanha. Atribuição por campanha exige mapping adicional no tracking/backend.

No final do relatório da conta/G006, exibir:

```text
Spend Meta
Receita Aquisição SB (NET_REVENUE)
ROI Aquisição = (Receita Aquisição − Spend) / Spend × 100

Custo SMS G006 em USD = custo BRL ÷ PTAX venda BCB
Receita SMS G006 (NET_REVENUE)
SMS enviados G006 (SMS Funnel, recorte de data)
ROI SMS = (Receita SMS − Custo SMS) / Custo SMS × 100

ROI Total sem SMS = ROI Aquisição
ROI Total com SMS = (Aquisição + SMS − Spend Meta − Custo SMS) / Spend Meta × 100
Lucro Líquido USD = Aquisição + SMS − Spend Meta − Custo SMS

Conciliação Meta×SB = Spend Meta − investimento Smart Bidding
```

Preservar exatamente esses quatro blocos e essa ordem no Diário. `Lucro Líquido USD` fica imediatamente depois de `ROI Total com SMS` e antes da separação para `Conciliação Meta×SB`. Sem custo SMS convertido disponível, mostrar `indisponível` em vez de inventar lucro líquido. Não exibir as linhas legadas `Receita total`, `ROI total antes custo SMS` ou `ROI total após custo SMS`; o valor líquido correspondente passa a ser rotulado `ROI total com SMS`.

O custo SMS é do bucket do gestor G006 e não deve ser repetido em cada campanha Meta.

Custo real informado por Rodolfo: `R$ 0,08 × SMS efetivamente enviados`. Para Creditoparaveiculo/G006, a quantidade não vem do total global nem do número de leads:

1. Resolver internamente o item 1Password `SMS Funnel Dashboard` e autenticar somente em modo read-only.
2. Listar as campanhas do SMS Funnel filtrando o gestor exato `G006`.
3. Aceitar exclusivamente as linhagens `AUTOMAÇÃO QUIZ ENTRADA - CREDITOPARAVEICULO - G006` e `AUTOMAÇÃO CHAT ENTRADA - CREDITOPARAVEICULO - G006`.
4. Abrir o drill-down `funnel-performance/{campaignId}/sequences` de cada linhagem.
5. Para um dia, enviar a mesma data em `start_date` e `end_date`; esse drill-down usa intervalo inclusivo.
6. Somar `sms_sent` e `cost`, separar quiz/chat e validar `sms_sent × R$ 0,08 = cost` com tolerância máxima de R$ 0,02.
7. O consolidado global apresentou `end_date` exclusivo no readback vivo; usar `dia+1` somente para auditoria global e nunca para atribuir custo ao G006.

Readback fechado de 20/08/2026: `430 SMS G006 = 430 quiz + 0 chat`, custo `R$ 34,40`. O total global de 5.176 envios permaneceu fora da atribuição do gestor. O card WordPress `linhas × R$ 0,08` continua sendo apenas estimativa e deve permanecer separado.

Como a conta Meta/SB é USD, o relatório visível converte o custo SMS para USD pela `cotacaoVenda` da PTAX oficial do Banco Central do Brasil na data-alvo. Em fim de semana/feriado, usar a taxa oficial mais recente disponível em até 7 dias anteriores e exibir `rate_date` e fonte. Preservar no audit o custo-base em BRL, a taxa e o cálculo. Fórmula:

```text
Custo SMS BRL = SMS enviados × R$ 0,08
Custo SMS USD = Custo SMS BRL ÷ taxa USD/BRL confirmada
ROI Total líquido após SMS =
(Receita Aquisição USD + Receita SMS USD − Spend Meta USD − Custo SMS USD)
÷ Spend Meta USD × 100
```

Se o SMS Funnel não fornecer `total_sms_sent`, exibir `ROI Total com SMS — antes do custo SMS`; não chamar de lucro líquido.

Pixel, evento, Page/identidade, Instagram e URL de destino devem ser herdados da campanha de referência validada na mesma conta e confirmados por readback antes de criar campanha. Não inferir IDs ou valores por nome.

### Seleção da origem do clone por ROI e tipo de veículo

Por correção permanente de Rodolfo em 27/08/2026, a origem do clone diário não é uma campanha fixa. Antes de selar cada manifest:

1. Resolver o tipo de cada grupo 1×1×3 como `CARRO` ou `MOTO`; os três assets do grupo precisam concordar e uma autorização nominal de tipo prevalece como gate.
2. Ler o Smart Bidding Adgroup da data operacional até o horário do preflight, em USD e com `Discount revenue share` ativo.
3. Agregar por campaign ID com `(ΣNET_REVENUE − ΣINVESTIMENT) × 100 ÷ ΣINVESTIMENT` e exigir investimento positivo.
4. Considerar somente campanhas não terminais, MAXVOL (`LOWEST_COST_WITHOUT_CAP`) e do mesmo tipo: nome com token inteiro `MOTO` para MOTO; sem esse token para CARRO.
5. Escolher o maior ROI; desempatar por maior investimento e depois campaign ID estável.
6. Confirmar por Meta GET uma campanha clonável com um adset `OFFSITE_CONVERSIONS` e um conjunto inequívoco `AD01/AD02/AD03`. Anúncios extras não entram quando os três slots canônicos são únicos; ambiguidade bloqueia.
7. Persistir campanha/adset/anúncios fonte, ROI, investimento, receita, data, moeda, fórmula e digest do snapshot antes do manifest. Retomada reutiliza o snapshot selado e nunca recalcula a fonte depois de possível write.

`MOTO→CARRO` e `CARRO→MOTO` são proibidos. C08 só pode ser escolhida quando realmente liderar o ROI elegível da partição correta. Sem fonte elegível, falhar fechado antes de reservar criativos ou escrever na Meta; nunca usar C08 como fallback. A regra vale para novos manifests e não reabre campanhas concluídas historicamente.

### Meta Purchase ROAS como proxy

A coluna do Ads Manager usada nesta operação é `purchase_roas:omni_purchase`, com atribuição padrão da conta. Ela usa valor de compra atribuído pela Meta e não é numericamente igual ao ROI líquido da SB.

Calibração read-only de 21/07/2026 a 19/08/2026:

- com `spend >= USD 10`, correlação Pearson `0,7783` e Spearman `0,7843` entre Meta ROAS e ROI SB;
- limiar empírico que melhor separou sinal positivo/negativo: Meta ROAS aproximado `1,34`;
- abaixo de `1,20`, nenhuma campanha ficou positiva na SB nesse recorte;
- a partir de `1,34`, todas as seis positivas com spend relevante foram capturadas, com duas falsas positivas (`20` e `54`);
- Meta ROAS >= `1,40` teve maior precisão, mas perdeu positivas marginais (`19` e `28`);
- spend muito baixo produz outliers e não deve calibrar limiar.

Usar Meta ROAS como triagem/sinal rápido, nunca como substituto isolado do ROI SB. A única automação que usa ROAS nesta operação é a rota D3 v2 explicitamente autorizada: ela exige junto o histórico real SB, ROI acumulado, D3 real negativo, entrega material, match e freshness; ROAS sozinho nunca pausa nem escala. “Repetir a calibração” significa conferir se os mesmos limites continuam funcionando em outros períodos fechados. Fora desse gate composto, a regra permanece: ROAS sinaliza, SB decide.

### Análise histórica do ciclo

Quando comparar duração e viradas de ROI:

1. Data de criação vem de `created_time` da Meta, convertida para o timezone da conta.
2. “Dia rodado” é uma data distinta com `spend > 0` nos insights diários da Meta; não usar apenas a diferença entre primeira e última data.
3. ROI diário agrega todas as linhas da SB por `CAMPAIGN_ID + DATE`, em USD, com revshare ativado: `(ΣNET_REVENUE − ΣINVESTIMENT) × 100 ÷ ΣINVESTIMENT`.
4. Dia sem spend não é positivo, negativo nem dia rodado.
5. Virada `positivo → negativo` ocorre entre dois dias de spend consecutivos na sequência cronológica; registrar todas as viradas, não apenas a primeira.
6. Marcar o dia atual como parcial e reconciliar spend diário Meta × SB antes de interpretar a curva.

Conclusão: criação, dias rodados, dias positivos/negativos e viradas fecham por campanha, sem confundir intervalo civil com entrega real.

Para status de campanha nesta operação, usar o rótulo do Ads Manager como status humano. O filtro `Campaign delivery = Deleted` pode corresponder a `ARCHIVED` nos edges de listagem, enquanto o GET direto após um write `status=DELETED` também pode devolver `status/effective_status/configured_status=DELETED` — readback vivo da C23 em 25/08/2026 confirmou esse caso. Aceitar ambos como terminais, exibir `DELETED` no relatório operacional e preservar o literal real em `api_raw_status` no audit técnico.

A unidade de intervenção depende da estratégia explicitamente atribuída à campanha:

```text
CAMPAIGN_LEVEL_D1_D3  pausas, reativações e encerramento somente no nível da campanha
CREATIVE_CUT_24H      pausas intermediárias no nível do anúncio; encerramento terminal no nível da campanha
```

Para `CREATIVE_CUT_24H`, carregar obrigatoriamente `references/creative-cut-24h-strategy.md`. A estratégia pertence à campanha e é independente de criar do zero, clonar com criativos novos ou duplicar igual. Campanha sem atribuição explícita permanece no modo canônico de sua operação; silêncio nunca migra estratégia.

Decisão de Rodolfo em 28/08/2026: a nova estratégia é destinada à conta operacional **05** do Creditoparaveiculo BR-CAR-BR. A conta **13** preserva `CAMPAIGN_LEVEL_D1_D3` até nova instrução explícita. A documentação não ativa conta, campanha, cron ou write; onboarding da 05 exige Meta account ID/alias/moeda/timezone e três threads fixas confirmadas.

Nunca pausar conjunto como substituto. Relatórios usam o status real da campanha e, em `CREATIVE_CUT_24H`, também exibem o estado dos anúncios e da janela. Se existir legado com campanha ativa e filhos pausados sem atribuição dessa estratégia, mencionar como observação e não inferir autorização.

## Estrutura padrão de lançamento

```text
Nível       Quantidade          Regra
----------- ------------------- ----------------------------------------------
Campanha    1                   CBO, link direto
Conjunto    1                   evento/UTMs validados
Anúncios    3                   criativos distintos e elegíveis
Lote diário dinâmica            calculada pelo pool de testes aprovado
```

A quantidade diária de campanhas não é fixa. Calcular pelo orçamento reservado a testes e pelo budget inicial mínimo aprovado:

```text
quantidade possível = piso(pool diário de testes ÷ budget inicial por campanha)
```

Exemplo vigente com piso operacional interno de `USD 500` e budget inicial de `USD 25`:

- pool normal sobre o piso: 20% = `USD 100` = até 4 campanhas de USD25;
- pool flexível sobre o piso: 30% = `USD 150` = até 6 campanhas;
- se o total live mais a criação/escala/reativação autorizada ultrapassar USD500, o envelope efetivo sobe ao valor exato necessário e deixa de bloquear o plano somente por esse motivo.

O envelope é controle operacional interno; não altera billing nem `account_spend_limit` da Meta. Desde 27/08/2026, campanhas novas usam budget inicial de USD25. Campanha existente só muda de budget mediante pedido nominal explícito; sem esse pedido, seu valor efetivamente autorizado/executado é preservado. A quantidade continua dinâmica pelo pool: com USD100 integralmente disponível, cabem até quatro campanhas de USD25. A quantidade final também depende de necessidade do ciclo, criativos elegíveis, capacidade de análise e todos os gates não relacionados a budget.

Programar a campanha para começar às `00:30` no timezone real da conta Meta. Não inferir o fuso pelo país ou pelo site; confirmar no runtime da conta.

## Ciclo de três dias

A contagem abaixo usa `D1` como o primeiro dia efetivo de entrega, iniciado às `00:30` no timezone da conta.

### Compliance de anunciante — financeiro BR

Antes de criar adset em campanha `FINANCIAL_PRODUCTS_SERVICES` para BR:

1. Não usar nome de página como beneficiário/pagador. Nesta operação, `Garagem Brasil` é o nome da página; Rodolfo confirmou `Digital Trust` como beneficiário e também como pagador.
2. Beneficiário e pagador são campos separados, mesmo quando têm o mesmo valor; enviar ambos explicitamente quando o fluxo exigir.
3. `/{ad_account_id}/dsa_recommendations` retorna sugestões baseadas na atividade da conta e pode devolver nome de página; isso não prova entidade legal verificada.
4. A documentação oficial da Meta informa que `dsa_beneficiary` e `dsa_payor` são campos para conjuntos que segmentam UE/territórios associados; fora da UE, os valores não são salvos mesmo quando enviados. Portanto, não tratar DSA como solução comprovada do `compliance_section` brasileiro.
5. Ler explicitamente na referência `dsa_beneficiary`, `dsa_payor` e `regional_regulated_categories`, mas separar esses valores de UE da identidade regional brasileira.
6. As tentativas diretas anteriores com `Garagem Brasil` nos dois campos foram inválidas como teste da entidade correta. O reteste com `Digital Trust` como beneficiário e pagador também retornou `3858634`; isso é coerente com a documentação oficial de que DSA não é salvo fora da UE e indica que o `compliance_section` brasileiro depende de outra identidade/estado regional.
7. Cópia profunda síncrona da campanha inteira com `deep_copy=true` falhou com `1885194 / Copy request is too large`.
8. O fallback antigo — cópia rasa de campanha seguida de criação manual de adset — não é clone completo e não pode ser usado para concluir que “clonar também gera 3858634”. Nesse fluxo, `3858634` veio do POST manual do adset.
9. Clone hierárquico validado parcialmente em 20/08/2026: cópia rasa nativa da campanha e cópia nativa do adset compliant passaram, evitando `1885194` e preservando `BRAZIL_REGULATION + VOLUNTARY_VERIFICATION`.
10. A cópia do primeiro anúncio parou com `code=10/subcode=1341012 / No permission to access this profile`. Readback de permissão confirmou que o token de `Roosevelt Mattei` já possui os scopes OAuth `ads_management`, `pages_manage_ads`, `pages_show_list`, `pages_read_engagement` e `business_management`, sem scopes negados.
11. O ativo Página `Garagem Brasil` não aparece em `/me/accounts`, e o GET da página foi negado. Pela documentação oficial, `/user-id/accounts` lista as páginas nas quais o usuário pode executar tasks; para anúncios a task necessária é `ADVERTISE`. Portanto, o blocker é assignment/acesso ao ativo Página, não falta de scope no token.
12. Corrigir no Business Manager: atribuir a Página `Garagem Brasil` ao usuário que emitiu o token (atualmente `Roosevelt Mattei`) com capacidade de anunciar/gerenciar anúncios, equivalente à task Graph `ADVERTISE`; depois renovar o token e validar que `/me/accounts?fields=id,name,tasks` retorna a página contendo `ADVERTISE`.
13. Como o criativo também referencia uma identidade Instagram, manter a conta Instagram associada à Página e atribuída ao mesmo usuário/Business/ad account; o primeiro blocker comprovado, porém, é a ausência da Página.
14. Não repetir cópia/criação de anúncios até o assignment da Página estar corrigido. Depois, repetir somente a camada de anúncios do clone hierárquico e validar 1×1×3 PAUSED.
15. Async batch mínimo permanece não validado e não contorna falta de permissão da página.

Para leituras Meta, usar o próprio header de usage para decidir a janela. A documentação oficial vigente define, no limite por ad account, `development_access` com score máximo 60, decaimento 300 segundos e bloqueio 300 segundos; `standard_access` usa máximo 9000, decaimento 300 segundos e bloqueio 60 segundos. Em `code 17/2446079` ou `613/1487742`, esperar `reset_time_duration` ou `estimated_time_to_regain_access` (em minutos) quando informado; sem estimativa, usar 300 segundos mais 5 segundos de margem na conta `development_access`. Depois do cooldown, retomar somente o GET/readback pendente quando campaign/adset/ad IDs já estiverem persistidos; não repetir copies, normalizações ou qualquer POST já confirmado. Intervalo fixo de 10 segundos fica somente para HTTP `5xx`. Não repetir erro de parâmetro, compliance, permissão ou validação.

Para chamadas Meta nesta operação:

- registrar `X-Business-Use-Case-Usage` em toda resposta;
- soft limit a partir de `80%` da maior métrica;
- `estimated_time_to_regain_access` é em minutos e governa espera de `17/613`;
- sem estimativa, backoff exponencial limitado;
- 10 segundos fixos somente para HTTP `5xx`;
- readbacks de campanha/adsets/ads devem ser agrupados por batch;
- readback rate-limited fica `DEFERRED`, sem classificação de falha nem cleanup até leitura conclusiva;
- state deferred separa `active_campaign_ids`, `deferred_target_ids`, `deferred_stage` e `async_session_ids`; somente campaign IDs criados entram em cleanup;
- sessão async sem ID ou ainda não terminal permanece PAUSED e nunca recebe hierarchy readback/cleanup como se estivesse concluída;
- outer `AresRateLimitDeferred` não recebe segundo backoff no runner; o orçamento de espera é único.

Sequência diagnóstica aprovada após cooldown completo:

1. Teste direto com `BRAZIL_REGULATION + dsa_beneficiary/dsa_payor`, tudo PAUSED; resultado binário por readback.
2. Copiar nativamente o adset compliant da campanha 08 para campanha shell nova, sem ads; se compliant, atualizar nome/budget/targeting e reler.
3. Somente se 1 e 2 falharem, usar async batch nativo com hierarquia mínima.

Qualquer erro novo interrompe a sequência, preserva JSON completo e tenta cleanup confirmado; erro de quota apenas adia o readback.

### Janela de criação e aprovação

Para campanhas novas, trabalhar no timezone da conta:

```text
17:00          materializar/prevalidar manifest e programar para o dia seguinte
17:00–23:30    acompanhar revisão/aprovação da Meta e corrigir erros permitidos
23:30          último readback de campanha, conjunto, anúncios, URLs e aprovação
00:30          início programado da entrega no dia seguinte
```

Essa janela não autoriza campanha sem budget/pool/criativos elegíveis. Se algum anúncio continuar pendente ou rejeitado às 23:30, reportar na thread de Criação e não inventar aprovação; manter a programação ou alterar status somente conforme autorização vigente.

### Guardrail padrão one-shot de primeiro gasto atrasado

Em Creditoparaveiculo BR-CAR-BR, **toda nova campanha de produção** entra automaticamente no guardrail após o readback validado do Campaign Engine v3. Não depende de novo pedido do operador.

1. Pós-processamento obrigatório: campanha `ACTIVE` com início futuro `00:30`, nome/data canônicos, allowlist/ID e hierarquia 1×1×3 validados e gasto observado zero. Falha de enrollment mantém a criação em `POSTPROCESS_PENDING`.
2. Consultar o gasto a cada 15 minutos enquanto a campanha estiver armada e sem primeiro spend.
3. Janela saudável: se o primeiro `spend > 0` for observado entre `00:30` e `02:00` inclusive em `America/Sao_Paulo`, manter ativa, tratar como D1 normal e retirar definitivamente do watcher sem pause.
4. Fora da janela saudável, no primeiro spend positivo pausar imediatamente no nível campanha, validar `PAUSED` por GET e registrar o gasto já ocorrido como pré-D1.
5. Agendar reativação única às `00:30` do dia seguinte, com proveniência obrigatória `first_delivery_guardrail`. Ajustar `DD-MM` para a data dessa reativação sem alterar UTM, ID, budget ou hierarquia.
6. A reativação confirmada começa o D1 operacional MGS. Isso não é alegação de reset técnico do aprendizado Meta.
7. Depois da liberação saudável ou dessa primeira reativação validada, remover a campanha do watcher e nunca rearmá-la automaticamente por esta regra. Pausa humana, terminal ou de origem desconhecida continua bloqueada.

Conclusão: campanhas novas não ficam descobertas; início normal até 02:00 segue otimizando e apenas a primeira entrega tardia recebe uma reentrada controlada.

### Preparação — antes do D1

1. Confirmar conta/alias, site, país, vertical, idioma, timezone, experiência quiz/chat, captura, evento e UTMs no contrato da operação.
2. Selecionar seis criativos elegíveis por bundle de duas campanhas e exigir IDs Meta vertical/square `ready` no media registry v3.
3. Validar o manifest contra a reconciliação/registry já materializados; nenhuma varredura global ocorre no hot path.
4. Executar o bundle CBO 1×1×3 por campanha com cap/quota da lane e mídia pre-stageada.
5. Fazer um readback consolidado das duas campanhas, adsets e ads, validando `00:30` no timezone da conta.

Conclusão: campanha aparece com estrutura 1×1×3, horário, budget e URLs corretos.

### D1 — observar e escalar somente às 08:00

1. Separar sempre as duas métricas da Smart Bidding: `ROI geral` é o ROI normal/real usado para escala; `ROI estimado` é a projeção separada usada nos guardrails de corte. Nunca chamar uma pela outra.
2. Às `08:00`, persistir o ROI estimado do D1 e aplicar no máximo uma escala pelo ROI geral:
   - ROI geral `> 40%`: budget `+30%`;
   - ROI geral `> 30%` e `<= 40%`: `+20%`;
   - ROI geral `> 20%` e `<= 30%`: `+10%`;
   - ROI geral `> 10%` e `<= 20%`: manter sem escala;
   - demais valores: observar, sem corte.
3. Campanha que já começa o D1 em faixa de escala participa normalmente da regra das 08:00.
4. Fora das faixas, D1 continua em observação. Respeitar USD150 por campanha; o envelope da conta usa piso USD500 e sobe ao total exato do plano autorizado. Todo scale exige POST único e GET/readback.

Conclusão: D1 não corta por resultado inicial; escala usa somente ROI geral, apenas às 08:00.

### D2 — repetir análise; ainda sem corte por resultado isolado

1. Às `08:00`, persistir o ROI estimado do D2.
2. Aplicar uma única escala usando o ROI geral e as mesmas faixas do D1: `>20–30% → +10%`, `>30–40% → +20%`, `>40% → +30%`; `>10–20%` mantém; fora das faixas observa.
3. Resultado ruim isolado continua sem corte no D2. Nunca escalar pelo ROI estimado.
4. Respeitar os tetos e confirmar qualquer write por GET/readback.

Conclusão: D2 preserva aprendizagem, registra a segunda observação estimada e mantém a escala restrita às 08:00.

### D3 — duas rotas de corte terminal

No D3, o resultado real passa a ser soberano e o estimado fica como sinal auxiliar.

**Rota A — trajetória estimada rejeitada, às 08:00**

1. Persistir o ROI estimado do D3 e comparar os três checkpoints matinais.
2. Se o ROI estimado foi estritamente negativo no D1, D2 e D3, pausar definitivamente a campanha no nível campanha.
3. Se faltar qualquer checkpoint estimado, falhar fechado e não inventar a sequência.

**Rota B — realidade econômica rejeitada, às 08:00 e recheck às 12:00**

Pausar definitivamente somente quando todos os critérios forem verdadeiros:

1. pelo menos 2 dos 3 ROIs reais estão negativos (`D1 fechado + D2 fechado + D3 parcial até o checkpoint`);
2. ROI real acumulado D1–D3 `<= -10%`;
3. ROI real do D3 no checkpoint `< 0`;
4. Meta `purchase_roas:omni_purchase` ponderado D1–D3 `< 1,20`;
5. spend Meta atual `>= USD 5`;
6. exatamente um match Smart Bidding válido, investimento SB presente, USD e revenue share ativo;
7. atraso Smart Bidding `<= 120 minutos`.

ROI estimado positivo entre `+10%` e `+30%` ou qualquer outra faixa não veta a Rota B. RPS é diagnóstico de monetização e também não veta o corte. Campo ausente, atraso excessivo, match incompleto ou entrega imaterial falha fechado: não executar write. Se a campanha não cumprir o gate completo às 08:00, não escala pela Rota B e é reavaliada às 12:00; se cumprir então, recebe o mesmo corte terminal.

Quando nenhuma rota acionar o corte, apenas às 08:00 continuam valendo as faixas do ROI geral: `>20–30% → +10%`, `>30–40% → +20%`, `>40% → +30%`; `>10–20%` mantém; fora disso observa. Nenhum corte terminal entra na fila de reativação das 00:30.

Conclusão: um estimado moderadamente positivo nunca salva uma campanha com perda real D1–D3 e ROAS abaixo do piso quando todo o gate de realidade está provado.

### Pós-corte terminal — conclusão imediata

Todo corte terminal desta operação (`PARAR D3 ESTIMADO`, `PARAR D3 REAL+ROAS` ou terceira ocorrência `PARAR RECORRÊNCIA`) dispara o ciclo completo no mesmo checkpoint, sem retenção de 24 horas:

1. Persistir a decisão e confirmar a campanha `PAUSED` por GET.
2. Capturar/preservar a entrega acumulada em nível de anúncio e reconciliar exatamente os três assets da campanha.
3. Classificar `spend share >= 10%` como `05_REJECTED`; abaixo de 10% como `03_TESTED / INCONCLUSIVO_POR_SUBENTREGA`.
4. Liberar reteste somente com menos de duas tentativas, nenhuma utilização Meta ativa e identidade Drive↔inventário íntegra; após duas tentativas, o asset não volta ao pool.
5. Mover os três assets no Shared Drive canônico usando a Service Account MGS e exigir readback Drive + inventário.
6. Somente depois da finalização criativa, enviar uma vez `status=DELETED` no nível campanha e aceitar `DELETED` ou `ARCHIVED` no GET terminal.
7. Persistir audit e estado resumível. Erro ambíguo recebe GET antes de qualquer nova tentativa; nunca repetir POST às cegas.

Se identidade, entrega, Drive, inventário ou readback estiver incompleto, a campanha permanece `PAUSED` sem gastar, e a exclusão fica bloqueada até concluir somente a camada faltante. Pausas temporárias das ocorrências 1–2 não entram nesse fluxo.

### Guardrail pós-escala das 16:00

A agenda do próprio dia é `08:00/12:00/14:00/16:00/20:00`; 07:00 permanece o dia anterior fechado. A escala acontece somente às 08:00.

- O guardrail das 16:00 só vale quando o aumento de budget das 08:00 foi realmente executado e confirmado por readback.
- Se às 16:00 o ROI geral estiver negativo, mas o ROI estimado continuar positivo, manter a campanha ativa.
- Se às 16:00 **ROI geral < 0 e ROI estimado < 0**, pausar no nível campanha independentemente da magnitude negativa.
- Primeira ocorrência: pausa temporária; reativação guardada às 00:30 do dia seguinte.
- Segunda ocorrência consecutiva: repetir a pausa temporária e a reativação das 00:30.
- Terceira ocorrência consecutiva: pausa definitiva; nunca reativar.
- Um dia seguinte que não repita o mesmo comportamento pós-escala rompe a sequência e zera o contador consecutivo; dia sem nova escala também não conta como repetição.
- A reativação só aceita proveniência de pausa confirmada por este guardrail; silêncio, pausa humana, hold manual, D3 terminal ou origem desconhecida nunca entram.
- Estado da ocorrência, POST e readback ficam persistidos por campaign ID. Dado estimado ausente/stale bloqueia write.

Conclusão: ROI geral e ROI estimado permanecem métricas distintas; a escala usa o geral às 08:00 e o corte pós-escala usa o estimado junto do geral às 16:00.

## Budget e renovação do portfólio

Parâmetros iniciais informados por Rodolfo:

```text
Parâmetro                                      Valor inicial
---------------------------------------------- ----------------------------------
Piso do envelope operacional interno da conta  USD 500 vigente desde 22/08/2026
Envelope efetivo da conta                      max(USD500, budget live + deltas autorizados)
Budget inicial por campanha nova               USD 25
Pool normal para campanhas novas               20% do piso operacional
Pool flexível autorizado                       até 30% quando o piso de USD 25 exigir
Quantidade de campanhas novas                  dinâmica, calculada pelo pool
Escala com ROI geral >20% e <=30%             +10%
Escala com ROI geral >30% e <=40%             +20%
Escala com ROI geral >40%                      +30%
Teto diário provisório por campanha            USD 150
```

“Budget da conta” é o envelope operacional interno diário do portfólio, não `account_spend_limit` da Meta. USD500 é o piso, não um teto rígido. O teto de USD 150 por campanha é provisório/empírico: após cada escala, acompanhar ROAS e ROI e interromper novas escalas se houver deterioração relevante.

### Envelope dinâmico da conta

Por autorização de Rodolfo em 24/08/2026, Ares recalcula o envelope efetivo em cada preflight como `max(USD500, budget configurado-ativo live + deltas exatos autorizados)`. Os deltas elegíveis são somente:

- campanhas do ciclo diário de 17:00, com USD25 por campanha nova e quantidade dinâmica pelo pool;
- escalas das faixas de ROI geral já aprovadas às 08:00;
- reativações de proveniência guardada já autorizadas.

A regra impede que o piso antigo bloqueie criação ou escala válida. Ela não cria budget extra arbitrário, não altera billing/limite de gasto da conta e não afrouxa identidade, saúde da conta, quota, criativos, reconciliação, horário, allowlist, teto USD150 por campanha ou readback. Drift inesperado depois do plano continua fail-closed.

Manter 20% do piso como pool normal de campanhas novas e até 30% quando o piso de USD 25 exigir. Separar budget comprometido em campanhas reativadas, campanhas novas e reserva operacional antes de qualquer write.

### Autoridade de budget nesta operação

Rodolfo e Nicolas/G006 estão autorizados a ajustar budgets das campanhas e informar/ajustar o teto operacional da conta `Creditoparaveiculo-BR-CAR-BR-13-G006`. Billing, pagamento, credencial e mudanças fora desta operação continuam fora desse escopo. Todo ajuste feito pelo Ares exige preflight, limite vigente, audit e readback.

## Naming Meta e rastreamento

Para criação sequencial normal, ler a conta e usar o próximo número livre. Em **replacement explícito e autorizado**, é permitido reutilizar o número/wrapper canônico `cNN` somente quando a campanha antiga do mesmo número estiver confirmada `DELETED` e não existir outra campanha não deletada com a mesma UTM. Nunca adicionar `rNN` ou outro sufixo fora do wrapper. Preservar auditoria do ID antigo e do novo.

A numeração operacional das campanhas não possui limite em `c59`. Rodolfo confirmou com o time de AdOps que campanhas `c60+` continuam rastreáveis normalmente na Smart Bidding.

```text
c01–c99     numeração com no mínimo dois dígitos
c100+       sequência natural com três ou mais dígitos
```

Continuar a sequência lida ao vivo na Meta, sem bloquear produção em `c59` e sem criar sufixos externos ao wrapper. Criação normal não recicla número deletado; replacement explícito continua podendo reutilizar o número canônico pelo fluxo controlado de campanha substituta `PAUSED` validada, antiga confirmada `DELETED` e ativação posterior. O wrapper permanece `b01fb13c{N}` / `b01fb13c{N}g01`, com o número da campanha em largura variável e mínimo de dois dígitos.

```text
Campanha  NN - DD-MM - {PAGE_NAME} - (b01fb13cNN) event_Subscribe
Adset     01 - AdGroup - (b01fb13cNNg01) event_Subscribe
Anúncio   AD01 - {CANONICAL_FILENAME_SEM_EXTENSÃO}
           AD02 - {CANONICAL_FILENAME_SEM_EXTENSÃO}
           AD03 - {CANONICAL_FILENAME_SEM_EXTENSÃO}
```

Significado:

```text
b01   Business Manager 01
fb13  conta de anúncio 13
cNN   número da campanha
g01   conjunto 01
DD-MM data de início no timezone da conta
event_Subscribe  evento de rewards/quiz obrigatório no nome
```

Tags opcionais entram somente quando diferenciam testes: `LC` = Lowest Cost; `ROAS1.3` = estratégia de bid/ROAS mínimo 1,3; `BROAD` = público amplo; `INT` = interesses; `LAL` = lookalike. Não adicionar tags fixas que sejam iguais em todas as campanhas.

UTMs:

```text
utm_source   facebook
utm_medium   g006-s
utm_campaign b01fb13cNN
utm_adgroup  b01fb13cNNg01
```

A URL base permanece a mesma, mas os parâmetros UTM devem ser substituídos de acordo com a nova campanha/conjunto. Preservar os demais parâmetros da URL, remover valores UTM antigos/duplicados, aplicar URL encoding, validar ausência de espaços e fazer readback da URL final nos três anúncios.

O nome do anúncio preserva o ordinal e o nome canônico do Drive. Inventário/audit também registra `asset_id`, Drive ID, checksum, Meta ad/creative/video ID e linhagem; filename sozinho não prova identidade.

## Três formas de criar campanha

Rodolfo definiu três operações distintas, todas com novos IDs de campanha e conjunto:

1. **Criar do zero (`from_zero_prestaged`):** POST de campanha, conjunto, creatives e anúncios novos, com todos os campos explícitos e criativos novos.
2. **Clonar com criativos novos (`clone_prestaged`):** copiar campanha/conjunto/anúncios da melhor fonte elegível da mesma vertical, preservar lineage e configurações estruturais, mas substituir os três creatives/posts por assets novos do Drive e UTMs do destino.
3. **Duplicar igual (`pure_clone`):** equivalente operacional ao botão `Duplicar` do Ads Manager, mas com rastreamento da nova campanha. Não trocar mídia, copy, estrutura, público, estratégia de lance ou budget. Usar o próximo número sequencial, reescrever campanha/conjunto, `utm_campaign`, `utm_adgroup` e link final para esse número e adicionar o sufixo exato `COPY C{número-fonte-imediato}` ao final do nome; nunca usar `DUP`. Exemplo: duplicar C10 cria C11, quando C11 for o próximo slot livre, e o nome termina em `COPY C10`. Preservar URL base e parâmetros não UTM. Novos IDs técnicos são inevitáveis; a alteração de `url_tags` pode rematerializar o Creative ID, por isso o readback valida equivalência de mídia/copy, link/UTMs e `effective_object_story_id` sem exigir Creative ID igual.

O pedido natural escolhe exatamente uma rota. “Clonar com criativos novos” e “duplicar igual” nunca são sinônimos. Quando o pedido disser “melhor campanha”, a fonte é recalculada no preflight dentro de CARRO ou MOTO; nenhum ID encontrado vira template fixo.

“Clonar” não é apenas renomear o objeto existente; é duplicá-lo em novos objetos. A diferença operacional é que o clone pode herdar configurações antigas ou ocultas. Para uma conta gerenciada 100% pelo Ares, o padrão recomendado é:

1. ler uma campanha humana correta como referência;
2. gerar uma especificação canônica validada;
3. criar a primeira campanha de teste **do zero e PAUSED**;
4. comparar por readback todos os campos críticos com a referência;
5. ativar somente após aprovação do teste;
6. depois usar a especificação validada como template determinístico, sem depender de clone de campanha viva.

Clone fica como fallback quando a API não expuser ou reproduzir com segurança algum campo necessário, ou quando Rodolfo pedir duplicação exata de uma campanha-base. Mesmo no clone, remover heranças indevidas e validar attribution, optimization, evento, placements, pixel, URLs, criativos, budget, horário e status.

## Seleção e variação de criativos

1. Usar apenas assets `ares_eligible=true` e sem reserva conflitante.
2. Tratar original e versão sanitizada como uma única linhagem, nunca como candidatos independentes.
3. Preferir assets novos; também é permitido criar variações reais de criativos promissores para acelerar novos testes.
4. Variação deve mudar criativo de verdade — hook, abertura, copy visual, CTA, composição ou edição — e não somente overlay/zoom.
5. Registrar campanha, conta, gestor, ad/creative IDs, image hash/video ID, Drive ID e data do teste.
6. Reconciliar novamente Meta × Drive e reservar os escolhidos imediatamente antes do write.

O estado atual do pool deve ser lido no inventário e no Drive imediatamente antes da seleção. `01_READY` e metadata limpa não liberam asset reservado; ausência de vínculo Meta também não prova ineditismo.

Quando selecionado, o asset canônico avança de `01_READY` para `02_TESTING`; conta, site, campanha, ad IDs e datas ficam no inventário. Não criar cópias nem mover o mesmo asset para subpastas por conta, pois ele pode participar de vários testes e a identidade deve permanecer única. Se for necessária navegação visual no Drive, usar atalhos por conta/site apontando para o arquivo canônico, somente após plano estrutural aprovado; o inventário continua sendo a fonte de verdade.

O ângulo vem do nome canônico/inventário (`SEM_ENTRADA`, `SUPER_OFERTA`, etc.) e entra no nome do anúncio pelo filename. Ares pode agregar spend e Purchase ROAS em nível de anúncio/ângulo na Meta e confrontar com o ROI SB da campanha. No endpoint AdGroup atual, `AD_NAME` veio vazio em todas as linhas; portanto, ROI SB por anúncio/ângulo ainda não é atribuível de forma honesta. Uma futura chave ad-level (`utm_content` ou AD_NAME ingerido pela SB) só entra após validação do backend.

Conclusão: os três anúncios têm assets distintos ou variações explicitamente aprovadas, rastreáveis, sanitizadas e reservadas para a campanha correta.

## Relatórios Discord e continuidade

Para tráfego direto desta operação, usar três threads operacionais fixas por conta e uma thread permanente de referência:

```text
Criação de Campanhas   registros por evento: pedido, dry-run, write, IDs e readback
Diário Consolidado     07:00 dia anterior; 08:00/12:00/14:00/16:00/20:00 mesmo dia
Intraday               01/03/05/07/09/11/13/15/17/19/21/23 São Paulo
CPV Regras              manual permanente da estratégia; consulta dos gestores
Checkpoint de ação     08:00 (escala + D3), 12:00 (recheck D3 v2) e 16:00 (pós-escala), separados e sem relatório extra
```

A thread `CPV Regras` (`1540426218405363873`) é manual, deve ser preservada indefinidamente e não recebe relatório recorrente nem ação automática de campanha. Ela é a única thread de regras para todas as contas de anúncio `Creditoparaveiculo BR-CAR-BR`; não criar uma cópia por conta. Exceções específicas de conta entram como seções claramente identificadas dentro dessa mesma thread. Quando Rodolfo alterar uma regra, atualizar a operação/skills por supersessão e publicar a regra revisada nessa mesma thread.

Não criar thread fixa de HOA nem de criativos/testes. Criativos permanecem no inventário canônico e são citados nos registros de criação/intraday quando relevantes.

Os relatórios automáticos devem ser script-only/no-agent, consultar Meta/SB ao vivo, postar diretamente na thread fixa, dividir mensagens abaixo de 2.000 caracteres e deixar stdout vazio após sucesso. Nunca depender do histórico de chat para valores operacionais.

Na coluna `Camp` do Diário, Intraday e histórico ROI do Intraday, o rótulo padrão é `C{NN}-{DD/MM}`. Quando o nome canônico da campanha Meta contiver o token inteiro `MOTO`, inserir `M` imediatamente após o número: `C{NN}M-{DD/MM}` (exemplo: `C24M-23/08`). O marcador é somente visual; IDs, UTM, número da campanha, status e cálculos permanecem inalterados. Campanhas sem o token inteiro `MOTO` continuam sem o marcador.

Nas tabelas desktop, paginar pela quantidade real de caracteres renderizados, nunca por um número fixo de campanhas. Se título + tabela couberem no payload seguro de 1.875 caracteres, manter todas as linhas na mesma cerca/tabela. Só dividir quando houver overflow real; nesse caso, repetir o cabeçalho e preservar cada campanha exatamente uma vez. Caso de regressão obrigatório: C07–C20, 14 linhas, permanece em uma única tabela e não deixa C20 órfã em outra parte.

No Intraday, o sinal visual é independente da ação e usa sempre duas bolinhas na ordem fixa `R/E`: primeira = ROI real/geral da Smart Bidding; segunda = ROI estimado. Para cada métrica, `🟢` significa estritamente positivo, `🔴` estritamente negativo, `🟡` exatamente zero e `⚪` indisponível/não calculável. Uma campanha com ROI real negativo e estimado positivo aparece `🔴🟢`; isso informa recuperação projetada, mas não autoriza escala, porque as faixas de escala das 08:00 continuam usando exclusivamente o ROI real/geral. A ação deve ter semântica e emoji próprios: `🧪 APRENDIZADO D1/D2`, `👁️ OBSERVAR`, `✅ MANTER`, `🚀 ESCALAR` e `🛑 PAUSAR/CORTE/BLOQUEADO`. O valor canônico/audit `OBSERVAR D1/D2` permanece inalterado, mas renderiza como `🧪 APRENDIZADO D1/D2`; `👁️ OBSERVAR` fica reservado para D3+ sem ação acionada.

O escopo de **exibição** é descoberto dinamicamente em cada execução pelas campanhas Meta da linhagem da conta (`b01fb13cNN`) e é separado do allowlist de **write** autônomo. Toda campanha nova não deletada entra no Diário e no Intraday mesmo antes do primeiro spend. Campanha deletada/histórica só entra quando possui métrica material no período solicitado: `spend`, `investment` ou `net_revenue` diferente de zero. Linha ausente da lista atual da Meta com todos esses valores zerados é ghost de agregação e fica excluída; C28/C34 são casos de regressão validados. Paginar tabelas e seções cercadas com segurança em vez de truncar campanhas silenciosamente. O allowlist de escala/pausa permanece fail-closed e não pode crescer apenas porque a campanha passou a aparecer no relatório.

No Diário de Creditoparaveiculo BR-CAR-BR, a apresentação ativa é somente desktop: tabela consolidada de campanhas seguida da tabela de resumo da conta. Cards verticais/mobile e divisores por campanha ficam desativados até Rodolfo decidir eventual uso em canais separados. Preservar conteúdo, métricas, cores, escopo dinâmico e paginação segura.

No Intraday da mesma operação, retirar os cards mobile e manter o histórico diário da Smart Bidding somente na tabela histórica compacta desktop — dia atual parcial e quatro dias anteriores — com colunas `Camp`, `Dia` (`Dn/PREP`) e cinco datas explícitas; usar `n/d` quando não houver investimento/match. A fonte continua sendo `NET_REVENUE` em USD com revenue share ativo; o histórico é diário e não substitui o ROI atual/estimado nem pode ser rotulado como acumulado.

O Intraday CPV inclui `RPS` e `CPM` por campanha no Adgroup, em USD e com revenue share descontado: `NET_REVENUE × 1.000 ÷ SESSIONS` e `NET_REVENUE × 1.000 ÷ GAM_IMPRESSIONS`. A Pricing filtrada por `rewarded` fornece `CR Reward = Σ gamMatchedRequests dos cinco blocos rewarded ÷ gamRequests do rewarded base × 100`, mas essa taxa é consolidada por página/operação, não por campanha; o valor cinza é o consolidado anterior/ontem. Não repetir `CR Reward` em cada linha como se fosse segmentada. Para cobertura por campanha, usar o rótulo distinto `Cob. CDP` e a fórmula `CDP_IMPRESSIONS (AD_MATCHED) ÷ CDP_REQUESTS × 100`, agrupada pela UTM da campanha/adgroup. Essa segunda taxa mede a cobertura CDP do tráfego pós-clique e não reproduz a cascata GAM reward; a cascata exata por campanha requer `gamRequests` e `gamMatchedRequests` expostos com dimensão de campanha/UTM.

Readback live de `Reports > CDP` em 24/08/2026 validou a combinação exata para o reward G006: `DATE + UTM_SOURCE + UTM_MEDIUM + UTM_CAMPAIGN + UTM_ADGROUP + JBF_OPERATION + PAGE_TYPE + PATHNAME + SLOT_ID + DEVICE`, métricas `REQUESTS/AD_REQUESTS`, `CDP_IMPRESSIONS/AD_MATCHED`, `COVERAGE`, `AVG_PRICE/PRICE` e `SESSIONS`. Filtrar `UTM_SOURCE=facebook`, `UTM_MEDIUM=g006-s`, campanha `b01fb13cNN`, `JBF_OPERATION=facebook_br_car_financ-carro-s_rec`, `PAGE_TYPE=rec`, `PATHNAME=rec-br-financiamento-de-carro-sem-entrada`, `SLOT_ID=digital-trust_creditoparaveiculo_mob_br_facebook_s_rewarded` e `DEVICE=mob`. A API `POST /report/queryBuilder` devolve `COVERAGE` igual a `AD_MATCHED ÷ AD_REQUESTS × 100` por campanha. O range UTC pode devolver a data civil adjacente; refiltrar `DATE` pela data operacional. Acrescentar `HOUR` aproxima o publisher do limite de 10.000 linhas; para Intraday recorrente, preferir o acumulado diário por campanha e deixar o histórico nascer dos snapshots de 2h. Consulta horária fica diagnóstico on-demand com controle explícito de completude. `JBF_C_PLACEMENT` e `JBF_EX` vieram vazios nesse recorte e não agregam valor.

O layout canônico do Intraday mostra o resumo uma única vez no início, imediatamente antes de `Tabela consolidada — visão desktop`; o chunker mantém esse resumo e a primeira página da tabela na mesma parte Discord. O atraso SB usa `Xh YYmin` a partir de 60 minutos e `Nmin` abaixo disso. `Rewarded CR` aparece somente nesse resumo; não aparece em cards nem como coluna por campanha, pois é um valor consolidado da operação.

Diariamente às 03:00 de São Paulo, criar snapshot local de continuidade com configuração, políticas e estado live. Não executar `/new`, `/reset` ou suposto `/renew`. Hermes não possui `/renew`; a compressão automática in-place preserva a sessão, deixa turns antigos pesquisáveis e evita reset destrutivo.

## Rotina diária do gestor

```text
Janela                 Ação
---------------------- ---------------------------------------------------
Antes de 17:00          fechar pool de budget, referência e criativos elegíveis
17:00                    materializar/prevalidar manifest e programar novas CBOs para 00:30 do dia seguinte
17:00–23:30              acompanhar aprovação Meta e corrigir erros permitidos
23:30                    readback final de aprovação/estrutura/URLs
Por volta de 08:00       persistir ROI estimado; ler ROI geral e executar a única escala elegível do dia
12:00 e 14:00            analisar a evolução sem nova escala
16:00                    aplicar o guardrail pós-escala pelo ROI geral + ROI estimado
20:00                    última análise regular do próprio dia
Durante D1/D2           observar campanhas fora das faixas; não cortar por resultado isolado
No D3 às 08:00          encerrar pela trajetória estimada negativa ou pelo gate composto de realidade
No D3 às 12:00          reavaliar somente a Rota B completa para campanhas preservadas às 08:00
00:30                    reativar somente pausas temporárias verificadas das ocorrências 1–2
Após qualquer write     readback Meta + audit da decisão e da fonte de ROI
```

O horário operacional é sempre o timezone da conta Meta, não o horário local presumido do gestor.

## Pontos ainda abertos antes do primeiro write

1. Escolher a campanha de referência e ler por API os IDs exatos de pixel, Page/Instagram, URL, placements e attribution.
2. Reconciliar/liberar no inventário os criativos que entrarão nas campanhas novas.
3. Definir o próximo número de campanha livre por leitura Meta imediatamente antes da criação.
4. Rodar dry-run da estrutura e validar campanha PAUSED antes de ativação.
5. O scheduler diário de criação às 17:00 São Paulo possui autorização permanente vigente desde 24/08/2026; write corretivo após `V3 BLOQUEADO`, mudança de quantidade/estratégia fora do padrão ou novo hold exige a autorização aplicável.
6. Acompanhar em janelas futuras se o modelo ROAS 1,20/1,34 continua estável; ROAS permanece sinal, SB permanece decisão.

## Pitfalls

1. Cortar no D1/D2 apenas porque a campanha começou ruim.
2. Escalar ROI levemente negativo como se fosse ROI positivo.
3. Decidir somente pelo Ads Manager quando o ROI decisório está no Smart Bidding Adgroup.
4. Misturar ROI diário com ROI acumulado sem rotular.
5. Usar timezone do gestor em vez do timezone da conta.
6. Executar criação/escala fora do envelope dinâmico calculado no preflight ou confundir esse envelope com billing Meta.
7. Criar três campanhas sem reconciliar o percentual real reservado a testes.
8. Reutilizar criativo reservado ou já em teste sem conciliação Meta × Drive.

## Verification

- [ ] Conta/alias, site, vertical, gestor e timezone confirmados
- [ ] Estratégia quiz/chat, captura, evento e UTMs confirmados
- [ ] Estrutura CBO 1×1×3 validada
- [ ] Três criativos sanitizados, elegíveis e reservados
- [ ] Início às 00:30 do timezone da conta validado
- [ ] ROI lido na Smart Bidding > Reports > Adgroup
- [ ] D1/D2 sem cortes por resultado isolado
- [ ] ROI geral e ROI estimado aparecem e são tratados como métricas distintas
- [ ] ROI geral >20%–30% escala 10%; >30%–40% escala 20%; >40% escala 30%, somente às 08:00
- [ ] ROI estimado negativo persistido em D1/D2/D3 às 08:00 gera pausa terminal no D3
- [ ] Gate D3 v2 às 08:00/12:00 exige 2 dias reais negativos, acumulado `<=-10%`, D3 real negativo, ROAS Meta `<1,20`, spend atual `>=USD5`, match único e atraso SB `<=120min`
- [ ] Estimado positivo e RPS não vetam a pausa quando o gate D3 v2 completo está provado
- [ ] Às 16:00, somente campanha escalada às 08:00 com ROI geral e estimado negativos recebe pausa temporária/terminal
- [ ] Ocorrências 1–2 reativam às 00:30; ocorrência 3 e D3 terminal nunca reativam
- [ ] Todo corte terminal confirma PAUSED, classifica/move três criativos com readback e conclui em DELETED/ARCHIVED sem retenção de 24 horas
- [ ] Falha de identidade/Drive/inventário mantém PAUSED e bloqueia a exclusão até a camada faltante ser reconciliada
- [ ] Receita SMS G006 separada e rotulada como não atribuída por campanha enquanto não houver mapping
- [ ] SMS enviados G006 filtrados por data nas duas linhagens SMS Funnel explícitas de quiz/chat
- [ ] Custo SMS G006 validado por `envios × R$ 0,08`, exibido em USD via PTAX venda BCB com data/fonte e sem atribuição do consolidado global
- [ ] Teto diário provisório de USD 150 respeitado e deterioração monitorada
- [ ] Toda campanha nova usa budget inicial de USD 25; campanhas existentes não são alteradas por esta regra
- [ ] Budget anterior/novo, moeda, período e fonte registrados
- [ ] Todo write confirmado por readback Meta
- [ ] Pendências desta versão resolvidas antes de automação autônoma
