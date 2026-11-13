# Datas fechadas em relatórios pontuais SHEIN

## Contrato e execução

- Resolva primeiro a janela pela identidade e pelo timezone Meta live, mesmo quando o catálogo sugerir outro fuso. Uma data explícita não muda por uma atualização do catálogo.
- Diferencie seleção de agenda de autorização pontual: a exclusão de Boostingecon/Growpowerhub do cron D-1 não exclui seus bindings de um pedido humano autorizado de relatório fechado.
- Para data fechada explícita fora do subconjunto/semântica da agenda D-1, use `closed_day_report={kind:'on_demand', source_message_id:<ID literal>, period:{since:day,until:day}, day_closed:true}` no modelo. Não invente policy_id D-1, não retrodate a coleta e não desabilite gates.
- Antes da renderização, persista pelo GET da própria identidade a mensagem humana e a origem/pai reais em `data/ares/meta-ads/reports/shein-on-demand-requests/<message_id>/authorization-readback.json`, com `message` (id, channel_id, author, content, timestamp), `origin` (id, parent_id, type) e observed_at. Ao lado, preserve `request.json` com data explícita, source_message_id/source_thread_id, requester_discord_id, request_text literal, bindings canônicos exatos, mode=on_demand_read_only e meta_writes=0. Essas provas não contêm credenciais.
- O renderer verifica autor humano autorizado, origem individual ou multicontas G006 canônica, pai real, binding exato, igualdade entre texto/prova/request e a única data literal pedida. Para pedido de Rodolfo numa thread do canal geral SHEIN que diga todos os canais, o ramo global exige operation_id=SHEIN-US-DIRECT, scope=all36_account_threads e igualdade integral dos 36 bindings canônicos, sem duplicatas. Nesse ramo, “dia fechado de ontem” resolve pela data da mensagem autenticada no fuso Meta live da conta; preserve timestamp, timezone e data resolvida, rejeitando data literal conflitante. Isso não inclui gestores, outras origens, subconjuntos ou reativação da agenda por inferência. Ausência ou divergência continua fail-closed; nomes de arquivo ou IDs locais sozinhos não demonstram autorização.
- Mantenha financeiro com timestamp real posterior ao fechamento, orçamento consultado na mesma data de coleta ou depois e todas as sete células históricas sem parcial. Preserve no último dia exatamente os valores do principal.
- Use o cabeçalho canônico `Relatório pontual`, dia fechado e `ATRASO GAM/SB ATUAL`. Status/Bid/budget/delay atuais nunca representam estado histórico. B.U.% continua gasto do dia solicitado dividido pelo budget vigente explicitamente datado.
- Reutilize fontes já concluídas do mesmo request quando a correção for somente de materialização/gate; não recolete nem publique duas vezes. Revise o texto e os complementos ativos antes de entregar, com journal/nonce/GET de todas as partes.

## Verificação

Execute `python3 -m unittest discover -s /root/.hermes/profiles/ares/tests -p 'test_shein_report*.py' -q`. `test_shein_report_on_demand_closed.py` cobre prova positiva, data mais antiga, dia aberto, budget antigo, autor/bot, origem/pai, binding errado, parcial, data divergente, seis bindings G006 e integração do renderer sem mutação financeira. O ramo D-1 recorrente e seus testes permanecem inalterados.

Manutenção do renderer exige inventário, rollback, testes e REPORT-INFRA; isso não altera agendas, campanhas, budgets nem permissões remotas. Preserve a prova no armazenamento durável para que a expiração do scratch não impeça o replay autorizado.
