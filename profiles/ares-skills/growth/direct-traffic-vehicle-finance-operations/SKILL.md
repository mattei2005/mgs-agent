---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 0.3.0
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
   - ROI `<= 30%`: manter budget, sem escala.
4. Respeitar o teto diário provisório de USD 150 e validar qualquer escala por GET/readback, registrando valor anterior, valor novo, ROI, ROAS e horário.

Conclusão: nenhuma campanha foi cortada no D1; eventual escala ocorreu somente nas faixas aprovadas e com autorização vigente.

### D2 — repetir análise; ainda não cortar

1. Reabrir ROI e spend no mesmo recorte/timezone.
2. Continuar sem corte por resultado ruim: a campanha permanece em aprendizagem/observação.
3. Por volta das `08:00` da conta, repetir as faixas de escala:
   - ROI `> 40%`: `+30%`;
   - ROI `> 30%` e `<= 40%`: `+20%`;
   - ROI `<= 30%`: manter.
4. Nunca ultrapassar o teto diário provisório de USD 150; validar write por readback e manter histórico cumulativo da campanha.

Conclusão: D2 preserva a campanha para leitura; cortes continuam bloqueados e escalas ficam auditadas.

### D3 — iniciar cortes e escala disciplinada

1. Ler o ROI cumulativo dos três dias na SB, em USD e com revshare ativado.
2. Aplicar a regra de corte no nível campanha:
   - ROI `<= -10%`: pausar/cortar a campanha;
   - ROI `> -10%` e `<= 30%`: manter sem escala e continuar observação;
   - ROI `> 30%` e `<= 40%`: escalar `20%`;
   - ROI `> 40%`: escalar `30%`.
3. Usar Meta ROAS como apoio: `<1,20` reforça negativo; `1,20–1,34` é faixa cinza; `>=1,34` é sinal positivo/proximidade, mas a SB decide.
4. Respeitar teto diário provisório de `USD 150` por campanha e monitorar se ROAS/ROI deterioram após escala.
5. Pausa, manutenção ou escala são feitas no nível campanha e validadas por readback.

Validação histórica: entre campanhas com Meta ROAS >1,30 e spend >=USD 10, nenhuma vencedora estava em ROI cumulativo `<= -10%` no D3. A campanha 28 estava em `-8,10%` no D3 e só ficou positiva no 9º dia, portanto não deve ser cortada pela regra. Campanhas 20, 34 e 54 estavam abaixo de -10% no D3 e terminaram negativas. O limite é operacional e deve continuar sendo monitorado.

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
Escala com ROI >30% e <=40%                    +20%
Escala com ROI >40%                            +30%
Teto diário provisório por campanha            USD 150
```

“Budget da conta” é o teto operacional interno diário do portfólio, não `account_spend_limit` da Meta. O teto de USD 150 por campanha é provisório/empírico: após cada escala, acompanhar ROAS e ROI e interromper novas escalas se houver deterioração relevante.

### Escala do teto da conta

O teto da conta será informado/ajustado por Rodolfo conforme a escala e a necessidade de manter campanhas boas. Ares pode calcular uso, projeção e espaço para testes, mas não aumenta o teto da conta por conta própria.

Manter 20% como pool normal de campanhas novas e até 30% quando o piso de USD 30 exigir. Separar budget comprometido em campanhas reativadas, campanhas novas e reserva operacional antes de qualquer write.

## Naming Meta e rastreamento

Antes do write, ler a conta e usar o próximo número de campanha livre; não reutilizar número de campanha deletada.

```text
Campanha  NN - {PAGE_NAME} - (b01fb13cNN) event_Subscribe
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
event_Subscribe  evento de rewards/quiz obrigatório no nome
```

UTMs:

```text
utm_source   facebook
utm_medium   g006-s
utm_campaign b01fb13cNN
utm_adgroup  b01fb13cNNg01
```

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

Conclusão: os três anúncios têm assets distintos ou variações explicitamente aprovadas, rastreáveis, sanitizadas e reservadas para a campanha correta.

## Rotina diária do gestor

```text
Janela                 Ação
---------------------- ---------------------------------------------------
Antes de 00:30          preparar e programar novas CBOs
Por volta de 08:00      ler ROI SB, revisar spend e executar escala elegível
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
- [ ] D3 pausa campanha com ROI cumulativo <= -10%
- [ ] ROI >30% e <=40% escala 20%; ROI >40% escala 30%
- [ ] Teto diário provisório de USD 150 respeitado e deterioração monitorada
- [ ] Budget anterior/novo, moeda, período e fonte registrados
- [ ] Todo write confirmado por readback Meta
- [ ] Pendências desta versão resolvidas antes de automação autônoma
