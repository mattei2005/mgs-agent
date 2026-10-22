# Setembro — ponto6: atribuição de receita aos gestores

Pedido1562675688522129499: explicar, sem executar transferência de receita ou alteração financeira. FonteSB1/SB2 relida integralmente sem delta. Dashreadback1661,cadastro19; pontos1–5preservados.

## O que está sendo comparado

Comparação atual de receita original por rede/site/dia/gestor, usando os overlays jáaplicados, não os antigos valores pré-fechamento. Total por site/moeda confere; restam diferenças na identidade do gestor emseis sites, todas naRede1/CAD. Tags atuais foram confrontadas também comf.manager; zero conflito interno entre identidade e tag nas linhas utilizadas.

Rede2 não tem diferença monetária de gestor após oponto2. M2 mantém a atribuiçãoUS/G001/BOT expressamente confirmada no ponto5.

## Cinco diferenças menores — proposta, ainda não aplicada

Se adotadas as identificações do fechamento:
- NewsounDE: transferirCAD90.795476379394158396 deG002/MGS paraG005/Kelly; hojeKelly294.33348001309826254646 eMGS90.795476379394158396, fonteKelly385.1289563924924236597/MGS0.
- Zuout: transferirCAD25.8473800166790513281 deG006/Nicolas paraG002/MGS.
- ZuoutFinanzas: transferirCAD5.7259909652983411566 deG006/Nicolas paraG002/MGS.
- WavesBee: transferirCAD0.2157071584548971452 deG003/Isliago paraG002/MGS.
- WavesBeeFinanzas: transferirCAD0.012742353809102358 deG003/Isliago paraG002/MGS.

São valores de receita brutaCAD, não comissões ou pagamentos. Nos cinco casos, a estratégia continua-d/BOT; não há mudança-d/-s proposta. Datas e países devem permanecer os mesmos. A divergência entre tags atuais do fechamento e registros das importações anteriores está comprovada; não foi atribuída uma causa externa específica a cada revisão.

## Yolokfx — exceção ativa, não erro a corrigir cegamente

Registro institucional ativoFINANCE-GAM-YOLO-1547678046553636905, canonical_keyfinance.revenue.gam.yolokfx.september2026, fonte`docs/gam-revenue-claude-yolo-september-2026.md`, seçãoDecisão ativaYolokfx.

Rodolfo confirmou que o histórico01–09/09 não voltaria comutm_medium confiável. Regra vigente: receitaSBAdGroup paraG001/G003/G004/G005/G006 por conta/gestor;G002-s recebe o complemento do totalGAM diário. A regra supersede o fallback simplista de concentrar tudo semidentificação emMGS. No ponto1, os valores do fechamento foram corrigidos sem revogar essa exceção: preservadas as parcelas dos outros gestores e ajustado o complementoG002 nosdiascomdedução.

Após as correções, o totalYolokfx confereCAD132197.18 nos dois lados. Se a distribuição do novo relatório fosse copiada cegamente, transfeririaCAD9041.6023004580030791395 dos gestores paraMGS, com reduções analíticas:Ícaro610.08937102858580756;Isliago96.7168399076009343;Joe4159.81958410852493056;Kelly2675.4671457757867642;Nicolas1499.5093596375053464. Os centavos individuais arredondados podem somar umcentavo diferente do total calculado antesdoarredondamento.

A diferença fica somente entre02–09/09 dentro daexceção01–09; a partir10/09 asatribuições conferem emcentavos. A estratégiaYolo permanece-s/direto. Não é autorização para transferir de novoG006→MGS por cutoff19/09, nem para superseder uma decisão anterior apenas para forçar tagsiguais.

**Recomendação:** preservar a exceçãoYolokfx jáaprovada e tratar somente oscinco casos menores como proposta de correção pelo fechamento. Não pedir novamente autorização para aexistência daexceção; uma revogação exigiria decisão explícita deRodolfo.

## Efeito financeiro e limite

Trocar o gestor não muda a receita total dosite, mas muda o resultado individual e pode alterar piso/7%/10%. Assim, o lucro final daempresa após remunerações pode mudar, mesmo comgrossigual. G002 éMGS e não recebe comissãoexterna. Antes daaplicação, congelar baseline de remuneração/ledger, calcular osreflexos e validar todos osgestores; nunca transformar o valor brutoCAD diretamente em descontoBRL nem mexer em pagamentos registrados.

Neste turno foram feitas apenas leituras e análises. Não foram aplicadas ascinco propostas, transferidosvaloresYolo, alteradas regras, comissões ou pagamentos.

Evidências privadas:`apps/finance-system/private/september-closing-1562564679400951829/point6-before-*.json`,point6-dimensional-comparison.json,point6-site-attribution-detail.json epoint6-source-verification.log. Próximo passo proposto: autorização para oscinco casos menores, preservandoYolokfx e pontos1–5.
