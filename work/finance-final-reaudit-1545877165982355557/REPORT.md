# Reauditoria integrada final — Agosto 2026

Estado: integrated_financial_checks_PASS_documentation_followup_open
Pedido: 1545877165982355557 | thread 1545426987756298340

## Cobertura integral
- principal:CAIXA SINTETICO: 749 células; 549 fórmulas; última linha/coluna com conteúdo [81, 18]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- principal:Agosto 2026: 58721 células; 50774 fórmulas; última linha/coluna com conteúdo [338, 1105]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- principal:BASE_DASH: 3155 células; 1484 fórmulas; última linha/coluna com conteúdo [154, 22]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- principal:DASH EXECUTIVO: 270 células; 12 fórmulas; última linha/coluna com conteúdo [85, 10]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- kelly:Agosto 2026: 3592 células; 49 fórmulas; última linha/coluna com conteúdo [241, 36]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- isliago:Agosto 2026: 5149 células; 61 fórmulas; última linha/coluna com conteúdo [315, 36]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- george:Agosto 2026: 5370 células; 67 fórmulas; última linha/coluna com conteúdo [353, 36]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- nicolas:Agosto 2026: 5423 células; 61 fórmulas; última linha/coluna com conteúdo [316, 54]. A leitura cobriu a aba inteira, não apenas a extensão histórica.
- joe:Agosto 2026: 3033 células; 44 fórmulas; última linha/coluna com conteúdo [242, 36]. A leitura cobriu a aba inteira, não apenas a extensão histórica.

## Validação
{
  "workbooks": 6,
  "tabs": 9,
  "cells": 85462,
  "formulas": 53101,
  "automatic_formula_recomputations_pass": 53085,
  "special_dashboard_formulas_independently_checked": 6,
  "observed_volatile_provider_formulas": 10,
  "import_formulas": 83,
  "exact_import_cells": 29058,
  "exact_import_mismatches": 0,
  "support_cells": 406,
  "displayed_errors_final": 0,
  "readback_changed_cells": 0,
  "charts": 4,
  "site_segments": 43,
  "country_source_segments": 78
}
{
  "semantic-checks": 25399,
  "spend-calendar-checks": 3318,
  "integrated-checks": 6514,
  "dashboard-independent-checks": 2639,
  "provider-continuity-checks": 83,
  "calendar-scenarios": 2240
}

As fórmulas automáticas foram recalculadas usando precedentes capturados; os testes semânticos reconstruíram componentes independentemente, inclusive totais zero/inativos, moedas, países, lower blocks e distribuição de custos. IMPORTRANGE teve comparação estrita célula a célula, inclusive blanks. Recaptura final: nenhuma mudança de fórmulas, valores efetivos, formatação numérica exibida ou notas; metadados dos gráficos e 406 dependências de apoio também permaneceram iguais.

## Achados / observações
{
  "id": "R01",
  "type": "confirmed_documentation_error",
  "state": "open_no_write_authorization",
  "scope": "BASE_DASH!V123:V153",
  "cells": 31,
  "description": "Source text still points to former AOW:APE global block. Financial formulas correctly reference current APE:APM; no financial impact.",
  "evidence": "dashboard-findings.json"
}
{
  "id": "R02",
  "type": "metric_definition_difference",
  "state": "clarification_not_arithmetic_error",
  "scope": [
    "CAIXA SINTETICO!J79",
    "DASH EXECUTIVO!A8",
    "BASE_DASH!U154",
    "Agosto 2026!APM36"
  ],
  "description": "Cash/dashboard ROI = net profit / media spend; August global ROI = postshare net / all costs - 1. Same ROI líquido label but different bases. Preserve calculations; recommend specific labels rather than automatic formula harmonization.",
  "values": {
    "cash_dashboard": 0.11928283131511075,
    "august_global": 0.10697322673926557
  }
}

## Valores reconciliados
{
  "cash_half_brl": 90840.87777065401,
  "august_half_brl": 90840.87777065428,
  "profit_usd": 35799.79805493349,
  "gross_usd": 413606.3690640221,
  "media_spend_usd": 300125.3211399784
}

## Limites e ressalvas
- Financial internal consistency and current recorded values, not audit against every bank/partner receipt.
- August remains PROVISORIO; 10 live GOOGLEFINANCE-derived formula outputs observed and sanity checked, not independently priced against external market feed.
- O121:P121 preserved per Rodolfo confirmation; manual USD/BRL difference is not declared a new accounting error.
- Chart data ranges, source series and current query outputs verified by API; no claim of visual rendering inspection.
- All live current filter outputs validated; alternate filter cases tested locally only to preserve read-only authorization.
- Initial George import loading state was transient; retry and final capture both zero errors.

## Escopo de escrita
Nenhuma escrita Google realizada. Apenas capturas, validadores locais, registro de auditoria, checkpoint, inventário e documentação procedural.

## Histórico
Os 19 achados anteriores foram rechecados no estado atual; F17 permanece encerrado pela decisão do responsável. O resultado atual supersede final_integrated_audit_pending como auditoria executada, mas não equivale a fechamento financeiro cambial nem encerra a pendência documental R01.
