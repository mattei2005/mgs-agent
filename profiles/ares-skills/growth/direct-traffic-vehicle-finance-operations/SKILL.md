---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 1.0.5
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
Receita Total = Aquisição + SMS
ROI Aquisição = (Receita Aquisição − Spend) / Spend × 100
ROI Total com SMS = (Receita Aquisição + Receita SMS − Spend) / Spend × 100
```

Custo real informado por Rodolfo: `R$ 0,08 × SMS efetivamente enviados`. A quantidade enviada deve vir do SMS Funnel/vendor (`total_sms_sent`); não usar quantidade de leads nem repetir o custo por campanha sem atribuição. O card WordPress `linhas × R$ 0,08` continua sendo apenas estimativa e deve permanecer separado.

Como a conta Meta/SB é USD, converter o custo real BRL→USD com taxa, data e fonte registradas antes do fechamento:

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

Exemplo com teto operacional diário de `USD 300` e budget inicial de `USD 30`:

- pool de 20% = `USD 60` = até 2 campanhas;
- pool de 30% = `USD 90` = até 3 campanhas.

O padrão é reservar 20%; Rodolfo autorizou flexibilização para 30% quando necessária para preservar o budget inicial de USD 30 e o volume de testes adequado. A quantidade final também depende de criativos elegíveis, capacidade de análise e espaço para escalar campanhas boas.

Programar a campanha para começar às `00:30` no timezone real da conta Meta. Não inferir o fuso pelo país ou pelo site; confirmar no runtime da conta.

## Ciclo de três dias

A contagem abaixo usa `D1` como o primeiro dia efetivo de entrega, iniciado às `00:30` no timezone da conta.

### Compliance de anunciante — financeiro BR

Antes de criar adset em campanha `FINANCIAL_PRODUCTS_SERVICES` para BR:

1. Ler `/{ad_account_id}/dsa_recommendations` e registrar a entidade recomendada sem inventar valor.
2. Ler explicitamente na referência `dsa_beneficiary`, `dsa_payor` e `regional_regulated_categories`.
3. Não assumir que os campos DSA resolvem o advertiser brasileiro: nesta conta a recomendação foi `Garagem Brasil`, a referência retornou DSA nulo e o POST continuou falhando com `3858634 / Advertiser is missing / compliance_section`, mesmo enviando `Garagem Brasil` nos dois campos.
4. Tratar `VOLUNTARY_VERIFICATION` visto no GET como estado derivado; não há evidência de que enviá-lo no POST crie o vínculo oculto.
5. Criação do zero via API pública permanece bloqueada nesta conta até capturar um payload/HAR sanitizado do Ads Manager ou a Meta expor o campo de identidade regional necessário.
6. Cópia profunda síncrona de 1×1×3 falha com `1885194 / Copy request is too large`; o próximo caminho autorizado de diagnóstico é async batch nativo, após cooldown da conta.

Para leituras Meta com falha transitória/rate limit, esperar 10 segundos e tentar novamente com limite total. Não repetir erro de parâmetro, compliance ou validação. Ao receber `code=17/subcode=2446079 / Ad Account Has Too Many API Calls`, parar imediatamente os writes, preservar cleanup/audit e aguardar cooldown.

### Janela de criação e aprovação

Para campanhas novas, trabalhar no timezone da conta:

```text
18:00          iniciar criação/write e programar para o dia seguinte
18:00–23:30    acompanhar revisão/aprovação da Meta e corrigir erros permitidos
23:30          último readback de campanha, conjunto, anúncios, URLs e aprovação
00:30          início programado da entrega no dia seguinte
```

Essa janela não autoriza campanha sem budget/pool/criativos elegíveis. Se algum anúncio continuar pendente ou rejeitado às 23:30, reportar na thread de Criação e não inventar aprovação; manter a programação ou alterar status somente conforme autorização vigente.

### Preparação — antes do D1

1. Confirmar conta/alias, site, país, vertical, idioma, timezone, experiência quiz/chat, captura, evento e UTMs.
2. Selecionar três criativos elegíveis no Shared Drive.
3. Reconciliar Drive × Meta e reservar os assets imediatamente antes do write.
4. Criar a CBO com um conjunto e três anúncios, no budget inicial aprovado.
5. Programar início para `00:30` da conta e validar por GET/readback.

Conclusão: campanha aparece com estrutura 1×1×3, horário, budget e URLs corretos.

### D1 — observar aprendizagem; não cortar

1. Ler o ROI na Smart Bidding, na sessão `Reports > Adgroup`.
2. Classificar provisoriamente:
   - ROI positivo: campanha promissora; aplicar escala somente nas faixas acima de 30%;
   - ROI `> -10%` e `<= 0%`: campanha promissora para observação, sem escala;
   - ROI `<= -10%` ou resultado muito ruim: marcar risco e continuar observando, mas não cortar/pausar no D1.
3. No primeiro horário operacional, por volta das `08:00` da conta, aplicar escala pelo ROI cumulativo da SB:
   - ROI `> 40%`: aumentar budget em `30%`;
   - ROI `> 30%` e `<= 40%`: aumentar budget em `20%`;
   - ROI `>= 20%` e `<= 30%`: aumentar budget em `10%`;
   - ROI `< 20%`: manter budget, sem escala.
4. Respeitar o teto diário provisório de USD 150 e validar qualquer escala por GET/readback, registrando valor anterior, valor novo, ROI, ROAS e horário.

Conclusão: nenhuma campanha foi cortada no D1; eventual escala ocorreu somente nas faixas aprovadas e com autorização vigente.

### D2 — repetir análise; ainda não cortar

1. Reabrir ROI e spend no mesmo recorte/timezone.
2. Continuar sem corte por resultado ruim: a campanha permanece em aprendizagem/observação.
3. Por volta das `08:00` da conta, repetir as faixas de escala:
   - ROI `> 40%`: `+30%`;
   - ROI `> 30%` e `<= 40%`: `+20%`;
   - ROI `>= 20%` e `<= 30%`: `+10%`;
   - ROI `< 20%`: manter.
4. Nunca ultrapassar o teto diário provisório de USD 150; validar write por readback e manter histórico cumulativo da campanha.

Conclusão: D2 preserva a campanha para leitura; cortes continuam bloqueados e escalas ficam auditadas.

### D3 — iniciar cortes e escala disciplinada

1. Ler o ROI cumulativo dos três dias na SB, em USD e com revshare ativado.
2. Aplicar a regra de corte no nível campanha:
   - ROI `<= -10%`: avaliar estimado/anomalias; pausar se o gate não justificar hold;
   - ROI `> -10%` e `< 20%`: manter sem escala e continuar observação;
   - ROI `>= 20%` e `<= 30%`: escalar `10%`;
   - ROI `> 30%` e `<= 40%`: escalar `20%`;
   - ROI `> 40%`: escalar `30%`.
3. Usar Meta ROAS como apoio: `<1,20` reforça negativo; `1,20–1,34` é faixa cinza; `>=1,34` é sinal positivo/proximidade, mas a SB decide.
4. Respeitar teto diário provisório de `USD 150` por campanha e monitorar se ROAS/ROI deterioram após escala.
5. Pausa, manutenção ou escala são feitas no nível campanha e validadas por readback.

Validação histórica: entre campanhas com Meta ROAS >1,30 e spend >=USD 10, nenhuma vencedora estava em ROI cumulativo `<= -10%` no D3. A campanha 28 estava em `-8,10%` no D3 e só ficou positiva no 9º dia, portanto não deve ser cortada pela regra. Campanhas 20, 34 e 54 estavam abaixo de -10% no D3 e terminaram negativas. O limite é operacional e deve continuar sendo monitorado.

### Gate de estimado e anomalias

A SB expõe `estimatedRevenue`, `estimatedRoi`, `confidence` e atraso estimado de consolidação. `confidence=0,95` significa confiança declarada do estimador, não garantia de acerto. O ROI estimado usa `(estimatedRevenue − INVESTIMENT) / INVESTIMENT × 100`.

- D1/D2: estimado é informativo; não há corte.
- D3 com ROI real `<= -10%` e ROI estimado também negativo: pausar, salvo anomalia externa.
- D3 com ROI real `<= -10%`, mas ROI estimado positivo: não escalar; colocar em hold por uma atualização consolidada/até o próximo checkpoint, respeitando teto de spend, e reavaliar ROI real.
- Se a projeção não se confirmar após o atraso informado pela SB, aplicar a regra do ROI real.
- Antes de culpar a campanha, verificar anomalia de monetização/entrega: queda ampla de RPS/CPM/AVG_PRICE, atraso de receita, problema de AdX/GAM/SB, Meta account/delivery, pixel/evento, URL/quiz ou queda simultânea em várias campanhas.
- Anomalia externa relevante gera `HOLD_EXTERNAL_ANOMALY`: sem corte/escala até confirmar a fonte ou o próximo checkpoint.

Conclusão: estimado pode adiar um corte por um período limitado; nunca autoriza escala sozinho. ROAS e estimado sinalizam, ROI real SB decide depois do gate de anomalia.

## Budget e renovação do portfólio

Parâmetros iniciais informados por Rodolfo:

```text
Parâmetro                                      Valor inicial
---------------------------------------------- ----------------------------------
Teto operacional diário da conta               USD 300 como referência inicial
Budget inicial por campanha                    USD 30
Pool normal para campanhas novas               20% do teto operacional
Pool flexível autorizado                       até 30% quando o piso de USD 30 exigir
Quantidade de campanhas novas                  dinâmica, calculada pelo pool
Escala com ROI >=20% e <=30%                  +10%
Escala com ROI >30% e <=40%                    +20%
Escala com ROI >40%                            +30%
Teto diário provisório por campanha            USD 150
```

“Budget da conta” é o teto operacional interno diário do portfólio, não `account_spend_limit` da Meta. O teto de USD 150 por campanha é provisório/empírico: após cada escala, acompanhar ROAS e ROI e interromper novas escalas se houver deterioração relevante.

### Escala do teto da conta

O teto da conta será informado/ajustado por Rodolfo conforme a escala e a necessidade de manter campanhas boas. Ares pode calcular uso, projeção e espaço para testes, mas não aumenta o teto da conta por conta própria.

Manter 20% como pool normal de campanhas novas e até 30% quando o piso de USD 30 exigir. Separar budget comprometido em campanhas reativadas, campanhas novas e reserva operacional antes de qualquer write.

### Autoridade de budget nesta operação

Rodolfo e Nicolas/G006 estão autorizados a ajustar budgets das campanhas e informar/ajustar o teto operacional da conta `Creditoparaveiculo-BR-CAR-BR-13-G006`. Billing, pagamento, credencial e mudanças fora desta operação continuam fora desse escopo. Todo ajuste feito pelo Ares exige preflight, limite vigente, audit e readback.

## Naming Meta e rastreamento

Antes do write, ler a conta e usar o próximo número de campanha livre; não reutilizar número de campanha deletada.

Limite da integração Smart Bidding informado por Rodolfo:

```text
c01–c59   campanhas operacionais rastreáveis na SB
c60+      sem tracking SB; permitido somente para teste técnico explicitamente autorizado
```

Ao esgotar `c59`, bloquear novas campanhas de produção e exigir nova convenção/mapping antes do write. Não contornar o limite reutilizando número deletado nem declarar ROI SB para `c60+`.

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

Para tráfego direto desta operação, usar três threads fixas por conta:

```text
Criação de Campanhas   registros por evento: pedido, dry-run, write, IDs e readback
Diário Consolidado     07:00 São Paulo, referente ao dia anterior fechado
Intraday               08:00, 12:00, 15:00, 20:00 e 23:00 São Paulo
```

Não criar thread fixa de HOA nem de criativos/testes. Criativos permanecem no inventário canônico e são citados nos registros de criação/intraday quando relevantes.

Os relatórios automáticos devem ser script-only/no-agent, consultar Meta/SB ao vivo, postar diretamente na thread fixa, dividir mensagens abaixo de 2.000 caracteres e deixar stdout vazio após sucesso. Nunca depender do histórico de chat para valores operacionais.

A cada três dias às 03:00 de São Paulo, criar snapshot local de continuidade com configuração, políticas e estado live. Não executar `/new`, `/reset` ou suposto `/renew`. Hermes não possui `/renew`; a compressão automática in-place preserva a sessão, deixa turns antigos pesquisáveis e evita reset destrutivo.

## Rotina diária do gestor

```text
Janela                 Ação
---------------------- ---------------------------------------------------
Antes de 18:00          fechar pool de budget, referência e criativos elegíveis
18:00                    criar/programar novas CBOs para 00:30 do dia seguinte
18:00–23:30              acompanhar aprovação Meta e corrigir erros permitidos
23:30                    readback final de aprovação/estrutura/URLs
Por volta de 08:00       ler ROI SB, revisar spend e executar escala elegível
Durante D1/D2           observar campanhas ruins; não cortar
No D3                   decidir corte, manutenção ou escala pelo acumulado
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
- [ ] D1/D2 sem cortes
- [ ] D3 com ROI <= -10% passa pelo gate de estimado/anomalia antes da pausa
- [ ] ROI 20%–30% escala 10%; >30%–40% escala 20%; >40% escala 30%
- [ ] Receita SMS G006 separada e rotulada como não atribuída por campanha enquanto não houver mapping
- [ ] Teto diário provisório de USD 150 respeitado e deterioração monitorada
- [ ] Budget anterior/novo, moeda, período e fonte registrados
- [ ] Todo write confirmado por readback Meta
- [ ] Pendências desta versão resolvidas antes de automação autônoma
