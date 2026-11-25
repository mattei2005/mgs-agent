# Fechamento de outubro/2026 — conferência ordenada

## Autoridade, fonte e ordem

Rodolfo1575041627167391744, thread1545426987756298340, forneceu https://docs.google.com/spreadsheets/d/11u9cPHNj2KmpMxOkLNn9Pl8MQS7ALkNQXkjijlTQWNk/edit?gid=565588781 e autorizou iniciar a conferência de outubro.

Fonte lida pela SA canônica: **Ad Manager Report Rede1 e Rede2 (Oct 1, 2026 - Oct 31, 2026)**. Gid565588781 é `rede 1 SB`; o pedido abrange o arquivo, não somente a aba inicial. A planilha é referência somente leitura; destino da comparação é a Dash financeira.

Ordem vigente:
1. Gastos Facebook e Google.
2. Receita M2, aba `Rede MonetizeMore (M2)`.
3. Receita Rede2, aba `rede 2 SB`.
4. Receita Rede1, aba `rede 1 SB`.

Rodolfo confirmou explicitamente **sem movimento nas abas AV em outubro**. A Conferência da Dash também não contém receita AV. Isso resolve a ausência de fonte AV deste mês, sem inserir zeros nem estender a confirmação a outros períodos.

A autorização atual é de conferência. Correções monetárias eventualmente necessárias devem ser apresentadas com valor/fonte/escopo antes de aplicação. Não reabrir agosto/setembro ou modificar taxas, SMS, recargas, comissões e ledger por inferência.

## Fase1 — gastos: comparação concluída

Evidência `apps/finance-system/private/october-close-1575041627167391744/`; relatório `reports/finance-october-spend-review-1575041627167391744.md`.

- Facebook:52contas na fonte, todas resolvidas inequivocamente ao cadastro/ledger; USD869020.28 na planilha e na Dash; diferença0. Nenhuma conta positiva exclusiva de um dos lados. A fonte contém totais mensais, não diário deFacebook.
- Google:Mattei1/5172498094→GameZoneAd;31dias. Fonte BRL91064.00; Dash original API BRL91063.991578, exibido91063.99. Cada um dos31valores de origem coincide com o arredondamento em centavos do `cost_micros` original; diferença bruta0.008422, diferença de exibição1centavo. Manter a precisão original por padrão; nenhuma correção financeira foi aplicada. A planilha tem11datas serializadas com mês/dia invertidos; a leitura M/D/YYYY foi validada pela competência explícita, sequência completa31dias e correspondência exata do gasto diário ao recibo API salvo. Fonte preservada sem edição de datas.
- Custos registrados:1149lançamentos positivos conta/dia rastreados até input/site/data;38contas com sufixoG conciliadas ao gestor;2108controles gestor/site/dia e68mensais sem diferença em centavos. Google não recebeu gestor inventado: respeitada a disposição explícita Mattei1→GameZoneAd sem gestor externo do contrato de contas.
- Readback de fonte integral FB/Google idêntico no fim; APIs reais dos cinco gestores, owner-preview e quatro vistas Conferência Rodolfo/Geizian desktop/mobile confirmados. Não houve nova coleta nos provedores de mídia; a comparação usa o fechamento fornecido e os recibos/fatos já registrados na Dash.

## Fase2 — M2: aplicada e validada

Supersessão: Rodolfo1575050438892585082 confirmou a proposta deoutubro; o estado anterior deaguardando aplicação está encerrado. Relatório `reports/finance-october-m2-complete-1575050438892585082.md`.

- Wantabrand principal:USD21.29,US-CC-ES/BOT/G001;FinanceWantabrand:USD0.49,US-CC-EN/BOT/G001. TotalUSD21.78, trêsdatas reais01/10,02/10,27/10 e62controlesexatos.
- Aplicação2179→2180,audit7703;backupdual/restoreisolado,recoveryimutável,idempotência/API/DOMconfirmados. Source/gastos/CAD/outrascompetências/ledger preservados;FinancepermaneceINATIVO. RemuneraçãoÍcaro recalculada pela regra7%; nenhum pagamento executado.
- Esta atribuição vale somenteoutubro. Setembro continua com sua confirmação própria e novembro/futuro não recebe cópia dessas receitas/regras pontuais.

## Fase3 — Rede2: aplicada e validada

Rodolfo1575120915530911765 confirmou a proposta1575058997373968486. Isso supersede somente a pendência Rede2, preservando o relatório histórico `reports/finance-october-rede2-review-1575050438892585082.md`.

- Resultado:USD209970.27 na fonte e naConferência;304controles/681linhas. CPV182043.93,Fincgriffin479.51,GameZoneAd27446.81,CarCreditAd0.02.
- 302overlaysUSD conservam originais;Fincgriffin identificaRede2naConferência semduplicação. CAD,catálogo/regras,câmbios,gastos,M2,AV,SMS/recargas,pagamentos e demaiscompetências preservados.
- Produção2189→2190,audit7736;recoveryimutável,backup/restore real,ensaio,readback idempotente,14vistasdesktop/mobile e496célulasgestor confirmados. Readbackposterior2191 confirmaadiçõesidênticas. Nenhumdeploy/restart/credencialalterada.
- Evidência:`reports/finance-october-rede2-complete-1575120915530911765.md` e `apps/finance-system/private/rede2-october-1575120915530911765/acceptance.json`.

## Fase4 — Rede1: auditada, aguardando confirmação

`reports/finance-october-rede1-review-1575120915530911765.md`:3476linhas,36sites,1805gruposfonte/1858gruposDash,1860união. FonteCAD1708827.76 versusDash1709447.03, reduçãoCAD619.27. ConferênciaUSD/Rede2 nãofoireaberta.

Além dosvaloresdiários, a fonteatribuiCliquetUSintegralmenteaMGS,NewsounDEaKelly eZuoutprincipal/FinanzasaNicolas;essasquatroatribuições divergemdosfatosCADsalvos e precisamconfirmaçãodeoutubro. Decisõesdesetembro nãoseestendemautomaticamente.

Simulaçãov2emmemóriaconciliauniãocompleta/cartão e5gestores,semwriteRede1. A simulaçãoanteriorfoiinvalidadaporfaltadedestinosCliquet;usarsomenterecibov2. Próximopasso:confirmarcorreçõesCADdiáriasequatroatribuições,entãoexecutarcombackup/restore/readback. AVsegueencerrada pela confirmaçãodotitular.
