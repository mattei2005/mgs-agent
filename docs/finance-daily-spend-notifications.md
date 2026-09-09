# Finance — confirmação diária de gastos

## Regra ativa
- Autoridade: Rodolfo Mattei, mensagem `1547230494289174719`, thread `1545426987756298340`, em 2026-09-09.
- Enviar uma confirmação curta nesta thread após cada execução diária agendada, inclusive quando tudo deu certo e não houve novos cadastros ou pendências.
- Sucesso rotineiro: embed compacto sem mention, com data-limite dos gastos, período conferido, quantidade de sites alterados (ou nenhuma alteração necessária) e link ao Relatório Diário.
- Novas contas, vínculos e pendências mantêm o detalhe operacional. Erros continuam com alerta de atenção; não mascarar falha como sucesso.
- Contas Google CANCELED/CLOSED continuam indisponíveis, nunca gasto zero confirmado. O aviso curto preserva essa ressalva quando presente.
- **Horário atual, supersessão1547235522055770142:** Rodolfo mudou de perto das7h para perto das9h Eastern. Agenda física `3 9 * * *` +25s =09:03:25 America/New_York (EST/EDT automático); primeiro minuto operacional livre próximo de09:00, informado na conversa. Substitui07:16+25s. Coleta, importação, vínculos, câmbio e janela do primeiro dia do mês de ontem até ontem não mudam. Fonte de horário: `data/finance-media-spend-contract.json`.
- A mudança não torna o gasto um fechamento definitivo: a API continuou revisando08/09 após09h. Preservar reconsulta dos dias anteriores; nunca ajustar centavos manualmente para imitar um print.
- Em09/09, atualização manual expressamente autorizada na mesma mensagem foi concluída:14sites/42campos ajustados,704registros, sem erros/exceções; readback e replay seco com zero alterações. Gasto08/09: MetaUSD15429.48 e GoogleBRL3520.169512. Aviso1547238158897516605 lido na thread. Evidência `apps/finance-system/private/nine-am-1547235522055770142/`.25testes e auditoria global8dias passaram; primeiro disparo natural das09:03 ainda futuro.
- O gate de execução agendada já concluída com sucesso no mesmo dia impede aviso duplicado. A assinatura igual à do dia anterior não suprime a confirmação do novo dia.
- Execução manual continua silenciosa sem `--notify`; dry-run bem-sucedido não publica confirmação.

## Supersessão explícita
A política anterior, autorizada para o destino em `1547016066645889074`, notificava apenas novos cadastros/vínculos e exceções acionáveis. O sucesso diário silencioso está substituído pela regra acima; o destino e os alertas de erro são preservados. Referências históricas a avisos apenas por exceção não são a regra atual.

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
