# Diagnóstico do saldo Geizian — outubro/2026

Pedido Rodolfo1575023523120947242, thread1545426987756298340. Consulta somente leitura; sem ajuste, pagamento ou recálculo persistido. Relaciona a pergunta anterior1575021020966813727 sobre CAD com as edições reais do fechamento.

## Fonte

- Banco e módulos produtivos da Dash, `finance_ledger`, `audit_events`, cenário `workspace-2026-10` revisão2173.
- Evidência privada: `apps/finance-system/private/conference-sms-1575019978305044612/geizian-diagnosis.json`, `geizian-bridge.json`, `fx-audit.json` e snapshot `workspace-2026-10.json`.
- Reexecução isolada do motor com o snapshot atual reproduziu a parte mensal de Geizian no centavo. Não representa restauração literal do screenshot ausente.

## Saldo lido

- Saldo anterior: R$49.598,65.
- Parte mensal realizada de outubro: R$765.132,89.
- Movimento de outubro: −R$9.686,81.
- Saldo: R$805.044,73.
- USD/BRL ainda automático em5,843475 no snapshot. CAD fixo1,44623. Valores podem mudar por cotação automática posterior.

## Ponte isolando as edições de outubro

Manter USD/BRL5,843475 e os mesmos fatos/ledger. Reverter apenas as taxas e despesas que têm before/after comprovados na auditoria; reaplicar sequencialmente CAD, inválidos e despesas pelo motor completo, incluindo o efeito nas remunerações.

- Antes dessas edições, com a dedução Amex já incluída: R$832.284,34.
- CAD1,426805→1,44623: −R$35.239,41 na parte de Geizian.
- Atualização de inválidos: +R$8.943,86.
- Despesas gerais: −R$944,06.
- Total líquido dessas edições: −R$27.239,61.
- Depois: R$805.044,73.

A mudança no CAD afeta a receita bruta em CAD antes dos custos; não é aplicada somente ao saldo ou lucro. A taxa USD/CAD subiu1,3614334%; um mesmo montante CAD passou a render1,3431474% menos USD. Variação percentual do lucro é outra medida.

## Movimento Amex independente

Audit7476, Rodolfo, `2026-11-24T04:11:13.975Z` (23/11 23:11 Eastern): ajuste negativo R$9.686,81 em outubro, descrição “50% juros do emprestimo do amex - a conferir”. Dependendo do horário do print, pode já estar incluído nele. Não somá-lo à queda27.239,61 por inferência. Nenhuma alteração ou confirmação desse lançamento foi feita.

## Limite e próxima evidência

Rodolfo informou aproximadamente835mil→805mil, sem enviar o screenshot neste turno. A composição principal está demonstrada, mas o delta exato do screenshot depende do valor, competência e horário capturados, inclusive USD/BRL automático naquele instante. Solicitado screenshot com horário. Não chamar a reconstrução a câmbio constante de saldo histórico literalmente observado; não atribuir toda diferença ao CAD, SMS ou a novo pagamento.

Os novos pedidos SMS/Geizian e spread CAD automático+2% estavam em validação isolada quando essa leitura foi feita; não causaram a queda já vista. A nova regra automática não altera o CAD fixo de outubro.
