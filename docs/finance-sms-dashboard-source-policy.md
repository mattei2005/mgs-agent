# SMS financeiro — dashboard do SMS Funnel como fonte final

## Regra ativa
Autoridade: Rodolfo Mattei, mensagem1557758039962951733 na thread1545426987756298340. Aplicação: outubro de2026 e todas as competências posteriores, preservando fechamentos anteriores.

**O total de SMS e o consumo financeiro devem seguir sempre o valor exibido na dashboard do SMS Funnel para o mesmo dia/período e fuso. Em divergência, esse valor prevalece.**

- A lista mensagem por mensagem serve para identificar gestor/campanha e conferir a distribuição; não pode substituir o total exibido na dashboard.
- WordPress, banco local, analytics por campanha e somas derivadas não vencem o total da dashboard.
- Uma consulta por API pode automatizar a leitura, mas só representa o valor oficial quando corresponde à mesma informação exibida na dashboard, com período e fuso equivalentes. Não presumir que todo endpoint do fornecedor seja a mesma superfície.
- Não perguntar novamente a Rodolfo qual dessas fontes deve prevalecer. Essa escolha está encerrada.
- Divergência no detalhe permanece como ocorrência de conciliação. Não inventar um envio, zero, desconto, rateio ou gestor para forçar igualdade; esta decisão de fonte não autoriza atribuição financeira arbitrária.
- Quantidade/custo oficial e atribuição por gestor são verificações distintas. Só declarar preenchimento/fechamento concluído depois de conferir o resultado efetivamente gravado.
- Recarga permanece crédito pré-pago fora do resultado; consumo permanece despesa direta. Preservar moedas, custo unitário confirmado, histórico, idempotência e backups.

## Supersessão e implementação
Esta decisão esclarece e supersede somente a precedência da fonte no registro `mgs-finance-sms-daily-accounting-1555567071864037377` e em `data/finance-sms-usage-contract.json`: dashboard acima da lista detalhada ou de outro agregado. Preserva as demais regras de consumo e atribuição confirmadas anteriormente.

Registro atual: `FINANCE-SMS-DASHBOARD-SOURCE-1557758039962951733`, chave `finance.sms_funnel.daily_consumption.accounting`.

O registro inicial1557758039962951733 salvou a regra, mas não publicou o coletor nem concluiu07/10. Esse estado de implementação foi supersedido pela execução autorizada em1557763144762269717, abaixo; o histórico do registro inicial permanece preservado.

## Implementação aplicada e verificada —1557763144762269717
- Frontend público do fornecedor confirmado: `DashboardComponent.dailySents` usa `/daily-sents?startDate=YYYY-MM-DD`. A resposta contém oito datas consecutivas, inclusive futuras, e a primeira posição corresponde à data solicitada. Validar rótulos/datas; não presumir que a série termine hoje.
- O executor financeiro consulta esse mesmo valor antes/depois da coleta, mantém IDs únicos e paginação completa dos detalhes e todas as sequências atribuídas a gestores conhecidos.
- O custo financeiro é quantidade oficial × custo unitário confirmado. A diferença em relação à soma observada por gestor vira um registro explícito de conciliação **sem gestor**, com sinal, autoridade, contagem de origem e hashes. Não é novo envio, não se confunde com G002 e não altera os custos individuais observados nem as comissões por conta dessa diferença.
- Uma divergência de total/detalhe deixa de bloquear o preenchimento quando o total da dashboard e a coleta forem válidos; a discrepância continua visível na trilha de conciliação e no recibo. Fonte indisponível, mudança durante a coleta, mensagem duplicada, outra data ou sequência desconhecida continuam bloqueando com segurança.
- Dia07/10:26.401SMS/R$2.112,08 aplicados, contra26.402 detalhes preservados. Conciliação de−1SMS/−R$0,08 no custo fica sem atribuição a gestor. SMS e receita GAM confirmados; cutoff07/10; replay sem duplicação.
- Release/report:`reports/finance-sms-dashboard-1557763144762269717.md`. Checkpoint:`ZEUS-FINANCE-SMS-DASHBOARD-1557763144762269717`. Relatos anteriores de dia07pendente foram supersedidos pelo readback dessa execução.
