# Parecer de viabilidade — histórico financeiro janeiro a julho2026

## Pedido e limite
Rodolfo1546757745078968381, thread1545426987756298340. Analisar sete meses fechados e confirmar viabilidade antes de importar; valores finais da principal/gestores, sem o motor atual. Agosto+ preservado. Pedido adicional de quatro logins ainda sujeito a confirmação crítica e identidadeÍcaro.

## Resultado
Viável tecnicamente mediante um módulo histórico de somenteleitura, separado dos workspaces calculados. Não basta acrescentar datas ao seletor: periods.mjs inicia em agosto/2026, modelos usam estrutura/grafoagosto e manager-view.mjs é fixoNicolas. Não houve importação nem criação de contas.

## Cobertura integral de leitura
- Principal: Janeiro,Fevereiro,Marco,Abril,Maio,Junho,Julho2026.
- Kelly,Isliago,Joe,Nicolas: todas as sete abas.
- George: Marco,Abril,Maio,Junho,Julho; nenhuma aba janeiro/fevereiro nas propriedades reais.
- 40abas mensais presentes + CAIXA SINTETICOA:I =41abas lidas em6arquivos;377907células mensais não vazias,40calendários com todos os dias do respectivo mês.
- Busca direta por Icaro/Ícaro/ICARO e busca paginada ampla de planilhasfinanceiras não identificaram sua fonte própria; há menções aÍcaro na principal. Não assumir George=Ícaro.
- FonteGustavo aparece em dependências históricas, mas não foi consultada como planilha de gestor, conforme restrição vigente; seus valores já presentes na principal não foram descartados.

## Por mês
- Janeiro:5abas mensais acessíveis, principal antigo com360colunas usadas;132ROI DIV0. Nicolas2REFlegados.
- Fevereiro:5abas,360colunas;148ROI DIV0. Nicolas2REFlegados.
- Março:6abas,879colunas principal;zeroerros exibidos nas6abas.
- Abril:6abas,879colunas principal;22VALUEprincipais originados por S19texto waves(PortalRelevante). Afeta indicadores na linha19 e totais36; demaisgestores semerros. Caixaabril preserva total válido.
- Maio:6abas,879colunas principal;zeroerros exibidos.
- Junho:6abas,993colunas e338linhas principais;zeroerros exibidos.
- Julho:6abas,1041colunas e338linhas principais;zeroerros exibidos.

Os306errosmensais são valores indisponíveis hoje, não prova de que o fechamento validado pelo usuário estava incorreto. ROI com denominadorzero é diferente de valor financeiro faltante. Não substituir por zero nem recomputar automaticamente.

## Resumo fechado
CAIXA SINTETICO C:I tem cabeçalhosJan–Jul e DOLARFECHADO, sem células de erro. Valores da linha77(MM TotalNET), exatamente comoexibidos:
- JanUS$46725.54
- FevUS$112230.94
- MarUS$99402.43
- AbrUS$111291.59
- MaiUS$84176.63
- JunUS$65070.43
- JulUS$27966.64
São leituras, não fechamentos recalculados nem números já importados. Detalhamento por site e por gestor deve preservar cada visão da origem, sem forçar igualdade com o resumo ou contar duas vezes.

## Bloqueios de fidelidade/identidade
- AbrilS19texto waves no lugar de receita numérica: não há valor final calculado em parte do bloco/total; preservar indisponibilidade até fontevalidada/decisão de Rodolfo.
- Nicolasjan/fev P1faz referência aJulho2024!ER95;AF38aponta parafontelegada1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso (404aoSA). Nenhum fallbackdeidentidade/consentimento/permissão tentado. Números não podem ser inventados para recuperar o bloco.
- Georgejan/fev ausentes; não presumir meseszerados nem exigir se ainda não existia.
- Ícaro: documento/manager_key próprio não identificado. Bloqueia concessão segura doacesso.

## Desenho recomendado (não implementado)
Snapshot histórico por competência, documento, aba, bloco e célula; valor efetivo bruto, valor formatado, moeda, data, status de disponibilidade eproveniência. Calendário eblocosdescobertos por mês, incluindo faixas inferiores/compartilhadas. Armazenar totais prontos sem nova soma para substituirfechamento; nunca aplicar regra atual de salário/comissão/ROI/câmbio aos sete meses. Manter realizado/estimativa/alternativasdecomissão distintos. Janeiro/fevereiro misturam USD/BRL na mesma estrutura; não rotular tudoUSD.
Módulo separadodeedição/refreshcotações/ledgeratual. Hoje não há Jan–Jul cadastrado; expansão requer testes antes da publicação. Comparar cópia célulaacélula, valores eformatos, contraasfontes; não reabrirauditoria financeira pelo motor.

## Acessos
finance_users continha apenasNicolas habilitado (Rodolfo é proprietário separado). Joe,Isliago,Kelly,Ícaro não criados. createusers e manager-workspace permitem somenteNicolas atualmente. Expandir por manager_key, dados próprios e testesnegativos entre todos; nada de criação direta contornando a validação ou rolepartner. Confirmar criação/ativação e novascredenciais com Rodolfo; armazenamento exclusivamente1Password.

## Evidências e execução
apps/finance-system/private/history-feasibility-1546757745078968381: metadata.json; arquivosmensaisgridcompleto/cells/summary;caixa-jan-jul.json;analysis.json;all-labels-and-currencies.json;dependency-ids.json;legacy-source-probe.json;nicolas-legacy-blocks.json;manifest.json;final-readback.json.
Coletor tests/history-feasibility.py comSAcanônico, Drive+Sheets preflight, somenteGET, campos efetivo/formatado/formula paraauditoria, todasaslinhas/colunas dasabas nomeadas, semexportfiltrado nemUSUARIOSBOT. Evidências locais comhash, metadados e persistência poraba.
Umafalha inicial de diretórioexistente corrigida comexist_ok=True; capturas então concluídas. Nenhum processo assíncrono, alteração Sheets, importação financeira, login criado ougatewayrestart. Persistência apenas em análise/scripts, direção deproduto,skill,registry/checkpoint/inbox/inventário/audit/report.
