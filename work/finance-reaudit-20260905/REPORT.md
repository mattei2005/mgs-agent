# Reauditoria financeira Agosto 2026 — 2026-09-05

Autorização: Rodolfo, mensagem1545832349957234688, thread1545426987756298340.

**Resultado: FAIL semântico. Varredura diagnóstica concluída; nenhuma correção nas planilhas foi executada.**

## Cobertura
{
  "books": 6,
  "tabs": 7,
  "cells": 81799,
  "formulas": 51377,
  "displayed_errors": 0,
  "formula_recompute": {
    "pass": 51367,
    "unsupported": 10
  },
  "manager_spill_cells": 29058,
  "semantic_tests": 31329,
  "findings_by_class": {
    "confirmed_error": 13,
    "latent_formula_gap": 2,
    "metric_definition_review": 1,
    "label_error": 1,
    "reporting_gap": 1,
    "business_evidence_needed": 1
  },
  "google_writes": 0,
  "initial_final_entered_deltas": 0,
  "initial_final_effective_deltas": 0
}

Leitura completa das abas Agosto 2026 e CAIXA SINTETICO da principal e Agosto 2026 dos cinco gestores ativos. API Sheets pelo helper/SA canônico, inclusive células ocultas/filtradas. Gustavo não integra o escopo ativo. As sete abas foram relidas integralmente ao final: nenhum delta de fórmula, valor digitado ou valor efetivo.

As fórmulas foram inventariadas e reavaliadas uma a uma sobre seus precedentes capturados. As dez GOOGLEFINANCE foram verificadas como dependências voláteis/provisórias, sem pretensão de reproduzir a cotação externa. Ausência de erros de execução não equivale a acerto semântico.

As referências históricas de CAIXA foram lidas em seus alvos exatos para validar as fórmulas desta aba; isto não constitui auditoria integral de Janeiro–Julho. As taxas de pagamento de agosto continuam provisórias conforme regra aprovada. Valores digitados foram lidos e testados quanto a tipo, datas, sinais/consolidação/moeda; sem os comprovantes/exportações originais, a auditoria não atesta veracidade documental ou completude do faturamento/custos lançados.

## Conciliação J81/J137
{
  "cash_J81": 90991.71517049983,
  "month_J137": 89681.14645833604,
  "fx": 5.0749379999999995,
  "cash_profit": 35859.24209143041,
  "daily_profit": 35799.79805493362,
  "closure_profit": 35342.75550098781,
  "cash_minus_daily_usd": 59.44403649678861,
  "daily_minus_closure_usd": 457.0425539458083,
  "missing_share_yolok_gross": 52.67985641269148,
  "omitted_invalid_yolok": 1.9457831764591726,
  "omitted_invalid_infinity_lower": 2.1650320645231074,
  "eggbev_missing_gross": 388.32604536729497,
  "cliquet_missing_gross": 149.32999999999998,
  "eggbev_missing_gross_net": 330.1023564555869,
  "cliquet_missing_gross_net": 126.94019749019998,
  "eggbev_missing_invalid_cash": 1.9164123334503225,
  "cliquet_missing_invalid_cash": 0.7369525098,
  "explained_delta_usd": 516.486590442711,
  "actual_delta_usd": 516.4865904425969,
  "residual_usd": -1.1402789823478088e-10
}

A diferença está integralmente explicada no snapshot: J70 omite rev share de Yolokfx; KX83/MZ83 omitem BR de Eggbev/Cliquet, afetando lucros e invalidos AV; P178 omite invalidos de Yolokfx e Infinitynexx inferior. Resíduo apenas de precisão float inferior a um centavo. A correção deve ocorrer nas origens, nunca forçando igualdade entre as células finais.

## Fila de achados — apresentação ao Rodolfo um por vez
Apenas F01 foi apresentado e aguarda a edição manual de J70. F02 em diante ainda não foram apresentados como instrução de correção. Cada impacto deve ser relido ao vivo após correções anteriores.

### F01 — confirmed_error
Escopo: CAIXA SINTETICO!J70
Yolokfx gross J37 omitted from JBF rev-share.
Evidência: {"formula": "=SUM(J38:J51,J62)*$B$3*-1", "J37": 554.5248043441209, "profit_overstatement_usd": 52.67985641269148, "half_brl_overstatement": 133.67350257165583}
Próxima proposta (não autorizada): =SUM(J37:J51,J62)*$B$3*-1

### F02 — confirmed_error
Escopo: Agosto 2026!KX83
Eggbev closing revenue omits Brazil LD36 despite inclusion in daily/site totals.
Evidência: {"formula": "=SUM(KU36,LM36)", "missing_gross_usd": 388.32604536729497, "gross_existing": 139167.4734802668, "gross_expected": 139555.7995256341}
Próxima proposta (não autorizada): =SUM(KU36,LD36,LM36)

### F03 — confirmed_error
Escopo: Agosto 2026!MZ83
Cliquet closing revenue omits Brazil NF36.
Evidência: {"formula": "=SUM(MW36,NO36)", "missing_gross_usd": 149.32999999999998, "gross_existing": 131.2178094315819, "gross_expected": 280.54780943158187}
Próxima proposta (não autorizada): =SUM(MW36,NF36,NO36)

### F04 — confirmed_error
Escopo: Agosto 2026!P178
JBF invalid-traffic consolidation omits Yolokfx AGQ84 and lower Infinitynexx AFN185.
Evidência: {"formula": "=SUM($WR$84,$ZT$84,$ABJ$84,$ACT$84,$AED$84,$AFN$84,$AHG$84,$AIH$84,$AIY$84,$AJP$84,$AKG$84,$AKX$84,$ALO$84)", "AGQ84": -2.275769797028272, "AFN185": -2.532201245056266, "missing_invalid_usd": -4.807971042084539}
Próxima proposta (não autorizada): Add $AGQ$84 and $AFN$185 to the existing SUM, preserving every current constituent.

### F05 — confirmed_error
Escopo: Agosto 2026!ACE36:ACF36, Agosto 2026!ABM36:ABN36, Agosto 2026!ABV36:ABW36
Helixenit country total ROI converts USD revenue to BRL but divides by USD costs; MX currently affected, DE/US latent.
Evidência: {"ACE36": 5.736242810107358, "ACE36_expected": 0.32735470070912376, "ACF36": 4.698743103862743, "ACF36_expected": 0.12291876351252817}
Próxima proposta (não autorizada): Repair one country pair at a time; use the same USD/USD identity and empty guards as the daily country formulas, without *$F$1.

### F06 — confirmed_error
Escopo: Agosto 2026!AGH135:AGI135
Lower Infinitynexx consolidated day-31 ROI formulas are absent although revenue/spend exist.
Evidência: {"actual": ["", ""], "gross_roi_expected": 1.2324560035549124, "net_roi_expected": 0.3991958408436307}
Próxima proposta (não autorizada): Translate row134 formulas down exactly one row; validate both cells.

### F07 — latent_formula_gap
Escopo: Agosto 2026!AOT35:AOU35
ZA consolidated day-31 ROI formulas absent; currently zero activity masks the gap.
Evidência: {"previous_formulas": ["=IF(OR(ABS(AOR34)=0,AOO34=0),\"\",(AOO34/ABS(AOR34))-1)\n", "=IF(OR(ABS(AOR34)=0,AOP34=0),\"\",(AOP34/(ABS(AOR34)+ABS(AOQ34)))-1)"]}
Próxima proposta (não autorizada): Restore by exact relative translation from row34 after authorization.

### F08 — confirmed_error
Escopo: Agosto 2026!APD5:APD35
Global gross ROI reconstructs gross from net with uniform 10% share; net already excludes invalid traffic and M2 uses 5%.
Evidência: {"sample": "=IF(ABS(APB5)=0,\"\",IF(AOW5=0,-1,((AOW5/(1-$D$1))/ABS(APB5))-1))\n"}
Próxima proposta (não autorizada): Use actual USD-normalized gross components, including every country and both special blocks; do not invert a uniform share.

### F09 — confirmed_error
Escopo: Agosto 2026!APD36
Monthly gross ROI uses unweighted AVERAGEIF of daily ratios and excludes valid zero-ROI days.
Evidência: {"formula": "=AVERAGEIF(APD5:APD35,\"<>0\")", "actual": 0.3819000179495419, "gross": 413606.3690640221, "spend": 300125.3211399784, "expected": 0.3781122082368922}
Próxima proposta (não autorizada): Compute ratio from monthly gross and monthly spend; do not average daily ROI.

### F10 — metric_definition_review
Escopo: Agosto 2026!APE5:APE35
Net-ROI denominator includes invalid traffic although AOW revenue already excludes it. The convention also differs from Caixa J79 (profit/media).
Evidência: {"sample": "=IF(ABS(APB5)=0,\"\",IF((ABS(APB5)+ABS(AOX5)+ABS(AOY5)+ABS(AOZ5)+ABS(APA5))=0,\"\",IF(AOW5=0,-1,(AOW5/(ABS(APB5)+ABS(AOX5)+ABS(AOY5)+ABS(AOZ5)+ABS(APA5)))-1)))", "net_already_excludes_invalid": true}
Próxima proposta (não autorizada): Confirm chosen KPI definition before editing; preserve separate labels for profit/media and return/all-costs.

### F11 — confirmed_error
Escopo: Agosto 2026!APE36
Monthly net ROI averages daily ratios instead of a ratio of monthly components.
Evidência: {"formula": "=AVERAGEIF(APE5:APE35,\"<>0\")", "actual": 0.0948004289425946}
Próxima proposta (não autorizada): After net-ROI definition is agreed, compute from monthly components; never average daily ratios.

### F12 — confirmed_error
Escopo: Isliago Agosto 2026!C14:F14
Projection range21:51 includes month/year and only Aug1–29, instead of the 31 daily rows23:53.
Evidência: {"range_current": "A21:A51/C21:C51", "range_calendar_correct": "A23:A53/C23:C53", "current_projection_equals_total_by_coincidence": true}
Próxima proposta (não autorizada): Correct exact date band and separately agree a complete-period projection rule.

### F13 — confirmed_error
Escopo: george Agosto 2026!C14:F14
Projection uses last nonblank revenue of first site as days completed for entire portfolio, even after the calendar month ended.
Evidência: {"denominator": 20, "actual_total_D12": -2633.4139748206617, "projected_D14": -4081.7916609720255, "current_salary_stays_R3000_floor": true}
Próxima proposta (não autorizada): Define a portfolio-wide data-completeness cutoff; closed complete months must not extrapolate from a site with no recent revenue.

### F14 — confirmed_error
Escopo: joe Agosto 2026!C14:F14
Projection uses last nonblank revenue of first site as days completed for entire portfolio, even after the calendar month ended.
Evidência: {"denominator": 30, "actual_total_D12": 3302.529307836749, "projected_D14": 3412.6136180979743, "current_salary_stays_R3000_floor": true}
Próxima proposta (não autorizada): Define a portfolio-wide data-completeness cutoff; closed complete months must not extrapolate from a site with no recent revenue.

### F15 — label_error
Escopo: Isliago Agosto 2026!A1, George Agosto 2026!A1, Nicolas Agosto 2026!A1, Joe Agosto 2026!A1
Four August manager tabs still display Julho; identities, tabs, and imported dates are August.
Evidência: {"kelly_correct": "Agosto", "four_incorrect": "Julho"}
Próxima proposta (não autorizada): Change only A1 to Agosto in each confirmed file, one verified scope at a time.

### F16 — reporting_gap
Escopo: Agosto 2026!AMC:AOU
Country summary excludes BR despite Brazilian revenue/spend in the source blocks.
Evidência: {"missing_gross_usd": 1330.9851955287163}
Próxima proposta (não autorizada): Add an approved BR summary or explicitly label the existing country overview partial; structural work requires separate scope.

### F17 — business_evidence_needed
Escopo: Agosto 2026!O121:P121
SMS Funnel has independently entered USD and BRL amounts, inconsistent with provisional F1; a settled transaction rate could justify this.
Evidência: {"usd": -4099.78, "brl": -20000, "implied_rate": 4.878310543492578, "provisional_rate": 5.0749379999999995}
Próxima proposta (não autorizada): Check payment proof before choosing source currency. Do not auto-convert or classify as confirmed accounting error.

### F18 — latent_formula_gap
Escopo: Agosto 2026!D38, Agosto 2026!V38, Agosto 2026!AN38, Agosto 2026!FY38, Agosto 2026!GQ38, Agosto 2026!AKD38, Agosto 2026!AKU38, Agosto 2026!ALL38
Eight dormant summary cells sum empty rows37:38 instead of monthly gross; zero blocks hide the defect. YMonetize retirement stays respected.
Evidência: {"D38": "=SUM(G37:G38)", "V38": "=SUM(Y37:Y38)", "AN38": "=SUM(AQ37:AQ38)", "FY38": "=SUM(GA37:GA38)", "GQ38": "=SUM(GS37:GS38)", "AKD38": "=SUM(AKF37:AKF38)", "AKU38": "=SUM(AKW37:AKW38)", "ALL38": "=SUM(ALN37:ALN38)"}
Próxima proposta (não autorizada): Disposition per inactive block before reuse; do not reactivate YMonetize or expand correction scope.

### F19 — confirmed_error
Escopo: Agosto 2026!P171
SB-CAD payout estimate omits lower Infinitynexx net-before-tax contribution AFN184:AFN186.
Evidência: {"formula": "=SUM(WR82:WR85,ABJ82:ABJ85,ACT82:ACT85,AED82:AED85,AFN82:AFN85,AHG82:AHG85,AIH83,AIH84,AIH85,AGQ83:AGQ85)", "omitted_usd": 553.0283094619638}
Próxima proposta (não autorizada): Add the lower Infinitynexx subtotal to existing SB-CAD constituents; preserve USD/CAD grouping distinct from partner grouping.

## Limites e status institucional
O PASS global antigo foi superado por esta reauditoria, preservando os artefatos históricos. O dashboard existente continua dependente das fontes com erros pendentes. Não foi auditado nem alterado nesta tarefa.
Artefatos locais: manifest.json; all-cell-inventory.jsonl; formula-recomputation.jsonl; semantic-checks.json; extended-semantic-checks.json; spend-calendar-checks.json; manager-semantic-audit.json; J81-J137-bridge.json; findings-queue.json; final/.
