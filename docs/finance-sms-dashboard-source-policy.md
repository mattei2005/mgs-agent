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

Este registro é a regra institucional, não um comprovante de conclusão de07/10, nova importação, seleção visual de uma tela ou publicação de um novo coletor. Nesta tarefa de registro não foram modificados os executores financeiros nem lançados valores. O checkpoint `ZEUS-FINANCE-ALERT-1557727865750159482` conserva separadamente o estado da conciliação pendente.
