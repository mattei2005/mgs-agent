# Fincgriffin — receita GAM USD na conferência mensal

## Decisão ativa
Rodolfo1575648329847799909, thread1545426987756298340, confirmou que a receita USD do Fincgriffin em novembro pertence à SB Rede2: Rede1 corresponde à receita CAD e Rede2 à receita USD no fluxo Smart Bidding discutido.

Escopo executável: **Conferência mensal**, Fincgriffin, receitas diárias com origem GAM-email comprovada em USD, novembro/2026 em diante. Persistir a classificação para novas ocorrências da mesma origem, sem exigir nova classificação mensal. A regra pontual de setembro1551931759061631058 permanece preservada; agosto/outubro e outros sites não são alterados por esta decisão.

Não generalizar todo USD para Rede2: AV e M2 também possuem USD. `source_components` e `source_network` explícitos mantêm precedência. Exigir data da competência, source_import_type gam_email_daily, source_import_id correspondente à data, ID Fincgriffin coincidente e hashUSD válido. Origem manual/ilegível permanece pendente.

## Efeito e limites
A correção agrupa a receita já registrada no cartão Gross USD · Rede2. Não reimporta, converte moeda, altera cadastro mensal, invalids/revshare, cálculos de lucro, comissões, pagamentos ou fatos originais. `partner=SB Rede1` herdado no cálculo não é prova da rede da origem importada; distinção de apresentação preserva os cálculos vigentes.

Diagnóstico inicial: workspace2026-11 revisão1063,34linhas não zero, datas01–25/11, totalUSD25.910847565314000422, exibido25,91. O agrupador anterior aceitava SB Rede1 somente com CAD e possuía exceção FincgriffinUSD somente para setembro, deixando novembro no aviso de origem não identificada.

## Verificação e publicação
Fonte de estado: checkpoint `ZEUS-FINANCE-FINC-REDE2-1575648329847799909`. Evidências em `apps/finance-system/private/finc-rede2-1575648329847799909/`. Aprovação/este documento não substituem o readback de publicação.
