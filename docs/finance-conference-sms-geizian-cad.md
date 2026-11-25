# Conferência mensal: SMS, Geizian e spread automático CAD

## Autoridade e estado

- Rodolfo `1575019978305044612`, thread `1545426987756298340`: incluir o gasto SMS Funnel na Conferência mensal e depois liberar a consulta para Geizian, preservando o acesso de Rodolfo e as demais permissões.
- Rodolfo `1575021696442966117`, mesma thread: manter USD/BRL live menos 1% e acrescentar 2% no USD/CAD live.
- Publicado e validado: `reports/finance-conference-sms-geizian-cad-1575019978305044612.md`, release `conference-sms-1575019978305044612` committed. Continuidade: checkpoint `ZEUS-FINANCE-CONFERENCE-SMS-1575019978305044612`; evidências em `apps/finance-system/private/conference-sms-1575019978305044612/`.

## Conferência mensal

Supersede o limite de seis itens de `1551798171628212275` somente para acrescentar **Gastos SMS Funnel** como sétimo item. Preservar os quatro cartões de receita, Facebook e Google, moedas e descontos existentes.

- Mostrar consumo registrado em BRL, equivalente USD salvo, site, fonte e período coberto; não recargas/crédito pré-pago ou recibos de importação contados novamente.
- Ler os fatos calculados da competência e sua origem: `direct_monthly_cost`, `direct_daily_cost`, `sms_dashboard_reconciliation`. Variância oficial é assinada, não absoluta, e não deve ser atribuída a um gestor por inferência.
- Agosto/setembro têm o custo mensal SMS na dimensão histórica de mídia. O cartão identifica essa parcela já incluída em Gastos com mídia, sem reclassificar ou duplicar valor. Desde outubro, identificar a dimensão Despesas diretas SMS.
- Somente apresentação: nenhum lançamento, pagamento, comissão, fonte, resultado ou taxa é alterado para acrescentar o cartão. Ausência de dados permanece indisponível; consulta não confirma fechamento externo.

## Consulta exata de Geizian

Supersede `1551924862854107256` apenas para os recursos necessários à Conferência simples: `/review.html`, `/review.js`, `/review.css`, `/api/monthly-conference`.

- Permitir `rodolfo` com papel `owner` ou `geizian` com papel `partner`, ambos pela autenticação e elegibilidade existentes.
- Não conceder acesso a outros owners, partners ou gestores, nem permissões Discord/Zeus. Não mudar papel, senha, MFA ou sessão de Geizian.
- `/api/monthly-review`, `/api/monthly-trace`, `/api/period-preview` e `/period-preview.js` continuam exclusivos de Rodolfo, pois a tela simples não depende deles.
- Navegação, inicialização do cliente, servidor e visualização owner-preview devem concordar. Testar sessão ausente/revogada/desativada separadamente de usuário autenticado sem autorização.

## USD/CAD automático +2%

Supersede apenas o valor automático CAD sem spread na política `1552011536011108493`; independência da fonte técnica e precedência de taxas fixas permanecem.

- USD/BRL automático: `GOOGLEFINANCE("USDBRL") × 0,99`, já aplicado em B1 da planilha técnica. Não descontar novamente.
- USD/CAD automático: valor bruto `GOOGLEFINANCE("USDCAD")` de C1 multiplicado por **1,02**, uma vez no coletor `sync-quotes.py`. Validar fórmula bruta exata e registrar `raw_value`, multiplicador, percentual e autoridade na proveniência.
- Manter Google read-only, mesma SA/projeto, mesmo ID e fórmulas da planilha técnica, GBP e horários. Não reativar dependência de células de fechamento.
- Aplicar apenas onde a competência utiliza cotação automática; taxas `fixed`, inclusive CAD de outubro **1,44623**, continuam com prioridade e não recebem +2%.
- Usar publicação coordenada, coleta fresca, publicação de quotes e recálculo existente, com backup/readback e comparação de lançamentos/ledger/taxas fixas. Uma nova coleta deve partir da fonte bruta; nunca multiplicar o cache ajustado novamente.

## Comparação histórica de cotação

Para responder quanto a cotação mudou, consultar `audit_events` da competência, ator e chave exatos. Evento `7579`, `workspace-2026-10`, Rodolfo, 24/11/2026 15:16:46 Eastern: H1 de `1.4268049999999999` para `1.44623`, fixed/confirmed. A chave contém Agosto por compatibilidade; a competência real é outubro.

Comparar com Decimal: variação USD/CAD = `(novo/antigo - 1) × 100`; efeito sobre a receita USD de um mesmo montante CAD = `(antigo/novo - 1) × 100`. Não confundir aumento da taxa com aumento da receita ou com variação do lucro final. A consulta não autoriza mutação financeira.
