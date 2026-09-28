# Agosto — paridade ao centavo concluída

Autoridade: Rodolfo1551624141885415455, thread1545426987756298340.

## Resultado

- Comparação completa dos totais mensais por domínio, Gross CAD/USD originais, Facebook USD e Google BRL:184/184controles PASS, zero divergências ao centavo.
- Quatro totais gerais também coincidem ao centavo.
- Yolokfx Facebook corrigido por Rodolfo: USD497.89 nos dois lados.
- Dashboard consultada por API e PostgreSQL: revisão438, fatos/cash/projeção de additions idênticos; zero escrita financeira na dashboard.
- Sem novos erros de fórmula; zero erros na aba inteira.

## Alterações autorizadas na planilha principal — Agosto2026

- D17: CAD0.01 → vazio; E17: fórmula de conversão → USD0.01 (Contecta, referência AV consolidado C4). Demais fórmulas de conversão preservadas.
- AJM175:359.37 →359.36, input MGS/G002 de CreditoParaVeiculo; total USD71815.90. Fórmulas SUM top/detalhe preservadas.
- ZQ175:1.13 →1.12, input MGS/G002 de Fincgriffin; total USD1682.83. Fórmulas SUM preservadas.
- ABX35:1486.90 →1486.89, Helixenit; total CAD35027.63.
- AFS35:886.68 →886.67, Infinitynexx; total CAD14055.88.
- Notas explicam ajuste mensal de centavos, não nova origem diária. Inputs de gestores externos não foram escritos.
- Backup integral, hashes, rollback exato com notas, preflight de merge/proteção, canary sem mudança numérica e readback integral de seis células.
- AKU35 e sua nota de sete origens permanecem preservados. A ponte CAD→USD não é receita duplicada nem atribuição real dos sete domínios ao AutoCreditAdx.

## Totais finais (planilha = dashboard ao centavo)

- gross_CAD: 292199.24; residual exato dash menos Sheet -0.00444485641826931122.
- gross_USD: 198683.65; residual exato dash menos Sheet 0.0014206297744593895.
- FB_USD: 286368.15; residual exato dash menos Sheet 0.00.
- Google_BRL: 71174.24; residual exato dash menos Sheet 0.00.

## Limite da afirmação 100%

100% no escopo combinado: totais de Agosto por domínio e moeda original/plataforma, comparados ao centavo, mais quatro totais gerais. Não significa igualdade de valores brutos subcentavo, distribuição diária ou valores líquidos/repasse/BRL convertido com taxas provisórias diferentes. Não constitui certificação universal da aplicação financeira.

## Evidência

/root/mgs-agent/apps/finance-system/private/sheet-centavos-1551624141885415455
Artefatos: changes.json, rollback.json, backup-hashes.json, before/after-targets-grid.json, after-FORMULA.json, cent-write-verification.json, comparison-final.json, final-verification.json.
