# Fonte financeira SHEIN — investimento SB já ajustado

## Regra vigente

Rodolfo autorizou na mensagem `1570801675239694367`, thread `1558146784554000467`, a correção de todos os próximos relatórios SHEIN, agendados e avulsos. Fonte única: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/financial_source_standard`. Após a vigência financeira registrada, Gasto, Saldo, ROI, ROI E., histórico de sete datas e complementos usam **INVESTIMENT + NET_REVENUE + REVENUE_ESTIMATED da mesma fonte SB**, cruzados por conta/campanha/data/moeda. O investimento já contém o ajuste de calendário upstream; não deslocar horas novamente nem reconstruir uma diferença fixa NY/Brasília. A regra substitui trechos históricos que usam gasto Meta no denominador financeiro, preservando snapshots anteriores à vigência.

## Camada comum e gate

A camada comum é `scripts/shein_financial_source.py` do profile Ares. `Runner.collect_account()` preserva também campanhas com atividade no dia financeiro SB, mesmo sem entrega no dia Meta; `Runner.materialize()` chama `layout.apply_financial_source(model, sb_rows, layout.policy())` antes de salvar/renderizar. O renderer exige proveniência `financial_source`, hash das linhas SB sanitizadas, corte `source_timestamps.financial` igual ao SB e coerência das métricas/histórico. Adaptadores avulsos reutilizam esses pontos, não um materializador antigo. Ao copiar código anterior ao cutover, trocar também seus asserts/resumos: Gasto financeiro e histórico são conferidos contra `INVESTIMENT` SB, não contra Insights; `meta_spend` é que conserva a soma Meta. Não editar Markdown nem remover o gate para acomodar um assert herdado. Modelo financeiro novo sem prova é bloqueado.

Ausência de investimento deixa Gasto/Saldo/ROI n/d, sem fallback Meta; zero SB explícito continua zero, mas ROI sem denominador positivo é n/d. Totais e companions usam soma com cobertura completa: não executar `Decimal(row['spend'])` sobre n/d; total n/d se algum gasto selecionado estiver ausente, e gasto zero somente para seleção vazia validada.

## Campos preservados

Meta bruto fica em `row.meta_spend` e `history.meta_spend` para auditoria. **B.U.% operacional mantém a regra Meta vigente** (gasto bruto Meta/daily_budget atual), identificado como fonte distinta do Gasto financeiro SB; ROAS continua Meta. Não converter a correção em mudança silenciosa de B.U.%, budget, timezone, agenda, destinos, suspensão ou ampliação de contas. Reativar Intraday suspenso exige sua autorização própria. Recorrência mantém o subconjunto contratado; a regra financeira cobre todos os bindings avulsos autorizados. Não reenviar/apagar relatórios antigos por este cutover.

## QA e continuidade

Executar `test_shein_report_financial_source.py`, regressões renderer/Intraday/D-1 e coleta read-only: fonte/recorte SB, ausente/zero, duplicatas, hash, preservação Meta/B.U./ROAS, cobertura dos bindings e replay histórico. Fixtures offline não são consultas live. Preservar agenda e suspensão reais durante os testes.
