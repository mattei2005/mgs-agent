# Fonte financeira SHEIN — investimento SB já ajustado

## Quando usar

Use para gerar, corrigir ou validar relatórios financeiros SHEIN, tanto agendados quanto avulsos, e para investigar diferenças entre o relatório e a dashboard Smart Bidding. Consulte a regra e sua vigência em `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/financial_source_standard`; autoridade, IDs e estado do rollout pertencem ao contrato/audit, não a esta receita.

## Procedimento

### 1. Resolver escopo, janela e semântica

- Resolva a origem no binding canônico e valide conta, domínio e autoridade. Para um pedido avulso em thread de conta, mantenha essa conta; não escolha uma amostra de outro gestor ou do lote de QA.
- Faça GET Meta de identidade/moeda/fuso antes das fontes financeiras e derive a data civil live. Registre separadamente a data financeira selecionada na SB e os horários reais de coleta; igualdade do texto `DATE` não demonstra igualdade de intervalos horários.
- Resolva a vigência da política pelo snapshot financeiro. Preserve replays anteriores; não reinterprete relatórios antigos pela regra nova nem apresente dados de QA como uma atualização recém-coletada.
- Confira o estado do produtor recorrente sem modificá-lo. Um avulso autorizado pode ser entregue com a recorrência suspensa; corrigir o código ou publicar essa amostra não reativa a agenda.

### 2. Coletar fontes homogêneas

- Use `Runner.collect_account()` e a fonte SB autorizada. A seleção financeira inclui atividade no dia SB mesmo sem entrega no dia Meta; não perca gastos próximos da virada por selecionar somente campanhas com Insights positivos na data Meta.
- Cruze SB por conta, campaign ID, data, publisher e moeda; preserve a granularidade real dos adgroups e rejeite duplicatas antes de somar.
- Após a vigência, use **INVESTIMENT + NET_REVENUE + REVENUE_ESTIMATED do mesmo retorno SB** para Gasto, Saldo, ROI, ROI E., histórico de sete datas e complementos. O investimento já contém o ajuste upstream; não aplique outro deslocamento horário.
- Preserve `meta_spend` no principal e no histórico para auditoria. B.U.% operacional conserva gasto bruto Meta/daily_budget atual; ROAS continua Meta. Identifique essas fontes distintas no relatório, sem trocar silenciosamente a fórmula de B.U.% para acompanhar o Gasto financeiro.
- Persista cada fonte com seu timestamp. Em coleta longa, separe unidades recuperáveis por conta ou batch limitado e salve cada uma ao terminar; manter todos os readbacks apenas em memória faz um timeout descartar leituras válidas. Retome só as unidades faltantes do mesmo request, sem chamar novamente a coleta financeira já congelada.

### 3. Materializar pelo ponto comum

A camada offline é `scripts/shein_financial_source.py` do profile Ares. `Runner.materialize()` chama:

```python
layout.apply_financial_source(model, sb_rows, layout.policy())
```

Reutilize esse ponto em vez de copiar um materializador antigo. Ao adaptar código anterior à troca de fonte, atualize também asserts e resumos: `spend` financeiro e histórico conferem com `INVESTIMENT`; `meta_spend` confere com Insights. Um assert herdado de soma Meta pode rejeitar corretamente o novo modelo sem indicar falha da SB. Corrija o adaptador, não o Markdown nem o gate.

Exija `financial_source` com hash das linhas SB sanitizadas, corte `source_timestamps.financial` igual ao da fonte SB, IDs exatos e coerência de métricas/histórico. Rode:

```python
layout.validate_financial_source(model, layout.policy())
```

Ausência de investimento resulta em Gasto/Saldo/ROI n/d, nunca fallback Meta. Zero SB explícito continua zero; sem denominador positivo, ROI é n/d. Totais e companions exigem cobertura completa: não executar `Decimal(row['spend'])` sobre n/d nem transformar soma vazia de receitas em zero. Gasto zero é admissível para seleção vazia validada.

### 4. Validar, revisar e entregar

- Rode `test_shein_report_financial_source.py` e as regressões renderer/Intraday/D-1. Cubra fonte ausente/zero, duplicatas, hash, histórico, preservação Meta/B.U./ROAS e replay anterior.
- Em testes offline de um produtor suspenso, use uma fixture explícita habilitada somente em memória para o caminho positivo e um teste negativo que prove bloqueio antes de API/transporte. Não reative produção para deixar a suíte verde nem aceite uma falha por suspensão como prova de outro gate.
- Faça QA live no universo autorizado e derive contagens dos pares conta/thread e campaign IDs efetivamente coletados; cardinalidades de outro lote não são critérios de aceitação. Confira cobertura da captura RPS e término da paginação.
- Renderize e valide com o renderer canônico. Revise o texto antes do POST e entregue as partes exatas com journal, nonce e GET de cada mensagem. Se já publicou pelo transporte, não repita o corpo na resposta nativa.
- Para afirmar equivalência com a dash, compare a parte financeira no mesmo recorte, moeda, configuração de revenue share e corte. Uma dash aberta depois pode ter avançado; B.U.% e ROAS de origem Meta não viram métricas SB por essa correção.

### 5. Fechar sem ampliar efeitos

Leia novamente contrato e estado dos schedulers antes de concluir. Preserve suspensões ou alterações autorizadas que outro pedido aplicou durante a execução; não restaure um crontab antigo só para recuperar o hash inicial. Separe no recibo correção instalada, QA realizado, relatório avulso efetivamente entregue e recorrência habilitada ou suspensa. Não reenviar/apagar relatórios anteriores nem ampliar destinos como efeito lateral.

Arquive somente fontes sanitizadas, modelos, relatórios e recibos por allowlist, com comparação de bytes/hashes; exclua sessões e credenciais. Mantenha a explicação técnica no audit e encerre na origem com cobertura, corte, moeda e limitações relevantes.
