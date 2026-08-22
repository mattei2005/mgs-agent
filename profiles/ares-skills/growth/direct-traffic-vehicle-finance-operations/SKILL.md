---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 1.0.26
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
Receita SMS G006 (NET_REVENUE)
SMS enviados G006 (SMS Funnel, recorte de data)
Custo SMS G006 em USD = custo BRL ÷ PTAX venda BCB
Receita Total = Aquisição + SMS
ROI Aquisição = (Receita Aquisição − Spend) / Spend × 100
ROI Total com SMS — antes do custo SMS
ROI Total após custo SMS em USD
```

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

### Meta Purchase ROAS como proxy

A coluna do Ads Manager usada nesta operação é `purchase_roas:omni_purchase`, com atribuição padrão da conta. Ela usa valor de compra atribuído pela Meta e não é numericamente igual ao ROI líquido da SB.

Calibração read-only de 21/07/2026 a 19/08/2026:

- com `spend >= USD 10`, correlação Pearson `0,7783` e Spearman `0,7843` entre Meta ROAS e ROI SB;
- limiar empírico que melhor separou sinal positivo/negativo: Meta ROAS aproximado `1,34`;
- abaixo de `1,20`, nenhuma campanha ficou positiva na SB nesse recorte;
- a partir de `1,34`, todas as seis positivas com spend relevante foram capturadas, com duas falsas positivas (`20` e `54`);
- Meta ROAS >= `1,40` teve maior precisão, mas perdeu positivas marginais (`19` e `28`);
- spend muito baixo produz outliers e não deve calibrar limiar.

Usar Meta ROAS como triagem/sinal rápido, nunca como substituto do ROI SB. “Repetir a calibração” significa conferir se os mesmos limites continuam funcionando em outros períodos fechados; não exige mudar a operação diária. “Automatizar por ROAS” significaria pausar/escalar sem abrir a SB — isso permanece desativado. A regra atual é: ROAS sinaliza, SB decide.

### Análise histórica do ciclo

Quando comparar duração e viradas de ROI:

1. Data de criação vem de `created_time` da Meta, convertida para o timezone da conta.
2. “Dia rodado” é uma data distinta com `spend > 0` nos insights diários da Meta; não usar apenas a diferença entre primeira e última data.
3. ROI diário agrega todas as linhas da SB por `CAMPAIGN_ID + DATE`, em USD, com revshare ativado: `(ΣNET_REVENUE − ΣINVESTIMENT) × 100 ÷ ΣINVESTIMENT`.
4. Dia sem spend não é positivo, negativo nem dia rodado.
5. Virada `positivo → negativo` ocorre entre dois dias de spend consecutivos na sequência cronológica; registrar todas as viradas, não apenas a primeira.
6. Marcar o dia atual como parcial e reconciliar spend diário Meta × SB antes de interpretar a curva.

Conclusão: criação, dias rodados, dias positivos/negativos e viradas fecham por campanha, sem confundir intervalo civil com entrega real.

Para status de campanha nesta operação, usar o rótulo do Ads Manager como status humano. O filtro `Campaign delivery = Deleted` corresponde, nos objetos validados desta conta, ao literal bruto `ARCHIVED` devolvido pela Graph API. Exibir `DELETED` no relatório operacional e preservar `api_raw_status=ARCHIVED` apenas no audit técnico.

Pausa, corte, reativação e encerramento operacional devem ocorrer **somente no nível da campanha**. Não pausar conjunto ou anúncios como substituto. Relatórios usam o status da campanha (`ACTIVE`, `PAUSED` ou `DELETED`) sem criar classificação adicional. Se existir legado com campanha ativa e filhos pausados, mencionar apenas como observação quando relevante; Rodolfo já orientou Nicolas a corrigir o procedimento.

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

Exemplo vigente com teto operacional diário de `USD 500` e budget inicial de `USD 30`:

- pool de 20% = `USD 100` = até 3 campanhas de USD30, preservando USD10;
- pool de 30% = `USD 150` = até 5 campanhas.

O padrão é reservar 20%; Rodolfo autorizou flexibilização para 30% quando necessária para preservar o budget inicial de USD 30 e o volume de testes adequado. A quantidade final também depende de criativos elegíveis, capacidade de análise e espaço para escalar campanhas boas.

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

Para leituras Meta, usar o próprio header de usage para decidir a janela. Em `code 17/613`, esperar `estimated_time_to_regain_access` informado pela Meta; sem estimativa, aplicar backoff exponencial limitado. Intervalo fixo de 10 segundos fica somente para HTTP `5xx`. Não repetir erro de parâmetro, compliance, permissão ou validação.

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
4. Fora das faixas, D1 continua em observação. Respeitar USD150 por campanha e USD500 na conta; todo scale exige POST único e GET/readback.

Conclusão: D1 não corta por resultado inicial; escala usa somente ROI geral, apenas às 08:00.

### D2 — repetir análise; ainda sem corte por resultado isolado

1. Às `08:00`, persistir o ROI estimado do D2.
2. Aplicar uma única escala usando o ROI geral e as mesmas faixas do D1: `>20–30% → +10%`, `>30–40% → +20%`, `>40% → +30%`; `>10–20%` mantém; fora das faixas observa.
3. Resultado ruim isolado continua sem corte no D2. Nunca escalar pelo ROI estimado.
4. Respeitar os tetos e confirmar qualquer write por GET/readback.

Conclusão: D2 preserva aprendizagem, registra a segunda observação estimada e mantém a escala restrita às 08:00.

### D3 — corte pela trajetória do ROI estimado

1. Na leitura das `08:00`, persistir o ROI estimado do D3 e comparar os três checkpoints matinais.
2. Se o **ROI estimado** foi negativo no D1, negativo no D2 e continua negativo no D3, pausar definitivamente a campanha no nível campanha. O valor negativo não possui tolerância de `-10%`; os três checkpoints negativos provam a trajetória.
3. Se faltar qualquer checkpoint estimado, falhar fechado e não inventar a sequência.
4. Quando a trajetória D1–D3 não acionar o corte, aplicar às 08:00 as faixas do ROI geral: `>20–30% → +10%`, `>30–40% → +20%`, `>40% → +30%`; `>10–20%` mantém; fora disso observa.
5. Pausa definitiva não entra na fila de reativação das 00:30.

Conclusão: no D3, trajetória negativa usa exclusivamente o ROI estimado persistido; escala continua usando exclusivamente o ROI geral.

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
Teto operacional diário da conta               USD 500 vigente desde 22/08/2026
Budget inicial por campanha                    USD 30
Pool normal para campanhas novas               20% do teto operacional
Pool flexível autorizado                       até 30% quando o piso de USD 30 exigir
Quantidade de campanhas novas                  dinâmica, calculada pelo pool
Escala com ROI geral >20% e <=30%             +10%
Escala com ROI geral >30% e <=40%             +20%
Escala com ROI geral >40%                      +30%
Teto diário provisório por campanha            USD 150
```

“Budget da conta” é o teto operacional interno diário do portfólio, não `account_spend_limit` da Meta. O teto de USD 150 por campanha é provisório/empírico: após cada escala, acompanhar ROAS e ROI e interromper novas escalas se houver deterioração relevante.

### Escala do teto da conta

O teto da conta será informado/ajustado por Rodolfo conforme a escala e a necessidade de manter campanhas boas. Ares pode calcular uso, projeção e espaço para testes, mas não aumenta o teto da conta por conta própria.

Manter 20% como pool normal de campanhas novas e até 30% quando o piso de USD 30 exigir. Separar budget comprometido em campanhas reativadas, campanhas novas e reserva operacional antes de qualquer write.

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

## Criação do zero versus clone

Os dois métodos são tecnicamente possíveis e ambos geram novos IDs na Meta:

- **Criar do zero:** POST de nova campanha, novo conjunto, novos criativos/anúncios e todos os campos explícitos.
- **Clonar:** copiar uma campanha/conjunto/anúncios existentes e depois alterar nome, criativos, horários, URLs, orçamento e demais diferenças.

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
Checkpoint de ação     08:00 e 16:00 São Paulo, separados e sem relatório extra
```

A thread `CPV Regras` (`1540426218405363873`) é manual, deve ser preservada indefinidamente e não recebe relatório recorrente nem ação automática de campanha. Quando Rodolfo alterar uma regra, atualizar a operação/skills por supersessão e publicar a regra revisada nessa mesma thread.

Não criar thread fixa de HOA nem de criativos/testes. Criativos permanecem no inventário canônico e são citados nos registros de criação/intraday quando relevantes.

Os relatórios automáticos devem ser script-only/no-agent, consultar Meta/SB ao vivo, postar diretamente na thread fixa, dividir mensagens abaixo de 2.000 caracteres e deixar stdout vazio após sucesso. Nunca depender do histórico de chat para valores operacionais.

O escopo de **exibição** é descoberto dinamicamente em cada execução pelas campanhas Meta da linhagem da conta (`b01fb13cNN`) e é separado do allowlist de **write** autônomo. Toda campanha nova não deletada entra no Diário e no Intraday mesmo antes do primeiro spend. Campanha deletada/histórica só entra quando possui métrica material no período solicitado: `spend`, `investment` ou `net_revenue` diferente de zero. Linha ausente da lista atual da Meta com todos esses valores zerados é ghost de agregação e fica excluída; C28/C34 são casos de regressão validados. Paginar tabelas e seções cercadas com segurança em vez de truncar campanhas silenciosamente. O allowlist de escala/pausa permanece fail-closed e não pode crescer apenas porque a campanha passou a aparecer no relatório.

No Diário de Creditoparaveiculo BR-CAR-BR, o formato solicitado é híbrido: cards verticais por campanha para mobile, com `Budget/Spend`, `Custo/ROAS` e `ROI SB`; divisor de 34 caracteres `━`; depois, preservar a tabela consolidada de campanhas e a tabela de resumo da conta para desktop. Cards e tabelas são seções atômicas no chunker, cercas ficam balanceadas e cada conteúdo final permanece em até 1.900 caracteres. Se o empacotamento seguro falhar antes do primeiro POST, repetir automaticamente uma única vez com parser fence-aware e paginação de tabela com cabeçalho repetido; só então falhar fechado. Após qualquer message ID, fazer readback antes de considerar novo envio e nunca repetir cegamente.

No Intraday da mesma operação, cada card mobile também mostra o ROI diário da Smart Bidding nas últimas três datas — dia atual parcial e dois dias anteriores — com data explícita e `n/d` quando não houver investimento/match. Para desktop, manter a tabela consolidada atual e acrescentar uma tabela histórica compacta separada. A fonte continua sendo `NET_REVENUE` em USD com revenue share ativo; o histórico é diário e não substitui o ROI atual/estimado nem pode ser rotulado como acumulado.

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
No D3 às 08:00          encerrar se o ROI estimado persistido foi negativo em D1, D2 e D3
00:30                    reativar somente pausas temporárias verificadas das ocorrências 1–2
Após qualquer write     readback Meta + audit da decisão e da fonte de ROI
```

O horário operacional é sempre o timezone da conta Meta, não o horário local presumido do gestor.

## Pontos ainda abertos antes do primeiro write

1. Escolher a campanha de referência e ler por API os IDs exatos de pixel, Page/Instagram, URL, placements e attribution.
2. Reconciliar/liberar no inventário os criativos que entrarão nas campanhas novas.
3. Definir o próximo número de campanha livre por leitura Meta imediatamente antes da criação.
4. Rodar dry-run da estrutura e validar campanha PAUSED antes de ativação.
5. Obter autorização explícita para o write concreto de reparo legado, reativação e/ou criação.
6. Acompanhar em janelas futuras se o modelo ROAS 1,20/1,34 continua estável; ROAS permanece sinal, SB permanece decisão.

## Pitfalls

1. Cortar no D1/D2 apenas porque a campanha começou ruim.
2. Escalar ROI levemente negativo como se fosse ROI positivo.
3. Decidir somente pelo Ads Manager quando o ROI decisório está no Smart Bidding Adgroup.
4. Misturar ROI diário com ROI acumulado sem rotular.
5. Usar timezone do gestor em vez do timezone da conta.
6. Ultrapassar o teto operacional por escalas sucessivas.
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
- [ ] Às 16:00, somente campanha escalada às 08:00 com ROI geral e estimado negativos recebe pausa temporária/terminal
- [ ] Ocorrências 1–2 reativam às 00:30; ocorrência 3 e D3 terminal nunca reativam
- [ ] Receita SMS G006 separada e rotulada como não atribuída por campanha enquanto não houver mapping
- [ ] SMS enviados G006 filtrados por data nas duas linhagens SMS Funnel explícitas de quiz/chat
- [ ] Custo SMS G006 validado por `envios × R$ 0,08`, exibido em USD via PTAX venda BCB com data/fonte e sem atribuição do consolidado global
- [ ] Teto diário provisório de USD 150 respeitado e deterioração monitorada
- [ ] Budget anterior/novo, moeda, período e fonte registrados
- [ ] Todo write confirmado por readback Meta
- [ ] Pendências desta versão resolvidas antes de automação autônoma
