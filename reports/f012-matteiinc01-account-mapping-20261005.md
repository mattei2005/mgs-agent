# F012 — contas SQL MatteiInc01

Fonte: Rodolfo 1556744996760059985, thread1551768281688580096; runtime 2026-10-05T19:18:41.603826+00:00.

## Problema, causa e proposta
- Problema:74 identidades SQL não sistêmicas existentes, todas localhost, todas com38 privilégios globais;72 possuem WordPress configurado e autenticado,2 são resíduos sem consumidor identificado.
- Causa técnica confirmada:concessões globais no MariaDB. Origem histórica de quem fez os grants e relação com invasão não atribuídas. Sem GRANT OPTION não remove SELECT/INSERT/UPDATE/DELETE/DROP,FILE,SUPER,SHUTDOWN ouCREATE USER globais.
- Proposta:para72 contas com consumidor,aprovar limitação ao próprio banco em pequenos canários com rollback/preservação de senha/conteúdo. Para2 resíduos,confirmar dependências/retirada antes de qualquer alteração. Não há autorização nova de alteração/exclusão neste pedido.
- MariaDB127.0.0.1:3306 impede acesso externo direto;não impede alcance lateral por credencial de um site local. SQL admin não é rootSSH.

## Cobertura e limites
-75WebApplications atuais:74WordPress com autenticação PASS;1mgs-finance-dash sem mapeamento MariaDB afirmado.
-72contas globais com sites;2 globais sem consumidor noescopo: bkpDicasfinancas_1748616480 e zionnmedia_1759949932.
- jobsDeolhonoworldCom_1783049106 e wantabrand_1754872464 possuem WordPress autenticado e zero grantsglobais;fora das74. root/mysql são sistêmicas e ficamfora do finding.
-103arquivos deconfigs/crons/serviços pesquisados:zero referência às2identidades;zero conexões na amostra. Isso não prova não uso histórico ou ausência de consumidor externo/manual.
- RunCloud: bkp-dicasfinancas2393888,phpmyadmins2486791,zionnmedia2578846 retornam404. ApenasZionn teveorigemreconciliada com encerramento explícito do dono;outrasretiradas nãoatribuídas,não classificadascomoanomalia.
- Nenhum banco com nome exatamenteigual às2contas residuais apareceu emSCHEMATA; nenhuma destas2apareceu no catálogoRunCloud de usuários SQL. Isso não autoriza exclusão nem prova todos seus vínculos históricos.
- Zionnfora da operaçãoMGS;nenhuma retomada/ação de site. Schemas temporárioshistoricamente ligados aZionn permaneceramintactos,fora doescopo de alteração.
- API429inicial:concurrency reducida e2.2segundo de pacing;75batches completos/uniques;limite exatodo provider nãofoiafirmado.
- Nenhuma credencial,grant,site,table,schema,cron deprodução ou conteúdo alterado. Somente artefatos locais de governança e skill.

## Lista completa
Todas @localhost. Nas72 contas mapeadas,o banco tem exatamenteo mesmo nome do usuário. Todas têm o mesmo risco de grantsglobais;ausência de tráfego nãofoi afirmada.

1. **allincraft.com** — `allincraft_5729`; banco `allincraft_5729`; app `allincraft` ID1790021; autenticação PASS; global38; propor own-schema sem exclusão.
2. **amazingxjobs.com** — `amazingxjobs_17099`; banco `amazingxjobs_17099`; app `amazingxjobs` ID1790018; autenticação PASS; global38; propor own-schema sem exclusão.
3. **app.conectageral.com** — `appConectageral_1787324091`; banco `appConectageral_1787324091`; app `app-conectageral` ID2996530; autenticação PASS; global38; propor own-schema sem exclusão.
4. **app.portalrelevante.com** — `appPortalrelevanteCom_1733178910`; banco `appPortalrelevanteCom_1733178910`; app `app-portalrelevante-com` ID2121416; autenticação PASS; global38; propor own-schema sem exclusão.
5. **bahuye.net** — `bahuye_1769621633`; banco `bahuye_1769621633`; app `bahuye` ID2716439; autenticação PASS; global38; propor own-schema sem exclusão.
6. **Sem consumidor atual identificado** — `bkpDicasfinancas_1748616480`; contaSQL presente/global38;WebApplication histórica404; nenhuma retirada automática. Revisar identidade residual separadamente.
7. **bkp.folhadaterra.com.br** — `bkpFolhadaterra_1754260328`; banco `bkpFolhadaterra_1754260328`; app `bkp-folhadaterra` ID2486831; autenticação PASS; global38; propor own-schema sem exclusão.
8. **careersjobsad.com** — `careersjobsad_16945238`; banco `careersjobsad_16945238`; app `careersjobsad` ID1790027; autenticação PASS; global38; propor own-schema sem exclusão.
9. **conectageral.com** — `conectageral_1787259636`; banco `conectageral_1787259636`; app `conectageral` ID2995514; autenticação PASS; global38; propor own-schema sem exclusão.
10. **consultarfinanca.info** — `consultarfinanca_1769625131`; banco `consultarfinanca_1769625131`; app `consultarfinanca` ID2716523; autenticação PASS; global38; propor own-schema sem exclusão.
11. **deolhonoworld.com** — `deolho_16799`; banco `deolho_16799`; app `deolho` ID1790008; autenticação PASS; global38; propor own-schema sem exclusão.
12. **dicasfinancas.info** — `dicasfinancas_1748630298`; banco `dicasfinancas_1748630298`; app `dicasfinancas` ID2394148; autenticação PASS; global38; propor own-schema sem exclusão.
13. **digitaltrustadx.com** — `digitaltrustadxbd_16`; banco `digitaltrustadxbd_16`; app `digitaltrustadx` ID1790029; autenticação PASS; global38; propor own-schema sem exclusão.
14. **eggbev.com** — `eggbevbd`; banco `eggbevbd`; app `eggbev` ID1790004; autenticação PASS; global38; propor own-schema sem exclusão.
15. **finanzas.eggbev.com** — `eggbevbd_finanzas`; banco `eggbevbd_finanzas`; app `finanzas-eggbev` ID2692284; autenticação PASS; global38; propor own-schema sem exclusão.
16. **eng.wrnoticia.com** — `engwrnoticiabd`; banco `engwrnoticiabd`; app `eng-wrnoticia` ID1790000; autenticação PASS; global38; propor own-schema sem exclusão.
17. **esp.noticiainforme.com** — `espnoticiainf_7458`; banco `espnoticiainf_7458`; app `esp-noticiainforme` ID1789989; autenticação PASS; global38; propor own-schema sem exclusão.
18. **es.seuprimeiroempregoam.com** — `esSeuprimeiroempregoam_1752629011`; banco `esSeuprimeiroempregoam_1752629011`; app `es-seuprimeiroempregoam` ID2459505; autenticação PASS; global38; propor own-schema sem exclusão.
19. **es.wrnoticia.com** — `eswrnoticiabd`; banco `eswrnoticiabd`; app `es-wrnoticia` ID1789998; autenticação PASS; global38; propor own-schema sem exclusão.
20. **everythingtented.com** — `everythingtented_1769623065`; banco `everythingtented_1769623065`; app `everythingtented` ID2716484; autenticação PASS; global38; propor own-schema sem exclusão.
21. **financescredit.com** — `financescredit_620`; banco `financescredit_620`; app `financescredit` ID1789985; autenticação PASS; global38; propor own-schema sem exclusão.
22. **financespost.com** — `financespost_16963`; banco `financespost_16963`; app `financespost` ID1789982; autenticação PASS; global38; propor own-schema sem exclusão.
23. **finance.topfeed.fun** — `financeTopfeed_1787177525`; banco `financeTopfeed_1787177525`; app `finance-topfeed` ID2994275; autenticação PASS; global38; propor own-schema sem exclusão.
24. **finanzas.conectageral.com** — `finanzasConectageral_1787335795`; banco `finanzasConectageral_1787335795`; app `finanzas-conectageral` ID2996688; autenticação PASS; global38; propor own-schema sem exclusão.
25. **finanzashispano.com** — `finanzashispano_6723`; banco `finanzashispano_6723`; app `finanzashispano` ID1789976; autenticação PASS; global38; propor own-schema sem exclusão.
26. **finanzas.topfeed.fun** — `finanzasTopfeed_1787187397`; banco `finanzasTopfeed_1787187397`; app `finanzas-topfeed` ID2994332; autenticação PASS; global38; propor own-schema sem exclusão.
27. **folhadaterra.com.br** — `folhadaterra_16836`; banco `folhadaterra_16836`; app `folhadaterra` ID1790030; autenticação PASS; global38; propor own-schema sem exclusão.
28. **growthnetworkinc.com** — `growthnetworkinc_1719368309`; banco `growthnetworkinc_1719368309`; app `growthnetworkinc` ID1847642; autenticação PASS; global38; propor own-schema sem exclusão.
29. **informegeral.com** — `informegeral_4910`; banco `informegeral_4910`; app `informegeral` ID1790038; autenticação PASS; global38; propor own-schema sem exclusão.
30. **jislainemattei.com** — `jislainemattei_3891`; banco `jislainemattei_3891`; app `jislainemattei` ID1790044; autenticação PASS; global38; propor own-schema sem exclusão.
31. **jobs.conectageral.com** — `jobsConectageral_1787261049`; banco `jobsConectageral_1787261049`; app `jobs-conectageral` ID2995522; autenticação PASS; global38; propor own-schema sem exclusão.
32. **kievportal.com** — `kievportal_170839`; banco `kievportal_170839`; app `kievportal` ID1789932; autenticação PASS; global38; propor own-schema sem exclusão.
33. **lyzmo.com** — `lyzmo_170249`; banco `lyzmo_170249`; app `lyzmo` ID1789974; autenticação PASS; global38; propor own-schema sem exclusão.
34. **finanzas.lyzmo.com** — `lyzmo_170249_finanzas`; banco `lyzmo_170249_finanzas`; app `finanzas-lyzmo` ID2692291; autenticação PASS; global38; propor own-schema sem exclusão.
35. **marketingdigitalad.com** — `marketingdbd_0091`; banco `marketingdbd_0091`; app `marketingdigitalad` ID1789928; autenticação PASS; global38; propor own-schema sem exclusão.
36. **matteiservicesinc.com** — `matteiservices_1713`; banco `matteiservices_1713`; app `matteiservicesinc` ID1790045; autenticação PASS; global38; propor own-schema sem exclusão.
37. **newsfolha.com** — `newsfolha_7982`; banco `newsfolha_7982`; app `newsfolha` ID1789971; autenticação PASS; global38; propor own-schema sem exclusão.
38. **jobs.newsfolha.com** — `newsfolhaJobs_1747496368`; banco `newsfolhaJobs_1747496368`; app `newsfolha-jobs` ID2373845; autenticação PASS; global38; propor own-schema sem exclusão.
39. **newsoun.com** — `newsoun_170249`; banco `newsoun_170249`; app `newsoun` ID1789970; autenticação PASS; global38; propor own-schema sem exclusão.
40. **finanzas.newsoun.com** — `newsoun_170249_finanzas`; banco `newsoun_170249_finanzas`; app `newsoun-finanzas` ID2692293; autenticação PASS; global38; propor own-schema sem exclusão.
41. **de.newsoun.com** — `newsounDe_1720052132`; banco `newsounDe_1720052132`; app `newsoun-de` ID1858527; autenticação PASS; global38; propor own-schema sem exclusão.
42. **noticiainforme.com** — `noticiainforme_5678`; banco `noticiainforme_5678`; app `noticiainforme` ID1789967; autenticação PASS; global38; propor own-schema sem exclusão.
43. **portalbrasilnews.com** — `portalbrasilnews_0394`; banco `portalbrasilnews_0394`; app `portalbrasilnews` ID1790046; autenticação PASS; global38; propor own-schema sem exclusão.
44. **portal.folhadaterra.com.br** — `portalFolhadaterrabds`; banco `portalFolhadaterrabds`; app `portalFolhadasbd` ID1790047; autenticação PASS; global38; propor own-schema sem exclusão.
45. **finanzas.portalrelevante.com** — `portalrelev_65612_finz`; banco `portalrelev_65612_finz`; app `portalrelevante-finanzas` ID2692310; autenticação PASS; global38; propor own-schema sem exclusão.
46. **portalrelevante.com** — `portalrelevante_1733365612`; banco `portalrelevante_1733365612`; app `portalrelevante` ID2124791; autenticação PASS; global38; propor own-schema sem exclusão.
47. **prospectcleaning.com** — `prospectcleaninbds`; banco `prospectcleaninbds`; app `prospectcleaning` ID1790048; autenticação PASS; global38; propor own-schema sem exclusão.
48. **prospecthomeimprovement.com** — `prospecthomeimprovement`; banco `prospecthomeimprovement`; app `prospecth` ID1790049; autenticação PASS; global38; propor own-schema sem exclusão.
49. **receitasdescomplicada.com.br** — `receitasdescomplicada`; banco `receitasdescomplicada`; app `receitasdescomplicada` ID1789965; autenticação PASS; global38; propor own-schema sem exclusão.
50. **revistacafe.com.br** — `revistacafe_0274`; banco `revistacafe_0274`; app `revistacafe` ID1790050; autenticação PASS; global38; propor own-schema sem exclusão.
51. **s4blindsandshades.com** — `s4blindsand_8596`; banco `s4blindsand_8596`; app `s4blindsandshades` ID1790051; autenticação PASS; global38; propor own-schema sem exclusão.
52. **scorexboost.com** — `scorexboost_1696`; banco `scorexboost_1696`; app `scorexboost` ID1789964; autenticação PASS; global38; propor own-schema sem exclusão.
53. **seniormenu.com** — `seniormenu_1769621205`; banco `seniormenu_1769621205`; app `seniormenu` ID2716426; autenticação PASS; global38; propor own-schema sem exclusão.
54. **seuprimeiroempregoam.com** — `seuprimeiroemp_bd17`; banco `seuprimeiroemp_bd17`; app `seuprimeiroempregoam` ID1789961; autenticação PASS; global38; propor own-schema sem exclusão.
55. **empleo.seuprimeiroempregoam.com** — `seuprimeiroempleo_bd17`; banco `seuprimeiroempleo_bd17`; app `seuprimeiroempleo` ID2692331; autenticação PASS; global38; propor own-schema sem exclusão.
56. **sotuz.com** — `sotuz_1769622821`; banco `sotuz_1769622821`; app `sotuz` ID2716470; autenticação PASS; global38; propor own-schema sem exclusão.
57. **jobs.scorexboost.com** — `sscorexboostJobs_1761693330`; banco `sscorexboostJobs_1761693330`; app `sscorexboost-jobs` ID2603187; autenticação PASS; global38; propor own-schema sem exclusão.
58. **sunshinebeautysupplier.com** — `sunshinebeauty`; banco `sunshinebeauty`; app `sunshinebeautysupplier` ID1790052; autenticação PASS; global38; propor own-schema sem exclusão.
59. **tapsaga.com** — `tapsaga_1696`; banco `tapsaga_1696`; app `tapsaga` ID1790053; autenticação PASS; global38; propor own-schema sem exclusão.
60. **topfeed.fun** — `topfeed_1787189584`; banco `topfeed_1787189584`; app `topfeed` ID2994339; autenticação PASS; global38; propor own-schema sem exclusão.
61. **vagaaqui.com** — `vagaaqui_5498`; banco `vagaaqui_5498`; app `vagaaqui` ID1789955; autenticação PASS; global38; propor own-schema sem exclusão.
62. **finance.wantabrand.com** — `wantabrafin_1754872464`; banco `wantabrafin_1754872464`; app `finance-wantabrand` ID2696446; autenticação PASS; global38; propor own-schema sem exclusão.
63. **wavesbee.com** — `wavesbee_17024`; banco `wavesbee_17024`; app `wavesbee` ID1789948; autenticação PASS; global38; propor own-schema sem exclusão.
64. **finanzas.wavesbee.com** — `wavesfinan_17024`; banco `wavesfinan_17024`; app `finanzas-wavesbee` ID2696451; autenticação PASS; global38; propor own-schema sem exclusão.
65. **wrnoticia.com** — `wrnoticia_home_8912`; banco `wrnoticia_home_8912`; app `wrnoticia-home` ID1789942; autenticação PASS; global38; propor own-schema sem exclusão.
66. **wr.wrnoticia.com** — `wrwrnoticiabd`; banco `wrwrnoticiabd`; app `wr-wrnoticia` ID1789943; autenticação PASS; global38; propor own-schema sem exclusão.
67. **zerhu.com** — `zerhu_1769621316`; banco `zerhu_1769621316`; app `zerhu` ID2716430; autenticação PASS; global38; propor own-schema sem exclusão.
68. **Sem consumidor atual identificado** — `zionnmedia_1759949932`; contaSQL presente/global38;WebApplication histórica404; nenhuma retirada automática. Revisar identidade residual separadamente.
69. **ziwus.com** — `ziwus_1769622918`; banco `ziwus_1769622918`; app `ziwus` ID2716475; autenticação PASS; global38; propor own-schema sem exclusão.
70. **zuout.com** — `zuout_170991`; banco `zuout_170991`; app `zuout` ID1789940; autenticação PASS; global38; propor own-schema sem exclusão.
71. **finanzas.zuout.com** — `zuout_finanzas_170991`; banco `zuout_finanzas_170991`; app `zuout-finanzas` ID2692314; autenticação PASS; global38; propor own-schema sem exclusão.
72. **zuploader.com** — `zuploader_1769622992`; banco `zuploader_1769622992`; app `zuploader` ID2716480; autenticação PASS; global38; propor own-schema sem exclusão.
73. **zytiva.com** — `zytiva_17024`; banco `zytiva_17024`; app `zytiva` ID1789935; autenticação PASS; global38; propor own-schema sem exclusão.
74. **finanzas.zytiva.com** — `zytiva_finanzas_17024`; banco `zytiva_finanzas_17024`; app `zytiva-finanzas` ID2692318; autenticação PASS; global38; propor own-schema sem exclusão.

## Evidência
-data/f012-matteiinc01-account-mapping-20261005.json
-/root/.hermes/profiles/zeus/workspace/f012-matteiinc01-1556744996760059985
-source metadata/config consumers and exact74-account reconciliation persisted privately.
