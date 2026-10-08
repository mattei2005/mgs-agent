# Finance — preenchimento diário de gastos e exceções

## Regra ativa — Rodolfo1557727865750159482, detalhada em1557733120655101973 e1557733965119361075

- Uma mensagem normal, curta, em primeira pessoa nesta thread, com **Problema, Causa e Solução**. Sem nomes de exceções, etapas internas ou alertas genéricos. Causa ainda não provada deve ser apresentada como desconhecida, não presumida.
- Não repetir o mesmo problema/data por mudança de horário, execução ou tentativa. O GAM não deve duplicar o alerta de gastos quando a entrega anterior estiver comprovada. Falha de entrega permanece recuperável; deduplicação não equivale a sucesso financeiro.
- Perguntas servem para dúvidas reais de preenchimento depois de consultar as decisões já registradas. O total oficial do SMS Funnel já é a fonte aprovada; não pedir que Rodolfo escolha essa fonte novamente nem que escolha um gestor para compensação sem reconciliar a evidência disponível. Preservar o total oficial, a atribuição comprovada e a divergência não conciliada, sem fechar falsamente o dia.

- Separar falha técnica de decisão humana. Falhas de coleta, validação, integração ou gravação são responsabilidade de Zeus; identificar o estado parcial/não confirmado e informar explicitamente quando não há decisão solicitada a Rodolfo. Nunca pedir genericamente “decisão/conferência” por um `source_error`.
- Pedir resposta somente para vínculo/classificação realmente ambíguos ou conflito com valor manual, em itens numerados com a pergunta exata. Em alerta misto, manter a seção técnica separada da seção de decisão.
- Contas Google encerradas já conhecidas e cadastros automáticos bem-sucedidos não devem poluir o aviso de falha. Permanecem na auditoria, nunca viram gasto zero.
- No GAM, uma interrupção na etapa anterior de gastos/SMS significa que a aplicação de receita não foi iniciada **naquela tentativa**, não uma gravação de receita incerta. Preservar incerteza real quando a falha acontecer em aplicação/verificação. Nunca afirmar “recuperação esgotada” sem evidência.
- Esta correção supersede somente a redação ambígua da política1553778586807304213. Mantém confirmação conjunta depois de gastos, SMS aplicável e receita verificados, bloqueio de fechamento parcial, autoridade financeira, retries, backups e deduplicação.
- Publicação/validação: checkpoint `ZEUS-FINANCE-ALERT-1557727865750159482`; evidência em `apps/finance-system/private/alert-clarity-1557727865750159482/`. A decisão não equivale a publicação; consultar o journal/readback.

## Política-base preservada — Rodolfo1553778586807304213

- Confirmar nesta mesma thread a conclusão de gastos **e** receita em uma mensagem normal, com a data preenchida e conferida; o orquestrador GAM emite a confirmação conjunta após validar ambos. A etapa isolada de gastos não deve afirmar que a receita está completa.
- Em erro ou parcial, explicar em texto normal o que falhou, o que foi preenchido e o que falta; incluir pergunta exata **somente quando houver decisão humana real**, conforme a correção ativa acima. Preservar recuperação automática segura. Sem embeds, cartões ou blocos de código; não truncar exceções.
- Deduplicar a confirmação por data/fonte. Falha de entrega não é falha financeira e deve ser retomada sem reimportação.
- Esta decisão supersede o silêncio em sucesso de1549047147465281658 e o formato embed legado; preserva partição, atribuição, datas, moedas, horários e regras de contas encerradas.
- Implementação e evidência desta mudança: `reports/finance-daily-status-1553778586807304213.md`.

## Histórico — política anterior superseded
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

## Supersessão histórica (substituída acima)
A regra `1549047147465281658` substitui a confirmação curta após todo sucesso diário autorizada em `1547230494289174719`. Volta a valer o princípio de preencher automaticamente o que está comprovado e usar a thread apenas para a exceção que precisa de decisão, preservando alertas de falha técnica persistente. A política ainda mais antiga `1547016066645889074` permanece apenas como histórico.

## Runtime e validação
- Contrato: `data/finance-media-spend-contract.json`.
- Executor: `apps/finance-system/finance_media_spend_sync.py`.
- Renderer: `apps/finance-system/spend_report.py`.
- Testes: `apps/finance-system/tests/test_daily_spend_notice.py` mais suites existentes de sincronização/reporting.
- Cutover `1549047147465281658`: a consulta parcial de `Creditoparaveiculo-BR-CAR-BR-06-G004` foi repetida automaticamente no mesmo turno e recuperou. Readback final até `2026-09-13`: `last_status=ok`, 0 source/discovery/query errors, 34 contas Meta com gasto e 2 Google; USD `204279.39` e BRL `48488.856745` gravados, cenário revisão 190. O código novo repete uma falha detalhada uma vez e não publica sucesso rotineiro.
- Validação integral após a supersessão: 143 testes Node e 99 Python passaram; o teste direcionado cobre sucesso agendado silencioso, exceção com atenção, retry automático e falha de entrega sem falso sucesso.
- Evidência e backups: `apps/finance-system/private/daily-notice-1547230494289174719/`.
- 24 testes passaram; dois testes de confirmação diária falharam contra o código anterior em memória, demonstrando a regressão coberta.
- Em 2026-09-09 o recibo real da execução de 07:16 foi usado apenas para enviar o aviso; nenhum gasto foi reimportado. Mensagem `1547231402167373946` entregue e lida no destino exato.
- O primeiro disparo natural da nova política permanece futuro; o gate agendado foi exercitado em testes isolados e a entrega real foi validada.

## Procedimento seguro de comprovação
Usar o recibo `last_report_path` com `pass/readback` verdadeiros e o método `notice(report)` para teste de entrega sem importação. Adquirir o lock da sincronização, reconciliar o estado antes da chamada, salvar o ID/readback e atualizar somente os campos de notificação. Nunca reexecutar a coleta/importação apenas para testar Discord.
