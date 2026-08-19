---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 0.2.0
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

### Meta Purchase ROAS como proxy

A coluna do Ads Manager usada nesta operação é `purchase_roas:omni_purchase`, com atribuição padrão da conta. Ela usa valor de compra atribuído pela Meta e não é numericamente igual ao ROI líquido da SB.

Calibração read-only de 21/07/2026 a 19/08/2026:

- com `spend >= USD 10`, correlação Pearson `0,7783` e Spearman `0,7843` entre Meta ROAS e ROI SB;
- limiar empírico que melhor separou sinal positivo/negativo: Meta ROAS aproximado `1,34`;
- abaixo de `1,20`, nenhuma campanha ficou positiva na SB nesse recorte;
- a partir de `1,34`, todas as seis positivas com spend relevante foram capturadas, com duas falsas positivas (`20` e `54`);
- Meta ROAS >= `1,40` teve maior precisão, mas perdeu positivas marginais (`19` e `28`);
- spend muito baixo produz outliers e não deve calibrar limiar.

Usar Meta ROAS como triagem/sinal rápido, nunca como substituto do ROI SB. Antes de automatizar corte ou escala por ROAS, repetir a calibração em outras janelas e aprovar thresholds com Rodolfo.

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

Programar a campanha para começar às `00:00` no timezone real da conta Meta. Não inferir o fuso pelo país ou pelo site; confirmar no runtime da conta.

## Ciclo de três dias

A contagem abaixo usa `D1` como o primeiro dia efetivo de entrega, iniciado à meia-noite da conta.

### Preparação — antes do D1

1. Confirmar conta/alias, site, país, vertical, idioma, timezone, experiência quiz/chat, captura, evento e UTMs.
2. Selecionar três criativos elegíveis no Shared Drive.
3. Reconciliar Drive × Meta e reservar os assets imediatamente antes do write.
4. Criar a CBO com um conjunto e três anúncios, no budget inicial aprovado.
5. Programar início para `00:00` da conta e validar por GET/readback.

Conclusão: campanha aparece com estrutura 1×1×3, horário, budget e URLs corretos.

### D1 — observar aprendizagem; não cortar

1. Ler o ROI na Smart Bidding, na sessão `Reports > Adgroup`.
2. Classificar provisoriamente:
   - ROI positivo: campanha promissora e elegível para escala;
   - ROI levemente negativo na faixa mencionada de `-10` a `-15`: campanha promissora para observação, sem escala automática por essa condição;
   - resultado muito ruim: marcar para vigilância, mas não cortar, pausar ou substituir no D1.
3. No primeiro horário operacional, por volta das `08:00` da conta, campanha com ROI positivo pode receber aumento de `25%` no budget.
4. Validar qualquer escala por GET/readback e registrar valor anterior, valor novo, fonte do ROI e horário.

Conclusão: nenhuma campanha foi cortada no D1; eventual escala de 25% ocorreu apenas com ROI positivo e autorização vigente.

### D2 — repetir análise; ainda não cortar

1. Reabrir ROI e spend no mesmo recorte/timezone.
2. Continuar sem corte por resultado ruim: a campanha permanece em aprendizagem/observação.
3. Por volta das `08:00` da conta, campanha com ROI positivo pode receber novo aumento de `25%`, sujeito à regra final de frequência/compounding e ao teto operacional.
4. Validar write por readback e manter histórico cumulativo da campanha.

Conclusão: D2 preserva a campanha para leitura; cortes continuam bloqueados e escalas ficam auditadas.

### D3 — iniciar cortes e escala disciplinada

1. Ler o acumulado dos três dias e também o desempenho diário, sem misturar timezones.
2. Aplicar critérios de corte e escala definidos pelo playbook final de Rodolfo.
3. Não permitir que a campanha ultrapasse o teto operacional informado de `USD 150` sem nova regra/autorização explícita.
4. Evitar escala agressiva que estoure custo e destrua o ROI.
5. Validar pausa, corte, escala ou manutenção por readback Meta e registrar o ROI da Smart Bidding usado na decisão.

Conclusão: cada campanha recebe uma decisão auditável no D3; os critérios exatos de corte permanecem pendentes até Rodolfo concluir o playbook.

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
Escala por rodada elegível                     +25%
Teto operacional por campanha                  USD 150, definição exata pendente
```

“Budget da conta” deve ser tratado como **teto operacional interno diário do portfólio**, não confundido automaticamente com `account_spend_limit` da Meta. Os writes normais continuam nos budgets CBO das campanhas.

### Escala sugerida do teto da conta

Ares pode recomendar aumento do teto quando a conta provar capacidade de absorção. Usar dois níveis independentes:

1. **Escala da campanha:** campanha elegível recebe +25% no primeiro checkpoint operacional, dentro do teto atual.
2. **Escala da conta:** aumentar o teto do portfólio somente quando a soma das campanhas boas estiver sem espaço para novas escalas/testes e o ROI consolidado da conta permanecer saudável em dias fechados.

Sugestão inicial para calibração:

- manter 70%–80% para campanhas em aprendizagem/escala e 20% para novos testes;
- permitir 30% de testes quando o piso de USD 30 ou a necessidade de volume justificar;
- recomendar aumento do teto em degraus de 20%–25%, nunca salto aberto;
- exigir pelo menos dois dias fechados consecutivos com ROI consolidado positivo e ausência de anomalia relevante antes de subir o teto;
- após o aumento, observar um dia fechado antes de recomendar novo degrau;
- se o ROI consolidado deteriorar, congelar novas escalas da conta antes de cortar automaticamente campanhas ainda em D1/D2.

Esses critérios de escala da conta são proposta do Ares e permanecem em calibração até aprovação explícita de Rodolfo.

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

## Seleção de criativos

1. Usar apenas assets `ares_eligible=true` e sem reserva conflitante.
2. Tratar original e versão sanitizada como uma única linhagem, nunca como candidatos independentes.
3. Preferir criativos com histórico compatível com o teste proposto, sem transformar winner antigo em garantia.
4. Registrar campanha, conta, gestor, ad IDs, creative IDs, hashes e data do teste.
5. Consumir o percentual aprovado de renovação somente após reconciliar o orçamento disponível.

Conclusão: os três anúncios têm assets distintos, rastreáveis, sanitizados e reservados para a campanha correta.

## Rotina diária do gestor

```text
Janela                 Ação
---------------------- ---------------------------------------------------
Antes de 00:00          preparar e programar novas CBOs
Por volta de 08:00      ler ROI SB, revisar spend e executar escala elegível
Durante D1/D2           observar campanhas ruins; não cortar
No D3                   decidir corte, manutenção ou escala pelo acumulado
Após qualquer write     readback Meta + audit da decisão e da fonte de ROI
```

O horário operacional é sempre o timezone da conta Meta, não o horário local presumido do gestor.

## Pontos ainda abertos

Não automatizar os itens abaixo até Rodolfo concluir a explicação:

1. Unidade exata da faixa `-10`/`-15` na Smart Bidding.
2. Critérios objetivos de corte no D3.
3. Se a escala de 25% pode ocorrer em dias consecutivos sobre o budget já escalado.
4. Se `USD 150` é teto de budget diário, spend acumulado ou outra medida.
5. Regra de realocação do budget liberado por campanhas cortadas.
6. Gatilho definitivo para aumentar o teto operacional da conta e percentual de cada degrau.
7. Frequência e momento de substituição dos três criativos.
8. Conta Meta piloto, alias, timezone, moeda, pixel/evento, experiência e credencial autorizada.

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
- [ ] Início às 00:00 do timezone da conta validado
- [ ] ROI lido na Smart Bidding > Reports > Adgroup
- [ ] Nenhum corte executado no D1/D2
- [ ] Escala de 25% aplicada somente com ROI positivo e autorização vigente
- [ ] D3 usa critérios finais aprovados por Rodolfo
- [ ] Teto de USD 150 respeitado conforme definição final
- [ ] Budget anterior/novo, moeda, período e fonte registrados
- [ ] Todo write confirmado por readback Meta
- [ ] Pendências desta versão resolvidas antes de automação autônoma
