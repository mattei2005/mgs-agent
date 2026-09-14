# Finance — preenchimento diário de gastos e exceções

## Regra ativa
- Autoridade atual: Rodolfo Mattei, mensagem `1549047147465281658`, thread `1545426987756298340`, em 2026-09-14.
- Preencher automaticamente na dashboard todos os gastos que tenham fonte, conta, site, moeda, data e valor confirmados.
- O Discord fica silencioso em sucesso rotineiro, cadastro/vínculo automático inequívoco e contas encerradas já conhecidas. Publicar diretamente somente a exceção que realmente precisa de confirmação de Rodolfo.
- Uma falha transitória na consulta detalhada de uma conta recebe uma repetição automática curta. Se persistir, preservar o valor anterior, nunca substituir por zero e publicar o bloqueio técnico exato; não pedir que Rodolfo diagnostique a API.
- Quando houver exceção, o embed informa primeiro que os demais gastos confirmados já foram preenchidos e lista somente os itens não confirmados. Totais rotineiros não ocupam a thread.
- Contas Google CANCELED/CLOSED continuam indisponíveis, nunca gasto zero confirmado, mas essa condição conhecida não gera aviso diário repetitivo.
- **Horário atual, supersessão1547235522055770142:** Rodolfo mudou de perto das7h para perto das9h Eastern. Agenda física `3 9 * * *` +25s =09:03:25 America/New_York (EST/EDT automático); primeiro minuto operacional livre próximo de09:00, informado na conversa. Substitui07:16+25s. Coleta, importação, vínculos, câmbio e janela do primeiro dia do mês de ontem até ontem não mudam. Fonte de horário: `data/finance-media-spend-contract.json`.
- A mudança não torna o gasto um fechamento definitivo: a API continuou revisando08/09 após09h. Preservar reconsulta dos dias anteriores; nunca ajustar centavos manualmente para imitar um print.
- Em09/09, atualização manual expressamente autorizada na mesma mensagem foi concluída:14sites/42campos ajustados,704registros, sem erros/exceções; readback e replay seco com zero alterações. Gasto08/09: MetaUSD15429.48 e GoogleBRL3520.169512. Aviso1547238158897516605 lido na thread. Evidência `apps/finance-system/private/nine-am-1547235522055770142/`.25testes e auditoria global8dias passaram; primeiro disparo natural das09:03 ainda futuro.
- O gate de execução agendada já concluída com sucesso no mesmo dia impede nova coleta/importação. Exceções usam assinatura estável para não repetir o mesmo pedido no mesmo estado.
- Execução manual continua silenciosa sem `--notify`; `--notify` continua disponível para uma comprovação explicitamente solicitada; dry-run bem-sucedido não publica.

## Supersessão explícita
A regra `1549047147465281658` substitui a confirmação curta após todo sucesso diário autorizada em `1547230494289174719`. Volta a valer o princípio de preencher automaticamente o que está comprovado e usar a thread apenas para a exceção que precisa de decisão, preservando alertas de falha técnica persistente. A política ainda mais antiga `1547016066645889074` permanece apenas como histórico.

## Runtime e validação
- Contrato: `data/finance-media-spend-contract.json`.
- Executor: `apps/finance-system/finance_media_spend_sync.py`.
- Renderer: `apps/finance-system/spend_report.py`.
- Testes: `apps/finance-system/tests/test_daily_spend_notice.py` mais suites existentes de sincronização/reporting.
- Evidência e backups: `apps/finance-system/private/daily-notice-1547230494289174719/`.
- 24 testes passaram; dois testes de confirmação diária falharam contra o código anterior em memória, demonstrando a regressão coberta.
- Em 2026-09-09 o recibo real da execução de 07:16 foi usado apenas para enviar o aviso; nenhum gasto foi reimportado. Mensagem `1547231402167373946` entregue e lida no destino exato.
- O primeiro disparo natural da nova política permanece futuro; o gate agendado foi exercitado em testes isolados e a entrega real foi validada.

## Procedimento seguro de comprovação
Usar o recibo `last_report_path` com `pass/readback` verdadeiros e o método `notice(report)` para teste de entrega sem importação. Adquirir o lock da sincronização, reconciliar o estado antes da chamada, salvar o ID/readback e atualizar somente os campos de notificação. Nunca reexecutar a coleta/importação apenas para testar Discord.
