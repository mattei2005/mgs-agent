# Confirmação de atribuição AV e corte de Zuout

## Autoridade e escopo

- Rodolfo: mensagem `1551312942182441111`, thread `1545426987756298340`.
- Prévia aprovada: `1551308976061419554`; total USD722.61,329 linhas,21 domínios, exclusivamente C=D=E=`-` no AV detalhado de agosto2026.
- Todos os destinos da prévia foram aprovados. Única substituição: `cliquet.com`, USD45.95, G002/BOT → `us-cc-en`, nunca `br-car-br`.
- Openzed: transferência USD1.76 do subconjunto G001 para o dono G003 aprovada; parcela G001 fora deste filtro preservada. Openzed Finanzas: `es-cc-es` aprovado.
- Eggbev: preservar sufixos `-d`/`-s`, com Nicolas/G006 e `us-cc-en`.
- Nenhuma nova receita: USD722.61 já integra o total AV.

## Supersessão posterior — setembro preservado

Rodolfo `1551316692565499956` esclareceu que pode ter confundido a data e determinou manter setembro como está: G006 com Nicolas e G002 com MGS. O corte19/09 abaixo é histórico, não uma regra ativa. Os seis fatos G006 de15–18/09 permanecem intactos; não há mais decisão pendente sobre sua transferência. Nenhuma mudança financeira ou no importador é necessária. Agosto e seus21 destinos aprovados permanecem válidos, ainda sujeitos à aplicação e validação final já registrada.

## Corte de ownership corrigido — histórico supersedido

`zuout.com` e `finanzas.zuout.com` pertencem a MGS/G002 antes de2026-09-19 e Nicolas/G006 somente desde2026-09-19. Isso supersede a referência anterior a18/09; agosto permanece MGS nos dois domínios.

As demais regras GAM e exceções continuam em `data/finance-gam-revenue-rules.json`; esta decisão corrige o corte de ownership, não torna o medium original ausente nem autoriza descartar sua evidência.

O readback vivo de setembro, revisão426, contém seis fatos de15–18/09 com medium bruto `g006-d`, total CAD67.368814485529361227. Os IDs e valores foram preservados em evidência privada. Existe uma diferença entre ownership declarado e medium explícito histórico; não classificar como anomalia, pois a regra anterior de G006 já está registrada na decisão `FINANCE-GAM-MANAGER-ATTRIBUTION-ZUOUT-G006-1549590981836275724`. Antes de reescrever esses fatos, reconciliar se o corte19/09 também substitui a atribuição ao gestor explicitamente marcada na fonte. A confirmação dos21 destinos de agosto não deve ser pedida novamente.

## Persistência e validação

- Artefato executado: `/root/mgs-agent/apps/finance-system/private/approved-attribution-1551312942182441111/record_approval.py`.
- Plano aprovado linha a linha: `approved-allocation.json`,329 fontes únicas,21 domínios,USD722.61.
- Releitura live do AV pelo helper Google/SA canônico: conteúdo integral idêntico ao usado na prévia.
- Validação `verification.json`: PASS; Cliquet US; corte19/09; zero escritas financeiras.
- Skill financeira, referência de atribuição e documentação GAM corrigidas com supersessão expressa da data18/09.
- Regra pós-fechamento20–25 continua válida, sem criar cron.

## Limite de conclusão

A classificação do filtro está aprovada e materializada, mas ainda NÃO aplicada ao workspace financeiro. A conciliação global AV/M2 também não foi encerrada: preservar o checkpoint de aplicação e resolver separadamente a classificação do tracking fora do filtro e os ajustes mensais por domínio. Não dizer que a dash foi atualizada, não duplicar USD722.61 e não reabrir a confirmação já concedida dos21 destinos.
