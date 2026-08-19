---
name: direct-traffic-vehicle-finance-operations
description: "Opera tráfego direto de financiamento veicular."
version: 0.1.0
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

## Estrutura padrão de lançamento

```text
Nível       Quantidade normal   Regra
----------- ------------------- -------------------------------------
Campanha    1                   CBO, link direto
Conjunto    1                   evento/UTMs validados
Anúncios    3                   criativos distintos e elegíveis
Lote diário 3 campanhas         padrão inicial informado por Rodolfo
```

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
---------------------------------------------- -----------------------------
Orçamento de referência por conta              USD 300
Budget inicial por campanha                    USD 30
Percentual reservado a campanhas novas         20% do orçamento da conta
Quantidade normal de campanhas novas por dia   3
Escala por rodada elegível                     +25%
Teto operacional por campanha                  USD 150
```

Há uma pendência matemática a fechar: `20% de USD 300 = USD 60`, enquanto `3 campanhas × USD 30 = USD 90`, ou `30%` do orçamento de referência. Não resolver por inferência. Antes de automatizar lotes, confirmar se muda o percentual, a quantidade de campanhas, o budget inicial ou a definição de “orçamento por conta”.

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
6. Resolução entre 20% para campanhas novas e o lote 3 × USD 30.
7. Frequência e momento de substituição dos três criativos.

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
