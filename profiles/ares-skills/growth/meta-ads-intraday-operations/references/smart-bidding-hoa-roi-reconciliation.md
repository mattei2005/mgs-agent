# Smart Bidding × Meta — ROI no HOA

## Quando usar

Use esta referência ao adicionar, validar ou investigar ROI em relatórios HOA Messenger. O objetivo é reconciliar receita do Smart Bidding com spend real da Meta sem transformar cashflow em atribuição de coorte.

## Fontes e identidade

- Spend: Meta Insights, no nível das campanhas pertencentes à página em foco.
- Receita: Smart Bidding `/report/messenger`.
- Chave principal: `UTM_CAMPAIGN == pg_id`, complementada por `ACCOUNT_NAME`, `DOMAIN`, `COUNTRY`, `VERTICAL`, período, moeda e timezone.
- Campos de receita:
  - Drip: `DRIP_REVENUE`
  - Broadcast: `BD_REVENUE`
  - Total: `REVENUE`
- Não calcular Total como Drip + Broadcast: pode existir residual legítimo. Usar sempre `REVENUE` para ROI Total.
- O campo histórico `INVESTIMENT` do Smart Bidding pode vir zerado ou apenas com o dia atual. O denominador canônico é o spend Meta reconciliado.

## Fórmula

```text
ROI = (receita - spend Meta) / spend Meta × 100
```

Se spend for zero, ROI é indisponível. Se não houver linha Smart Bidding para a data/chave, mostrar dado indisponível; nunca converter ausência de linha em receita zero.

ROI Drip e ROI Broadcast, quando calculados separadamente, usam individualmente o spend Meta completo. Eles não são aditivos. ROI Total é calculado diretamente com `REVENUE`.

## Consulta histórica por data

Para uma tabela diária:

1. Consultar Meta Insights uma vez para todo o intervalo, com `time_increment=1`.
2. Consultar Smart Bidding para o intervalo completo, não uma chamada isolada por dia.
3. Na API observada, aquecer/consultar primeiro `/report/messenger_insights` e depois `/report/messenger` com o mesmo payload. Uma chamada isolada a `/report/messenger` pode devolver somente o dia atual mesmo quando o intervalo contém histórico.
4. Agrupar a resposta Smart Bidding por `DATE`.
5. Filtrar e reconciliar cada dia pela identidade completa da operação/página.
6. Validar `matched_rows`, datas retornadas e moeda antes do cálculo.
7. Marcar o dia atual como parcial e usar o timezone da conta Meta, não o timezone do VPS.

### Invariante de data exata no HOA diário

Para qualquer consulta de um único dia, aplicar `row.DATE == report_date` **antes** de somar `DRIP_REVENUE`, `BD_REVENUE` ou `REVENUE`. O endpoint `/report/messenger` pode devolver linhas de D-1 mesmo quando o payload pede somente D0; nunca assumir que o intervalo solicitado limita as datas retornadas.

- `matched_rows` conta apenas linhas da data exata e da identidade completa.
- Datas inesperadas ficam no audit como `unexpected_dates`, mas não entram em receita nem ROI.
- Se nenhuma linha da data exata existir, retornar dado indisponível; não reaproveitar D-1 nem converter ausência em zero.
- Em recheck histórico, receita pode maturar e mudar; registrar horário da consulta e não comparar snapshots sem declarar essa limitação.

### Evidência visual no dashboard

Ao comprovar a origem por screenshot em `Reports → Messenger Daily`:

1. Usar o timezone da conta no contexto do navegador.
2. Isolar um único site/domínio, `Group by = UTM_CAMPAIGN`, filtro do `pg_id`, moeda e coluna da data.
3. Para Total, usar a métrica geral `REVENUE`; para Drip, selecionar `DRIP → REVENUE`. Como o seletor mostra apenas `REVENUE` após fechar, manter o menu aberto ou rotular a captura sem alterar os valores.
4. Comparar a célula da data com a linha crua de mesma `DATE`; não usar o `Total` de uma janela multidiária.
5. Se o screenshot divergir do HOA, interromper a apresentação como válida e reconciliar as linhas por data antes de qualquer correção de script.

## Semântica do relatório

Esse cálculo é ROI de **cashflow diário da página**, não ROI de coorte. Broadcast pode maturar em D+1 ou depois, e receitas do dia podem vir de leads adquiridos anteriormente. Portanto:

- ROI é inicialmente informativo e não aciona pause, reactivation ou replacement.
- Para decisão, preferir janelas fechadas/rolling depois de validar maturação e estabilidade.
- Preservar receita e ROI Broadcast no JSON/audit mesmo quando não exibidos no Discord.

## Layout OpenzedFinanzas aprovado por Rodolfo

No HOA da operação OpenzedFinanzas-CC-ES, o bloco visível deve mostrar:

```text
PG | Spend | Receita Drip | Receita Total | ROI Drip | ROI Total | Status
```

Os valores de spend e receita devem indicar a moeda no título do bloco. Não exibir `Receita Broad` nem `ROI Broad`. Rodolfo investiga separadamente a receita Broadcast; `BD_REVENUE`, a receita Broadcast e o ROI Broadcast permanecem no audit técnico.

Para tabela histórica por data, usar o formato compacto:

```text
Data | Spend | M0 | CPM0 | ROI Drip | ROI Total
```

Evitar repetir ROI em cada campanha quando a receita só é atribuível à página/PG. Um bloco separado por página impede falsa atribuição por campanha.

## Autenticação e segurança

- Credenciais vêm do item autorizado do 1Password e nunca entram em output, audit ou argumentos visíveis.
- Fluxo validado: Auth0 Authorization Code + PKCE.
- Cache de access token deve ser local, `0600`, com expiração e refresh/login fail-closed.
- Auditoria pode registrar item, comprimento do token e origem do cache, nunca o token.

## Verificação mínima

- Testar fórmula com receita acima, abaixo e spend zero.
- Confirmar que o bloco Discord contém `ROI Drip` e `ROI Total` e não contém `ROI Broad` para Openzed.
- Confirmar que o JSON mantém `broadcast_revenue` para investigação.
- Testar resposta single-day contendo D0 + D-1 e provar que somente `row.DATE == report_date` entra em receita, `matched_rows` e ROI; preservar datas extras em `unexpected_dates`.
- Em screenshot, validar site único, `UTM_CAMPAIGN`, `pg_id`, moeda, coluna da data e caminho da métrica (`REVENUE` ou `DRIP → REVENUE`) antes de apresentar a imagem como evidência.
- Validar ausência de `access_token`, `password`, `username`, `id_token` e valores reais de credencial em output/report.
- Rodar geração live read-only e poster Discord em dry-run; validar fences balanceados e chunks dentro do limite.
- Confirmar que target CPMO, R1–R5, budget e modo Meta write não mudaram quando o escopo era somente reporting.
