# Setembro — ponto4/Google: precisão e arredondamento

Autoridade1562622867873603655: explicar o ponto4, sem aplicação. FonteGastos Google,gid1132083250, spreadsheet1ARyzDDEpVhlED6ndmHs1RC3pUlsJNQ20yTyZ6wSJVtA; relida integralmente e idêntica. Dash atualworkspace-2026-09 revisão1653,cadastro19; pontos1–3 preservados.

## Prova

43registros de origemGoogle:13Gamingadx-US-01 e30Mattei1/GameZoneAd. Os43inputs vivos coincidem exatamente com osamounts capturados pelaAPI e todos satisfazemcost_micros/1000000=amount. As43linhas da planilha correspondem aos mesmos valores arredondados a centavos por dia.

- Gamingadx-US-01: soma originalDashBRL5350.600433→exibição5350,60; soma de cada dia arredondado/planilha5350,59. Diferença original0.010433BRL.
- Mattei1: soma originalDashBRL106197.327563→exibição106197,33; soma diária arredondada/planilha106197,30. Diferença original0.027563BRL.
- TotalDashBRL111547.927996→exibição111547,93.
- Total43dias arredondados individualmente/planilhaBRL111547,89.
- Diferença originalBRL0.037996; diferença exibidaBRL0,04.

Exemplo realGamingAdx01/09:API441944193micros=BRL441.944193; relatórioBRL441,94. Não há gasto ausente nesse conjunto nem efeito de conversãoUSD; é ordem de arredondamento.

## Disposição proposta

Recomendação: preservar a precisão original daAPI e registrar a diferença de apresentação, sem lançamento compensatório. Isso mantémDash111547,93 versus soma arredondada111547,89; não declarar igualdade dos totais exibidos.

Se Rodolfo determinar paridade visual estrita com o relatório neste fechamento, o plano correto é usar os43valores diários de centavos do relatório, mantendo origemmicros em evidência, recalculando o resultado e limitando a exceção a setembro. Não inserir desconto0,04 em dia aleatório, não alterar câmbio nem estabelecer regra global de arredondamento por inferência. Essa alternativa ainda não foi autorizada/aplicada.

Evidência:workspaceprivado`apps/finance-system/private/september-closing-1562564679400951829/`,point4-source-readback.json,point4-explanation.json,point4-before-*.json ecomparison.json. Nenhuma escrita financeira neste turno. Próximo passo: decisão de Rodolfo sobre preservar precisão ou alinhar os centavos diários do fechamento; não avançar paraM2 antes do alinhamento.
