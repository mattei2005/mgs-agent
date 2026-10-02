# Reconciliação das abas atuais de gestores

## Autoridade e fonte

Rodolfo `1548145007612137554`, thread `1545426987756298340`. Relatório completo: `/root/mgs-agent/reports/finance-manager-tabs-audit-1548145007612137554.md`. Evidência: `/root/mgs-agent/apps/finance-system/private/manager-tabs-audit-1548145007612137554/`.

## ROI sem mídia — confirmação `1548779265607073944`

Rodolfo confirmou que ROI líquido de 1.900% sem gasto de mídia não possui sentido operacional. Nas visões atuais dos gestores, ROI bruto e ROI líquido, diário ou mensal, só existem quando o mesmo grupo possui mídia diferente de zero. Imposto isolado nunca vira denominador de ROI. Quando mídia é zero, ambos aparecem como `—`, alinhados à visão do proprietário e ao texto “Sem gasto, não há ROI para calcular”. A correção é de apresentação/derivação da API de gestor; não altera receita, imposto, lucro, pagamentos, banco nem histórico fechado. Grupos com mídia preservam o cálculo existente `net ÷ (|mídia| + |imposto|) − 1`.

## Remuneração atual e progresso do piso — aprovação `1548770990954119179`

A correção conceitual de Rodolfo `1548770555963113584` separa comissão calculada de remuneração efetivamente devida. Na visão do gestor, o segundo card atual não mostra mais a comissão teórica como se fosse pagamento: ele mostra `Remuneração atual`, em BRL principal e USD secundário, lida do mesmo registro `COMMISSION_FLOOR` usado por Pagamentos. A tela de Pagamentos permanece inalterada e exibe somente o valor devido, saldo anterior, ajustes/pagamentos e saldo a pagar.

Estados visuais automáticos:

- enquanto o piso de BRL 3.000 for maior que a comissão: `Piso mensal aplicado`, com comissão calculada na faixa atual, resultado BRL, meta para a comissão superar o piso e quanto falta;
- quando 7% superar o piso: `Comissão de 7% aplicada · piso superado`, com o piso e o progresso até a faixa de 10%;
- a partir de BRL 100.000 de resultado: `Comissão de 10% aplicada`, sobre o resultado inteiro;
- gestor inativo: estado explícito, sem apresentar comissão como devida.

Com piso BRL 3.000, taxa 7% e arredondamento half-up da folha, o primeiro resultado em centavos cuja comissão paga excede o piso é BRL 42.857,22. Este limiar é apresentação derivada da política ativa; não altera `expenses.py`, a base, o pagamento nem o ledger. O fluxo continua: resultado row12 → câmbio BRL → `COMMISSION_FLOOR` → remuneração em `domain.expenses` → devido de Pagamentos. Pagamentos registrados permanecem fixos; devido/saldo provisórios acompanham o recálculo.

## Explicação de custo direto no card de resultado — Rodolfo `1555449010519679079`

Quando a competência possui `direct_monthly_cost` para o gestor, a API expõe `direct_cost_note` derivada das adições vivas, nunca de texto ou valor hardcoded no navegador. O card `Resultado líquido` mostra uma nota contextual no espaço à direita, sem competir com `Remuneração atual`:

- recarga/pagamento preservado e retirado do rateio das Despesas Gerais;
- consumo direto daquele gestor no Creditoparaveiculo;
- confirmação de que o custo já está descontado do resultado e que a remuneração foi recalculada.

A nota usa o período, site, custo BRL, recarga preservada e autoridade presentes no workspace. Se não houver custo direto para o gestor/competência, o card permanece no layout anterior e nenhum texto é inventado. Desktop usa duas colunas dentro do card de resultado; em telas de até 700 px a nota desce abaixo dos valores. Validar todos os cinco gestores em desktop e mobile, sem overflow, erros JS ou falhas same-origin. A mudança é somente de API de apresentação/UI; não recalcula nem grava valores financeiros.

## Cards atuais e estimados — correção de Rodolfo `1548174919920128083`

Esta regra supersede integralmente a interpretação de `1548167344650461236` que ligou os cards diretamente ao resumo legado `row=14`. Aquela implementação gerou valores altos e duplicou `Projeção do mês` com `Resultado líquido estimado`; `row14` não é mais fonte dos cards.

Mostrar cinco cards:

- linha atual: `Resultado líquido até DD/MM`, usando o row12 acumulado até o cutoff;
- linha atual: `Comissão atual · 7%` quando o resultado atual convertido para BRL estiver abaixo de R$ 100.000, ou `Comissão atual · 10%` a partir de R$ 100.000;
- linha estimada: `Resultado líquido estimado = resultado atual ÷ dias preenchidos × dias do mês`;
- linha estimada: `Referência 7% estimada = resultado estimado × 7%`;
- linha estimada: `Referência 10% estimada = resultado estimado × 10%`.

Usar `domain.realized.elapsed_days`; fallback somente para o dia do cutoff da própria competência. Zero dias preenchidos mantém a estimativa indisponível. Todos os cards exibem USD principal e BRL secundário pela cotação da competência. O piso permanece na regra de pagamento e não muda a comissão/faixa mostrada no segundo card.

Relatório e readback: `/root/mgs-agent/reports/finance-manager-card-formula-1548174919920128083.md`.

## Causa e regra ativa

A página usava apenas células legadas para os blocos diários. A receita GAM de setembro já existia em `domain.facts` e atualizava o total row12, mas não entrava nas colunas dos sites. Nunca conclua que coluna vazia significa receita zero sem comparar o bloco com fatos nativos por gestor/site/país/dia.

Para setembro/2026 e seguintes:

- preservar métricas legadas do bloco, principalmente mídia e receita anterior;
- somar fatos `native_addition` pelo gestor interno (`george` para Ícaro), site, país e dia;
- preservar origem não-USD pelo `addition` correspondente e Gross normalizado em USD;
- integrar `native_manager_spend` no próprio site com sinal negativo; não manter bloco `spend_only` quando existe o site financeiro;
- criar bloco completo para site nativo sem metadata legada;
- se houver exatamente um país legado e um país real diferente, usar o país real e transportar a mídia existente; múltiplos países continuam fail-closed, sem remapeamento arbitrário;
- dias posteriores ao cutoff ficam vazios;
- total mensal soma dias não arredondados; ROI mensal usa totais, nunca média de ROI diário;
- reconstruir resumos por site dos blocos corrigidos;
- exigir soma dos sites igual ao row12 da fonte dentro de USD 0,000001; divergência bloqueia a API em vez de maquiar ajuste;
- remuneração e caixa só podem ser declarados preservados quando row12 e fingerprint do banco permanecerem iguais.

A regra anterior de agosto exclusivamente legado foi supersedida por Rodolfo1551324490271695064: somente `workspace-2026-08`, com a política `august-adops-cpv16-1551324490271695064`, integra os fatos nativos já existentes aos blocos de gestores; snapshots sem a política e janeiro–julho permanecem preservados. A política também corrige somente a derivação de CPV16/G006 em agosto: inclui AJX nas fórmulas diárias de custo de Nicolas em memória, preservando as 85.868 source_cells, todos os valores de mídia e os fatos de receita. Valide cash/facts/inputs iguais, diferença de custo Nicolas USD74.57, cinco summary_controls e ausência de importação duplicada. O fechamento AV/M2 permanece uma etapa separada; esta correção de exibição não prova receitas conciliadas com AdOps.

## Estado validado

- Setembro: 443 fatos nativos verificados.
- Blocos: Joe 6; Isliago 9; Kelly 7; Ícaro 11; Nicolas 9.
- Yolokfx completo 5/5; Portal Relevante presente para Ícaro; Openzed canônico; Creditoparaveiculo BR.
- Row12: 5/5 reconciliados; remuneração e caixa inalterados.
- Banco: fingerprint antes/depois idêntico.
- Produção: 85/85 APIs, 5/5 logins reais, owner 5/5, 390/1440px, zero JS errors.
- Testes: 130 Node e 87 Python; cards 2+3 validados nos cinco gestores, projeção por 10 dias preenchidos × 30 dias de setembro, faixa atual 7%/10%, USD/BRL exatos, 390/1440px e zero JS errors.

## August-only supersession — Rodolfo1551644766125428847

- Yolokfx in **August2026 only** belongs entirely to G002/MGS: no manager operated it. This supersedes the prior Isliago/G003 attribution for the seven August native rows and the audit's suggestion that Yolokfx should appear in his workbook. Preserve native currencies, every amount/date/lineage and the site's existing expense-allocation state. September and later shared/tagged attribution are unchanged. Verified revision442/audit1677;38facts attributed SEM_COMISSAO, zero Yolokfx manager earnings, unchanged7ledger entries and other months. Canonical decision/report: `/root/mgs-agent/reports/finance-august-adjust-1551644766125428847.md`.
- Runtime uses month-bound reconciliation policy `august-yolokfx-mgs-1551644766125428847` with matching authorization in `august_reconciliation.py`. It changes only a calculation-local copy of the two BASE_DASH owner metadata fields; imported source.json stays immutable. Native entries retain original raw G003 source rows and add explicit assignment authority; catalog manager/owner becomes SEM_COMISSAO/MGS for August only.
- The former BRL0.01 credit placeholders are **superseded** by Rodolfo1551658668393631755 and `reports/finance-geizian-credits-1551658668393631755.md`: preserve five current positive credits (Canva104.70, rent405.00, internet45.88, energy284.02, Portal60.00), totaling BRL899.60. Six historical voided entries remain audit-only and are excluded from the active list/calculation. Never revive/re-create the old one-cent credits; verify current ledger and Sheet numeric cells before proposing changes.
- After manual mixed-currency repair, recheck BOTH original-currency totals and converted/net totals. Restoring a CAD conversion is insufficient when the moved original USD was inadvertently reduced. Readback in this case found TC21 changed486.33→634.11 while TC22's USD276.29 was replaced by conversion: original USD fell128.51. The proposed TC21 total762.62 preserves both USD inputs; it was not applied without separate authority.
- Expense review-status labels are outside this reconciliation while Rodolfo has not performed his review; leave statuses unchanged.

## Openzed August — explicit supersession1551714950781866035

- Rodolfo ordered the **dashboard**, not either Sheet, to match Ícaro/G001 for USD1.76 of Openzed US in August2026. This supersedes only the G001 subset of pointB approved1551312942182441111, not the remaining Openzed/G003 allocation or September+ rules.
- Exact AV source:sheet1938914193, rows10981/10983/10987/10993, dates02/03/05/14August, USD0.26/0.67/0.49/0.34. The original medium is g001-d despite C/D/E hyphens. Canonical decision:`docs/finance-openzed-august-attribution.md`; report:`reports/finance-openzed-icaro-1551714950781866035.md`.
- Move only the four exact source portions between existing daily entries. Native daily `gross` may be0 because actual originals live in `gross_pair`: adjust paired USD values and move the exact `source_components.rows` lineage together. Preserve entry IDs, CAD, currencies, quotes, source bundle, every non-target row and multiset of source references. Never assign an entire aggregate daily G003 entry to Ícaro.
- Back up; compute/rehearse with transaction rollback, revision lock, protected-month/ledger fingerprints; apply atomically with recovery scenario/audit; second run must be no-op. Validate public workspace and all manager summary_controls. Blank fact metrics remain blank, not zero; compare their exact fingerprint separately from numeric sums. API expense-status presentation may differ from stored DB result; compare financial fields like-for-like instead of counting that display normalization as financial drift.
- Verified revision452/audit1739: original Openzed US USD Ícaro3.24→5.00; Isliago11790.79→11789.03; all site gross/net/tax/invalid/media totals preserved. Automatic payroll recalculation lowered Isliago remuneration0.54BRL, left Ícaro remuneration unchanged and raised Geizian half0.27BRL at the same quote; no payment/ledger/Sheet edit. Do not claim final net is invariant when commissions recalculate.

## Principal-Sheet payroll and final-net audit

When gross/spend totals already match, do not infer net/payroll parity. Reconcile all company expense origins, fixed staff values, each manager's gross and result base, payable commission/floor, and the final partner ledger separately. Freeze one common USD/BRL and USD/CAD snapshot in an offline diagnostic; first prove that the unmodified formula graph reproduces the principal Sheet's actual totals. A later live manager IMPORTRANGE read may have fresher volatile values than the principal cache, so never call that timing difference a missing payment.

- Inspect every CAD/converted-USD pair for a numeric USD cell coexisting with nonzero CAD on the same row. Original-currency totals can match while the Sheet's net calculation silently drops the CAD conversion. In the August audit `1551627541519794186`, Openzed Finanzas TB22 CAD180.31 + TC22 USD276.29 triggered this exact condition. Report and obtain correction authority; do not discard either native source.
- Verify manager summary coverage explicitly: principal gross parity does not prove that guest operations such as Yolokfx appear in the manager workbook. Preserve approved source-manager assignments and check known CPV16/G006 cost inclusion and the current Openzed USD1.76 G003→G001 restoration under1551714950781866035 independently of totals. The former opposite transfer is superseded for those four August rows only.
- Discover manager blocks at every actual header row, not only the first. Normalize Gross/GROSS case and mixed headers such as `Openzed US\nGross USD`; exclude ROI and TOTAL duplicates. API public identity is `icaro`, while calculation namespace and original workbook key remain `george`.
- Distinguish entered numeric amounts from text like `60,00`: Sheets SUM ignores text, and a ledger may already contain a signed numeric adjustment. Verify sign, prior balance, cent-unit ledger fields and any repeated one-cent entries before proposing repair. Ledger/payment changes require their own authority and Critical Subset confirmation where applicable.
- SMS dual-display history is superseded for August only by1551644766125428847: USD4099.78 remains the operative basis; principal P121 now converts O121 by F1. Use `company-expense-source-order.md` for the current rule; do not propagate this August edit to September.

Evidence and unresolved review points from the read-only audit: `reports/finance-expense-audit-1551627541519794186.md`. No financial correction is authorized by that audit request.

## Full-month read-only audit controls

- Enumerate every IMPORTRANGE spill and compare the complete imported rectangle with its actual source, including the shared Caixa rate dependency; checking only the visible summary is insufficient. Preserve blank versus missing versus numeric zero.
- Reconcile four distinct layers: original-currency gross/media, converted operational results, each person's rounded payable, and the final payment ledger. Report raw precision deltas and cent-rounded presentation deltas separately; a sub-cent raw difference can straddle a cent boundary.
- Test both `ROUND(SUM(raw amounts),2)` and `SUM(ROUND(each payable,2))`. Sheets can retain fractional-cent commissions and carried balances while the ledger stores each obligation in integer cents. Equal individual payables do not prove equal payroll totals or partner balances. Do not change original revenues to force cosmetic agreement; rounding/FX policy changes require their own authorization.
- Fetch all counterparty ledgers; prove due matches remuneration, movements match active signed entries, and previous+due+movement equals balance. Keep review status outside the financial comparison when Rodolfo has not reviewed it.
- Use the public manager API for displayed commissions and cards: it normalizes summary fields that may be stale in the raw workspace domain. Sum site summaries with `row<12`, including native `row=0`, and exclude both total row12 and estimate row14. Reconcile daily blocks plus explicitly monthly-only closing adjustments without manufacturing a day31 posting.
- If quotes refresh during the audit, preserve both revisions, verify nominal additions/model/site configuration stayed identical, and use one internally consistent revision for all final comparisons. Distinguish automatic quote writes from financial-source edits; timestamp conclusions and label the closing provisional.

## Rateio das Despesas Gerais

Apresentação aprovada na mesma mensagem:

- coluna `Rateio das Despesas Gerais`;
- badge `Participa` ou `Não participa`;
- editor `Participa do rateio` ou `Não participa do rateio`.

`Não participa` preserva receitas/gastos e remove somente as cotas do rateio. Valores internos `ATIVO/INATIVO` permanecem para compatibilidade e nunca devem voltar a aparecer como rótulos nessa interface.
