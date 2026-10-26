# Invoice e Setembro — schema atual de dez colunas

## Autoridade e precedência

Rodolfo, mensagem `1564022485366734969`, pediu Invoice e Setembro antes da antiga E, **na mesma aba**, usando relatório do Ares como referência. O print define Setembro como invoice Unpaid; não é autorização para repetir status antigo nem criar outra aba. Esta referência supersede todas as letras de colunas dos runbooks de sete/oito colunas.

Atual: A Nome, B Forma, C Default, D Última cobrança no cartão, E Invoice, F Setembro — saldo em aberto, G Média diária3 dias, H Pay now, I Current balance, J Outubro/2026. Cabeçalhos repetidos continuam na linha13, título de grupo em A12. Não inserir linhas nem desfazer ordenação humana.

## Coleta e publicação executadas

`python3 scripts/refresh_september_invoices.py` coleta e faz plano; `--apply` atualiza apenas E/F, sob writer.lock, snapshot imutável e readback integral A:K. `--insert-columns-if-needed` serviu só à migração inicial; **não usar nos ticks**. O script resolve a BM/47 IDs pelo contrato, usa token BM-admin existente em memória, /me exato e somente GET Meta; Google somente SA canônica. Pagina business_invoices até o fim e seleciona billing_period=2026-09-01, não invoice_date (outubro). Valida USD, ID de conta exato, invoice_id literal, original em centavos, amount_due.amount_in_hundredths e status.

- **Regra vigente E — Rodolfo `1564382678168502295`:** E é lista operacional de invoices ainda a pagar, não histórico. Quando a Meta confirmar Paid/due=0 ou a invoice não constar mais como pendente após enumeração completa, deixar E em branco; não conservar o número de setembro pago. Preservar número/status anterior só no ledger, notas de evidência e backup. Na virada mensal, preencher as invoices de outubro somente depois que a Meta realmente as gerar/exibir (normalmente por volta do dia2, sem prometer uma data fixa). Não criar número nem transportar invoice paga para o mês seguinte. Esta regra supersede expressamente a conservação de números Paid de versões anteriores. F continua usando amount_due live, zero quando pago; gasto de outubro J não muda implicitamente.
- F mostra **amount_due atual**. Paid exige due=0 e publica0; não apresentar original como pendência. Unpaid/parte remanescente usa o saldo explícito, nunca balance menos Pay now. Sem invoice encontrada após enumeração completa, linha de crédito recebe0 com nota de ausência localizada, não gasto de setembro.
- Cartões sem invoice ficam vazios. Totais monetários usam ROUND(SUM(...),2). Não somar IDs de invoice.
- Invoice compartilhada entre múltiplas contas ou múltiplas invoices para a mesma conta neste recorte bloqueia alocação automática, em vez de duplicar total ou inventar rateio.
- Enumerar toda a BM não autoriza reinserir contas antes excluídas do workbook. A coluna mostra o recorte de47 contas; header/total anotam a diferença contra a BM inteira e o ledger preserva a lista fora do recorte para decisão.

Fonte histórica da implantação (não estado corrente): `reports/meta-september-invoices-1564022485366734969/publication/`. Foram152 invoices em2 páginas,28 de setembro:26 Unpaid e2 Paid. Na aba,20 pendentes somaramUSD275644.71; BM inteiraUSD283813.02, com6 contas fora da aba totalizandoUSD8168.31. CPV04 invoice26877313 e Yolokfx-US-SHEIN-EN-01-G002 invoice26891526 estavam Paid. Revalidar antes de responder.

## Competência após a virada

Por `1564382678168502295`, o runner usa `invoice_period_mode=latest_closed_generated`: seleciona a competência fechada mais recente que **exista realmente** em business_invoices. Se novembro começar sem invoice de outubro gerada, E permanece vazia após a baixa de setembro; não criar número previsto. Quando a Meta gerar outubro, selecionar essa competência e manter o header de F coerente com seu amount_due; J continua outubro conforme contrato separado. Se existir invoice antiga ainda aberta durante a troca, bloquear a troca para conciliação em vez de apagar a dívida. A rotina já existente faz a consulta, sem novo cron do dia2. As referências abaixo a setembro documentam o período inicial.

## Cada tick e compatibilidade

No mesmo job3x/dia, executar primeiro refresh_september_invoices.py --apply. Depois o fluxo normal de API/cartão/Pay now e validador. O fluxo de API escreve C/G/I/J; publisher UI resolve H pelo header e não toca E/F. Instrumento histórico continua somente D com prova PC1.

A ordenação de linhas é apresentação, não identidade: comparar targets por ID/nome, não por row_index/ordem congelados. Resolver a linha atual pelo ID e proteger por snapshot + lock antes de escrever. Nunca usar uma antiga posição para devolver valores após sort. Isso corrigiu um bloqueio indevido do publisher ao receber a ordenação humana atual da aba.

**Gate descoberto na implantação:** Meta passou a informar funding tipo1 para Mavroa-US-SHEIN-ES-03-G003 (`1543098427832443`), enquanto a planilha ainda classifica como linha. Nenhuma mudança de billing foi executada por esta operação. O refresh API geral parou corretamente por funding_group_changed_requires_skill_regroup; Invoice/Setembro e dados existentes foram preservados. Não chamar isso de anomalia nem atribuir autoria sem reconciliar fontes. A classificação/reorganização deve ser alinhada antes de declarar o fluxo inteiro recuperado; não alterar Meta para fazê-la voltar à classificação antiga. A nova coleta UI não deve prosseguir como se ainda fossem39 linhas quando o preflight de funding bloqueia.

As6 contas externas estão registradas no ledger `data/meta-manual-payments/september-invoice-ledger.json`; inclusão requer novo pedido. Não reduzir o escopo por conta própria nem apagar snapshots. Se o gate geral persistir, invoices ainda podem ser atualizadas independentemente e a entrega deve explicar que o restante ficou histórico; não afirmar sucesso integral do tick.
