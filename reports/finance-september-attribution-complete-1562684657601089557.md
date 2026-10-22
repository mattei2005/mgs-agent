# Setembro2026 — atribuição do ponto6 aplicada e validada

## Autoridade e vigência

Rodolfo1562684657601089557, thread1545426987756298340, determinou:
- NewsounDE integralmenteKelly/G005.
- Zuout eZuoutFinanzas emsetembro: G002→MGS;G006→Nicolas, segundo osmarcadores do fechamento, sem corte de19/09.
- WavesBee eWavesBeeFinanzas integralmenteIsliago/G003.

Esta decisão substitui a proposta anterior de transferir osresíduosWavesBee paraMGS. Escopo somente setembro/2026,sem modificar ingestão global ou meses anteriores/futuros. Fonte financeira: planilha1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA,SB Rede1/gid565588781,relida integralmente. A atribuição explícita doowner governa as exceções; a planilha continua governando os valores.

O usuário perguntou o que estava errado noYolokfx; isso NÃO autorizou nova distribuição. Mantida a decisão ativaFINANCE-GAM-YOLO-1547678046553636905/canonical_keyfinance.revenue.gam.yolokfx.september2026:01–09/09 porSB/gestor,complementoG002. Explicado na própria thread que a diferença é uma exceção de identificação, não receita ausente. O totalYoloCAD132197.18 confere e nenhum fatoYolo foi alterado.

## Aplicação e totais por gestor

A aplicação redistribuiu receita sem alterar o total de cada site/país/dia/moeda:
- NewsounDE: transferidosCAD90.795476379394158396 deMGS paraKelly; fechamentoKellyCAD385.12895639249242094246,exibido385.13;MGSzero.
- Zuout: transferidosCAD25.8473800166790513181 deNicolas paraMGS; fechamentoG002CAD36.1808665834352230181/G006CAD705.20658648921179360149,exibidos36.18/705.21.
- ZuoutFinanzas: transferidosCAD5.725990965298340229 deNicolas paraMGS; fechamentoG002CAD37.878170986689454072/G006CAD252.86823540046865688246,exibidos37.88/252.87.
- WavesBee eFinanzas: **nenhum ajuste financeiro necessário**; suas receitas já estavam inteiramente emIsliago. Comparação dos fatos antes/depois igual.
- Yolokfx: todos osfatos antes/depois iguais.

Implementação:46overlaysCAD e8destinos nativos determinísticos,fonte original eIDs preservados,sem reescrever tagsoriginais. Redução da origem e aumento do destino na mesma transação. As estratégias permanecemBOT/-d nos sites alterados;Yolo mantém-s/direto. Plano temdelta agregadoCAD0E-20. Nenhuma duplicação,despesa adicional,alteração de câmbio,revshare,inválidos,rateio oucutoff.

## Efeito na remuneração — não pagamento

No mesmo snapshot1663→1664 e nas mesmas cotações:
- Kelly:BRL3927.60→3946.78,delta+19.18.
- Nicolas:BRL28497.33→28487.80,delta-9.53.
- Ícaro:3000→3000;Isliago:12465.73→12465.73;Joe:3175.55→3175.55.

Essas são remunerações calculadas/devidas, não pagamentos executados. O ledger ficou exatamente igual. O resultado após remunerações refletiu esse recálculo; receita,gastos,impostos eDespesasGerais permaneceram iguais em precisão monetária. Os últimos dígitos abaixo da precisão monetária podem variar pelo agrupamentoDecimal, com controles completos e nenhumdelta emcentavos. Cotações automáticas posteriores continuam podendo atualizar conversões pelas regras já existentes.

## Backup, ensaio e segurança

- Backup remoto:`/home/zeus/mgs-finance-backups/attrib-close-1562684657601089557/finance-before.dump`.
- Cópia local privada/ignorada:`apps/finance-system/private/september-closing-1562564679400951829/attrib-before.dump`.
-149516904bytes,SHA25661d0ba1ac0e893c01aa0c51d57d0e1fa9cb93069e9687ad86f51ed831226acfa.
- Restore materializado`mgs_finance_attrib_1562684657601089557`,242cenários com fingerprintsiguais.
- Stage`/home/mgsfinance/stage-attrib-1562684657601089557`:65arquivos de código;1417arquivos/fixtures/dependências/Node hash-verificados.
- Ensaio,aplicação e verificaçãoidempotente no banco restaurado passaram antes deprodução.
- Produção: revisão1663→1664,audit4981/SEPTEMBER_MANAGER_ATTRIBUTION_RECONCILED,recoveryimutável`recovery-attrib-1562684657601089557`.
- Financeirofinal:4285fatos/2246additions. Todas asadditions originais preservadas,mais54registros auditáveis.
- Proteções:admissão,backup,lock/CAS,uma transação,verificação de todos osoutroscenários eledger,audit e readback. Reexecução reconhece exatamente54registros e não reaplica.
- Backups,stage e banco restaurado retidos; nenhuma exclusão. Nenhuma mudança em código produtivo,serviço,cron,credencial,permissão ou schema.

## Intercorrência recuperada

A primeira tentativa debackup expirou após30s esperando admissão exclusiva,antes de qualquer backup/escrita financeira. O holder real era olookup worker legítimo emlease compartilhada durante seu long-poll de até65s. Estado de releasecommitted; origem da última publicação de cotações conciliada em audit/inventário. O caller passou a esperar até120s,preservando a mesma trava; retry concluiu backup/restore normalmente. Não houve kill,restart,bypass ou indisponibilidade financeira. Aespera120s também foi aplicada ao runner deste fechamento.

## Validações

-132controles site/país/data/gestor emcentavos e66totais diários preservados; releitura independenteDecimalPASS.
- Todos os cinco renders de gestor reconciliados; detalhesKelly/NewsounDE,Nicolas/Zuout+Finanzas,Isliago/WavesBee+Finanzas conferidos por dia e mês.
- API/UI públicas autenticadas:desktop1440/mobile390,22checksPASS,zeroerrosJS,zeroPOSTfinanceiro,semoverflow e reloadOK. Sessão de validação revogada e401confirmado.
- Monitor financeiro15/15PASS,sem alerta e semwritefinanceiro.
- Rede1CAD778884.56;Rede2USD209644.93;M2USD705.00;FacebookUSD500749.61;GoogleBRL111547.89 preservados.
- Não é declaração de liquidação/pagamento ou resolução de fontes semdados; taxas/provisoriedade seguem seu ciclo independente.

## Evidências e continuidade

Evidências:`apps/finance-system/private/september-closing-1562564679400951829/point6-*`,scripts preservados no mesmo diretório,`point6-final-independent-checks.json`,`point6-completion-sha256.json`;provasAPI/UI em`private/attribution-1562684657601089557/`.

CheckpointZEUS-FINANCE-SEPT-CLOSE-1562562282838429729;decisão canônicafinance.2026-09.manager-attribution-closing. Procedimento e limites salvos em`mgs-finance-dashboard/references/adops-monthly-source-reconciliation.md`.

Os ajustes explicitamente autorizados estão concluídos. A dúvida sobreYolo foi esclarecida sem transformar a pergunta em autorização de mudança; sua exceção anterior permanece vigente.
