# Outubro/2026 — Rede2 aplicada e validada

## Autoridade e resultado

Rodolfo `1575120915530911765` confirmou a proposta `1575058997373968486` na thread `1545426987756298340`. O Sim é exclusivo da correção Rede2; não autoriza Rede1.

Fonte read-only: `11u9cPHNj2KmpMxOkLNn9Pl8MQS7ALkNQXkjijlTQWNk`, aba `rede 2 SB`, gid869925501. As 681linhas originais foram preservadas e relidas idênticas antes/depois. Os 304controles site/país/gestor/data coincidem em centavos.

- CarCreditAd: USD0.02 preservado.
- CreditoParaVeiculo: USD182043.92506855902721724 → exibido182043.93.
- Fincgriffin: USD479.50987975530599996312 → exibido479.51.
- GameZoneAd: USD27446.811090755621433132 → exibido27446.81.
- Total: USD209970.27 na fonte e na Conferência. Resíduo bruto máximo por controle4e−18, exclusivamente CarCreditAd preservado; não inventado ajuste de representação.

302overlays `gross_pair` de origemUSD, conservando entradas originais e sua linhagem. Metadata `source_network=SB Rede2` nos86fatosUSD deFincgriffin; nenhum novo valor duplicado. Catálogo/regras de inválidos/share/FX permanecem inalterados. ReceitaCAD, M2,AV,FB,Google,SMS/recargas,despesasgerais,rateio,pagamentos e demaiscompetências preservados.

Produção2189→2190, audit7736 `OCTOBER_REDE2_CLOSING_APPLIED`; recoveryimutável `recovery-r2oct-1575120915530911765`. Novo readback na2191 confirmou exatamenteasmesmasadições; câmbio automático pode atualizar resultados emBRL depois da transação. No mesmo câmbio congelado: remuneraçãoÍcaro5934.95→5932.58;Isliago40672.18→40666.45;Joe10048.86→10047.99;Kelly26682.76→26678.84;Nicolas60384.59→60358.38. São valoresdevidos calculados, nenhum pagamentoexecutado.

## Recuperação e execução

Backup privado remoto `/home/zeus/mgs-finance-backups/rede2-october-1575120915530911765/finance-before.dump`, cópia local previamente confirmada foraGit;232603360bytes;SHA256 `f41574084bda43f9980e24f34b78871b5e4d395a2e158bd5385766d5470b19be`. Restore real `mgs_finance_r2oct_1575120915530911765`,320cenários comfingerprintsiguais;stage `/home/mgsfinance/stage-r2oct-1575120915530911765`,516arquivos hashverificados. Backup/bancoisolado retidos.

Rehearsal/apply/verifyisolados e rehearsalprodutivo passaram antes da transação row-lock/CAS sobadmissãoexclusiva e quote-lock. Verifyprodutivo idempotente, zero replay. Testeisolado complanodiário real30/10: antesdooverlay replayidempotente; depoisdooverlay fonteantiga rejeitada semescrita. Oteste ajustou somente o cutoff da cópia emmemória para30/10, para exercitar a guarda deconteúdo além da guarda naturaldecutoff31/10.

## Aceitação pública

Login realMFA e logoutvalidado, semcriar sessão degestor. 14vistas:ConferênciaRodolfo/Geiziandesktop/mobile e cincoowner-previewsdosgestoresemambaslarguras;496célulasUSDdiáriasrenderizadascontraafonte,footersmensais,paridadeAPIowner/preview e reload. ZeroJS/POSTfinanceiro. FincgriffinUSD479.51 visível porrolagemdalistainterna e confirmação visualmobile. APIs e readbackremotoindependentesconfirmam304controlescompletos.

## Recuperações de validação

- Preparo inicial esperava302mudançasmascontou303alvos; identificada1entradaCPV exatamenteigual. Preservada;pré-write repetido,302overlayscorretos.
- Testedereplayinicial parou naguardadecutoff31/10 versusplan30/10. Cópias emmemória delimitadas a30/10 para testar oconteúdo;nenhumcutoffprodutivo alterado.
- Primeirobrowser interpretou`<0,01`comoumcentavo. Corrigido o validadorpara osubcentreal e repetidaaceitaçãocompleta;nenhumlançamentorepetido.
- Na faseposteriorRede1, comparação comdefaultdict mascarouausências e simulaçãoinicialomitiudestinosnovosCliquet. Reciboinvalidado,setsindependentes/uniãocompletarefeitos;v2passou. Isso nuncafoiaplicado;autoridadeRede1seguependente.

Evidência: `apps/finance-system/private/rede2-october-1575120915530911765/acceptance.json`,backup-proof,production-apply/verify,source-postapply-proof,browser-proof,final-live-readback e replay-guard-proof. Continuidade: `reports/finance-october-rede1-review-1575120915530911765.md`.
