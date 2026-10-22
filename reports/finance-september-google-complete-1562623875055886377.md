# Setembro2026 — ponto4/Google alinhado aos centavos diários

## Autoridade e escopo

Rodolfo1562623875055886377 escolheu corrigir aDash após a explicação1562622867873603655 sobre a diferença de arredondamento. A decisão aplica os43valores diários em centavos do fechamento **somente em setembro/2026**. Não cria uma política global de arredondamento nem altera aAPI doGoogle.

Fonte somente leitura: spreadsheet1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA, abaGastos Google,gid1132083250. A planilha geral permanece fora do escopo. Os pontos1–3 e os demais meses/pagamentos foram preservados.

## Resultado verificado

- Valor anterior naDash: BRL111547.927996, exibidoR$111.547,93.
- Fonte eDash após: **R$111.547,89**.
- Diferença final: **R$0,00**, igualdade decimal exata na soma dos valores aplicados.
- Ajuste consolidado original:−BRL0.037996; diferença visual deR$0,04.
- Gamingadx-US-01/ID2780300411: **R$5.350,59**,13valores alterados.
- Mattei1/GameZoneAd/ID5172498094: **R$106.197,30**,30valores alterados.
-43registros nativosaccount_spend atualizados,60/60controles conta/data aprovados, incluindo os diassem gasto que permaneceraminalterados.
- Aplicação produtiva **1654→1655**, controlemedia-spend35→36, audit4961/SEPTEMBER_GOOGLE_DAILY_CENTS_ALIGNED.

## Precisão original preservada e proteção da escolha

Cada valor aplicado foi comprovado como o arredondamento para centavos do valor original, sem abatimento arbitrário em um dia. No recibo de importação, os camposoriginaisamount,cost_micros,queried_at eapplied_amount da última aplicação automática permanecem intactos. A soma originalGoogle continua111547.927996 como evidência de origem, não como total financeiro efetivo do fechamento.

Os valores autorizados e sua proveniência ficam separadamente emclosing_override por registro eclosing_applied_totals.BRL=111547.89, além declosing_reconciliations com autoridade, fonte/hash e razão. O campoapplied_amount original representa a aplicação automática anterior; o valor manual vigente está explicitamente nooverride de fechamento.

Replay do snapshot original pelo`planSpend` real:zero alterações propostas e43manual_conflict esperados. Isso prova que a trava existente não desfaz silenciosamente a escolha manual de setembro. Não houve respostaAPI fabricada, alteração dos micros de origem, relaxamento do guard ou execução de reimportação real; foi um teste de replay isolado do snapshot preservado.

## Backup, ensaio e aplicação

- Backup remoto privado:`/home/zeus/mgs-finance-backups/googleclose-close-1562623875055886377/finance-before.dump`.
- Cópia local ignorada peloGit previamente:`apps/finance-system/private/september-closing-1562564679400951829/googleclose-before.dump`.
-146922902bytes; SHA256dcfd1b3714265725494093542133f85746a6a5826a77f2ae970264a949cb84ad. Catálogo e igualdade das cópias conferidos.
- Restore materializado:`mgs_finance_googleclose_1562623875055886377`,239cenários com fingerprints iguais. Stage:`/home/mgsfinance/stage-googleclose-1562623875055886377`,65arquivos fonte atuais,fixturesexplícitas eNode com hashes conferidos. Artefatos retidos, nenhuma exclusão.
- Ensaio, aplicação isolada, readback e replay aprovados antes da aplicação produtiva.
- Uma transação emprodução com admissão/locks,CAS,audit, recuperação imutável deworkspace econtroleimportação. Recoveries:`recovery-googleclose-1562623875055886377` e sufixo`-spend`.
- Origem de cada valor, IDs, datas, sites,atribuição,moedaBRL e todos os campos dosaccount_spend, excetoamount, preservados. Overrides de parâmetros intactos.

## Aceite e preservações

- Releitura independente comDecimal:60/60controles exatos,43valores do relatório,2totais de contas e total111547,89.
- ReceitaRede1CAD778884,56; Rede2USD209644,93; FacebookUSD500749,61 permanecem conferidos e inalterados.
- Receitasgross/net/invalid/tax, DespesasGerais, taxas, ledgerde pagamentos e outros cenários preservados. Resultado recalculado pelo câmbio vigente, sem ajuste de câmbio para forçar paridade.
- Cinco visões de gestor passaram. API/UIpúblicas comMFA doOwner, desktop1440/mobile390, totalGoogle, duas contas,60registros, microsoriginais,totais anteriores e reload:12checksPASS, zeroerroJS e zeroPOSTfinanceiro de teste. Sessão de validação revogada.
- Monitor financeiro final:15/15PASS,sem novo alerta. Nenhuma alteração de código,cron,serviço,credencial,permissão ouschema neste ponto.
- Planilha relida antes/depois, sem alteração da fonte.

## Continuidade

Evidênciafinanceira:`apps/finance-system/private/september-closing-1562564679400951829/point4-*`; aceite público:`apps/finance-system/private/google-closing-1562623875055886377/`. Procedimento de exceção explícita de centavos diários salvo em`mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md`.

Ponto4 concluído. Próximo:ponto5/MonetizeMore, ainda sem aplicação, comUSD705,00 no relatório e sem receitaM2 naDash. Manter a etapa de explicação/atribuição antes de qualquer preenchimento.
