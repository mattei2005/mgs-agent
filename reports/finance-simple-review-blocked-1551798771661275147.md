# Conferência simples — candidato preparado; publicação bloqueada

Autoridade de apresentação: Rodolfo `1551798771661275147`; escopo funcional dos seis itens: `1551798171628212275`; thread `1545426987756298340`.

## Estado

Código candidato preparado para mostrar somente gross CAD Rede1, gross USD Rede2, gross USD AV, gross USD M2, gastos Facebook e gastos Google, por competência, com total e detalhamento opcional por site. Despesas, folha, saldos, regras técnicas e prévia do próximo mês não aparecem no novo frontend. Endpoints técnicos anteriores permanecem sem mudança de semântica. A projeção é read-only, não faz reconciliação externa automática nem marca um mês conferido.

Ainda NÃO publicado. O gate completo e a aceitação browser não foram concluídos porque a simulação obrigatória de preenchimento outubro versus conferência setembro encontrou uma falha preexistente do editor financeiro, fora do escopo de apresentação.

## Verificações concluídas

- Backup exato dos quatro arquivos existentes; módulo `simple-review.mjs` novo. Dump PostgreSQL transferido/hash verificado e restaurado em `mgs_finance_prevention_1551798771661275147`.
- TDD RED por módulo ausente seguido de sete testes unitários aprovados.
- Leitura da projeção dos seis itens nas 17 competências em banco restaurado; controles anteriores à simulação passaram, incluindo acesso owner, 403 para partner/manager, gestores legíveis e futuro sem valores herdados.
- Agosto: CAD Rede1 292199.235848737593194682; USD Rede2 87151.001420629773761489; USD AV 106920.78; USD M2 4611.87; Facebook USD 286368.15; Google BRL 71174.24. Os totais agregados respeitam a auditoria anterior; centavos não foram corrigidos.
- Setembro apresenta USD 143.85282264606195 de Fincgriffin sem rede comprovada na projeção: posições legadas USD, cadastro de rede atual SB Rede1, sem componente de origem por rede nessas posições. Não presumir AV ou Rede2 nem reclassificar. O candidato mostra valor agrupado explicitamente pendente; não mistura com total confirmado de rede. O primeiro teste exigia zero desconhecidos indevidamente; foi corrigido para testar essa lacuna real explícita, sem mudar valores.
- Código produtivo dos cinco alvos ainda coincide com `before-hashes.json` (módulo novo ausente em produção). `calc.py`, `gross_pairs.py`, `worker.py`, `ui_model.py` e `periods.py` locais coincidem com produção: a falha descrita abaixo não foi introduzida pela apresentação candidata.
- Serviços produtivos PostgreSQL/dashboard/socket ativos. Nenhuma escrita financeira produtiva nesta tarefa.

## Bloqueio reproduzido

No banco restaurado, o próprio modelo do editor expõe `principal|Agosto 2026|D5` como campo de receita CAD editável na competência outubro. A identidade interna conserva o nome Agosto por compatibilidade do grafo; o request e a data pertencem a outubro.

POST isolado `/api/scenarios/workspace-2026-10/ui-inputs` com revisão correta, `period=2026-10`, par CAD sintético 123.45 e USD vazio retornou 500. Reprodução direta do mesmo motor identificou:

`calc.CalculationError: override is not an input`

Chave exata: `principal|Agosto 2026|D5`; registro sem `kind`, sem fórmula e sem `input`; override gerado do tipo Decimal.

Causa: `worker.run()` chama `prepare_inputs()` antes de `gross_pairs.prepare()`. O par de moedas depois acrescenta um override para uma posição originalmente vazia que ainda não foi materializada como entrada; `Workbook.get()` o rejeita corretamente pelo guard de origem. Não enfraquecer o guard nem escolher outro campo de teste apenas para obter verde.

A simulação de correção posterior de setembro não foi executada, pois a primeira gravação de outubro falhou antes do commit. O finally restaurou os dois snapshots do banco de teste; readback das respostas setembro/outubro iguais às capturas pré-simulação foi confirmado. Nenhum restore foi aplicado em produção.

## Decisão necessária

Recomendação: autorizar ampliar o escopo somente para corrigir a preparação dos campos originais vazios expostos pelo editor de receita, sem mudar fórmulas, regras de comissão, atribuições, taxas ou valores existentes. Reproduzir RED específico, corrigir o reconhecimento de entrada em cópia de cálculo, repetir a simulação nos dois sentidos, a suíte completa e os controles de preservação antes de publicar a simplificação.

Sem essa autorização, o candidato permanece em stage, a versão produtiva anterior é preservada e não se declara concluída a validação de virada do mês.

Evidência protegida: `apps/finance-system/private/simple-review-1551798771661275147/`, incluindo `blocked-verification.json`, `stage-run.log`, backup, TDD e snapshot de diagnóstico setembro. Stage: `/var/tmp/mgs-finance-prevention-1551798771661275147`. Preservar artefatos e banco isolado; nenhuma limpeza destrutiva autorizada.
