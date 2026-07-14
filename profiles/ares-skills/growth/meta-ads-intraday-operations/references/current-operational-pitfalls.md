# Pitfalls operacionais atuais

Este arquivo preserva literalmente os pitfalls extraídos do `SKILL.md` em 2026-07-13. Retries citados abaixo permanecem subordinados ao limite obrigatório definido no `SKILL.md`.

## Pitfalls

- Quando Rodolfo pedir ação no canal do Zeus, mencionar explicitamente o bot Zeus (`<@1496296175014252634>`); mensagem sem mention pode não ser lida/acionada pelo Zeus.
- Não confundir controlled-write explícito de setup com autorização geral para write/autonomia; registrar escopo exato aprovado, rodar dry-run, validar por GET e manter os crons de gestão em read-only até nova aprovação.
- Antes de liberar qualquer regra de custo para write, normalizar a taxonomia real de bid strategy. A Meta pode retornar `LOWEST_COST_WITHOUT_CAP`, enquanto rulesets históricos usam `LOWEST_COST`; o matcher deve mapear ambos para a mesma estratégia lógica ou aceitar explicitamente os dois valores. Dry-run sem candidatos não prova que R4 está funcional.
- A rota CLI histórica `reactivate-all` agora é apenas compatibilidade de nome para o passe seguro das 00:30. Mesmo em dry-run, só pode gerar candidato com state persistido `paused_by_ares_rule`; `paused_by_human`, histórico, saturação, hold e proveniência desconhecida são bloqueados. Aplicar também gate de quantidade ativa, budget configurado e projeção de gasto contra o cap da conta.
- Para ROI Messenger via Smart Bidding, os endpoints `/report/messenger` e `/report/messenger_insights` podem expor `DRIP_REVENUE`, `BD_REVENUE` e `REVENUE`. Usar gasto Meta reconciliado como denominador quando `INVESTIMENT` histórico do SB estiver ausente/zero, unir por `pg_id`/`UTM_CAMPAIGN` + conta + período/timezone e rotular o resultado como cashflow quando não houver coorte de aquisição.
- Para ROI histórico por data no Smart Bidding, consultar o intervalo completo e agrupar por `DATE`; não fazer apenas uma chamada isolada por dia. Na API observada, `/report/messenger` retornou somente o dia atual quando chamado sozinho, enquanto a sequência `/report/messenger_insights` seguida de `/report/messenger` para o mesmo intervalo devolveu o histórico completo da página. Validar `matched_rows` e datas antes de calcular ROI; ausência de linha deve aparecer como dado indisponível, nunca como receita zero.
- Antes de executar pedidos como “deixar 20 campanhas”, validar quantas campanhas existem no escopo ativo e esclarecer se deve duplicar, reativar pausadas ou limitar ao escopo atual; não assumir.
- Não inferir CPS sem validar qual campo da Meta corresponde ao subscriber real.
- Não confundir timezone do VPS com timezone da conta; crons finais devem respeitar a conta.
- Não pausar campanha TEST dentro dos 3 dias mesmo se regra disparar.
- Não usar teto de R$1.500 como kill switch; por decisão atual ele é referência para planejamento e deve ser convertido usando USD/BRL do dia porque a conta está em USD.
- Para pedidos de HOA histórico ou separação de relatórios, não reaproveitar a thread intraday por conveniência. Separar `Intraday` e `HOA` por thread fixa/diária; enviar dias passados com `--report-date YYYY-MM-DD --checkpoint-time 22:00` para representar o dia completo; validar membros da thread e retry em `429` antes de reportar sucesso. Ver `references/hoa-thread-routing-historical-reports-and-mobile-layout-2026-06-22.md`.
- Não enviar tabelas recorrentes largas no Discord/mobile. Compactar IDs, campanha e motivo no display (`REC001`, `Elena ES ESP 013`, `Learning<3d; R2`) e manter detalhes completos no audit JSON. Validar o poster em dry-run para evitar `Parte 1 de 3`/chunking feio quando possível.
