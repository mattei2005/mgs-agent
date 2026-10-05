# Health — Smart Bidding Adgroup

Quando um operador pedir a coluna Health da dashboard, confirmar a definição no bundle vivo e no endpoint do mesmo relatório. Não supor que Health seja cobertura ou apenas uma razão limitada a 100%.

Na conta 13, o contrato canônico autoriza Health no Diário e Intraday; não projetar a alteração para outras contas ou estratégias sem escopo.

- O frontend Adgroup vivo usa o ID `ESTIMATED_HEALTH`, label `ESTIMATED HEALTH`, com `CDP_IMPRESSIONS` e `GAM_CODE_SERVED_COUNT`.
- Somar os dois contadores no mesmo grupo/período antes do cálculo: `x = ΣCDP_IMPRESSIONS × 100 ÷ ΣGAM_CODE_SERVED_COUNT`; resultado `max(0, x > 100 ? 200 − x : x)`. Nunca usar média simples dos percentuais. A penalização acima de 100% é parte da fórmula do provider.
- Contadores explicitamente presentes com denominador zero reproduzem o zero da dashboard. Linha inexistente, campo ausente, negativo ou não finito fica `n/d`, não zero inventado.
- Exibir `Health` com duas casas e `%`; registrar contadores, completude e fórmula no audit. Esse indicador não é ROI, CR Rewarded nem cobertura CDP.
- Health é diagnóstico de alinhamento CDP/GAM; sua inclusão não autoriza qualquer mudança nos gates de escala/corte.
- Preservar R/E, métricas existentes, resumo único, histórico ROI e paginação fence-aware. Testar razão abaixo/igual/acima de 100, piso zero, denominador zero, campo ausente e agregação ponderada.
- Reemissão manual usa `build_intraday(..., execute_actions=False)` / `--report-only`; validar conteúdo, contagem e chunks e exigir GET dos IDs publicados antes de concluir.

Fonte primária operacional: `reporting_presentation.smart_bidding_health` em `data/ares/meta-ads/operations/Creditoparaveiculo-BR-CAR-BR.json`. O audit apontado por esse contrato contém trecho literal e checksum da fonte pública do provider e probe API real.
