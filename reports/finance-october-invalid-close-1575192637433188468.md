# Outubro/2026 — conciliação bancária por taxa efetiva Rede1

## Autoridade

Rodolfo1575192637433188468 confirmou a proposta1575192544994795552: aplicar0.12745966%emInválidosSB Rede1 apenasoutubro2026, incluindo o efeito indireto deFincgriffin no cartãoRede2. Banco informado porRodolfo1575190845873979433:USD1250860.59; literaloriginal `USD 1.250.860.59`. Trata-se detaxaefetivadeconciliação, não comprovação de tráfego inválido pelo provedor. Supersede a pendência da proposta `reports/finance-october-invalid-proposal-1575191740409843723.md`.

## Aplicação e readback

Controle `principal|Agosto 2026|L1`, na competência`workspace-2026-10`:0.000823→0.0012745966;percentual0.0823%→0.12745966%,fixed/confirmed. IDlegadoAgosto nãoaltera o mês de aplicação.

Uma única chamada à API existente `/api/scenarios/workspace-2026-10/rates`, autenticada porMFA/CSRF, sob admissãoexclusiva e locksGAM/spend/quotes/history. Baselineatual2206 e expectedrecalculado/validado dentrodoslocks;produção2206→2207,audit7878`FINANCIAL_RATE_CHANGED`. Recoveryimutável `recovery-invalid-oct-1575192637433188468`. Readback exato deoverrides/additions/result e auditapóscommit; nenhuma repetição financeira.

Resultado final confirmado naAPI/DOMdesktop/mobile e porPythonDecimal:

- Rede1 líquidoUSD1062061.17,comCAD1535984.726528294007030562preservado naexibiçãooriginal.
- Rede2 líquidoUSD188799.42.
- SomaUSD1250860.59.
- RecebimentoinformadoUSD1250860.59.
- DiferençaUSD0.00.

USD/CAD1.44623preservado;grossCAD1708827.762198232372209362 eRede2grossUSD209970.266004744825650338 preservados. InválidosRede1CAD2178.066055683475505357. O controle daRede2 nãofoialterado; seu líquidocaiuUSD0.19porFincgriffinUSDherdarL1,dependênciaexplicitamenteconfirmada. Revsharepercentual intacto,descontorecalculadopela regraexistente.

Todososfatosmantêmgross,gastos,site,país,gestor,data,share,tax,origens eclassificações. CAD/USD,M2/AV,gastosFB/Google,SMS/recargas,despesasgerais,rateio,câmbios eledger preservados. Demaiscenáriosfingerprintsiguais dentrodatransação operacional. Remuneraçõesrecalculadaspelasregrasexistentes;nenhumpagamentoregistrado.

## Backup e ensaio

Dump remoto `/home/zeus/mgs-finance-backups/invalid-october-1575192637433188468/finance-before.dump`, cópialocalforaGit verificada;238071377bytes,SHA256 `6576e3b747966d351fd0fe759bfe441a40fe0419898b173213b97dc9eda9f0a2`. Restore real `mgs_finance_invoct_1575192637433188468`,324cenáriosfingerprintsiguais. Stage `/home/mgsfinance/stage-invoct-1575192637433188468`,módulos/fixtures/Node/dependênciasHTTP/public hashverificados,ownerisoladomgs_pg;produção/grants/pg_hba intactos.

Ensaio real da mesma API noPostgreSQLrestaurado;aplicaçãoisolada,cinco gestorespass,replaycomrevisionantigarejeitado409 semsegundacommit. Expectedprodutivo voltou a sercalculado no baselinefrescodentrodo lock; nãoreaplicadaasimulaçãoBRLantigaapósatualizaçõesautomáticasdeUSD/BRL.

## Aceitação pública

14vistas:ConferênciaRodolfo/Geiziandesktop/mobile e5gestoresnasduaslarguras. Taxaexatafixed/confirmed lida em`workspace.rates`,novoslíquidosvisíveis,expansões/reload/CADpreservado,5summarycontrolspass;zeroJS/POSTfinanceiro duranteverificação. Sessões temporáriasdestaoperação encerradas e revogação conferida.

## Recuperações — sem replay financeiro

- PrimeiroensaioPGlite inseriuowner emfinance_users,cujoCHECKadmiteparceiros/gestores. Removidaapenasainserçãodafixture;ownerpermaneceuconfigauthisolada.
- Ensaio local revelou refresh deFX porlive-quoteslocaldesatualizado. Mantidaguardadepreservação;ensaio migrado ao runtimecopiadodaprodução eDBrestaurado,semalterarcotaçõesativas.
- RuntimecalculatóriofaltavaExpress/publicparaAPIHTTP. Fechadaaclosureexplicitadospacotesinstalados e30assetspúblicoscomhash;nenhuminstall/patchprodutivo.
- APIfinanceiraconcluiuefoirelida;logoutposterior recebeuresetdeconexão. Serviçosfinanceiro/socket/PGconfirmadosactive. Sessãotemporáriaúnica correlacionadaaoLOGIN_SUCCESS7877,created_at`2026-11-25 17:04:55.843255+00`;revogadaindividualmente e relida,demais sessõespreservadas. Join inicialviadataJSperdeumicrossegundos;corrigidoparaSQLcomprecisãooriginal. Auditorialogoutdescritiva registradacomoZeus,semcredenciais.
- Validadorpublicopresumiaoverrides/rateemadditions;payloadrealfornece`rates`. Corrigido apenasovalidador e repetidaaceitaçãocompleta;nenhumaaplicaçãorepetida. Novasleiturasautenticadas usamConnectioncloseparanãoreutilizarconexãoociosa;logout/401 passaram.

## Fontes

`apps/finance-system/private/invalid-october-1575192637433188468/`:baseline,before,backup-proof,stage-proof,expected,production-before,production-rehearse,recovery,after,applied,apply-logout,API/DOMscreenshots,browser-proof,logout-proof eacceptance.json. Banco é valorinformadopelotitular,nãoextratoconsultado. Nenhumdeploy/restartprodutivo foi necessário.
