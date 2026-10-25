---
name: meta-manual-payments-planning
description: "Use when planning manual Meta card payments."
version: 0.1.0
author: Rodolfo Mattei, Hermes Agent
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, meta, billing, manual-payments, credit-cards, credit-line, sheets, finance]
    related_skills: [meta-ads-api-operations, google-drive-agent-automation, secure-remote-windows-automation]
---

# Planejamento de pagamentos manuais Meta

## Objetivo e autoridade

Esta é a skill dona do fluxo de apoio financeiro a Rodolfo: inventariar contas Meta, separar cartão e linha de crédito, conferir cobranças e invoices, calcular o gasto diário e organizar uma planilha que o ajude a fazer pagamentos manuais com seus diversos cartões, reduzindo os saldos das contas e a dependência da linha de crédito.

Fonte da finalidade aprovada: Rodolfo, mensagem `1563943171392667679`, thread `1563926766286803004`. Essa finalidade é estratégia de planejamento, não uma autorização permanente para efetuar pagamentos, escolher cartões, alterar billing, budgets, permissões ou credenciais. Rodolfo decide e executa os pagamentos; qualquer execução futura por Zeus continua sujeita à autorização específica e à confirmação adicional de billing do `AGENT.md`.

## When to Use

- Planilha de contas, saldos, últimas cobranças no cartão, gasto mensal ou média diária para decidir pagamentos manuais.
- Distribuir pagamentos entre cartões disponíveis e diminuir utilização da linha de crédito, sem alterar a forma padrão por inferência.
- Distinguir saldo corrente, valor do Pay now, invoice fechada, crédito publicitário e pagamento efetivamente realizado.
- Reconciliar um pagamento manual relatado por Rodolfo e atualizar o mesmo workbook sob pedido autorizado.
- Não usar para criar/otimizar campanhas, autorizar novos pagadores, pagar automaticamente ou mudar a forma padrão.

## Pré-requisitos e fontes

1. Resolver o pedido, BM, workbook/aba, período, moedas e autoridade exatos. Ler o estado live antes de mutação; nunca ampliar para outras BMs.
2. Carregar `meta-ads-api-operations` para transporte Meta, leitura segura de 1Password e cobertura BM-admin. Usar a credencial administrativa existente aprovada; um token operacional restrito não prova inventário completo. Não trocar referências de produção.
3. Carregar `google-drive-agent-automation` antes de Sheets: somente SA `mgsagent@mgs-core-prod.iam.gserviceaccount.com`, projeto `mgs-core-prod`, helper `/root/mgs-agent/scripts/mgs_google_workspace_auth.py`. Conferir os quatro seletores `service_account`, Drive `canEdit` e Sheets HTTP 200. Não usar OAuth pessoal/browser Google como fallback.
4. APIs/dashboards/recibos live são fonte de estado; screenshots são evidência limitada ao conteúdo visível. Ler imagens com `vision_analyze`. Nunca confundir nome de conta, posição de linha, pagamento atual e transação histórica.
5. Para endpoints e evidência do workbook existente, carregar `references/collection-and-workbook.md`. Para retomada e limites comprovados do caso inicial, carregar `references/digital-trust-baseline.md`; valores históricos dessa referência nunca substituem coleta atual.

## Procedimento

### 1. Congelar e coletar o escopo

- Paginar completamente `owned_ad_accounts` e `client_ad_accounts` da BM e unir por ID; preservar duplicatas de nome como contas distintas. Registrar contagem por origem e lacunas de acesso.
- Ler identidade, moeda, timezone, funding atual e balance por conta. Manter só tipo e bandeira/final mascarados; nunca persistir tokens, payment-source IDs ou transações protegidas em saída pública.
- Classificar cartão por funding tipo 1; linha de crédito por tipo 4 com monthly-invoicing; omissão é não identificado, não ausência de meio de pagamento.
- Coletar Insights do mês solicitado e reconciliar diário x agregado por conta com Decimal, respeitando moeda e dia atual parcial. Não usar lifetime `amount_spent` como mês.
- Persistir cada lote sanitizado e exigir igualdade do conjunto de IDs antes de publicar.

### 2. Última cobrança somente no cartão

- Ler atividades `category=BUDGET`; identificar a transação histórica efetivamente paga por cartão e selecionar a mais recente confirmada.
- Excluir **Advertising credit**, créditos de anúncio/promocionais, cupons, bônus, estornos, reversões, falhas e recusas.
- `ad_account_billing_charge`, `payment_amount` e `action=67` não comprovam cartão: créditos publicitários podem ter exatamente o mesmo formato. O valor ser pequeno/grande e o default atual também não comprovam o meio histórico.
- Exigir evidência do instrumento da transação: registro transacional/UI com cartão identificado ou screenshot do usuário reconciliado de forma única por conta e sequência/data/valor. Guardar data, timezone, bandeira/final permitido e fonte na nota da célula.
- API é a primeira rota. Inspecionar campos/rotas suportados antes de declarar que a API não atende; ausência de instrumento no endpoint consultado não é impossibilidade global da API. Não derivar um tipo de cartão de transaction IDs ou códigos opacos.
- Se precisar de UI, usar sessão autenticada aprovada e conferir conta/BM/perfil/URL reais. Um gate numa janela não prova que o Facebook esteja deslogado em todo o PC1. Só pedir login após verificar a superfície correta; preservar janelas, perfis e credenciais.
- Se faltar prova, deixar o campo em branco, sinalizar a lacuna e preservar o valor anterior no backup/audit, sem apresentá-lo como cartão. Sem evento no histórico não significa cobrança zero. Não somar últimas cobranças de datas diferentes como um total mensal.

### 3. Média diária e planejamento entre cartões

- Usar os três últimos dias **completos**, no timezone de cada conta; excluir hoje. Somar gasto dessas datas e dividir por 3, inclusive datas sem gasto. Reconciliar com agregado independente.
- Publicar número com dois decimais e nota das datas/fuso. Subtotais são a soma das médias por conta exibidas; não misturar moedas.
- Para recomendar valor/cartão, obter de fonte atual a disponibilidade de cada cartão e obrigações relevantes; não supor capacidade a partir de saldo Meta ou funding default. Usar apenas bandeira/final e um alias seguro, nunca número completo/CVC.
- Apresentar por conta: saldo corrente, gasto diário, pagamento proposto, cartão proposto e saldo/projeção após pagamento, sempre distinguindo observado de simulado. Não adicionar novas colunas ou abas sem pedido.
- Nunca prometer que um pagamento liberará a mesma quantia da linha: conciliar efeito real na conta e na linha/available credit após liquidação. Pagamento avulso não implica mudança da forma padrão.

### 4. Balance, Pay now, invoices e pagamentos

- Tratar separadamente: current balance, gasto do mês, valor permitido no modal Pay now, invoice original, saldo pendente da invoice e pagamentos efetivados.
- No modal ler rótulo/período literalmente. `Amount you can pay now` não é automaticamente o saldo total, uma invoice ou o limite do cartão. Não inferir que balance menos Pay now seja dívida do mês passado.
- Paginar invoices com campos explícitos e unir por `ad_account_ids`. Reportar número, competência, moeda, valor original, status, pendência e vencimento. `Paid` com pendência zero não é invoice ainda devida; não inventar invoice de mês ainda aberto.
- Reconciliar pagamento de uma conta na linha por evento/data/valor e evidência do instrumento quando disponível; pagamento no cartão pode coexistir com monthly invoicing padrão. Não atribuir transação a uma invoice sem ligação comprovada.
- Atualizar balance e Insights em um lote GET-only temporalmente coerente antes de explicar diferenças. Só reportar conciliação exata quando observada em centavos; não forçar igualdade contábil universal nem inventar causa para divergência.

### 5. Publicar no mesmo workbook

- Preservar ID do workbook/aba, contas, notas, links, fórmulas e outras abas; backup imutável antes de cada mudança e diário de recuperação separado.
- Layout padrão já aprovado neste fluxo: **A Nome da conta; B Forma de pagamento; C Cartão default; D Última cobrança no cartão; E Média diária dos últimos 3 dias; F Saldo a pagar; G Gasto do mês**. Identificar a coluna pelo header/schema, não continuar usando a antiga letra E após inserções.
- Separar blocos de cartão e linha, ordenar por nome exato/ID e colocar subtotais abaixo dos blocos e total geral abaixo. D não recebe soma que pareça total mensal de pagamentos. Valores em moeda original explícita, sem total misto.
- Exclusão de linhas zero somente sob pedido específico e com a coluna de gasto mensal corretamente resolvida. Não excluir automaticamente contas novas/inativas; preservar as removidas no backup e validar todos os IDs restantes.
- Nomes das contas são clicáveis para Billing & payments, não Summary. Usar URL de billing validada com BM e `asset_id` exatos; preservar nomes e IDs em notas, sem normalizá-los ou inferir parâmetros ocultos de prints.
- Totais financeiros usam `ROUND(SUM(...),2)`; validar resultado calculado independentemente com Decimal. Ler effective formatting quando cores sinalizam pendências e tolerar apenas quantização RGB comprovada.
- Depois de inserir/reordenar colunas, ler de volta todos os valores/fórmulas, IDs, links, notas relevantes, moedas, blocos e subtotais; confirmar preservação de outras abas. Se um write já ocorreu, recuperar apenas a camada faltante, nunca reaplicar non-idempotent inserts ou reescrever o dataset às cegas.

### 6. Apoio ao pagamento manual e acompanhamento

- Antes de qualquer proposta, fornecer fonte/data, contas exatas, cartões propostos, valores, disponibilidade conhecida e lacunas. Proposta não é pagamento autorizado.
- Não clicar em Pay now final, cadastrar cartão, mudar default, pagar invoice ou automatizar transferências por causa desta skill. Uma eventual execução futura deve obter o gate de billing específico e sua confirmação adicional.
- Quando Rodolfo informar que pagou, confirmar transação e saldo de forma read-only. Registrar confirmado, pendente ou não localizado; não descontar apenas porque o usuário planejou pagar, nem repetir uma cobrança ambígua.
- Não instalar cron/refresh automático por padrão. A planilha é fotografia datada até haver autorização explícita e validação de um processo recorrente.

## Validação executável somente leitura

Usar `terminal(command="python3 /root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts/validate_workbook_readonly.py --spreadsheet-id <ID> --sheet-id <GID> --business-id <BM_ID>", timeout=180)` depois da publicação. O helper usa a SA canônica, confere schema, IDs, links de billing, fórmulas calculadas e totais; reporta campos de cartão vazios sem fingir que validou o instrumento. Não coleta novos gastos, não atualiza a aba e não executa pagamentos. A saída é evidência de estrutura/readback do snapshot, não refresh financeiro.

## Verificação e entrega

Concluir somente após contagem/IDs e dados alterados baterem com a fonte, fórmulas calculadas estarem corretas, efeitos externos terem readback e lacunas estarem explícitas. Na resposta: o que mudou na aba, período da média, cobrança somente no cartão, conciliação das contas citadas, o que permanece pendente e se houve ou não pagamento real. Nunca declarar que esta skill concluiu a conferência das contas pendentes.

Para alterações nesta skill, atualizar o inventário, registrar audit, sincronizar o espelho versionado e publicar REPORT-INFRA pelo helper canônico, com readback do embed. Decisões estratégicas e retomadas ficam no registry/checkpoint MGS, não em MEMORY/USER.
