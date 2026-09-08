# Manager access, history exceptions and carried balances

Authority: Rodolfo1546858367635685396, reply to explicit critical confirmation asking creation/activation of Joe, Isliago, Kelly and Ícaro with1Password. Direct mid-turn: AprilS19deleted; ignoreNicolasJan/Febrefs; ROIrepairallowedwithoutvaluechanges; ÍcarocommissionssinceMarch, prior salaryonly; questionJuly135.01/August749.29. Canonical identity `context/team.md`; decisions `docs/finance-system-product-direction.md`; report `reports/finance-manager-access-1546858367635685396.md`.

## Active access (supersedes Nicolas-only pilot)
- Fournew logins `joe`, `isliago`, `kelly`, `icaro`, enabled manager role. Nicolasexistingpreserved. Display Ícaro, never create Georgeasasecondperson. `manager-layouts.json` maps publicicaro to immutablebookgeorge. Preserve graphkeys, sourceSheetnames/IDs and financialvalues. Appsaccess != agents/Discordauthorization.
- 1Passwordvault MGS Conteúdo; titles `MGS Finance - {username} - dash.mgsdigitalcorp.com`. Generated32charpasswords/readback; never printorlog fields/cookies/salt/hash. No forcedfirstloginpasswordreset implemented.
- Managerworkspace derives identity from auth, not query, and rejects any foreignmanagerquery403. Ownercanpreview explicitmanager. Managersees only ownbookblocks, summaries, remuneration, ledger and ownprofile. Never grant fullshareddomain results based onlyonsiteownership.
- `managerView` has explicitmetadataforeachbook (Joe5/Kelly6/Isliago8/Ícaro9/Nicolas8blocks). Sourcegraphomitslabels, so use completeauditcapturefor metadata, not partialinferredheaders. GeorgeOpenzedrow207 hasirregularUS/BR/GB/TOTALheaders: normalize display labels with originalsource_labelretained. MonthlyROIdirectenginevalueatblock.row+33; dailyrow=block.row+1+day. Missingenginevaluesremainblank. WavesBeelabeloriginCADonlyAug/Sepmatchingapprovedcurrencychange.
- Generalize BOTH APIvalidations anddatabaseCHECKconstraints; changingonlyJS givesHTTP500onusercreation. `manager-access-migration.sql` replaces two constraints only, preservesroles/credentialguard/users/data, and requiresnotnullkeyformanager. Restoremigrationtestedfirst; actualcode/SQLschemafile aligned.

## Verification / release
- `deploy/manager-access-release.py` is one-shot boundedrelease: fouroldcodefiles+newmetadata, dualcode/PGbackup/hash/restore, isolatedDB, stageexercise, coherentappsocket+servicecutover (notHermes), finalschemafilebackup/sync, exacthash/servicechecks. No datasource/financialscenario/ledgerwrites in apppublication.
- Stage`mgs_finance_managers_1546858367635685396`, `/var/tmp/mgs-finance-managers-1546858367635685396`; remote backups `/home/zeus/mgs-finance-backups/1546858367635685396`; local `private/manager-access-1546858367635685396`. Preserveartifacts, no destructivecleanupauthorized.
- 52Node testsPASS (initial150stimeout, bounded188sretrycompleted). Stage5managers×17periods=85,396270dailyvalues,100negativetests,financialhashesunchanged. Public5reallogins,10monthchecks,10mobile/desktopchecks,70API403,logout401,0JSerrors.
- `manager-access-create.py` reconciles1Pitemtitle/ID andappusernamebeforeeachwrite. Existingenableduserisneverresetblindly. Savesperuserreadbackasprogress. Python-defaultHTTPrequestgot403; explicitUser-Agentworkedwithoutchangingsecurity. Publicbrowser harness usesinstalledChromium1234chrome-linux64, never alterprotected1228profiles.
- Loginrate10perIP/15min: reuseownercontext; do notloopnewownerloginsfornegativecrossusertests. Testsneverlogproductionpasswords; passinmemory/stdin. Failedfirststagecreationmade nouser; readafterfailurebeforemigrating/retry.

## Historical dispositions
January–Julyremainclosed,frozenvalues; NOhistoricalimportdonehere. MainandmanagerSheetsremainoriginalsources. ÍcarosalaryexistsbeforeMarchdespiteabsenceofJan/Febmanagercommissiontabs. Do notzeroorcalculatecommissionforthosemonths.
- RodolfoclearedAprilS19; liveemptyand22priorVALUEtargetsresolved. Notanagentdeletion.
- NicolasJan/FebP1/AF38 legacyrefs ignoredbyexplicitdecision: notanopenrepair, notzero, notpermissiontoexcludevalidNicolasdata.
- `tests/closed-roi-repair.py`: wholeJan/Febcapture,hash,validateonlyDIV0andROIheadersFN:FRrow100, exactformulaSUM(numerator)/denominator-1. Guard`IF(denominator=0,"",original)`onlyon132Jan+148Febcells; canaryandfullreadbackconfirmed280guardsand33165numericcellsidentical, otherformula/input/formattedvaluespreserved. AvoidblanketIFERRORhidingotherfailuretypes. Appliedone-shot; don'trerunprepareorrestorewithoutfreshscope/readback.

## Cash carry diagnosis and authorized restoration
**Later supersession:** Rodolfo1546866505663254599 chose July Jislaine1500 and August3000. `tests/july-salary-restore.py` wrote ONLYJulyO156−1500 after backup/hash; exact input diff1cell, JulyF132/AugustG129 returned0.7133221368276281. AugustSheetP157−3000 and dashpersonnel|1573000 preserved. No hardcoded balance write. July is NOT imported in dash, so don't claim its app payroll was edited. LiveAPI proved August previous71centavos and September previous equals August balance9152432centavos. July salary decision is no longer pending. Historical diagnosis below remains evidence of the cause, not the current value.

Rodolfo subsequently confirmed the expected automatic internal carry after Jan–Jul import. The future import must include closed results, adjustments, payments and balances, not merely site facts; replace August opening71 with linkage to July closure inside the dash. Preserve frozen history; don't query Sheet live or apply August payroll rules retroactively. Import and removing the fixed-opening exception remain unimplemented. September onward already calculates internal carry.

- JulyvalueisF129(notG129):135.0062095139292, fromJuneF132, unchangedversusearliercapture.
- AugustG129=`SUM('Julho 2026'!F132)` now−749.2866778631869; parenthesesindicateNEGATIVE, not+749.29. Earliercapture0.7133221368276281.
- Exactcomparisontool`private/navigation-1546682010066489394/july-sheet.json`versuslive: onlyinputchangeinJulyA99:O160isJislaineO156−1500→−3000. DependencyO156→N156→N160→H136→I136→I137→F103→F132→AugustG129. Extraexpense1500reducesGeizianhalf750, explainingentiredelta; paymentsandJulyF129unchanged. DoesnotidentifytheeditororproveauthorizationforJulyretroactivity.
- PreviousZeusJislainechangeaffectedDASHAugust2026–December2027only. SourceJulychangeisnotattributed; don'tclaimanomalyorblamewithoutcanonicalreconciliation.
- Before1546866505663254599, July1500vs3000neededRodolfodecision. Heconfirmed1500andtheboundedrestorationabovewasvalidated. Do notchangeG129bytyping0.71or0: itisalink. Dashopening0.71remainedpreservedandmatchesrestoredJuly; removalofitsfixedsourceawaitshistoricalimport.
